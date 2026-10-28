"""GDD-EDGE-16: independent sourced Hound and Chronicler caution notice."""
import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "spike/fvillage"))
from world import route_surveys as state


class CautionNoticeTests(unittest.TestCase):
    def setUp(self):
        self.s, ok, reason = state.field_decision(
            None, 4, "red_cord", "hound", "protect", False,
            11, "Hound", 40)
        self.assertTrue(ok, reason)
        self.base = dict(day=4, hour=12, account_id=22, mask_id=222,
                         mask="Chronicler", event_id=41, source_event_id=40,
                         source_account_id=11, source_mask_id=111,
                         source_cord_id=500, source_hour=10)

    def publish(self, **overrides):
        return state.publish_caution(self.s, **{**self.base, **overrides})

    def test_distinct_roles_sign_source_bound_public_notice(self):
        s, ok, why = self.publish()
        self.assertTrue(ok, why)
        self.assertEqual(s["caution_notice"]["source_event_id"], 40)
        self.assertIn("not a verified threat", " ".join(state.field_lines(s)))
        self.assertEqual(s["field_decisions"]["hound"]["event_id"], 40)

    def test_same_account_cannot_self_publish_after_role_switch(self):
        _, ok, _ = self.publish(account_id=11)
        self.assertFalse(ok)

    def test_reject_missing_source(self):
        _, ok, _ = state.publish_caution(None, **self.base)
        self.assertFalse(ok)

    def test_reject_forged_source_id_and_account(self):
        for change in ({"source_event_id": 99}, {"source_account_id": 99}):
            with self.subTest(change=change):
                _, ok, _ = self.publish(**change)
                self.assertFalse(ok)

    def test_reject_future_source_and_invalid_hours(self):
        for change in ({"source_hour": 13}, {"hour": 24},
                       {"hour": True}, {"source_hour": -1}):
            with self.subTest(change=change):
                _, ok, _ = self.publish(**change)
                self.assertFalse(ok)

    def test_reject_invalid_or_boolean_identifiers(self):
        for key in ("account_id", "mask_id", "event_id", "source_event_id",
                    "source_account_id", "source_mask_id", "source_cord_id"):
            for value in (True, 0, "not-an-id"):
                with self.subTest(key=key, value=value):
                    _, ok, _ = self.publish(**{key: value})
                    self.assertFalse(ok)

    def test_duplicate_publication_rejected(self):
        self.s, ok, _ = self.publish()
        self.assertTrue(ok)
        _, ok, why = self.publish(event_id=42)
        self.assertFalse(ok)
        self.assertIn("already published", why)

    def test_json_restart_preserves_source_and_blocks_replay(self):
        self.s, ok, _ = self.publish()
        self.assertTrue(ok)
        restored = json.loads(json.dumps(self.s))
        normalized = state.normalize(restored)
        self.assertEqual(normalized["caution_notice"]["account_id"], 22)
        _, ok, _ = state.publish_caution(restored, **{**self.base, "event_id": 42})
        self.assertFalse(ok)

    def test_day_rollover_archives_but_does_not_republish(self):
        self.s, ok, _ = self.publish()
        self.assertTrue(ok)
        newer = state.refresh(json.loads(json.dumps(self.s)), 5)
        self.assertIsNone(newer["caution_notice"])
        self.assertEqual(newer["history"][-1]["caution_notice"]["event_id"], 41)
        self.assertIsNone(state.normalize(newer)["caution_notice"])

    def test_old_day_cannot_overwrite_new_day(self):
        self.s, ok, _ = self.publish()
        self.assertTrue(ok)
        newer = state.refresh(self.s, 5)
        _, ok, _ = state.publish_caution(newer, **self.base)
        self.assertFalse(ok)

    def test_corrupted_notice_does_not_become_public_truth(self):
        self.s, ok, _ = self.publish()
        self.assertTrue(ok)
        for change in ({"source_event_id": 999}, {"source_account_id": 22},
                       {"day": 8}, {"hour": "invalid"}):
            with self.subTest(change=change):
                broken = json.loads(json.dumps(self.s))
                broken["caution_notice"].update(change)
                self.assertIsNone(state.normalize(broken)["caution_notice"])


    def test_damaged_persisted_notice_keeps_daily_slot_consumed(self):
        self.s, ok, why = self.publish()
        self.assertTrue(ok, why)
        damaged = json.loads(json.dumps(self.s))
        damaged["caution_notice"]["source_event_id"] = 999
        normalized = state.normalize(damaged)
        self.assertIsNone(normalized["caution_notice"])
        self.assertEqual(normalized["caution_publication_event_id"], 41)
        _, accepted, reason = state.publish_caution(
            damaged, **{**self.base, "event_id": 42})
        self.assertFalse(accepted)
        self.assertIn("already published", reason)

        # Upgrade a pre-guard saved Square without erasing its completed slot.
        legacy = json.loads(json.dumps(damaged))
        del legacy["caution_publication_event_id"]
        self.assertEqual(state.normalize(legacy)["caution_publication_event_id"], 41)
        _, accepted, reason = state.publish_caution(
            legacy, **{**self.base, "event_id": 42})
        self.assertFalse(accepted)
        self.assertIn("already published", reason)

        # A new village day can receive a fresh independently sourced notice.
        rolled = state.refresh(damaged, 5)
        self.assertIsNone(rolled["caution_publication_event_id"])
        self.assertEqual(rolled["history"][-1]["caution_publication_event_id"], 41)

    def test_later_day_renewed_hound_source_can_be_published(self):
        first, ok, _ = self.publish()
        self.assertTrue(ok)
        next_day = state.refresh(first, 5)
        renewed, ok, why = state.field_decision(
            next_day, 5, "red_cord", "hound", "protect", True,
            11, "Hound", 50, caution_day=4)
        self.assertTrue(ok, why)
        self.assertTrue(renewed["field_decisions"]["hound"]["retied_previous_day"])
        newer, ok, why = state.publish_caution(
            renewed, day=5, hour=13, account_id=22, mask_id=222,
            mask="Chronicler", event_id=51, source_event_id=50,
            source_account_id=11, source_mask_id=111,
            source_cord_id=500, source_hour=11)
        self.assertTrue(ok, why)
        self.assertEqual(newer["caution_notice"]["source_event_id"], 50)
        self.assertEqual(newer["history"][-1]["caution_notice"]["event_id"], 41)
        self.assertIn("re-tied", " ".join(state.field_lines(newer)))

    def test_later_day_renewal_rejects_missing_or_same_day_source(self):
        next_day = state.refresh(self.s, 5)
        for caution_day in (None, 5, 6, True, "4"):
            with self.subTest(caution_day=caution_day):
                _, ok, _ = state.field_decision(
                    next_day, 5, "red_cord", "hound", "protect", True,
                    11, "Hound", 50, caution_day=caution_day)
                self.assertFalse(ok)
        renewed, ok, _ = state.field_decision(
            next_day, 5, "red_cord", "hound", "protect", True,
            11, "Hound", 50, caution_day=4)
        self.assertTrue(ok)
        _, ok, _ = state.field_decision(
            renewed, 5, "red_cord", "hound", "protect", True,
            11, "Hound", 51, caution_day=4)
        self.assertFalse(ok)

    def test_malformed_persisted_decision_containers_never_authorize_notice(self):
        self.s, ok, why = self.publish()
        self.assertTrue(ok, why)
        for bad in ("corrupt", 17, [1], {"hound": ["bad"]}):
            with self.subTest(bad=bad):
                damaged = json.loads(json.dumps(self.s))
                damaged["field_decisions"] = bad
                restored = state.normalize(damaged)
                self.assertEqual(restored["field_decisions"], {})
                self.assertIsNone(restored["caution_notice"])
                _, allowed, _ = state.publish_caution(
                    damaged, **{**self.base, "event_id": 42})
                self.assertFalse(allowed)

    def test_malformed_report_and_history_containers_do_not_crash(self):
        self.s, ok, why = self.publish()
        self.assertTrue(ok, why)
        rolled = state.refresh(self.s, 5)
        valid_history = rolled["history"][-1]
        self.assertEqual(valid_history["caution_notice"]["event_id"], 41)
        for bad in ("corrupt", 17, [1], {"invalid": "entry"}):
            with self.subTest(bad=bad):
                damaged = json.loads(json.dumps(rolled))
                damaged["reports"] = bad
                damaged["history"] = bad
                normalized = state.normalize(damaged)
                self.assertEqual(normalized["reports"], {})
                self.assertEqual(normalized["history"], [])
                self.assertIsInstance(state.field_lines(normalized), list)
        mixed = json.loads(json.dumps(rolled))
        mixed["history"] = [
            None, {"day": 4, "completed": True, "reports": {}},
            {"day": 4, "completed": False, "reports": {"bogus": {}}},
            valid_history,
        ]
        restored = state.normalize(mixed)
        self.assertEqual(len(restored["history"]), 1)
        self.assertEqual(restored["history"][0]["caution_notice"]["event_id"], 41)

    def test_solo_hound_still_has_public_firsthand_record(self):
        self.assertIsNone(self.s["caution_notice"])
        self.assertIn("frayed cord was tied", " ".join(state.field_lines(self.s)))
        self.assertEqual(self.s["field_decisions"]["hound"]["event_id"], 40)


if __name__ == "__main__":
    unittest.main()
