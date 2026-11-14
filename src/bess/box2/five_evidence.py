"""Five-evidence Box 2 adapter for the three legacy attack families.

Ports the original synchronization, temporal, voltage, freshness, fusion,
persistence, signature classifier, and situation-assessment classes. The
physical SOC-step evidence is an independently computed, calibrated
replacement for the old physics validator's SOC-derived energy surrogate.

All static thresholds are estimated from source clean profiles ONLY; the
telemetry's truth/attack_window columns are never read by detection.
The score is an ordinal heuristic, NOT a calibrated attack probability.
"""
from dataclasses import dataclass
import numpy as np
import pandas as pd
from .legacy.sync_evidence import SynchronizationEvidence
from .legacy.temporal_evidence import TemporalEvidence
from .legacy.voltage_evidence import VoltageEvidence
from .legacy.freshness_evidence import FreshnessEvidence
from .legacy.evidence_fusion import EvidenceFusion
from .legacy.persistence import PersistenceAssessment
from .legacy.attack_classifier import AttackTypeClassifier
from .legacy.situation_assessment import SituationAssessment

REQUIRED = ('time_min', 'telemetry_soc_pct', 'soc_estimated_pct',
            'telemetry_voltage_v', 'voltage_predicted_v',
            'source_timestamp_min', 'receive_timestamp_min')
REGIONS = ('high', 'middle', 'low')

def _band(z):
    return 'high' if z >= 80 else 'middle' if z >= 40 else 'low'

def _limits(x):
    v=np.asarray(x,dtype=float)
    if len(v)<2 or not np.isfinite(v).all():
        raise ValueError('At least two finite clean calibration observations required')
    return {'p95':float(np.quantile(v,.95,method='higher')),
            'p99':float(np.quantile(v,.99,method='higher'))}

def _physics_delta_errors(frame):
    """Absolute difference between changes of telemetry SOC and independent twin SOC.

    Both are percentage points per sample. This is NOT independent energy
    metering, and does NOT use attack labels or future samples.
    """
    t=frame.telemetry_soc_pct.to_numpy(float)
    x=frame.soc_estimated_pct.to_numpy(float)
    return np.r_[0.,np.abs(np.diff(t)-np.diff(x))]

@dataclass(frozen=True)
class FiveEvidenceCalibration:
    envelopes: dict
    voltage: dict
    physics: dict
    n_source_profiles: int
    n_source_rows: int

def calibrate_five_evidence(source_clean: list[pd.DataFrame])->FiveEvidenceCalibration:
    if not source_clean:
        raise ValueError('Source-only clean calibration is required')
    sync_by={r:[] for r in REGIONS};volt=[];phys=[];count=0
    for frame in source_clean:
        if not set(REQUIRED).issubset(frame): raise ValueError('Missing input columns')
        if len(frame)<30: raise ValueError('Insufficient source observations')
        if 'truth_attack' in frame and frame.truth_attack.to_numpy().any():
            raise ValueError('Attack-contaminated calibration source')
        soc=frame.telemetry_soc_pct.to_numpy(float);tw=frame.soc_estimated_pct.to_numpy(float)
        if not np.isfinite(soc).all() or not np.isfinite(tw).all():raise ValueError('Nonfinite SOC')
        for est,err in zip(tw,np.abs(soc-tw)):
            sync_by[_band(est)].append(err)
        volt.extend(np.abs(frame.telemetry_voltage_v.to_numpy(float)-frame.voltage_predicted_v.to_numpy(float)))
        phys.extend(_physics_delta_errors(frame)[1:]) # skip artificial first sample
        count+=len(frame)
    global_sync=[v for a in sync_by.values() for v in a]
    # Sparse bins use global source envelope; no target observation used.
    envelopes={r:_limits(values if len(values)>=30 else global_sync) for r,values in sync_by.items()}
    return FiveEvidenceCalibration(envelopes,_limits(volt),_limits(phys),len(source_clean),count)

def _score(v, limits):
    if v<=limits['p95']+1e-12:return 0
    if v<=limits['p99']+1e-12:return 1
    return 2

def detect_five_evidence(telemetry:pd.DataFrame, cal:FiveEvidenceCalibration,
                         *, persistence:int=3)->pd.DataFrame:
    if not set(REQUIRED).issubset(telemetry):
        raise ValueError('Missing required telemetry channels')
    for name in REQUIRED:
        if not np.isfinite(telemetry[name].to_numpy(dtype=float)).all():
            raise ValueError('Nonfinite '+name)
    if not np.all(np.diff(telemetry.time_min.to_numpy(float))>0):
        raise ValueError('Expected strictly increasing receive index time')
    sync=SynchronizationEvidence(envelopes=cal.envelopes,region_source='twin')
    voltage=VoltageEvidence(p95_threshold=cal.voltage['p95'],p99_threshold=cal.voltage['p99'])
    freshness=FreshnessEvidence(p95_threshold=0.,p99_threshold=1.)
    temporal=TemporalEvidence()
    fusion=EvidenceFusion()
    persist=PersistenceAssessment(persistence_limit=persistence)
    classifier=AttackTypeClassifier()
    situation=SituationAssessment()
    rows=[];previous_soc=None;previous_twin=None
    # Evaluate actual observations online; never read truth flags.
    for tup in telemetry.itertuples(index=False):
        soc=float(tup.telemetry_soc_pct);twin=float(tup.soc_estimated_pct)
        sync_score=sync.calculate_score(twin,twin,soc)
        physical_error=0. if previous_soc is None else abs((soc-previous_soc)-(twin-previous_twin))
        physical_score=_score(physical_error,cal.physics)
        time_result=temporal.evaluate(soc,float(tup.source_timestamp_min),expected_interval=1.0,
                  expected_soc_change=0. if previous_twin is None else twin-previous_twin)
        temporal_score=time_result['temporal_score']
        voltage_score=voltage.calculate_score(float(tup.telemetry_voltage_v),float(tup.voltage_predicted_v),'2A')
        freshness_score=freshness.calculate_score(float(tup.receive_timestamp_min),float(tup.source_timestamp_min))
        fused=fusion.fuse(sync_score,physical_score,temporal_score,voltage_score,freshness_score)
        persistent=persist.update(fused['fusion_score'])
        attack=classifier.classify(sync_score,physical_score,temporal_score,voltage_score,freshness_score,fused['fusion_score'])
        assessment=situation.assess(persistent['final_classification'],attack['attack_type'],attack['confidence'])
        rows.append(dict(sync_score=sync_score,physics_score=physical_score,temporal_score=temporal_score,
               voltage_score=voltage_score,freshness_score=freshness_score,physics_delta_error_pp=physical_error,
               fusion_score=fused['fusion_score'],instant_classification=fused['classification'],
               classification=persistent['final_classification'],
               suspected_attack_type=assessment['suspected_attack_type'],
               attack_assessment=assessment['attack_assessment'],alarm=int(persistent['final_classification']=='ABNORMAL')))
        previous_soc=soc;previous_twin=twin
    return pd.DataFrame(rows)
