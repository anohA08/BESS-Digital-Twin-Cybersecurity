"""Truth-separated, paired and event-level metrics (adapted from old Box4)."""
from __future__ import annotations
import numpy as np


def episodes(mask):
    m=np.asarray(mask, dtype=bool)
    if m.ndim != 1: raise ValueError('Expected 1-D mask')
    start=np.flatnonzero(m & ~np.r_[False,m[:-1]])
    end=np.flatnonzero(m & ~np.r_[m[1:],False])
    return list(zip(start.tolist(),end.tolist()))


def binary_alarms(values):
    a=np.asarray(values)
    if a.ndim!=1 or not np.isin(a,[0,1,False,True]).all():
        raise ValueError('Alarm and truth must be binary')
    return a.astype(bool)


def detection_metrics(truth, alarm, times):
    t=binary_alarms(truth); a=binary_alarms(alarm); times=np.asarray(times,dtype=float)
    if len(t)!=len(a) or len(t)!=len(times) or len(t)==0: raise ValueError('Unequal/empty arrays')
    if not np.isfinite(times).all() or not (np.diff(times)>0).all():raise ValueError('Invalid time axis')
    tp=int((t&a).sum()); fp=int((~t&a).sum()); fn=int((t&~a).sum()); tn=int((~t&~a).sum())
    events=episodes(t); alert_events=episodes(a)
    delays=[]
    for start,stop in events:
        hits=np.flatnonzero(a[start:stop+1]);delays.append(float(times[start+hits[0]]-times[start]) if len(hits) else None)
    false_alert_episodes=sum(not t[s:e+1].any() for s,e in alert_events)
    return dict(n=len(t),tp=tp,fp=fp,fn=fn,tn=tn,
        clean_far=fp/(fp+tn) if fp+tn else None,
        attack_alarm_fraction=tp/(tp+fn) if tp+fn else None,
        attack_events=len(events),detected_attack_events=sum(v is not None for v in delays),
        first_detection_delay_min=delays[0] if len(delays)==1 else None,
        false_alert_episodes=int(false_alert_episodes),alert_episodes=len(alert_events))


def paired_metrics(normal, attacked, attack_mask, times):
    c=binary_alarms(normal);a=binary_alarms(attacked);m=binary_alarms(attack_mask)
    if not (len(c)==len(a)==len(m)==len(times)):raise ValueError('Pair mismatch')
    if not m.any():raise ValueError('No attack window')
    # Attack injection does not affect the past; any difference before onset signals leakage/bug.
    onset=np.flatnonzero(m)[0]
    if not np.array_equal(c[:onset],a[:onset]):raise ValueError('Pre-attack alarm mismatch / leakage')
    dm=detection_metrics(m,a,times)
    clean_window_alarms=int(c[m].sum()); attack_window_alarms=int(a[m].sum())
    dm.update(paired_clean_window_alarms=clean_window_alarms,
       attack_window_alarms=attack_window_alarms,
       paired_excess_alarm_fraction=(attack_window_alarms-clean_window_alarms)/int(m.sum()),
       new_attack_alarm_samples=int((a[m]&~c[m]).sum()),
       paired_clean_event_hit=bool(c[m].any()),
       attacked_event_hit=bool(a[m].any()),
       new_event_hit=bool(a[m].any() and not c[m].any()),
       attack_length_samples=int(m.sum()))
    return dm


def advisory_metrics(frame, requested_power_kw):
    tr=frame['trust_mode'].to_numpy(str); power=frame['advisory_power_kw'].to_numpy(float)
    dt=frame['dt_h'].to_numpy(float); truth=binary_alarms(frame['truth_attack_evaluation_only'])
    if not np.isfinite(power).all() or not np.isfinite(dt).all() or (dt<=0).any():
        raise ValueError('Invalid powers or step sizes')
    if not np.isfinite(requested_power_kw):raise ValueError('Invalid request')
    dv=np.abs(power-requested_power_kw)*dt
    safe=(tr=='SAFE'); cautious=(tr=='CAUTIOUS')
    return dict(safe_samples=int(safe.sum()),safe_outside_attack=int((safe&~truth).sum()),
                safe_inside_attack=int((safe&truth).sum()),
                safe_episodes=len(episodes(safe)),cautious_samples=int(cautious.sum()),
                mode_transitions=int((tr[1:]!=tr[:-1]).sum()),
                advisory_deviation_kwh=float(dv.sum()),
                advisory_deviation_clean_kwh=float(dv[~truth].sum()),
                advisory_deviation_attack_kwh=float(dv[truth].sum()),
                changed_samples=int((np.abs(power-requested_power_kw)>1e-9).sum()))
