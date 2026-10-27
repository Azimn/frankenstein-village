"""GDD-EDGE-13: signed Wanderer observation -> Chronicler public map.

Pure behavioral, negative, day-rollover and JSON restart tests. Real telnet
and process-restart checks live in the existing spike integration suite.
"""
import copy
import json
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "spike/fvillage"))
from world import route_surveys as r


def wanderer(day=4, account=21, event=101, marked=False):
    state, ok, error = r.field_decision(
        None, day, "red_cord", "wanderer", "passability",
        marked, account, "WandererTester", event,
    )
    assert ok, error
    return state


class ChroniclerWandererAdvisoryTests(unittest.TestCase):
    def test_distinct_accounts_publish_actual_snapshot(self):
        state = wanderer()
        published, ok, error = r.publish_advisory(
            state, 4, 22, "ChroniclerTester", 102, 101,
        )
        self.assertTrue(ok, error)
        item = published["advisory"]
        self.assertEqual(item["source_account_id"], 21)
        self.assertEqual(item["account_id"], 22)
        self.assertEqual(item["source_event_id"], 101)
        self.assertEqual(item["event_id"], 102)
        self.assertEqual(item["observation"], "unmarked")
        self.assertEqual(item["version"], 1)
        self.assertIn("not a current safety guarantee", r.advisory_lines(published)[0])
        self.assertIsNone(state["advisory"], "Input must not be mutated")

    def test_no_wanderer_source_no_publication(self):
        result, ok, reason = r.publish_advisory(None, 4, 22, "C", 102, 101)
        self.assertFalse(ok)
        self.assertIn("Wanderer", reason)
        self.assertIsNone(result["advisory"])

    def test_self_attestation_is_not_two_account_work(self):
        source = wanderer()
        result, ok, reason = r.publish_advisory(
            source, 4, 21, "W", 102, 101,
        )
        self.assertFalse(ok)
        self.assertIn("independent", reason)
        self.assertIsNone(result["advisory"])

    def test_forged_source_and_invalid_ids_fail_closed(self):
        source = wanderer()
        for account, event, source_id in (
            (22, 102, 999), (True, 102, 101), (22, False, 101),
            (22, 102, True), (0, 102, 101), (22, -1, 101),
        ):
            result, ok, reason = r.publish_advisory(
                source, 4, account, "C", event, source_id,
            )
            self.assertFalse(ok, reason)
            self.assertIsNone(result["advisory"])
        self.assertIsNone(source["advisory"])

    def test_duplicate_and_stale_day_are_denied_without_rewrite(self):
        state = wanderer()
        state, ok, error = r.publish_advisory(
            state, 4, 22, "C", 102, 101,
        )
        self.assertTrue(ok, error)
        original = copy.deepcopy(state)
        duplicate, ok, reason = r.publish_advisory(
            state, 4, 23, "Another", 103, 101,
        )
        self.assertFalse(ok)
        self.assertIn("already published", reason)
        self.assertEqual(duplicate, original)
        next_day = r.refresh(state, 5)
        stale, ok, reason = r.publish_advisory(
            next_day, 4, 23, "Late", 104, 101,
        )
        self.assertFalse(ok)
        self.assertIn("later village day", reason)
        self.assertEqual(stale, next_day)

    def test_later_hound_caution_does_not_rewrite_map(self):
        state = wanderer()
        state, ok, error = r.publish_advisory(
            state, 4, 22, "C", 102, 101,
        )
        self.assertTrue(ok, error)
        later, ok, error = r.field_decision(
            state, 4, "red_cord", "hound", "protect", False,
            23, "Hound", 103,
        )
        self.assertTrue(ok, error)
        self.assertEqual(later["advisory"]["observation"], "unmarked")
        self.assertEqual(later["field_decisions"]["hound"]["event_id"], 103)

    def test_json_restart_and_next_day_archive(self):
        state = wanderer(marked=True)
        state, ok, error = r.publish_advisory(
            state, 4, 22, "C", 102, 101,
        )
        self.assertTrue(ok, error)
        reloaded = r.normalize(json.loads(json.dumps(state)))
        self.assertEqual(reloaded["advisory"], state["advisory"])
        day5 = r.refresh(reloaded, 5)
        self.assertIsNone(day5["advisory"])
        self.assertEqual(day5["history"][-1]["advisory"]["source_event_id"], 101)
        self.assertIn("marked caution", r.advisory_lines(reloaded)[0])

    def test_corrupt_persisted_advisory_cannot_gain_authority(self):
        state = wanderer()
        state["advisory"] = {
            "version": True, "source_day": 4, "observation": "safe",
            "account_id": 22, "event_id": 102, "source_account_id": 21,
            "source_event_id": 101,
        }
        self.assertIsNone(r.normalize(state)["advisory"])


if __name__ == "__main__":
    unittest.main()
