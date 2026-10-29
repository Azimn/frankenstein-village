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


if __name__ == "__main__":
    unittest.main()
