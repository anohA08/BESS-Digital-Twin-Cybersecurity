"""Closed-loop, illustrative grid-scale scenario runner.

True SOC exists solely inside the plant; only its unauthenticated BMS-like
report goes to online cybersecurity algorithms. Exogenous demand and attacks
are paired across policies but the trajectories respond to the executed power.
"""
from pathlib import Path
import json
import numpy as np
import pandas as pd
from bess.box2.five_evidence import calibrate_five_evidence
from bess.box3.core import Box3Coordinator, Config
from bess.box3.bridge import policy_step
from bess.gridscale.plant import GridPlant, PlantConfig
from bess.gridscale.monitor import OnlineFiveEvidence

POLICIES=('unprotected','legacy','confirmed_only')
SCENARIOS=('normal','spoof_p5','spoof_m5','spoof_ramp_p5','fixed_replay','rolling_replay','delay_3min')

def _requested_kw(k):
    return 700. if k < 60 else (-800. if k < 120 else 850.)

def _shadow(row):
    if row['attack_assessment']=='ATTACK_DETECTED': return row
    return {'classification':'NORMAL','attack_assessment':'NO_ATTACK_DETECTED'}

def _synthetic_clean_source(initial_soc, n, bias_pp, capacity_kwh, efficiency):
    # Independently specified illustrative operating traces. No attack outcomes used.
    p=initial_soc;twin=p
    rows=[]
    for k in range(n):
        req=(500. if k%100 < 50 else -600.)
        dt=1/60.
        d=(-req/efficiency if req>=0 else -req*efficiency)*dt/capacity_kwh*100
        p=max(20.,min(90.,p+d));twin=max(20.,min(90.,twin+d*.996))
        rows.append(dict(time_min=float(k),telemetry_soc_pct=p+bias_pp,
             soc_estimated_pct=twin,telemetry_voltage_v=3.6+0.005*p,
             voltage_predicted_v=3.6+0.005*twin,
             source_timestamp_min=float(k),receive_timestamp_min=float(k),truth_attack=0))
    return pd.DataFrame(rows)

def make_calibration(cfg):
    """Frozen clean-calibration inputs, independent of simulated target scenario.
    Synthetic bias is configured, not inferred from target truth or attacks.
    """
    sources=[_synthetic_clean_source(55.,180,+.35,cfg.capacity_kwh,cfg.discharge_efficiency),
             _synthetic_clean_source(65.,180,-.25,cfg.capacity_kwh,cfg.discharge_efficiency)]
    return calibrate_five_evidence(sources)

def _scenario_soc(scenario,k,clean_report,history):
    attacked=30 <= k < 90
    if not attacked:return clean_report,False
    if scenario=='spoof_p5': return clean_report+5.,True
    if scenario=='spoof_m5': return clean_report-5.,True
    if scenario=='spoof_ramp_p5': return clean_report+5*min((k-30)/50.,1.),True
    if scenario=='fixed_replay':return history[29],True
    if scenario=='rolling_replay':return history[max(0,k-8)],True
    return clean_report,scenario=='delay_3min'

def simulate(scenario,policy,cfg=None,n=180,calibration=None):
    if scenario not in SCENARIOS or policy not in POLICIES:raise ValueError('Unknown scenario or policy')
    if n < 91:raise ValueError('At least 91 minutes needed for full attack window')
    cfg=cfg or PlantConfig()
    cal=calibration or make_calibration(cfg)
    plant=GridPlant(cfg)
    detector=OnlineFiveEvidence(cal)
    coord=None if policy=='unprotected' else Box3Coordinator(Config(
        soc_min=cfg.soc_min,soc_max=cfg.soc_max,max_power_kw=cfg.power_limit_kw))
    # Twin is estimated from the trusted power meter / executed dispatch only.
    # Initialization is an assumption, NOT a trusted true-SOC feed during operation.
    twin=cfg.initial_soc+0.4
    clean_history=[]; rows=[]
    h=cfg.dt_minutes/60.
    for k in range(n):
        requested=_requested_kw(k)
        # Simulated BMS report is obtained through a separate reporting interface.
        # The harness knows true SOC to synthesize the report, but does not send
        # this state or any truth label to the detector or Box3 coordinator.
        clean_report=plant.evaluation_soc+0.3
        clean_history.append(clean_report)
        reported,attacked=_scenario_soc(scenario,k,clean_report,clean_history)
        source_time=float(max(29,k-3) if (scenario=='delay_3min' and attacked) else k)
        # Simulated terminal voltage is only a proxy; no cell ECM scaling is claimed.
        measured_v=3.6+0.005*plant.evaluation_soc
        predicted_v=3.6+0.005*twin
        monitoring=detector.step(time_min=float(k), telemetry_soc_pct=reported,
            soc_estimated_pct=twin,telemetry_voltage_v=measured_v,
            voltage_predicted_v=predicted_v,source_timestamp_min=source_time,
            receive_timestamp_min=float(k))
        if policy=='unprotected':
            advised=requested;mode='UNPROTECTED';trust=float('nan')
        else:
            inp=monitoring if policy=='legacy' else _shadow(monitoring)
            decision=policy_step(coord,inp,twin,reported,requested)
            advised=decision['advisory_power_kw'];mode=decision['trust_mode'];trust=decision['trust_score']
        result=plant.step(advised)
        actual=result['executed_kw']
        # The twin receives executed dispatch via a hypothetical independent meter.
        # Introduce a fixed efficiency mismatch, predeclared and never calibrated on attacks.
        twin_eff=0.94
        twin += 100*((-actual/twin_eff) if actual>=0 else (-actual*twin_eff))*h/cfg.capacity_kwh
        twin=max(cfg.soc_min,min(cfg.soc_max,twin))
        rows.append(dict(minute=k,scenario=scenario,policy=policy,attack_truth_evaluation_only=int(attacked),
           requested_kw=requested,advised_kw=advised,executed_kw=actual,
           true_soc_evaluation_only=result['soc_true_evaluation_only'],
           twin_soc_pct=twin,reported_soc_pct=reported,mode=mode,trust=trust,
           strict_box2_alarm=monitoring['alarm'],
           box2_assessment=monitoring['attack_assessment'],
           requested_vs_executed_kwh=abs(requested-actual)*h,
           intervention_from_policy_kwh=abs(requested-advised)*h,
           plant_interlock_kwh=abs(advised-actual)*h))
    return pd.DataFrame(rows)

def run(out='results/gridscale',n=180):
    dest=Path(out);dest.mkdir(parents=True,exist_ok=True)
    cfg=PlantConfig();cal=make_calibration(cfg)
    summary=[]
    for scenario in SCENARIOS:
        for policy in POLICIES:
            df=simulate(scenario,policy,cfg,n,cal)
            df.to_csv(dest/f'{scenario}_{policy}.csv',index=False)
            summary.append(dict(scenario=scenario,policy=policy,
                simulated_alarm_samples=int(df.strict_box2_alarm.sum()),
                simulated_safe_samples=int((df['mode']=='SAFE').sum()),
                min_true_soc=float(df.true_soc_evaluation_only.min()),
                max_true_soc=float(df.true_soc_evaluation_only.max()),
                delivered_discharge_kwh=float(df.executed_kw.clip(lower=0).sum()/60),
                plant_interlock_kwh=float(df.plant_interlock_kwh.sum()),
                intervention_kwh=float(df.intervention_from_policy_kwh.sum()),
                changed_dispatch_kwh=float(df.requested_vs_executed_kwh.sum())))
    result=pd.DataFrame(summary);result.to_csv(dest/'summary.csv',index=False)
    (dest/'ASSUMPTIONS.json').write_text(json.dumps({
        'status':'SIMULATED; NOT grid-scale hardware or independent-cell validation',
        'plant':cfg.__dict__, 'monitor':'Frozen five-evidence algorithm, synthetically source-calibrated',
        'trust':'Frozen Box3 heuristic, different report from private physical state',
        'voltage':'Illustrative linear SOC-voltage proxy, NOT scaled cell ECM or real pack voltage',
        'meter':'Assumed independent trusted executed-power measurement; not demonstrated secure',
        'hard_limits':'Enforced by plant oracle inside its own physical interlocks: zero violations are guaranteed by construction',
        'attack':'SOC report manipulation/replay; delay modeled as source timestamp age only',
        'comparability':'Exogenous requested dispatch matched; executed trajectories differ by policy',
        'scope':'Supplemental demonstration; do not merge these events with twelve-session measurements'
    },indent=2))
    print(result.to_string(index=False));print('Output:',dest)
    return result
