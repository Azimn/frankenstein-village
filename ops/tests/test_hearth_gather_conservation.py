"""A gathered firewood bundle must correspond to one live finite stock unit.

Execute the production gather function through an isolated AST with Evennia
boundaries substituted. Competing actions are injected after the preflight
preview and before the signed event consequence. These deterministic tests do
not claim parallel Evennia server execution.
"""
import ast
from contextlib import nullcontext
import sys
from pathlib import Path
from types import SimpleNamespace
import unittest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "spike" / "fvillage"))
from world import hearth_state


class HearthGatherConservationTests(unittest.TestCase):
    def setUp(self):
        path = ROOT / "spike" / "fvillage" / "world" / "community_hearth.py"
        tree = ast.parse(path.read_text(encoding="utf-8"))
        function = next(
            node for node in tree.body
            if isinstance(node, ast.FunctionDef) and node.name == "gather"
        )
        module = ast.fix_missing_locations(ast.Module(body=[function], type_ignores=[]))
        self.namespace = {}
        exec(compile(module, str(path), "exec"), self.namespace)
        self.mask = SimpleNamespace(key="Gatherer", account=SimpleNamespace(id=202))
        self.carried = []
        self.day = 1
        self.wood = SimpleNamespace(
            id=33, db=SimpleNamespace(civic_wood={"day": 1, "remaining": 2})
        )
        self.before_consequence = lambda: None
        self.created = []

        def create_object(typeclass, *, key, location, aliases):
            obj = SimpleNamespace(
                id=500 + len(self.created),
                key=key,
                location=location,
                db=SimpleNamespace(),
            )
            self.created.append(obj)
            self.carried.append(obj)
            return obj

        def publish(kind, *, actor, payload, consequence):
            self.assertEqual(kind, "civic.hearth_firewood_gathered")
            self.assertIs(actor, self.mask)
            self.before_consequence()
            event = {"id": 90}
            event["consequence"] = consequence(event)
            return event

        self.namespace.update({
            "_actor_ok": lambda actor, room: (True, None),
            "_carried": lambda actor: list(self.carried),
            "_woodpile": lambda: self.wood,
            "_clock": lambda: (self.day, 21),
            "SQUARE_KEY": "Village Square",
            "FIREWOOD_KEY": "a bundle of firewood",
            "hearth_state": hearth_state,
            "create_object": create_object,
            "transaction": SimpleNamespace(atomic=nullcontext),
            "publish_world_event": publish,
        })

    def gather(self):
        return self.namespace["gather"](self.mask)

    def test_competing_gather_updates_from_live_remaining_stock(self):
        def competitor():
            updated, accepted = hearth_state.take(self.wood.db.civic_wood, 1)
            self.assertTrue(accepted)
            self.wood.db.civic_wood = updated

        self.before_consequence = competitor
        result, error = self.gather()
        self.assertIsNone(error)
        self.assertEqual(result["remaining"], 0)
        self.assertEqual(self.wood.db.civic_wood["remaining"], 0)
        self.assertEqual(len(self.created), 1)
        self.assertEqual(self.created[0].db.gather_event_id, 90)

    def test_last_bundle_taken_after_preview_does_not_duplicate_wood(self):
        self.wood.db.civic_wood["remaining"] = 1

        def competitor():
            updated, accepted = hearth_state.take(self.wood.db.civic_wood, 1)
            self.assertTrue(accepted)
            self.wood.db.civic_wood = updated

        self.before_consequence = competitor
        result, error = self.gather()
        self.assertIsNone(result)
        self.assertIn("no more bundles", error.lower())
        self.assertEqual(self.wood.db.civic_wood["remaining"], 0)
        self.assertEqual(self.created, [])

    def test_newly_received_bundle_prevents_second_gather(self):
        self.before_consequence = lambda: self.carried.append(
            SimpleNamespace(id=401, db=SimpleNamespace(civic_firewood=True))
        )
        result, error = self.gather()
        self.assertIsNone(result)
        self.assertIn("already carry", error.lower())
        self.assertEqual(self.wood.db.civic_wood["remaining"], 2)
        self.assertEqual(self.created, [])

    def test_day_change_between_preview_and_event_cannot_mint_wood(self):
        self.before_consequence = lambda: setattr(self, "day", 2)
        result, error = self.gather()
        self.assertIsNone(result)
        self.assertIn("day changed", error.lower())
        self.assertEqual(self.wood.db.civic_wood["remaining"], 2)
        self.assertEqual(self.created, [])


if __name__ == "__main__":
    unittest.main()
