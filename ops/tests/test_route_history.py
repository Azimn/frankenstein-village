"""Pure read-only route history: saved wrappers, rollover and forged archives."""
import copy
import sys
import unittest
from collections import UserDict, UserList
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "spike/fvillage"))
from world import route_surveys as route


class RouteHistoryTests(unittest.TestCase):
    def test_wrapped_history_is_detached_and_private_data_omitted(self):
        archive = UserList([UserDict({
            "day": 1, "completed": False,
            "reports": UserDict({"river_gauge": UserDict({
                "account_id": 7, "event_id": 19, "mask": "Witness"
            })}),
            "field_decisions": UserDict({}), "private_note": "not public",
        })])
        raw = UserDict({"day": 2, "history": archive, "reports": UserDict()})
        before = copy.deepcopy(raw)
        rows = route.history_records(raw, 2)
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["reports"]["river_gauge"]["event_id"], 19)
        self.assertNotIn("private_note", rows[0])
        rows[0]["reports"]["river_gauge"]["mask"] = "Edited"
        self.assertEqual(raw, before)

    def test_rollover_makes_bounded_sorted_old_days(self):
        state = None
        for day in range(1, 9):
            state, yes, reason = route.report(
                state, day, "river_gauge", day, f"Observer{day}", day + 100
            )
            self.assertTrue(yes, reason)
        self.assertEqual([r["day"] for r in route.history_records(state, 9)],
                         [8, 7, 6, 5, 4])
        self.assertEqual(route.history_records(state, 9, selected_day=2)[0]["day"], 2)
        self.assertFalse(route.history_records(state, 9, selected_day=9))

    def test_duplicate_and_future_days_do_not_project(self):
        old = {"day": 1, "completed": False, "reports": {
            "red_cord": {"account_id": 2, "event_id": 3, "mask": "One"},
        }, "field_decisions": {}}
        raw = {"day": 3, "history": [old, copy.deepcopy(old),
                                  dict(old, day=4)]}
        self.assertEqual(route.history_records(raw, 3), [])
        self.assertEqual(len(route.history_records(
            {"day": 3, "history": [old]}, 3
        )), 1)

    def test_bool_receipt_ids_and_private_fields_are_removed(self):
        raw = {"day": 2, "history": [{
            "day": 1, "completed": False, "patient_secret": "hidden",
            "reports": {"red_cord": {
                "account_id": True, "event_id": 3, "mask": "Forged",
            }},
            "field_decisions": {"hound": {
                "account_id": 3, "event_id": False, "site": "red_cord",
                "action": "protect", "mask": "Fake",
            }},
        }]}
        rows = route.history_records(raw, 2)
        self.assertEqual(rows[0]["reports"], {})
        self.assertEqual(rows[0]["field_decisions"], {})
        self.assertNotIn("patient_secret", rows[0])

    def test_invalid_ranges_fail_closed(self):
        raw = {"day": 1, "history": []}
        for value in (0, True, "2", None):
            self.assertEqual(route.history_records(raw, value), [])
        for value in (0, -1, True, "5", 11):
            self.assertEqual(route.history_records(raw, 2, limit=value), [])
        for value in (-1, True, "1", 0):
            self.assertEqual(route.history_records(raw, 2, selected_day=value), [])


if __name__ == "__main__":
    unittest.main()
