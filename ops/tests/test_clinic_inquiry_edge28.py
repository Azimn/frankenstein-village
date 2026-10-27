"""GDD-EDGE-28: signed Healer source, independent Detective and durable cot."""
import copy
import json
import sys
import unittest
from collections import UserDict
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "spike/fvillage"))

from world import clinic_inquiry_state as rules


def fixture():
    assessment = dict(day=1, hour=21, account_id=11, mask_id=111,
                      mask="HealerTester", event_id=101)
    event = {
        "id": 101, "kind": "village.clinic_assess", "status": "complete",
        "actor": {"account_id": 11, "mask_id": 111, "mask": "HealerTester"},
        "payload": {"day": 1, "hour": 21, "professional_calling": "healer"},
        "consequence": {"room_id": 301, "assessment_event_id": 101,
                        "patient_condition": "cold"},
    }
    args = dict(day=1, hour=21, account_id=22, mask_id=222,
                mask="DetectiveTester", event_id=202, source_event_id=101,
                source_account_id=11, source_mask_id=111,
                source_day=1, source_hour=21, cot_id=401, room_id=301)
    return assessment, event, args


class ClinicInquiryRules(unittest.TestCase):
    def test_signed_source_and_separate_account(self):
        assessment, event, args = fixture()
        self.assertTrue(rules.source_valid(event, assessment, 301))
        state, good, reason = rules.investigate(None, **args)
        self.assertTrue(good, reason)
        self.assertEqual(state["records"][0]["source_event_id"], 101)
        self.assertEqual(state["records"][0]["cot_id"], 401)
        self.assertNotIn("cold", rules.public_lines(state, 1))
        self.assertNotIn("HealerTester", rules.public_lines(state, 1))

    def test_forged_or_failed_ledger_source_is_rejected(self):
        assessment, event, _ = fixture()
        for path, value in (
            (("kind",), "village.clinic_treat"),
            (("status",), "consequence_failed"),
            (("id",), 999),
            (("actor", "account_id"), 999),
            (("actor", "mask_id"), 999),
            (("actor", "mask"), "Impostor"),
            (("payload", "professional_calling"), "detective"),
            (("payload", "day"), 2),
            (("payload", "hour"), 20),
            (("consequence", "room_id"), 302),
            (("consequence", "assessment_event_id"), 999),
            (("consequence", "patient_condition"), "magic"),
        ):
            with self.subTest(path=path):
                forged = copy.deepcopy(event)
                target = forged
                for part in path[:-1]:
                    target = target[part]
                target[path[-1]] = value
                self.assertFalse(rules.source_valid(forged, assessment, 301))
        self.assertFalse(rules.source_valid(None, assessment, 301))
        self.assertFalse(rules.source_valid(event, None, 301))
        self.assertFalse(rules.source_valid(event, assessment, True))

    def test_role_switching_and_forged_ids(self):
        _, _, args = fixture()
        for field, value in (("account_id", 11), ("account_id", True),
                             ("mask_id", 0), ("event_id", True),
                             ("source_event_id", -1), ("cot_id", 0),
                             ("room_id", "301"), ("day", True),
                             ("hour", 24), ("hour", -1)):
            with self.subTest(field=field, value=value):
                bad = dict(args, **{field: value})
                _state, good, _reason = rules.investigate(None, **bad)
                self.assertFalse(good)

    def test_duplicate_and_future_source(self):
        _, _, args = fixture()
        state, good, _ = rules.investigate(None, **args)
        self.assertTrue(good)
        for update in ({"event_id": 203}, {"day": 1, "hour": 22, "event_id": 203},
                       {"day": 2, "hour": 1, "event_id": 204},
                       {"day": 1, "hour": 20, "event_id": 205}):
            with self.subTest(update=update):
                _state, good, _reason = rules.investigate(
                    state, **dict(args, **update))
                self.assertFalse(good)

    def test_one_patient_day_and_bounded_history(self):
        state = None
        for day in range(1, 43):
            _, _, args = fixture()
            args.update(day=day, source_day=day, event_id=day * 10 + 2,
                        source_event_id=day * 10 + 1)
            state, good, reason = rules.investigate(state, **args)
            self.assertTrue(good, reason)
        self.assertEqual(len(state["records"]), rules.MAX_RECORDS)
        self.assertEqual(state["records"][-1]["day"], 42)
        self.assertEqual(state["records"][0]["day"], 7)

    def test_json_roundtrip_and_mapping_proxy(self):
        _, _, args = fixture()
        state, good, _ = rules.investigate(None, **args)
        self.assertTrue(good)
        restored = rules.normalize(json.loads(json.dumps(state)))
        self.assertEqual(state, restored)
        self.assertEqual(state, rules.normalize(UserDict(state)))
        restored["records"][0]["source_event_id"] = 999
        self.assertEqual(state["records"][0]["source_event_id"], 101)


if __name__ == "__main__":
    unittest.main()
