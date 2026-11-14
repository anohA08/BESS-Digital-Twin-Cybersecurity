"""Unchanged five-channel Box 2 diagnostic and leave-one-channel-out ablation.

This script does not fit new thresholds, access attack labels in detector logic,
or alter the original fusion weights/persistence settings. Labels are accessed
only when calculating evaluation summaries.
"""
from pathlib import Path
import argparse
import sys
import numpy as np
import pandas as pd
sys.path.insert(0, str(Path(__file__).resolve().parent / 'src'))
from bess.box1.replay import run_replay
from bess.box2.attacks import inject_attack
from bess.box2.five_evidence import calibrate_five_evidence, detect_five_evidence
from bess.box2.legacy.evidence_fusion import EvidenceFusion
from bess.box2.legacy.persistence import PersistenceAssessment

CHANNELS = ('sync_score', 'physics_score', 'temporal_score', 'voltage_score', 'freshness_score')
SCENARIOS = ('normal', 'spoof_5', 'spoof_m5', 'spoof_ramp_p5', 'fixed_replay', 'rolling_replay', 'delay_3min')
PROFILES = ('1A', '1.5A', '2A')


def ablate_from_scores(detected: pd.DataFrame, omit: str | None = None) -> np.ndarray:
    """Counterfactual removal of one score after evidence was calculated.

    NOT a retrained detector. Reuses fixed weight=1, normal_max=1,
    suspicious_max=3 and persistence_limit=3.
    """
    if omit is not None and omit not in CHANNELS:
        raise ValueError(f'Unknown channel: {omit}')
    if not set(CHANNELS).issubset(detected):
        raise ValueError('Missing evidence channels')
    f = EvidenceFusion()
    p = PersistenceAssessment(persistence_limit=3)
    alarms = []
    for scores in detected.loc[:, CHANNELS].itertuples(index=False, name=None):
        s = dict(zip(CHANNELS, map(float, scores)))
        if omit is not None:
            s[omit] = 0.
        fused = f.fuse(s['sync_score'], s['physics_score'], s['temporal_score'], s['voltage_score'], s['freshness_score'])
        alarms.append(int(p.update(fused['fusion_score'])['final_classification'] == 'ABNORMAL'))
    return np.asarray(alarms, dtype=np.int8)


def summarise_trace(telemetry: pd.DataFrame, detected: pd.DataFrame, profile: str, scenario: str):
    attack = telemetry['truth_attack'].to_numpy(dtype=bool)
    inside = attack if scenario != 'normal' else np.ones(len(telemetry), dtype=bool)
    clean = ~attack
    channel_rows = []
    for c in CHANNELS:
        values = detected[c].to_numpy(dtype=float)
        channel_rows.append(dict(profile=profile, scenario=scenario, channel=c,
            attack_n=int(attack.sum()), clean_n=int(clean.sum()),
            attack_any_n=int(np.sum(values[attack] >= 1)),
            attack_strong_n=int(np.sum(values[attack] >= 2)),
            clean_any_n=int(np.sum(values[clean] >= 1)),
            clean_strong_n=int(np.sum(values[clean] >= 2)),
            attack_mean=float(values[attack].mean()) if attack.any() else np.nan,
            clean_mean=float(values[clean].mean()) if clean.any() else np.nan))
    ablation_rows = []
    ref = detected['alarm'].to_numpy(dtype=np.int8)
    for omit in (None, *CHANNELS):
        alarm = ablate_from_scores(detected, omit)
        ablation_rows.append(dict(profile=profile, scenario=scenario, omitted=omit or 'none',
            n_clean=int(clean.sum()), n_attack=int(attack.sum()),
            clean_alarm_n=int(alarm[clean].sum()), attack_alarm_n=int(alarm[attack].sum()),
            changed_alarm_samples=int(np.sum(alarm != ref)),
            new_alarms=int(np.sum((alarm==1)&(ref==0))),
            lost_alarms=int(np.sum((alarm==0)&(ref==1)))))
    return channel_rows, ablation_rows


def run(profile: str = '2A', out: str = 'results/box2_diagnostics'):
    if profile not in PROFILES: raise ValueError('Unknown profile')
    target = Path(out); target.mkdir(parents=True, exist_ok=True)
    source = [inject_attack(run_replay(p), 'normal') for p in PROFILES if p != profile]
    calibration = calibrate_five_evidence(source)
    base = run_replay(profile)
    channels, ablations, traces = [], [], []
    for scenario in SCENARIOS:
        telemetry = inject_attack(base, scenario)
        detected = detect_five_evidence(telemetry, calibration)
        _, ar = summarise_trace(telemetry, detected, profile, scenario)
        cr, _ = summarise_trace(telemetry, detected, profile, scenario)
        channels.extend(cr); ablations.extend(ar)
        exported = pd.concat([telemetry[['time_min', 'truth_attack', 'attack_window']], detected], axis=1)
        exported.insert(0, 'scenario', scenario)
        traces.append(exported)
    ch = pd.DataFrame(channels); ab = pd.DataFrame(ablations); tr = pd.concat(traces, ignore_index=True)
    ch.to_csv(target/'channel_summary.csv', index=False)
    ab.to_csv(target/'ablation_summary.csv', index=False)
    tr.to_csv(target/'evidence_traces.csv', index=False)
    print('CHANNEL STRONG COUNTS INSIDE ATTACK (>=2):')
    print(ch.pivot(index='scenario', columns='channel',values='attack_strong_n').fillna(0).astype(int).to_string())
    print('\nALARM COUNTS (unaltered vs leave-one-channel-out):')
    print(ab.pivot(index='scenario', columns='omitted', values='attack_alarm_n').fillna(0).astype(int).to_string())
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    fig, ax = plt.subplots(figsize=(10,5))
    pivot = ch.pivot(index='scenario',columns='channel',values='attack_any_n').reindex([x for x in SCENARIOS if x!='normal'])
    pivot.plot(kind='bar',ax=ax)
    ax.set_title('Evidence-channel activations in attack windows (2 A example)' if profile=='2A' else 'Evidence-channel activations in attack windows')
    ax.set_ylabel('Samples with score >=1; not confirmed detections')
    ax.set_xlabel('Scenario')
    ax.legend(title='Channel',fontsize=8)
    fig.tight_layout()
    fig.savefig(target/'channel_activation.png',dpi=220)
    fig.savefig(target/'channel_activation.svg')
    plt.close(fig)
    fig, ax = plt.subplots(figsize=(10,5))
    a = ab[ab.omitted!='none'].pivot(index='scenario',columns='omitted',values='attack_alarm_n').reindex([x for x in SCENARIOS if x!='normal'])
    a.plot(kind='bar',ax=ax)
    ax.set_title('Post-score single-channel removal (fixed fusion rules)')
    ax.set_ylabel('Alarm samples within attack')
    fig.tight_layout(); fig.savefig(target/'ablation_alarm_counts.png',dpi=220); fig.savefig(target/'ablation_alarm_counts.svg'); plt.close(fig)
    print('\nFiles saved:',target)
    return ch,ab,tr

if __name__ == '__main__':
    parser=argparse.ArgumentParser()
    parser.add_argument('--profile',choices=PROFILES,default='2A')
    parser.add_argument('--out', default='results/box2_diagnostics')
    args=parser.parse_args();run(args.profile,args.out)
