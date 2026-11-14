# Box 2: Five-evidence integration — exploratory

## Provenance and scope

The following prior-repository components were copied without changing their public implementations from `BESS_ClosedLoop_Framework_v0_2/BESS_Box1_Box2_RealData_Baseline/box2/`: synchronization, temporal, voltage, freshness, evidence fusion, persistence, attack classification, and situation assessment. They are held under `src/bess/box2/legacy/`.

`five_evidence.py` is the new controlled adapter that supplies source-calibrated thresholds and per-run state resets. **Physics evidence** is a *new minimal adaptation*: a measured-SOC-surrogate versus independent-twin **SOC-step consistency residual**. We deliberately did **not** port the previous energy-consistency evidence as an independent channel because its `observed_energy` originated from reported SOC. It cannot serve as independent attack evidence. This adapter does not duplicate the legacy PhysicsValidator.

The SOC-report channel is constructed from a laboratory SOC proxy, **not authenticated BMS telemetry**. Replay and communication-delay cases simulate timestamps and SOC/voltage packets, not a real network. Fresh timestamps on replay intentionally prevent freshness-only replay detection.

## Detector specification

- Source calibration: 1 A / 1.5 A / 2 A other profiles; target profile is held out for threshold estimation. These profiles are derived from the **same battery**, not independent cells.
- Synchronization: `abs(telemetry_soc - twin_soc)`; 3 region envelopes selected by **estimated twin SOC** (fallback to global when a source bin has fewer than 30 points), source p95/p99.
- Physics: absolute difference between the timestep changes in telemetry SOC and independently propagated twin SOC, source p95/p99.
- Temporal: original stateful jump/repetition/gap detector, reset on each scenario; expected SOC change derived from twin only.
- Voltage: original voltage-evidence implementation with source-only global p95/p99, in V; this does NOT use the legacy per-current calibration table (it would be incompatible with cross-profile testing).
- Freshness: original timestamp-age detector, p95=0 and p99=1 minute, matching simulated timestamp semantics; not learned from data.
- Fusion: original ordinal 0/1/2 five-channel weighted fusion and consecutive 3-sample persistence. Signature classifier and situation assessment are **heuristic labels**, not confirmed attack ground truth or calibrated posterior probability.

No detector reads `truth_attack` or `attack_window`; those remain evaluation labels only.

## Run

From repository root (Windows PowerShell):

```
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
.\.venv\Scripts\python.exe run_box2_fusion.py --profile 2A
```

Results: `results/box2_fusion/comparison.csv` and per-method/per-scenario traces.

## First exploratory 2 A experiment

| Scenario | Five-evidence attack-window alarm fraction |
|---|---:|
| Clean | 0/152 clean sample alarms |
| +5 percentage-point SOC spoofing | 0/70 |
| -5 percentage-point SOC spoofing | 0/70 |
| +5 pp SOC drift | 0/70 |
| Fixed replay | 57/70 (81.4%) |
| Eight-step rolling replay | 0/70 |
| 3-minute delay | 17/70 (24.3%) |

These numbers are from a previously examined laboratory profile. They demonstrate **functional integration** and **serious missed-attack limitations**, not superior detection. No equal-FAR or independent-cell comparison has been established. Single scenario/trace observations are not statistical confidence bounds.

## Next Box 2 decisions

1. Preserve the unchanged original global threshold and two-sided SOC CUSUM as explicit comparators.
2. Audit evidence-channel activation for missed spoof/rolling-replay and inspect clean operating-condition sensitivity. Do **not** retune against the same held-out samples.
3. Finalize Box 2 interfaces to Box 3 before implementation of trust-control actions.
