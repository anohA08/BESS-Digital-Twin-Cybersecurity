# BESS Twelve-Session Calibration Audit — submission-code release candidate

**Paper title:** *Bias-Dependent Detectability of Reported-SOC Manipulation in Battery Digital-Twin Monitoring: A Twelve-Session Calibration Audit*

This is the **paper-specific code**, not a replacement for the four-box BESS repository. The laboratory digital twin, EKF, BC-MED, trust-policy, and grid-scale demonstration are intentionally not bundled into this single-protocol article release.

## Reproduce

Python 3.10+ recommended. Install dependencies:

```powershell
python -m pip install -r requirements.txt
python run_submission.py
python -m unittest discover -s tests -v
```

This script validates input format and sample sequence, then runs the original global/estimated-SOC/absolute-time threshold and basic CUSUM calculations, the six source-quantile frontier values, and the source-only normalized-time comparator. It writes:

- `results/`: evaluated session records, descriptive session-bootstrap intervals, paired differences, response/delay summaries, and a six-alpha source-quantile sweep;
- `normalized_comparison/`: five-method comparisons, source-only normalized time-bin summary, and paired exact tests;
- `publication_figures/`: corrected legend and paired-session plots, actual source-quantile FAR–response curve and attack-hit comparison;
- `REPRODUCIBILITY_MANIFEST.json`: original input SHA-256, per-output SHA-256, and protocol declaration.

For Windows PowerShell, from project directory:

```powershell
cd 'E:\Research\BESS Rebuilder\BESS_REBUILD_STARTER'
Expand-Archive -Path "$HOME\Downloads\BESS_SUBMISSION_CODE_REFINED.zip" -DestinationPath '.\paper_reproduction' -Force
cd '.\paper_reproduction'
.\.venv\Scripts\python.exe run_submission.py  # only if the venv exists here
```

If the venv is in the repository root, use `..\.venv\Scripts\python.exe` instead, or activate it and use `python`. This archive is **standalone** and may be extracted anywhere; running `python run_submission.py` from its own directory is sufficient after dependency installation.

## Protocol / interpretation

- **One battery, 12 sessions:** 4 sessions each at 1, 1.5, and 2 A. Each is a 151-row recorded segment. The 30-row prefix is excluded, leaving 121 evaluated rows per session.
- **Attack construction:** purely semi-synthetic perturbation to the SOC-discrepancy report; ±5 percentage-point steps and 0→±5 percentage-point 50-sample ramps, applied at indices 40–89. They are not authenticated field BMS attack logs.
- **Source-only held-out split:** 11 runs set thresholds; the held-out run is evaluated without using its labels to set thresholds. The physical twin *itself* is not independently refitted from 11 runs; original model-data overlap remains unresolved.
- **Calibration:** one global 95th-percentile absolute-discrepancy threshold or threshold in one of 10 estimated-SOC bins, absolute 10-minute time bins, or 10 normalized-time bins. Each bin requires ≥30 source samples, otherwise falls back to the source global threshold. Three consecutive threshold crossings are necessary for an alarm.
- **CUSUM:** a deliberately basic two-sided residual CUSUM with a source-derived allowance `k=0.5*median(abs(source residual))`, and a source 95th percentile of per-session-reset CUSUM scores for threshold `h`; not a faithful replication of a published EKF+CUSUM algorithm.
- **Normalized-time:** the bin horizon is the median maximum time in source sessions **of the held-out run's known current**, never target-session end time. The recorded 151-minute extents are identical across these truncated exports. Source-only normalization does not eliminate battery/current/time confounding or mean-FAR mismatch.
- **Metrics:** sample FAR is proportion of evaluation samples with an alarm, *not* event-level FAR; event hit requires an alarm in the attacked period not simultaneously present in the paired clean trace. Delay begins at the onset index and is reported only for such new alarm samples. A `new_event` does not establish attack intent attribution.
- **Session-bootstrap intervals:** descriptive repeated-session resampling from the same cell, not independent-cell confidence intervals. Unadjusted paired exact sign p-values are exploratory and do not fix multi-comparison or cell-dependence problems.
- **Frontier:** six predeclared source-quantile alpha levels (`0.01,0.025,0.05,0.10,0.20,0.30`). It is *not* a comparison at exactly matched achieved clean FAR.
- **Scope boundary:** the voltage-or-SOC joint detector tested elsewhere failed the nominal clean gate (8.88% mean FAR, 8/12 sessions at ≤5%). That negative outcome must be disclosed in the article; it is not part of these SOC-channel baselines.

## Checks before public release

1. **Data rights:** the included `data/raw_session_replayed_residuals.csv` contains record-level derived measurements from the original laboratory workbook. Confirm the dataset license and redistribution permission before publishing the archive. If redistribution is not authorized, remove it and describe controlled-access reconstruction; do not claim a fully self-contained public-data release.
2. **Source data/model provenance:** original workbook and twin parameter fitting may overlap evaluated sessions. Leave-one-session-out here guarantees only *threshold* isolation.
3. **Paper concordance:** independently compare final Word/PDF abstract, methods, tables, and figure captions with the generated tables. This archive does not claim a publication-ready author-signed manuscript.
4. **External replication:** no independent-cell result, grid-scale validation, proven mitigation improvement, or validated finite-window stealth guarantee is supported.

## Reproducibility contract

`run_submission.py` rejects altered-length, malformed, missing-value and non-monotonic-time data. Seven tests guard expected headline results, leakage-relevant source separation, the event window and persistence, and malformed input handling. The source SHA-256 is recorded to distinguish the frozen 12-session export from subsequent modifications.
