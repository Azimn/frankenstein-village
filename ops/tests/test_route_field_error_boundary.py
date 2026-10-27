"""Exercise the real player command boundary without importing Evennia.

A competing account or advancing village clock can invalidate a signed
Hound/Wanderer action after preflight. The canonical ledger marks the event
failed; the caller must get recoverable feedback, not a server traceback.
"""
import ast
from pathlib import Path
from types import SimpleNamespace
import unittest
from unittest.mock import Mock


class FieldActionErrorBoundaryTests(unittest.TestCase):
    def test_late_signed_action_rejection_is_player_feedback(self):
        source = (Path(__file__).resolve().parents[2]
                  / "spike/fvillage/world/route_work.py")
        module = ast.parse(source.read_text(encoding="utf-8"), filename=str(source))
        function = next(
            node for node in module.body
            if isinstance(node, ast.FunctionDef) and node.name == "field_action"
        )
        code = compile(ast.fix_missing_locations(ast.Module(
            body=[function], type_ignores=[]
        )), str(source), "exec")
        cord = SimpleNamespace(
            key="frayed red cord",
            db=SimpleNamespace(landmark_id="red_cord", route_caution=None),
            access=lambda *_args, **_kwargs: True,
        )
        room = SimpleNamespace(
            key="Northern Treeline",
            tags=SimpleNamespace(has=lambda *_args, **_kwargs: True),
            contents=[cord],
        )
        mask = SimpleNamespace(
            account=SimpleNamespace(id=7), key="Hound", location=room,
            db=SimpleNamespace(
                landmark_discoveries=[],
                landmark_latest_view={"red_cord": {"day": 3}},
            ),
        )
        square = SimpleNamespace(db=SimpleNamespace(daily_route_survey=None))
        publish = Mock(side_effect=RuntimeError(
            "Village time advanced before this route action."
        ))
        namespace = {
            "active_calling": lambda _mask: "hound",
            "LANDMARKS": {"red_cord": {
                "room": "Northern Treeline", "key": "frayed red cord",
            }},
            "known_landmarks": lambda _raw: [{"id": "red_cord"}],
            "_square": lambda: square,
            "_day_hour": lambda: (3, 12),
            "route_surveys": SimpleNamespace(field_decision=lambda *_args: (
                None, True, None
            )),
            "publish_world_event": publish,
        }
        exec(code, namespace)
        result, error = namespace["field_action"](mask, "protect")
        self.assertIsNone(result)
        self.assertEqual(error, "Village time advanced before this route action.")
        publish.assert_called_once()
        self.assertEqual(publish.call_args.args[0], "village.route_protected")
        publish.reset_mock(side_effect=True)
        publish.return_value = {"id": 44}
        result, error = namespace["field_action"](mask, "protect")
        self.assertIsNone(error)
        self.assertEqual(result["event_id"], 44)


if __name__ == "__main__":
    unittest.main()
