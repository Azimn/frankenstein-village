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


def signed_events():
    calibration, source = fixture()
    history, accepted, reason = attempt(calibration=calibration, source=source)
    assert accepted, reason
    inquiry = {
        "id": 41, "kind": fs.INQUIRY_KIND, "status": "complete",
        "actor": {
            "account_id": 22, "mask_id": 220, "mask": "DetectiveTester",
        },
        "payload": {
            "action": "inspect", "day": 2, "hour": 15,
            "location": "Market Lane", "scale_object_id": 99,
            "smith_source_event_id": 40,
            "professional_calling": "detective",
        },
        "consequence": {
            "scale_object_id": 99, "market_room_id": 88,
            "smith_source_event_id": 40, "finding": fs.FINDING,
            "day": 2,
        },
    }
    return history, {40: source, 41: inquiry}


def signed_public(history, events, *, scale_id=99, market_id=88):
    return fs.public_lines(
        history, 2, event_lookup=events.get,
        scale_id=scale_id, market_id=market_id,
    )


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
        events = signed_events()[1]
        self.assertIn("does not establish", signed_public(state, events))
        self.assertIn("cannot be verified", fs.public_lines(state, 2))
        saved = json.loads(json.dumps(state))
        self.assertEqual(fs.normalize(saved), state)
        self.assertIn("may use trade inspect", fs.public_lines(saved, 3))

    def test_public_custody_requires_completed_original_events(self):
        history, events = signed_events()
        saved = json.loads(json.dumps(history))
        self.assertIn("Detective DetectiveTester", signed_public(saved, events))
        self.assertIn("cannot be verified", signed_public(saved, {}))
        for absent in (40, 41):
            missing = copy.deepcopy(events)
            missing.pop(absent)
            self.assertIn("cannot be verified", signed_public(saved, missing))
        for field, value in (("scale_id", 999), ("market_id", 999)):
            altered = copy.deepcopy(saved)
            altered[0][field] = value
            self.assertIn("cannot be verified", signed_public(altered, events))
        self.assertIn("cannot be verified", signed_public(saved, events, scale_id=100))
        self.assertIn("cannot be verified", signed_public(saved, events, market_id=89))

    def test_public_custody_rejects_forged_event_provenance(self):
        history, events = signed_events()
        attacks = (
            (40, "root", "kind", "village.market_honor"),
            (40, "root", "status", "consequence_failed"),
            (40, "root", "id", 999991),
            (40, "actor", "account_id", 22),
            (40, "actor", "mask_id", True),
            (40, "payload", "action", "honor"),
            (40, "payload", "professional_calling", "merchant"),
            (40, "payload", "location", "Village Square"),
            (40, "payload", "day", 3),
            (40, "payload", "hour", 16),
            (40, "consequence", "calibration_event_id", 999992),
            (41, "root", "kind", "village.market_honor"),
            (41, "root", "status", "consequence_failed"),
            (41, "root", "id", 999993),
            (41, "actor", "account_id", 11),
            (41, "actor", "mask_id", 999),
            (41, "actor", "mask", "FalseDetective"),
            (41, "payload", "action", "calibrate"),
            (41, "payload", "professional_calling", "smith"),
            (41, "payload", "location", "Village Square"),
            (41, "payload", "day", 3),
            (41, "payload", "hour", 12),
            (41, "payload", "scale_object_id", 100),
            (41, "payload", "smith_source_event_id", 999991),
            (41, "consequence", "scale_object_id", 100),
            (41, "consequence", "market_room_id", 89),
            (41, "consequence", "smith_source_event_id", 999991),
            (41, "consequence", "finding", "The Detective proved fraud."),
            (41, "consequence", "day", 3),
        )
        for eid, section, field, value in attacks:
            with self.subTest(event=eid, section=section, field=field):
                forged = copy.deepcopy(events)
                target = forged[eid] if section == "root" else forged[eid][section]
                target[field] = value
                self.assertIn("cannot be verified", signed_public(history, forged))
                self.assertNotIn("Detective DetectiveTester inspected",
                                 signed_public(history, forged))
        forged = copy.deepcopy(events)
        forged[40]["payload"]["hour"] = True
        self.assertIn("cannot be verified", signed_public(history, forged))
        forged = copy.deepcopy(events)
        forged[41]["actor"] = None
        self.assertIn("cannot be verified", signed_public(history, forged))

    def test_public_custody_corrupt_persisted_row_and_lookup_fail_closed(self):
        history, events = signed_events()
        for key, value in (
            ("event_id", 999992), ("source_event_id", 999991),
            ("event_id", True), ("source_event_id", 41),
            ("account_id", 11), ("smith_account_id", 22),
            ("mask", "Impostor"), ("hour", 14),
        ):
            with self.subTest(key=key, value=value):
                forged = json.loads(json.dumps(history))
                forged[0][key] = value
                self.assertNotIn("Detective DetectiveTester inspected",
                                 signed_public(forged, events))
        def unavailable(_):
            raise RuntimeError("ledger unavailable")
        self.assertIn("cannot be verified", fs.public_lines(
            history, 2, event_lookup=unavailable,
            scale_id=99, market_id=88,
        ))


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
