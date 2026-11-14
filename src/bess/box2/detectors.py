"""Transparent Box 2 baseline detectors. These do not claim statistical FAR guarantees."""
from dataclasses import dataclass
import numpy as np
import pandas as pd


def _quantile(values, alpha=0.05):
    if not (0 < alpha < 1):
        raise ValueError('0 < alpha < 1 required')
    v=np.asarray(values,dtype=float)
    if len(v)<2 or not np.isfinite(v).all():
        raise ValueError('Clean calibration needs at least 2 finite values')
    return float(np.quantile(np.abs(v), 1-alpha,method='higher'))

@dataclass(frozen=True)
class ThresholdConfig:
    soc_limit_pp: float
    voltage_limit_v: float
    alpha: float


def calibrate_global(source_clean: list[pd.DataFrame], alpha:float=.05)->ThresholdConfig:
    """Other profiles only; avoid target-run calibration. Units: pp and V."""
    if not source_clean: raise ValueError('Source clean profiles required')
    soc=[]; voltage=[]
    for df in source_clean:
        if len(df)<2: raise ValueError('Too few source rows')
        soc.extend((df.telemetry_soc_pct-df.soc_estimated_pct).to_numpy(float))
        voltage.extend((df.telemetry_voltage_v-df.voltage_predicted_v).to_numpy(float))
    return ThresholdConfig(_quantile(soc,alpha),_quantile(voltage,alpha),alpha)


def detect_threshold(telemetry: pd.DataFrame, cfg: ThresholdConfig, persistence:int=3)->pd.DataFrame:
    if persistence<1: raise ValueError('persistence must be positive')
    # Pseudosequential baseline: joint OR decision followed by persistence.
    soc_r=(telemetry.telemetry_soc_pct-telemetry.soc_estimated_pct).to_numpy(float)
    vol_r=(telemetry.telemetry_voltage_v-telemetry.voltage_predicted_v).to_numpy(float)
    freshness=(telemetry.receive_timestamp_min-telemetry.source_timestamp_min).to_numpy(float)
    raw_soc=np.abs(soc_r)>cfg.soc_limit_pp
    raw_voltage=np.abs(vol_r)>cfg.voltage_limit_v
    # Timestamp difference is independent telemetry evidence, but simulated delay is not packet-queue model.
    raw_fresh=freshness>2.0
    instant=raw_soc|raw_voltage|raw_fresh
    streak=0; alarms=[]
    for a in instant:
        streak=streak+1 if a else 0
        alarms.append(int(streak>=persistence))
    return pd.DataFrame({'soc_residual_pp':soc_r,'voltage_residual_v':vol_r,
        'soc_flag':raw_soc.astype(int),'voltage_flag':raw_voltage.astype(int),
        'freshness_flag':raw_fresh.astype(int),'instant_flag':instant.astype(int),
        'alarm':alarms})


def detect_cusum(telemetry:pd.DataFrame, calibration:list[pd.DataFrame],
                  reference_drift:float=.5, alarm_threshold:float=5.0)->pd.DataFrame:
    """Two-sided SOC CUSUM with fixed source-only centering/scaling.

    Exploratory baseline, *not* a statistically controlled false-alarm method.
    Voltage is not used in this SOC-only CUSUM; see output label.
    """
    if reference_drift<=0 or alarm_threshold<=0: raise ValueError('Invalid CUSUM parameters')
    source=np.concatenate([(d.telemetry_soc_pct-d.soc_estimated_pct).to_numpy(float) for d in calibration])
    if len(source)<3: raise ValueError('Need source samples')
    mu=float(np.mean(source)); scale=max(float(np.std(source,ddof=1)),1e-6)
    residual=(telemetry.telemetry_soc_pct-telemetry.soc_estimated_pct).to_numpy(float)
    s_pos=s_neg=0.0; out=[]
    for val in residual:
        z=(val-mu)/scale
        s_pos=max(0.,s_pos+z-reference_drift)
        s_neg=max(0.,s_neg-z-reference_drift)
        out.append((s_pos,s_neg,int(max(s_pos,s_neg)>alarm_threshold)))
    return pd.DataFrame(out,columns=['cusum_pos','cusum_neg','alarm'])
