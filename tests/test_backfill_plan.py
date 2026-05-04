import math
import unittest

from scripts.plan_tw_backfill import _estimate_batches, _phase_count


class BackfillPlanTests(unittest.TestCase):
    def test_estimate_batches(self):
        self.assertEqual(_estimate_batches(0, 25), 0)
        self.assertEqual(_estimate_batches(1, 25), 1)
        self.assertEqual(_estimate_batches(25, 25), 1)
        self.assertEqual(_estimate_batches(26, 25), 2)

    def test_phase_count(self):
        self.assertEqual(_phase_count(-1, 100), 100)
        self.assertEqual(_phase_count(0, 100), 0)
        self.assertEqual(_phase_count(20, 100), 20)
        self.assertEqual(_phase_count(120, 100), 100)


if __name__ == "__main__":
    unittest.main()
