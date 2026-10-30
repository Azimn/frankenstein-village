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


def signed_events():
    """Canonical event fixture matching the actual market inquiry publisher."""
    return {
        40: {
            "id": 40, "kind": "village.market_hold", "status": "complete",
            "actor": {"account_id": 10, "mask_id": 100, "mask": "Merchant"},
            "payload": {
                "action": "hold", "professional_calling": "merchant",
                "day": 3, "hour": 11, "location": "Market Lane",
            },
            "consequence": {
                "action": "hold", "review_event_id": 40,
                "market_distribution_held": True,
            },
        },
        41: {
            "id": 41, "kind": "village.market_inquiry_opened",
            "status": "complete",
            "actor": {"account_id": 20, "mask_id": 200, "mask": "Detective"},
            "payload": {
                "action": "investigate", "professional_calling": "detective",
                "day": 3, "hour": 12, "source_event_id": 40,
                "scale_id": 300, "market_room_id": 301,
            },
            "consequence": {
                "source_event_id": 40, "scale_id": 300,
                "market_room_id": 301, "case_event_id": 41,
                "rebuttal_event_id": None,
            },
        },
        42: {
            "id": 42, "kind": "village.market_inquiry_rebutted",
            "status": "complete",
            "actor": {"account_id": 10, "mask_id": 100, "mask": "Merchant"},
            "payload": {
                "action": "rebut", "professional_calling": "merchant",
                "day": 3, "hour": 13, "source_event_id": 40,
                "scale_id": 300, "market_room_id": 301,
            },
            "consequence": {
                "source_event_id": 40, "scale_id": 300,
                "market_room_id": 301, "case_event_id": 41,
                "rebuttal_event_id": 42,
            },
        },
    }


def signed_lines(rows, events=None):
    events = signed_events() if events is None else events
    return inquiry.public_lines(rows, event_lookup=events.get, room_id=301)



class MarketInquiryTests(unittest.TestCase):
    def test_independent_signed_case_and_attributed_rebuttal(self):
        rows, okay, why = open_one()
        self.assertTrue(okay, why)
        self.assertEqual(rows[0]["source_event_id"], 40)
        self.assertEqual(rows[0]["detective_account_id"], 20)
        self.assertIn("not a finding of fraud", signed_lines(rows))
        rows, okay, why = rebut_one(rows)
        self.assertTrue(okay, why)
        self.assertEqual(rows[0]["rebuttal_event_id"], 42)
        self.assertIn("remains contested", signed_lines(rows))

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

    def test_fractional_or_coerced_signed_fields_fail_closed(self):
        # int(40.9) silently becomes a different canonical event ID.
        # The same truncation must never rewrite an account, day, or hour.
        invalid_open = (
            ("source_event_id", 40.9),
            ("source_account_id", 10.5),
            ("source_mask_id", 100.5),
            ("detective_account_id", 20.5),
            ("detective_mask_id", 200.5),
            ("scale_id", 300.5),
            ("case_event_id", 41.5),
            ("day", 3.9),
            ("source_day", 3.9),
            ("hour", 12.9),
            ("source_hour", 11.9),
            ("source_event_id", "40.0"),
            ("source_event_id", "4e1"),
            ("source_event_id", ["40"]),
            ("hour", {"hour": 12}),
        )
        for field, value in invalid_open:
            with self.subTest(operation="open", field=field, value=value):
                result, accepted, _ = open_one(**{field: value})
                self.assertFalse(accepted)
                self.assertEqual(result, [])

        rows, accepted, reason = open_one()
        self.assertTrue(accepted, reason)
        for field, value in (
            ("source_event_id", 40.9),
            ("merchant_account_id", 10.9),
            ("merchant_mask_id", 100.9),
            ("event_id", 42.9),
            ("day", 3.9),
            ("hour", 13.9),
        ):
            with self.subTest(operation="rebut", field=field):
                result, accepted, _ = rebut_one(rows, **{field: value})
                self.assertFalse(accepted)
                self.assertEqual(result, rows)
                self.assertIsNone(result[0]["rebuttal_event_id"])

        for field, value in (
            ("source_event_id", 40.9),
            ("detective_account_id", 20.9),
            ("source_hour", 11.9),
            ("hour", 12.9),
            ("day", 3.9),
        ):
            with self.subTest(operation="restore", field=field):
                self.assertEqual(inquiry.normalize([{**rows[0], field: value}]), [])

        restored, accepted, reason = open_one(
            day=" 3 ", source_day="3", hour="12", source_hour="11",
            source_event_id="40", detective_account_id="20",
        )
        self.assertTrue(accepted, reason)
        self.assertEqual(inquiry.normalize(json.loads(json.dumps(restored))), restored)

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


    def test_public_readback_requires_real_completed_event_chain(self):
        rows, okay, why = open_one()
        self.assertTrue(okay, why)
        self.assertIn("not verified", inquiry.public_lines(rows))
        self.assertIn("independently examined", signed_lines(rows))
        original = signed_events()
        mutations = (
            (41, None),
            (41, ("kind", "village.market_inquiry_rebutted")),
            (41, ("status", "consequence_failed")),
            (41, ("actor", {"account_id": 10, "mask_id": 200, "mask": "Detective"})),
            (41, ("payload", {**original[41]["payload"], "source_event_id": 999})),
            (41, ("payload", {**original[41]["payload"], "scale_id": 999})),
            (41, ("payload", {**original[41]["payload"], "market_room_id": 999})),
            (41, ("consequence", {**original[41]["consequence"], "case_event_id": 999})),
            (40, ("status", "consequence_failed")),
            (40, ("payload", {**original[40]["payload"], "day": 4})),
            (40, ("consequence", {**original[40]["consequence"], "review_event_id": 999})),
        )
        for event_id, mutation in mutations:
            with self.subTest(event_id=event_id, mutation=mutation):
                events = json.loads(json.dumps(original))
                if mutation is None:
                    del events[event_id]
                else:
                    field, value = mutation
                    events[event_id][field] = value
                self.assertIn("not verified", signed_lines(rows, events))
                self.assertNotIn("independently examined", signed_lines(rows, events))

    def test_forged_rebuttal_fails_closed_but_historic_signed_reply_survives(self):
        rows, okay, _ = open_one()
        self.assertTrue(okay)
        rows, okay, _ = rebut_one(rows)
        self.assertTrue(okay)
        events = signed_events()
        self.assertIn("remains contested", signed_lines(rows, events))
        for event_id, change in (
            (42, None),
            (42, ("kind", "village.market_inquiry_opened")),
            (42, ("actor", {"account_id": 20, "mask_id": 100, "mask": "Merchant"})),
            (42, ("payload", {**events[42]["payload"], "scale_id": 999})),
            (42, ("consequence", {**events[42]["consequence"], "rebuttal_event_id": 999})),
        ):
            with self.subTest(event_id=event_id, change=change):
                corrupted = json.loads(json.dumps(events))
                if change is None:
                    del corrupted[event_id]
                else:
                    field, value = change
                    corrupted[event_id][field] = value
                text = signed_lines(rows, corrupted)
                self.assertIn("not verified", text)
                self.assertNotIn("remains contested", text)
        forged = json.loads(json.dumps(rows))
        forged[0]["rebuttal_event_id"] = 999991
        self.assertIn("not verified", signed_lines(forged, events))
        restored = inquiry.normalize(json.loads(json.dumps(rows)))
        self.assertEqual(restored, rows)
        self.assertIn("remains contested", signed_lines(restored, events))
        self.assertIn("not verified", inquiry.public_lines(restored, event_lookup=events.get, room_id=999))

    def test_no_inquiry_is_valid_solo_market_fallback(self):
        self.assertIn("No independent", inquiry.public_lines(None))
        self.assertEqual(inquiry.normalize({"fake": "case"}), [])
        self.assertEqual(inquiry.normalize([{"source_event_id": 1}]), [])


if __name__ == "__main__":
    unittest.main()
