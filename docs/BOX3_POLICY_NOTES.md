# Box 3 — Trust Policy and Advisory Mitigation

- Core implementation ported unchanged from historical `BESS_ClosedLoop_Framework_v0_2/Box3_Standalone_Prototype/box3/core.py`.
- Five-evidence `classification` and `attack_assessment` are mapped explicitly to the legacy Box 3 inputs. No labels or recorded reference SOC pass to the policy.
- Trust score **heuristic**, NOT an attack probability. SAFE mode is a policy reaction, NOT evidence that Box 2 detected an attack.
- The replay uses a constant illustrative power request of 60 kW and shows absolute advisory power deviation. **No physical plant is actuated**, so kWh values are neither measured energy curtailment nor avoided safety exposure.
- Data: three previously examined current profiles from one laboratory battery; SOC channel is a laboratory proxy.
- Existing Box 2 detectors and thresholds are unchanged. Box 3 is a downstream, descriptive policy prototype.
- Tests cover state bounds, hysteresis, suspected vs confirmed distinction, truth-label independence, and deterministic replay.
