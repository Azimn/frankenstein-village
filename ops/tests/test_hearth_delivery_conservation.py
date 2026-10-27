"""The ordinary hearth must conserve physical bundles under stale previews.

Execute the exact production community_hearth.deliver function with its
Evennia boundaries replaced. The event callback deliberately changes live
state after the command preview but before the signed consequence. This is a
deterministic interleaving test, not proof of parallel server execution.
"""
import ast
from contextlib import nullcontext
import sys
from pathlib import Path
from types import SimpleNamespace
import unittest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "spike" / "fvillage"))
from world import civic_commissions, hearth_state


class FakeBundle:
    def __init__(self, owner, identifier):
        self.id = identifier
        self.location = owner
        self.db = SimpleNamespace(civic_firewood=True, gather_event_id=identifier + 100)
        self.deleted = False

    def delete(self):
        self.deleted = True
        self.location = None


class HearthDeliveryConservationTests(unittest.TestCase):
    def setUp(self):
        path = ROOT / "spike" / "fvillage" / "world" / "community_hearth.py"
        tree = ast.parse(path.read_text(encoding="utf-8"))
        function = next(
            node for node in tree.body
            if isinstance(node, ast.FunctionDef) and node.name == "deliver"
        )
        isolated = ast.fix_missing_locations(ast.Module(body=[function], type_ignores=[]))
        self.namespace = {}
        exec(compile(isolated, str(path), "exec"), self.namespace)
        self.mask = SimpleNamespace(account=SimpleNamespace(id=202), key="Carrier")
        self.bundles = [FakeBundle(self.mask, 450)]
        self.tavern = SimpleNamespace(db=SimpleNamespace(
            civic_commission=civic_commissions.refresh(None, 1),
            civic_hearth={"reserve": 2},
        ))
        self.before_consequence = lambda: None
        self.events = []

        def publish(kind, *, actor, payload, consequence):
            self.assertEqual(kind, "civic.hearth_firewood_delivered")
            self.assertIs(actor, self.mask)
            self.before_consequence()
            event = {"id": 90}
            event["consequence"] = consequence(event)
            self.events.append(event)
            return event

        self.namespace.update({
            "_actor_ok": lambda actor, room: (True, None),
            "_carried": lambda actor: [
                bundle for bundle in self.bundles if bundle.location is actor
            ],
            "_room": lambda key: self.tavern,
            "_clock": lambda: (1, 21),
            "TAVERN_KEY": "The Blood of the Vine",
            "FIREWOOD_KEY": "a bundle of firewood",
            "hearth_state": hearth_state,
            "transaction": SimpleNamespace(atomic=nullcontext),
            "publish_world_event": publish,
        })

    def deliver(self):
        return self.namespace["deliver"](self.mask)

    def test_receipt_and_rack_include_competing_delivery(self):
        def competitor():
            updated, accepted = hearth_state.deliver(self.tavern.db.civic_hearth)
            self.assertTrue(accepted)
            self.tavern.db.civic_hearth = updated

        self.before_consequence = competitor
        result, error = self.deliver()
        self.assertIsNone(error)
        self.assertEqual(self.tavern.db.civic_hearth["reserve"], 4)
        self.assertEqual(result["reserve"], 4)
        self.assertEqual(self.events[0]["consequence"]["reserve"], 4)
        self.assertEqual(self.events[0]["consequence"]["gather_event_id"], 550)
        self.assertTrue(self.bundles[0].deleted)

    def test_full_rack_after_preview_does_not_destroy_bundle(self):
        self.tavern.db.civic_hearth = {"reserve": 5}

        def competitor():
            updated, accepted = hearth_state.deliver(self.tavern.db.civic_hearth)
            self.assertTrue(accepted)
            self.tavern.db.civic_hearth = updated

        self.before_consequence = competitor
        result, error = self.deliver()
        self.assertIsNone(result)
        self.assertIn("rack", error.lower())
        self.assertEqual(self.tavern.db.civic_hearth["reserve"], 6)
        self.assertFalse(self.bundles[0].deleted)
        self.assertIs(self.bundles[0].location, self.mask)

    def test_new_pledge_after_preview_cannot_be_consumed(self):
        def competitor():
            state, accepted, reason = civic_commissions.pledge(
                self.tavern.db.civic_commission, 1, 101, "Supplier",
                bundle_id=450, event_id=10,
            )
            self.assertTrue(accepted, reason)
            self.tavern.db.civic_commission = state

        self.before_consequence = competitor
        result, error = self.deliver()
        self.assertIsNone(result)
        self.assertIn("pledged", error.lower())
        self.assertEqual(self.tavern.db.civic_hearth["reserve"], 2)
        self.assertFalse(self.bundles[0].deleted)

    def test_moved_bundle_after_preview_cannot_be_consumed(self):
        self.before_consequence = lambda: setattr(self.bundles[0], "location", object())
        result, error = self.deliver()
        self.assertIsNone(result)
        self.assertIn("no longer", error.lower())
        self.assertEqual(self.tavern.db.civic_hearth["reserve"], 2)
        self.assertFalse(self.bundles[0].deleted)

    def test_unpledged_bundle_can_be_delivered_while_other_is_pledged(self):
        state, accepted, reason = civic_commissions.pledge(
            self.tavern.db.civic_commission, 1, 101, "Supplier",
            bundle_id=450, event_id=10,
        )
        self.assertTrue(accepted, reason)
        self.tavern.db.civic_commission = state
        free_bundle = FakeBundle(self.mask, 451)
        self.bundles.append(free_bundle)
        result, error = self.deliver()
        self.assertIsNone(error)
        self.assertEqual(result["reserve"], 3)
        self.assertFalse(self.bundles[0].deleted)
        self.assertTrue(free_bundle.deleted)
        self.assertEqual(self.events[0]["consequence"]["gather_event_id"], 551)


if __name__ == "__main__":
    unittest.main()
