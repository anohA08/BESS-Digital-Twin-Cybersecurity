# Box 2 — Frozen channel-level diagnostics and ablation

## Purpose
Examine the previously validated five-evidence detector *without tuning* or refitting its thresholds. The original source-only calibration, five evidence channels, unnormalized weights, `fusion_score > 3` abnormal condition, and three-consecutive-sample persistence are unchanged. Ground truth is used only to summarize outcomes.

## Inputs
Existing `run_box2_fusion.py`, `src/bess/box2/`, and Box 1 code from the prior add-ons. No additional dataset or package required.

## Execution
From the repository root in PowerShell:

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
.\.venv\Scripts\python.exe run_box2_diagnostics.py --profile 2A
```

Optional: run with `--profile 1A` or `--profile 1.5A` and distinct output folders, e.g. `--out results/box2_diagnostics_1A`.

## Files produced
- `channel_summary.csv`: for each channel and scenario, strong/weak activation counts in clean and attacked windows
- `ablation_summary.csv`: original alarm counts and counterfactual one-channel-removed alarm counts
- `evidence_traces.csv`: sample-level evidence scores, original fused classifications, and evaluation-only labels
- `channel_activation.png/.svg` and `ablation_alarm_counts.png/.svg`

## Observations from 2A executed analysis (70-sample attack windows)
- +5 pp SOC spoof: 0/70 strict fusion alarms; physics strong evidence on 4/70; synchronization strong on 0/70.
- -5 pp SOC spoof: synchronization evidence is **2/2** on all 70 attack samples, but strict fusion alarms remain **0/70**; the fusion rule requires a score **strictly greater than 3** for three consecutive samples. A single strong channel cannot independently trigger ABNORMAL.
- Fixed replay: 57/70 strict alarms. Removing physics or synchronization evidence decreases to 37/70; removing temporal evidence decreases to 56/70; removing freshness or voltage leaves 57/70. These are *counterfactual* ablations and not evidence of additional attack detection.
- Rolling replay: 0/70 alarms; only 2/70 strong physics evidence.
- 3-minute delay: 17/70 alarms; removing freshness or synchronization yields 0/70 alarms, though both score channels can be dependent on related timing and SOC phenomena.
- Clean 2A: 0/152 strict alarms, but some channels activate individually. This must not be generalized to unseen cells.
- Across 1A, 1.5A, 2A, fixed replay strict alarms were 14/70, 30/70, 57/70; all six signed spoof scenarios in this diagnostic set had 0/70 strict alarms for the five-evidence method. Delay had 0/70, 0/70, 17/70.

## Important limitations
1. The attack variants are laboratory SOC-report surrogates and simulated replay/delay manipulation; they are not recorded cyber intrusions.
2. Each current profile is from the same laboratory battery system. Not a multi-cell validation.
3. All analyses are retrospective and reuse previously investigated profiles.
4. The original detector score is ordinal, **not** a calibrated attack probability.
5. Source-only calibration transfers between current profiles; therefore zero clean alarms in these runs do not imply a distribution-free bound.
6. One-channel removal is a **post-score** ablation at unchanged weights and thresholds, not a retrained optimal detector.
7. These results diagnose fusion behavior and should not be called a new cybersecurity algorithm or improved detection performance.

## Scientific decision
Box 2 implementation operates and can be frozen for Box 3 integration. The five-evidence detector is not sufficiently sensitive to the tested SOC-report spoofing and rolling replay to claim broad detection reliability. No automatic retuning will be performed on these test profiles.
