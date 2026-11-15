# Supplemental grid-scale closed-loop BESS case study

**Status: illustrative simulation, not field or independent-cell validation.** This module is isolated from the twelve-session retrospective manuscript. It does not change Box 1–4 source or any historical numerical claim.

## Architecture

- Plant: 2,000 kWh energy balance with 1,000 kW power limit, 20–90% physical SOC interlocks, initial 60% SOC, 95% direction-specific efficiency, one-minute steps.
- Measurements: a BMS-like SOC report constructed by the evaluation harness, and an illustrative linear SOC–voltage proxy. No pack-level cell equivalent circuit is calibrated or assumed to represent grid-scale electrical dynamics.
- Monitoring: the **unchanged** five-evidence scoring/fusion/persistence algorithm from `bess.box2.five_evidence`, wrapped in an online streaming adapter. A parity test checks sample-for-sample equivalence with the batch method on clean synthetic data.
- Calibration: two independently generated *synthetic clean* source traces, not the 12 laboratory sessions and not the target run. **Calibration has not been validated on independent physical grid-scale measurements.**
- Response: unchanged Box 3 coordinator and a confirmed-only shadow policy. Unprotected operation serves as a control.
- Closed loop: output of policy -> power command -> physical plant -> next SOC report/voltage. The digital twin advances using **executed** power from an assumed trustworthy meter; the assumption is unverified.
- Attack truth and physical true SOC are available only in the synthetic sensor-generation harness and after-the-fact evaluation; they are not passed to `OnlineFiveEvidence` or `Box3Coordinator`.

## Scenarios

Normal; +5 pp step, -5 pp step, +5 pp ramp over 50 steps; fixed SOC replay; 8-step rolling replay; 3-minute timestamp delay with causal onset. Attack window minute 30 through 89, when enabled. The attacker manipulates the *reported SOC / source timestamp* rather than physical current or voltage.

## Interpretation

`intervention_kwh` is an **absolute difference in requested and advisory power integrated over the simulation**. It is not measured grid revenue loss or avoided damage. `plant_interlock_kwh` measures independent hard-interlock clipping. Physical limit violations are zero by construction because the plant enforces those limits using its private state. That cannot support a claim of safety benefit from cyber detection. Monitoring alarms in normal operation are false alarms in this simulated setting, and the attached results should be reported even when unfavorable.

Do not pool simulation scenarios with the repeated physical discharge sessions and do not incorporate this demonstration into the focused retrospective paper's experimental denominator.

## Run

From the root of the existing rebuilt repository:

```powershell
Expand-Archive -Path "$HOME\Downloads\BESS_GRIDSCALE_CLOSED_LOOP_ADDON.zip" -DestinationPath "." -Force
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
.\.venv\Scripts\python.exe run_gridscale.py
```

Outputs: `results/gridscale/summary.csv`, per-scenario policy traces and `ASSUMPTIONS.json`.

## Source discipline

Only `src/bess/gridscale/`, `run_gridscale.py`, `tests/test_gridscale.py`, and this document are new. There are no modifications to the frozen Box 1–4 code. Existing Box 2 and Box 3 imports are required.
