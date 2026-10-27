"""Market decisions must be authorized at the signed event boundary.

Execute the actual production perform() AST without importing Evennia. The
publisher simulates a state change between player preflight and consequence.
"""
import ast
from contextlib import nullcontext
from pathlib import Path
from types import SimpleNamespace
import unittest


SOURCE = Path(__file__).resolve().parents[2] / "spike/fvillage/world/market_work.py"


def simulate(mutate=None):
    room = SimpleNamespace(db=SimpleNamespace(market_standards=None))
    mask = SimpleNamespace(
        account=SimpleNamespace(id=5), id=15, key="MarketTester",
        location=room, role="merchant", inspected=True,
    )
    now = [1, 14]
    participation = []

    def apply(_state, _action, **kwargs):
        return {
            "review": None, "calibration": None,
            "signed_account": kwargs["account_id"],
        }, True, None

    def publish(_kind, *, actor, payload, consequence):
        if mutate is not None:
            mutate(mask, now)
        consequence({"id": 23})
        return {"id": 23}

    namespace = {
        "ACTION_ROLE": {"honor": "merchant"},
        "MARKET": "Market Lane",
        "market_room": lambda: room,
        "clock": lambda: tuple(now),
        "active_calling": lambda actor: actor.role,
        "witnessed_scale_today": lambda actor, day: (
            actor.location is room and actor.inspected and day == now[0]
        ),
        "market_standards": SimpleNamespace(
            apply=apply, suspended=lambda *_: False,
            verified_sources=lambda *_: True,
        ),
        "get_event_ledger": lambda: SimpleNamespace(get_event=lambda _: None),
        "transaction": SimpleNamespace(atomic=nullcontext),
        "publish_world_event": publish,
        "record_participation": lambda *args, **kwargs: participation.append(
            (args, kwargs)
        ),
        "state_lines": lambda: "Market state",
    }
    tree = ast.parse(SOURCE.read_text(encoding="utf-8"), filename=str(SOURCE))
    perform_node = next(
        node for node in tree.body
        if isinstance(node, ast.FunctionDef) and node.name == "perform"
    )
    isolated = ast.fix_missing_locations(
        ast.Module(body=[perform_node], type_ignores=[])
    )
    exec(compile(isolated, str(SOURCE), "exec"), namespace)
    result, error = namespace["perform"](mask, "honor")
    return result, error, room.db.market_standards, participation


class MarketCommitAuthorityTests(unittest.TestCase):
    def test_valid_market_decision_still_signs_and_attributes_account(self):
        result, error, state, participation = simulate()
        self.assertIsNone(error)
        self.assertEqual(result["event_id"], 23)
        self.assertEqual(state["signed_account"], 5)
        self.assertEqual(len(participation), 1)

    def test_revoked_or_replaced_account_cannot_sign_market_state(self):
        changes = (
            lambda actor, now: setattr(actor, "account", None),
            lambda actor, now: setattr(
                actor, "account", SimpleNamespace(id=99)
            ),
            lambda actor, now: setattr(actor, "id", 99),
        )
        for mutate in changes:
            with self.subTest(change=mutate):
                result, error, state, participation = simulate(mutate)
                self.assertIsNone(result)
                self.assertIn("account changed", error)
                self.assertIsNone(state)
                self.assertEqual(participation, [])

    def test_day_or_hour_rollover_rejects_stale_signed_decision(self):
        for index, value in ((0, 2), (1, 15)):
            with self.subTest(index=index):
                result, error, state, participation = simulate(
                    lambda actor, now: now.__setitem__(index, value)
                )
                self.assertIsNone(result)
                self.assertIn("time advanced", error)
                self.assertIsNone(state)
                self.assertEqual(participation, [])

    def test_revoked_calling_or_inspection_still_rejects_commit(self):
        for mutate in (
            lambda actor, now: setattr(actor, "role", "smith"),
            lambda actor, now: setattr(actor, "inspected", False),
        ):
            with self.subTest(change=mutate):
                result, error, state, participation = simulate(mutate)
                self.assertIsNone(result)
                self.assertTrue(error)
                self.assertIsNone(state)
                self.assertEqual(participation, [])


if __name__ == "__main__":
    unittest.main()
