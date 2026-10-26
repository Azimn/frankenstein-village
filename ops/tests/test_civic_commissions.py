import json
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "spike" / "fvillage"))
from world.civic_commissions import refresh, pledge, finish, cancel


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

    def test_many_days_restart_and_attempted_duplicate_claims(self):
        state = None
        for day in range(1, 251):
            state = refresh(state, day)
            expected_id = f"civic-{day}"
            state, accepted, _ = stage(
                state, day=day, supplier=100 + day, bundle=1000 + day,
                event=2 * day,
            )
            self.assertTrue(accepted)
            duplicate, accepted, _ = stage(
                state, day=day, supplier=9000, bundle=9000,
                event=9999,
            )
            self.assertFalse(accepted)
            self.assertEqual(duplicate, state)
            state = json.loads(json.dumps(state))
            state, accepted, _ = complete(
                state, day=day, finisher=500 + day,
                bundle=1000 + day, event=2 * day + 1,
            )
            self.assertTrue(accepted)
            self.assertEqual(state["commission"]["id"], expected_id)
            self.assertLessEqual(len(state["history"]), 32)
        self.assertEqual(state["history"][-1]["id"], "civic-250")

    def test_no_day_zero_or_backwards_refill(self):
        with self.assertRaises(ValueError):
            refresh(None, 0)
        state = refresh(None, 3)
        self.assertEqual(refresh(state, 2), state)
        stale, accepted, _ = stage(state, day=2)
        self.assertFalse(accepted)
        self.assertEqual(stale, state)
        stale, accepted, _ = complete(state, day=2)
        self.assertFalse(accepted)
        self.assertEqual(stale, state)


    def test_t13_supplier_cancels_before_neighbor_delivers(self):
        state, accepted, error = stage(refresh(None, 1))
        self.assertTrue(accepted, error)
        state, accepted, error = cancel(state, 1, 101, event_id=12)
        self.assertTrue(accepted, error)
        self.assertEqual(state["commission"]["status"], "cancelled")
        self.assertEqual(state["commission"]["bundle_id"], 450)
        self.assertEqual(state["commission"]["event_ids"], [10, 12])
        self.assertEqual(len(state["history"]), 1)
        self.assertEqual(state["history"][0]["status"], "cancelled")

        # A different account may still physically hold the bundle. Canceling
        # the ORDER cannot delete that object, mint a rack delivery or reopen it.
        replay, accepted, _ = complete(state, finisher=202, event=13)
        self.assertFalse(accepted)
        self.assertEqual(replay, state)
        replay, accepted, _ = cancel(state, 1, 101, event_id=14)
        self.assertFalse(accepted)
        self.assertEqual(replay, state)

        restored = json.loads(json.dumps(state))
        renewed = refresh(restored, 2)
        self.assertEqual(renewed["commission"]["status"], "open")
        self.assertEqual(len(renewed["history"]), 1)
        self.assertEqual(renewed["history"][0]["status"], "cancelled")
        self.assertEqual(renewed["history"][0]["bundle_id"], 450)

    def test_t13_neighbor_finishes_before_supplier_cancels(self):
        state, accepted, error = stage(refresh(None, 1))
        self.assertTrue(accepted, error)
        state, accepted, error = complete(state, finisher=202, event=11)
        self.assertTrue(accepted, error)
        self.assertEqual(state["commission"]["status"], "complete")
        self.assertEqual(len(state["history"]), 1)
        rejected, accepted, _ = cancel(state, 1, 101, event_id=12)
        self.assertFalse(accepted)
        self.assertEqual(rejected, state)
        rejected, accepted, _ = complete(state, finisher=303, event=13)
        self.assertFalse(accepted)
        self.assertEqual(rejected, state)
        self.assertEqual(len(state["history"]), 1)
        self.assertEqual(state["history"][0]["event_ids"], [10, 11])

    def test_t13_only_original_supplier_can_cancel_live_pledge(self):
        state = refresh(None, 1)
        rejected, accepted, _ = cancel(state, 1, 101, event_id=12)
        self.assertFalse(accepted)
        self.assertEqual(rejected, state)
        state, accepted, error = stage(state)
        self.assertTrue(accepted, error)
        with self.assertRaises(ValueError):
            cancel(state, 0, 101, event_id=12)
        for account, day, event in (
            (202, 1, 12), (101, 1, 0), (101, 1, -2)
        ):
            rejected, accepted, _ = cancel(state, day, account, event_id=event)
            self.assertFalse(accepted)
            self.assertEqual(rejected, state)
        rejected, accepted, _ = cancel(state, 1, 101, event_id=True)
        self.assertFalse(accepted)
        self.assertEqual(rejected, state)


if __name__ == "__main__":
    unittest.main()
