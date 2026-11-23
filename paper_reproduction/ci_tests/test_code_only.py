import sys
from pathlib import Path
import unittest
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import run_single_protocol as core
import run_normalized_comparator as norm
class ProtocolCodeChecks(unittest.TestCase):
    def test_alarm_persistence(self):
        self.assertEqual(core.alarm([True, True, True, False, True, True]).tolist(), [False, False, True, False, False, False])
    def test_paired_sign_counts(self):
        self.assertEqual(norm.exact_sign_p(6,0), 0.03125)
        self.assertEqual(norm.exact_sign_p(2,0), 0.5)
    def test_protocol_constants(self):
        self.assertEqual((core.START,core.STOP,core.PERSIST), (40,90,3))
if __name__ == '__main__': unittest.main()
