"""Streaming equivalent of the frozen five-evidence Box2 detector.

Uses its same legacy evidence, fusion, persistence and situation-assessment
objects, rather than recalibrating or changing their decision rules.
"""
from math import isfinite
from bess.box2.five_evidence import _score
from bess.box2.legacy.sync_evidence import SynchronizationEvidence
from bess.box2.legacy.temporal_evidence import TemporalEvidence
from bess.box2.legacy.voltage_evidence import VoltageEvidence
from bess.box2.legacy.freshness_evidence import FreshnessEvidence
from bess.box2.legacy.evidence_fusion import EvidenceFusion
from bess.box2.legacy.persistence import PersistenceAssessment
from bess.box2.legacy.attack_classifier import AttackTypeClassifier
from bess.box2.legacy.situation_assessment import SituationAssessment

class OnlineFiveEvidence:
    def __init__(self, calibration):
        self.cal=calibration
        self.sync=SynchronizationEvidence(envelopes=calibration.envelopes,region_source='twin')
        self.voltage=VoltageEvidence(p95_threshold=calibration.voltage['p95'],p99_threshold=calibration.voltage['p99'])
        self.freshness=FreshnessEvidence(p95_threshold=0.,p99_threshold=1.)
        self.temporal=TemporalEvidence()
        self.fusion=EvidenceFusion()
        self.persistence=PersistenceAssessment(persistence_limit=3)
        self.classifier=AttackTypeClassifier()
        self.situation=SituationAssessment()
        self.prev_soc=None
        self.prev_twin=None
        self.prev_time=None

    def step(self, *, time_min, telemetry_soc_pct, soc_estimated_pct,
             telemetry_voltage_v, voltage_predicted_v,
             source_timestamp_min, receive_timestamp_min):
        vals=(time_min,telemetry_soc_pct,soc_estimated_pct,telemetry_voltage_v,
              voltage_predicted_v,source_timestamp_min,receive_timestamp_min)
        if not all(isfinite(float(v)) for v in vals): raise ValueError('Nonfinite telemetry')
        if self.prev_time is not None and time_min <= self.prev_time:
            raise ValueError('Non-increasing telemetry time')
        soc=float(telemetry_soc_pct); twin=float(soc_estimated_pct)
        s=self.sync.calculate_score(twin,twin,soc)
        pe=0. if self.prev_soc is None else abs((soc-self.prev_soc)-(twin-self.prev_twin))
        p=_score(pe,self.cal.physics)
        t=self.temporal.evaluate(soc,float(source_timestamp_min), expected_interval=1.,
                expected_soc_change=0. if self.prev_twin is None else twin-self.prev_twin)['temporal_score']
        v=self.voltage.calculate_score(float(telemetry_voltage_v),float(voltage_predicted_v),'2A')
        f=self.freshness.calculate_score(float(receive_timestamp_min),float(source_timestamp_min))
        fused=self.fusion.fuse(s,p,t,v,f)
        persistent=self.persistence.update(fused['fusion_score'])
        cls=self.classifier.classify(s,p,t,v,f,fused['fusion_score'])
        assessment=self.situation.assess(persistent['final_classification'],cls['attack_type'],cls['confidence'])
        self.prev_soc=soc;self.prev_twin=twin;self.prev_time=time_min
        return {'classification':persistent['final_classification'],
                'attack_assessment':assessment['attack_assessment'],
                'alarm':int(persistent['final_classification']=='ABNORMAL'),
                'sync_score':s,'physics_score':p,'freshness_score':f,
                'temporal_score':t,'voltage_score':v}
