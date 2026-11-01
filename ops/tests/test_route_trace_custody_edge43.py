"""Pure behavioral and adversarial tests for GDD-EDGE-43."""
import json
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "spike/fvillage"))
from world import route_trace_custody as trace


def preserve(raw=None, **overrides):
    args = {
        "day": 3, "hour": 14, "source_day": 3, "source_hour": 13,
        "source_event_id": 31, "hound_account_id": 7, "hound_mask_id": 70,
        "detective_account_id": 8, "detective_mask_id": 80,
        "detective_mask": "DetectiveTester", "cord_id": 90, "event_id": 32,
        "observed_condition": "tied_caution",
    }
    args.update(overrides)
    return trace.preserve(raw, **args)




def signed_public_fixture():
    record, okay, why = preserve()
    assert okay, why
    source = {
        "id": 31, "kind": "village.route_protected", "status": "complete",
        "actor": {"account_id": 7, "mask_id": 70, "mask": "HoundTester"},
        "payload": {
            "site": "red_cord", "role": "hound", "action": "protect",
            "location": "Northern Treeline", "day": 3, "hour": 13,
        },
        "consequence": {
            "cord_object_id": 90, "site": "red_cord", "role": "hound",
            "action": "protect", "caution_marked": True,
        },
    }
    detective = {
        "id": 32, "kind": "village.route_trace_preserved",
        "status": "complete",
        "actor": {"account_id": 8, "mask_id": 80, "mask": "DetectiveTester"},
        "payload": {
            "site": "red_cord", "professional_calling": "detective",
            "location": "Northern Treeline", "day": 3, "hour": 14,
            "cord_object_id": 90, "hound_source_event_id": 31,
        },
        "consequence": {
            "cord_object_id": 90, "hound_source_event_id": 31,
            "hound_account_id": 7, "detective_account_id": 8,
            "late_arrival": False, "observed_condition": "tied_caution",
        },
    }
    caution = {
        "event_id": 31, "account_id": 7,
        "mask": "HoundTester", "day": 3,
    }
    return record, source, detective, caution


def public_projection(record, source, detective, caution, *, cord_id=90):
    return trace.verified_public_lines(
        record, source, detective, cord_id=cord_id,
        room="Northern Treeline", caution=caution,
    )

class RouteTraceCustodyTests(unittest.TestCase):
    def test_independent_hound_and_detective_preserve_qualified_record(self):
        row, okay, why = preserve()
        self.assertTrue(okay, why)
        self.assertEqual(row["hound_account_id"], 7)
        self.assertEqual(row["detective_account_id"], 8)
        self.assertEqual(row["source_event_id"], 31)
        self.assertFalse(row["late_arrival"])
        self.assertIn("neither tracks nor a culprit", trace.public_lines(row))

    def test_late_arrival_keeps_original_source_and_limits(self):
        row, okay, why = preserve(day=4, hour=7)
        self.assertTrue(okay, why)
        self.assertTrue(row["late_arrival"])
        self.assertEqual(row["source_day"], 3)
        self.assertIn("late-arrival", trace.public_lines(row))

    def test_same_account_role_switch_rejected(self):
        row, okay, why = preserve(detective_account_id=7)
        self.assertFalse(okay)
        self.assertIsNone(row)

    def test_same_mask_role_switch_rejected(self):
        row, okay, _ = preserve(detective_mask_id=70)
        self.assertFalse(okay)
        self.assertIsNone(row)

    def test_invalid_identity_source_object_and_event_rejected(self):
        for overrides in (
            {"source_event_id": 0}, {"source_event_id": True},
            {"hound_account_id": False}, {"hound_mask_id": -1},
            {"detective_account_id": None}, {"detective_mask_id": 0},
            {"cord_id": -9}, {"event_id": True},
            {"event_id": 31}, {"observed_condition": "untouched"},
            {"day": 0}, {"source_day": 0},
            {"hour": -1}, {"hour": 24}, {"source_hour": 24},
        ):
            with self.subTest(overrides=overrides):
                row, okay, _ = preserve(**overrides)
                self.assertFalse(okay)
                self.assertIsNone(row)

    def test_future_source_and_clock_rewind_rejected(self):
        for overrides in (
            {"source_day": 4}, {"source_hour": 15},
            {"day": 2}, {"day": 3, "hour": 12},
        ):
            with self.subTest(overrides=overrides):
                row, okay, _ = preserve(**overrides)
                self.assertFalse(okay)
                self.assertIsNone(row)

    def test_duplicate_custody_is_never_overwritten(self):
        first, okay, _ = preserve()
        self.assertTrue(okay)
        row, okay, why = preserve(first, event_id=35, detective_account_id=10)
        self.assertFalse(okay)
        self.assertEqual(row, first)
        self.assertIn("already has", why)

    def test_corrupted_existing_record_fails_closed(self):
        row, okay, why = preserve({"source_event_id": 31})
        self.assertFalse(okay)
        self.assertIsNone(row)
        self.assertIn("malformed", why)

    def test_json_roundtrip_and_mapping_backed_record(self):
        row, okay, _ = preserve()
        self.assertTrue(okay)
        restored = json.loads(json.dumps(row))
        self.assertEqual(trace.normalize(restored), row)
        from collections import UserDict
        self.assertEqual(trace.normalize(UserDict(restored)), row)

    def test_boolean_and_forged_late_flag_rejected_or_rederived(self):
        row, okay, _ = preserve()
        self.assertTrue(okay)
        forged = {**row, "late_arrival": True}
        self.assertFalse(trace.normalize(forged)["late_arrival"])
        forged["hound_account_id"] = True
        self.assertIsNone(trace.normalize(forged))

    def test_no_custody_does_not_claim_a_crime_or_preservation(self):
        self.assertIn("No independent", trace.public_lines(None))
        self.assertIsNone(trace.normalize({"event_id": 1}))


    def test_first_hound_event_id_is_a_valid_distinct_source(self):
        record, okay, why = preserve(source_event_id=1, event_id=2)
        self.assertTrue(okay, why)
        self.assertEqual(record["source_event_id"], 1)
        self.assertEqual(record["event_id"], 2)

    def test_public_readback_requires_both_completed_signed_events(self):
        record, source, detective, caution = signed_public_fixture()
        output = public_projection(record, source, detective, caution)
        self.assertIn("Detective event 32", output)
        self.assertIn("Hound source 31", output)
        self.assertIn("neither tracks nor a culprit", output)

    def test_public_readback_rejects_missing_failed_and_foreign_events(self):
        from copy import deepcopy
        record, source, detective, caution = signed_public_fixture()
        for part, change in (
            ("source", None),
            ("detective", None),
            ("source", {"status": "consequence_failed"}),
            ("detective", {"status": "consequence_failed"}),
            ("source", {"kind": "village.route_inspected"}),
            ("detective", {"kind": "village.route_inspected"}),
            ("source", {"id": "31"}),
            ("detective", {"id": True}),
            ("source", {"actor": {"account_id": 99, "mask_id": 70, "mask": "HoundTester"}}),
            ("detective", {"actor": {"account_id": 8, "mask_id": 88, "mask": "DetectiveTester"}}),
            ("detective", {"actor": {"account_id": 8, "mask_id": 80, "mask": "Impostor"}}),
        ):
            with self.subTest(part=part, change=change):
                s, d = deepcopy(source), deepcopy(detective)
                if part == "source":
                    s = None if change is None else {**s, **change}
                else:
                    d = None if change is None else {**d, **change}
                output = public_projection(record, s, d, caution)
                self.assertNotIn("Detective event 32", output)

    def test_public_readback_rejects_forged_site_time_source_and_consequence(self):
        from copy import deepcopy
        record, source, detective, caution = signed_public_fixture()
        for part, section, field, forged in (
            ("source", "payload", "location", "Village Square"),
            ("source", "payload", "day", 4),
            ("source", "payload", "hour", 14),
            ("source", "consequence", "cord_object_id", 99),
            ("source", "consequence", "caution_marked", False),
            ("detective", "payload", "location", "Village Square"),
            ("detective", "payload", "day", 4),
            ("detective", "payload", "hour", 13),
            ("detective", "payload", "hound_source_event_id", 55),
            ("detective", "payload", "professional_calling", "hound"),
            ("detective", "consequence", "detective_account_id", 99),
            ("detective", "consequence", "observed_condition", "untouched"),
        ):
            with self.subTest(part=part, field=field):
                s, d = deepcopy(source), deepcopy(detective)
                target = s if part == "source" else d
                target[section][field] = forged
                self.assertNotIn(
                    "Detective event 32",
                    public_projection(record, s, d, caution),
                )
        self.assertNotIn(
            "Detective event 32",
            public_projection(record, source, detective, caution, cord_id=99),
        )
        forged_caution = {**caution, "event_id": 66}
        self.assertNotIn(
            "Detective event 32",
            public_projection(record, source, detective, forged_caution),
        )

    def test_public_readback_survives_json_roundtrip_without_trusting_raw_ids(self):
        record, source, detective, caution = signed_public_fixture()
        restore = lambda value: json.loads(json.dumps(value))
        self.assertIn(
            "Detective event 32",
            public_projection(*(restore(v) for v in (record, source, detective, caution))),
        )
        forged = {**record, "event_id": 888}
        self.assertNotIn(
            "Detective event 888",
            public_projection(forged, source, detective, caution),
        )



if __name__ == "__main__":
    unittest.main()
