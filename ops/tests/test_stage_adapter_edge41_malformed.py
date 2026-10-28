"""EDGE-41 adapter regression: malformed saved evidence must fail closed.

Load only the real adapter's three verification functions via AST so this
pure unit test runs without Django or Evennia. This tests the production
function bodies, not copied verification logic.
"""
import ast
import copy
import sys
import types
import unittest
from collections import UserDict
from collections.abc import Mapping
from pathlib import Path
from unittest.mock import patch

SOURCE = (Path(__file__).resolve().parents[2] /
          "spike/fvillage/world/stage_work.py")
FUNCTIONS = {"_verified_warning", "_verified_decision", "_verified_route_source"}


def load_functions():
    tree = ast.parse(SOURCE.read_text(encoding="utf-8"))
    selected = [node for node in tree.body
                if isinstance(node, ast.FunctionDef) and node.name in FUNCTIONS]
    if len(selected) != len(FUNCTIONS):
        raise AssertionError("EDGE-41 adapter verification functions missing")
    namespace = {"Mapping": Mapping}
    exec(compile(ast.Module(body=selected, type_ignores=[]),
                 str(SOURCE), "exec"), namespace)
    return namespace


def evidence():
    warning = {
        "account_id": 11, "mask_id": 111, "event_id": 102,
        "source_event_id": 90, "cord_id": 777, "hour": 20,
    }
    decision = {
        "account_id": 22, "mask_id": 222, "event_id": 103,
        "warning_event_id": 102, "choice": "indoor", "hour": 21,
    }
    events = {
        102: {
            "kind": "village.stage_warned", "status": "complete",
            "actor": {"account_id": 11, "mask_id": 111},
            "payload": {"day": 4, "hour": 20, "source_event_id": 90},
            "consequence": {
                "source_event_id": 90, "hour": 20, "cord_id": 777,
                "tavern_room_id": 300,
            },
        },
        103: {
            "kind": "village.stage_adapted", "status": "complete",
            "actor": {"account_id": 22, "mask_id": 222},
            "payload": {"day": 4, "hour": 21, "choice": "indoor"},
            "consequence": {
                "tavern_room_id": 300, "hour": 21,
                "warning_event_id": 102, "choice": "indoor",
            },
        },
    }
    return {"safety_warning": warning, "safety_decision": decision}, events


class Edge41MalformedAdapterTests(unittest.TestCase):
    def setUp(self):
        self.ns = load_functions()
        self.state, self.events = evidence()
        self.ns.update({
            "stage_state": types.SimpleNamespace(
                refresh=lambda raw, day: raw,
                verified_hound_source=lambda *a, **kw: True,
            ),
            "_tavern": lambda: types.SimpleNamespace(id=300),
            "_verified_route_source": lambda **kw: True,
            "get_event_ledger": lambda: types.SimpleNamespace(
                get_event=lambda event_id: self.events.get(event_id)),
        })

    def test_valid_warning_and_independent_decision(self):
        self.assertTrue(self.ns["_verified_warning"](self.state, 4, 21))
        self.assertTrue(self.ns["_verified_decision"](self.state, 4, 21))

    def test_corrupt_warning_nested_receipts_are_rejected_not_crashed(self):
        for field in ("actor", "payload", "consequence"):
            for invalid in (None, 17, "corrupt", ["bad"]):
                with self.subTest(field=field, invalid=invalid):
                    state, events = evidence()
                    events[102][field] = invalid
                    self.events = events
                    self.assertFalse(self.ns["_verified_warning"](state, 4, 21))
                    self.assertFalse(self.ns["_verified_decision"](state, 4, 21))

    def test_corrupt_decision_nested_receipts_are_rejected_not_crashed(self):
        for field in ("actor", "payload", "consequence"):
            for invalid in (None, 17, "corrupt", ["bad"]):
                with self.subTest(field=field, invalid=invalid):
                    state, events = evidence()
                    events[103][field] = invalid
                    self.events = events
                    self.assertTrue(self.ns["_verified_warning"](state, 4, 21))
                    self.assertFalse(self.ns["_verified_decision"](state, 4, 21))

    def test_persisted_mapping_wrappers_remain_valid(self):
        state, events = evidence()
        for event in events.values():
            for field in ("actor", "payload", "consequence"):
                event[field] = UserDict(event[field])
        self.events = events
        self.assertTrue(self.ns["_verified_warning"](state, 4, 21))
        self.assertTrue(self.ns["_verified_decision"](state, 4, 21))

    def test_missing_tavern_fails_closed(self):
        self.ns["_tavern"] = lambda: None
        self.assertFalse(self.ns["_verified_warning"](self.state, 4, 21))
        self.assertFalse(self.ns["_verified_decision"](self.state, 4, 21))

    def test_corrupt_physical_cord_marker_fails_closed(self):
        # Exercise the real source adapter with an actual route/room/object
        # arrangement, but replace external Evennia/Django dependencies.
        original = self.ns["_verified_route_source"]
        source_ns = load_functions()
        source_ns["stage_state"] = self.ns["stage_state"]
        source_ns["get_event_ledger"] = self.ns["get_event_ledger"]
        self.ns["_verified_route_source"] = source_ns["_verified_route_source"]
        square = types.SimpleNamespace(
            id=88, db=types.SimpleNamespace(daily_route_survey={
                "day": 4, "field_decisions": {
                    "hound": {"event_id": 90, "account_id": 11},
                },
            }))
        cord = types.SimpleNamespace(
            id=777, key="frayed red cord",
            db=types.SimpleNamespace(landmark_id="red_cord", route_caution=None))
        room = types.SimpleNamespace(
            key="Northern Treeline", location=None, contents=[cord])
        fake_world = types.ModuleType("world")
        fake_world.route_work = types.SimpleNamespace(_square=lambda: square)
        fake_world.route_surveys = types.SimpleNamespace(normalize=lambda raw: raw)
        discoveries = types.ModuleType("world.discoveries")
        discoveries.LANDMARKS = {
            "red_cord": {"room": "Northern Treeline", "key": "frayed red cord"}}
        source_ns["search"] = types.SimpleNamespace(search_object=lambda key: [room])
        args = dict(account_id=11, mask_id=111, source_event_id=90,
                    cord_id=777, day=4, hour=21)
        try:
            with patch.dict(sys.modules, {"world": fake_world,
                                          "world.discoveries": discoveries}):
                for invalid in (None, "bad", ["bad"], 17, [("bad",)]):
                    with self.subTest(marker=invalid):
                        cord.db.route_caution = invalid
                        self.assertFalse(self.ns["_verified_route_source"](**args))
                cord.db.route_caution = UserDict({
                    "event_id": 90, "account_id": 11, "day": 4})
                self.assertTrue(self.ns["_verified_route_source"](**args))
        finally:
            self.ns["_verified_route_source"] = original


if __name__ == "__main__":
    unittest.main()
