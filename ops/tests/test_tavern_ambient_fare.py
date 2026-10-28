"""T-09 regression: ambient NPCs must respect physical Tavern stock.

A scripted regular is not allowed to bypass the same depleted-fare guard
used by ordinary player eat/drink commands. These tests need no LLM or
Evennia server; full game integration remains the separate CI gate.
"""
from __future__ import annotations

import sys
import types
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "spike/fvillage"))
from world import tavern_life


def fare(key, servings, food=True):
    return types.SimpleNamespace(
        key=key,
        db=types.SimpleNamespace(servings=servings),
        tags=types.SimpleNamespace(has=lambda tag: tag == ("food" if food else "drink")),
    )


class AmbientFareConservationTests(unittest.TestCase):
    def setUp(self):
        self.regular = object()
        self.consumed = []
        self.guarded = []
        fake = types.ModuleType("commands.village_cmds")

        def depleted(actor, item):
            self.guarded.append((actor, item))
            return item.db.servings <= 0

        fake._fare_depleted = depleted
        fake._consume = lambda *args: self.consumed.append(args)
        package = types.ModuleType("commands")
        package.__path__ = []
        self.modules = patch.dict(
            sys.modules, {"commands": package, "commands.village_cmds": fake}
        )
        self.modules.start()
        self.addCleanup(self.modules.stop)

    def beat(self, contents):
        room = types.SimpleNamespace(contents=contents)
        with patch.object(tavern_life, "_tavern", return_value=room):
            return tavern_life._beat_consume(
                [self.regular], None, lambda line: None
            )

    def test_missing_physical_fare_is_quietly_skipped(self):
        self.assertEqual(self.beat([]), "consume-skipped")
        self.assertEqual(self.consumed, [])

    def test_depleted_food_and_drink_do_not_create_ghost_meals(self):
        stew = fare("a bowl of stew", 0)
        ale = fare("a tankard of ale", 0, food=False)
        self.assertEqual(self.beat([stew, ale]), "consume-skipped")
        self.assertEqual(self.consumed, [])
        self.assertEqual({id(item) for _, item in self.guarded}, {id(stew), id(ale)})

    def test_regular_uses_real_ale_when_stew_is_depleted(self):
        stew = fare("a bowl of stew", 0)
        ale = fare("a tankard of ale", 2, food=False)
        self.assertEqual(self.beat([stew, ale]), "consume")
        self.assertEqual(len(self.consumed), 1)
        self.assertIs(self.consumed[0][1], ale)
        self.assertEqual(self.consumed[0][2:4], ("drink", "drink"))

    def test_regular_uses_real_stew_when_ale_is_depleted(self):
        stew = fare("a bowl of stew", 2)
        ale = fare("a tankard of ale", 0, food=False)
        self.assertEqual(self.beat([stew, ale]), "consume")
        self.assertEqual(len(self.consumed), 1)
        self.assertIs(self.consumed[0][1], stew)
        self.assertEqual(self.consumed[0][2:4], ("food", "eat"))


    def test_last_serving_exhaustion_prevents_second_ambient_meal(self):
        """One actual serving cannot nourish two successive NPC beats.

        This is a routing/conservation test with the production guard mocked.
        The separate Evennia acceptance suite must still prove persistence.
        """
        stew = fare("a bowl of stew", 1)
        fake_commands = sys.modules["commands.village_cmds"]

        def consume(actor, item, *args):
            self.consumed.append((actor, item, *args))
            item.db.servings -= 1

        fake_commands._consume = consume
        self.assertEqual(self.beat([stew]), "consume")
        self.assertEqual(stew.db.servings, 0)
        self.assertEqual(self.beat([stew]), "consume-skipped")
        self.assertEqual(stew.db.servings, 0)
        self.assertEqual(len(self.consumed), 1)
        self.assertEqual(len(self.guarded), 2)


if __name__ == "__main__":
    unittest.main()
