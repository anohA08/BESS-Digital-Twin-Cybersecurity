"""Run stand-alone supplementary grid-scale closed-loop simulation."""
import argparse,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent/'src'))
from bess.gridscale.integration import run
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--out',default='results/gridscale');p.add_argument('--minutes',type=int,default=180)
    a=p.parse_args();run(a.out,a.minutes)
