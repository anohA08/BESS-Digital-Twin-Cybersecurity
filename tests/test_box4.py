import sys
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
import numpy as np
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src'))
sys.path.insert(0,str(ROOT))
from bess.box4.metrics import detection_metrics,paired_metrics,episodes,advisory_metrics
from run_box4 import run,PROFILES,ALL_SCENARIOS,METHODS

class Box4Tests(unittest.TestCase):
    def test_episode_boundaries(self):
        self.assertEqual(episodes([0,1,1,0,1]),[(1,2),(4,4)])
    def test_event_delay_and_false_event(self):
        m=detection_metrics([0,0,1,1,1,0],[1,0,0,1,0,0],np.arange(6.)*2.)
        self.assertEqual(m['first_detection_delay_min'],2.)
        self.assertEqual(m['false_alert_episodes'],1)
        self.assertEqual(m['tp'],1)
    def test_no_hit_not_zero_delay(self):
        self.assertIsNone(detection_metrics([0,1,1],[0,0,0],[0,1,2])['first_detection_delay_min'])
    def test_invalid_labels_rejected(self):
        with self.assertRaises(ValueError):detection_metrics([0,1,2],[0,0,1],[0,1,2])
    def test_pairing_leakage_rejected(self):
        with self.assertRaisesRegex(ValueError,'Pre-attack'):
            paired_metrics([0,0,0,0],[1,0,0,0],[0,0,1,1],range(4))
    def test_paired_new_event_control(self):
        m=paired_metrics([0,0,1,0,0],[0,0,1,1,0],[0,0,1,1,0],range(5))
        self.assertFalse(m['new_event_hit']);self.assertEqual(m['paired_excess_alarm_fraction'],.5)
    def test_full_protocol_cross_profile(self):
        with TemporaryDirectory() as td:
            out=run(td)
            self.assertEqual(len(out['clean']),len(PROFILES)*len(METHODS))
            self.assertEqual(len(out['detection']),len(PROFILES)*len(METHODS)*len(ALL_SCENARIOS))
            self.assertEqual(len(out['policies']),len(PROFILES)*len(ALL_SCENARIOS)*2)
            self.assertTrue((Path(td)/'evaluation_manifest.json').exists())
            self.assertTrue((out['clean'].clean_far>=0).all())
    def test_truth_not_passed_into_detector(self):
        from bess.box1.replay import run_replay
        from bess.box2.attacks import inject_attack
        from bess.box2.five_evidence import calibrate_five_evidence,detect_five_evidence
        src=[inject_attack(run_replay('1A'),'normal'),inject_attack(run_replay('1.5A'),'normal')]
        data=inject_attack(run_replay('2A'),'spoof_m5')
        cal=calibrate_five_evidence(src)
        original=detect_five_evidence(data,cal)
        data['truth_attack']=1-data['truth_attack']
        data['attack_window']=1-data['attack_window']
        alt=detect_five_evidence(data,cal)
        np.testing.assert_array_equal(original.alarm,alt.alarm)
if __name__=='__main__':unittest.main()
