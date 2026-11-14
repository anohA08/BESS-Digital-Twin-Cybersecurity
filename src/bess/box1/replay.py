"""Minimal measured-voltage replay. Recorded SOC is never used to drive the model."""
from pathlib import Path
import csv
import numpy as np
import pandas as pd
from .battery import Battery
from .digital_twin import DigitalTwin

PROCESSED=Path(__file__).parent/'data'/'processed'

def run_replay(current_name: str = '1A', initial_soc: float = 100.0) -> pd.DataFrame:
    paths={'1A':'discharge_1A.csv','1.5A':'discharge_1_5A.csv','2A':'discharge_2A.csv'}
    if current_name not in paths: raise ValueError('Use 1A, 1.5A or 2A')
    frame=pd.read_csv(PROCESSED/paths[current_name])
    required=['time(min)','voltage(V)','dis_current (A)','soc(%)']
    if not set(required).issubset(frame.columns): raise ValueError('Missing measured columns')
    for col in required:
        if not np.isfinite(pd.to_numeric(frame[col],errors='coerce').to_numpy(float)).all(): raise ValueError(f'Invalid {col}')
    times=frame['time(min)'].to_numpy(float)
    if (np.diff(times)<=0).any(): raise ValueError('Non-increasing time')
    battery=Battery()
    if not (battery.soc_min <= initial_soc <= battery.soc_max): raise ValueError('Initial SOC outside bounds')
    battery.set_state(initial_soc)
    twin=DigitalTwin(battery)
    rows=[]
    for i, row in frame.iterrows():
        dt=0 if i==0 else (times[i]-times[i-1])/60.0
        current=float(row['dis_current (A)'])
        v_pred=twin.predict_ecm_voltage(current,dt)
        measured=float(row['voltage(V)'])
        rows.append({'time_min':times[i], 'current_a':current, 'voltage_measured_v':measured,
            'voltage_predicted_v':v_pred,'voltage_residual_v':measured-v_pred,
            'soc_estimated_pct':battery.get_soc(), 'soc_recorded_for_evaluation_only_pct':float(row['soc(%)'])})
    return pd.DataFrame(rows)
