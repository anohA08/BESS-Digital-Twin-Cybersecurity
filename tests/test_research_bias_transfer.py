import unittest
import numpy as np
import pandas as pd
from pathlib import Path
import sys,tempfile
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
from bess.research.bias_transfer import fit_bias_model,evaluate_soc_flags
from bess.box1.replay import run_replay
from bess.box2.attacks import inject_attack

class BiasTransferTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.clean={p:inject_attack(run_replay(p),'normal') for p in ('1A','1.5A','2A')}
    def test_source_only_all_targets(self):
        for target in self.clean:
            m=fit_bias_model([v for k,v in self.clean.items() if k!=target])
            self.assertEqual(m.source_profiles,2)
            self.assertTrue(np.isfinite(m.residual_limit_pp))
    def test_contaminated_source_rejected(self):
        bad=self.clean['1A'].copy();bad.loc[50,'truth_attack']=1
        with self.assertRaises(ValueError):fit_bias_model([bad])
    def test_future_data_cannot_affect_prior_alarms(self):
        m=fit_bias_model([self.clean['1A'],self.clean['1.5A']]);clean=self.clean['2A'].copy()
        changed=clean.copy();changed.loc[110:,'telemetry_soc_pct']+=5
        a=evaluate_soc_flags(clean,m);b=evaluate_soc_flags(changed,m)
        for k in ('raw','bias_aware'):
            np.testing.assert_array_equal(a[k][:110],b[k][:110])
    def test_attack_truth_independent(self):
        m=fit_bias_model([self.clean['1A'],self.clean['1.5A']]);x=self.clean['2A'].copy()
        y=x.copy();y['truth_attack']=1-y['truth_attack']
        a=evaluate_soc_flags(x,m);b=evaluate_soc_flags(y,m)
        for k in ('raw','bias_aware'):
            np.testing.assert_array_equal(a[k],b[k])
    def test_zero_target_bias_does_not_make_attack_truth(self):
        x=self.clean['1A'].copy();x['telemetry_soc_pct']=x['soc_estimated_pct']
        m=fit_bias_model([x]);a=evaluate_soc_flags(x,m)
        self.assertEqual(int(a['raw'].sum()),0)
        self.assertEqual(int(a['bias_aware'].sum()),0)
    def test_frozen_gate_flags_failure(self):
        from run_research_bias_transfer import run
        with tempfile.TemporaryDirectory() as d:
            result=run(d)
            a=result['clean']
            r=a[(a.profile=='2A')&(a.method=='bias_aware')].iloc[0]
            self.assertGreater(r.clean_far,.05)
            self.assertFalse(bool(r.passes_5pct))
            self.assertEqual(len(result['events']),54)

if __name__=='__main__':unittest.main()
