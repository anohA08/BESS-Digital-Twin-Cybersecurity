"""Frozen Box 1–3, all profiles and attacks; no target-based retuning or oracle policy.

All lab profiles are from one battery system. This is retrospective evaluation,
not independently validated cybersecurity or a closed-loop BESS plant.
"""
from __future__ import annotations
import argparse, json, hashlib, sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent/'src'))
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from bess.box1.replay import run_replay
from bess.box2.attacks import ALL_SCENARIOS, inject_attack
from bess.box2.detectors import calibrate_global,detect_threshold,detect_cusum
from bess.box2.five_evidence import calibrate_five_evidence,detect_five_evidence
from bess.box3.core import Box3Coordinator, Config
from bess.box3.bridge import policy_step
from bess.box4.metrics import detection_metrics,paired_metrics,advisory_metrics
from run_box3_policy_audit import shadow_input

PROFILES=('1A','1.5A','2A')
METHODS=('global_threshold','soc_cusum','five_evidence')
POWER_KW=60.0
MAX_POWER_KW=100.0

def _sha256(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()

def _methods(telemetry, threshold_cal, source, fusion_cal):
    return {'global_threshold':detect_threshold(telemetry,threshold_cal),
            'soc_cusum':detect_cusum(telemetry,source),
            'five_evidence':detect_five_evidence(telemetry,fusion_cal)}

def _policy(telemetry, detection, variant, power_kw=POWER_KW):
    coord=Box3Coordinator(Config(max_power_kw=MAX_POWER_KW))
    times=telemetry.time_min.to_numpy(float)
    if len(times)<2 or not (np.diff(times)>0).all():raise ValueError('Invalid timeline')
    dt=np.r_[np.diff(times),np.median(np.diff(times))]/60.0
    rec=[]
    for i in range(len(telemetry)):
        row=detection.iloc[i]
        decision=row if variant=='legacy' else shadow_input(row)
        response=policy_step(coord,decision,float(telemetry.soc_estimated_pct.iloc[i]),
            float(telemetry.telemetry_soc_pct.iloc[i]),power_kw)
        rec.append({'profile_time_min':times[i], 'dt_h':dt[i],
            'truth_attack_evaluation_only':int(telemetry.truth_attack.iloc[i]), **response})
    return pd.DataFrame(rec)

def run(out='results/box4', include_traces=False):
    dest=Path(out);dest.mkdir(parents=True,exist_ok=True)
    details=dest/'traces'
    if include_traces:details.mkdir(exist_ok=True)
    source_profiles={p:run_replay(p) for p in PROFILES}
    records=[]; policies=[]; clean_rows=[]
    for profile in PROFILES:
        source=[inject_attack(source_profiles[p],'normal') for p in PROFILES if p!=profile]
        th=calibrate_global(source);fusion=calibrate_five_evidence(source)
        base=source_profiles[profile]
        normal=inject_attack(base,'normal')
        clean_methods=_methods(normal,th,source,fusion)
        clean_times=normal.time_min.to_numpy(float)
        for method in METHODS:
            alarms=clean_methods[method].alarm.to_numpy()
            dm=detection_metrics(np.zeros(len(alarms),dtype=bool),alarms,clean_times)
            clean_rows.append({'profile':profile,'method':method,'source_profiles':len(source),
                'clean_alarms':dm['fp'],'clean_samples':dm['n'],
                'clean_far':dm['clean_far'], 'clean_false_alert_episodes':dm['false_alert_episodes'],
                'passes_5pct_clean_far':bool(dm['clean_far']<=.05)})
        for scenario in ALL_SCENARIOS:
            telemetry=inject_attack(base,scenario)
            d=_methods(telemetry,th,source,fusion)
            mask=telemetry.truth_attack.to_numpy(bool)
            times=telemetry.time_min.to_numpy(float)
            for method in METHODS:
                det=d[method]
                if scenario=='normal':
                    met=detection_metrics(mask,det.alarm.to_numpy(),times)
                else:
                    met=paired_metrics(clean_methods[method].alarm.to_numpy(),
                                      det.alarm.to_numpy(),mask,times)
                records.append({'profile':profile,'scenario':scenario,'method':method,
                    'attack_family': ('clean' if scenario=='normal' else 'spoofing' if scenario.startswith('spoof_') else 'replay' if 'replay' in scenario else 'delay'),
                    **met})
                if include_traces:
                    trace=pd.concat([telemetry[['time_min','truth_attack','attack_window']].reset_index(drop=True),
                        det.reset_index(drop=True)],axis=1)
                    trace.to_csv(details/f'{profile}_{scenario}_{method}.csv',index=False)
            for policy in ('legacy','confirmed_only'):
                pf=_policy(telemetry,d['five_evidence'],policy)
                metrics=advisory_metrics(pf,POWER_KW)
                policies.append({'profile':profile,'scenario':scenario,'policy':policy,**metrics})
                if include_traces:pf.to_csv(details/f'{profile}_{scenario}_{policy}_policy.csv',index=False)
    detect=pd.DataFrame(records);policy=pd.DataFrame(policies);clean=pd.DataFrame(clean_rows)
    detect.to_csv(dest/'detection_per_scenario.csv',index=False)
    clean.to_csv(dest/'clean_profile_gate.csv',index=False)
    policy.to_csv(dest/'policy_per_scenario.csv',index=False)
    # Sign-aware paired observations; no post-hoc tuning or aggregated certainty claim.
    signed=detect[detect.scenario.isin(['spoof_m5','spoof_5','spoof_m2','spoof_p2'])].pivot_table(
        index=['profile','method'],columns='scenario',values='paired_excess_alarm_fraction',aggfunc='first')
    signed['negative_minus_positive_5pp']=signed['spoof_m5']-signed['spoof_5']
    signed['negative_minus_positive_2pp']=signed['spoof_m2']-signed['spoof_p2']
    signed.reset_index().to_csv(dest/'signed_asymmetry.csv',index=False)
    alert=detect[detect.scenario!='normal'].groupby(['method','scenario'],as_index=False).agg(
        scenarios=('profile','size'),event_hits=('attacked_event_hit','sum'),new_event_hits=('new_event_hit','sum'),
        mean_paired_excess=('paired_excess_alarm_fraction','mean'))
    alert.to_csv(dest/'event_detection_summary.csv',index=False)
    # These are transparent post-hoc engineering audit gates, not preregistered claims.
    gates=[]
    for method in METHODS:
        cm=clean[clean.method==method]
        em=alert[alert.method==method]
        # Per-profile clean false-alarm gate, not pooled values.
        spoof=em[em.scenario.str.startswith('spoof_')]
        gates.append({'method':method,'clean_far_5pct_all_three_profiles':bool(cm.passes_5pct_clean_far.all()),
            'soc_spoof_new_event_hits':int(spoof.new_event_hits.sum()),
            'soc_spoof_event_injections':int(spoof.scenarios.sum()),
            'no_independent_cells':True,'no_closed_loop_safety_evaluation':True,
            'publication_validation_ready':False})
    pd.DataFrame(gates).to_csv(dest/'research_readiness_gates.csv',index=False)

    # No statistical inference from 3 correlated profiles.
    fig,ax=plt.subplots(figsize=(10,4));pivot=clean.pivot(index='profile',columns='method',values='clean_far')
    pivot.plot.bar(ax=ax);ax.axhline(.05,ls='--',c='black',label='5% descriptive gate')
    ax.set_ylabel('Achieved clean sample alarm fraction');ax.set_title('Held-out profile results; thresholds calibrated on other currents')
    ax.legend(fontsize=8);fig.tight_layout();fig.savefig(dest/'clean_far_by_profile.png',dpi=160);plt.close(fig)
    fig,ax=plt.subplots(figsize=(12,5));asym=signed.reset_index()
    asym.pivot(index='profile',columns='method',values='negative_minus_positive_5pp').plot.bar(ax=ax)
    ax.axhline(0,c='black',lw=1);ax.set_ylabel('−5 pp excess alarm fraction minus +5 pp')
    ax.set_title('Directional asymmetry; paired semi-synthetic SOC attacks')
    fig.tight_layout();fig.savefig(dest/'signed_attack_asymmetry.png',dpi=160);plt.close(fig)
    manifest={
        'protocol':'Frozen Box1–3, leave-one-current-profile-out threshold calibration',
        'source_profile_names':list(PROFILES),'same_battery_system':True,
        'dataset_not_independent_cells':True,
        'model_parameters_previously_derived_using_laboratory_repository':True,
        'not_independent_physics_validation':True,
        'attack_truth_for_evaluation_only':True,
        'soc_reference_is_unverified_bms_report_surrogate':True,
        'replay_timestamps_refreshed':True,
        'delay_is_packet_age_manipulation_not_full_network_model':True,
        'baseline_not_matched_achieved_far':True,
        'five_percent_gate_is_descriptive_not_statistical_guarantee':True,
        'no_physical_closed_loop_or_safety_verification':True,
        'advisory_power_kw':POWER_KW,
        'test_coverage':'No independent cells, unseen operating modes, hardware-in-loop or natural network attacks',
        'file_sha256':{name:_sha256(Path(__file__).resolve().parent/name) for name in [
           'src/bess/box2/attacks.py','src/bess/box2/detectors.py','src/bess/box2/five_evidence.py',
           'src/bess/box3/core.py','src/bess/box3/bridge.py']}
        }
    (dest/'evaluation_manifest.json').write_text(json.dumps(manifest,indent=2))
    print('\nCLEAN PROFILE GATE (5%, descriptive only):\n',clean.to_string(index=False))
    print('\nATTACK EVENT SUMMARY (each row: three profile-specific injections):\n',alert.to_string(index=False))
    print('\nOutput:',dest)
    return {'clean':clean,'detection':detect,'policies':policy,'events':alert,'signed':signed}

if __name__=='__main__':
    ap=argparse.ArgumentParser()
    ap.add_argument('--out',default='results/box4');ap.add_argument('--traces',action='store_true')
    a=ap.parse_args();run(a.out,a.traces)
