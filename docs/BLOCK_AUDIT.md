# Old repository four-box audit

Source: uploaded `BESS_Digital_Twin_reporisatory (2).zip`. This audit is a static source review, not a claim that every module was retested here.

| Block | Reusable old implementation | Problems and change | New project policy |
|---|---|---|---|
| 1 — Physical twin | `BESS_ClosedLoop_Framework_v0_2/BESS_Box1_Box2_RealData_Baseline/{battery.py,digital_twin.py,ekf.py,data/processed}` | Workbook/lookup calibration provenance; initial SOC and availability of reported-SOC distinct; ECM is open-loop in main final analysis | One ECM, explicit input units and initialization, independent evidence validation; EKF as optional estimator |
| 2 — Cyber detection | `.../box2/{sync_evidence,physics_evidence,temporal_evidence,voltage_evidence,freshness_evidence,evidence_fusion,persistence,attack_classifier}.py` plus `box2_pipeline.py` | Multiple parallel prototypes; original detector missed low-amplitude attacks; fixed-prefix BC-MED falsely alarmed in 329/363 clean samples | One documented baseline and one SOC-conditioned comparator; combine signals only when source-calibrated and evaluated at realized FAR |
| 3 — Trust / response | `.../Box3_Standalone_Prototype/box3/core.py` and `.../grid_plant.py` | Trust heuristic is not an attack probability; SAFE operation is not strict attack detection; 2 MWh grid model illustrative | Preserve separate policy prototype and use paired curtailment consequence metrics; do not claim verified safety gains |
| 4 — Evaluation | `.../Box4_Standalone_Evaluation/box4_metrics.py`, previous `test_*`, `plot_*` | Some metrics sample-wise correlated; sessions same cell; simulation mixed with measured data | Repeat-session grouping, explicit attack channel, denominators, immutable thresholds and reproducible figures |

Previous finalized exploratory main results are in the old research packages; the new repository must **not** claim these were independently validated. Frozen BC-MED is a **failed reference candidate**, not the selected method.

## Model selection (deliberately bounded)
- ECM: primary open-loop physical predictor.
- EKF: optional reproducible state-estimation comparator, only with valid initialization and leakage controls.
- Global residual threshold: interpretable baseline.
- SOC-conditioned threshold: focal method for calibration study.
- Two-sided CUSUM: relevant sequential baseline **if implemented and evaluated**; do not claim it based on mathematical derivation alone.
- Original evidence-fusion and trust-policy algorithms: optional supporting experiments, not automatically scientific contributions.

Do not add deep learning, RL or GNN without a predefined measurement gap and adequate independent data.
