"""Run the frozen single-cell 12-session calibration audit end-to-end.

A reproducibility entry point, NOT a claim of independent-cell validation.
Never train model parameters from these held-out threshold tests.
"""
from __future__ import annotations
import argparse
import hashlib
import json
from pathlib import Path
import numpy as np
import pandas as pd

import run_single_protocol as base
import run_normalized_comparator as norm

ROOT = Path(__file__).resolve().parent
REQUIRED = ('run','current_group','i','time','online_soc','soc_discrepancy')

def validate_input(path: Path) -> dict:
    if not path.is_file():
        raise FileNotFoundError(f'Missing original residual export: {path}')
    d = pd.read_csv(path)
    missing = set(REQUIRED)-set(d.columns)
    if missing: raise ValueError(f'Missing columns: {sorted(missing)}')
    if len(d)!=1812 or d.run.nunique()!=12:
        raise ValueError('Frozen protocol requires 12 runs x 151 records (1812 rows)')
    if d[list(REQUIRED[1:])].isna().any().any():
        raise ValueError('Input has missing numeric values')
    if not np.isfinite(d[list(REQUIRED[1:])].to_numpy(dtype=float)).all():
        raise ValueError('Input has nonfinite numeric values')
    for run,g in d.groupby('run'):
        if len(g)!=151 or g.i.nunique()!=151 or sorted(g.i)!=list(range(1,152)):
            raise ValueError(f'Invalid sample sequence in {run}')
        if len(g.current_group.unique())!=1 or not np.all(np.diff(g.sort_values('i').time.to_numpy())>0):
            raise ValueError(f'Invalid current or time sequence in {run}')
    raw=path.read_bytes()
    return {'source_filename':str(path.relative_to(ROOT)) if path.is_relative_to(ROOT) else path.name,
            'source_sha256':hashlib.sha256(raw).hexdigest(), 'source_rows':len(d),
            'sessions':int(d.run.nunique()), 'evaluated_rows_per_session':121,
            'evaluated_total_rows':1452, 'single_cell':True,
            'model_parameter_fit_independence':'NOT VERIFIED',
            'physical_grid_scale_validation':False}

def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--input',type=Path,default=base.DEFAULT)
    args=ap.parse_args()
    path=args.input.resolve()
    manifest=validate_input(path)
    base.ALPHA=.05
    base.main(path)
    base.frontier(path)
    base.ALPHA=.05
    norm.main(path)
    from publication_figures import make_figures
    make_figures()
    targets=[ROOT/'run_submission.py',ROOT/'run_single_protocol.py',ROOT/'run_normalized_comparator.py',ROOT/'publication_figures.py']
    targets+=sorted((ROOT/'results').glob('*.csv'))
    targets+=sorted((ROOT/'normalized_comparison').glob('*.csv'))
    targets+=sorted((ROOT/'publication_figures').glob('*.png'))
    manifest['analysis_artifacts_sha256']={str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in targets}
    manifest['protocol']='leave-one-session-out source-only quantile; first 30 samples excluded; 5% source tail; persistence 3'
    manifest['scope']='SOC-discrepancy channel only; same-cell; semi-synthetic ±5pp steps/ramps; not independent EKF+CUSUM replication'
    (ROOT/'REPRODUCIBILITY_MANIFEST.json').write_text(json.dumps(manifest,indent=2)+'\n',encoding='utf8')
    print('\nPASS: validated data; complete reproducible frozen-protocol analysis')
    print('Input SHA256:',manifest['source_sha256'])

if __name__=='__main__':main()
