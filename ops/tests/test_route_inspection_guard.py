"""Route inspection commands must reject malformed persisted player views.

The small guard is extracted from the actual production source so these
tests run offline without importing Django or Evennia.
"""
import ast
from pathlib import Path
from types import SimpleNamespace
import unittest


SOURCE = Path(__file__).resolve().parents[2] / "spike/fvillage/world/route_work.py"


class RouteInspectionGuardTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        tree = ast.parse(SOURCE.read_text(encoding="utf-8"), filename=str(SOURCE))
        functions = {
            node.name: node for node in tree.body
            if isinstance(node, ast.FunctionDef)
        }
        guard = functions["_inspected_today"]
        namespace = {"Mapping": __import__("collections.abc", fromlist=["Mapping"]).Mapping}
        exec(compile(ast.fix_missing_locations(ast.Module(
            body=[guard], type_ignores=[]
        )), str(SOURCE), "exec"), namespace)
        cls.guard = staticmethod(namespace["_inspected_today"])
        cord_guard = functions["_cord_condition_matches_inspection"]
        exec(compile(ast.fix_missing_locations(ast.Module(
            body=[cord_guard], type_ignores=[]
        )), str(SOURCE), "exec"), namespace)
        cls.cord_guard = staticmethod(namespace["_cord_condition_matches_inspection"])
        cls.functions = functions

    def test_real_same_day_view_still_qualifies(self):
        for value in ({"day": 4}, {"day": "4"}):
            mask = SimpleNamespace(db=SimpleNamespace(
                landmark_latest_view={"red_cord": value}
            ))
            self.assertTrue(self.guard(mask, "red_cord", 4))
            self.assertFalse(self.guard(mask, "red_cord", 5))

    def test_corrupt_and_untrusted_views_fail_closed(self):
        invalid = (
            None, "", "damaged", 7, True, [("red_cord", {"day": 4})],
            {"red_cord": 4}, {"red_cord": "broken"},
            {"red_cord": ["day", 4]}, {"red_cord": {"day": True}},
            {"red_cord": {"day": float("inf")}},
            {"red_cord": {"day": "tomorrow"}},
        )
        for view in invalid:
            with self.subTest(view=view):
                mask = SimpleNamespace(db=SimpleNamespace(
                    landmark_latest_view=view
                ))
                self.assertFalse(self.guard(mask, "red_cord", 4))

    def test_both_real_player_actions_use_the_same_guard(self):
        for name in ("report", "field_action"):
            with self.subTest(action=name):
                calls = [
                    node for node in ast.walk(self.functions[name])
                    if isinstance(node, ast.Call)
                    and isinstance(node.func, ast.Name)
                    and node.func.id == "_inspected_today"
                ]
                self.assertEqual(len(calls), 2, "Preflight and commit both require inspection")


    def test_cord_warning_must_match_the_actual_firsthand_view(self):
        def scene(observed, current):
            mask = SimpleNamespace(db=SimpleNamespace(
                landmark_latest_view={
                    "red_cord": {"day": 4, "hour": 12,
                                 "caution_event_id": observed}
                }
            ))
            cord = SimpleNamespace(db=SimpleNamespace(
                route_caution=(
                    {"event_id": current} if current is not None else None
                )
            ))
            return mask, cord

        for observed, current in ((0, None), (31, 31), (42, 42)):
            mask, cord = scene(observed, current)
            self.assertTrue(self.cord_guard(mask, cord))

        # A Hound can tie or tend the cord during the same village hour.
        # The Wanderer's old inspection must not be signed as a new view.
        for observed, current in ((0, 31), (31, 42), (31, None)):
            mask, cord = scene(observed, current)
            self.assertFalse(self.cord_guard(mask, cord))

        for invalid in (None, True, -1, "31", [], {"event_id": 31}):
            mask, cord = scene(invalid, 31)
            self.assertFalse(self.cord_guard(mask, cord))
        mask, cord = scene(31, 31)
        mask.db.landmark_latest_view["red_cord"].pop("caution_event_id")
        self.assertFalse(self.cord_guard(mask, cord),
                         "Legacy inspection requires a fresh physical look")

    def test_both_field_action_gates_recheck_warning_version(self):
        field = self.functions["field_action"]
        calls = [
            node for node in ast.walk(field)
            if isinstance(node, ast.Call)
            and isinstance(node.func, ast.Name)
            and node.func.id == "_cord_condition_matches_inspection"
        ]
        self.assertEqual(len(calls), 2,
                         "Preflight and signed consequence must recheck")

    def test_physical_look_captures_cord_warning_version(self):
        # Exercise the actual production capture function without Evennia.
        import sys
        from types import ModuleType
        from unittest.mock import patch

        source = SOURCE.parents[0] / "discoveries.py"
        tree = ast.parse(source.read_text(encoding="utf-8"), filename=str(source))
        capture = next(
            node for node in tree.body
            if isinstance(node, ast.FunctionDef) and node.name == "capture"
        )
        namespace = {
            "LANDMARKS": {
                "red_cord": {"key": "a frayed red cord",
                             "room": "The Northern Treeline"}
            },
            "record": lambda raw, ident, day, hour: ([], False),
        }
        exec(compile(ast.fix_missing_locations(ast.Module(
            body=[capture], type_ignores=[]
        )), str(source), "exec"), namespace)

        class ScriptDB:
            objects = SimpleNamespace(get=lambda **kw: SimpleNamespace(
                db=SimpleNamespace(day=4, hour=12)
            ))

        evennia = ModuleType("evennia")
        scripts = ModuleType("evennia.scripts")
        models = ModuleType("evennia.scripts.models")
        models.ScriptDB = ScriptDB
        room = SimpleNamespace(
            key="The Northern Treeline",
            tags=SimpleNamespace(has=lambda *args, **kw: True),
        )
        looker = SimpleNamespace(
            account=SimpleNamespace(id=9), location=room,
            db=SimpleNamespace(landmark_latest_view=None,
                               landmark_discoveries=[]),
        )
        cord = SimpleNamespace(
            key="a frayed red cord", location=room,
            db=SimpleNamespace(route_caution=None),
        )
        with patch.dict(sys.modules, {
            "evennia": evennia, "evennia.scripts": scripts,
            "evennia.scripts.models": models,
        }):
            namespace["capture"](looker, cord, "red_cord")
            self.assertEqual(
                looker.db.landmark_latest_view["red_cord"]["caution_event_id"], 0
            )
            cord.db.route_caution = {"event_id": 81, "day": 4}
            namespace["capture"](looker, cord, "red_cord")
            self.assertEqual(
                looker.db.landmark_latest_view["red_cord"]["caution_event_id"], 81
            )


if __name__ == "__main__":
    unittest.main()
