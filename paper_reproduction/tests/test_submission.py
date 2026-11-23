"""Frozen protocol: guards against silent scientific-result drift."""
import unittest
from pathlib import Path
import tempfile
import numpy as np
import pandas as pd
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import run_submission as release
import run_single_protocol as base
import run_normalized_comparator as normalized

ROOT=Path(__file__).resolve().parents[1]
DATA=base.DEFAULT

class TestFrozenSubmission(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.data=pd.read_csv(DATA)
        cls.evaldata=cls.data[cls.data.i>30].copy()

    def test_input_manifest_and_sample_counts(self):
        m=release.validate_input(DATA)
        self.assertEqual(m['sessions'],12)
        self.assertEqual(m['evaluated_total_rows'],1452)
        self.assertEqual(m['source_sha256'],'83b73658d4c12dc4982dca45ba435c41be03b23673ecf4be99e5023dcbfa2316')
        self.assertEqual(len(self.evaldata),1452)

    def test_corrupted_data_rejected(self):
        with tempfile.TemporaryDirectory() as td:
            d=self.data.drop(columns=['soc_discrepancy']);p=Path(td)/'bad.csv';d.to_csv(p,index=False)
            with self.assertRaisesRegex(ValueError,'Missing columns'):release.validate_input(p)
            d=self.data.copy();d.loc[0,'i']=2;d.to_csv(p,index=False)
            with self.assertRaisesRegex(ValueError,'Invalid sample sequence'):release.validate_input(p)

    def test_source_only_threshold_is_independent_of_target_attack(self):
        tar=self.evaldata[self.evaldata.run=='run_01'].sort_values('i')
        src=self.evaldata[self.evaldata.run!='run_01']
        r0,_,_=base.eval_method(src,tar,'soc_binned','normal')
        r1,_,_=base.eval_method(src,tar,'soc_binned','step_m5')
        self.assertAlmostEqual(r0['clean_far'],r1['clean_far'])
        self.assertEqual(r0['n_clean'],121)
        self.assertEqual(r1['n_attack'],50)
        self.assertTrue((src.run!='run_01').all())

    def test_attack_persistence(self):
        self.assertEqual(base.alarm([True,True,True,False,True,True]).tolist(),[False,False,True,False,False,False])

    def test_reproduction_of_primary_results(self):
        x=pd.read_csv(ROOT/'normalized_comparison'/'all_methods_per_session.csv')
        clean=x[x.attack=='normal'].groupby('method').clean_far.mean()
        self.assertAlmostEqual(clean.loc['global'],.03856749311294766,places=6)
        self.assertAlmostEqual(clean.loc['soc_binned'],.01997245179063361,places=6)
        self.assertAlmostEqual(clean.loc['normalized_time_binned'],.024104683195592286,places=6)
        hits=x[x.attack!='normal'].groupby(['method','attack']).new_event.sum()
        self.assertEqual(int(hits.loc[('soc_binned','step_m5')]),12)
        self.assertEqual(int(hits.loc[('normalized_time_binned','step_m5')]),6)
        self.assertEqual(int(hits.loc[('soc_binned','ramp_p5')]),4)
        self.assertEqual(int(hits.loc[('global','ramp_p5')]),0)

    def test_exact_paired_sign_test(self):
        self.assertEqual(normalized.exact_sign_p(6,0),.03125)
        self.assertEqual(normalized.exact_sign_p(2,0),.5)
        self.assertEqual(normalized.exact_sign_p(0,0),1.)

    def test_all_calibration_records_source_only(self):
        for run in sorted(self.evaldata.run.unique()):
            src=self.evaldata[self.evaldata.run!=run]
            tar=self.evaldata[self.evaldata.run==run]
            self.assertFalse((src.run==run).any())
            self.assertEqual(len(tar),121)
            self.assertEqual(len(src),1331)
            for method in ('global','soc_binned','time_binned'):
                out,_,_=base.eval_method(src,tar,method,'step_p5')
                self.assertGreaterEqual(out['source_supported_fraction'],0)
                self.assertLessEqual(out['source_supported_fraction'],1)

if __name__=='__main__':unittest.main()
