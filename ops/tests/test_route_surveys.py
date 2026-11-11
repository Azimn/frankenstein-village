"""Pure deterministic and adversarial route survey tests."""
import sys
from pathlib import Path
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "spike/fvillage"))
from world import route_surveys as r


class SurveyTests(unittest.TestCase):
    def test_collaboration_repeatability_and_event_receipts(self):
        state = None
        for index, site in enumerate(r.SITES):
            account = 101 + index
            state, ok, error = r.report(
                state, 6, site, account, f"Mask{account}", index + 20,
            )
            self.assertTrue(ok, error)
            self.assertEqual(state["reports"][site]["event_id"], index + 20)
            self.assertEqual(r.complete(state), index == len(r.SITES) - 1)
        same, ok, error = r.report(state, 6, r.SITES[0], 999, "Fake", 88)
        self.assertFalse(ok)
        self.assertIn("already signed", error)
        self.assertEqual(same, state)
        next_day = r.refresh(state, 7)
        self.assertEqual(next_day["day"], 7)
        self.assertEqual(next_day["reports"], {})
        self.assertEqual(len(next_day["history"]), 1)
        self.assertTrue(next_day["history"][0]["completed"])
        self.assertEqual(len(next_day["history"][0]["reports"]), len(r.SITES))
        later, ok, err = r.report(next_day, 7, r.SITES[0], 101, "Mask101", 90)
        self.assertTrue(ok, err)
        self.assertEqual(later["reports"][r.SITES[0]]["event_id"], 90)

    def test_expired_unfinished_days_and_no_clock_rewind(self):
        state, ok, err = r.report(None, 2, "red_cord", 3, "First", 30)
        self.assertTrue(ok, err)
        advanced = r.refresh(state, 4)
        self.assertFalse(advanced["history"][0]["completed"])
        self.assertEqual(len(advanced["history"][0]["reports"]), 1)
        rewind, ok, message = r.report(advanced, 3, "grave_marker", 2, "Back", 44)
        self.assertFalse(ok)
        self.assertIn("later village day", message)
        self.assertEqual(rewind, advanced)

    def test_invalid_actions_never_create_state(self):
        for ident, account, event in [
            ("forbidden", 1, 3), ("grave_marker", 0, 1),
            ("grave_marker", 1, -1), ("grave_marker", "x", 5),
            ("grave_marker", True, 5), ("grave_marker", 1, True),
            ("grave_marker", 1.0, 5), ("grave_marker", 1, 5.0),
            ("grave_marker", "1", 5), ("grave_marker", 1, "5"),
        ]:
            state, ok, err = r.report(None, 1, ident, account, "A", event)
            self.assertFalse(ok)
            self.assertEqual(state["reports"], {})
            self.assertTrue(err)
        with self.assertRaises(ValueError):
            r.refresh(None, 0)

    def test_persisted_survey_receipts_reject_coerced_identifiers(self):
        for field in ("account_id", "event_id"):
            for invalid in (True, 1.0, "1", False, -1, None):
                with self.subTest(field=field, invalid=invalid):
                    record = {"account_id": 7, "event_id": 11, "mask": "Surveyor"}
                    record[field] = invalid
                    raw = {"day": 2, "reports": {"grave_marker": record}}
                    self.assertEqual(r.normalize(raw)["reports"], {})
        valid = {"day": 2, "reports": {
            "grave_marker": {"account_id": 7, "event_id": 11, "mask": "Surveyor"}
        }}
        self.assertEqual(r.normalize(valid)["reports"]["grave_marker"]["event_id"], 11)

    def test_field_decision_requires_exact_signed_identifiers(self):
        for field in ("account_id", "event_id"):
            for invalid in (True, 1.0, "1", False, -1, None):
                with self.subTest(field=field, invalid=invalid):
                    ids = {"account_id": 7, "event_id": 11}
                    ids[field] = invalid
                    state, ok, error = r.field_decision(
                        None, 2, "red_cord", "hound", "protect", False,
                        ids["account_id"], "Hound", ids["event_id"],
                    )
                    self.assertFalse(ok)
                    self.assertEqual(state["field_decisions"], {})
                    self.assertTrue(error)
                    persisted = {"day": 2, "field_decisions": {
                        "hound": {"site": "red_cord", "action": "protect",
                                  "mask": "Hound", **ids}
                    }}
                    self.assertEqual(r.normalize(persisted)["field_decisions"], {})
        state, ok, error = r.field_decision(
            None, 2, "red_cord", "hound", "protect", False, 7, "Hound", 11,
        )
        self.assertTrue(ok, error)
        self.assertEqual(state["field_decisions"]["hound"]["event_id"], 11)

    def test_persisted_corroboration_rejects_coerced_identifiers(self):
        hound = {"account_id": 7, "event_id": 11, "mask": "Hound",
                 "action": "protect", "retied_previous_day": False}
        wanderer = {"account_id": 8, "event_id": 12, "mask": "Wanderer",
                    "action": "passability", "observation": "marked_caution"}
        valid_joint = {"event_id": 13, "hound_event_id": 11,
                       "account_id": 8, "observation": "marked_caution"}
        def normalized(joint):
            return r.normalize({"day": 2, "field_decisions": {
                "hound": hound,
                "wanderer": {**wanderer, "corroboration": joint},
            }})["field_decisions"]["wanderer"]
        self.assertEqual(normalized(valid_joint)["corroboration"]["event_id"], 13)
        for field in ("event_id", "hound_event_id", "account_id"):
            for invalid in (True, 1.0, "1", False, -1, None):
                with self.subTest(field=field, invalid=invalid):
                    self.assertNotIn("corroboration",
                        normalized({**valid_joint, field: invalid}))

    def test_persisted_editorial_advisory_rejects_coerced_identifiers(self):
        wanderer = {"account_id": 8, "event_id": 12, "mask": "Wanderer",
                    "action": "passability", "observation": "marked_caution"}
        valid = {"account_id": 9, "event_id": 13, "source_account_id": 8,
                 "source_event_id": 12, "source_day": 2, "version": 1,
                 "observation": "marked_caution", "mask": "Chronicler"}
        def normalized(advisory):
            return r.normalize({"day": 2,
                "field_decisions": {"wanderer": wanderer},
                "advisory": advisory})["advisory"]
        self.assertEqual(normalized(valid)["event_id"], 13)
        for field in ("account_id", "event_id", "source_account_id",
                      "source_event_id", "source_day", "version"):
            for invalid in (True, 1.0, str(valid[field]), False, None):
                with self.subTest(field=field, invalid=invalid):
                    self.assertIsNone(normalized({**valid, field: invalid}))

    def test_live_chronicler_publication_rejects_coerced_signed_ids(self):
        state, ok, error = r.field_decision(
            None, 2, "red_cord", "wanderer", "passability", False,
            8, "Wanderer", 12,
        )
        self.assertTrue(ok, error)
        valid = {"account_id": 9, "event_id": 13, "source_event_id": 12}
        for field in valid:
            for invalid in (True, False, 1.0, "1", None, 0, -1):
                with self.subTest(field=field, invalid=invalid):
                    ids = {**valid, field: invalid}
                    result, accepted, message = r.publish_advisory(
                        state, 2, ids["account_id"], "Chronicler",
                        ids["event_id"], ids["source_event_id"],
                    )
                    self.assertFalse(accepted)
                    self.assertIsNone(result["advisory"])
                    self.assertIn("identifiers", message)
        published, accepted, message = r.publish_advisory(
            state, 2, 9, "Chronicler", 13, 12,
        )
        self.assertTrue(accepted, message)
        self.assertEqual(published["advisory"]["source_event_id"], 12)
        repeated, accepted, message = r.publish_advisory(
            published, 2, 10, "Another", 14, 12,
        )
        self.assertFalse(accepted)
        self.assertEqual(repeated["advisory"]["event_id"], 13)

    def test_history_is_bounded_and_does_not_mutate_previous_snapshots(self):
        state = r.fresh()
        for day in range(1, 90):
            state, ok, err = r.report(state, day, "river_gauge", 5, "A", day)
            self.assertTrue(ok, err)
        self.assertEqual(len(state["history"]), r.MAX_HISTORY)
        self.assertEqual(state["history"][-1]["day"], 88)
        original = state["history"][-1]["reports"]["river_gauge"]["mask"]
        newer = r.refresh(state, 90)
        newer["history"][-1]["reports"]["river_gauge"]["mask"] = "Modified"
        self.assertEqual(state["history"][-1]["reports"]["river_gauge"]["mask"], original)


if __name__ == "__main__":
    unittest.main()
