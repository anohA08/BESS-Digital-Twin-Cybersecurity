BESS signed stealth regions study (new files only)

Extract ZIP into E:\Research\BESS Rebuilder\BESS_REBUILD_STARTER
No extra top-level folder is included.

PowerShell commands:
  Expand-Archive -Path "$HOME\Downloads\BESS_SIGNED_STEALTH_GATE_ADDON.zip" -DestinationPath "." -Force
  Test-Path .\run_research_stealth_regions.py
  Test-Path .\tests\test_research_stealth_regions.py
  .\.venv\Scripts\python.exe -m unittest discover -s tests -v
  .\.venv\Scripts\python.exe run_research_stealth_regions.py

Expected full suite in assembled workspace: 84 tests, OK.
Output folder: results\research_stealth_regions

After verification:
  git add run_research_stealth_regions.py tests/test_research_stealth_regions.py docs/RESEARCH_SIGNED_STEALTH_GATE.md
  git commit -m "Add frozen-calibration signed stealth region audit"
  git push origin main
