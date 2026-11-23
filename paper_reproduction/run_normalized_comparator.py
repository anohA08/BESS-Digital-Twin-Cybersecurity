"""Supplementary comparator: source-only normalized-time binned thresholds.
The source-derived normalization uses the median recorded session end from OTHER
runs of the same recorded current. It does not access held-out run endpoints.
All 12 laboratory runs are from a single cell. No claim of grid-scale validation.
"""
from pathlib import Path
from math import comb
import numpy as np
import pandas as pd
import run_single_protocol as base

OUT = Path(__file__).resolve().parent / 'normalized_comparison'

def exact_sign_p(better, worse):
    n=better+worse
    return min(1., 2*sum(comb(n,k) for k in range(min(better,worse)+1))/2**n) if n else 1.

def assess(source, target, attack):
    # Source-only current-matched session duration; no held-out future observations.
    curr=float(target.current_group.iloc[0]); dur_by_run=source[source.current_group==curr].groupby('run').time.max()
    if dur_by_run.empty: raise ValueError('No source current-matched runs')
    horizon=float(dur_by_run.median())
    if horizon<=0: raise ValueError('Invalid horizon')
    s=np.minimum(9, np.floor(np.maximum(0,source.time.to_numpy())/horizon*10).astype(int))
    t=np.minimum(9, np.floor(np.maximum(0,target.time.to_numpy())/horizon*10).astype(int))
    raw=target.soc_discrepancy.to_numpy(); src=source.soc_discrepancy.to_numpy()
    overall=base.threshold(src)
    lookup={int(k):base.threshold(src[s==k]) for k in np.unique(s) if (s==k).sum()>=30}
    lim=np.array([lookup.get(int(k),overall) for k in t]);ix=target.i.to_numpy();w=(ix>=base.START)&(ix<base.STOP)
    delta=np.zeros(len(raw))
    if attack.startswith('step_'):delta[w]=5 if attack.endswith('p5') else -5
    if attack.startswith('ramp_'):delta[w]=(5 if attack.endswith('p5') else -5)*(ix[w]-base.START)/(base.STOP-base.START-1)
    clean=base.alarm(np.abs(raw)>lim);att=base.alarm(np.abs(raw+delta)>lim)
    j=np.where(w&att&~clean)[0]
    return dict(clean_far=clean.mean(),clean_alarms=clean.sum(),new_event=bool(len(j)),delay=float(ix[j[0]]-base.START) if len(j) else np.nan,offset_first_alarm_pp=float(delta[j[0]]) if len(j) else np.nan,reference_duration_min=horizon,source_supported_fraction=np.mean([k in lookup for k in t]),n_samples=len(raw))

def main(input_file=base.DEFAULT):
    OUT.mkdir(exist_ok=True)
    d=pd.read_csv(input_file);d=d[d.i>30].copy()
    rows=[]
    for run in sorted(d.run.unique()):
        src=d[d.run!=run];tar=d[d.run==run].sort_values('i')
        for attack in ['normal','step_p5','step_m5','ramp_p5','ramp_m5']:
            r=assess(src,tar,attack)
            rows.append(dict(run=run, current=float(tar.current_group.iloc[0]),method='normalized_time_binned',attack=attack,**r))
    norm=pd.DataFrame(rows)
    old_path=base.OUT/'per_session_results.csv'
    if not old_path.is_file():
        raise FileNotFoundError('Run run_single_protocol.py before normalized comparison')
    old=pd.read_csv(old_path)
    old=old[old.method.isin(['global','soc_binned','time_binned','basic_cusum'])].copy()
    old=old.rename(columns={'first_new_alarm_delay_samples':'delay'})
    old['offset_first_alarm_pp']=np.where(old.attack.str.startswith('step_'),np.where(old.attack.str.endswith('p5'),5,-5),np.where(old.attack.str.endswith('ramp_'),np.where(old.attack.str.endswith('p5'),5,-5)*old.delay/49,np.nan))
    union=pd.concat([old,norm],ignore_index=True)
    union.to_csv(OUT/'all_methods_per_session.csv',index=False)
    summary=union.groupby(['method','attack'],as_index=False).agg(hits=('new_event','sum'),mean_clean_far=('clean_far','mean'),median_delay=('delay','median'),n=('run','size'))
    summary.to_csv(OUT/'method_event_summary.csv',index=False)
    clean=union[union.attack=='normal'].groupby('method',as_index=False).agg(mean_far=('clean_far','mean'),passing_sessions=('clean_far',lambda s:int((s<=.05).sum())),max_far=('clean_far','max'))
    clean.to_csv(OUT/'clean_gate_summary.csv',index=False)
    pairs=[]
    for attack in ['step_p5','step_m5','ramp_p5','ramp_m5']:
        a=union[(union.method=='soc_binned')&(union.attack==attack)].set_index('run').new_event.astype(bool)
        b=union[(union.method=='normalized_time_binned')&(union.attack==attack)].set_index('run').new_event.astype(bool)
        wins=int((a&~b).sum());losses=int((~a&b).sum())
        pairs.append(dict(attack=attack,soc_hits=int(a.sum()),normalized_time_hits=int(b.sum()),soc_only=wins,time_only=losses,both=int((a&b).sum()),neither=int((~a&~b).sum()),paired_exact_two_sided_p=exact_sign_p(wins,losses)))
    pd.DataFrame(pairs).to_csv(OUT/'paired_exact_hits.csv',index=False)
    with open(OUT/'PROTOCOL_NOTES.md','w') as f:
        f.write('## Comparator scope\n\nSource-only duration-normalized time bins: the target current is known from the discharge schedule, and its scaling horizon is the median *source* maximum time from same-current sessions. This makes the bin assignment causal with respect to target measurements. The archived residual export has **identical recorded 151-minute extents for all 12 sessions**, so the often-cited different-discharge-duration argument does not describe this particular truncated dataset. The source-normalized baseline has ten fractional-time bins; the previous absolute baseline uses 10-minute bins, so both bin alignment and bin resolution change. All runs are same-cell, and no grid-scale physical validation is implied.\n')
    print('\nCLEAN GATE\n',clean.to_string(index=False))
    print('\nPAIRED EVENT TEST\n',pd.DataFrame(pairs).to_string(index=False))
    print('\nSaved:',OUT)
if __name__=='__main__':main()
