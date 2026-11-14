# Research phase: signed increment pilot (exploratory, NOT independently validated)

## Reproducible context

- Frozen baseline: GitHub `main` at `bca1754`, user's local checkpoint. This add-on does **not** modify existing Box 1–4.
- Reconstructed environment from the prior delivered starter and additive ZIP archives, **not a fresh GitHub clone** (network GitHub unavailable in the execution container). Confirm local baseline test suite before interpreting output.
- Three profiles (1 A, 1.5 A, 2 A) derive from the **same battery system**, not three cells; sample time is one minute.
- SOC is reconstructed/recorded laboratory surrogate, **not a cryptographically authenticated BMS SOC channel**. Synthetic attack insertions are not real attacks.
- Design and parameter exploration used knowledge of all three target profiles, including residual increments. Therefore leave-one-current-out *calibration* is **not** honest independent method-selection validation. The `guard_multiplier=1.5` is a heuristic, not a statistical guarantee; it was selected in this exploratory phase.

## Candidate

Define `r_t = SOC_reported_t - SOC_twin_t`. The signed increment is `Δr_t = r_t - r_(t-1)`.

For clean source recordings (each of the **other two** current profiles), derive sign-specific source extremes:

`U = 1.5 × max(0.01, max_source Δr_t)`;
`L = 1.5 × max(0.01, max_source(-Δr_t))`.

Flag an **upward** onset if `Δr_t > U`, or a **downward** onset if `Δr_t < -L`. Keep an alarm active for three samples after onset. Never use attack truth or future target observations in detection. This is **standard first-difference change-point screening** with a conservative envelope—not a novel detector.

## Pilot results

| Category | Candidate new event hits (three profiles/category) | Interpretation |
|---|---:|---|
| +2 pp | 3/3 | Abrupt positive change |
| −2 pp | 3/3 | Abrupt negative change |
| +5 pp | 3/3 | Abrupt positive change |
| −5 pp | 3/3 | Abrupt negative change |
| Gradual +5 pp drift | 0/3 | Failure: incremental slope is under source limits |
| Fixed replay | 0/3 | Failure |
| Eight-observation rolling replay | 3/3 | Onset jump in these traces |
| 3-minute packet-age delay | 0/3 | No timestamp channel in candidate |

Candidate clean sample false alarms on **unmodified target recordings**: 0/152 on each of 1 A, 1.5 A and 2 A, **but this is not a FAR guarantee**. A benign SOC reporting reset of 2 pp causes a false event by construction; see test `test_benign_soc_reporting_reset_is_ambiguous`.

All event counts are dependent tests on three runs of **one battery**. Repeated attack injections on the same signal must not be treated as independent experimental replicates.

## Research decision

This candidate is a useful **complimentary feature** or comparator for sudden telemetry discontinuities. It is not an acceptable final cybersecurity solution because a benign measurement reset is observationally indistinguishable from a spoofing step without extra trusted evidence, and low-slope attacks evade it.

Potential high-impact follow-up: (1) independent-cell external validation; (2) authentic SOC/time channels or a trusted current + physical measurement chain; (3) separate drift/slope statistics with uncertainty-aware calibration; (4) same false-alarm constraints and matched assumptions; (5) identify when attackers and benign drift are unidentifiable from available observables; (6) only then consider mitigation policy improvement on a validated plant. No unverified claims of waterproof detection or Q1 novelty.

## Recent competing papers (validate exact method details before claims of difference)

- Huang et al. (2026), *Journal of Energy Storage*, chaotic time/frequency hopping for low-amplitude SOC FDIA: https://doi.org/10.1016/j.est.2026.121934
- He et al. (2026), *Computers & Security*, unknown-input EKF for resilient SOC estimation and anomaly detection: https://doi.org/10.1016/j.cose.2026.105205
- Li et al. (2026), *Journal of Energy Storage*, resilient switching control in BESS: https://doi.org/10.1016/j.est.2026.123349

These papers already address some of the broader problem. A first-difference alarm alone is not a publishable contribution.

## How to run

From project root: `python -m unittest discover -s tests -v` and then `python run_research_candidate.py --traces`.

The experiment writes `results/research_signed_increment` with clean profile metrics, each attack scenario and baseline paired comparisons, source-only calibration limits, event summary, traces, and machine-readable caveats. Do **not** replace Box 2 fusion or let Box 3 trust policy consume this exploratory alarm until an independently calibrated and validated policy bridge exists.
