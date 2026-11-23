import sys
from pathlib import Path
import unittest
import numpy as np
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src'))
from bess.box1.replay import run_replay
from bess.box1.battery import Battery
from bess.box1.digital_twin import DigitalTwin

class TestBox1(unittest.TestCase):
    def test_all_recorded_profiles(self):
        for name in ['1A','1.5A','2A']:
            with self.subTest(profile=name):
                df=run_replay(name)
                self.assertGreater(len(df),30)
                self.assertTrue(np.isfinite(df.voltage_residual_v.to_numpy()).all())
                self.assertTrue((df.soc_estimated_pct.between(10,100)).all())
    def test_replay_is_deterministic(self):
        a=run_replay('1A');b=run_replay('1A')
        self.assertTrue(a.equals(b))
    def test_no_target_soc_oracle(self):
        # the evaluation proxy must not be used to update the model state
        df=run_replay('2A',initial_soc=80)
        self.assertAlmostEqual(df.soc_estimated_pct.iloc[0],80)
        self.assertGreater(abs(df.soc_recorded_for_evaluation_only_pct.iloc[0]-df.soc_estimated_pct.iloc[0]),10)
    def test_invalid_initialization(self):
        with self.assertRaises(ValueError):run_replay('1A',initial_soc=-5)
    def test_model_zero_step(self):
        bat=Battery();twin=DigitalTwin(bat)
        old=bat.get_soc();v=twin.predict_ecm_voltage(1.0,0)
        self.assertAlmostEqual(old,bat.get_soc())
        self.assertTrue(np.isfinite(v))
if __name__=='__main__':unittest.main()
