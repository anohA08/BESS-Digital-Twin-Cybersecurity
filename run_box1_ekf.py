"""Research diagnostic: compare one-step-ahead ECM and EKF predictions on measured discharge profiles.

The EKF prediction is recorded BEFORE the voltage measurement update; posterior fit is
not treated as out-of-sample voltage prediction. Recorded SOC is evaluation-only.
"""
import argparse
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parent / 'src'))
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from bess.box1.replay import run_replay, PROCESSED
from bess.box1.battery import Battery
from bess.box1.ekf import ExtendedKalmanFilter

FILES = {'1A': 'discharge_1A.csv', '1.5A': 'discharge_1_5A.csv', '2A': 'discharge_2A.csv'}

def compare(profile='1A', initial_soc=100.0):
    if profile not in FILES:
        raise ValueError(f'Unknown profile: {profile}')
    open_loop = run_replay(profile, initial_soc)
    raw = pd.read_csv(PROCESSED / FILES[profile])
    battery = Battery()
    if not battery.soc_min <= initial_soc <= battery.soc_max:
        raise ValueError('Initial SOC is outside battery bounds')
    ekf = ExtendedKalmanFilter(battery, initial_soc=initial_soc)
    records = []
    for i, row in raw.iterrows():
        dt_hours = 0.0 if i == 0 else (float(raw.iloc[i]['time(min)']) - float(raw.iloc[i - 1]['time(min)'])) / 60.0
        current = float(row['dis_current (A)'])
        measured_voltage = float(row['voltage(V)'])
        if dt_hours < 0:
            raise ValueError('Nonmonotonic time')
        ekf.predict(current=current, timestep_hours=dt_hours)
        soc_prior = ekf.get_soc()
        pred_prior = ekf._predict_terminal_voltage(ekf.get_soc(), ekf.get_v_rc(), current)
        innovation = measured_voltage - pred_prior
        ekf.update(measured_voltage=measured_voltage, current=current)
        records.append({
            'time_min': float(row['time(min)']), 'current_a': current,
            'voltage_measured_v': measured_voltage,
            'ecm_voltage_prior_v': float(open_loop.iloc[i]['voltage_predicted_v']),
            'ekf_voltage_prior_v': pred_prior,
            'ekf_innovation_v': innovation,
            'ecm_soc_estimated_pct': float(open_loop.iloc[i]['soc_estimated_pct']),
            'ekf_soc_prior_pct': soc_prior,
            'ekf_soc_posterior_pct': ekf.get_soc(),
            'soc_recorded_evaluation_only_pct': float(row['soc(%)']),
            'ekf_covariance_min_eigenvalue': float(np.linalg.eigvalsh((ekf.P + ekf.P.T) / 2).min())
        })
    return pd.DataFrame(records)

def summarize(df, profile):
    obs = df['voltage_measured_v'].to_numpy()
    result = {'profile': profile, 'samples': len(df)}
    for key, col in [('ecm', 'ecm_voltage_prior_v'), ('ekf', 'ekf_voltage_prior_v')]:
        err = obs - df[col].to_numpy()
        result[f'{key}_prior_voltage_rmse_mv'] = float(1000*np.sqrt(np.mean(err**2)))
        result[f'{key}_prior_voltage_mae_mv'] = float(1000*np.mean(np.abs(err)))
    return result

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--profile', choices=['1A','1.5A','2A','all'], default='all')
    ap.add_argument('--out', default='results/box1_ekf')
    args = ap.parse_args()
    out = Path(args.out); out.mkdir(parents=True, exist_ok=True)
    rows = []
    for profile in (list(FILES) if args.profile == 'all' else [args.profile]):
        df = compare(profile)
        df.to_csv(out / f'comparison_{profile.replace(".", "_")}.csv', index=False)
        rows.append(summarize(df, profile))
        fig, ax = plt.subplots(figsize=(9, 4))
        ax.plot(df.time_min, df.voltage_measured_v, label='Measured', linewidth=1.7)
        ax.plot(df.time_min, df.ecm_voltage_prior_v, label='Open-loop ECM', linewidth=1.3)
        ax.plot(df.time_min, df.ekf_voltage_prior_v, label='EKF prior (before update)', linewidth=1.3)
        ax.set(xlabel='Time (min)', ylabel='Terminal voltage (V)', title=f'Box 1 diagnostic — {profile}')
        ax.legend(); fig.tight_layout()
        fig.savefig(out / f'voltage_{profile.replace(".", "_")}.png', dpi=180)
        plt.close(fig)
    pd.DataFrame(rows).to_csv(out / 'metrics.csv', index=False)
    print(pd.DataFrame(rows).to_string(index=False))
    print('Exploratory same-profile evaluation. EKF receives measured voltage for updating; these are prior predictions.')

if __name__ == '__main__':
    main()
