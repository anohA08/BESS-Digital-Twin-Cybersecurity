"""Frozen baseline vs SOC-conditioned polynomial bias transfer; exploratory only."""
from pathlib import Path
import argparse,json,sys
import numpy as np
import pandas as pd
sys.path.insert(0,str(Path(__file__).resolve().parent/'src'))
from bess.box1.replay import run_replay
from bess.box2.attacks import inject_attack
from bess.research.bias_transfer import fit_bias_model,evaluate_soc_flags
from bess.box4.metrics import paired_metrics
PROFILES=('1A','1.5A','2A')
SCENARIOS=('spoof_m2','spoof_p2','spoof_m5','spoof_5','spoof_10','spoof_ramp_p5','fixed_replay','rolling_replay','delay_3min')
def run(output='results/research_bias_transfer'):
    dest=Path(output);dest.mkdir(parents=True,exist_ok=True)
    raws={p:run_replay(p) for p in PROFILES}
    clean=[];events=[];calibrations=[]
    for profile in PROFILES:
        source=[inject_attack(raws[p],'normal') for p in PROFILES if p!=profile]
        model=fit_bias_model(source)
        calibrations.append(dict(profile=profile,source_profiles=model.source_profiles,raw_threshold_pp=model.raw_limit_pp,bias_threshold_pp=model.residual_limit_pp,coef_0=model.coefficients[0],coef_1=model.coefficients[1],coef_2=model.coefficients[2]))
        baseline=inject_attack(raws[profile],'normal')
        normal=evaluate_soc_flags(baseline,model)
        for method in ('raw','bias_aware'):
            flags=normal[method]
            clean.append(dict(profile=profile,method=method,clean_alarms=int(flags.sum()),clean_samples=len(flags),clean_far=float(flags.mean()),passes_5pct=bool(flags.mean()<=.05)))
        for scenario in SCENARIOS:
            attacked=inject_attack(raws[profile],scenario)
            target=evaluate_soc_flags(attacked,model)
            truth=attacked.truth_attack.to_numpy(bool);times=attacked.time_min.to_numpy(float)
            for method in ('raw','bias_aware'):
                m=paired_metrics(normal[method],target[method],truth,times)
                events.append(dict(profile=profile,scenario=scenario,method=method,new_event_hit=int(m['new_event_hit']),raw_event_hit=int(m['attacked_event_hit']),new_alarm_samples=int(m['new_attack_alarm_samples']),paired_excess_alarm_fraction=m['paired_excess_alarm_fraction'],clean_window_alarms=int(m['paired_clean_window_alarms']),attack_window_alarms=int(m['attack_window_alarms'])))
    a=pd.DataFrame(clean);b=pd.DataFrame(events);c=pd.DataFrame(calibrations)
    a.to_csv(dest/'clean_gate.csv',index=False);b.to_csv(dest/'paired_attack_metrics.csv',index=False);c.to_csv(dest/'calibration_coefficients.csv',index=False)
    summary=b.groupby(['method','scenario'],as_index=False).agg(new_events=('new_event_hit','sum'),total_events=('new_event_hit','count'))
    summary.to_csv(dest/'event_summary.csv',index=False)
    report={'source_only_calibration':True,'source_battery_count':1,'profiles_used_to_design_research_prior_to_this_run':True,'soc_report_is_surrogate':True,'attack_injections_are_synthetic':True,'no_malicious_intent_identification':True,'no_independent_false_alarm_control':True,'feature':'quadratic SOC normalized (SOC-50)/50','ridge_penalty':0.01,'empirical_source_quantile':0.95,'persistence':3,'model_selection_using_target':False}
    (dest/'limitations.json').write_text(json.dumps(report,indent=2))
    print('CLEAN\n',a.to_string(index=False));print('\nEVENTS\n',summary.to_string(index=False));print('\nOUTPUT:',dest)
    return {'clean':a,'events':b,'summary':summary,'calibration':c}
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--out',default='results/research_bias_transfer');args=p.parse_args();run(args.out)
