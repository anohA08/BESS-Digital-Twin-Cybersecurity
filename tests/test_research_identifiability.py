import sys,unittest,tempfile
from pathlib import Path
import numpy as np
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
from bess.box1.replay import run_replay
from bess.box2.attacks import inject_attack
from bess.research.identifiability_gate import (benign_report_change,observable_equal,report_anchor_discrepancy,audit_profile,PHYSICAL)

class IdentifiabilityTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):cls.replay=run_replay('2A')
    def test_gradual_attack_benign_same_visible_stream(self):
        a=inject_attack(self.replay,'spoof_ramp_p5')
        b=benign_report_change(self.replay,5,ramp=True)
        self.assertTrue(observable_equal(a,b))
        self.assertNotEqual(a.truth_attack.sum(),b.truth_attack.sum())
    def test_abrupt_attack_benign_same_visible_stream(self):
        self.assertTrue(observable_equal(inject_attack(self.replay,'spoof_p2'),benign_report_change(self.replay,2,ramp=False)))
    def test_physical_stream_not_modified_by_soc_injection(self):
        c=inject_attack(self.replay,'normal')
        self.assertTrue(observable_equal(c,inject_attack(self.replay,'spoof_ramp_p5'),PHYSICAL))
    def test_report_anchor_identifies_inconsistency_not_intent(self):
        a=inject_attack(self.replay,'spoof_p2');b=benign_report_change(self.replay,2,ramp=False)
        reference=self.replay.soc_recorded_for_evaluation_only_pct.to_numpy(float)
        self.assertTrue(np.array_equal(report_anchor_discrepancy(a,reference,uncertainty_pp=1),report_anchor_discrepancy(b,reference,uncertainty_pp=1)))
        self.assertEqual(int(report_anchor_discrepancy(a,reference,uncertainty_pp=1)[40:110].sum()),70)
    def test_invalid_anchor_is_rejected(self):
        f=inject_attack(self.replay,'normal')
        with self.assertRaises(ValueError):report_anchor_discrepancy(f,np.zeros(len(f)),uncertainty_pp=-1)
        with self.assertRaises(ValueError):report_anchor_discrepancy(f,np.zeros(2),uncertainty_pp=1)
    def test_all_profiles_and_both_ramp_signs(self):
        for k in ('1A','1.5A','2A'):
            x=audit_profile(k,run_replay(k))
            self.assertEqual(len(x),12)
            self.assertTrue(x.attack_and_benign_observationally_identical.all())
            self.assertTrue(x.physical_channels_invariant_under_soc_attack.all())
    def test_runner_reproducible(self):
        sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
        from run_research_identifiability import run
        with tempfile.TemporaryDirectory() as a,tempfile.TemporaryDirectory() as b:
            p=run(a);q=run(b)
            self.assertTrue(p.equals(q))
            self.assertEqual((Path(a)/'gate.json').read_bytes(),(Path(b)/'gate.json').read_bytes())
if __name__=='__main__':unittest.main()
