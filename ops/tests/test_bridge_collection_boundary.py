"""B13 command-boundary regressions against the actual bridgework collection body.

The extracted production function runs with disposable ordinary-player,
physical-room, finite-table and event-consequence doubles. This is not a
claim of a new authenticated telnet session; the full clean-checkout suite
runs the existing real-client and restart scenarios separately.
"""
import ast
from contextlib import nullcontext
from pathlib import Path
import sys
import types
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "spike/fvillage"))
from world import bridge_choices, bridge_materials, bridge_provenance


class BridgeCollectBoundaryTests(unittest.TestCase):
    def setUp(self):
        self.market = types.SimpleNamespace(
            key="Market Lane",
            tags=types.SimpleNamespace(has=lambda *a, **k: True),
        )
        self.bridge = types.SimpleNamespace(
            id=300,
            db=types.SimpleNamespace(bridge_inquiry=None),
        )
        self.table = types.SimpleNamespace(
            id=500,
            location=self.market,
            db=types.SimpleNamespace(bridge_material_stock={
                "day": 2, "remaining": {"preserve": 2, "display": 2}
            }),
        )
        self.mask = types.SimpleNamespace(
            location=self.market,
            account=types.SimpleNamespace(id=12),
            contents=[],
        )
        self.published = []
        self.created = []
        self.inject_before_consequence = None
        source = (ROOT / "spike/fvillage/world/bridge_work.py").read_text(
            encoding="utf-8"
        )
        tree = ast.parse(source)
        functions = [node for node in tree.body
                     if isinstance(node, ast.FunctionDef)
                     and node.name in {"collect", "_collection_open"}]
        self.assertTrue(any(node.name == "collect" for node in functions))
        env = {
            "MARKET_NAME": "Market Lane",
            "_market_supply": lambda: self.table,
            "_bridge": lambda: self.bridge,
            "_carried": lambda mask: [],
            "_ledger_get": lambda event_id: None,
            "_clock": lambda: (2, 19),
            "bridge_choices": bridge_choices,
            "bridge_materials": bridge_materials,
            "bridge_provenance": bridge_provenance,
            "transaction": types.SimpleNamespace(atomic=nullcontext),
            "create_object": self._create_object,
            "publish_world_event": self._publish,
        }
        exec(compile(ast.Module(body=functions, type_ignores=[]),
                     str(ROOT / "spike/fvillage/world/bridge_work.py"), "exec"),
             env)
        self.collect = env["collect"]
        self.market_work = types.ModuleType("world.market_work")
        self.market_work.supply_held = lambda: False

    def _create_object(self, *args, **kwargs):
        obj = types.SimpleNamespace(
            id=700 + len(self.created),
            key=kwargs["key"],
            db=types.SimpleNamespace(),
        )
        self.created.append(obj)
        return obj

    def _publish(self, kind, *, actor, payload, consequence):
        self.published.append(kind)
        if self.inject_before_consequence is not None:
            self.bridge.db.bridge_inquiry = self.inject_before_consequence
        result = consequence({"id": 81})
        return {"id": 81, "consequence": result}

    def _collect(self):
        with patch.dict(sys.modules, {"world.market_work": self.market_work}):
            return self.collect(self.mask, "preserve")

    def test_corrupt_saved_record_fails_closed_before_signed_event(self):
        for raw in (7, True, "invalid", {"resolution": {"choice": "preserve"}},
                    {"checks": [{"event_id": 91}]}):
            with self.subTest(raw=raw):
                self.bridge.db.bridge_inquiry = raw
                original_stock = dict(self.table.db.bridge_material_stock["remaining"])
                result, error = self._collect()
                self.assertIsNone(result)
                self.assertIn("source review", error)
                self.assertEqual(self.table.db.bridge_material_stock["remaining"],
                                 original_stock)
                self.assertEqual(self.bridge.db.bridge_inquiry, raw)
                self.assertEqual(self.created, [])
                self.assertEqual(self.published, [])

    def test_corrupt_record_between_preview_and_consequence_cannot_mint_kit(self):
        for raw in (7, True, {"resolution": {"choice": "preserve"}}):
            with self.subTest(raw=raw):
                self.bridge.db.bridge_inquiry = None
                self.inject_before_consequence = raw
                with self.assertRaisesRegex(RuntimeError, "source review"):
                    self._collect()
                self.assertEqual(
                    self.table.db.bridge_material_stock["remaining"]["preserve"], 2
                )
                self.assertEqual(self.created, [])
                self.assertEqual(self.bridge.db.bridge_inquiry, raw)
                self.published.clear()

    def test_unsettled_original_record_preserves_finite_solo_collection(self):
        for raw in (None, {"resolution": None, "checks": []}):
            with self.subTest(raw=raw):
                self.bridge.db.bridge_inquiry = raw
                self.inject_before_consequence = None
                self.table.db.bridge_material_stock = {
                    "day": 2, "remaining": {"preserve": 2, "display": 2}
                }
                self.created.clear()
                self.published.clear()
                result, error = self._collect()
                self.assertIsNone(error)
                self.assertEqual(result["remaining"], 1)
                self.assertEqual(self.table.db.bridge_material_stock["remaining"]["preserve"], 1)
                self.assertEqual(self.created[-1].db.bridge_material_source_event, 81)
                self.assertEqual(self.published, ["village.bridge_material_collected"])


if __name__ == "__main__":
    unittest.main()
