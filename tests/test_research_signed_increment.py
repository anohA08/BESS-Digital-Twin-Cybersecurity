"""Transparent properties and counterexamples for the exploratory candidate."""
import sys, unittest
from pathlib import Path
from tempfile import TemporaryDirectory
import numpy as np
import pandas as pd
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src'))
sys.path.insert(0,str(ROOT))
from bess.box1.replay import run_replay
from bess.box2.attacks import inject_attack
from bess.research.signed_increment import calibrate_signed_increment,detect_signed_increment
from run_research_candidate import run

class SignedIncrementResearchTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.sources=[inject_attack(run_replay('1A'),'normal'),inject_attack(run_replay('1.5A'),'normal')]
        cls.cal=calibrate_signed_increment(cls.sources)
        cls.target=inject_attack(run_replay('2A'),'normal')

    def test_signed_step_detected_both_directions(self):
        for name in ('spoof_m2','spoof_p2','spoof_m5','spoof_5'):
            with self.subTest(scenario=name):
                a=inject_attack(run_replay('2A'),name)
                det=detect_signed_increment(a,self.cal)
                self.assertEqual(int(det.onset.iloc[40]),1)
                self.assertEqual(int(det.alarm.iloc[40]),1)

    def test_same_source_rows_do_not_auto_raise_alarm(self):
        for src in self.sources:
            self.assertFalse(bool(detect_signed_increment(src,self.cal).alarm.any()))

    def test_attack_truth_not_read(self):
        a=inject_attack(run_replay('2A'),'spoof_m5')
        original=detect_signed_increment(a,self.cal)
        a['truth_attack']=1-a.truth_attack
        a['attack_window']=1-a.attack_window
        np.testing.assert_array_equal(original.alarm,detect_signed_increment(a,self.cal).alarm)

    def test_contaminated_source_rejected(self):
        a=inject_attack(run_replay('1A'),'spoof_5')
        with self.assertRaisesRegex(ValueError,'attack'):
            calibrate_signed_increment([a])

    def test_nonfinite_rejected(self):
        a=self.target.copy()
        a.loc[14,'telemetry_soc_pct']=np.nan
        with self.assertRaisesRegex(ValueError,'finite'):
            detect_signed_increment(a,self.cal)

    def test_missing_values_rejected(self):
        a=self.target.drop(columns=['soc_estimated_pct'])
        with self.assertRaisesRegex(ValueError,'required'):
            detect_signed_increment(a,self.cal)

    def test_invalid_calibration_guard_and_hold(self):
        with self.assertRaises(ValueError):calibrate_signed_increment(self.sources,guard_multiplier=1)
        with self.assertRaises(ValueError):detect_signed_increment(self.target,self.cal,hold_samples=0)

    def test_unchanged_measurements_yield_identical_alarms(self):
        d=detect_signed_increment(self.target,self.cal)
        np.testing.assert_array_equal(d.alarm,detect_signed_increment(self.target.copy(deep=True),self.cal).alarm)

    def test_benign_soc_reporting_reset_is_ambiguous(self):
        """A benign report-offset reset is observationally identical to FDIA step."""
        a=self.target.copy(deep=True)
        a.loc[40:109,'telemetry_soc_pct']-=2.0
        det=detect_signed_increment(a,self.cal)
        self.assertEqual(det.negative_onset.iloc[40],1)
        # Hence zero clean FAR on unmodified recordings cannot certify field FAR.

    def test_gradual_drift_missed(self):
        a=inject_attack(run_replay('2A'),'spoof_ramp_p5')
        det=detect_signed_increment(a,self.cal)
        self.assertEqual(int(det.alarm.iloc[40:110].sum()),0)

    def test_event_held_then_releases(self):
        a=inject_attack(run_replay('2A'),'spoof_m5')
        d=detect_signed_increment(a,self.cal,hold_samples=3)
        self.assertEqual(d.alarm.iloc[40:43].tolist(),[1,1,1])
        self.assertEqual(int(d.alarm.iloc[43]),0)

    def test_full_experiment_reproducible(self):
        with TemporaryDirectory() as tmp:
            x=run(tmp)
            y=run(tmp)
            pd.testing.assert_frame_equal(x['events'],y['events'])
            self.assertEqual(len(x['clean']),3*4)
            self.assertEqual(len(x['details']),3*4*12)
            self.assertTrue((Path(tmp)/'limitations_and_manifest.json').exists())

if __name__=='__main__':unittest.main()
