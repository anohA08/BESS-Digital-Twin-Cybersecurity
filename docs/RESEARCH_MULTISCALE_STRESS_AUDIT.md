# Multi-timescale bias audit — exploratory negative result

## Motivation
The pre-existing signed residual increment candidate detects abrupt SOC-report changes but misses gradual SOC manipulation. This audit tests whether signed change over causal windows of 4, 8, 16 and 32 observations, with source-only maxima multiplied by a fixed 1.5 guard, offers any improvement.

## Provenance and limitations
The three target discharge profiles (1 A, 1.5 A, 2 A) come from one physical battery. The SOC column is an evaluation surrogate, not independently authenticated BMS telemetry. The attack injections are deterministic synthetic modifications of recorded trajectories, not real cyber intrusions. These same target profiles have been reviewed during development. Leave-one-current-profile-out calibration is NOT independent external validation. Source maxima multiplied by a guard factor give no statistical false-alarm guarantee. The benign +2 pp report correction is observationally indistinguishable from a +2 pp FDIA for an SOC-only monitor.

## Reproducible observations
- All pre-existing 65 tests plus 7 new tests passed (72 total).
- Source-calibrated multi-window monitor: clean alarms 0/152 at 1 A; 0/152 at 1.5 A; **11/152 at 2 A** (7.24%).
- Both +5 pp and -5 pp gradual 70-sample ramps: **0/3 event hits** each. A clean per-profile 5% gate fails on the 2 A recording.
- Abrupt positive +2 pp: **0/3** hits for the multi-window monitor, versus 3/3 for signed increment.
- The signed increment monitor flags the benign +2 pp reset in **3/3** tests, demonstrating a non-identifiability limitation.
- Multi-window thresholding is **not** promoted as a better detector. There is no performance tuning, data-driven selection of windows, or modification of the frozen Box 1–4 baselines.

## Interpretation
Long-window model drift can exceed the accumulated effect of low-amplitude ramp attacks, so unconditioned maximum-source-drift thresholding is insufficient. Strengthening claims requires independently measured SOC or trustworthy physics-based evidence, benign reset/operating-condition controls, held-out cells, and matched-FAR comparisons. A more elaborate alarm fusion would not by itself overcome identical observation sequences.

## Reproduce
```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
.\.venv\Scripts\python.exe run_research_multiscale.py
```

Results: `results/research_multiscale/scenario_comparison.csv`, `window_calibration.csv`, `event_summary.csv`, and `limitations.json`.
