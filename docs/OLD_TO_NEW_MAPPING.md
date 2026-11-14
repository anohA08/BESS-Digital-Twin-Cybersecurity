# Source-file mapping and provenance

The starting files in `src/bess/box1/` were extracted from the uploaded older repository:
`BESS_ClosedLoop_Framework_v0_2/BESS_Box1_Box2_RealData_Baseline/`.

`battery.py`, `digital_twin.py`, and `ekf.py` are preserved; `digital_twin.py` and `ekf.py` have only their local imports adapted for the new package. The processed battery lookups and three discharge CSVs are copied from the same source folder. `replay.py`, `run_box1.py`, tests, README and docs are newly created.

No '.git' directory or previous cached output is copied into the new repository.
