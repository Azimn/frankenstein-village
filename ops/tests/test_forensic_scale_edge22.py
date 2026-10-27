"""EDGE-22: Smith calibration and independent Detective custody contract."""
import copy
import json
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "spike/fvillage"))
from world import forensic_scale as fs


def fixture():
    calibration = {
        "account_id": 11, "mask_id": 110, "mask": "SmithTester",
        "event_id": 40, "day": 2, "hour": 14,
    }
    source = {
        "id": 40, "kind": "village.market_calibrate", "status": "complete",
        "actor": {"account_id": 11, "mask_id": 110, "mask": "SmithTester"},
        "payload": {
            "action": "calibrate", "day": 2, "hour": 14,
            "location": "Market Lane", "professional_calling": "smith",
        },
        "consequence": {"calibration_event_id": 40},
    }
    return calibration, source


def attempt(raw=None, calibration=None, source=None, **overrides):
    if calibration is None or source is None:
        good_calibration, good_source = fixture()
        if calibration is None:
            calibration = good_calibration
        if source is None:
            source = good_source
    args = {
        "calibration": calibration, "source_event": source,
        "account_id": 22, "mask_id": 220, "mask": "DetectiveTester",
        "day": 2, "hour": 15, "event_id": 41,
        "scale_id": 99, "market_id": 88,
    }
    args.update(overrides)
    return fs.inspect(raw, **args)


class ForensicScaleTests(unittest.TestCase):
    def test_real_separate_account_custody_is_qualified_and_persistent(self):
        calibration, source = fixture()
        old = copy.deepcopy((calibration, source))
        state, ok, why = attempt(calibration=calibration, source=source)
        self.assertTrue(ok, why)
        self.assertEqual((calibration, source), old)
        self.assertEqual(state[0]["source_event_id"], 40)
        self.assertEqual(state[0]["scale_id"], 99)
        self.assertEqual(state[0]["smith_account_id"], 11)
        self.assertIn("does not establish", fs.public_lines(state, 2))
        saved = json.loads(json.dumps(state))
        self.assertEqual(fs.normalize(saved), state)
        self.assertIn("may use trade inspect", fs.public_lines(saved, 3))

    def test_same_account_switching_cannot_self_certify(self):
        state, ok, why = attempt(account_id=11, mask_id=300)
        self.assertFalse(ok)
        self.assertIn("own work", why)
        self.assertEqual(state, [])

    def test_no_calibration_or_missing_source_event(self):
        _, source = fixture()
        state, ok, why = attempt(calibration={}, source=source)
        self.assertFalse(ok)
        self.assertIn("incomplete", why)
        state, ok, why = attempt(source={})
        self.assertFalse(ok)
        self.assertIn("provenance", why)

    def test_forged_source_identity_kind_status_and_consequence(self):
        cal, src = fixture()
        for section, field, value in (
            ("root", "kind", "village.market_honor"),
            ("root", "status", "recorded"),
            ("root", "id", 999),
            ("actor", "account_id", 22),
            ("actor", "mask_id", 999),
            ("actor", "mask", "Unknown"),
            ("payload", "professional_calling", "detective"),
            ("payload", "action", "honor"),
            ("payload", "location", "Village Square"),
            ("payload", "day", 3),
            ("payload", "hour", 18),
            ("consequence", "calibration_event_id", 999),
        ):
            tampered = copy.deepcopy(src)
            target = tampered if section == "root" else tampered[section]
            target[field] = value
            state, ok, why = attempt(calibration=cal, source=tampered)
            self.assertFalse(ok, (section, field, why))
            self.assertEqual(state, [])

    def test_duplicate_and_rewind_refused_without_mutation(self):
        state, ok, why = attempt()
        self.assertTrue(ok, why)
        original = copy.deepcopy(state)
        again, ok, why = attempt(state, event_id=42, account_id=23)
        self.assertFalse(ok)
        self.assertIn("already", why)
        self.assertEqual(again, original)
        older, ok, why = attempt(state, day=1, event_id=43)
        self.assertFalse(ok)
        self.assertIn("rewound", why)
        self.assertEqual(state, original)

    def test_late_source_and_invalid_clock(self):
        for changes in ({"hour": 13}, {"day": 0}, {"hour": 24},
                        {"hour": True}, {"day": True}):
            _, ok, why = attempt(**changes)
            self.assertFalse(ok, changes)
        cal, src = fixture()
        cal["day"] = 1
        _, ok, why = attempt(calibration=cal, source=src)
        self.assertFalse(ok)
        self.assertIn("today", why)

    def test_malformed_history_and_forged_record_fail_closed(self):
        for raw in ({}, "false", [{"day": 2}], [True]):
            _, ok, why = attempt(raw)
            self.assertFalse(ok)
            self.assertIn("malformed", why)
        good, ok, _ = attempt()
        self.assertTrue(ok)
        good[0]["smith_account_id"] = 22
        _, ok, why = attempt(good, day=3)
        self.assertFalse(ok)
        self.assertIn("malformed", why)

    def test_invalid_ids_and_source_metadata(self):
        for changes in ({"account_id": True}, {"mask_id": 0},
                        {"event_id": "41"}, {"scale_id": None},
                        {"market_id": -1}, {"mask": ""}):
            _, ok, why = attempt(**changes)
            self.assertFalse(ok, changes)
        cal, src = fixture()
        cal["account_id"] = True
        _, ok, why = attempt(calibration=cal, source=src)
        self.assertFalse(ok)
        cal, src = fixture()
        src["actor"] = None
        _, ok, why = attempt(calibration=cal, source=src)
        self.assertFalse(ok)


if __name__ == "__main__":
    unittest.main()
