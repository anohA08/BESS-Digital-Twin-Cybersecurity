"""Measurement-identifiability audit, NOT an attack detector.

Distinguishes observable *report deviation* from unobservable *attack intent*.
Physical telemetry invariance below is specific to the project's SOC-only injection.
"""
import numpy as np
import pandas as pd
from bess.box2.attacks import inject_attack

OBSERVABLE = ('time_min','current_a','telemetry_soc_pct','telemetry_voltage_v',
              'source_timestamp_min','receive_timestamp_min','soc_estimated_pct',
              'voltage_predicted_v')
PHYSICAL = ('time_min','current_a','telemetry_voltage_v','soc_estimated_pct','voltage_predicted_v')

def benign_report_change(clean, offset_pp=5., start=40, stop=110, *, ramp=True):
    """Unattested, benign BMS report correction; same waveform as spoofing.

    No claim that such a correction actually occurred in recorded battery data.
    `truth_attack` is kept at zero and is never part of OBSERVABLE.
    """
    if not (np.isfinite(offset_pp) and 1 <= start < stop <= len(clean)):
        raise ValueError('Invalid offset or attack window')
    out = inject_attack(clean,'normal')
    offset = np.linspace(0.,offset_pp,stop-start) if ramp else np.full(stop-start,offset_pp)
    idx=np.arange(start,stop)
    out.loc[idx,'telemetry_soc_pct']=np.clip(out.loc[idx,'telemetry_soc_pct'].to_numpy(float)+offset,0,100)
    return out

def observable_equal(a,b,columns=OBSERVABLE):
    """Exact observable equality (tolerates no deviation); excludes truth labels."""
    if len(a)!=len(b) or any(c not in a or c not in b for c in columns):
        raise ValueError('Missing observables or length mismatch')
    return all(np.array_equal(a[c].to_numpy(),b[c].to_numpy(),equal_nan=False) for c in columns)

def report_anchor_discrepancy(observed, trusted_soc, *, uncertainty_pp):
    """Illustrative inconsistency flag given an *independent* trusted SOC anchor.

    A reference equal to `soc_recorded_for_evaluation_only_pct` is an oracle in
    these data, NOT a deployable verified BMS measurement. The flag indicates
    measurement mismatch, NEVER proof of malicious intent. Bounds require an
    externally justified uncertainty_pp (absolute per-sample error bound).
    """
    if not np.isfinite(uncertainty_pp) or uncertainty_pp < 0:
        raise ValueError('Uncertainty must be finite and nonnegative')
    x=observed['telemetry_soc_pct'].to_numpy(float)
    y=np.asarray(trusted_soc,dtype=float)
    if x.shape!=y.shape or not np.isfinite(x).all() or not np.isfinite(y).all():
        raise ValueError('Anchor shape or finite values invalid')
    return (np.abs(x-y)>uncertainty_pp).astype(int)

def audit_profile(profile, replay, *, start=40,stop=110):
    """Produce deterministic, scenario-specific physical invariance and ambiguity audit."""
    clean=inject_attack(replay,'normal')
    scenarios={
        'gradual_positive_5pp':(inject_attack(replay,'spoof_ramp_p5'),benign_report_change(replay,5,start,stop,ramp=True)),
        'gradual_negative_5pp':(_negative_ramp(replay,start,stop),benign_report_change(replay,-5,start,stop,ramp=True)),
        'abrupt_positive_2pp':(inject_attack(replay,'spoof_p2'),benign_report_change(replay,2,start,stop,ramp=False)),
    }
    out=[]
    for name,(attack,benign) in scenarios.items():
        identical=observable_equal(attack,benign)
        physical=observable_equal(clean,attack,PHYSICAL)
        # Demonstration uses recorded reference SOC as an *oracle* anchor. Its
        # provenance cannot support a real trustworthy independent SOC anchor.
        anchor=clean['soc_recorded_for_evaluation_only_pct'].to_numpy(float)
        cut=np.arange(start,stop)
        for bound in (0.5,1.,2.,5.):
            flags_attack=report_anchor_discrepancy(attack,anchor,uncertainty_pp=bound)
            flags_benign=report_anchor_discrepancy(benign,anchor,uncertainty_pp=bound)
            out.append(dict(profile=profile,scenario=name,assumed_anchor_error_bound_pp=bound,
                attack_and_benign_observationally_identical=identical,
                physical_channels_invariant_under_soc_attack=physical,
                attack_oracle_anchor_flagged_samples=int(flags_attack[cut].sum()),
                benign_oracle_anchor_flagged_samples=int(flags_benign[cut].sum()),
                attack_window_samples=len(cut),
                independent_anchor_available_in_project=False,
                authenticated_maintenance_log_available=False))
    return pd.DataFrame(out)

def _negative_ramp(replay,start,stop):
    df=inject_attack(replay,'normal')
    idx=np.arange(start,stop)
    df.loc[idx,'telemetry_soc_pct']=np.clip(df.loc[idx,'telemetry_soc_pct'].to_numpy(float)-np.linspace(0,5,len(idx)),0,100)
    df.loc[idx,'truth_attack']=1
    return df
