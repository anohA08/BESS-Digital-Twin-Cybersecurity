"""Reproducible single-cell 12-session audit. No attack labels enter calibration.
Note: same-cell sessions; bootstrap is session-level descriptive, not cell population CI.
"""
from pathlib import Path
import argparse, numpy as np, pandas as pd
import matplotlib; matplotlib.use('Agg')
import matplotlib.pyplot as plt
ROOT=Path(__file__).resolve().parent
DEFAULT=ROOT/'data'/'raw_session_replayed_residuals.csv'
OUT=ROOT/'results'; OUT.mkdir(exist_ok=True)
ALPHA=.05; START=40; STOP=90; PERSIST=3

def alarm(z):
    o=np.zeros(len(z),bool); n=0
    for i,a in enumerate(z):
        n=n+1 if a else 0;o[i]=n>=PERSIST
    return o

def threshold(v): return float(np.quantile(np.abs(v),1-ALPHA,method='higher'))

def make_bin(df,method):
    if method=='soc_binned': return np.floor(np.clip(df.online_soc.to_numpy(),0,99.999)/10).astype(int)
    if method=='time_binned':
        # Fixed *absolute* 10-minute bins (time is recorded in minutes): reproducible schedule,
        # no target-dependent normalization or future endpoint leakage.
        return np.floor(df.time.to_numpy()/10).astype(int)
    return np.zeros(len(df),int)

def eval_method(source,target,method,attack):
    src=source.copy(); tar=target.copy(); sb=make_bin(src,method);tb=make_bin(tar,method)
    srcval=src.soc_discrepancy.to_numpy(); raw=tar.soc_discrepancy.to_numpy()
    lim=threshold(srcval)
    lookup={int(k):threshold(srcval[sb==k]) for k in np.unique(sb) if (sb==k).sum()>=30}
    tau=np.array([lookup.get(int(k),lim) for k in tb]) if method!='global' else np.full(len(tar),lim)
    clean=alarm(np.abs(raw)>tau)
    delta=np.zeros(len(raw)); ix=tar.i.to_numpy(); w=(ix>=START)&(ix<STOP)
    if attack in ('step_p5','step_m5'):
        delta[w]=5 if attack=='step_p5' else -5
    elif attack in ('ramp_p5','ramp_m5'):
        delta[w]=(5 if attack=='ramp_p5' else -5)*((ix[w]-START)/(STOP-START-1))
    elif attack!='normal':raise ValueError(attack)
    attacked=alarm(np.abs(raw+delta)>tau)
    idx=np.where(w & attacked & ~clean)[0]
    first=int(ix[idx[0]]-START) if len(idx) else np.nan
    return {'clean_far':float(clean.mean()),'n_clean':len(clean),'clean_alarms':int(clean.sum()),'excess':float((attacked[w].astype(int)-clean[w].astype(int)).mean()),'new_event':bool(len(idx)), 'first_new_alarm_delay_samples':first,'attack_flags':int(attacked[w].sum()),'n_attack':int(w.sum()),'source_supported_fraction':float(np.mean([k in lookup for k in tb])) if method!='global' else 1.0},clean,attacked

def eval_cusum(source,target,attack):
    # Transparent basic two-sided residual CUSUM (not a reproduction of published EKF+CUSUM).
    # Baseline uses zero residual reference, source-derived k and h, held-out target untouched.
    sourcearr=source.soc_discrepancy.to_numpy()
    k=max(float(np.median(np.abs(sourcearr)))*.5,1e-9)
    def trace(vals):
        p=m=0.;arr=[]
        for x in vals:
            p=max(0,p+x-k);m=max(0,m-x-k);arr.append(max(p,m))
        return np.array(arr)
    # Source segment reset each session. threshold quantile of source CUSUM trajectories.
    allscore=np.concatenate([trace(g.soc_discrepancy.to_numpy()) for _,g in source.groupby('run')])
    h=threshold(allscore)
    raw=target.soc_discrepancy.to_numpy();ix=target.i.to_numpy();w=(ix>=START)&(ix<STOP)
    delta=np.zeros(len(raw))
    if attack in ('step_p5','step_m5'):delta[w]=5 if attack=='step_p5' else -5
    if attack in ('ramp_p5','ramp_m5'):delta[w]=(5 if attack=='ramp_p5' else -5)*(ix[w]-START)/(STOP-START-1)
    clean=alarm(trace(raw)>h);att=alarm(trace(raw+delta)>h)
    hits=np.where(w&att&~clean)[0]
    return {'clean_far':float(clean.mean()),'n_clean':len(clean),'clean_alarms':int(clean.sum()),'excess':float((att[w].astype(int)-clean[w].astype(int)).mean()),'new_event':bool(len(hits)),'first_new_alarm_delay_samples':float(ix[hits[0]]-START) if len(hits) else np.nan,'attack_flags':int(att[w].sum()),'n_attack':int(w.sum()),'source_supported_fraction':1.0},clean,att

def bootstrap(g,col,seed=20261114,B=5000):
    vals=g[col].to_numpy(dtype=float);vals=vals[np.isfinite(vals)]
    if len(vals)==0:return np.nan,np.nan
    rng=np.random.default_rng(seed);draw=rng.choice(vals,size=(B,len(vals)),replace=True).mean(axis=1)
    return np.quantile(draw,[.025,.975])

def main(input_file=DEFAULT):
    d=pd.read_csv(input_file); d=d[d.i>30].copy()
    assert d.run.nunique()==12
    methods=['global','soc_binned','time_binned','basic_cusum']
    attacks=['normal','step_p5','step_m5','ramp_p5','ramp_m5']
    rows=[]
    for run in sorted(d.run.unique()):
        src=d[d.run!=run];tar=d[d.run==run].sort_values('i')
        for method in methods:
            for atk in attacks:
                r,_,_=eval_cusum(src,tar,atk) if method=='basic_cusum' else eval_method(src,tar,method,atk)
                rows.append(dict(run=run,current=float(tar.current_group.iloc[0]),method=method,attack=atk,**r))
    res=pd.DataFrame(rows);res.to_csv(OUT/'per_session_results.csv',index=False)
    clean=res[res.attack=='normal'];summary=[]
    for method,g in clean.groupby('method'):
        lo,hi=bootstrap(g,'clean_far')
        summary.append(dict(method=method,mean_far=g.clean_far.mean(),ci_lo=lo,ci_hi=hi,median_far=g.clean_far.median(),sessions_passing_5pct=int((g.clean_far<=.05).sum()),n_sessions=len(g),max_far=g.clean_far.max(),note='Session resampling from one cell: descriptive, not cell generalization'))
    pd.DataFrame(summary).to_csv(OUT/'far_bootstrap.csv',index=False)
    paired=[]
    for method in ['soc_binned','time_binned','basic_cusum']:
        a=clean[clean.method=='global'].set_index('run').clean_far
        b=clean[clean.method==method].set_index('run').clean_far
        for run in a.index:paired.append(dict(run=run,comparison=method+' minus global',difference=float(b[run]-a[run])))
    pd.DataFrame(paired).to_csv(OUT/'paired_clean_differences.csv',index=False)
    event=[]
    for (method,atk),g in res[res.attack!='normal'].groupby(['method','attack']):
        z=g.first_new_alarm_delay_samples.dropna()
        event.append(dict(method=method,attack=atk,new_event_hits=int(g.new_event.sum()),n_sessions=len(g),mean_excess=g.excess.mean(),median_delay_samples=float(z.median()) if len(z) else np.nan,mean_delay_samples=float(z.mean()) if len(z) else np.nan,delay_denominator=len(z),note='Delay only for a new attack-window alarm not already present in paired clean run'))
    pd.DataFrame(event).to_csv(OUT/'event_delay_summary.csv',index=False)
    # per-session differences: step sign comparison at each method.
    diff=[]
    for method in methods:
        g=res[res.method==method].pivot(index='run',columns='attack',values='excess')
        for run,r in g.iterrows():diff.append(dict(run=run,method=method,negative_minus_positive_step=float(r.step_m5-r.step_p5),negative_minus_positive_ramp=float(r.ramp_m5-r.ramp_p5)))
    pd.DataFrame(diff).to_csv(OUT/'signed_pairs.csv',index=False)
    # Figures: raw paired differences and per-session FAR response curves.
    fig,axs=plt.subplots(1,2,figsize=(11,4.6))
    colors={'soc_binned':'C0','time_binned':'C1','basic_cusum':'C2'}
    for method in colors:
        x=pd.DataFrame(paired);g=x[x.comparison==method+' minus global'];axs[0].scatter([method]*len(g),g.difference*100,label=method,alpha=.8)
    axs[0].axhline(0,color='black',lw=.8);axs[0].set_ylabel('Paired clean-FAR change (percentage points)');axs[0].set_title('12 raw session-paired differences');axs[0].tick_params(axis='x',rotation=18)
    for method,g in res[res.attack.isin(['normal','step_p5','step_m5'])].groupby('method'):
        c=g[g.attack=='normal'].set_index('run').clean_far
        y=g[g.attack=='step_m5'].set_index('run').excess
        axs[1].scatter(c*100,y*100,label=method,alpha=.7)
    axs[1].axvline(5,color='grey',ls='--');axs[1].set_xlabel('Achieved clean FAR (%)');axs[1].set_ylabel('−5 pp excess response (pp)');axs[1].set_title('FAR versus response · session points');axs[1].legend(fontsize=8)
    fig.tight_layout();fig.savefig(OUT/'paired_points_frontier.png',dpi=180);plt.close(fig)
    # uncertainty sign warning and assertion on pairing.
    assert len(res)==12*4*5
    assert (res[res.attack=='normal'].groupby('method').size()==12).all()
    print(pd.read_csv(OUT/'far_bootstrap.csv').to_string(index=False))
    print(pd.read_csv(OUT/'event_delay_summary.csv').to_string(index=False))
    print('Saved',OUT)

if __name__=='__main__':
    ap=argparse.ArgumentParser();ap.add_argument('--input',type=Path,default=DEFAULT);args=ap.parse_args();main(args.input)

# Additional source-quantile sweep to display realized FAR-response trade-offs.
def frontier(input_file=DEFAULT):
    global ALPHA
    d=pd.read_csv(input_file);d=d[d.i>30].copy();r=[]
    for alpha in (.01,.025,.05,.10,.20,.30):
      ALPHA=alpha
      for run in sorted(d.run.unique()):
        src=d[d.run!=run];target=d[d.run==run].sort_values('i')
        for method in ['global','soc_binned','time_binned']:
          clean,_,_=eval_method(src,target,method,'normal')
          for attack in ('step_p5','step_m5','ramp_p5','ramp_m5'):
            a,_,_=eval_method(src,target,method,attack)
            r.append(dict(alpha=alpha,run=run,method=method,attack=attack,clean_far=clean['clean_far'],excess=a['excess'],new_event=a['new_event']))
    ALPHA=.05
    pd.DataFrame(r).to_csv(OUT/'source_quantile_frontier.csv',index=False)
    return pd.DataFrame(r)
