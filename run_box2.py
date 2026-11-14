"""Reproducible exploratory Box 2 attack-family smoke evaluation.

Runs global threshold and SOC-only CUSUM; does NOT run legacy five-channel fusion.
Source calibration uses other current profiles (same battery; not independent cells).
"""
import argparse
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parent/'src'))
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from bess.box1.replay import run_replay
from bess.box2.attacks import inject_attack, ALL_SCENARIOS
from bess.box2.detectors import calibrate_global,detect_threshold,detect_cusum
from bess.box2.evaluation import summarise,paired_excess

def run(profile='2A',scenarios=('normal','spoof_5','fixed_replay','rolling_replay','delay_3min'),out='results/box2'):
    if profile not in ('1A','1.5A','2A'): raise ValueError('Unknown profile')
    root=Path(out);root.mkdir(parents=True,exist_ok=True)
    source=[inject_attack(run_replay(p),'normal') for p in ('1A','1.5A','2A') if p!=profile]
    base=run_replay(profile)
    cfg=calibrate_global(source)
    metrics=[]; by_method={}
    for scenario in scenarios:
        telemetry=inject_attack(base,scenario)
        results={'threshold':detect_threshold(telemetry,cfg),'cusum_soc':detect_cusum(telemetry,source)}
        for method, det in results.items():
            export=pd.concat([telemetry.reset_index(drop=True),det],axis=1)
            export.to_csv(root/f'{profile}_{scenario}_{method}.csv',index=False)
            row={'profile':profile,'scenario':scenario,'method':method,**summarise(export)}
            if scenario!='normal':
                normal=by_method.get(method)
                if normal is not None:
                    row['paired_excess_alarm_fraction']=paired_excess(normal,export)
            metrics.append(row)
            if scenario=='normal':by_method[method]=export
    table=pd.DataFrame(metrics);table.to_csv(root/'scenario_summary.csv',index=False)
    # Critical: figures explicitly distinguish source-only calibration and exploratory runs.
    fig,ax=plt.subplots(figsize=(10,4))
    for scenario in scenarios:
        rows=table[table.scenario.eq(scenario)]
        for _,r in rows.iterrows():
            ax.bar(f'{scenario}\n{r["method"]}',r['attack_window_alarm_fraction'] if scenario!='normal' else r['clean_far'])
    ax.tick_params(axis='x',labelrotation=55);ax.set_ylim(0,1.05)
    ax.set_ylabel('Alarm fraction (clean FAR or attack-window alarm fraction)')
    ax.set_title('Exploratory Box 2, not calibrated at matched FAR')
    fig.tight_layout();fig.savefig(root/'scenario_alarm_fraction.png',dpi=180);plt.close(fig)
    print(table[['scenario','method','clean_far','attack_window_alarm_fraction']].to_string(index=False))
    print('Outputs:',root)
    return table

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--profile',choices=['1A','1.5A','2A'],default='2A')
    p.add_argument('--scenarios',nargs='+',choices=ALL_SCENARIOS,default=['normal','spoof_5','fixed_replay','rolling_replay','delay_3min'])
    p.add_argument('--out',default='results/box2')
    a=p.parse_args();run(a.profile,a.scenarios,a.out)
