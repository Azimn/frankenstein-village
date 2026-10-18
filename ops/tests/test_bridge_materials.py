"""Finite bridge supplies are not fictional progress or unlimited free inventory."""
from __future__ import annotations

import sys
from pathlib import Path
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "spike/fvillage"))
from world import bridge_materials as mats


class BridgeMaterialsTests(unittest.TestCase):
    def test_two_distinct_kits_and_independent_finite_stock(self):
        state = mats.normalize(None, 1)
        self.assertEqual(state["remaining"], {"preserve": 2, "display": 2})
        latest, ok, problem = mats.withdraw(state, 1, "preserve")
        self.assertTrue(ok, problem)
        self.assertEqual(latest["remaining"], {"preserve": 1, "display": 2})
        self.assertEqual(state["remaining"]["preserve"], 2)
        latest, ok, problem = mats.withdraw(latest, 1, "preserve")
        self.assertTrue(ok, problem)
        blocked, ok, problem = mats.withdraw(latest, 1, "preserve")
        self.assertFalse(ok)
        self.assertEqual(blocked, latest)
        self.assertIn("No more", problem)
        other, ok, problem = mats.withdraw(latest, 1, "display")
        self.assertTrue(ok, problem)
        self.assertEqual(other["remaining"]["display"], 1)

    def test_reset_is_clock_driven_and_never_farms_elapsed_days(self):
        state = mats.normalize(None, 6)
        state, ok, _ = mats.withdraw(state, 6, "display")
        self.assertTrue(ok)
        self.assertEqual(mats.normalize(state, 6)["remaining"]["display"], 1)
        stale = mats.normalize(state, 5)
        self.assertEqual(stale["remaining"]["display"], 1)
        blocked, ok, reason = mats.withdraw(state, 5, "display")
        self.assertFalse(ok)
        self.assertIn("earlier day", reason)
        next_day = mats.normalize(state, 60)
        self.assertEqual(next_day["day"], 60)
        self.assertEqual(next_day["remaining"], {"preserve": 2, "display": 2})
        self.assertEqual(state["day"], 6)
        self.assertEqual(mats.normalize(next_day, 60), next_day)

    def test_invalid_and_corrupt_stock_never_grants_extra_kits(self):
        state = mats.normalize(
            {"day": 4, "remaining": {"preserve": 999,
                                    "display": "not a number"}},
            4
        )
        self.assertEqual(state["remaining"], {"preserve": 2, "display": 0})
        snapshot, ok, problem = mats.withdraw(state, 4, "unknown")
        self.assertFalse(ok)
        self.assertEqual(snapshot, state)
        self.assertIn("Choose", problem)
        with self.assertRaises(ValueError):
            mats.normalize(None, 0)

    def test_materials_have_one_identifiable_physical_item_per_branch(self):
        self.assertEqual(set(mats.ITEM_NAMES), set(mats.CHOICES))
        self.assertEqual(set(mats.ITEM_DESCRIPTIONS), set(mats.CHOICES))
        self.assertNotEqual(mats.ITEM_NAMES["preserve"], mats.ITEM_NAMES["display"])
        self.assertIn("Canvas", mats.ITEM_DESCRIPTIONS["preserve"])
        self.assertIn("oak panel", mats.ITEM_DESCRIPTIONS["display"])


if __name__ == "__main__":
    unittest.main()
