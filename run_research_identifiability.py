"""Run state/measurement identifiability gate on three related lab profiles."""
import argparse,sys,json
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent/'src'))
import pandas as pd
from bess.box1.replay import run_replay
from bess.research.identifiability_gate import audit_profile

def run(out='results/research_identifiability'):
    p=Path(out);p.mkdir(parents=True,exist_ok=True)
    report=pd.concat([audit_profile(k,run_replay(k)) for k in ('1A','1.5A','2A')],ignore_index=True)
    report.to_csv(p/'observability_counterexamples.csv',index=False)
    checks=dict(
        recorded_profiles=3,independent_batteries=1,
        tested_injected_scenarios=['gradual_positive_5pp','gradual_negative_5pp','abrupt_positive_2pp'],
        hypotheses_have_identical_observations=bool(report.attack_and_benign_observationally_identical.all()),
        physical_measurements_unchanged_by_soc_only_attack=bool(report.physical_channels_invariant_under_soc_attack.all()),
        note='Identical observations imply identical outputs for any deterministic observation-only detector; randomness cannot create distinguishing evidence.',
        oracle_anchor_is_not_deployable=True,anchor_uncertainty_bounds_hypothetical=True,
        positive_attack_proof=False,attack_intent_identifiable=False,
        action='Require authenticated reporting events or independent measurements to distinguish malicious FDIA from benign identical resets; do not claim gradual FDIA detection.'
    )
    (p/'gate.json').write_text(json.dumps(checks,indent=2),encoding='utf-8')
    print('Measurement counterexample valid:',checks['hypotheses_have_identical_observations'])
    print('SOC-only physical channel invariance:',checks['physical_measurements_unchanged_by_soc_only_attack'])
    print('\nOracle reference inconsistency (not an attack-intent detector):')
    print(report[['profile','scenario','assumed_anchor_error_bound_pp','attack_oracle_anchor_flagged_samples']].to_string(index=False))
    print('Output:',p)
    return report
if __name__=='__main__':
    a=argparse.ArgumentParser();a.add_argument('--out',default='results/research_identifiability');v=a.parse_args();run(v.out)
