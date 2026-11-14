"""Exploratory multi-window SOC residual drift audit. NOT a validated detector.

Source-profile calibration, causal windows, and per-window indicators. Correlated
window comparisons are NOT a statistical false-alarm guarantee. Window choices
were examined on these related profiles: results are developmental only.
"""
from dataclasses import dataclass
import numpy as np
import pandas as pd
from .signed_increment import _residual

WINDOWS=(4,8,16,32)

@dataclass(frozen=True)
class MultiWindowCalibration:
    windows: tuple
    positive_limits: tuple
    negative_limits: tuple
    source_profiles: int
    guard: float


def calibrate_windows(source_clean, windows=WINDOWS, guard=1.5):
    windows=tuple(windows)
    if not windows or any(not isinstance(w,int) or w<1 for w in windows) or len(set(windows))!=len(windows):
        raise ValueError('windows must be unique positive integers')
    if not np.isfinite(guard) or guard<=1: raise ValueError('guard must exceed 1')
    if not source_clean:raise ValueError('clean source profiles required')
    residuals=[]
    for f in source_clean:
        if 'truth_attack' in f and f.truth_attack.astype(bool).any():
            raise ValueError('attacked calibration source')
        r=_residual(f)
        if len(r)<=max(windows):raise ValueError('source too short')
        residuals.append(r)
    pos=[];neg=[]
    for w in windows:
        values=np.concatenate([r[w:]-r[:-w] for r in residuals])
        pos.append(max(float(np.max(values)),0.,.01)*guard)
        neg.append(max(float(-np.min(values)),0.,.01)*guard)
    return MultiWindowCalibration(windows,tuple(pos),tuple(neg),len(residuals),float(guard))


def detect_windows(telemetry, calibration):
    r=_residual(telemetry)
    n=len(r);out={}; flags=[]
    for w,p,nlim in zip(calibration.windows,calibration.positive_limits,calibration.negative_limits):
        delta=np.zeros(n)
        delta[w:]=r[w:]-r[:-w]
        up=np.zeros(n,dtype=bool);down=up.copy()
        up[w:]=delta[w:]>p
        down[w:]=delta[w:]< -nlim
        flags.append(up|down)
        out[f'delta_{w}_pp']=delta
        out[f'up_{w}']=up.astype(int)
        out[f'down_{w}']=down.astype(int)
    out['alarm']=np.logical_or.reduce(flags).astype(int)
    return pd.DataFrame(out)
