"""Frozen-source signed-stealth-region diagnostic; exploratory, not a new detector.

Uses actual Box 1/2 code, including clipping and original attack-window assumptions.
No target data are used for threshold calibration; observed clean target residuals
are inspected only in post-hoc *analysis*. All three profiles are one cell.
"""
from pathlib import Path
import argparse, hashlib, json, sys
import numpy as np
import pandas as pd
sys.path.insert(0, str(Path(__file__).resolve().parent / 'src'))
from bess.box1.replay import run_replay
from bess.box2.attacks import AttackWindow, inject_attack
from bess.box2.detectors import calibrate_global, detect_threshold
from bess.box4.metrics import paired_metrics

PROFILES = ('1A','1.5A','2A')
OFFSETS = (-10.,-5.,-2.,2.,5.,10.)


def interval(bias, threshold):
    """r=bias+attack, strict alarm iff |r|>threshold. Closed non-alarm interval."""
    if not np.isfinite(bias).all() or not np.isfinite(threshold) or threshold <= 0:
        raise ValueError('Finite bias and positive threshold required')
    b=np.asarray(bias,dtype=float)
    return -threshold-b,threshold-b


def analyze_profile(raw, source_clean, target, offsets=OFFSETS, window=AttackWindow()):
    """Returns per-sample signed predictions and paired detector-level outcomes.

    The algebraic predictions are SOC-only and are not full detector alarms.
    All source calibration excludes target. Reported SOC is a dataset surrogate.
    """
    cal=calibrate_global(source_clean)
    normal=inject_attack(raw,'normal',window)
    b=(normal.telemetry_soc_pct-normal.soc_estimated_pct).to_numpy(float)
    low,high=interval(b,cal.soc_limit_pp)
    original_alarm=detect_threshold(normal,cal).alarm.to_numpy()
    indices=np.arange(window.start,window.stop)
    samples=[];summary=[]
    for a in offsets:
        if a==0: raise ValueError('Offsets must be nonzero')
        attacked=normal.copy(deep=True)
        reported=np.clip(normal.telemetry_soc_pct.to_numpy(float)[indices]+a,0.,100.)
        attacked.loc[indices,'telemetry_soc_pct']=reported
        attacked.loc[indices,'truth_attack']=1
        # Compare the actual altered residual, including clipping.
        actual_r=reported-attacked.soc_estimated_pct.to_numpy(float)[indices]
        clean_r=b[indices]
        attack_change=actual_r-clean_r
        pre_soc_flags=np.abs(clean_r)>cal.soc_limit_pp
        post_soc_flags=np.abs(actual_r)>cal.soc_limit_pp
        new_soc_flags=post_soc_flags & ~pre_soc_flags
        hidden_soc=(~post_soc_flags)
        scores=detect_threshold(attacked,cal)
        met=paired_metrics(original_alarm,scores.alarm.to_numpy(),
                 attacked.truth_attack.to_numpy(bool),attacked.time_min.to_numpy(float))
        for j,i in enumerate(indices):
            samples.append(dict(profile=target,offset_requested_pp=a,index=int(i),
               time_min=float(normal.time_min.iloc[i]),clean_bias_pp=float(b[i]),
               effective_attack_pp=float(attack_change[j]),
               source_soc_threshold_pp=float(cal.soc_limit_pp),
               lower_non_alarm_offset_pp=float(low[i]),upper_non_alarm_offset_pp=float(high[i]),
               predicted_soc_clean_alarm=int(pre_soc_flags[j]),
               predicted_soc_attacked_alarm=int(post_soc_flags[j]),
               predicted_soc_new_alarm=int(new_soc_flags[j]),
               predicted_soc_stealth=int(hidden_soc[j])))
        summary.append(dict(profile=target,offset_requested_pp=a,
            calibrated_source_profiles=len(source_clean),soc_threshold_pp=float(cal.soc_limit_pp),
            voltage_threshold_v=float(cal.voltage_limit_v),
            soc_stealth_fraction=float(hidden_soc.mean()),
            soc_new_alarm_fraction=float(new_soc_flags.mean()),
            clean_soc_above_fraction=float(pre_soc_flags.mean()),
            min_effective_attack_pp=float(attack_change.min()),
            max_effective_attack_pp=float(attack_change.max()),
            paired_new_full_detector_event=int(met['new_event_hit']),
            paired_excess_full_alarm_fraction=float(met['paired_excess_alarm_fraction']),
            full_detector_attack_window_alarm_fraction=float(met['attack_alarm_fraction']),
            clean_full_detector_window_alarm_fraction=float(met['paired_clean_window_alarms']/len(indices))))
    cleanres=dict(profile=target,bias_mean_pp=float(np.mean(b[indices])),
        bias_median_pp=float(np.median(b[indices])),
        bias_min_pp=float(np.min(b[indices])),bias_max_pp=float(np.max(b[indices])),
        source_soc_threshold_pp=float(cal.soc_limit_pp),
        clean_full_detector_alarm_fraction=float(original_alarm.mean()))
    return pd.DataFrame(samples),pd.DataFrame(summary),cleanres


def run(output='results/research_stealth_regions'):
    dest=Path(output);dest.mkdir(parents=True,exist_ok=True)
    raws={p:run_replay(p) for p in PROFILES}
    samples=[];summaries=[];clean=[]
    for target in PROFILES:
        src=[inject_attack(raws[p],'normal') for p in PROFILES if p!=target]
        detail,result,cleanres=analyze_profile(raws[target],src,target)
        samples.append(detail);summaries.append(result);clean.append(cleanres)
    sample=pd.concat(samples,ignore_index=True)
    summary=pd.concat(summaries,ignore_index=True)
    baseline=pd.DataFrame(clean)
    pairs=[]
    for magnitude in (2.,5.,10.):
        pos=summary[summary.offset_requested_pp==magnitude].set_index('profile')
        neg=summary[summary.offset_requested_pp==-magnitude].set_index('profile')
        for profile in PROFILES:
            pairs.append(dict(profile=profile,abs_offset_pp=magnitude,
                 positive_soc_stealth_fraction=float(pos.loc[profile,'soc_stealth_fraction']),
                 negative_soc_stealth_fraction=float(neg.loc[profile,'soc_stealth_fraction']),
                 positive_minus_negative_stealth=float(pos.loc[profile,'soc_stealth_fraction']-neg.loc[profile,'soc_stealth_fraction']),
                 positive_new_full_event=int(pos.loc[profile,'paired_new_full_detector_event']),
                 negative_new_full_event=int(neg.loc[profile,'paired_new_full_detector_event'])))
    asym=pd.DataFrame(pairs)
    sample.to_csv(dest/'per_sample_stealth_intervals.csv',index=False)
    summary.to_csv(dest/'signed_offset_summary.csv',index=False)
    baseline.to_csv(dest/'clean_bias_characterization.csv',index=False)
    asym.to_csv(dest/'matched_signed_asymmetry.csv',index=False)
    try:
        import matplotlib.pyplot as plt
        fig,ax=plt.subplots(figsize=(9,5))
        for p in PROFILES:
            s=summary[summary.profile==p].sort_values('offset_requested_pp')
            ax.plot(s.offset_requested_pp,s.soc_stealth_fraction,'o-',label=p)
        ax.set(xlabel='Requested SOC-report offset (percentage points)',ylabel='Fraction of attack window below SOC threshold',
               title='Frozen SOC-threshold non-alarm fractions (descriptive)',ylim=(-.05,1.05))
        ax.grid(alpha=.2);ax.legend();fig.tight_layout()
        fig.savefig(dest/'signed_stealth_regions.png',dpi=180);plt.close(fig)
    except ImportError:
        pass
    notes=dict(frozen_source_only_calibration=True,target_inspected_in_analysis=True,
        target_profiles_used_to_design_prior_methods=True,
        source_count_per_target=2,physical_battery_count=1,
        authentic_bms_soc=False,measured_attacks=False,
        confidence_interval_claim=False,statistical_fpr_guarantee=False,
        threshold_intervals_are_soc_only=True,full_detector_uses_voltage_and_persistence=True,
        all_results_exploratory=True,
        binning_or_method_optimization_performed=False,
        code_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest())
    (dest/'limitations_manifest.json').write_text(json.dumps(notes,indent=2))
    print('BIAS\n',baseline.to_string(index=False))
    print('\nSIGNED PAIRS\n',asym.to_string(index=False))
    print('\nOUTPUT:',dest)
    return {'samples':sample,'summary':summary,'bias':baseline,'asymmetry':asym}

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--out',default='results/research_stealth_regions');args=p.parse_args();run(args.out)
