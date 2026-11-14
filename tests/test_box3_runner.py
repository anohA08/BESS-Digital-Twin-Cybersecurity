import sys, unittest, tempfile
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from run_box3 import run

class TestBox3Runner(unittest.TestCase):
    def test_runs_and_reproducible(self):
        with tempfile.TemporaryDirectory() as a, tempfile.TemporaryDirectory() as b:
            x=run('2A',a);y=run('2A',b)
            self.assertEqual(x.to_csv(index=False),y.to_csv(index=False))
            self.assertEqual(len(x),7)
            self.assertTrue((Path(a)/'advisory_deviation.png').exists())
    def test_no_false_alarm_is_not_claimed_safety(self):
        with tempfile.TemporaryDirectory() as a:
            x=run('2A',a)
            self.assertIn('absolute_dispatch_deviation_outside_attack_kwh',x.columns)
            self.assertTrue((Path(a)/'limitations.json').exists())

if __name__=='__main__':unittest.main()
