"""Regression for finite player meals and Bram's original sideboard stock.

Run the production restock function in isolation without a live Evennia DB.
The builder test exercises the real _fare function, not a duplicated policy.
"""
import ast
from pathlib import Path
import sys
from types import ModuleType, SimpleNamespace
from unittest import TestCase
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]
WORLD = ROOT / "spike" / "fvillage" / "world"


class Tags:
    def __init__(self):
        self.values = set()

    def add(self, name, category=None):
        self.values.add((name, category))

    def has(self, name, category=None):
        return (name, category) in self.values


def production_function(filename, name, globals_dict):
    path = WORLD / filename
    tree = ast.parse(path.read_text(encoding="utf-8"))
    funcs = [node for node in tree.body
             if isinstance(node, ast.FunctionDef) and node.name == name]
    assert len(funcs) == 1, (filename, name)
    namespace = dict(globals_dict)
    exec(compile(ast.fix_missing_locations(
        ast.Module(body=funcs, type_ignores=[])), str(path), "exec"),
        namespace)
    return namespace[name]


def item(key, *, house=False, servings=0, maximum=1,
         ration=None, soup=None):
    tags = Tags()
    if house:
        tags.add("house-sideboard-fare", category="origin")
    return SimpleNamespace(
        key=key, tags=tags, typeclass_path="typeclasses.objects.Object",
        db=SimpleNamespace(
            consume={"short": key, "servings_max": maximum},
            servings=servings, uses=maximum if house else None,
            kitchen_ration=ration, soup_serving=soup,
        ),
    )


class SideboardFiniteMealTests(TestCase):
    def test_builder_marks_house_fare_idempotently(self):
        bread = item("a loaf of bread", servings=None, maximum=6)
        room = SimpleNamespace(contents=[bread])
        make_fare = production_function("build_spike.py", "_fare", {
            "tavern": room,
            "configure_mechanical_properties": lambda obj, props: None,
        })
        self.assertFalse(bread.tags.has("house-sideboard-fare", category="origin"))
        returned = make_fare(
            "a loaf of bread", ["bread"], "food", "House bread",
            {"nourish": 25}, servings=6, short="bread", worth=4,
        )
        self.assertIs(returned, bread)
        self.assertTrue(bread.tags.has("house-sideboard-fare", category="origin"))
        self.assertEqual(bread.db.servings, 6)

    def test_only_house_fare_refills_after_player_drops_spent_bowls(self):
        keeper = item("Bram")
        bread = item("a loaf of bread", house=True, servings=0, maximum=6)
        plain = item("a bowl of plain kitchen broth", servings=0,
                     ration={"cook_event_id": 41})
        cooked = item("a bowl of turnip soup", servings=0,
                      soup={"cook_event_id": 42})
        impostor = item("a loaf of bread", servings=0, maximum=6)
        announcements = []
        room = SimpleNamespace(
            contents=[keeper, bread, plain, cooked, impostor],
            msg_contents=announcements.append,
        )
        properties = ModuleType("world.object_properties")
        properties.mechanical_value = lambda obj, key, default: obj.db.uses
        restock = production_function("routines.py", "restock_sideboard", {
            "_room": lambda key: room,
        })
        with patch.dict(sys.modules, {"world.object_properties": properties}):
            self.assertEqual(restock(), ["a loaf of bread"])
        self.assertEqual(bread.db.servings, 6)
        self.assertEqual(plain.db.servings, 0)
        self.assertEqual(cooked.db.servings, 0)
        self.assertEqual(impostor.db.servings, 0)
        self.assertEqual(len(announcements), 1)
        with patch.dict(sys.modules, {"world.object_properties": properties}):
            self.assertEqual(restock(), [])
        self.assertEqual(len(announcements), 1)

    def test_no_keeper_means_no_house_restock(self):
        bread = item("a loaf of bread", house=True, servings=0, maximum=6)
        room = SimpleNamespace(contents=[bread], msg_contents=lambda msg: None)
        restock = production_function("routines.py", "restock_sideboard", {
            "_room": lambda key: room,
        })
        self.assertEqual(restock(), [])
        self.assertEqual(bread.db.servings, 0)


if __name__ == "__main__":
    import unittest
    unittest.main()
