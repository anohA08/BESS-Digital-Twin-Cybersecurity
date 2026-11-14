"""Run the copied ECM on recorded voltage/current, saving results and a figure."""
import argparse
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parent/'src'))
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from bess.box1.replay import run_replay

def main():
    p=argparse.ArgumentParser()
    p.add_argument('--profile', choices=['1A','1.5A','2A'],default='1A')
    p.add_argument('--out',default='results/box1')
    args=p.parse_args()
    out=Path(args.out);out.mkdir(parents=True,exist_ok=True)
    df=run_replay(args.profile)
    df.to_csv(out/f'box1_{args.profile}_replay.csv',index=False)
    fig,ax=plt.subplots(figsize=(8,4));ax.plot(df.time_min,df.voltage_measured_v,label='Recorded voltage');ax.plot(df.time_min,df.voltage_predicted_v,label='ECM prediction');ax.set(xlabel='Time (min)',ylabel='Voltage (V)',title=f'Box 1 replay: {args.profile}');ax.legend();fig.tight_layout();fig.savefig(out/f'box1_{args.profile}_voltage.png',dpi=200);plt.close(fig)
    print(f'PASS: {len(df)} rows; outputs saved under {out}')
if __name__=='__main__':main()
