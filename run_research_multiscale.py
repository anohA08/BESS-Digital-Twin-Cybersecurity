"""Related-profile, exploratory multiscale stress test; no held-out validation."""
import argparse,sys,json
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent/'src'))
import numpy as np
import pandas as pd
from bess.box1.replay import run_replay
from bess.box2.attacks import inject_attack
from bess.box4.metrics import paired_metrics
from bess.research.signed_increment import calibrate_signed_increment, detect_signed_increment
from bess.research.multiscale_audit import calibrate_windows,detect_windows
PROFILES=('1A','1.5A','2A')
SCENARIOS=('spoof_p2','spoof_m2','spoof_5','spoof_m5','spoof_ramp_p5','rolling_replay','fixed_replay','delay_3min')

def _negative_ramp(clean):
    t=inject_attack(clean,'normal')
    ids=np.arange(40,110)
    t.loc[ids,'telemetry_soc_pct']=np.clip(t.loc[ids,'telemetry_soc_pct'].to_numpy(float)-np.linspace(0,5,len(ids)),0,100)
    t.loc[ids,'truth_attack']=1
    return t

def _benign_reset(clean):
    t=inject_attack(clean,'normal')
    # Legitimate BMS display adjustment: observationally identical to FDIA.
    t.loc[40:109,'telemetry_soc_pct']=np.clip(t.loc[40:109,'telemetry_soc_pct'].to_numpy(float)+2,0,100)
    return t

def run(output='results/research_multiscale'):
    dest=Path(output);dest.mkdir(parents=True,exist_ok=True)
    replays={p:run_replay(p) for p in PROFILES}
    records=[];cal_records=[]
    for profile in PROFILES:
        clean=inject_attack(replays[profile],'normal')
        source=[inject_attack(replays[p],'normal') for p in PROFILES if p!=profile]
        c=calibrate_windows(source)
        si=calibrate_signed_increment(source)
        cal_records.extend(dict(profile=profile,window=w,positive_limit_pp=a,negative_limit_pp=b,
                                source_profiles=c.source_profiles,guard=c.guard)
                           for w,a,b in zip(c.windows,c.positive_limits,c.negative_limits))
        methods={'multiscale':lambda f:detect_windows(f,c),
                 'signed_increment':lambda f:detect_signed_increment(f,si)}
        for method,fn in methods.items():
            baseline=fn(clean).alarm.to_numpy(dtype=bool)
            records.append(dict(profile=profile,method=method,scenario='normal',
                                new_event_hit=False,raw_event_hit=False,clean_alarm_samples=int(baseline.sum()),
                                attacked_alarm_samples=0,paired_excess_fraction=0.,first_delay_min=None))
            for scenario in SCENARIOS+('negative_ramp_5','benign_report_reset_p2'):
                if scenario=='negative_ramp_5':attack=_negative_ramp(replays[profile])
                elif scenario=='benign_report_reset_p2':attack=_benign_reset(replays[profile])
                else:attack=inject_attack(replays[profile],scenario)
                attack_alarm=fn(attack).alarm.to_numpy(dtype=bool)
                truth=np.zeros(len(attack),dtype=bool)
                truth[40:110]=True  # Evaluation only, never passed to methods.
                metrics=paired_metrics(baseline,attack_alarm,truth,attack.time_min.to_numpy(float))
                records.append(dict(profile=profile,method=method,scenario=scenario,
                    new_event_hit=metrics['new_event_hit'],raw_event_hit=metrics['attacked_event_hit'],
                    clean_alarm_samples=int(baseline.sum()),attacked_alarm_samples=int(attack_alarm.sum()),
                    paired_excess_fraction=metrics['paired_excess_alarm_fraction'],
                    first_delay_min=metrics['first_detection_delay_min']))
    df=pd.DataFrame(records);cal=pd.DataFrame(cal_records)
    df.to_csv(dest/'scenario_comparison.csv',index=False)
    cal.to_csv(dest/'window_calibration.csv',index=False)
    summary=df[df.scenario!='normal'].groupby(['method','scenario'],as_index=False).agg(
        events=('profile','size'),new_hits=('new_event_hit','sum'),
        mean_excess=('paired_excess_fraction','mean'))
    summary.to_csv(dest/'event_summary.csv',index=False)
    (dest/'limitations.json').write_text(json.dumps(dict(
        single_physical_battery=True,related_profiles=3,method_designed_after_reviewing_targets=True,
        no_real_soc_telemetry=True,lab_soc_used_as_surrogate=True,synthetic_attacks_only=True,
        no_independent_validation=True,source_max_times_guard_not_far_guarantee=True,
        benign_reset_ambiguity=True,gradual_attack_may_be_unidentifiable_from_model_drift=True),indent=2))
    print('CLEAN SAMPLE ALARMS\n',df[df.scenario=='normal'][['profile','method','clean_alarm_samples']].to_string(index=False))
    print('\nEVENT RESULTS\n',summary.to_string(index=False))
    print('\nOutput:',dest)
    return dict(details=df,calibration=cal,summary=summary)

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--out',default='results/research_multiscale');a=p.parse_args();run(a.out)
