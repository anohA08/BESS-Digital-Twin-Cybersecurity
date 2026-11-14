"""Evaluate legacy five-channel evidence against unchanged two Box 2 baselines."""
import argparse
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parent/'src'))
import pandas as pd
from bess.box1.replay import run_replay
from bess.box2.attacks import inject_attack,ALL_SCENARIOS
from bess.box2.detectors import calibrate_global,detect_threshold,detect_cusum
from bess.box2.five_evidence import calibrate_five_evidence,detect_five_evidence
from bess.box2.evaluation import summarise,paired_excess

def run(profile='2A',out='results/box2_fusion'):
    profiles=('1A','1.5A','2A')
    if profile not in profiles:raise ValueError('Unknown profile')
    dest=Path(out);dest.mkdir(parents=True,exist_ok=True)
    source=[inject_attack(run_replay(x),'normal') for x in profiles if x!=profile]
    legacy_cal=calibrate_five_evidence(source)
    threshold_cal=calibrate_global(source)
    base=run_replay(profile)
    conditions=('normal','spoof_5','spoof_m5','spoof_ramp_p5','fixed_replay','rolling_replay','delay_3min')
    records=[];normal={}
    for s in conditions:
        telem=inject_attack(base,s)
        methods={'global_threshold':detect_threshold(telem,threshold_cal),
                 'soc_cusum':detect_cusum(telem,source),
                 'five_evidence':detect_five_evidence(telem,legacy_cal)}
        for name,det in methods.items():
            exported=pd.concat([telem.reset_index(drop=True),det.reset_index(drop=True)],axis=1)
            exported.to_csv(dest/f'{profile}_{s}_{name}.csv',index=False)
            metrics={'profile':profile,'scenario':s,'method':name,**summarise(exported)}
            if s=='normal':normal[name]=exported
            else:metrics['paired_excess_alarm_fraction']=paired_excess(normal[name],exported)
            records.append(metrics)
    data=pd.DataFrame(records)
    data.to_csv(dest/'comparison.csv',index=False)
    print(data[['scenario','method','clean_far','attack_window_alarm_fraction']].to_string(index=False))
    print('Output:',dest)
    return data

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--profile',choices=['1A','1.5A','2A'],default='2A');parser.add_argument('--out',default='results/box2_fusion')
    args=parser.parse_args();run(args.profile,args.out)
