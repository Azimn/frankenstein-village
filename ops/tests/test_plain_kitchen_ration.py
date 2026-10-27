"""The plain soup ration uses existing finite shared stock, not free food.

Execute the exact production ration and availability functions via isolated
AST with Evennia boundaries replaced. Competitor actions are injected after
preflight and before the signed world-event consequence. Deterministic
interleavings are not proof of parallel database transactions.
"""
import ast
import copy
from contextlib import nullcontext
from pathlib import Path
import sys
from types import SimpleNamespace
import unittest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "spike" / "fvillage"))
from world import soup_state


class Tags:
    def __init__(self):
        self.data = set()

    def add(self, name):
        self.data.add(name)

    def has(self, name):
        return name in self.data


class FakeBowl:
    def __init__(self, owner, identifier):
        self.id = identifier
        self.location = owner
        self.db = SimpleNamespace()
        self.tags = Tags()


class PlainRationTests(unittest.TestCase):
    def setUp(self):
        path = ROOT / "spike/fvillage/world/soup_kitchen.py"
        tree = ast.parse(path.read_text(encoding="utf-8"))
        names = {"_ration_pair", "_full_bowls", "can_make_ration", "ration"}
        funcs = [f for f in tree.body
                 if isinstance(f, ast.FunctionDef) and f.name in names]
        assert {f.name for f in funcs} == names
        self.ns = {}
        exec(compile(ast.fix_missing_locations(
            ast.Module(body=funcs, type_ignores=[])),
            str(path), "exec"), self.ns)
        self.day = 1
        self.tavern = SimpleNamespace(
            id=55, key="The Blood of the Vine",
            db=SimpleNamespace(soup_pantry=soup_state.pantry(None, 1)))
        self.mask = SimpleNamespace(
            id=301, key="Visitor", account=SimpleNamespace(id=111),
            location=self.tavern, contents=[], active_calling="smith")
        self.created = []
        self.events = []
        self.before_consequence = lambda: None

        def create_object(typeclass, *, key, location, aliases):
            bowl = FakeBowl(location, 400 + len(self.created))
            bowl.key, bowl.aliases = key, aliases
            location.contents.append(bowl)
            self.created.append(bowl)
            return bowl

        def publish(kind, *, actor, payload, consequence):
            self.assertEqual(kind, "village.kitchen_plain_ration")
            self.assertIs(actor, self.mask)
            self.before_consequence()
            evt = {"id": 90 + len(self.events), "kind": kind}
            evt["consequence"] = consequence(evt)
            self.events.append(evt)
            return evt

        self.ns.update({
            "_access": lambda actor, name: (
                (self.tavern, None)
                if actor.location is self.tavern and actor.account is not None
                else (None, "You must be in the IC kitchen.")
            ),
            "_room": lambda name: self.tavern,
            "_clock": lambda: (self.day, 21),
            "soup_state": soup_state,
            "transaction": SimpleNamespace(atomic=nullcontext),
            "create_object": create_object,
            "publish_world_event": publish,
            "copy": copy,
            "TAVERN": self.tavern.key,
            "RATION": "a bowl of plain kitchen broth",
            "RATION_PAIRS": (
                ("barley", "salt"), ("turnip", "salt"),
                ("barley", "thyme"), ("turnip", "thyme"),
                ("barley", "pepper"), ("turnip", "pepper"),
            ),
        })

    def set_only(self, **counts):
        state = soup_state.pantry(None, 1)
        state["stock"] = {k: 0 for k in soup_state.BASE_STOCK}
        state["stock"].update(counts)
        self.tavern.db.soup_pantry = state

    def test_any_calling_can_make_finite_travelers_broth(self):
        self.set_only(barley=1, salt=1)
        result, error = self.ns["ration"](self.mask)
        self.assertIsNone(error)
        self.assertEqual(result["base"], "barley")
        self.assertEqual(result["seasoning"], "salt")
        self.assertEqual(result["nourish"], 24)
        self.assertEqual(result["stock_after"]["barley"], 0)
        self.assertEqual(result["stock_after"]["salt"], 0)
        self.assertEqual(len(self.created), 1)
        bowl = self.created[0]
        self.assertEqual(bowl.db.servings, 1)
        self.assertTrue(bowl.tags.has("food"))
        self.assertTrue(bowl.tags.has("consumable"))
        self.assertEqual(bowl.db.kitchen_ration["cook_event_id"], 90)
        self.assertEqual(bowl.db.consume["nourish"], 24)

    def test_last_stock_taken_after_preview_cannot_create_second_meal(self):
        self.set_only(barley=1, salt=1)

        def competitor():
            state, accepted, reason = soup_state.reserve(
                self.tavern.db.soup_pantry, 1, "barley", "salt")
            self.assertTrue(accepted, reason)
            self.tavern.db.soup_pantry = state

        self.before_consequence = competitor
        result, error = self.ns["ration"](self.mask)
        self.assertIsNone(result)
        self.assertIn("no bowl was made", error.lower())
        self.assertEqual(self.created, [])
        self.assertEqual(self.tavern.db.soup_pantry["stock"]["barley"], 0)
        self.assertEqual(self.events, [])

    def test_other_cook_takes_barley_and_current_stock_selects_turnip(self):
        self.set_only(barley=1, turnip=1, salt=2)

        def competitor():
            state, accepted, reason = soup_state.reserve(
                self.tavern.db.soup_pantry, 1, "barley", "salt")
            self.assertTrue(accepted, reason)
            self.tavern.db.soup_pantry = state

        self.before_consequence = competitor
        result, error = self.ns["ration"](self.mask)
        self.assertIsNone(error)
        self.assertEqual((result["base"], result["seasoning"]),
                         ("turnip", "salt"))
        self.assertEqual(result["stock_after"]["salt"], 0)
        self.assertEqual(self.tavern.db.soup_pantry["stock"]["barley"], 0)
        self.assertEqual(self.tavern.db.soup_pantry["stock"]["turnip"], 0)

    def test_no_ration_on_day_change_or_outside_kitchen(self):
        self.before_consequence = lambda: setattr(self, "day", 2)
        result, error = self.ns["ration"](self.mask)
        self.assertIsNone(result)
        self.assertIn("day changed", error.lower())
        self.assertEqual(self.created, [])
        self.assertEqual(self.tavern.db.soup_pantry["stock"],
                         soup_state.BASE_STOCK)
        self.day = 1
        self.mask.location = SimpleNamespace(key="Village Square")
        result, error = self.ns["ration"](self.mask)
        self.assertIsNone(result)
        self.assertIn("ic kitchen", error.lower())

    def test_spent_bowls_do_not_block_new_but_three_live_do(self):
        spent = FakeBowl(self.mask, 802)
        spent.db.kitchen_ration = {"day": 1}
        spent.db.servings = 0
        self.mask.contents.append(spent)
        result, error = self.ns["ration"](self.mask)
        self.assertIsNone(error)
        self.assertEqual(self.ns["_full_bowls"](self.mask), 1)
        for n in range(2):
            extra = FakeBowl(self.mask, 900+n)
            extra.db.soup_serving = {"day": 1}
            extra.db.servings = 1
            self.mask.contents.append(extra)
        result, error = self.ns["ration"](self.mask)
        self.assertIsNone(result)
        self.assertIn("eat a carried soup bowl", error.lower())
        self.assertEqual(len(self.created), 1)

    def test_stock_guidance_never_advertises_empty_pantry(self):
        initial = copy.deepcopy(self.tavern.db.soup_pantry)
        self.assertTrue(self.ns["can_make_ration"]())
        self.assertEqual(initial, self.tavern.db.soup_pantry)
        self.set_only(barley=1)
        self.assertFalse(self.ns["can_make_ration"]())
        self.assertEqual(self.created, [])


if __name__ == "__main__":
    unittest.main()
