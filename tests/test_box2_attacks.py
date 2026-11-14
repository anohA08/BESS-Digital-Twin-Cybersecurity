import sys,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
from bess.box1.replay import run_replay
from bess.box2.attacks import inject_attack,AttackWindow,ALL_SCENARIOS
from bess.box2.detectors import calibrate_global,detect_threshold,detect_cusum
from bess.box2.evaluation import paired_excess

class Box2AttackTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.clean=run_replay('2A')
    def test_legacy_attack_family_catalogue(self):
        for case in ('normal','spoof_5','spoof_10','spoof_15','spoof_20','fixed_replay','rolling_replay','delay_3min'):
            self.assertIn(case,ALL_SCENARIOS)
    def test_spoof_only_soc(self):
        att=inject_attack(self.clean,'spoof_5'); k=50
        self.assertAlmostEqual(att.loc[k,'telemetry_soc_pct'],min(100,self.clean.loc[k,'soc_recorded_for_evaluation_only_pct']+5))
        self.assertAlmostEqual(att.loc[k,'telemetry_voltage_v'],self.clean.loc[k,'voltage_measured_v'])
        self.assertEqual(int(att.loc[k,'truth_attack']),1)
        self.assertEqual(int(att.loc[15,'truth_attack']),0)
    def test_negative_and_ramp(self):
        minus=inject_attack(self.clean,'spoof_m5')
        self.assertAlmostEqual(minus.loc[65,'telemetry_soc_pct'],max(0,self.clean.loc[65,'soc_recorded_for_evaluation_only_pct']-5))
        ramp=inject_attack(self.clean,'spoof_ramp_p5')
        self.assertAlmostEqual(ramp.loc[40,'telemetry_soc_pct'],self.clean.loc[40,'soc_recorded_for_evaluation_only_pct'])
    def test_positive_two_pp_spoof_regression(self):
        plus=inject_attack(self.clean,'spoof_p2')
        self.assertAlmostEqual(plus.loc[65,'telemetry_soc_pct'], min(100,self.clean.loc[65,'soc_recorded_for_evaluation_only_pct']+2))
    def test_replay_refreshes_timestamps(self):
        fixed=inject_attack(self.clean,'fixed_replay');rolling=inject_attack(self.clean,'rolling_replay')
        self.assertAlmostEqual(fixed.loc[66,'telemetry_soc_pct'],self.clean.loc[39,'soc_recorded_for_evaluation_only_pct'])
        self.assertAlmostEqual(rolling.loc[66,'telemetry_soc_pct'],self.clean.loc[58,'soc_recorded_for_evaluation_only_pct'])
        self.assertAlmostEqual(fixed.loc[66,'source_timestamp_min'],self.clean.loc[66,'time_min'])
    def test_delay_only_age(self):
        delay=inject_attack(self.clean,'delay_3min')
        self.assertAlmostEqual(delay.loc[50,'receive_timestamp_min']-delay.loc[50,'source_timestamp_min'],3.0)
        self.assertAlmostEqual(delay.loc[50,'telemetry_soc_pct'],self.clean.loc[50,'soc_recorded_for_evaluation_only_pct'])
        self.assertAlmostEqual(delay.loc[20,'receive_timestamp_min']-delay.loc[20,'source_timestamp_min'],0.0)
    def test_labels_not_detector_inputs(self):
        sources=[inject_attack(run_replay(p),'normal') for p in ('1A','1.5A')]
        config=calibrate_global(sources)
        attacked=inject_attack(self.clean,'spoof_10')
        first=detect_threshold(attacked,config)
        attacked['truth_attack']=0
        attacked['attack_window']=0
        second=detect_threshold(attacked,config)
        self.assertTrue(first.equals(second))
    def test_cusum_determinism_and_pairing(self):
        sources=[inject_attack(run_replay(p),'normal') for p in ('1A','1.5A')]
        clean=inject_attack(self.clean,'normal');att=inject_attack(self.clean,'spoof_5')
        a=detect_cusum(att,sources);b=detect_cusum(att,sources)
        self.assertTrue(a.equals(b))
        self.assertAlmostEqual(paired_excess(clean.assign(alarm=detect_cusum(clean,sources).alarm),att.assign(alarm=a.alarm)),float(paired_excess(clean.assign(alarm=detect_cusum(clean,sources).alarm),att.assign(alarm=b.alarm))))
    def test_invalid_window(self):
        with self.assertRaises(ValueError):inject_attack(self.clean,'spoof_5',AttackWindow(110,40))

if __name__=='__main__':unittest.main()
