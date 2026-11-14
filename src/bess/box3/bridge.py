"""Explicit mapping between frozen Box2 decisions and Box3 policy.

Only current/timeline predictions, observed surrogate SOC, and live classifications
are permitted. Never pass truth_attack or reference SOC into a policy decision.
"""
from math import isfinite
from .core import Box3Coordinator, Config

CLASSIFICATIONS = {'NORMAL', 'SUSPICIOUS', 'ABNORMAL'}
ASSESSMENTS = {'NO_ATTACK_DETECTED', 'ATTACK_SUSPECTED',
               'UNEXPLAINED_ANOMALY', 'ATTACK_DETECTED'}

def map_box2(row):
    classification = str(row['classification']).upper()
    assessment = str(row['attack_assessment']).upper()
    if classification not in CLASSIFICATIONS or assessment not in ASSESSMENTS:
        raise ValueError('Unknown Box2 classification/assessment')
    # Legacy Box 3 expects fusion_classification; Box 2 exposes classification.
    return {'attack_assessment': assessment, 'fusion_classification': classification}

def policy_step(coordinator, box2_row, twin_soc, sensor_soc, requested_power_kw):
    for name, value in [('twin_soc',twin_soc),('sensor_soc',sensor_soc),('power',requested_power_kw)]:
        if not isfinite(float(value)):
            raise ValueError(f'Nonfinite {name}')
    return coordinator.step(map_box2(box2_row), twin_soc, sensor_soc, requested_power_kw)
