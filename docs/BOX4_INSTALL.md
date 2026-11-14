# Box 4 installation

Extract ZIP **directly into the existing repository root** (where `run_box3.py` is located).

```powershell
Expand-Archive -Path "$HOME\Downloads\BESS_BOX4_EVALUATION_ADDON.zip" -DestinationPath "." -Force
Test-Path .\run_box4.py
Test-Path .\tests\test_box4.py
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
.\.venv\Scripts\python.exe run_box4.py --traces
```

The patch also updates the existing `src/bess/box2/attacks.py` to fix a previously undetected parsing bug with `spoof_p2` and updates `tests/test_box2_attacks.py`. It does **not** change any detectors or Box 3 policies.

Outputs in `results\box4`: `clean_profile_gate.csv`, `detection_per_scenario.csv`, `event_detection_summary.csv`, `signed_asymmetry.csv`, `policy_per_scenario.csv`, `research_readiness_gates.csv`, `evaluation_manifest.json`, figures, and optional `traces\`.

After reviewing the outputs:

```powershell
git add run_box4.py src/bess/box4/ src/bess/box2/attacks.py tests/test_box2_attacks.py tests/test_box4.py docs/BOX4_INSTALL.md docs/BOX4_RESEARCH_REVIEW.md
git commit -m "Add full Box 4 evaluation and signed attack generator regression fix"
git push origin main
```

Do not report observed event hits as successful detection without checking clean-window hits; do not call illustrative kWh the power-plant's actual curtailed energy.
