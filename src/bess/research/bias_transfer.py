"""Exploratory source-only bias calibration; not an attack-intent detector.

Frozen protocol: fit degree-2 SOC polynomial with ridge (lambda=0.01), then
calibrate 95%-quantile of absolute source residuals. No target tuning.
"""
from dataclasses import dataclass
import numpy as np

@dataclass(frozen=True)
class BiasModel:
    coefficients: tuple
    residual_limit_pp: float
    raw_limit_pp: float
    source_profiles: int

def _extract(frame):
    needed=('telemetry_soc_pct','soc_estimated_pct')
    if not all(k in frame for k in needed): raise ValueError('missing telemetry')
    x=np.asarray(frame['soc_estimated_pct'],float)
    y=np.asarray(frame['telemetry_soc_pct'],float)-x
    if len(x)<3 or not np.isfinite(x).all() or not np.isfinite(y).all():raise ValueError('nonfinite or short telemetry')
    return x,y

def _features(x):
    z=(np.asarray(x)-50.)/50.
    return np.column_stack([np.ones_like(z),z,z*z])

def fit_bias_model(source_clean, *, alpha=.05):
    if not 0<alpha<1 or not source_clean:raise ValueError('invalid calibration')
    xs=[];ys=[]
    for frame in source_clean:
        if 'truth_attack' in frame and np.asarray(frame['truth_attack']).astype(bool).any():
            raise ValueError('attacked calibration source')
        x,y=_extract(frame);xs.append(x);ys.append(y)
    x=np.concatenate(xs);y=np.concatenate(ys)
    a=_features(x); reg=np.diag([0.,.01,.01]);coef=np.linalg.solve(a.T@a+reg,a.T@y)
    residual=y-a@coef
    limit=float(np.quantile(np.abs(residual),1-alpha,method='higher'))
    raw_limit=float(np.quantile(np.abs(y),1-alpha,method='higher'))
    return BiasModel(tuple(float(v) for v in coef),limit,raw_limit,len(source_clean))

def evaluate_soc_flags(frame,model,*,persistence=3):
    if persistence<1:raise ValueError('invalid persistence')
    x,y=_extract(frame)
    corrected=y-_features(x)@np.asarray(model.coefficients)
    raw=np.abs(y)>model.raw_limit_pp
    bias=np.abs(corrected)>model.residual_limit_pp
    def persist(flags):
        streak=0;out=[]
        for f in flags:
            streak=streak+1 if f else 0
            out.append(int(streak>=persistence))
        return np.asarray(out,dtype=int)
    return {'raw':persist(raw),'bias_aware':persist(bias),'raw_residual':y,'corrected_residual':corrected}
