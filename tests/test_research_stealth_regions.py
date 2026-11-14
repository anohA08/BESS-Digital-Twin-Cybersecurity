import sys,unittest,tempfile
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
import numpy as np
from bess.box1.replay import run_replay
from bess.box2.attacks import inject_attack
from run_research_stealth_regions import interval,analyze_profile,run

class StealthRegionsTests(unittest.TestCase):
    def test_interval_geometry(self):
        low,high=interval(np.array([3.,-3.]),5.)
        np.testing.assert_allclose(low,[-8.,-2.]);np.testing.assert_allclose(high,[2.,8.])
    def test_invalid_threshold(self):
        with self.assertRaises(ValueError): interval(np.array([1.]),0.)
    def test_source_only_and_sign(self):
        frames={p:run_replay(p) for p in ('1A','1.5A','2A')}
        src=[inject_attack(frames[p],'normal') for p in ('1A','1.5A')]
        detail,summary,_=analyze_profile(frames['2A'],src,'2A',offsets=(-2.,2.))
        self.assertEqual(len(detail),140)
        self.assertEqual(set(summary.offset_requested_pp),{-2.,2.})
        self.assertTrue((summary.calibrated_source_profiles==2).all())
        self.assertTrue(((detail.predicted_soc_stealth + detail.predicted_soc_attacked_alarm)==1).all())
    def test_reproducibility(self):
        with tempfile.TemporaryDirectory() as d:
            a=run(Path(d)/'first');b=run(Path(d)/'second')
            for k in a:
                import pandas as pd
                pd.testing.assert_frame_equal(a[k],b[k])
    def test_physical_measurements_untouched(self):
        raw=run_replay('2A');normal=inject_attack(raw,'normal');attack=normal.copy()
        attack.loc[40:109,'telemetry_soc_pct']+=2.
        for col in ('current_a','voltage_measured_v','voltage_predicted_v','soc_estimated_pct'):
            np.testing.assert_array_equal(normal[col],attack[col])

if __name__=='__main__':unittest.main()
