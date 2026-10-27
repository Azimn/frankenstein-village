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
                self.assertEqual(len(calls), 2 if name == "field_action" else 1)


if __name__ == "__main__":
    unittest.main()
