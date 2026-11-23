# BESS Digital Twin — New Research Implementation

This is a clean **new** repository started by selecting functional components from the older BESS project.
The old repository has **not** been modified. This starter implements only **Box 1** with a measured-voltage replay.

## Windows PowerShell setup

```powershell
py -3.13 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
.\.venv\Scripts\python.exe run_box1.py --profile 1A
```

Run the commands **in the folder containing this README and `run_box1.py`**.

The outputs are under `results/box1/`. The original processed laboratory profiles and model lookup tables were carried over as **local research inputs**. Confirm their licensing and provenance before a public push.

The ECM is copied from the previous repository, apart from package-relative imports. It is an **open-loop model**, not an independently validated physical battery or security detector. The recorded SOC column is evaluation-only; the replay uses a declared assumed SOC (default 100%).

## Research stages

1. Box 1: ECM / EKF and data interface — starter working; EKF validation pending.
2. Box 2: source-only calibration, signed residuals, global/SOC-condition thresholds; standard EKF+CUSUM baseline and optional five-channel legacy evidence — pending.
3. Box 3: bounded trust policy and illustrative dispatch consequences — pending.
4. Box 4: held-out run results, attack contrasts, figures, run-level metrics — pending.

See `docs/BLOCK_AUDIT.md` and `docs/ROADMAP.md` for exact legacy-file mapping and gates.
