"""Explicit clean/attack paired sample and event accounting."""
import numpy as np
import pandas as pd

def summarise(df:pd.DataFrame, alarm_col='alarm')->dict:
    a=df[alarm_col].to_numpy(dtype=int)
    truth=df['truth_attack'].to_numpy(dtype=int)
    active=truth==1
    clean=~active
    return dict(clean_n=int(clean.sum()),false_alarm_samples=int(a[clean].sum()),
        clean_far=float(a[clean].mean()) if clean.any() else None,
        attack_n=int(active.sum()),attack_alert_samples=int(a[active].sum()),
        attack_window_alarm_fraction=float(a[active].mean()) if active.any() else None,
        attack_event_flag=int(a[active].any()) if active.any() else None)

def paired_excess(clean:pd.DataFrame, attacked:pd.DataFrame)->float:
    if len(clean)!=len(attacked) or not np.array_equal(clean.attack_window.to_numpy(),attacked.attack_window.to_numpy()):
        raise ValueError('Paired evaluation requires matched windows')
    mask=attacked.attack_window.to_numpy(dtype=bool)
    return float(np.mean(attacked.alarm.to_numpy()[mask]-clean.alarm.to_numpy()[mask]))
