# Box 4: paper-oriented evaluation of the *frozen* battery-cybersecurity workflow

## What was inspected, not just remembered

- `BESS_Digital_Twin_reporisatory (2).zip`, especially `Box4_Standalone_Evaluation/box4_metrics.py`, its README, and its demo runner. That prior evaluator included binary confusion metrics, attack-event delay, reference-SOC discrepancy, advisory mode transitions, and paired ablation. Its example Box 3 observations were explicitly synthetic.
- Earlier focused retrospective report `BESS_FINAL_FOCUSED_ANALYSIS/FINAL_DECISION_REPORT.md`: 12 discharge sessions (four at each of three currents) **one physical battery**; source-only SOC-conditioned threshold diagnostic improved SOC-only clean sample FAR but *joint* voltage-or-SOC method still missed a 5% clean FAR target. It also flagged that the physical ECM parameters were derived using material from the same lab repository. Thus this study cannot claim independent physics-model validation.
- Rebuilt current project Box 1–3 scripts and actual three-profile replay outputs. This Box 4 add-on does not import or silently substitute old demo scores.

## Current protocol

1. Evaluate each of three nominal current profiles `1A`, `1.5A`, `2A` in turn. All detection calibrations use the **other two clean current profiles only**. This is **leave-one-current-profile-out threshold calibration**, *not independent battery validation* and *not* a guarantee of no prior model-data overlap.
2. Run all original and added scenario generators, including signed ±2/±5 percentage-point SOC manipulations, 5/10/15/20 percentage-point positive manipulation, gradual drift, fixed/rolling replay, and packet-age delay. A single deterministic 70-sample attack window is used in each case; repetitions across currents are *not independent trials*.
3. For each target and scenario, run unchanged global threshold, SOC CUSUM, and five-evidence fusion baselines. Compare injection window with the same profile's *separately executed normal run*; account explicitly for alarms that would have occurred without the attack.
4. Generate sample confusion and event metrics; clean-profile false alarms; pairwise excess alarms; event-hit versus **new** event-hit; first alarm delay *within attack*; signed response asymmetry and clean alert episodes.
5. Evaluate unchanged Box 3 and its previously created confirmed-only shadow using the same frozen five-evidence decisions. The only operational metrics are **advisory power deviations**, SAFE/CAUTIOUS counts and mode switching. The example 60-kW command is not measured dispatch.
6. Keep post-hoc publication-readiness gates clearly separate from scientific claims. Do not use current results to choose new cutoffs and then claim prospective calibration or matched false alarm comparisons.

## Why sample detection rate alone is misleading

- A sequential method can alarm throughout clean operating segments and still obtain near-perfect `attack_event_hit` by coincidence. `new_event_hit` is true only if the attacked replay has a hit **and** its paired normal replay does not hit within the same injection window. It is a conservative counterfactual measure.
- `clean_far` is the fraction of *clean samples* alerted. It is not a probabilistic bound, population false-positive rate, or false-alert-events-per-hour.
- First detection delay is `null` for a missed event; do not replace it with zero or exclude misses without stating the denominator.
- Multiple samples within a battery discharge trace are highly correlated. Three profiles of one battery do not support population confidence intervals.
- The attack labels are evaluation metadata. Confirmed policy decisions never see them.

## Critical findings from initial execution

- Five-evidence has zero clean alarms in three selected target recordings, but zero attack-window hits across *all* SOC-spoofing variants, including +20 pp. Its more reliable fixed replay response does not establish general robustness.
- SOC CUSUM produces substantial clean alarms in all profiles. Its raw event detection count is highly confounded with clean-window alarms.
- Global residual threshold fails the 5% descriptive clean FAR gate on 1 A and 2 A in the current three-profile replay.
- Box 3 has costly clean-mode interventions under the legacy policy, while a confirmed-only policy misses protection of unconfirmed spoof cases. Neither is a physically validated control strategy.
- Positive +2 pp attack generation contained a parsing bug (`spoof_p2` incorrectly splitting at the first 'p' of 'spoof'). Fixed with `removeprefix` and tested. This is a bug fix, not new scientific methodology.

## High-potential next-method directions (NOT implemented here)

### Priority A: bias-aware, sign-sensitive **causal** innovations

Old retrospective work showed signed residual asymmetry and SOC-dependent calibration effects. A strong prospective candidate would explicitly estimate source-only time/SOC-conditioned innovation bias with one-sided statistical monitors; use block/episode-level calibration against clean recordings; compare at matched *achieved* held-out false-alarm constraints. Existing retrospective conditioned *joint* threshold failed the 5% goal; don't quietly promote it as a successful model. Need data from independent battery cells, independent BMS SOC, and separated model-fitting/calibration/test folds.

### Priority B: dynamic watermarking / active challenge-response for replay

True active challenge-response injects a small, recorded excitation into an actuator and verifies the unpredictable physical response. It requires a controllable physics loop and safety constraints, which the static laboratory discharge profiles do not provide. Offline fabrication of challenges or a fake response cannot validate it.

### Priority C: state-estimator uncertainty / prediction set monitoring

Confidence sequences, innovation ellipsoids, conformal/prediction intervals or unknown-input observers are plausible, but assumptions about dependent residuals, physically trusted measurements, and actual coverage must be tested. Do not claim mathematical coverage from a naïve sample quantile of correlated battery data.

### Priority D: safety-aware response with *measured* objective

Risk-aware escalation should use confidence and independent physical safety limits, and compare actual operational cost and voltage/SOC violation against a validated battery and grid plant. The present advisory replay has no such proof.

## Relevant research, not claims of novelty

- O'Brien, Trevizan, Rao, **NAPS 2021**, EKF+CUSUM: https://doi.org/10.1109/NAPS52732.2021.9654567
- Sequential FDIA data restoration, **Journal of Energy Storage 2024**: https://doi.org/10.1016/j.est.2024.113248
- Resource-efficient SOC/SOH co-monitoring with attack detection, **IEEE Transactions on Smart Grid 2025**: https://doi.org/10.1109/TSG.2025.3525558
- Huang et al., chaotic time/frequency hopping for BESS FDIA, **Journal of Energy Storage 2026**: https://doi.org/10.1016/j.est.2026.121934
- Li et al., resilient switching for DC BESS, **Journal of Energy Storage 2026**: https://doi.org/10.1016/j.est.2026.123349
- Ghosh et al., dynamic watermark and robust state estimation, **IEEE Transactions on Smart Grid 2026**: https://doi.org/10.1109/TSG.2026.3711153
- Shekhar & Ramdas, sequential change detection via confidence sequences, **ICML 2024**: https://proceedings.mlr.press/v235/shekhar24a.html
- A hybrid physics-informed digital twin EMS for attack detection/reconstruction, **Energy Conversion and Management 2026**: https://doi.org/10.1016/j.enconman.2025.120728

**Verdict:** a repeatable **diagnostic evaluation benchmark**, not yet a strong Q1 submission with demonstrated attack-resilient control. Additional independent datasets and a detection method that closes the signed/stealthy attack gap are critical.
