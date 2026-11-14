# Research gate: observability and attack-intent identifiability

**Decision (2026-11-14): Measurement identifiability PASS; gradual-FDIA superiority HOLD.**

## Why this gate exists
The three related recordings (1 A, 1.5 A, 2 A) belong to one physical battery. `soc_recorded_for_evaluation_only_pct` is a dataset-derived evaluation surrogate, not verified live/authenticated BMS SOC. Our attack generator modifies SOC telemetry alone for spoofing, leaving measured voltage, current, and twin state untouched. The negative multi-window experiment produced 11/152 clean alarms on 2 A and 0/3 detections of each tested +5 and -5 pp gradual ramp.

The previous repository's Phase 18 counterexample already established a separate mathematical fact: with an affine OCV curve and unconstrained constant voltage bias, offset-invariant voltage signatures cannot identify a constant SOC shift. The present gate **does not claim a new theorem**; it adds a concrete comparison aligned to our new repository's measurements and attack injections.

## Constructive indistinguishability
Write the observable sequence as `Y = (time, current, voltage, reported_SOC, twin_SOC, model_voltage, source_timestamp, receive_timestamp)`. Let `S(t)` be the pre-injection reported SOC and `a(t)` be a signed step or ramp. Consider:

- **FDIA hypothesis:** attacker changes the report to `S(t)+a(t)`.
- **Benign hypothesis:** a legitimate but *unauthenticated* SOC reporting/offset correction generates `S(t)+a(t)`.

All other observed measurements and timestamps are kept identical in the project's SOC-only injection model. Consequently `Y_FDIA == Y_benign` sample by sample. Any deterministic detector using only `Y` must give identical outputs. A randomized detector has the same output distribution if its independent randomness has the same distribution. It cannot distinguish attack *cause* from these observations; it may still detect an anomalous *measurement*. This statement is limited to the specified benign and malicious hypotheses and sensors, not an impossibility for systems with authenticated provenance, distinct hardware channels, validated electrodynamics or controlled excitation.

## Oracle anchor sensitivity (not field validation)
We separately compare the modified reported SOC with the dataset's `soc_recorded_for_evaluation_only_pct`. For each hypothesized absolute reference-error bound `u`, flag `abs(reported_SOC-reference_SOC)>u` over 70 injected samples. This reference is **not a deployable independent SOC sensor**. No statistical FAR guarantee follows from the hypothetical bounds. Even a genuine trusted SOC anchor might prove mismatch but would **not** distinguish malicious manipulation from a benign report reset unless provenance/maintenance context is trusted.

The outputs report, for each profile, sign and bound, the number of oracle-reference inconsistencies and whether physical channels changed. These are structural audit measurements, **not detection rates**, and each of the three profiles belongs to one battery.

## Decision gates for a new method
1. **Trusted source:** identify an authenticated independent state/measurement (e.g., trusted charge-integrated SOC with independently bounded current and initial SOC error, authenticated maintenance log/event record, or active challenge-response measurement).
2. **Assumptions:** derive independently justified error bounds including sensor bias, time alignment, temperature, capacity drift, current integration and model uncertainty. Dataset SOC surrogate cannot be silently upgraded to ground truth.
3. **Threat model:** state which channels attacker can compromise; whether a legitimate report reset can be authenticated; and whether simultaneous voltage/current spoofing is allowed.
4. **Evaluation:** test independent battery cells with frozen tuning, matched false-alarm constraints, low-amplitude signed steps and ramps, benign resets, replay, delays, and disturbances. Count **independent cells**, not injected windows, as independent physical replicates.
5. **Box 3:** measure clean intervention costs; do not claim physical safety improvement until a separately validated closed-loop physical plant is available.

The existing signed-increment candidate remains an exploratory abrupt-change detector, not a verified FDIA-intent classifier. The failed multi-window approach remains recorded as a negative result.

## Run
```
python -m unittest discover -s tests -v
python run_research_identifiability.py
```
Expected full suite in the assembled build: 79 tests. Outputs: `results/research_identifiability/observability_counterexamples.csv` and `gate.json`.
