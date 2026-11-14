# Source-only quadratic SOC-bias transfer — negative result

## Status
Rejected as a final detector. Exploratory comparison using **three profiles of one physical battery** and an SOC surrogate, not authenticated BMS SOC.

## Frozen specification
Model residual `r = telemetry_soc_pct - soc_estimated_pct`. Fit a quadratic to clean **source-only** residual versus digital-twin SOC: `z=(SOC_est-50)/50`, `b_hat=beta0+beta1*z+beta2*z^2`, with ridge penalty 0.01 on the non-intercept coefficients. Calibrate an absolute residual 95%-quantile with `method=higher` using clean sources. The baseline uses the exact same source profiles, persistence=3, and absolute 95%-quantile on uncorrected residual. No target-data threshold tuning.

## Clean false alarm results

| Profile | Uncorrected SOC-only | Bias-corrected SOC-only |
|---|---:|---:|
| 1 A | 0/152 | 7/152 (4.61%) |
| 1.5 A | 0/152 | 3/152 (1.97%) |
| 2 A | 20/152 (13.16%) | **38/152 (25.00%)** |

The prespecified 5% per-profile descriptive criterion **fails** for the proposed method. Do not promote or tune on the same target run.

## Paired event sensitivity (3 profile-specific simulations per scenario)

| Scenario | Uncorrected new events | Bias-corrected new events |
|---|---:|---:|
| +2 pp | 0/3 | 2/3 |
| -2 pp | 1/3 | 2/3 |
| +5 pp | 1/3 | 3/3 |
| -5 pp | 1/3 | 2/3 |
| +10 pp | 2/3 | 3/3 |
| +5 pp gradual drift | 0/3 | 3/3 |
| Fixed replay | 2/3 | 3/3 |
| Rolling replay | 2/3 | 3/3 |
| Delay | 0/3 | 0/3 |

**Do not claim better overall detection:** false alarms are not matched in the target, and the comparison is the SOC-threshold component (not the full fused five-channel monitor). Source-only calibration does not yield statistical error guarantees, especially with a single cell and correlated samples.

## Scientific conclusion
The state-dependent bias hypothesis is supported as a descriptive failure mode. A degree-2 correction does not reliably transfer among available currents. Priority should shift to identifying source/target shift and obtaining new independent cells, reliable BMS SOC or independently bounded anchors; do not keep targeting already-seen profiles to select polynomial order, window length, or threshold.

## Provenance
The three recorded sessions come from one physical battery; synthetic SOC-only injected attacks change reported telemetry, not the physical plant. Both attack and benign SOC-report modifications can produce the same visible telemetry. Evaluation is not evidence of malicious intent or physical mitigation safety.
