"""Replay Box2 five-evidence events into legacy Box3 advisory policy.

Research-only replay. Power requests and kWh accounting are illustrative, not
physical validation. This runner does NOT close the loop through a battery plant.
"""
from __future__ import annotations
import argparse, json, sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent/'src'))
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from bess.box1.replay import run_replay
from bess.box2.attacks import inject_attack, AttackWindow
from bess.box2.five_evidence import calibrate_five_evidence, detect_five_evidence
from bess.box3.core import Box3Coordinator, Config
from bess.box3.bridge import policy_step

PROFILES=('1A','1.5A','2A')
SCENARIOS=('normal','spoof_5','spoof_m5','spoof_ramp_p5','fixed_replay','rolling_replay','delay_3min')

def run(profile='2A', out='results/box3', requested_power_kw=60., max_power_kw=100.):
    if profile not in PROFILES or requested_power_kw < 0 or max_power_kw <= 0:
        raise ValueError('Invalid run options')
    dest=Path(out);dest.mkdir(parents=True,exist_ok=True)
    source=[inject_attack(run_replay(x),'normal') for x in PROFILES if x!=profile]
    cal=calibrate_five_evidence(source)
    original=run_replay(profile)
    summaries=[]
    for scenario in SCENARIOS:
        telem=inject_attack(original,scenario)
        box2=detect_five_evidence(telem,cal)
        coord=Box3Coordinator(Config(max_power_kw=max_power_kw))
        rows=[]
        times=telem.time_min.to_numpy(float)
        # Sample represents control action over the next recorded interval.
        dt=np.r_[np.diff(times),np.median(np.diff(times))]/60.
        for i in range(len(telem)):
            decision=policy_step(coord,box2.iloc[i],
                float(telem.soc_estimated_pct.iloc[i]),float(telem.telemetry_soc_pct.iloc[i]),
                requested_power_kw)
            rows.append({'time_min':times[i], 'truth_attack_evaluation_only':int(telem.truth_attack.iloc[i]),
                'attack_assessment':str(box2.attack_assessment.iloc[i]),
                'box2_abnormal':int(box2.alarm.iloc[i]), 'requested_power_kw':requested_power_kw,
                'dt_h':float(dt[i]), **decision})
        df=pd.DataFrame(rows)
        df['absolute_power_change_kw']=(df.requested_power_kw-df.advisory_power_kw).abs()
        df['absolute_dispatch_deviation_kwh']=df.absolute_power_change_kw*df.dt_h
        df.to_csv(dest/f'{profile}_{scenario}_advisory.csv',index=False)
        summaries.append({'profile':profile,'scenario':scenario,
            'clean_alarm_samples':int(((df.box2_abnormal==1)&(df.truth_attack_evaluation_only==0)).sum()),
            'attack_alarm_samples':int(((df.box2_abnormal==1)&(df.truth_attack_evaluation_only==1)).sum()),
            'safe_samples':int((df.trust_mode=='SAFE').sum()),
            'safe_outside_attack_samples':int(((df.trust_mode=='SAFE')&(df.truth_attack_evaluation_only==0)).sum()),
            'advisory_changed_samples':int((df.absolute_power_change_kw>1e-9).sum()),
            'absolute_dispatch_deviation_kwh':float(df.absolute_dispatch_deviation_kwh.sum()),
            'absolute_dispatch_deviation_outside_attack_kwh':float(df.loc[df.truth_attack_evaluation_only==0,'absolute_dispatch_deviation_kwh'].sum())})
    summary=pd.DataFrame(summaries)
    summary.to_csv(dest/'box3_scenario_summary.csv',index=False)
    fig,ax=plt.subplots(figsize=(10,4))
    ax.bar(summary.scenario,summary.absolute_dispatch_deviation_kwh)
    ax.set_ylabel('Absolute advisory power deviation (kWh)')
    ax.set_title('Illustrative consequence of unchanged Box 2 decisions')
    ax.tick_params(axis='x',rotation=35)
    fig.tight_layout();fig.savefig(dest/'advisory_deviation.png',dpi=180);plt.close(fig)
    (dest/'limitations.json').write_text(json.dumps({
       'measured_data':'Recorded voltage/current; recorded SOC is a surrogate report',
       'power':'Illustrative requested power; no plant state/physics feedback',
       'trust':'Heuristic policy score, not calibrated probability',
       'metrics':'Absolute advisory deviation is NOT grid energy curtailed or avoided physical damage',
       'independence':'Same lab battery system, previously explored current profiles'},indent=2))
    print(summary.to_string(index=False));print('Output:',dest)
    return summary

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--profile',choices=PROFILES,default='2A')
    p.add_argument('--out',default='results/box3');args=p.parse_args()
    run(args.profile,args.out)
