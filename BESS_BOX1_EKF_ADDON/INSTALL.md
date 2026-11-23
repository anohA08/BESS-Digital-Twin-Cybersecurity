# Box 1 EKF diagnostic add-on

Copy `run_box1_ekf.py`, `tests/test_box1_ekf_diagnostic.py`, and `docs/BOX1_EKF_VALIDATION_NOTES.md` to the corresponding locations in your **existing** BESS_REBUILD_STARTER checkout. No original file must be replaced.

From the VS Code PowerShell terminal in the repository root:

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
.\.venv\Scripts\python.exe run_box1_ekf.py --profile all
```

Inspect `results/box1_ekf/metrics.csv` and the three `voltage_*.png` files. These are exploratory model diagnostics, not physical SOC validation.

Only commit source files and docs once you have reviewed them:

```powershell
git add run_box1_ekf.py tests/test_box1_ekf_diagnostic.py docs/BOX1_EKF_VALIDATION_NOTES.md
git commit -m "Add Box 1 EKF prior-prediction diagnostic and tests"
git push
```
