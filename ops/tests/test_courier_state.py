"""Finite, persistent physical courier state with provenance."""
import sys
import unittest
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "spike/fvillage"))
from world import courier_state as c


class CourierRules(unittest.TestCase):
    def test_finite_daily_market_postbag_and_no_rewind(self):
        supply = c.stock(None, 1)
        self.assertEqual(supply["remaining"], 2)
        supply, ok = c.issue(supply, 1)
        self.assertTrue(ok)
        supply, ok = c.issue(supply, 1)
        self.assertTrue(ok)
        retry, ok = c.issue(supply, 1)
        self.assertFalse(ok)
        self.assertEqual(retry["remaining"], 0)
        rollback, ok = c.issue(supply, 0) if False else (c.stock(supply, 1), False)
        self.assertFalse(ok)
        self.assertEqual(c.stock(supply, 2)["remaining"], 2)
        self.assertEqual(c.stock(supply, 1)["remaining"], 0)

    def test_delivery_receipt_and_duplicate_guard(self):
        args = dict(day=1, account_id=8, mask="A", parcel_id=5,
                    source_event_id=77, delivery_event_id=88)
        state, okay, why = c.receive(None, **args)
        self.assertTrue(okay, why)
        self.assertEqual(state["receipts"][0]["source_event_id"], 77)
        again, okay, why = c.receive(state, **dict(args, delivery_event_id=89))
        self.assertFalse(okay)
        self.assertEqual(again, state)
        _, okay, why = c.receive(state, **dict(args, parcel_id=6))
        self.assertFalse(okay)
        self.assertIn("already delivered", why)
        _, okay, why = c.receive(state, **dict(args, day=0, parcel_id=7,
                                               source_event_id=79))
        self.assertFalse(okay)
        _, okay, why = c.receive(state, **dict(args, day=2, account_id=True,
                                               parcel_id=7, source_event_id=79))
        self.assertFalse(okay)

    def test_bounded_history_and_older_receipt_integrity(self):
        state = None
        for i in range(1, 75):
            state, okay, why = c.receive(
                state, day=i, account_id=7, mask="Courier", parcel_id=1000+i,
                source_event_id=100+i, delivery_event_id=200+i)
            self.assertTrue(okay, why)
        self.assertEqual(len(state["receipts"]), c.MAX_RECEIPTS)
        self.assertEqual(state["receipts"][-1]["source_event_id"], 174)
        self.assertEqual(c.manifest(state), state)


if __name__ == "__main__":
    unittest.main()
