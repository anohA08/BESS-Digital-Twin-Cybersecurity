"""Frozen-policy counterfactual audit; not a plant simulation or validated controller.

Produces identical scenario inputs for:
  legacy: previously committed Box3 TrustManager/RecoveryManager.
  confirmed_only: shadow decision policy that filters unconfirmed classifications.
The shadow is a sensitivity analysis; neither method accesses attack truth.
"""
from __future__ import annotations
import argparse
import json
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent / 'src'))
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

from bess.box1.replay import run_replay
from bess.box2.attacks import inject_attack
from bess.box2.five_evidence import calibrate_five_evidence, detect_five_evidence
from bess.box3.core import Box3Coordinator, Config
from bess.box3.bridge import policy_step
from run_box3 import PROFILES, SCENARIOS


def shadow_input(row):
    """Ablation: only a confirmed Box2 alert can reduce policy trust.

    Does NOT use attack truth or future measurements. This is a deliberately
    less cautious counterfactual, not an advocated safety controller.
    """
    a = str(row['attack_assessment']).upper()
    c = str(row['classification']).upper()
    if a == 'ATTACK_DETECTED':
        return {'classification': 'ABNORMAL', 'attack_assessment': 'ATTACK_DETECTED'}
    if a not in {'NO_ATTACK_DETECTED', 'ATTACK_SUSPECTED', 'UNEXPLAINED_ANOMALY'} or c not in {'NORMAL', 'SUSPICIOUS', 'ABNORMAL'}:
        raise ValueError('Unrecognized classification in shadow input')
    return {'classification': 'NORMAL', 'attack_assessment': 'NO_ATTACK_DETECTED'}


def run_audit(profile='2A', out='results/box3_policy_audit', requested_power_kw=60.0, max_power_kw=100.0):
    if profile not in PROFILES or not np.isfinite(requested_power_kw) or not np.isfinite(max_power_kw) or max_power_kw <= 0:
        raise ValueError('Invalid profile or power settings')
    output = Path(out)
    output.mkdir(parents=True, exist_ok=True)
    cal = calibrate_five_evidence([inject_attack(run_replay(p),'normal') for p in PROFILES if p != profile])
    original = run_replay(profile)
    summary = []
    for scenario in SCENARIOS:
        telemetry = inject_attack(original, scenario)
        box2 = detect_five_evidence(telemetry, cal)
        times = telemetry.time_min.to_numpy(float)
        if len(times) < 2 or np.any(~np.isfinite(times)) or np.any(np.diff(times) <= 0):
            raise ValueError('Invalid or nonmonotonic telemetry timeline')
        dt_h = np.r_[np.diff(times), np.median(np.diff(times))] / 60.0
        for policy in ('legacy', 'confirmed_only'):
            coordinator = Box3Coordinator(Config(max_power_kw=max_power_kw))
            rows = []
            for i in range(len(telemetry)):
                row = box2.iloc[i]
                input_decision = row if policy == 'legacy' else shadow_input(row)
                decision = policy_step(
                    coordinator, input_decision,
                    float(telemetry.soc_estimated_pct.iloc[i]),
                    float(telemetry.telemetry_soc_pct.iloc[i]),
                    requested_power_kw
                )
                rows.append({
                    'sample_index': i,
                    'time_min': times[i],
                    'dt_h': dt_h[i],
                    'scenario': scenario,
                    'policy': policy,
                    'box2_alarm': int(row['alarm']),
                    'box2_assessment': str(row['attack_assessment']),
                    'box2_classification': str(row['classification']),
                    'truth_attack_evaluation_only': int(telemetry.truth_attack.iloc[i]),
                    **decision,
                })
            df = pd.DataFrame(rows)
            df['absolute_power_deviation_kw'] = (requested_power_kw - df.advisory_power_kw).abs()
            df['absolute_advisory_deviation_kwh'] = df.absolute_power_deviation_kw * df.dt_h
            df.to_csv(output / f'{profile}_{scenario}_{policy}.csv', index=False)
            attack = df.truth_attack_evaluation_only.astype(bool)
            normal = ~attack
            summary.append({
                'profile':profile, 'scenario':scenario, 'policy':policy,
                'samples':len(df),
                'strict_alarm_samples':int(df.box2_alarm.sum()),
                'safe_samples':int((df.trust_mode == 'SAFE').sum()),
                'safe_clean_samples':int(((df.trust_mode == 'SAFE') & normal).sum()),
                'safe_attack_samples':int(((df.trust_mode == 'SAFE') & attack).sum()),
                'cautious_samples':int((df.trust_mode == 'CAUTIOUS').sum()),
                'deviation_kwh_total':float(df.absolute_advisory_deviation_kwh.sum()),
                'deviation_kwh_clean':float(df.loc[normal, 'absolute_advisory_deviation_kwh'].sum()),
                'deviation_kwh_attack':float(df.loc[attack, 'absolute_advisory_deviation_kwh'].sum()),
                'changed_samples':int((df.absolute_power_deviation_kw > 1e-9).sum()),
                'alarm_in_attack':int((df.box2_alarm.astype(bool) & attack).sum()),
            })
    result = pd.DataFrame(summary)
    result.to_csv(output/'policy_comparison.csv',index=False)
    pivot = result.pivot(index='scenario', columns='policy', values='deviation_kwh_clean').reindex(SCENARIOS)
    ax=pivot.plot.bar(figsize=(10,4),rot=35)
    ax.set_ylabel('Absolute advisory deviation outside attack window (kWh)')
    ax.set_title('Frozen legacy vs confirmed-only shadow policy (not physical curtailment)')
    ax.figure.tight_layout()
    ax.figure.savefig(output/'policy_comparison.png',dpi=180)
    ax.figure.savefig(output/'policy_comparison.svg')
    plt.close(ax.figure)
    (output/'LIMITATIONS.json').write_text(json.dumps({
        'scope':'Shadow-policy sensitivity analysis on 2 A/other existing laboratory traces',
        'unchanged_box3':'Legacy policy source and parameters are not modified',
        'shadow':'Treats unconfirmed suspicious/unexplained inputs as normal for policy only; not a recommended deployment mode',
        'labels':'Attack truth used only after decisions for accounting, never for policy input',
        'power':'Requested power is illustrative and not derived from recorded battery dispatch',
        'metric':'Absolute advisory deviation is not measured energy curtailed, operating cost, SOC error avoided, or a safety guarantee',
        'sample_dependence':'One physical battery, correlated time steps',
        'no_independent_validation':True,
    },indent=2))
    print(result[['scenario','policy','strict_alarm_samples','safe_samples','safe_clean_samples','deviation_kwh_clean','deviation_kwh_attack']].to_string(index=False))
    return result


if __name__ == '__main__':
    ap=argparse.ArgumentParser()
    ap.add_argument('--profile',choices=PROFILES,default='2A')
    ap.add_argument('--out',default='results/box3_policy_audit')
    args=ap.parse_args()
    run_audit(args.profile,args.out)
