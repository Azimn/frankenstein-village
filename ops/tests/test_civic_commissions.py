import json
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "spike" / "fvillage"))
from world.civic_commissions import refresh, pledge, finish


def stage(state, day=1, supplier=101, bundle=450, event=10):
    return pledge(state, day, supplier, "Supplier", bundle_id=bundle, event_id=event)


def complete(state, day=1, finisher=202, bundle=450, event=11, space=True):
    return finish(state, day, finisher, "Finisher",
                  carried_bundle_id=bundle, reserve_has_space=space,
                  event_id=event)


class CivicCommissionTests(unittest.TestCase):
    def test_two_accounts_exact_same_physical_object_and_no_replay(self):
        state = refresh(None, 1)
        state, accepted, error = stage(state)
        self.assertTrue(accepted, error)
        self.assertEqual(state["commission"]["bundle_id"], 450)
        rejected, accepted, _ = stage(state, supplier=301, bundle=451)
        self.assertFalse(accepted)
        self.assertEqual(rejected, state)
        rejected, accepted, _ = complete(state, finisher=101)
        self.assertFalse(accepted)
        self.assertEqual(rejected, state)
        rejected, accepted, _ = complete(state, bundle=451)
        self.assertFalse(accepted)
        self.assertEqual(rejected, state)
        rejected, accepted, _ = complete(state, space=False)
        self.assertFalse(accepted)
        self.assertEqual(rejected, state)
        state, accepted, error = complete(state)
        self.assertTrue(accepted, error)
        self.assertEqual(state["commission"]["status"], "complete")
        self.assertEqual(state["commission"]["event_ids"], [10, 11])
        again, accepted, _ = complete(state, finisher=303, event=12)
        self.assertFalse(accepted)
        self.assertEqual(again, state)

    def test_bad_bundle_and_day_renewal(self):
        state = refresh(None, 1)
        rejected, accepted, _ = stage(state, bundle=-4)
        self.assertFalse(accepted)
        self.assertEqual(rejected, state)
        state, accepted, _ = stage(state)
        state = refresh(state, 2)
        self.assertEqual(state["history"][-1]["status"], "expired")
        self.assertEqual(state["commission"]["status"], "open")
        self.assertEqual(refresh(state, 1), state)
        rejected, accepted, _ = complete(state, 1)
        self.assertFalse(accepted)
        self.assertEqual(rejected, state)

    def test_restart_and_bounded_history(self):
        state = refresh(None, 4)
        state, _, _ = stage(state, day=4, supplier=10, bundle=99)
        restored = json.loads(json.dumps(state))
        restored, accepted, _ = complete(restored, day=4, finisher=11, bundle=99)
        self.assertTrue(accepted)
        for day in range(5, 50):
            restored = refresh(restored, day)
        self.assertLessEqual(len(restored["history"]), 32)
        self.assertEqual(restored["commission"]["id"], "civic-49")

    def test_no_day_zero_or_backwards_refill(self):
        with self.assertRaises(ValueError):
            refresh(None, 0)
        state = refresh(None, 3)
        self.assertEqual(refresh(state, 2), state)


if __name__ == "__main__":
    unittest.main()
