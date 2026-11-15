import sys,unittest,tempfile
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
from bess.gridscale.plant import GridPlant,PlantConfig
from bess.gridscale.integration import simulate,make_calibration,run
from bess.gridscale.monitor import OnlineFiveEvidence
from bess.box2.five_evidence import detect_five_evidence
import pandas as pd

class TestGridScale(unittest.TestCase):
    def test_grid_config_checks(self):
        with self.assertRaises(ValueError):PlantConfig(capacity_kwh=-1)
        with self.assertRaises(ValueError):PlantConfig(initial_soc=99)
    def test_grid_plant_limits_and_interlocks(self):
        p=GridPlant()
        for _ in range(300):p.step(2000)
        self.assertGreaterEqual(p.evaluation_soc,20)
        self.assertAlmostEqual(p.evaluation_soc,20)
        for _ in range(500):p.step(-2000)
        self.assertAlmostEqual(p.evaluation_soc,90)
    def test_energy_accounting(self):
        p=GridPlant();v=p.step(600)
        self.assertAlmostEqual(p.evaluation_soc,60-100*(600/.95/60)/2000,places=9)
        self.assertAlmostEqual(v['executed_kw'],600)
    def test_online_batch_equivalence(self):
        from bess.gridscale.integration import _synthetic_clean_source
        cfg=PlantConfig();cal=make_calibration(cfg)
        f=_synthetic_clean_source(60,100,0.3,cfg.capacity_kwh,cfg.discharge_efficiency)
        b=detect_five_evidence(f,cal)
        m=OnlineFiveEvidence(cal)
        rows=[]
        for v in f.to_dict('records'):
            rows.append(m.step(**{name:v[name] for name in ('time_min','telemetry_soc_pct','soc_estimated_pct','telemetry_voltage_v','voltage_predicted_v','source_timestamp_min','receive_timestamp_min')}))
        for i,r in enumerate(rows):
            for key in ('alarm','classification','attack_assessment','sync_score','physics_score','temporal_score','voltage_score','freshness_score'):
                self.assertEqual(r[key],b.iloc[i][key],(i,key))
    def test_all_scenarios_and_policies(self):
        from bess.gridscale.integration import POLICIES,SCENARIOS
        cal=make_calibration(PlantConfig())
        for s in SCENARIOS:
            for p in POLICIES:
                f=simulate(s,p,n=91,calibration=cal)
                self.assertEqual(len(f),91)
                self.assertTrue(f.true_soc_evaluation_only.between(20,90).all())
    def test_policy_not_reading_attack_label(self):
        import inspect
        from bess.gridscale import integration
        code=inspect.getsource(integration.simulate)
        self.assertIn('policy_step(coord,inp,twin,reported,requested)',code)
        self.assertNotIn('policy_step(coord,inp,plant.evaluation_soc',code)
    def test_deterministic_and_files(self):
        a=simulate('spoof_p5','legacy',n=94)
        b=simulate('spoof_p5','legacy',n=94)
        pd.testing.assert_frame_equal(a,b)
        with tempfile.TemporaryDirectory() as tmp:
            result=run(tmp,n=91)
            self.assertEqual(len(result),21)
            self.assertTrue((Path(tmp)/'ASSUMPTIONS.json').is_file())
            self.assertTrue((Path(tmp)/'summary.csv').is_file())
