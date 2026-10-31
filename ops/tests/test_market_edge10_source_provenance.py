"""GDD-EDGE-10: signed Smith calibration must precede sourced Chronicle proof."""
import ast
import copy
import json
import sys
import unittest
from contextlib import nullcontext
from pathlib import Path
from types import SimpleNamespace

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "spike/fvillage"))
from world import market_standards as market


def signed(state, action, actor, event, day=1):
    return market.apply(
        state, action, day=day, hour=14, account_id=actor,
        mask_id=actor + 100, mask="Player" + str(actor), event_id=event,
    )


def ledger_event(row, action, role, *, review_id=None, calibration_id=None,
                 distribution_held=False):
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
        "consequence": {
            "action": action,
            "market_distribution_held": distribution_held,
            "review_event_id": review_id,
            "calibration_event_id": calibration_id,
        },
    }


class Edge10SourceVerification(unittest.TestCase):
    def setUp(self):
        held, ok, error = signed(None, "hold", 5, 10)
        self.assertTrue(ok, error)
        self.state, ok, error = signed(held, "calibrate", 9, 12)
        self.assertTrue(ok, error)
        self.ledger = {
            10: ledger_event(self.state["review"], "hold", "merchant",
                             review_id=10, distribution_held=True),
            12: ledger_event(self.state["calibration"], "calibrate", "smith",
                             review_id=10, calibration_id=12),
        }

    def check(self, state=None, ledger=None):
        source = self.ledger if ledger is None else ledger
        return market.verified_sources(
            self.state if state is None else state, 1, source.get,
        )

    def test_consequence_schema_and_source_links_fail_closed(self):
        # The ledger's completed flag and action alone cannot prove that the
        # physical market consequence actually happened.
        cases = (
            (10, "market_distribution_held", "missing", None),
            (10, "market_distribution_held", "replace", False),
            (10, "market_distribution_held", "replace", 1),
            (12, "market_distribution_held", "missing", None),
            (12, "market_distribution_held", "replace", True),
            (12, "market_distribution_held", "replace", "false"),
            (10, "review_event_id", "missing", None),
            (10, "review_event_id", "replace", 12),
            (10, "review_event_id", "replace", True),
            (10, "calibration_event_id", "missing", None),
            (10, "calibration_event_id", "replace", 12),
            (12, "review_event_id", "missing", None),
            (12, "review_event_id", "replace", 99),
            (12, "calibration_event_id", "missing", None),
            (12, "calibration_event_id", "replace", 10),
            (12, "calibration_event_id", "replace", True),
        )
        for event_id, field, operation, bad in cases:
            with self.subTest(event=event_id, field=field, bad=bad):
                forged = copy.deepcopy(self.ledger)
                consequence = forged[event_id]["consequence"]
                if operation == "missing":
                    del consequence[field]
                else:
                    consequence[field] = bad
                self.assertFalse(self.check(ledger=forged))
        self.assertTrue(self.check(), "Valid signed freight-free market sources survive")

    def test_smith_first_then_merchant_honor_has_historical_source_links(self):
        # A Smith may calibrate before the Merchant honors prices. Each
        # completed event only links to receipts already present at that time.
        first, ok, error = signed(None, "calibrate", 9, 12)
        self.assertTrue(ok, error)
        state, ok, error = signed(first, "honor", 5, 13)
        self.assertTrue(ok, error)
        ledger = {
            12: ledger_event(state["calibration"], "calibrate", "smith",
                             calibration_id=12),
            13: ledger_event(state["review"], "honor", "merchant",
                             review_id=13, calibration_id=12),
        }
        self.assertTrue(market.verified_sources(state, 1, ledger.get))
        restored = json.loads(json.dumps(state))
        self.assertTrue(market.verified_sources(restored, 1, ledger.get))
        signed_state, ok, error = signed(restored, "attest", 11, 14)
        self.assertTrue(ok, error)
        self.assertEqual(signed_state["attestation"]["review_event_id"], 13)
        self.assertEqual(signed_state["attestation"]["calibration_event_id"], 12)

    def test_actual_commit_gate_does_not_publish_invalid_source(self):
        # Execute the actual market_work.perform function AST, without
        # importing Django/Evennia. This checks preflight and consequence
        # against the real pure verifier, not a hand-written copy of the gate.
        source = (Path(__file__).resolve().parents[2]
                  / "spike/fvillage/world/market_work.py")
        tree = ast.parse(source.read_text(encoding="utf-8"), filename=str(source))
        perform = next(node for node in tree.body
                       if isinstance(node, ast.FunctionDef)
                       and node.name == "perform")
        module = ast.fix_missing_locations(ast.Module(body=[perform], type_ignores=[]))

        def run(ledger):
            room = SimpleNamespace(db=SimpleNamespace(
                market_standards=copy.deepcopy(self.state)))
            mask = SimpleNamespace(account=SimpleNamespace(id=11),
                                   id=111, key="Chronicler11", location=room)
            published = []
            def publish(kind, *, actor, payload, consequence):
                published.append(kind)
                consequence({"id": 14})
                return {"id": 14}
            namespace = {
                "ACTION_ROLE": {"attest": "chronicler"},
                "MARKET": "Market Lane",
                "market_room": lambda: room,
                "clock": lambda: (1, 14),
                "active_calling": lambda actor: "chronicler",
                "witnessed_scale_today": lambda actor, day: True,
                "market_standards": market,
                "get_event_ledger": lambda: SimpleNamespace(get_event=ledger.get),
                "transaction": SimpleNamespace(atomic=nullcontext),
                "publish_world_event": publish,
                "record_participation": lambda *args, **kwargs: None,
                "state_lines": lambda: "Market state",
            }
            exec(compile(module, str(source), "exec"), namespace)
            result, error = namespace["perform"](mask, "attest")
            return result, error, room.db.market_standards, published

        valid, error, state, published = run(self.ledger)
        self.assertIsNone(error)
        self.assertEqual(valid["event_id"], 14)
        self.assertEqual(published, ["village.market_attest"])
        self.assertEqual(state["attestation"]["review_event_id"], 10)

        for event_id, field, bad in (
            (10, "market_distribution_held", False),
            (12, "market_distribution_held", True),
            (12, "review_event_id", 999),
            (12, "calibration_event_id", None),
        ):
            with self.subTest(event=event_id, field=field):
                invalid = copy.deepcopy(self.ledger)
                invalid[event_id]["consequence"][field] = bad
                result, error, state, published = run(invalid)
                self.assertIsNone(result)
                self.assertIn("cannot be verified", error)
                self.assertIsNone(state["attestation"])
                self.assertEqual(published, [], "No event may be emitted on denial")

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


    def test_corrupt_saved_merchant_choice_keeps_trade_board_playable(self):
        # Old or damaged Attribute data must not crash trade for every player.
        for bad in (["hold"], {"value": "hold"}):
            with self.subTest(saved_choice=bad):
                corrupted = copy.deepcopy(self.state)
                corrupted["review"]["choice"] = bad
                snapshot = copy.deepcopy(corrupted)
                self.assertIsNone(market.normalize(corrupted)["review"])
                board = " ".join(market.public_lines(corrupted, 1))
                self.assertNotIn("Merchant Player5 chose", board)
                self.assertFalse(self.check(corrupted))
                # A legitimate new decision can still be recorded today.
                recovered, ok, error = signed(corrupted, "honor", 21, 41)
                self.assertTrue(ok, error)
                self.assertEqual(recovered["review"]["choice"], "honor")
                self.assertEqual(corrupted, snapshot)

    def test_corrupt_ledger_action_does_not_crash_source_verification(self):
        for bad in (["hold"], {"action": "hold"}):
            with self.subTest(ledger_action=bad):
                forged = copy.deepcopy(self.ledger)
                forged[10]["payload"]["action"] = bad
                self.assertFalse(self.check(ledger=forged))
                self.assertTrue(self.check())


if __name__ == "__main__":
    unittest.main()
