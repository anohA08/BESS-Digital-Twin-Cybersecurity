# Install final research-phase pilot (no baseline replacement)

Extract the archive directly into `E:\Research\BESS Rebuilder\BESS_REBUILD_STARTER`.

PowerShell:

```powershell
Expand-Archive -Path "$HOME\Downloads\BESS_RESEARCH_SIGNED_INCREMENT_PILOT.zip" -DestinationPath "." -Force
Test-Path .\run_research_candidate.py
Test-Path .\src\bess\research\signed_increment.py
Test-Path .\tests\test_research_signed_increment.py
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
.\.venv\Scripts\python.exe run_research_candidate.py --traces
```

Expected `Ran 65 tests ... OK` assuming all previous add-ons are correctly installed. Outputs: `results\research_signed_increment`. Inspect `docs\RESEARCH_CANDIDATE_PILOT.md` before interpreting results.

Git add ONLY these five files if tests pass:

```powershell
git add run_research_candidate.py src/bess/research/__init__.py src/bess/research/signed_increment.py tests/test_research_signed_increment.py docs/RESEARCH_CANDIDATE_PILOT.md docs/RESEARCH_PILOT_INSTALL.md
git commit -m "Add exploratory signed-increment research benchmark"
git push origin main
```

NOTE: The pilot is an exploratory comparator, not a tested replacement for Box 2 fusion or Box 3 control. No files under frozen `src/bess/box1`, `src/bess/box2`, `src/bess/box3`, or `src/bess/box4` are overwritten.
