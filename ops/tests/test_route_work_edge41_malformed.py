"""EDGE-41: real Hound route adapter rejects malformed persisted caution evidence.

The production function bodies are extracted with AST so these regressions run
without Django/Evennia. The full telnet and restart suites cover integration.
"""
import ast
import contextlib
import sys
import types
import unittest
from collections import UserDict, UserList
from collections.abc import Mapping, Sequence
from pathlib import Path

SOURCE = (Path(__file__).resolve().parents[2] /
          "spike/fvillage/world/route_work.py")
FUNCTIONS = {"_caution_marker", "_signed_prior_caution", "field_action"}


def production():
    tree = ast.parse(SOURCE.read_text(encoding="utf-8"))
    nodes = [node for node in tree.body
             if isinstance(node, ast.FunctionDef) and node.name in FUNCTIONS]
    if len(nodes) != len(FUNCTIONS):
        raise AssertionError("Production route caution functions not found")
    ns = {"Mapping": Mapping, "Sequence": Sequence}
    exec(compile(ast.Module(body=nodes, type_ignores=[]),
                 str(SOURCE), "exec"), ns)
    return ns


def signed_source():
    return {
        "kind": "village.route_protected", "status": "complete",
        "actor": {"account_id": 11, "mask_id": 111},
        "payload": {
            "day": 4, "site": "red_cord", "role": "hound",
            "action": "protect", "location": "Northern Treeline",
        },
        "consequence": {
            "cord_object_id": 777, "square_room_id": 88,
            "day": 4, "role": "hound", "action": "protect",
            "caution_marked": True,
        },
    }


class MalformedCautionTests(unittest.TestCase):
    def setUp(self):
        self.ns = production()
        self.cord = types.SimpleNamespace(
            id=777, key="frayed red cord",
            db=types.SimpleNamespace(
                landmark_id="red_cord", route_caution=None,
                route_caution_history=None),
            access=lambda *a, **kw: True)
        self.square = types.SimpleNamespace(
            id=88, db=types.SimpleNamespace(daily_route_survey=None))
        self.ns["LANDMARKS"] = {
            "red_cord": {"room": "Northern Treeline",
                         "key": "frayed red cord"}}
        self.source = signed_source()
        self.ns["get_event_ledger"] = lambda: types.SimpleNamespace(
            get_event=lambda event_id: self.source if event_id == 90 else None)
        self.marker = {
            "event_id": 90, "account_id": 11, "day": 4,
            "prior_caution_event_id": None,
        }

    def test_physical_marker_requires_mapping_but_accepts_userdict(self):
        read = self.ns["_caution_marker"]
        self.assertEqual(read(None), {})
        self.assertEqual(read(UserDict(self.marker)), self.marker)
        for bad in (False, 0, "", "bad", 17, [("event_id", 90)], ["bad"]):
            with self.subTest(raw=bad):
                self.assertIsNone(read(bad))

    def test_signed_prior_validates_real_source_and_wrappers(self):
        verify = self.ns["_signed_prior_caution"]
        self.assertTrue(verify(self.cord, self.square, self.marker, 5))
        wrapped = signed_source()
        for field in ("actor", "payload", "consequence"):
            wrapped[field] = UserDict(wrapped[field])
        self.source = UserDict(wrapped)
        self.assertTrue(verify(self.cord, self.square, UserDict(self.marker), 5))
        self.assertFalse(verify(self.cord, self.square, self.marker, 4))
        self.assertFalse(verify(self.cord, self.square, self.marker, 3))

    def test_malformed_ledger_root_and_nested_receipts_fail_closed(self):
        verify = self.ns["_signed_prior_caution"]
        for bad in (None, 17, "bad", ["bad"]):
            with self.subTest(root=bad):
                self.source = bad
                self.assertFalse(verify(self.cord, self.square, self.marker, 5))
        for field in ("actor", "payload", "consequence"):
            for bad in (None, 17, "bad", ["bad"]):
                with self.subTest(field=field, bad=bad):
                    self.source = signed_source()
                    self.source[field] = bad
                    self.assertFalse(verify(self.cord, self.square,
                                            self.marker, 5))

    def _player_scene(self, role, marker):
        self.cord.db.route_caution = marker
        room = types.SimpleNamespace(
            key="Northern Treeline", contents=[self.cord],
            tags=types.SimpleNamespace(has=lambda *a, **kw: True))
        self.cord.location = room
        mask = types.SimpleNamespace(
            key="Player", account=types.SimpleNamespace(id=11),
            location=room, db=types.SimpleNamespace(
                landmark_discoveries=[{"id": "red_cord"}],
                landmark_latest_view={"red_cord": {"day": 5}}))
        self.ns.update({
            "active_calling": lambda player: role,
            "_day_hour": lambda: (5, 20),
            "known_landmarks": lambda raw: raw,
            "_square": lambda: self.square,
            "route_surveys": types.SimpleNamespace(
                field_decision=lambda *a, **kw: ({}, True, None)),
            "transaction": types.SimpleNamespace(atomic=contextlib.nullcontext),
            "record_participation": lambda *a, **kw: None,
        })
        return mask

    def test_player_commands_reject_corrupt_cord_without_world_event(self):
        for role, action in (("hound", "protect"),
                             ("wanderer", "passability")):
            for bad in ("bad", 17, ["bad"], False, [("day", 4)]):
                with self.subTest(role=role, marker=bad):
                    mask = self._player_scene(role, bad)
                    self.ns["publish_world_event"] = lambda *a, **kw: (
                        self.fail("Malformed marker must not publish an event"))
                    result, error = self.ns["field_action"](mask, action)
                    self.assertIsNone(result)
                    self.assertIn("malformed", error)

    def test_marker_changed_to_corrupt_during_signed_action_rejects_commit(self):
        for role, action in (("hound", "protect"),
                             ("wanderer", "passability")):
            with self.subTest(role=role):
                mask = self._player_scene(role, None)
                def publish(kind, *, actor, payload, consequence):
                    self.cord.db.route_caution = ["corrupt"]
                    return consequence({"id": 99})
                self.ns["publish_world_event"] = publish
                with self.assertRaisesRegex(RuntimeError, "became malformed"):
                    self.ns["field_action"](mask, action)


    def test_third_day_renewal_accepts_persisted_evennia_sequence(self):
        """Day 6 must accept the day-5 saved history, not just the first renewal."""
        mask = self._player_scene("hound", UserDict(self.marker))
        # The adapter test executes the real field_action body, not a
        # substitute for its persistence and provenance checks.
        self.ns["route_surveys"] = types.SimpleNamespace(
            field_decision=lambda *a, **kw: (
                {"field_decisions": {}}, True, None))
        signed_day_five = signed_source()
        signed_day_five["payload"]["day"] = 5
        signed_day_five["consequence"]["day"] = 5
        sources = {90: self.source, 99: signed_day_five}
        self.ns["get_event_ledger"] = lambda: types.SimpleNamespace(
            get_event=lambda event_id: sources.get(event_id))

        def publish_five(kind, *, actor, payload, consequence):
            consequence({"id": 99})
            return {"id": 99}

        self.ns["publish_world_event"] = publish_five
        result, error = self.ns["field_action"](mask, "protect")
        self.assertIsNone(error)
        self.assertEqual(result["event_id"], 99)
        self.assertEqual(
            [row["event_id"] for row in self.cord.db.route_caution_history],
            [90])
        self.assertEqual(self.cord.db.route_caution["day"], 5)

        # Evennia restores this list as a mutable sequence wrapper on restart.
        self.cord.db.route_caution_history = UserList(
            self.cord.db.route_caution_history)
        mask.db.landmark_latest_view["red_cord"]["day"] = 6
        self.ns["_day_hour"] = lambda: (6, 20)

        def publish_six(kind, *, actor, payload, consequence):
            consequence({"id": 100})
            return {"id": 100}

        self.ns["publish_world_event"] = publish_six
        result, error = self.ns["field_action"](mask, "protect")
        self.assertIsNone(error)
        self.assertEqual(result["event_id"], 100)
        self.assertEqual(
            [row["event_id"] for row in self.cord.db.route_caution_history],
            [90, 99])
        self.assertEqual(self.cord.db.route_caution["day"], 6)
        self.assertEqual(self.cord.db.route_caution["prior_caution_event_id"], 99)

    def test_wrapped_history_rejects_malformed_rows_and_strings(self):
        for bad in (UserList([self.marker, "bad"]),
                    UserList([self.marker, None]), "bad", b"bad"):
            with self.subTest(history=repr(bad)):
                mask = self._player_scene("hound", self.marker)
                self.cord.db.route_caution_history = bad
                self.ns["publish_world_event"] = (
                    lambda kind, *, actor, payload, consequence:
                    consequence({"id": 99}))
                with self.assertRaisesRegex(RuntimeError, "history is malformed"):
                    self.ns["field_action"](mask, "protect")
                self.assertEqual(self.cord.db.route_caution, self.marker)

    def test_corrupt_history_prevents_signed_retying(self):
        mask = self._player_scene("hound", self.marker)
        self.cord.db.route_caution_history = "corrupt"
        def publish(kind, *, actor, payload, consequence):
            return consequence({"id": 99})
        self.ns["publish_world_event"] = publish
        with self.assertRaisesRegex(RuntimeError, "history is malformed"):
            self.ns["field_action"](mask, "protect")
        self.assertEqual(self.cord.db.route_caution, self.marker)


if __name__ == "__main__":
    unittest.main()
