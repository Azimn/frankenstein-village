"""Pure behavioral and negative tests for GDD-EDGE-33 market inquiry."""
import json
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "spike/fvillage"))
from world import market_inquiry_state as inquiry


def open_one(raw=None, **changes):
    args = dict(
        day=3, hour=12, source_day=3, source_hour=11,
        source_event_id=40, source_account_id=10, source_mask_id=100,
        detective_account_id=20, detective_mask_id=200,
        detective_mask="Detective", scale_id=300, case_event_id=41,
    )
    args.update(changes)
    return inquiry.open_case(raw, **args)


def rebut_one(raw, **changes):
    args = dict(
        day=3, hour=13, source_event_id=40,
        merchant_account_id=10, merchant_mask_id=100, event_id=42,
    )
    args.update(changes)
    return inquiry.rebut_case(raw, **args)


class MarketInquiryTests(unittest.TestCase):
    def test_independent_signed_case_and_attributed_rebuttal(self):
        rows, okay, why = open_one()
        self.assertTrue(okay, why)
        self.assertEqual(rows[0]["source_event_id"], 40)
        self.assertEqual(rows[0]["detective_account_id"], 20)
        self.assertIn("not a finding of fraud", inquiry.public_lines(rows))
        rows, okay, why = rebut_one(rows)
        self.assertTrue(okay, why)
        self.assertEqual(rows[0]["rebuttal_event_id"], 42)
        self.assertIn("remains contested", inquiry.public_lines(rows))

    def test_same_account_role_switch_denied(self):
        rows, okay, why = open_one(detective_account_id=10)
        self.assertFalse(okay)
        self.assertIn("independent account", why)
        self.assertEqual(rows, [])

    def test_unbacked_and_invalid_source_denied(self):
        for changes in (
            {"source_event_id": 0}, {"source_account_id": True},
            {"scale_id": -3}, {"case_event_id": None},
            {"detective_mask_id": 0}, {"day": 0},
            {"hour": 24}, {"source_hour": -1},
        ):
            with self.subTest(changes=changes):
                rows, okay, _ = open_one(**changes)
                self.assertFalse(okay)
                self.assertEqual(rows, [])

    def test_future_hold_and_wrong_day_denied(self):
        for changes in ({"source_day": 2}, {"source_day": 4},
                        {"source_hour": 14}, {"hour": 9}):
            rows, okay, why = open_one(**changes)
            self.assertFalse(okay)
            self.assertIn("precede", why)
            self.assertEqual(rows, [])

    def test_duplicate_source_and_clock_rewind_denied(self):
        rows, okay, _ = open_one()
        self.assertTrue(okay)
        later, okay, why = open_one(rows, case_event_id=55)
        self.assertFalse(okay)
        self.assertIn("already been investigated", why)
        later, okay, why = open_one(
            rows, day=2, source_day=2, source_hour=10,
            source_event_id=44, case_event_id=45)
        self.assertFalse(okay)
        self.assertIn("clock cannot be rewound", why)
        self.assertEqual(later, rows)

    def test_rebuttal_requires_original_merchant_and_existing_case(self):
        rows, okay, why = rebut_one([])
        self.assertFalse(okay)
        self.assertIn("No independent", why)
        rows, okay, _ = open_one()
        self.assertTrue(okay)
        for changes in (
            {"merchant_account_id": 20}, {"merchant_mask_id": 201},
            {"source_event_id": 999}, {"day": 4},
            {"hour": 11}, {"event_id": True},
        ):
            with self.subTest(changes=changes):
                result, accepted, _ = rebut_one(rows, **changes)
                self.assertFalse(accepted)
                self.assertIsNone(result[0]["rebuttal_event_id"])

    def test_rebuttal_replay_denied(self):
        rows, okay, _ = open_one()
        self.assertTrue(okay)
        rows, okay, _ = rebut_one(rows)
        self.assertTrue(okay)
        result, okay, why = rebut_one(rows, event_id=43)
        self.assertFalse(okay)
        self.assertIn("already recorded", why)
        self.assertEqual(result, rows)

    def test_json_restart_roundtrip_and_bounded_history(self):
        rows, okay, _ = open_one()
        self.assertTrue(okay)
        rows, okay, _ = rebut_one(rows)
        self.assertTrue(okay)
        restored = inquiry.normalize(json.loads(json.dumps(rows)))
        self.assertEqual(restored, rows)
        for number in range(41, 75):
            rows, okay, why = open_one(
                rows, day=number, source_day=number,
                source_event_id=1000 + number,
                case_event_id=2000 + number,
            )
            self.assertTrue(okay, why)
        self.assertEqual(len(rows), inquiry.MAX_CASES)
        self.assertEqual(rows[-1]["day"], 74)

    def test_evennia_sequence_wrapper_and_string_ids(self):
        class SaverSequence:
            def __init__(self, values):
                self.values = values

            def __iter__(self):
                return iter(self.values)

        rows, okay, why = open_one(
            day="3", source_day="3", source_event_id="40",
            detective_account_id="20")
        self.assertTrue(okay, why)
        self.assertEqual(rows[0]["day"], 3)
        self.assertEqual(rows[0]["source_event_id"], 40)
        self.assertEqual(inquiry.normalize(SaverSequence(rows)), rows)
        self.assertEqual(inquiry.normalize(json.loads(json.dumps(rows))), rows)
        rows, okay, why = rebut_one(SaverSequence(rows), event_id="42")
        self.assertTrue(okay, why)
        self.assertEqual(rows[0]["rebuttal_event_id"], 42)

    def test_no_inquiry_is_valid_solo_market_fallback(self):
        self.assertIn("No independent", inquiry.public_lines(None))
        self.assertEqual(inquiry.normalize({"fake": "case"}), [])
        self.assertEqual(inquiry.normalize([{"source_event_id": 1}]), [])


if __name__ == "__main__":
    unittest.main()
