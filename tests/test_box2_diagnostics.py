import sys
import unittest
from pathlib import Path
import numpy as np
import pandas as pd
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from run_box2_diagnostics import CHANNELS, ablate_from_scores, run

class Box2Diagnostics(unittest.TestCase):
    def test_ablation_no_change_at_all_zero(self):
        f = pd.DataFrame({c: [0.,0.,0.,0.] for c in CHANNELS})
        for c in (None, *CHANNELS):
            self.assertEqual(int(ablate_from_scores(f,c).sum()),0)

    def test_ablation_can_suppress_existing_detection(self):
        f = pd.DataFrame({c:[0.]*5 for c in CHANNELS})
        f['sync_score']=2.;f['physics_score']=2.
        self.assertEqual(int(ablate_from_scores(f).sum()),3)
        self.assertEqual(int(ablate_from_scores(f,'sync_score').sum()),0)

    def test_original_fusion_equivalence(self):
        from bess.box1.replay import run_replay
        from bess.box2.attacks import inject_attack
        from bess.box2.five_evidence import calibrate_five_evidence, detect_five_evidence
        cal=calibrate_five_evidence([inject_attack(run_replay(p),'normal') for p in ('1A','1.5A')])
        d=detect_five_evidence(inject_attack(run_replay('2A'),'fixed_replay'),cal)
        self.assertTrue(np.array_equal(ablate_from_scores(d),d['alarm'].to_numpy()))

    def test_source_only_and_output(self):
        import tempfile
        with tempfile.TemporaryDirectory() as td:
            ch,ab,tr=run('2A',td)
            self.assertEqual(len(ch),35)
            self.assertEqual(len(ab),42)
            self.assertTrue((Path(td)/'channel_summary.csv').exists())
            self.assertTrue((Path(td)/'ablation_summary.csv').exists())
            self.assertEqual(int(ab[(ab.scenario=='fixed_replay')&(ab.omitted=='none')].attack_alarm_n.iloc[0]),57)

if __name__=='__main__': unittest.main()
