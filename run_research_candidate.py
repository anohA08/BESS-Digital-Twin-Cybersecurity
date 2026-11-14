"""Frozen-baseline-compatible, exploratory signed increment study.

Explicitly tests all original and new Box 2 attack families on three related
profiles of ONE physical battery. No statistically guaranteed FAR claims.
"""
import argparse, json, hashlib, sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent/'src'))
import numpy as np
import pandas as pd
from bess.box1.replay import run_replay
from bess.box2.attacks import ALL_SCENARIOS, inject_attack
from bess.box2.detectors import calibrate_global, detect_threshold, detect_cusum
from bess.box2.five_evidence import calibrate_five_evidence, detect_five_evidence
from bess.box4.metrics import detection_metrics, paired_metrics
from bess.research.signed_increment import calibrate_signed_increment, detect_signed_increment
PROFILES=('1A','1.5A','2A')


def run(output='results/research_signed_increment',traces=False):
    dest=Path(output);dest.mkdir(parents=True,exist_ok=True)
    raw={p:run_replay(p) for p in PROFILES}
    summary=[];clean_out=[];thresholds=[]
    for target in PROFILES:
        src=[inject_attack(raw[p],'normal') for p in PROFILES if p!=target]
        cal=calibrate_signed_increment(src)
        th=calibrate_global(src)
        fusion=calibrate_five_evidence(src)
        thresholds.append(dict(profile=target,positive_limit_pp=cal.positive_limit_pp,
                 negative_limit_pp=cal.negative_limit_pp,guard_multiplier=cal.guard_multiplier,
                 source_profiles=cal.source_profiles,source_differences=cal.source_differences))
        normal=inject_attack(raw[target],'normal')
        def detectors(t):
            return dict(signed_increment=detect_signed_increment(t,cal),
                   global_threshold=detect_threshold(t,th),
                   soc_cusum=detect_cusum(t,src),
                   five_evidence=detect_five_evidence(t,fusion))
        clean=detectors(normal)
        for method,d in clean.items():
            met=detection_metrics(np.zeros(len(normal),dtype=bool),d.alarm.to_numpy(),normal.time_min.to_numpy(float))
            clean_out.append(dict(profile=target,method=method,clean_far=met['clean_far'],
                    clean_alarms=met['fp'],clean_samples=met['n'],
                    clean_false_alert_episodes=met['false_alert_episodes']))
        for scenario in ALL_SCENARIOS:
            attack=inject_attack(raw[target],scenario)
            ds=detectors(attack)
            truth=attack.truth_attack.to_numpy(dtype=bool)
            for method,d in ds.items():
                if scenario=='normal':
                    met=detection_metrics(truth,d.alarm.to_numpy(),attack.time_min.to_numpy(float))
                else:
                    met=paired_metrics(clean[method].alarm.to_numpy(),d.alarm.to_numpy(),truth,
                                   attack.time_min.to_numpy(float))
                summary.append(dict(profile=target,scenario=scenario,method=method,**met))
                if traces:
                    path=dest/'traces';path.mkdir(exist_ok=True)
                    d.to_csv(path/f'{target}_{scenario}_{method}.csv',index=False)
    table=pd.DataFrame(summary);clean=pd.DataFrame(clean_out);limits=pd.DataFrame(thresholds)
    table.to_csv(dest/'paired_scenario_metrics.csv',index=False)
    clean.to_csv(dest/'clean_profile_metrics.csv',index=False)
    limits.to_csv(dest/'source_only_limits.csv',index=False)
    events=table[table.scenario!='normal'].groupby(['method','scenario'],as_index=False).agg(
        injected_events=('profile','size'),new_event_hits=('new_event_hit','sum'),
        raw_event_hits=('attacked_event_hit','sum'),
        mean_paired_excess=('paired_excess_alarm_fraction','mean'))
    events.to_csv(dest/'event_summary.csv',index=False)
    statement=dict(same_physical_battery=True,related_recordings=3,
        target_profiles_used_for_calibration=False,
        target_profiles_examined_during_method_design=True,
        no_independent_battery_validation=True,no_real_attacks=True,
        reported_soc_is_surrogate_not_authenticated_bms_channel=True,
        no_false_alarm_guarantee=True,
        fixed_guard_multiplier=1.5,
        hold_samples=3,
        note='Exploratory transparent signed step monitor. NOT proposed novel detector or publishable accuracy claim.',
        candidate_file_sha256=hashlib.sha256((Path(__file__).resolve().parent/'src/bess/research/signed_increment.py').read_bytes()).hexdigest())
    (dest/'limitations_and_manifest.json').write_text(json.dumps(statement,indent=2))
    print('CLEAN PROFILE SUMMARY\n',clean.to_string(index=False))
    print('\nSOURCE CALIBRATION LIMITS\n',limits.to_string(index=False))
    print('\nEVENT SUMMARY\n',events.to_string(index=False))
    print('\nOutput:',dest)
    return dict(clean=clean,details=table,events=events,limits=limits)

if __name__=='__main__':
    ap=argparse.ArgumentParser();ap.add_argument('--out',default='results/research_signed_increment');ap.add_argument('--traces',action='store_true');a=ap.parse_args();run(a.out,a.traces)
