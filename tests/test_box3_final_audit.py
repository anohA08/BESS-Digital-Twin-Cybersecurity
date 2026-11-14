import sys
import tempfile
import unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from bess.box3.core import Box3Coordinator
from bess.box3.bridge import policy_step
from run_box3_policy_audit import run_audit, shadow_input

class TestFinalBox3Audit(unittest.TestCase):
    def test_shadow_filters_suspicion_without_truth(self):
        row={'classification':'SUSPICIOUS','attack_assessment':'ATTACK_SUSPECTED','truth_attack':1}
        self.assertEqual(shadow_input(row), {'classification':'NORMAL','attack_assessment':'NO_ATTACK_DETECTED'})
        row['truth_attack']=0
        self.assertEqual(shadow_input(row), {'classification':'NORMAL','attack_assessment':'NO_ATTACK_DETECTED'})

    def test_shadow_preserves_confirmed(self):
        row={'classification':'ABNORMAL','attack_assessment':'ATTACK_DETECTED'}
        self.assertEqual(shadow_input(row), row)

    def test_bad_shadow_class_rejected(self):
        with self.assertRaises(ValueError):
            shadow_input({'classification':'BROKEN','attack_assessment':'ATTACK_SUSPECTED'})

    def test_shadows_respond_to_confirmed(self):
        c1=Box3Coordinator();c2=Box3Coordinator()
        row={'classification':'ABNORMAL','attack_assessment':'ATTACK_DETECTED'}
        self.assertEqual(policy_step(c1,row,60,60,60),policy_step(c2,shadow_input(row),60,60,60))

    def test_audit_reproducible_and_positive_clean_penalty(self):
        with tempfile.TemporaryDirectory() as a, tempfile.TemporaryDirectory() as b:
            x=run_audit('2A',a);y=run_audit('2A',b)
            self.assertEqual(x.to_csv(index=False),y.to_csv(index=False))
            legacy=x[(x.scenario=='normal')&(x.policy=='legacy')].iloc[0]
            shadow=x[(x.scenario=='normal')&(x.policy=='confirmed_only')].iloc[0]
            self.assertEqual(legacy.safe_clean_samples,55)
            self.assertEqual(legacy.strict_alarm_samples,0)
            self.assertGreater(legacy.deviation_kwh_clean,0)
            self.assertEqual(shadow.safe_clean_samples,0)
            self.assertEqual(shadow.deviation_kwh_clean,0)
            # Same Box2 detector outputs, only response policy is shadowed
            for scenario in x.scenario.unique():
                group=x[x.scenario==scenario]
                self.assertEqual(group.strict_alarm_samples.nunique(),1)

if __name__=='__main__':unittest.main()
