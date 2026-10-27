"""GDD-EDGE-10: signed Smith calibration must precede sourced Chronicle proof."""
import copy
import json
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "spike/fvillage"))
from world import market_standards as market


def signed(state, action, actor, event, day=1):
    return market.apply(
        state, action, day=day, hour=14, account_id=actor,
        mask_id=actor + 100, mask="Player" + str(actor), event_id=event,
    )


def ledger_event(row, action, role):
    return {
        "id": row["event_id"],
        "kind": "village.market_" + action,
        "status": "complete",
        "actor": {
            "account_id": row["account_id"],
            "mask_id": row["mask_id"], "mask": row["mask"],
        },
        "payload": {
            "action": action, "day": row["day"], "hour": row["hour"],
            "location": "Market Lane", "professional_calling": role,
        },
        "consequence": {"action": action},
    }


class Edge10SourceVerification(unittest.TestCase):
    def setUp(self):
        held, ok, error = signed(None, "hold", 5, 10)
        self.assertTrue(ok, error)
        self.state, ok, error = signed(held, "calibrate", 9, 12)
        self.assertTrue(ok, error)
        self.ledger = {
            10: ledger_event(self.state["review"], "hold", "merchant"),
            12: ledger_event(self.state["calibration"], "calibrate", "smith"),
        }

    def check(self, state=None, ledger=None):
        source = self.ledger if ledger is None else ledger
        return market.verified_sources(
            self.state if state is None else state, 1, source.get,
        )

    def test_two_independent_accounts_and_json_restart(self):
        self.assertTrue(self.check())
        persisted = json.loads(json.dumps(self.state))
        self.assertTrue(self.check(persisted))
        attested, ok, error = signed(persisted, "attest", 11, 14)
        self.assertTrue(ok, error)
        self.assertEqual(attested["attestation"]["review_event_id"], 10)
        self.assertEqual(attested["attestation"]["calibration_event_id"], 12)
        board = " ".join(market.public_lines(attested, 1))
        self.assertIn("Merchant source 10, Smith source 12", board)
        self.assertTrue(self.check(attested))
        self.assertFalse(market.verified_sources(
            market.refresh(attested, 2), 2, self.ledger.get,
        ))

    def test_missing_or_failed_receipt_never_attests(self):
        self.assertFalse(self.check(ledger={10: self.ledger[10]}))
        failed = copy.deepcopy(self.ledger)
        failed[12]["status"] = "consequence_failed"
        self.assertFalse(self.check(ledger=failed))
        failed[12]["consequence"] = None
        self.assertFalse(self.check(ledger=failed))

    def test_forged_actor_calling_or_wrong_event_kind(self):
        for field, bad in (
            ("actor", {"account_id": 44, "mask_id": 109, "mask": "Player9"}),
            ("kind", "village.market_honor"),
            ("payload", {"action": "calibrate", "day": 1, "hour": 14,
                         "location": "Market Lane", "professional_calling": "merchant"}),
            ("consequence", {"action": "honor"}),
            ("id", 99),
        ):
            with self.subTest(field=field):
                altered = copy.deepcopy(self.ledger)
                altered[12][field] = bad
                self.assertFalse(self.check(ledger=altered))

    def test_docket_forgery_duplicate_source_and_future_day(self):
        altered = copy.deepcopy(self.state)
        altered["calibration"]["event_id"] = 10
        self.assertFalse(self.check(altered))
        altered = copy.deepcopy(self.state)
        altered["review"]["choice"] = "honor"
        self.assertFalse(self.check(altered))
        self.assertFalse(market.verified_sources(None, 1, self.ledger.get))
        self.assertFalse(market.verified_sources(
            market.refresh(self.state, 2), 2, self.ledger.get,
        ))

    def test_smith_can_work_without_merchant_or_chronicler(self):
        solo, ok, error = signed(None, "calibrate", 9, 12)
        self.assertTrue(ok, error)
        self.assertFalse(market.suspended(solo, 1))
        self.assertFalse(market.verified_sources(solo, 1, self.ledger.get))
        self.assertIn("physically recalibrated", " ".join(market.public_lines(solo, 1)))


if __name__ == "__main__":
    unittest.main()
