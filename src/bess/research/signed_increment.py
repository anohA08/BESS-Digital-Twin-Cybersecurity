"""Source-calibrated signed SOC residual increment *research candidate*.

This detector is NOT a novel algorithm, not a conformal predictor, and offers
NO distribution-free false-alarm control or attack detection guarantee.
It can detect discontinuities, not low-amplitude gradual drift or steady bias
already present before monitoring begins.
"""
from dataclasses import dataclass
import numpy as np
import pandas as pd

@dataclass(frozen=True)
class SignedIncrementCalibration:
    positive_limit_pp: float
    negative_limit_pp: float
    source_profiles: int
    source_differences: int
    guard_multiplier: float


def _residual(frame):
    required=('telemetry_soc_pct','soc_estimated_pct')
    if not all(col in frame.columns for col in required):
        raise ValueError('SOC telemetry and independent twin estimate required')
    a=frame.telemetry_soc_pct.to_numpy(dtype=float)
    b=frame.soc_estimated_pct.to_numpy(dtype=float)
    if len(a)<3 or not np.isfinite(a).all() or not np.isfinite(b).all():
        raise ValueError('At least three finite values required')
    return a-b


def calibrate_signed_increment(source_clean, *, guard_multiplier=1.5):
    """Limit = guard * worst signed step on clean source profiles.

    The guard is a fixed engineering sensitivity parameter, NOT selected to
    guarantee FAR and NOT tuned on held-out attacked target profiles.
    """
    if not np.isfinite(guard_multiplier) or guard_multiplier<=1:
        raise ValueError('guard_multiplier must exceed 1')
    if not source_clean:raise ValueError('Need source-only clean profiles')
    d=[]
    for frame in source_clean:
        if 'truth_attack' in frame.columns and frame.truth_attack.to_numpy(dtype=bool).any():
            raise ValueError('Calibration contains attack-labeled samples')
        d.append(np.diff(_residual(frame)))
    delta=np.concatenate(d)
    return SignedIncrementCalibration(
        positive_limit_pp=max(float(np.max(delta)),0.,0.01)*guard_multiplier,
        negative_limit_pp=max(float(-np.min(delta)),0.,0.01)*guard_multiplier,
        source_profiles=len(source_clean),source_differences=len(delta),
        guard_multiplier=guard_multiplier)


def detect_signed_increment(telemetry, calibration, *, hold_samples=3):
    """Causal first differences, sign-separated onset flags, short alarm hold.

    This is a *change detector*, not a magnitude/bias detector: an abrupt
    innocent measurement reset may look identical to an attack step.
    """
    if not isinstance(hold_samples,int) or hold_samples<1:
        raise ValueError('hold_samples must be positive integer')
    r=_residual(telemetry)
    d=np.r_[0.,np.diff(r)]
    up=d>calibration.positive_limit_pp
    down=d< -calibration.negative_limit_pp
    onset=up|down
    age=0;alarms=[]
    for event in onset:
        age=hold_samples if event else max(0,age-1)
        alarms.append(int(age>0))
    return pd.DataFrame(dict(soc_residual_pp=r,signed_increment_pp=d,
         positive_onset=up.astype(int),negative_onset=down.astype(int),
         onset=onset.astype(int), alarm=alarms))
