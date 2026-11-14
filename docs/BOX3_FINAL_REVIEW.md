# Box 3: literature-informed code review and frozen-policy sensitivity audit

## Executive engineering decision
**Functionality PASS; cybersecurity effectiveness / physical safety NOT VALIDATED.**
The previous Box3 `core.py` matches the legacy `BESS_ClosedLoop_Framework_v0_2/Box3_Standalone_Prototype/box3/core.py` byte-for-byte; this audit leaves it unchanged. Existing Box2 algorithms and thresholds are not modified. The audit adds a *shadow policy* for controlled sensitivity analysis only.

## Four components reviewed
- **TrustManager:** heuristic score with severe and suspected penalties and clean-streak recovery. Not a calibrated probability. It accumulates repeated `ATTACK_SUSPECTED` or `UNEXPLAINED_ANOMALY` classifications; repeated uncertain classifications can initiate SAFE without a strict alarm.
- **RecoveryManager:** NORMAL/CAUTIOUS/SAFE state machine with clean streak, minimum dwell and stepwise de-escalation. Streak and dwell count *samples*, not elapsed seconds; the behavior therefore depends on sampling rate.
- **ResilientEstimator:** sensor contribution is capped at 1 SOC percentage point and eliminated in SAFE mode. This is not a formally verified attack-resilient state estimator; no independent SOC reference establishes whether its corrections help.
- **MitigationController:** SOC limit checks and illustrative power caps (100 kW max, 50% cautious, SAFE=0). Outputs are advisories, not actuator commands. Instantaneous full stops may be inappropriate for real-world grid services; the mode selection must never be represented as a certified protection action.
- **Bridge/evaluation:** explicit classification mapping, no label-dependent policy decisions, per-run reset. The 60 kW request, sample-to-hour intervals and absolute power deviation are illustrative. Attack truth is accessed only AFTER the policy decision for scoring.

## Main failure mode
On the 2 A clean replay, Box2 records **zero strict abnormal alerts**, but Box3 enters SAFE for **55 samples** and causes **57.333333 kWh** of absolute advisory deviation against the illustrative 60 kW request. This is a *policy consequence of unconfirmed classification*, not an FDIA detection result or measured grid curtailment. The same clean scenario at 1 A has 30 SAFE samples and 33.166667 kWh deviation; at 1.5 A, zero. Only one physical battery is represented.

## Shadow-policy ablation
Run two policies on the same precomputed Box2 rows:
- `legacy`: original policy, frozen.
- `confirmed_only`: **counterfactual** maps unconfirmed suspicion/unexplained states to NORMAL before Box3, but preserves `ATTACK_DETECTED` (strict confirmed alerts).

The ablation is diagnostic, **not a recommended or validated replacement**. This policy uses no attack labels at decision time; labels are used strictly to score after decisions.

### 2 A numerical findings
| Scenario | Legacy SAFE / shadow SAFE | Legacy clean-window advisory deviation / shadow (kWh) | Legacy attack-window advisory deviation / shadow (kWh) |
|---|---:|---:|---:|
| Normal | 55 / 0 | 57.333 / 0 | 0 / 0 |
| +5 pp SOC spoof | 0 / 0 | 3 / 0 | 0 / 0 |
| −5 pp SOC spoof | 92 / 0 | 32.5 / 0 | 61.833 / 0 |
| +5 pp SOC ramp | 0 / 0 | 3 / 0 | 0 / 0 |
| Fixed replay | 92 / 68 | 32.5 / 13.5 | 61.833 / 56.167 |
| Rolling replay | 0 / 0 | 1.5 / 0 | 0 / 0 |
| 3-minute delay | 92 / 28 | 32.5 / 1.167 | 61.833 / 28.5 |

**Interpretation:** eliminating unconfirmed-response penalties suppresses clean interventions, but it also eliminates response to the −5 pp spoof, an attack not strictly confirmed by Box2. The cost–coverage tradeoff is not solved by simply ignoring all suspicion. A statistically supported *evidence confidence / consequence-aware response policy* could be useful in later work, but is NOT implemented or proven here.

## Potentially high-impact next improvement (not introduced to frozen controller)
1. Separate `security evidence state` from `operational response state`, with calibrated false-alert evidence, independent physical safety interlocks, and documented fail-safe policy.
2. Measure *false intervention burden* and *attack-window response coverage* jointly, on paired clean/attacked conditions; add a proper battery/grid plant and independent SOC-error/out-of-bounds reference before claiming resilience or avoided damage.
3. Evaluate policies at matched nuisance alarm burdens, cross-session/condition holdouts, and explicit target operating conditions. Do not fit response thresholds to final held-out attack labels.

## Review against published methods and standards
These sources illustrate stronger definitions of **resilient control** than this prototype currently meets, and they are prior work, not borrowed novelty:
1. **O'Brien, Rao & Trevizan (2023), IEEE Transactions on Industry Applications**, input-noise-aware state estimation + CUSUM, https://doi.org/10.1109/TIA.2023.3308548. Highlights the need to validate the upstream detector, not infer success from downstream SAFE behavior.
2. **Kaheni, Usai & Franceschelli (2023), IEEE Transactions on Automation Science and Engineering**, resilient multi-agent BESS optimization under attack, https://doi.org/10.1109/TASE.2023.3310328. Includes a defined optimization/control objective; unlike a heuristic power cap.
3. **Li et al. (2026), Journal of Energy Storage**, resilient switching control for DC microgrid BESS against FDIA, https://doi.org/10.1016/j.est.2026.123349. Focuses on SOC/voltage over-boundary behavior with control design.
4. **Data-driven defense framework for sequential FDIAs in grid-connected BESS (2024), Journal of Energy Storage**, https://doi.org/10.1016/j.est.2024.113248. Investigates detection and measurement restoration; note that this prototype's bounded SOC blending is not comparably validated.
5. **Kharlamova, Træhold & Hashemi (2023), Journal of Energy Storage**, cyberattack detection methods for BESS, https://doi.org/10.1016/j.est.2023.107795. Defines BESS-specific threat and evidence landscape.
6. **NIST SP 800-82 Rev. 3 (2023)**, Guide to Operational Technology Security, https://doi.org/10.6028/NIST.SP.800-82r3. Highlights safety, performance, and reliability constraints for operational control responses.

## Verification and unresolved issues
- Test suite assembled from Box1 + Box2 + Box3 and final audit: **44/44 PASS** (39 existing + five new).
- Exact frozen legacy code retained, including default advisory parameters.
- Per-profile shadow audit runs 1 A / 1.5 A / 2 A. Clean 1 A: 30 SAFE / 33.167 kWh under legacy, 0/0 under shadow; clean 1.5 A: 0/0 both; clean 2 A: 55 SAFE / 57.333 kWh legacy vs 0/0 shadow.
- Scientific blockers for a high-tier *resilient control* claim: no independent physical plant simulation, no independent SOC-error benefit, no stability or safety guarantee, heuristic trust uncalibrated, repeated observations from one battery, and unconfirmed-alert-driven intervention.
- Engineering risks to address before any physical deployment: validate policy configurations and units; harden unknown mode/error handling; duration-based dwell/recovery; power ramp limits; independent BMS interlocks; credible safe fallback under communication loss. **Do not attach this prototype to a physical BESS.**
