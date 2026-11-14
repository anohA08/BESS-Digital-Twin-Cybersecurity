"""Deterministic attack replay, ported from previous repository's Box2 validation.

Attack labels are returned for evaluation only, never detector inputs.
All attacks modify telemetry, not the physical battery or independent twin.
"""
from dataclasses import dataclass
import numpy as np
import pandas as pd

LEGACY_SCENARIOS = ("normal", "spoof_5", "spoof_10", "spoof_15", "spoof_20",
                    "fixed_replay", "rolling_replay", "delay_3min")
ADDITIONAL_SCENARIOS = ("spoof_m5", "spoof_m2", "spoof_p2", "spoof_ramp_p5")
ALL_SCENARIOS = LEGACY_SCENARIOS + ADDITIONAL_SCENARIOS

@dataclass(frozen=True)
class AttackWindow:
    start: int = 40
    stop: int = 110  # exclusive; matching previous Box2 validation

    def validate(self, n: int) -> None:
        if not (1 <= self.start < self.stop <= n):
            raise ValueError("Require 1 <= start < stop <= number of observations")


def inject_attack(clean: pd.DataFrame, scenario: str, window: AttackWindow = AttackWindow()) -> pd.DataFrame:
    """Return a telemetry copy with original reference values and evaluation-only truth.

    Expected Box 1 run_replay columns: time_min, voltage_measured_v,
    soc_recorded_for_evaluation_only_pct, voltage_predicted_v,
    soc_estimated_pct. Recorded SOC is a surrogate report, NOT authenticated BMS SOC.
    """
    if scenario not in ALL_SCENARIOS:
        raise ValueError(f"Unsupported attack scenario: {scenario}")
    window.validate(len(clean))
    required = ('time_min','voltage_measured_v','soc_recorded_for_evaluation_only_pct',
                'voltage_predicted_v','soc_estimated_pct')
    if any(c not in clean.columns for c in required):
        raise ValueError("Missing Box 1 replay fields")
    df = clean.copy(deep=True).reset_index(drop=True)
    for col in required:
        vals = pd.to_numeric(df[col], errors='coerce').to_numpy(dtype=float)
        if not np.isfinite(vals).all():
            raise ValueError(f"Nonfinite input: {col}")
    times = df.time_min.to_numpy(dtype=float)
    if (np.diff(times) <= 0).any():
        raise ValueError("Non-increasing source time")
    df['telemetry_soc_pct'] = df['soc_recorded_for_evaluation_only_pct'].astype(float)
    df['telemetry_voltage_v'] = df['voltage_measured_v'].astype(float)
    df['source_timestamp_min'] = df['time_min'].astype(float)
    df['receive_timestamp_min'] = df['time_min'].astype(float)
    df['truth_attack'] = 0
    df['attack_window'] = 0
    df.loc[window.start:window.stop-1,'attack_window'] = 1
    if scenario == 'normal':
        return df
    indices = np.arange(window.start,window.stop)
    df.loc[indices,'truth_attack'] = 1
    if scenario.startswith('spoof_'):
        if scenario == 'spoof_ramp_p5':
            offsets = np.linspace(0.0, 5.0, len(indices))
        elif scenario.startswith('spoof_m'):
            offsets = -float(scenario.removeprefix('spoof_m'))
        elif scenario.startswith('spoof_p'):
            offsets = float(scenario.removeprefix('spoof_p'))
        else:
            offsets = float(scenario.split('_')[1])
        df.loc[indices,'telemetry_soc_pct'] = np.clip(
            df.loc[indices,'telemetry_soc_pct'].to_numpy(dtype=float) + offsets, 0., 100.)
    elif scenario == 'fixed_replay':
        i = window.start - 1
        df.loc[indices,'telemetry_soc_pct'] = float(df.at[i,'telemetry_soc_pct'])
        df.loc[indices,'telemetry_voltage_v'] = float(df.at[i,'telemetry_voltage_v'])
        # Source timestamps refreshed by design: *not* authenticated packet replay.
    elif scenario == 'rolling_replay':
        source_indices = np.maximum(0, indices-8)
        df.loc[indices,'telemetry_soc_pct'] = df.loc[source_indices,'telemetry_soc_pct'].to_numpy()
        df.loc[indices,'telemetry_voltage_v'] = df.loc[source_indices,'telemetry_voltage_v'].to_numpy()
    elif scenario == 'delay_3min':
        df.loc[indices,'receive_timestamp_min'] += 3.0
    return df
