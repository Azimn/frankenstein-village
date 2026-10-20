"""Contract tests for agent observations without importing Evennia."""
from __future__ import annotations

import ast
from pathlib import Path
import types
import unittest

SOURCE = Path(__file__).resolve().parents[2] / "spike/fvillage/commands/agent_context.py"
tree = ast.parse(SOURCE.read_text(encoding="utf-8"))
fn = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == "payload_for")
scope = {"VERSION": 1}
exec(compile(ast.fix_missing_locations(ast.Module(body=[fn], type_ignores=[])), str(SOURCE), "exec"), scope)
payload_for = scope["payload_for"]


class Tags:
    def __init__(self, kind): self.kind = kind
    def has(self, name, category=None): return category == "side" and name == self.kind


class Object:
    def __init__(self, name, ident, *, hidden=False, not_searchable=False, destination=None,
                 traverse=True, view=True):
        self.key, self.id = name, ident
        self.hidden, self.not_searchable = hidden, not_searchable
        self.destination, self.traverse, self.view = destination, traverse, view

    def access(self, _mask, verb, default=True):
        if verb == "view": return self.view and not self.hidden
        if verb == "search": return not self.not_searchable and not self.hidden
        if verb == "traverse": return self.traverse
        return default

    def get_display_name(self, _mask): return self.key


class TalkableResident(Object):
    def talk_to(self, player):
        return None

    def ask_about(self, player, topic):
        return None


class Room(Object):
    def __init__(self, name, kind="ic"):
        super().__init__(name, 500)
        self.tags = Tags(kind)
        self.exits, self.contents = [], []


class Mask(Object):
    def __init__(self, room):
        super().__init__("Mask", 19)
        self.location = room


class AgentObservationTests(unittest.TestCase):
    def test_visibility_and_traverse_locks_and_no_private_state(self):
        room, visible = Room("Village Square"), Room("The Blood of the Vine")
        hidden = Room("Hidden Chamber")
        hidden.hidden = True
        east = Object("east", 1, destination=visible)
        north = Object("north", 2, destination=hidden)
        no = Object("west", 3, destination=hidden, traverse=False)
        secret = Object("under", 4, destination=hidden, not_searchable=True)
        room.exits = [east, north, no, secret]
        public = Object("public noticeboard", 30)
        private = Object("private staff dossier", 31, hidden=True)
        nosearch = Object("secret map", 32, not_searchable=True)
        resident = TalkableResident("Miklós Farkas", 33)
        hidden_resident = TalkableResident("Hidden Witness", 34, hidden=True)
        room.contents = [
            east, north, no, secret, public, private, nosearch,
            resident, hidden_resident,
        ]
        mask = Mask(room)
        room.contents.append(mask)
        data = payload_for(mask)
        self.assertEqual(data["exits"], ["east", "north"])
        self.assertEqual(data["exit_targets"], {"east": "The Blood of the Vine"})
        self.assertEqual(
            data["visible_nearby"],
            ["Miklós Farkas", "public noticeboard"],
        )
        self.assertEqual(data["visible_residents"], ["Miklós Farkas"])
        encoded = repr(data)
        self.assertNotIn("private staff dossier", encoded)
        self.assertNotIn("secret map", encoded)
        self.assertNotIn("Hidden Chamber", encoded)
        self.assertNotIn("Hidden Witness", encoded)

    def test_public_navigation_and_contextual_actions(self):
        room = Room("Village Square")
        room.exits = [Object("east", 1, destination=Room("The Blood of the Vine"))]
        data = payload_for(Mask(room))
        self.assertEqual(data["schema"], "fvillage.agent_context.v1")
        self.assertEqual(data["exit_targets"]["east"], "The Blood of the Vine")
        self.assertEqual(data["commands"]["firewood"], "hearth gather")
        self.assertEqual(data["commands"]["community_work"], "commission")

    def test_capped_visible_list_and_ooc_boundary(self):
        room = Room("Inn Common Room", kind="ooc")
        room.contents = [Object(f"object-{i:03d}", i) for i in range(60)]
        data = payload_for(Mask(room))
        self.assertEqual(len(data["visible_nearby"]), 32)
        self.assertEqual(data["visible_residents"], [])
        self.assertEqual(data["commands"]["personal_return"], "agenda")
        self.assertNotIn("community_work", data["commands"])


if __name__ == "__main__":
    unittest.main()
