import sys,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
from bess.box3.core import Box3Coordinator,Config,MitigationController,ResilientEstimator
from bess.box3.bridge import map_box2, policy_step

NORMAL={'classification':'NORMAL','attack_assessment':'NO_ATTACK_DETECTED'}
ATTACK={'classification':'ABNORMAL','attack_assessment':'ATTACK_DETECTED'}
SUSPECT={'classification':'SUSPICIOUS','attack_assessment':'ATTACK_SUSPECTED'}

class TestBox3Policy(unittest.TestCase):
    def test_normal(self):
        c=Box3Coordinator();r=policy_step(c,NORMAL,60,61,20)
        self.assertEqual(r['trust_mode'],'NORMAL');self.assertEqual(r['trust_score'],1.)
    def test_repeated_attack_safe(self):
        c=Box3Coordinator()
        for _ in range(2):r=policy_step(c,ATTACK,50,90,80)
        self.assertEqual(r['trust_mode'],'SAFE');self.assertEqual(r['soc_estimate'],50.)
        self.assertEqual(r['advisory_power_kw'],0.)
    def test_recovery_hysteresis(self):
        c=Box3Coordinator()
        for _ in range(2):policy_step(c,ATTACK,50,80,10)
        for _ in range(4):self.assertEqual(policy_step(c,NORMAL,50,51,10)['trust_mode'],'SAFE')
        for _ in range(60):r=policy_step(c,NORMAL,50,51,10)
        self.assertEqual(r['trust_mode'],'NORMAL')
    def test_bounds_and_caps(self):
        c=MitigationController()
        self.assertEqual(c.advise(500,50,'NORMAL')['advisory_power_kw'],100)
        self.assertEqual(c.advise(-500,50,'CAUTIOUS')['advisory_power_kw'],-50)
        self.assertEqual(c.advise(30,10,'NORMAL')['advisory_power_kw'],0)
    def test_untrusted_unknown_class_rejected(self):
        with self.assertRaises(ValueError):map_box2({'classification':'SAFE','attack_assessment':'ATTACK_DETECTED'})
    def test_nonfinite_rejected(self):
        with self.assertRaises(ValueError):policy_step(Box3Coordinator(),NORMAL,float('nan'),50,20)
    def test_no_truth_dependency(self):
        a={**ATTACK,'truth_attack':0};b={**ATTACK,'truth_attack':1}
        ca=Box3Coordinator();cb=Box3Coordinator()
        self.assertEqual(policy_step(ca,a,50,60,80),policy_step(cb,b,50,60,80))
    def test_suspicion_not_equivalent_to_confirmation(self):
        a=policy_step(Box3Coordinator(),SUSPECT,50,60,80)
        b=policy_step(Box3Coordinator(),ATTACK,50,60,80)
        self.assertGreater(a['trust_score'],b['trust_score'])

if __name__=='__main__':unittest.main()
