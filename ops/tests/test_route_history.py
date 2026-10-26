"""GDD Phase A: signed daily route history remains readable and source-limited.

The public archive is a projection of the existing Square survey state, not
another source of truth. Tests include clock rollover and forged receipts.
"""
import copy
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "spike/fvillage"))
from world import route_surveys as route


class RouteHistoryTests(unittest.TestCase):
    def test_first_day_has_no_past_and_rollover_shows_signed_people(self):
        state, ok, error = route.report(
            None, 1, "red_cord", 13, "WandererTester", 101
        )
        self.assertTrue(ok, error)
        state, ok, error = route.field_decision(
            state, 1, "red_cord", "wanderer", "passability",
            False, 13, "WandererTester", 102,
        )
        self.assertTrue(ok, error)
        state, ok, error = route.field_decision(
            state, 1, "red_cord", "hound", "protect",
            False, 14, "HoundTester", 103,
        )
        self.assertTrue(ok, error)
        original = copy.deepcopy(state)
        self.assertEqual(route.history_records(state, 1), [])
        history = route.history_records(state, 2)
        self.assertEqual(len(history), 1)
        self.assertEqual(history[0]["day"], 1)
        self.assertFalse(history[0]["completed"])
        self.assertEqual(history[0]["reports"]["red_cord"]["event_id"], 101)
        self.assertEqual(history[0]["field_decisions"]["hound"]["event_id"], 103)
        self.assertEqual(
            history[0]["field_decisions"]["wanderer"]["observation"],
            "unmarked",
        )
        self.assertEqual(state, original, "History lookup must not write state")
        history[0]["reports"]["red_cord"]["mask"] = "Forged"
        self.assertEqual(state, original, "Returned history must be independent")

    def test_latest_five_days_only_and_no_backdated_current_day(self):
        state = None
        for day in range(1, 11):
            state, ok, error = route.report(
                state, day, "river_gauge", day, f"Reporter{day}", day + 100
            )
            self.assertTrue(ok, error)
        days = [x["day"] for x in route.history_records(state, 11)]
        self.assertEqual(days, [10, 9, 8, 7, 6])
        self.assertEqual(route.history_records(state, 11, limit=0), [])
        self.assertEqual(route.history_records(state, 11, limit=-3), [])

    def test_forged_boolean_receipts_never_become_real_accounts(self):
        for account, event in ((True, 20), (9, False)):
            state, ok, error = route.report(
                None, 1, "grave_marker", account, "NotSigned", event
            )
            self.assertFalse(ok)
            self.assertEqual(state["reports"], {})
            self.assertIn("signed account", error)
        raw = {
            "day": 2, "reports": {},
            "history": [{
                "day": 1, "private_patient": "should never appear",
                "reports": {
                    "red_cord": {"account_id": True, "event_id": 77, "mask": "Fake"},
                    "river_gauge": {"account_id": 8, "event_id": 78, "mask": "Real"},
                },
                "field_decisions": {},
            }],
        }
        entries = route.history_records(raw, 2)
        self.assertEqual(set(entries[0]),
                         {"day", "completed", "reports", "field_decisions"})
        self.assertEqual(set(entries[0]["reports"]), {"river_gauge"})
        self.assertEqual(entries[0]["reports"]["river_gauge"]["mask"], "Real")

    def test_invalid_archive_rows_fail_closed_without_leaking_data(self):
        raw = {
            "day": 3, "reports": {},
            "history": [
                {"day": True, "reports": {"red_cord": {"secret": "no"}}},
                {"day": 1, "reports": "not a mapping",
                 "field_decisions": "not a mapping", "private": "no"},
                {"day": "tomorrow", "reports": {}},
                {"day": 3, "reports": {}},
            ],
        }
        entries = route.history_records(raw, 3)
        self.assertEqual(len(entries), 1)
        self.assertEqual(entries[0]["day"], 1)
        self.assertEqual(entries[0]["reports"], {})
        self.assertEqual(entries[0]["field_decisions"], {})

    def test_prior_wanderer_observation_not_rewritten_by_later_protection(self):
        state, ok, error = route.field_decision(
            None, 1, "red_cord", "wanderer", "passability",
            False, 8, "Walker", 201,
        )
        self.assertTrue(ok, error)
        state, ok, error = route.field_decision(
            state, 1, "red_cord", "hound", "protect",
            False, 9, "Protector", 202,
        )
        self.assertTrue(ok, error)
        history = route.history_records(state, 2)
        public = " ".join(route.field_lines(history[0])).lower()
        self.assertIn("unmarked cord", public)
        self.assertIn("caution marker", public)
        self.assertNotIn("guaranteed safety", public.split("this does not repair")[0])


if __name__ == "__main__":
    unittest.main()
