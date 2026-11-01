"""Main-compatible Chronicler advisory plus renewable EDGE-41 physical Hound caution.

Pure signed-state checks only. Authenticated clients and cold restart require
the separate Evennia regression; these tests do not claim human acceptance.
"""
import json
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "spike/fvillage"))
from world import route_surveys as route


def observed(day, *, marked, state, event):
    return route.field_decision(
        state, day, "red_cord", "wanderer", "passability", marked,
        22, "Wanderer", event,
    )


def signed_map(state, event_id, *, square_id=88):
    item = state["advisory"]
    return {
        "id": event_id, "kind": "village.route_map_published",
        "status": "complete",
        "actor": {"account_id": 33, "mask": "Chronicler"},
        "payload": {
            "site": "red_cord", "day": item["source_day"], "version": 1,
            "source_event_id": item["source_event_id"],
            "source_account_id": item["source_account_id"],
        },
        "consequence": {
            "square_room_id": square_id, "day": item["source_day"],
            "version": 1, "source_event_id": item["source_event_id"],
            "source_account_id": item["source_account_id"],
            "observation": item["observation"],
        },
    }


class AdvisoryRenewalCompatibility(unittest.TestCase):
    def test_independent_signed_map_and_next_day_retying_survive_json(self):
        first, ok, why = route.field_decision(
            None, 1, "red_cord", "hound", "protect", False,
            11, "Hound", 101,
        )
        self.assertTrue(ok, why)
        first, ok, why = observed(1, marked=True, state=first, event=102)
        self.assertTrue(ok, why)
        first, ok, why = route.publish_advisory(
            first, 1, 33, "Chronicler", 103, 102,
        )
        self.assertTrue(ok, why)
        self.assertTrue(route.verified_advisory_publication(
            first, signed_map(first, 103), square_id=88,
        ))
        self.assertIn("Public route map", " ".join(route.advisory_lines(first)))
        second = route.refresh(json.loads(json.dumps(first)), 2)
        self.assertEqual(second["history"][-1]["advisory"]["event_id"], 103)
        self.assertIsNone(second["advisory"])
        second, ok, why = route.field_decision(
            second, 2, "red_cord", "hound", "protect", True,
            11, "Hound", 104, caution_day=1,
        )
        self.assertTrue(ok, why)
        self.assertTrue(second["field_decisions"]["hound"]["retied_previous_day"])
        second, ok, why = observed(2, marked=True, state=second, event=105)
        self.assertTrue(ok, why)
        second, ok, why = route.publish_advisory(
            second, 2, 33, "Chronicler", 106, 105,
        )
        self.assertTrue(ok, why)
        restored = route.normalize(json.loads(json.dumps(second)))
        self.assertTrue(restored["field_decisions"]["hound"]["retied_previous_day"])
        self.assertTrue(route.verified_advisory_publication(
            restored, signed_map(restored, 106), square_id=88,
        ))
        self.assertIn("re-tied", " ".join(route.field_lines(restored)))

    def test_forged_publication_and_same_account_are_refused(self):
        state, ok, why = observed(3, marked=False, state=None, event=205)
        self.assertTrue(ok, why)
        duplicate_actor, ok, why = route.publish_advisory(
            state, 3, 22, "Wanderer", 206, 205,
        )
        self.assertFalse(ok)
        self.assertIsNone(duplicate_actor["advisory"])
        state, ok, why = route.publish_advisory(
            state, 3, 33, "Chronicler", 206, 205,
        )
        self.assertTrue(ok, why)
        good = signed_map(state, 206)
        self.assertTrue(route.verified_advisory_publication(
            state, good, square_id=88,
        ))
        for field, replacement in (
            ("status", "pending"), ("kind", "village.route_protected"),
            ("id", 207),
        ):
            with self.subTest(field=field):
                forged = dict(good, **{field: replacement})
                self.assertFalse(route.verified_advisory_publication(
                    state, forged, square_id=88,
                ))
        self.assertFalse(route.verified_advisory_publication(
            state, good, square_id=99,
        ))
        forged = json.loads(json.dumps(good))
        forged["consequence"]["source_event_id"] = 999
        self.assertFalse(route.verified_advisory_publication(
            state, forged, square_id=88,
        ))
        self.assertEqual(route.normalize(state)["advisory"]["event_id"], 206)


if __name__ == "__main__":
    unittest.main()
