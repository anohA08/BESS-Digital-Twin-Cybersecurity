# Box 2 attack-family migration: exact source and scope

Source inspected: uploaded `BESS_Digital_Twin_reporisatory (2).zip`, especially `Box2_Attack_Validation/BESS_Box1_Box2_RealData_Baseline/run_box2_attack_validation.py` and its `ATTACK_VALIDATION_README.md`.

Three families from old repo: (1) SOC sensor spoofing; (2) fixed or rolling replay of reported SOC and terminal voltage; (3) communication delay. Original scenario names: `normal`, `spoof_5`, `spoof_10`, `spoof_15`, `spoof_20`, `fixed_replay`, `rolling_replay`, `delay_3min`. Default attack indices 40..109, rolling lag 8 observations. Spoof offsets are percentage **points**, clipped to [0,100]. Replay refreshes source timestamps and is not authenticated packet replay. Delay changes receive timestamp by 3 minutes; it is not a simulated network queue.

Added (NOT in legacy validated scenario catalogue): `spoof_m5`, `spoof_m2`, `spoof_p2`, `spoof_ramp_p5`. These are exploratory extensions for signed low-amplitude effects.

The code uses the Box 1 `run_replay()` output, whose recorded SOC is an **unverified surrogate** for a reported BMS SOC channel. The attack changes that telemetry, not Box 1's independent twin. Truth labels are used only for metrics. Every scenario is an independent replay and detector history resets.

This add-on currently contains **two simple diagnostic baselines**: global source-calibrated SOC/voltage threshold with timestamp-age evidence and 3-sample persistence; and SOC-only two-sided CUSUM with source-derived mean/scale. Neither is calibrated for guaranteed 5% target FAR. They are NOT a replacement for the old five-evidence Box2 pipeline. The next Box 2 step is to port and unit-test the five actual legacy evidence channels, fusion, persistence, classifier and adapter while resolving configuration provenance. Do not claim the old 3 attacks were independently validated on unseen cells. The tests here are functional checks, not validation.

## Install / Windows PowerShell

Extract to your project root, preserving `src`, `tests`, `docs`, and `run_box2.py`. If extraction creates an extra `BESS_BOX2_ATTACK_ADDON` directory, copy its contents **into the root** instead of running it nested.

```powershell
Test-Path .\run_box2.py
Test-Path .\src\bess\box2\attacks.py
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
.\.venv\Scripts\python.exe run_box2.py --profile 2A
```

Expected new output: `results/box2/scenario_summary.csv`, per-scenario CSV and `scenario_alarm_fraction.png`. `git add run_box2.py src/bess/box2 tests/test_box2_attacks.py docs/BOX2_ATTACK_MIGRATION.md` only after verifying the code.
