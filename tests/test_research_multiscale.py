import sys,unittest,tempfile
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
import numpy as np
import pandas as pd
from bess.research.multiscale_audit import calibrate_windows,detect_windows
from run_research_multiscale import run

class MultiScaleTests(unittest.TestCase):
    def data(self,n=80):
        return pd.DataFrame(dict(telemetry_soc_pct=60+np.arange(n)*.05,
                                 soc_estimated_pct=60+np.arange(n)*.05,truth_attack=np.zeros(n,int)))
    def test_identical_baseline_no_alarm(self):
        x=self.data();cal=calibrate_windows([x],windows=(4,8))
        self.assertEqual(int(detect_windows(x,cal).alarm.sum()),0)
    def test_causal_past_unchanged(self):
        x=self.data();cal=calibrate_windows([x],windows=(4,8))
        y=x.copy();y.loc[40:,'telemetry_soc_pct']+=5
        a=detect_windows(x,cal);b=detect_windows(y,cal)
        self.assertTrue(np.array_equal(a.alarm[:40],b.alarm[:40]))
    def test_contaminated_calibration_rejected(self):
        x=self.data();x.loc[22,'truth_attack']=1
        with self.assertRaises(ValueError):calibrate_windows([x])
    def test_short_source_rejected(self):
        with self.assertRaises(ValueError):calibrate_windows([self.data(10)])
    def test_benign_step_indistinguishable(self):
        x=self.data();cal=calibrate_windows([x])
        a=x.copy();a.loc[40:,'telemetry_soc_pct']+=2
        b=x.copy();b.loc[40:,'telemetry_soc_pct']+=2
        self.assertTrue(np.array_equal(detect_windows(a,cal).alarm,detect_windows(b,cal).alarm))
    def test_invalid_windows_and_guard(self):
        x=self.data()
        for windows in ((0,), (4,4),()):
            with self.assertRaises(ValueError):calibrate_windows([x],windows=windows)
        with self.assertRaises(ValueError):calibrate_windows([x],guard=1)
    def test_full_runner(self):
        with tempfile.TemporaryDirectory() as d:
            result=run(d)
            self.assertEqual(len(result['details']),3*2*11)
            self.assertTrue((Path(d)/'limitations.json').exists())

if __name__=='__main__': unittest.main()
