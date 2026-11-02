"""EDGE-41 stage adapter compatibility with already merged Tavern systems.

Executes the real status and archive functions in an isolated adapter boundary.
This is not a substitute for authenticated Evennia sessions or restart tests.
"""
import ast
import copy
from collections.abc import Mapping
from pathlib import Path
import sys
import types
import unittest
from unittest.mock import patch

SOURCE = Path(__file__).resolve().parents[2] / "spike/fvillage/world/stage_work.py"


def source_functions():
    tree = ast.parse(SOURCE.read_text(encoding="utf-8"), filename=str(SOURCE))
    return {node.name: node for node in tree.body
            if isinstance(node, ast.FunctionDef)}


class StageMergedAdapterTests(unittest.TestCase):
    def setUp(self):
        self.functions = source_functions()
        self.assertTrue({
            "status", "archive", "act", "cater", "safety_action",
            "_verified_public_status", "_verified_warning",
            "_verified_decision", "_verified_route_source",
            "_public_service_verified",
        }.issubset(self.functions))
        self.raw = {
            "day": 1, "history": [], "performance": None,
            "witnesses": [], "service": {"bowl_id": 7},
            "safety_warning": {"event_id": 11},
            "safety_decision": {"event_id": 12},
        }
        self.service_signed = True
        self.warning_signed = True
        self.decision_signed = True
        self.tavern = types.SimpleNamespace(
            db=types.SimpleNamespace(village_stage=self.raw)
        )
        self.bowl = types.SimpleNamespace(id=7)
        self.stage_state = types.SimpleNamespace(
            refresh=lambda raw, day: copy.deepcopy(raw),
            public_lines=lambda state, day: "|".join((
                "CATERED" if state["service"] else "UNCATERED",
                "WARNED" if state["safety_warning"] else "NO-WARNING",
                "ADAPTED" if state["safety_decision"] else "NO-DECISION",
            )),
            archive_lines=lambda raw, day: "SIGNED ARCHIVE",
        )
        self.scope = {
            "Mapping": Mapping,
            "stage_state": self.stage_state,
            "_guard": lambda mask: (self.tavern, None),
            "_clock": lambda: (1, 21),
            "search": types.SimpleNamespace(
                search_object=lambda query: [self.bowl]
            ),
            "get_event_ledger": lambda: object(),
            "_public_service_verified": lambda *args: self.service_signed,
            "_verified_warning": lambda *args: self.warning_signed,
            "_verified_decision": lambda *args: self.decision_signed,
        }
        selected = [self.functions[name] for name in
                    ("_verified_public_status", "status", "archive")]
        exec(compile(ast.Module(body=selected, type_ignores=[]),
                     str(SOURCE), "exec"), self.scope)
        self.world = types.ModuleType("world")
        self.world.stage_fitting_work = types.SimpleNamespace(
            public_status=lambda tavern: "FITTED STAGE"
        )

    def status(self):
        with patch.dict(sys.modules, {"world": self.world}):
            return self.scope["status"](object())

    def test_signed_catering_safety_and_fitting_coexist(self):
        result = self.status()
        self.assertIn("CATERED|WARNED|ADAPTED", result)
        self.assertIn("FITTED STAGE", result)
        self.assertEqual(self.raw["service"]["bowl_id"], 7)

    def test_forged_service_and_safety_claims_do_not_become_public(self):
        self.service_signed = False
        self.warning_signed = False
        self.decision_signed = False
        result = self.status()
        self.assertIn("UNCATERED|NO-WARNING|NO-DECISION", result)
        self.assertIn("could not be verified", result)
        self.assertIn("FITTED STAGE", result)
        # A public projection must not silently rewrite the persistent source.
        self.assertEqual(self.raw["service"]["bowl_id"], 7)
        self.assertEqual(self.raw["safety_warning"]["event_id"], 11)

    def test_independent_decision_without_valid_warning_is_not_signed(self):
        self.warning_signed = False
        result = self.status()
        self.assertIn("NO-WARNING|NO-DECISION", result)
        self.assertNotIn("|ADAPTED", result)

    def test_chronicler_archive_remains_available(self):
        self.assertEqual(self.scope["archive"](object()), "SIGNED ARCHIVE")

    def test_live_stage_admission_retains_review_contest_and_safety_gate(self):
        source = ast.unparse(self.functions["act"])
        for required in ("review", "contest", "parse_review_id",
                         "verify_review_sources", "_verified_decision",
                         "The signed Performer safety decision changed"):
            with self.subTest(required=required):
                self.assertIn(required, source)
        safety = ast.unparse(self.functions["safety_action"])
        self.assertIn("_verified_route_source", safety)
        self.assertIn("_verified_warning", safety)


if __name__ == "__main__":
    unittest.main()
