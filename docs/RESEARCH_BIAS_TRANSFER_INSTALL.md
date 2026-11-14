# Installation
Extract `BESS_RESEARCH_BIAS_TRANSFER_GATE.zip` to the root of `BESS_REBUILD_STARTER`, not inside an extra directory.

```powershell
Expand-Archive -Path "$HOME\Downloads\BESS_RESEARCH_BIAS_TRANSFER_GATE.zip" -DestinationPath "." -Force
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
.\.venv\Scripts\python.exe run_research_bias_transfer.py
```

Outputs: `results/research_bias_transfer/` (`clean_gate.csv`, `paired_attack_metrics.csv`, `event_summary.csv`, `calibration_coefficients.csv`, `limitations.json`).

The full local test count may differ depending on other add-ons. Verify the new `test_research_bias_transfer` tests pass and final `OK`. This is a **negative result** and must not replace the frozen detectors.

```powershell
git add run_research_bias_transfer.py src/bess/research/bias_transfer.py tests/test_research_bias_transfer.py docs/RESEARCH_BIAS_TRANSFER_GATE.md docs/RESEARCH_BIAS_TRANSFER_INSTALL.md
git commit -m "Record source-only SOC bias transfer failure gate"
git push origin main
```
