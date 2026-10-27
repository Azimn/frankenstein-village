"""EDGE-12: an independent Chronicler audits a real Merchant decision."""
import copy
import json
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "spike/fvillage"))
from world import market_standards as market


def sign(state, action, *, account=4, event=10, day=1, hour=14):
    return market.apply(
        state, action, day=day, hour=hour,
        account_id=account, mask_id=account + 100,
        mask="MerchantTester" if account == 4 else "ChroniclerTester",
        event_id=event,
    )


def source(review):
    choice = review["choice"]
    return {
        "id": review["event_id"], "status": "complete",
        "kind": "village.market_" + choice,
        "actor": {
            "account_id": review["account_id"],
            "mask_id": review["mask_id"],
            "mask": review["mask"],
        },
        "payload": {
            "action": choice, "day": review["day"], "hour": review["hour"],
            "location": "Market Lane", "professional_calling": "merchant",
        },
        "consequence": {
            "action": choice, "review_event_id": review["event_id"],
        },
    }


class Edge12MarketAuditTests(unittest.TestCase):
    def test_distinct_audit_of_real_hold_changes_public_record_not_stock(self):
        held, ok, error = sign(None, "hold")
        self.assertTrue(ok, error)
        self.assertTrue(market.verified_merchant_review(held["review"], source(held["review"])))
        audited, ok, error = sign(held, "audit", account=7, event=11)
        self.assertTrue(ok, error)
        self.assertTrue(market.suspended(audited, 1))
        self.assertEqual(audited["audit"]["review_event_id"], 10)
        self.assertEqual(audited["audit"]["review_choice"], "hold")
        self.assertIn("independently audited Merchant hold", " ".join(market.public_lines(audited, 1)))
        self.assertIn("independent Chronicler audit", " ".join(market.personal_agenda(audited, 1, 107)))
        self.assertIsNone(held["audit"])
        fixed, ok, error = sign(audited, "calibrate", account=8, event=12)
        self.assertTrue(ok, error)
        self.assertFalse(market.suspended(fixed, 1))
        self.assertEqual(fixed["audit"], audited["audit"])

    def test_missing_source_same_account_duplicate_and_early_clock(self):
        state, ok, error = sign(None, "audit", account=7)
        self.assertFalse(ok)
        self.assertIn("Merchant decision", error)
        held, ok, _ = sign(None, "hold")
        bad, ok, error = sign(held, "audit", account=4, event=11)
        self.assertFalse(ok)
        self.assertIn("separate account", error)
        self.assertEqual(bad, held)
        bad, ok, error = sign(held, "audit", account=7, event=11, hour=13)
        self.assertFalse(ok)
        self.assertIn("cannot precede", error)
        audited, ok, _ = sign(held, "audit", account=7, event=11)
        self.assertTrue(ok)
        duplicate, ok, error = sign(audited, "audit", account=8, event=12)
        self.assertFalse(ok)
        self.assertIn("already been audited", error)
        self.assertEqual(duplicate, audited)

    def test_honor_and_json_restart_day_rollover(self):
        honored, ok, _ = sign(None, "honor")
        self.assertTrue(ok)
        audited, ok, error = sign(honored, "audit", account=7, event=11)
        self.assertTrue(ok, error)
        restored = market.normalize(json.loads(json.dumps(audited)))
        self.assertEqual(restored["audit"], audited["audit"])
        self.assertFalse(market.suspended(restored, 1))
        tomorrow = market.refresh(restored, 2)
        self.assertIsNone(tomorrow["audit"])
        self.assertEqual(tomorrow["history"][-1]["audit"]["review_event_id"], 10)
        self.assertIn("previous day's standards work is archived",
                      " ".join(market.personal_agenda(tomorrow, 2, 107)))
        earlier, ok, error = sign(tomorrow, "audit", account=8, event=13, day=1)
        self.assertFalse(ok)
        self.assertIn("later village day", error)
        self.assertEqual(earlier, tomorrow)

    def test_source_validation_rejects_forged_and_failed_events(self):
        held, ok, _ = sign(None, "hold")
        self.assertTrue(ok)
        review = held["review"]
        good = source(review)
        self.assertTrue(market.verified_merchant_review(review, good))
        for field, bad_value in (
            ("id", 999), ("status", "consequence_failed"),
            ("kind", "village.market_honor"),
        ):
            bad = copy.deepcopy(good)
            bad[field] = bad_value
            with self.subTest(field=field):
                self.assertFalse(market.verified_merchant_review(review, bad))
        for section, field, value in (
            ("actor", "account_id", 999),
            ("actor", "mask_id", 999),
            ("actor", "mask", "Impostor"),
            ("payload", "professional_calling", "smith"),
            ("payload", "location", "Village Square"),
            ("payload", "day", 2),
            ("payload", "hour", 10),
            ("payload", "action", "honor"),
            ("consequence", "review_event_id", 999),
            ("consequence", "action", "honor"),
        ):
            bad = copy.deepcopy(good)
            bad[section][field] = value
            with self.subTest(section=section, field=field):
                self.assertFalse(market.verified_merchant_review(review, bad))
        self.assertFalse(market.verified_merchant_review(review, None))
        self.assertFalse(market.verified_merchant_review(review, {"status": "complete"}))
        self.assertFalse(market.verified_merchant_review({}, good))
        self.assertFalse(market.verified_merchant_review(review, {**good, "id": True}))

    def test_normalization_refuses_forged_audit_fields(self):
        held, ok, _ = sign(None, "hold")
        audited, ok, _ = sign(held, "audit", account=7, event=11)
        self.assertTrue(ok)
        bad = copy.deepcopy(audited)
        bad["audit"]["review_event_id"] = True
        self.assertIsNone(market.normalize(bad)["audit"])
        bad = copy.deepcopy(audited)
        bad["audit"]["review_choice"] = "invent"
        self.assertIsNone(market.normalize(bad)["audit"])


if __name__ == "__main__":
    unittest.main()
