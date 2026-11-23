"""Figures with consistent legends, 12 session points, and true alpha frontiers."""
from pathlib import Path
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import pandas as pd
import numpy as np
ROOT=Path(__file__).resolve().parent
OUT=ROOT/'publication_figures'
STYLE={'global':('#444444','Global'), 'soc_binned':('#1565a3','Estimated-SOC bins'),
       'time_binned':('#ed8a25','Absolute-time bins'),
       'normalized_time_binned':('#2e8b57','Normalized-time bins'),
       'basic_cusum':('#9b59b6','Basic CUSUM')}

def make_figures():
    OUT.mkdir(exist_ok=True)
    allres=pd.read_csv(ROOT/'normalized_comparison'/'all_methods_per_session.csv')
    clean=allres[allres.attack=='normal'].set_index(['run','method']).clean_far
    fig,axs=plt.subplots(1,2,figsize=(11.4,4.5),layout='constrained')
    methods=['soc_binned','time_binned','normalized_time_binned','basic_cusum']
    for j,m in enumerate(methods):
        c,label=STYLE[m]
        diffs=[100*(clean.loc[(r,m)]-clean.loc[(r,'global')]) for r in sorted(allres.run.unique())]
        x=np.full(len(diffs),j)+np.linspace(-.15,.15,len(diffs))
        axs[0].scatter(x,diffs,color=c,s=26,alpha=.85,label=label)
        axs[0].plot([j-.22,j+.22],[np.mean(diffs)]*2,color=c,lw=2)
    axs[0].axhline(0,color='#333',lw=.8,ls='--')
    axs[0].set_xticks(range(len(methods)),[STYLE[m][1].replace(' bins','\nbins') for m in methods],fontsize=8)
    axs[0].set_ylabel('Clean FAR minus global (percentage points)')
    axs[0].set_title('(a) Held-out session-paired differences (n=12)')
    for m in ['global']+methods:
        c,label=STYLE[m]
        g=allres[(allres.method==m)&(allres.attack=='step_m5')].set_index('run')
        vals=[(100*clean.loc[(r,m)],100*g.loc[r,'excess']) for r in sorted(g.index)]
        axs[1].scatter(*np.array(vals).T,label=label,color=c,alpha=.75,s=28)
    axs[1].axvline(5,color='grey',ls='--',lw=.8)
    axs[1].set_xlabel('Achieved clean FAR (%)')
    axs[1].set_ylabel('−5 pp excess alarm fraction (percentage points)')
    axs[1].set_title('(b) Per-session FAR versus excess response')
    axs[1].legend(fontsize=7,loc='best')
    fig.savefig(OUT/'F1_session_pairs.png',dpi=220);plt.close(fig)

    # A real source-quantile frontier: aggregate paired session mean at six frozen alpha values.
    d=pd.read_csv(ROOT/'results'/'source_quantile_frontier.csv')
    fig,ax=plt.subplots(figsize=(7.7,5.2),layout='constrained')
    for m in ['global','soc_binned','time_binned']:
        g=d[(d.method==m)&(d.attack=='step_m5')]
        p=g.groupby('alpha').agg(far=('clean_far','mean'),response=('excess','mean')).reset_index()
        c,label=STYLE[m]
        ax.plot(p.far*100,p.response*100,'o-',color=c,label=label,lw=1.6,markersize=5)
        for _,r in p.iterrows(): ax.annotate(f'{r.alpha:g}',(r.far*100,r.response*100),xytext=(3,3),textcoords='offset points',fontsize=7,color=c)
    ax.set_xlabel('Mean achieved clean FAR across 12 sessions (%)')
    ax.set_ylabel('Mean −5 pp excess alarm fraction (percentage points)')
    ax.set_title('Source-quantile FAR–response sweep (annotations: source α)')
    ax.legend(fontsize=9)
    ax.grid(alpha=.15)
    fig.savefig(OUT/'F2_actual_source_quantile_frontier.png',dpi=220);plt.close(fig)

    fig,ax=plt.subplots(figsize=(8,4.7),layout='constrained')
    at=allres[allres.attack.isin(['step_p5','step_m5','ramp_p5','ramp_m5'])]
    summ=at.groupby(['method','attack'],as_index=False).new_event.sum()
    for j,m in enumerate(['global','soc_binned','time_binned','normalized_time_binned','basic_cusum']):
        g=summ[summ.method==m].set_index('attack')
        xx=np.arange(4)+(j-2)*.15
        ax.bar(xx,[g.loc[a,'new_event'] for a in ['step_p5','step_m5','ramp_p5','ramp_m5']],width=.14,color=STYLE[m][0],label=STYLE[m][1])
    ax.set_xticks(np.arange(4),['+5 pp step','−5 pp step','+5 pp ramp','−5 pp ramp'])
    ax.set_ylim(0,13);ax.set_yticks(range(0,13,2));ax.set_ylabel('Sessions with new paired attack-window alarm (of 12)')
    ax.legend(loc='upper center',bbox_to_anchor=(.5,1.18),ncol=3,fontsize=8)
    fig.savefig(OUT/'F3_attack_event_counts.png',dpi=220,bbox_inches='tight');plt.close(fig)

if __name__=='__main__':make_figures()
