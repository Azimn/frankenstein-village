"""Exercise production public-brazier action with real stock interleavings.

The game action functions are executed from their AST with Evennia boundary
calls mocked. Interleaving tests do NOT establish truly simultaneous SQL
transactions. Real-client and restart tests live in spike/tests.
"""
import ast
from contextlib import nullcontext
from pathlib import Path
import sys
from types import SimpleNamespace
import unittest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "spike/fvillage"))
from world import square_brazier_state as fire


class FakeBundle:
    def __init__(self, owner, key=100):
        self.id = key
        self.location = owner
        self.db = SimpleNamespace(
            civic_firewood=True, gather_event_id=200 + key
        )
        self.deleted = False

    def delete(self):
        self.deleted = True
        self.location = None


class SquareBrazierRuntimeTests(unittest.TestCase):
    def setUp(self):
        path = ROOT / "spike/fvillage/world/square_brazier.py"
        tree = ast.parse(path.read_text(encoding="utf-8"))
        function = next(
            node for node in tree.body
            if isinstance(node, ast.FunctionDef) and node.name == "act"
        )
        module = ast.fix_missing_locations(
            ast.Module(body=[function], type_ignores=[])
        )
        self.ns = {}
        exec(compile(module, str(path), "exec"), self.ns)
        self.day, self.hour = 1, 21
        self.square = SimpleNamespace(key="Village Square")
        self.mask = SimpleNamespace(
            key="Traveler", id=31, account=SimpleNamespace(id=22),
            location=self.square
        )
        self.brazier = SimpleNamespace(
            id=50, location=self.square,
            db=SimpleNamespace(square_brazier=None)
        )
        self.bundle = FakeBundle(self.mask)
        self.pledged = None
        self.before_consequence = lambda: None
        self.events = []

        def publish(kind, *, actor, payload, consequence):
            self.assertTrue(kind.startswith("civic.square_brazier_"))
            self.assertIs(actor, self.mask)
            self.before_consequence()
            event = {"id": 90 + len(self.events), "kind": kind,
                     "payload": payload}
            event["consequence"] = consequence(event)
            self.events.append(event)
            return event

        self.ns.update({
            "_guard": lambda player: (
                (self.square, None) if player.location is self.square
                else (None, "Not in Village Square.")
            ),
            "_brazier": lambda: self.brazier,
            "_clock": lambda: (self.day, self.hour),
            "_usable_bundle": lambda player, day: (
                self.bundle
                if self.bundle.location is player
                and self.bundle.id != self.pledged
                else None
            ),
            "_carried": lambda player: (
                [self.bundle] if self.bundle.location is player else []
            ),
            "_pledged_bundle_id": lambda day: self.pledged,
            "square_brazier_state": fire,
            "transaction": SimpleNamespace(atomic=nullcontext),
            "publish_world_event": publish,
        })

    def act(self, mode):
        return self.ns["act"](self.mask, mode)

    def test_signed_light_spends_one_actual_bundle_and_records_provenance(self):
        result, error = self.act("light")
        self.assertIsNone(error)
        self.assertTrue(self.bundle.deleted)
        self.assertEqual(result["remaining"], fire.LIGHT_HOURS)
        receipt = self.events[0]["consequence"]
        self.assertEqual(receipt["bundle_id"], self.bundle.id)
        self.assertEqual(receipt["gather_event_id"],
                         self.bundle.db.gather_event_id)
        self.assertEqual(len(self.brazier.db.square_brazier["history"]), 1)
        self.assertEqual(self.events[0]["kind"], "civic.square_brazier_light")

    def test_competing_visitor_lights_first_and_bundle_is_retained(self):
        def competitor():
            new_state, okay, reason = fire.contribute(
                self.brazier.db.square_brazier, 1, 21, mode="light",
                actor={"mask_id": 49, "mask": "Earlier Traveler"},
                bundle_id=75, gather_event_id=177, event_id=77
            )
            self.assertTrue(okay, reason)
            self.brazier.db.square_brazier = new_state

        self.before_consequence = competitor
        result, error = self.act("light")
        self.assertIsNone(result)
        self.assertIn("already burning", error)
        self.assertFalse(self.bundle.deleted)
        self.assertIs(self.bundle.location, self.mask)
        self.assertEqual(len(self.brazier.db.square_brazier["history"]), 1)

    def test_moved_bundle_before_consequence_is_never_consumed(self):
        self.before_consequence = lambda: setattr(
            self.bundle, "location", object()
        )
        result, error = self.act("light")
        self.assertIsNone(result)
        self.assertIn("no longer in your hands", error)
        self.assertFalse(self.bundle.deleted)
        self.assertIsNone(self.brazier.db.square_brazier)

    def test_newly_pledged_bundle_is_protected_during_event(self):
        self.before_consequence = lambda: setattr(
            self, "pledged", self.bundle.id
        )
        result, error = self.act("light")
        self.assertIsNone(result)
        self.assertIn("pledged to a civic commission", error)
        self.assertFalse(self.bundle.deleted)
        self.assertIsNone(self.brazier.db.square_brazier)

    def test_clock_changing_mid_action_does_not_steal_fuel(self):
        self.before_consequence = lambda: setattr(self, "hour", 22)
        result, error = self.act("light")
        self.assertIsNone(result)
        self.assertIn("clock changed", error)
        self.assertFalse(self.bundle.deleted)

    def test_feed_of_cold_fire_and_second_light_are_refused(self):
        result, error = self.act("feed")
        self.assertIsNone(result)
        self.assertIn("cold", error)
        self.assertFalse(self.bundle.deleted)
        self.assertEqual(self.events, [])

    def test_refuse_over_full_horizon_with_custody_intact(self):
        self.brazier.db.square_brazier = {
            "warm_until": fire.hour_index(1, 21) + 10,
            "last_action_at": fire.hour_index(1, 21),
            "history": [],
        }
        result, error = self.act("feed")
        self.assertIsNone(result)
        self.assertIn("well supplied", error)
        self.assertFalse(self.bundle.deleted)


if __name__ == "__main__":
    unittest.main()
