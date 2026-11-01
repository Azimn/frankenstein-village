"""Pure tests for limited daily work, custody, renewal and replay denial."""
import sys
from collections import UserDict, UserList
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

    def test_evennia_mutable_sequence_history_survives_two_reloads(self):
        # Evennia's Attribute _SaverList implements MutableSequence, not list.
        # UserList reproduces the relevant persisted container contract.
        day_one, okay, error = craft()
        self.assertTrue(okay, error)
        day_one, okay, error = craft(
            day_one, aid=11, mid=110, eid=22, item=52,
        )
        self.assertTrue(okay, error)
        self.assertEqual(day_one["offcuts"], 0)
        day_two = w.refresh(day_one, 2)
        self.assertEqual(len(day_two["history"]), 1)
        persisted = UserDict(day_two)
        persisted["history"] = UserList(
            [UserDict(row) for row in day_two["history"]]
        )
        reloaded = w.normalize(persisted)
        self.assertEqual([row["day"] for row in reloaded["history"]], [1])
        self.assertEqual(
            {craft["event_id"] for craft in reloaded["history"][0]["crafts"]},
            {21, 22},
        )
        day_two, okay, error = craft(
            persisted, day=2, aid=12, mid=120, eid=23, item=53,
        )
        self.assertTrue(okay, error)
        self.assertEqual(day_two["offcuts"], 1)
        self.assertEqual(len(day_two["history"][0]["crafts"]), 2)
        second_persisted = UserDict(day_two)
        second_persisted["history"] = UserList(
            [UserDict(row) for row in day_two["history"]]
        )
        after_second_reload = w.normalize(second_persisted)
        self.assertEqual(
            [row["day"] for row in after_second_reload["history"]], [1]
        )
        self.assertEqual(
            {craft["event_id"] for craft in after_second_reload["history"][0]["crafts"]},
            {21, 22},
        )
        self.assertEqual(after_second_reload["crafts"][0]["event_id"], 23)
        day_three = w.refresh(after_second_reload, 3)
        self.assertEqual([row["day"] for row in day_three["history"]], [1, 2])
        self.assertEqual(len(day_three["history"][0]["crafts"]), 2)
        self.assertEqual(len(day_three["history"][1]["crafts"]), 1)
        self.assertEqual(w.normalize({"day": 2, "history": "invalid"})["history"], [])

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
