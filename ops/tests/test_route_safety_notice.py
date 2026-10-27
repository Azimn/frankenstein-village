"""GDD EDGE-16: source-bound Hound field evidence and independent Chronicler notice."""
import copy
import json
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "spike/fvillage"))
from world import route_surveys as routes


def assessed(*, marked=True, day=3, account=17, event=101):
    state, ok, error = routes.field_decision(
        None, day, "red_cord", "hound", "assess", marked,
        account, "HoundTester", event,
    )
    assert ok, error
    return state


def signed_source(*, marked=True, day=3, account=17, event=101):
    return {
        "id": event, "status": "complete",
        "kind": "village.route_hazard_assessed",
        "actor": {"account_id": account, "mask_id": 170,
                  "mask": "HoundTester"},
        "payload": {"site": "red_cord", "role": "hound", "action": "assess",
                    "location": "The Northern Treeline",
                    "day": day, "hour": 11},
        "consequence": {"site": "red_cord", "role": "hound",
                        "action": "assess", "day": day,
                        "cord_object_id": 72, "square_room_id": 20,
                        "caution_marked": marked,
                        "interpretation": "marked_caution" if marked else "unmarked"},
    }


def notice(state, source=None, *, day=3, hour=12, account=29, event=102):
    return routes.publish_safety_notice(
        state, day=day, hour=hour, account_id=account,
        mask_id=290, mask="ChroniclerTester", event_id=event,
        source=signed_source(day=day) if source is None else source,
    )


class SafetyNoticeTests(unittest.TestCase):
    def test_two_distinct_callings_and_public_consequence(self):
        state = assessed()
        before = copy.deepcopy(state)
        result, ok, error = notice(state)
        self.assertTrue(ok, error)
        self.assertEqual(state, before, "Signing mutated the original state")
        row = result["safety_notice"]
        self.assertEqual(row["source_event_id"], 101)
        self.assertEqual(row["event_id"], 102)
        self.assertNotEqual(row["source_account_id"], row["account_id"])
        lines = " ".join(routes.field_lines(result))
        self.assertIn("Hound event 101", lines)
        self.assertIn("notice event 102", lines)
        self.assertIn("No injury or monster is established", lines)
        self.assertEqual(result["field_decisions"]["hound_assessment"]["event_id"], 101)

    def test_repeatable_daily_evidence_and_persistent_history(self):
        first = assessed(marked=False)
        source = signed_source(marked=False)
        first, ok, err = notice(first, source)
        self.assertTrue(ok, err)
        serialized = json.loads(json.dumps(first))
        second = routes.refresh(serialized, 4)
        self.assertIsNone(second["safety_notice"])
        self.assertEqual(second["history"][-1]["safety_notice"]["source_event_id"], 101)
        self.assertEqual(second["history"][-1]["safety_notice"]["observation"], "unmarked")
        self.assertIn("unmarked cord", " ".join(routes.field_lines(first)))
        second, ok, err = routes.field_decision(
            second, 4, "red_cord", "hound", "assess", True, 17,
            "HoundTester", 105,
        )
        self.assertTrue(ok, err)
        third, ok, err = routes.publish_safety_notice(
            second, day=4, hour=12, account_id=29, mask_id=290,
            mask="ChroniclerTester", event_id=106,
            source=signed_source(day=4, event=105),
        )
        self.assertTrue(ok, err)
        self.assertEqual(third["safety_notice"]["source_event_id"], 105)
        self.assertEqual(third["history"][-1]["safety_notice"]["source_event_id"], 101)

    def test_reject_same_account_and_repeated_publication(self):
        state = assessed()
        same, ok, err = notice(state, account=17)
        self.assertFalse(ok)
        self.assertIn("independent account", err)
        self.assertIsNone(same["safety_notice"])
        signed, ok, err = notice(state)
        self.assertTrue(ok, err)
        repeated, ok, err = notice(signed, event=103)
        self.assertFalse(ok)
        self.assertIn("already been published", err)
        self.assertEqual(repeated, signed)

    def test_reject_forged_failed_or_mismatched_source(self):
        state = assessed()
        for field, value in (
            ("status", "consequence_failed"),
            ("kind", "village.route_protected"),
            ("id", 999),
        ):
            source = signed_source()
            source[field] = value
            unchanged, ok, err = notice(state, source)
            self.assertFalse(ok, (field, err))
            self.assertIsNone(unchanged["safety_notice"])
        for path, value in (
            (("actor", "account_id"), 18),
            (("actor", "mask"), "OtherHound"),
            (("actor", "mask_id"), True),
            (("payload", "role"), "wanderer"),
            (("payload", "location"), "Village Square"),
            (("payload", "day"), 2),
            (("payload", "hour"), True),
            (("consequence", "cord_object_id"), 0),
            (("consequence", "interpretation"), "unmarked"),
            (("consequence", "caution_marked"), False),
        ):
            source = signed_source()
            source[path[0]][path[1]] = value
            unchanged, ok, err = notice(state, source)
            self.assertFalse(ok, (path, err))
            self.assertIsNone(unchanged["safety_notice"])

    def test_no_source_backdated_notice_or_invalid_actor(self):
        empty, ok, err = notice(None)
        self.assertFalse(ok)
        self.assertIn("Hound assessment", err)
        state = assessed()
        for changes in ({"hour": 10}, {"account": True},
                        {"event": 0}, {"day": 2}):
            _, ok, err = notice(state, **changes)
            self.assertFalse(ok, changes)
        self.assertFalse(routes.verified_hound_assessment(
            state["field_decisions"]["hound_assessment"], None, 3
        ))
        later = routes.refresh(state, 4)
        _, ok, err = routes.publish_safety_notice(
            later, day=3, hour=12, account_id=29, mask_id=290,
            mask="Chron", event_id=103, source=signed_source(),
        )
        self.assertFalse(ok)
        self.assertIn("later village day", err)

    def test_hound_assess_is_independent_of_protection_and_wanderer(self):
        first, ok, err = routes.field_decision(
            None, 3, "red_cord", "wanderer", "passability", False,
            13, "Wanderer", 90,
        )
        self.assertTrue(ok, err)
        protected, ok, err = routes.field_decision(
            first, 3, "red_cord", "hound", "protect", False,
            17, "HoundTester", 99,
        )
        self.assertTrue(ok, err)
        assessed_state, ok, err = routes.field_decision(
            protected, 3, "red_cord", "hound", "assess", True,
            17, "HoundTester", 101,
        )
        self.assertTrue(ok, err)
        self.assertEqual(set(assessed_state["field_decisions"]),
                         {"wanderer", "hound", "hound_assessment"})
        self.assertEqual(assessed_state["field_decisions"]["wanderer"]["observation"],
                         "unmarked")
        duplicate, ok, err = routes.field_decision(
            assessed_state, 3, "red_cord", "hound", "assess", True,
            19, "OtherHound", 111,
        )
        self.assertFalse(ok)
        self.assertEqual(duplicate, assessed_state)


if __name__ == "__main__":
    unittest.main()
