import sys
import unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
from bess.box1.replay import run_replay
from bess.box2.attacks import inject_attack
from bess.box2.five_evidence import calibrate_five_evidence,detect_five_evidence

class TestFiveEvidence(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.clean=[inject_attack(run_replay(x),'normal') for x in ('1A','1.5A')]
        cls.target=inject_attack(run_replay('2A'),'normal')
        cls.cal=calibrate_five_evidence(cls.clean)
    def test_calibration_source_only(self):
        self.assertEqual(self.cal.n_source_profiles,2)
        self.assertTrue(all(k in self.cal.envelopes for k in ('high','middle','low')))
    def test_finite_and_deterministic(self):
        a=detect_five_evidence(self.target,self.cal)
        b=detect_five_evidence(self.target,self.cal)
        self.assertEqual(a.to_csv(index=False),b.to_csv(index=False))
        self.assertTrue(set(['sync_score','physics_score','temporal_score','voltage_score','freshness_score','fusion_score','alarm']).issubset(a))
    def test_attack_labels_never_used(self):
        alternate=self.target.copy();alternate['truth_attack']=1;alternate['attack_window']=0
        a=detect_five_evidence(self.target,self.cal)
        b=detect_five_evidence(alternate,self.cal)
        self.assertEqual(a.to_csv(index=False),b.to_csv(index=False))
    def test_all_original_attack_families(self):
        for s in ('spoof_5','fixed_replay','rolling_replay','delay_3min'):
            with self.subTest(scenario=s):
                out=detect_five_evidence(inject_attack(run_replay('2A'),s),self.cal)
                self.assertEqual(len(out),152)
                self.assertTrue(out.alarm.isin([0,1]).all())
    def test_reject_contaminated_calibration(self):
        attacked=inject_attack(run_replay('1A'),'spoof_5')
        with self.assertRaises(ValueError):calibrate_five_evidence([attacked])
    def test_cannot_read_future_labels(self):
        x=self.target.drop(columns=['truth_attack','attack_window'])
        out=detect_five_evidence(x,self.cal)
        self.assertEqual(len(out),152)
