"""Research-only Box 3. No physical actuator or live controller interface.

Inputs: pre-assimilation twin SOC, possibly attacked sensor SOC, Box2 result.
Ground-truth SOC is never consumed here. Fresh state per independent run.
"""
from dataclasses import dataclass
from math import isfinite


def bounded(x, lo, hi):
    if not all(isfinite(float(v)) for v in (x, lo, hi)) or lo >= hi:
        raise ValueError('Invalid numeric value or SOC bounds')
    return max(float(lo), min(float(hi), float(x)))


@dataclass(frozen=True)
class Config:
    soc_min: float = 10.0
    soc_max: float = 100.0
    severe_trust: float = 0.35
    cautious_trust: float = 0.70
    trust_penalty_confirmed: float = 0.35
    trust_penalty_suspected: float = 0.07
    trust_recovery_step: float = 0.04
    clean_required: int = 5
    minimum_mode_samples: int = 3
    max_soc_correction_pp: float = 1.0
    max_power_kw: float = 100.0  # PLACEHOLDER research rating; user must configure
    cautious_power_fraction: float = 0.5


class TrustManager:
    """Trust is a heuristic policy score, NOT a calibrated attack probability."""
    def __init__(self, config=None):
        self.cfg = config or Config()
        self.trust = 1.0
        self.clean_streak = 0

    def update(self, assessment):
        state = str(assessment.get('attack_assessment', '')).upper()
        fused = str(assessment.get('fusion_classification', '')).upper()
        if state == 'ATTACK_DETECTED':
            self.trust = max(0, self.trust - self.cfg.trust_penalty_confirmed)
            self.clean_streak = 0
        elif state in ('ATTACK_SUSPECTED', 'UNEXPLAINED_ANOMALY') or fused == 'SUSPICIOUS':
            self.trust = max(0, self.trust - self.cfg.trust_penalty_suspected)
            self.clean_streak = 0
        elif state == 'NO_ATTACK_DETECTED' and fused == 'NORMAL':
            self.clean_streak += 1
            if self.clean_streak >= self.cfg.clean_required:
                self.trust = min(1.0, self.trust + self.cfg.trust_recovery_step)
        else:
            self.clean_streak = 0
        return self.trust


class RecoveryManager:
    """Conservative hysteresis and dwell: SAFE can only clear after stable clean evidence."""
    def __init__(self, config=None):
        self.cfg = config or Config()
        self.mode = 'NORMAL'
        self.samples_in_mode = 0

    def update(self, trust, clean_streak):
        self.samples_in_mode += 1
        if trust <= self.cfg.severe_trust:
            candidate = 'SAFE'
        elif trust < self.cfg.cautious_trust:
            candidate = 'CAUTIOUS'
        else:
            candidate = 'NORMAL'
        if candidate == self.mode:
            return self.mode
        # Escalation is immediate; de-escalation requires clean streak and minimum dwell.
        severity = {'NORMAL': 0, 'CAUTIOUS': 1, 'SAFE': 2}
        if severity[candidate] > severity[self.mode]:
            self.mode = candidate
            self.samples_in_mode = 0
        elif clean_streak >= self.cfg.clean_required and self.samples_in_mode >= self.cfg.minimum_mode_samples:
            # Step down only one mode each recovery transition.
            self.mode = 'CAUTIOUS' if self.mode == 'SAFE' else 'NORMAL'
            self.samples_in_mode = 0
        return self.mode


class ResilientEstimator:
    """Policy-level estimate. Do not confuse with a validated EKF or secure observer."""
    def __init__(self, config=None):
        self.cfg = config or Config()
        self.previous_output = None

    def estimate(self, predicted_soc, sensor_soc, trust, mode):
        model = bounded(predicted_soc, self.cfg.soc_min, self.cfg.soc_max)
        sensor = bounded(sensor_soc, self.cfg.soc_min, self.cfg.soc_max)
        # In SAFE mode do NOT assimilate suspect sensor; caution limits its influence.
        weight = 0.0 if mode == 'SAFE' else min(0.5, trust * 0.5)
        correction = max(-self.cfg.max_soc_correction_pp,
                         min(self.cfg.max_soc_correction_pp, weight * (sensor - model)))
        estimate = bounded(model + correction, self.cfg.soc_min, self.cfg.soc_max)
        self.previous_output = estimate
        return {'soc_estimate': estimate, 'sensor_weight': weight,
                'applied_sensor_correction_pp': correction}


class MitigationController:
    """Computes advisory limits only. Cannot issue commands to physical BESS."""
    def __init__(self, config=None):
        self.cfg = config or Config()
        if self.cfg.max_power_kw <= 0 or not 0 < self.cfg.cautious_power_fraction <= 1:
            raise ValueError('Invalid configured power rating')

    def advise(self, requested_power_kw, soc_estimate, mode):
        if not isfinite(float(requested_power_kw)):
            raise ValueError('Invalid power request')
        cap = (0.0 if mode == 'SAFE' else
               self.cfg.max_power_kw * (self.cfg.cautious_power_fraction if mode == 'CAUTIOUS' else 1.0))
        requested = float(requested_power_kw)
        power = max(-cap, min(cap, requested))
        # Convention: +kW discharge, -kW charge.
        if soc_estimate <= self.cfg.soc_min + 1e-6 and power > 0:
            power = 0.0
        if soc_estimate >= self.cfg.soc_max - 1e-6 and power < 0:
            power = 0.0
        return {'advisory_power_kw': power, 'advisory_limit_kw': cap,
                'note': 'Research-only advisory; no actuator connection or verified safety guarantee'}


class Box3Coordinator:
    def __init__(self, config=None):
        self.cfg = config or Config()
        self.trust = TrustManager(self.cfg)
        self.recovery = RecoveryManager(self.cfg)
        self.estimator = ResilientEstimator(self.cfg)
        self.mitigation = MitigationController(self.cfg)

    def step(self, box2_result, twin_soc_pre_assimilation, sensor_soc, requested_power_kw):
        trust = self.trust.update(box2_result)
        mode = self.recovery.update(trust, self.trust.clean_streak)
        estimation = self.estimator.estimate(twin_soc_pre_assimilation, sensor_soc, trust, mode)
        mitigation = self.mitigation.advise(requested_power_kw, estimation['soc_estimate'], mode)
        return {'trust_score': trust, 'trust_mode': mode, 'clean_streak': self.trust.clean_streak,
                **estimation, **mitigation}
