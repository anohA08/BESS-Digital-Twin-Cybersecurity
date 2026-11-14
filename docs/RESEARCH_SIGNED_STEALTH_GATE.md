# Signed stealth region research gate — exploratory result

## Scientific question
Does the same-magnitude positive and negative reported-SOC offset have asymmetric visibility to a **fixed, source-only calibrated SOC residual threshold** when the digital twin already has state-dependent bias?

## Protocol
- Source profiles: the other two current profiles (one physical battery); target excluded from threshold calibration.
- Frozen baseline: `bess.box2.detectors.calibrate_global` and `detect_threshold`, unmodified. Nominal alpha=0.05 is an empirical source quantile setting, **not** a test-set FAR guarantee.
- Attack injection: nominal signed offsets ±2, ±5, ±10 percentage points, samples 40–109, with SOC bounded to 0–100%.
- Keep deterministic SOC-only analytic detector separate from the full threshold detector, which additionally includes voltage, freshness, persistence and preexisting clean alarms.
- Report per-row non-alarm geometry and paired full detector differences. This is a model-derived **non-alarm interval**, not guaranteed attack stealth across noise or other channels.

## Model
Let `b_t = reported_clean_SOC_t - twin_SOC_t` and `a_t` be the *effective* injected change after clipping; residual is `r_t=b_t+a_t`. For strictly triggering `abs(r_t)>tau`, the SOC component does NOT alarm iff `-tau-b_t <= a_t <= tau-b_t`. Threshold is determined using source-only clean data; `b_t` from the held-out target is used in **retrospective characterization**, not to set or run the detector. The algebra itself is standard, not a new theorem.

## Key measured descriptive findings
- 2 A: clean residual median during injected window approximately **−5.30 pp**, source threshold **6.46 pp**. At +5 pp, all 70 attacked samples are SOC-component non-alarms; at −5 pp, none are non-alarms.
- 1 A: median clean residual approximately **+1.29 pp**, source threshold **6.99 pp**; +5 pp has 45/70 SOC-component non-alarms, −5 pp has 70/70.
- 1.5 A: median clean residual approximately **−1.70 pp**, source threshold **7.03 pp**; +5 pp has 66/70 non-alarms, −5 pp 39/70.
- Full-detector event-hit results must be interpreted separately. For instance on 2 A, the clean baseline already alarms during part of the attack window (20/70 samples). The `new_event_hit` definition is false whenever the paired clean has **any** alarm in the attack window; this does not imply no attack-induced alarm increase. Inspect `paired_excess_full_alarm_fraction`.

## Limitations
1. Three related profiles represent one battery cell and are not independent battery validations.
2. Reported SOC is a dataset-based surrogate rather than authenticated BMS SOC.
3. Injections are post-hoc and do not model compromised physical voltage/current sensors or closed-loop effects.
4. Retrospective characterization has been informed by these same profile data; exploratory, not a locked independent holdout study.
5. The algebraic non-alarm interval is SOC-only and deterministic; it does not establish stochastic false alarm / detection guarantees.
6. No malicious-intent claim is possible when benign SOC report corrections can reproduce the same observed telemetry.
7. This is a diagnostic and mechanism demonstration, **not a newly calibrated detector**; no Q1 novelty claim yet.

## Scientific decision
Mechanism demonstrable: **PASS (descriptive)**. Controlled FAR: **HOLD**. Independent cell validation: **HOLD**. Detecting gradual spoofing: **HOLD**. SOC channel provenance: **HOLD**. Physical mitigation benefit: **NOT TESTED**.

## Original repository connection
The older project already examined SOC-conditioned residual variability and a structural bias-induced asymmetric non-alarm interval. This add-on consolidates that observation in the rebuilt Box 4 pipeline with frozen source-only calibration, per-sample diagnostic outputs, matched signed offsets and paired full-detector outcomes. It should not be represented as the first discovery of residual-bias stealth in the literature.

## Relevant prior art
- Zhuang & Liang, *IEEE Transactions on Smart Grid* (2020), sequential FDIA on BESS SOC estimation, DOI: 10.1109/TSG.2020.3042926.
- Trevizan et al., Sandia/IEEE PES General Meeting (2024), sensor encoding for stealth battery SOC FDIA, DOI: 10.2172/2586031.
- O'Brien et al., *IEEE Open Access Journal of Power and Energy* (2024), signed bias identification in attacked battery sensors, described by Sandia (2025).
- Huang et al., *Journal of Energy Storage* (2026), chaotic TH/FH signal coding for low-amplitude SOC FDIA, DOI: 10.1016/j.est.2026.121934.

## Reproduce
```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
.\.venv\Scripts\python.exe run_research_stealth_regions.py
```
Outputs go to `results/research_stealth_regions/`.
