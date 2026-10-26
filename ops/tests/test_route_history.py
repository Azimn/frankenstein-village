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

    def test_select_older_day_beyond_recent_five_without_changing_history(self):
        state = None
        for day in range(1, 19):
            state, ok, error = route.report(
                state, day, "river_gauge", day, f"Reporter{day}", day + 100
            )
            self.assertTrue(ok, error)
        before = copy.deepcopy(state)
        self.assertEqual(
            [row["day"] for row in route.history_records(state, 19)],
            [18, 17, 16, 15, 14],
        )
        selected = route.history_records(state, 19, selected_day=3)
        self.assertEqual(len(selected), 1)
        self.assertEqual(selected[0]["day"], 3)
        self.assertEqual(selected[0]["reports"]["river_gauge"]["mask"], "Reporter3")
        self.assertEqual(selected[0]["reports"]["river_gauge"]["event_id"], 103)
        self.assertEqual(state, before, "Selecting history must not mutate world")
        selected[0]["reports"]["river_gauge"]["mask"] = "Tampered"
        self.assertEqual(state, before, "Archive projections are independent")

    def test_exact_day_lookup_fails_closed_for_absent_future_or_invalid_days(self):
        state, ok, error = route.report(
            None, 1, "grave_marker", 9, "Observer", 81
        )
        self.assertTrue(ok, error)
        self.assertEqual(route.history_records(state, 2, selected_day=2), [])
        self.assertEqual(route.history_records(state, 2, selected_day=50), [])
        for requested in (True, False, -1, 0, "1", 1.5):
            with self.subTest(requested=requested):
                self.assertEqual(
                    route.history_records(state, 2, selected_day=requested),
                    [],
                )
        self.assertEqual(
            route.history_records(state, 2, selected_day=1)[0]["day"], 1
        )

    def test_selected_archive_day_is_bounded_by_retained_thirty_days(self):
        state = None
        for day in range(1, route.MAX_HISTORY + 6):
            state, ok, error = route.report(
                state, day, "grave_marker", day, f"Walker{day}", day + 200
            )
            self.assertTrue(ok, error)
        future_day = route.MAX_HISTORY + 6
        self.assertEqual(
            route.history_records(state, future_day, selected_day=1), []
        )
        newest = route.history_records(
            state, future_day, selected_day=future_day - 1
        )
        self.assertEqual(newest[0]["day"], future_day - 1)

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

    def test_daily_board_projection_ignores_malformed_and_stale_archive_flags(self):
        # The public survey board now uses this validated projection instead
        # of indexing unchecked persisted history dictionaries directly.
        raw = {
            "day": 3, "reports": {},
            "history": [
                {"day": 1, "completed": True, "reports": "corrupt"},
                {"day": 2, "completed": True, "reports": {
                    "river_gauge": {
                        "account_id": 4, "event_id": 20, "mask": "Observer"
                    }
                }},
                {"bad": "untrusted"},
            ],
        }
        latest = route.history_records(raw, 3, limit=1)
        self.assertEqual(len(latest), 1)
        self.assertEqual(latest[0]["day"], 2)
        self.assertFalse(latest[0]["completed"],
                         "Stale completion flags must not fabricate surveys")
        self.assertEqual(set(latest[0]["reports"]), {"river_gauge"})
        self.assertEqual(route.history_records(raw, 3, selected_day=1)[0]["reports"], {})

    def test_corrupt_current_receipts_do_not_crash_board_or_erase_valid_archive(self):
        signed = {
            "day": 1, "completed": False,
            "reports": {
                "river_gauge": {
                    "account_id": 7, "event_id": 19, "mask": "RiverWitness"
                }
            },
            "field_decisions": {},
        }
        for bad in ("damaged", 42, True, [1, 2], {"unknown": "value"}):
            with self.subTest(bad=bad):
                raw = {
                    "day": 2, "reports": bad, "field_decisions": bad,
                    "history": [copy.deepcopy(signed)],
                }
                before = copy.deepcopy(raw)
                current = route.normalize(raw)
                self.assertEqual(current["reports"], {})
                self.assertEqual(current["field_decisions"], {})
                archive = route.history_records(raw, 2)
                self.assertEqual(archive[0]["reports"]["river_gauge"]["mask"],
                                 "RiverWitness")
                self.assertEqual(raw, before, "Read-only board must not rewrite saves")
                after, accepted, error = route.report(
                    raw, 2, "grave_marker", 8, "NewWitness", 21
                )
                self.assertTrue(accepted, error)
                self.assertEqual(after["reports"]["grave_marker"]["event_id"], 21)
                self.assertEqual(len(after["history"]), 1)

    def test_invalid_root_and_history_shapes_fail_closed_without_crashing(self):
        for raw in (7, True, "broken", [7], [("bad",)]):
            with self.subTest(raw=raw):
                self.assertEqual(route.normalize(raw)["reports"], {})
                self.assertEqual(route.history_records(raw, 2), [])
                state, accepted, error = route.report(
                    raw, 2, "red_cord", 9, "Observer", 23
                )
                self.assertTrue(accepted, error)
                self.assertEqual(state["reports"]["red_cord"]["event_id"], 23)
        for invalid in ("not an archive", 99, True, {"day": 1}):
            with self.subTest(history=invalid):
                raw = {"day": 2, "reports": {}, "history": invalid}
                self.assertEqual(route.history_records(raw, 2), [])
                self.assertEqual(route.normalize(raw)["history"], [])

    def test_unhashable_wanderer_observation_cannot_break_public_archive(self):
        bad = {
            "account_id": 4, "event_id": 8, "mask": "Malformed",
            "action": "passability", "observation": ["unmarked"],
        }
        signed = {
            "account_id": 5, "event_id": 9, "mask": "Protector",
            "action": "protect",
        }
        raw = {
            "day": 2, "reports": {},
            "field_decisions": {"wanderer": bad, "hound": signed},
            "history": [{
                "day": 1, "reports": {},
                "field_decisions": {"wanderer": dict(bad, observation={"x": 1}),
                                    "hound": signed},
            }],
        }
        before = copy.deepcopy(raw)
        current = route.normalize(raw)
        self.assertEqual(set(current["field_decisions"]), {"hound"})
        archive = route.history_records(raw, 2)
        self.assertEqual(set(archive[0]["field_decisions"]), {"hound"})
        self.assertEqual(raw, before)

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
