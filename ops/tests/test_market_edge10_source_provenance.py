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

    def test_independent_accounts_required_for_public_attestation(self):
        # Role switching does not turn one account into independent witnesses.
        snapshot = copy.deepcopy(self.state)
        for actor in (5, 9):
            with self.subTest(attester_account=actor):
                denied, ok, error = signed(self.state, "attest", actor, 14)
                self.assertFalse(ok)
                self.assertIn("Independent Merchant, Smith and Chronicler", error)
                self.assertIsNone(denied["attestation"])
        self.assertEqual(self.state, snapshot)
        accepted, ok, error = signed(self.state, "attest", 11, 14)
        self.assertTrue(ok, error)
        self.assertIsNotNone(accepted["attestation"])

    def test_same_account_merchant_and_smith_cannot_be_sources(self):
        forged = copy.deepcopy(self.state)
        forged["calibration"]["account_id"] = 5
        altered_ledger = copy.deepcopy(self.ledger)
        altered_ledger[12]["actor"]["account_id"] = 5
        # Even matching docket and ledger signatures are insufficient if
        # both professional acts came from the same authenticated account.
        self.assertFalse(self.check(forged, altered_ledger))
        denied, ok, error = signed(forged, "attest", 11, 14)
        self.assertFalse(ok)
        self.assertIn("Independent Merchant, Smith and Chronicler", error)
        self.assertIsNone(denied["attestation"])

    def test_persisted_same_account_attestation_is_not_published(self):
        attested, ok, error = signed(self.state, "attest", 11, 14)
        self.assertTrue(ok, error)
        forged = copy.deepcopy(attested)
        forged["attestation"]["account_id"] = 5
        self.assertIsNone(market.normalize(forged)["attestation"])
        self.assertNotIn("attested both source events",
                         " ".join(market.public_lines(forged, 1)))

    def test_corrupt_persisted_attestation_cannot_appear_on_public_board(self):
        attested, ok, error = signed(self.state, "attest", 11, 14)
        self.assertTrue(ok, error)
        forged = copy.deepcopy(attested)
        forged["attestation"]["calibration_event_id"] = 888
        self.assertIsNone(market.normalize(forged)["attestation"])
        self.assertNotIn("attested both source events",
                         " ".join(market.public_lines(forged, 1)))
        forged = copy.deepcopy(attested)
        forged["attestation"]["event_id"] = 10
        self.assertIsNone(market.normalize(forged)["attestation"])

    def test_returning_players_see_signed_archived_market_decisions(self):
        attested, ok, error = signed(self.state, "attest", 11, 14)
        self.assertTrue(ok, error)
        day_two = market.refresh(json.loads(json.dumps(attested)), 2)
        day_two, ok, error = signed(day_two, "calibrate", 21, 22, day=2)
        self.assertTrue(ok, error)
        day_three = market.refresh(json.loads(json.dumps(day_two)), 3)
        snapshot = copy.deepcopy(day_three)
        board = " ".join(market.public_lines(day_three, 3))
        self.assertIn("Prior day 2: Smith Player21 calibrated the scale (event 22)", board)
        self.assertIn("Prior day 1: Merchant Player5 chose hold (event 10)", board)
        self.assertIn("Smith Player9 calibrated the scale (event 12)", board)
        self.assertIn("Chronicler Player11 attested sources 10 and 12 (event 14)", board)
        self.assertNotIn("record preserved", board)
        self.assertEqual(day_three, snapshot, "Public history must not mutate the archive")

        # A corrupted prior-day source cannot be laundered into a public
        # attestation merely because an archive row exists.
        corrupted = copy.deepcopy(day_three)
        corrupted["history"][0]["attestation"]["review_event_id"] = 999
        board = " ".join(market.public_lines(corrupted, 3))
        self.assertNotIn("Chronicler Player11 attested", board)
        self.assertIn("Smith Player9 calibrated", board)

    def test_public_history_is_bounded_to_three_actual_prior_days(self):
        state = self.state
        for day in range(2, 6):
            state, ok, error = signed(
                state, "honor", 30 + day, 50 + day, day=day,
            )
            self.assertTrue(ok, error)
        state = market.refresh(json.loads(json.dumps(state)), 6)
        board = " ".join(market.public_lines(state, 6))
        self.assertIn("Prior day 5:", board)
        self.assertIn("Prior day 4:", board)
        self.assertIn("Prior day 3:", board)
        self.assertNotIn("Prior day 2:", board)
        self.assertNotIn("Prior day 1:", board)

    def test_smith_can_work_without_merchant_or_chronicler(self):
        solo, ok, error = signed(None, "calibrate", 9, 12)
        self.assertTrue(ok, error)
        self.assertFalse(market.suspended(solo, 1))
        self.assertFalse(market.verified_sources(solo, 1, self.ledger.get))
        self.assertIn("physically recalibrated", " ".join(market.public_lines(solo, 1)))


if __name__ == "__main__":
    unittest.main()
