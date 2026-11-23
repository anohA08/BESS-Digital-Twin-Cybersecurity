import unittest
import numpy as np
from run_box1_ekf import compare, summarize
from bess.box1.battery import Battery
from bess.box1.ekf import ExtendedKalmanFilter

class TestBox1EKFDiagnostic(unittest.TestCase):
    def test_all_profiles_execute(self):
        for p in ('1A', '1.5A', '2A'):
            d = compare(p)
            self.assertGreater(len(d), 100)
            self.assertTrue(np.isfinite(d.select_dtypes(include='number')).all().all())
    def test_soc_stays_in_limits(self):
        b = Battery()
        d = compare('1A')
        self.assertTrue(d.ekf_soc_posterior_pct.between(b.soc_min, b.soc_max).all())
    def test_prior_is_preupdate_prediction(self):
        d = compare('1A')
        np.testing.assert_allclose(d.ekf_innovation_v, d.voltage_measured_v-d.ekf_voltage_prior_v)
    def test_repeatability(self):
        a = compare('1A'); b = compare('1A')
        np.testing.assert_allclose(a.ekf_voltage_prior_v, b.ekf_voltage_prior_v)
    def test_invalid_initial_soc(self):
        with self.assertRaises(ValueError): compare('1A', -10)
    def test_metrics_exist(self):
        m = summarize(compare('1A'), '1A')
        self.assertGreaterEqual(m['ekf_prior_voltage_rmse_mv'],0)
        self.assertGreaterEqual(m['ecm_prior_voltage_rmse_mv'],0)

if __name__ == '__main__': unittest.main()
