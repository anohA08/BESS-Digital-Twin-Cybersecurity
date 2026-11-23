# Step-by-step build gates

**Box 1**: measured current+voltage input schema, copied ECM, test all three current profiles, meaningful voltage-residual plots, explicit assumed SOC, no reference-SOC oracle. Gate: all tests pass and replay generates CSV+PNG.

**Box 2**: import only needed previous evidence-channel files; global threshold vs SOC-conditioned comparator; sign-aware offset model; source-only leave-one-session-out calibration; CUSUM baseline only if empirically tested. Gate: matched test records with clean FAR and attack-alarm fractions; no retuning final held-out sessions.

**Box 3**: import bounded trust module + plant only after measurement/trust contract is stable; a safety 'benefit' requires independent consequence evidence. Gate: paired counterfactual dispatch-energy table; clean false-alarm cost reported.

**Box 4**: import existing metrics, produce run-level CSV and 6 selected figures from the exact underlying data. Gate: one-command reproducibility, figure-data audit, clear limitations.

Recommended cadence: Box 1 → Box 2 → Box 3 → Box 4. A 1–2-day target is a prioritization constraint, not a promise of background delivery or scientific validation.
