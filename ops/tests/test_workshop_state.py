"""Pure tests for limited daily work, custody, renewal and replay denial."""
import sys
from pathlib import Path
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "spike/fvillage"))
from world import workshop_state as w


def craft(state=None, *, day=1, hour=11, aid=10, mid=100, eid=21, item=51):
    return w.forge(
        state, day=day, hour=hour, account_id=aid, mask_id=mid,
        mask="Smith", event_id=eid, item_id=item,
    )


def deliver(state, *, day=1, hour=12, aid=10, mid=100, eid=25,
            item=51, source=21):
    return w.install(
        state, day=day, hour=hour, account_id=aid, mask_id=mid,
        mask="Carrier", event_id=eid, item_id=item,
        source_event_id=source,
    )


class WorkshopTests(unittest.TestCase):
    def test_physical_work_and_transferable_install(self):
        state, okay, error = craft()
        self.assertTrue(okay, error)
        self.assertEqual(state["offcuts"], 1)
        state, okay, error = craft(state, aid=10, eid=22, item=52)
        self.assertFalse(okay)
        self.assertIn("already forged", error)
        state, okay, error = craft(state, aid=11, mid=110, eid=22, item=52)
        self.assertTrue(okay, error)
        self.assertEqual(state["offcuts"], 0)
        # A different account can physically carry the real item and sign.
        state, okay, error = deliver(
            state, aid=18, mid=180, eid=29, item=51, source=21
        )
        self.assertTrue(okay, error)
        self.assertEqual(state["installation"]["account_id"], 18)
        self.assertEqual(state["installation"]["source_event_id"], 21)
        self.assertEqual(state["installation"]["item_id"], 51)
        self.assertIn("Carrier installed", w.public_lines(state, 1))
        duplicate, okay, error = deliver(
            state, aid=19, mid=190, eid=30, item=52, source=22
        )
        self.assertFalse(okay)
        self.assertIn("already been installed", error)
        self.assertEqual(duplicate, state)

    def test_daily_renewal_incomplete_history_and_rewind(self):
        state, okay, error = craft()
        self.assertTrue(okay, error)
        second = w.refresh(state, 2)
        self.assertEqual(second["offcuts"], w.DAILY_OFFCUTS)
        self.assertEqual(second["history"][-1]["day"], 1)
        self.assertIsNone(second["history"][-1]["installation"])
        self.assertIsNone(second["installation"])
        expired, okay, message = craft(second, day=1)
        self.assertFalse(okay)
        self.assertIn("behind", message.lower())
        self.assertEqual(expired, second)
        repaired, okay, why = deliver(
            second, day=2, eid=45, item=51, source=21
        )
        self.assertTrue(okay, why)
        refreshed = w.refresh(repaired, 3)
        self.assertEqual(refreshed["history"][-1]["installation"]["source_event_id"], 21)
        replay, okay, error = deliver(
            refreshed, day=3, eid=46, item=51, source=21
        )
        self.assertFalse(okay)
        self.assertIn("already installed", error)
        self.assertEqual(replay, refreshed)

    def test_source_event_provenance_and_invalid_input(self):
        for kwargs in (
            {"aid": 0}, {"eid": True}, {"item": -1},
            {"mid": 0}, {"hour": 24}, {"hour": -1},
        ):
            _state, okay, error = craft(**kwargs)
            self.assertFalse(okay, kwargs)
            self.assertTrue(error)
        initial = w.fresh()
        for kwargs in (
            {"aid": 0}, {"eid": True}, {"source": None},
            {"item": 0}, {"hour": 99},
        ):
            _state, okay, error = deliver(initial, **kwargs)
            self.assertFalse(okay, kwargs)
            self.assertTrue(error)
        with self.assertRaises(ValueError):
            w.refresh(initial, 0)

    def test_bounded_history_and_custody_ids(self):
        state = None
        for day in range(1, 58):
            state, okay, error = craft(
                state, day=day, eid=day * 3, item=day * 10,
            )
            self.assertTrue(okay, error)
            state, okay, error = deliver(
                state, day=day, eid=day * 3 + 1,
                item=day * 10, source=day * 3,
            )
            self.assertTrue(okay, error)
        later = w.refresh(state, 58)
        self.assertEqual(len(later["history"]), w.MAX_HISTORY)
        self.assertEqual(later["history"][-1]["day"], 57)
        snapshot = w.normalize(later)
        snapshot["history"][-1]["installation"]["mask"] = "tampered"
        self.assertNotEqual(later["history"][-1]["installation"]["mask"],
                            snapshot["history"][-1]["installation"]["mask"])


if __name__ == "__main__":
    unittest.main()
