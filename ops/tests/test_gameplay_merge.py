"""Conflict-resolution guard for PR #40 command registration and game state.

Static checks run before installing Evennia and complement live world/telnet tests.
"""

from __future__ import annotations

import ast
from collections import Counter
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[2] / "spike" / "fvillage" / "commands"


def tree(name):
    return ast.parse((ROOT / name).read_text(encoding="utf-8"))


class MergedCmdsetTests(unittest.TestCase):
    def test_all_registered_commands_resolve_without_duplicate_keys(self):
        source = tree("default_cmdsets.py")
        character = next(
            node for node in source.body
            if isinstance(node, ast.ClassDef) and node.name == "CharacterCmdSet"
        )
        method = next(
            item for item in character.body
            if isinstance(item, ast.FunctionDef)
            and item.name == "at_cmdset_creation"
        )
        imports = {}
        for node in ast.walk(method):
            if isinstance(node, ast.ImportFrom) and node.module.startswith("commands."):
                for item in node.names:
                    self.assertNotIn(item.name, imports)
                    imports[item.name] = node.module.removeprefix("commands.") + ".py"

        registered = []
        for node in ast.walk(method):
            if not isinstance(node, ast.Call) or not isinstance(node.func, ast.Attribute):
                continue
            if node.func.attr != "add" or not node.args:
                continue
            arg = node.args[0]
            if isinstance(arg, ast.Call) and isinstance(arg.func, ast.Name):
                registered.append(arg.func.id)
        self.assertGreaterEqual(len(registered), 50)
        self.assertEqual(len(registered), len(set(registered)))

        key_by_name = {}
        for name in registered:
            self.assertIn(name, imports, f"{name} was never imported")
            mod = tree(imports[name])
            definitions = [
                node for node in mod.body
                if isinstance(node, ast.ClassDef) and node.name == name
            ]
            self.assertEqual(len(definitions), 1, f"{name} did not resolve uniquely")
            keys = [
                assign.value.value
                for assign in definitions[0].body
                if isinstance(assign, ast.Assign)
                and any(
                    isinstance(t, ast.Name) and t.id == "key"
                    for t in assign.targets
                )
                and isinstance(assign.value, ast.Constant)
                and isinstance(assign.value.value, str)
            ]
            self.assertEqual(len(keys), 1, f"{name} lacks a concrete command key")
            key_by_name[name] = keys[0].lower()
        frequencies = Counter(key_by_name.values())
        self.assertFalse(
            {key: count for key, count in frequencies.items() if count > 1},
            "Two custom commands own the same key"
        )
        self.assertEqual(key_by_name["CmdRoll"], "roll")
        self.assertEqual(key_by_name["CmdWrestle"], "wrestle")
        self.assertEqual(key_by_name["CmdAgentContext"], "agent")

    def test_dice_uses_player_route_and_keeper_route(self):
        source = tree("village_cmds.py")
        roll = next(
            node for node in source.body
            if isinstance(node, ast.ClassDef) and node.name == "CmdRoll"
        )
        self.assertEqual(
            sum(isinstance(x, ast.ClassDef) and x.name == "CmdRoll"
                for x in source.body), 1
        )
        duel = next(
            node for node in roll.body
            if isinstance(node, ast.FunctionDef) and node.name == "_duel"
        )
        calls = {
            node.func.attr
            for node in ast.walk(duel)
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute)
        }
        self.assertIn("_challenge_dice", calls)
        self.assertIn("_keeper_duel", calls)


if __name__ == "__main__":
    unittest.main()
