"""Exercise the real player command boundary without importing Evennia.

A competing account or advancing village clock can invalidate a signed
Hound/Wanderer action after preflight. The canonical ledger marks the event
failed; the caller must get recoverable feedback, not a server traceback.
"""
import ast
from collections.abc import Mapping
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
        inspection_guard = next(
            node for node in module.body
            if isinstance(node, ast.FunctionDef) and node.name == "_inspected_today"
        )
        code = compile(ast.fix_missing_locations(ast.Module(
            body=[inspection_guard, function], type_ignores=[]
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
            "Mapping": Mapping,
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


    def test_signed_consequence_rechecks_current_role_inspection_and_access(self):
        """A preflight-valid Hound cannot sign after authority is revoked."""
        from contextlib import nullcontext

        source = (Path(__file__).resolve().parents[2]
                  / "spike/fvillage/world/route_work.py")
        tree = ast.parse(source.read_text(encoding="utf-8"), filename=str(source))
        functions = {
            node.name: node for node in tree.body
            if isinstance(node, ast.FunctionDef)
        }
        code = compile(ast.fix_missing_locations(ast.Module(
            body=[functions["_inspected_today"], functions["field_action"]],
            type_ignores=[],
        )), str(source), "exec")
        roles = ["hound"]
        can_view = [True]
        mode = ["none"]
        cord = SimpleNamespace(
            id=23, key="frayed red cord",
            db=SimpleNamespace(landmark_id="red_cord", route_caution=None),
            access=lambda *_args, **_kwargs: can_view[0],
        )
        room = SimpleNamespace(
            key="Northern Treeline",
            tags=SimpleNamespace(has=lambda *_args, **_kwargs: True),
            contents=[cord],
        )
        cord.location = room
        mask = SimpleNamespace(
            account=SimpleNamespace(id=7), key="Hound", location=room,
            db=SimpleNamespace(
                landmark_discoveries=[],
                landmark_latest_view={"red_cord": {"day": 3}},
            ),
        )
        square = SimpleNamespace(
            id=11, db=SimpleNamespace(daily_route_survey=None)
        )
        participation = Mock()

        def publish(_kind, **kwargs):
            if mode[0] == "role":
                roles[0] = "innkeep"
            elif mode[0] == "inspection":
                mask.db.landmark_latest_view.clear()
            elif mode[0] == "access":
                can_view[0] = False
            kwargs["consequence"]({"id": 44})
            return {"id": 44}

        namespace = {
            "Mapping": Mapping,
            "active_calling": lambda _mask: roles[0],
            "LANDMARKS": {"red_cord": {
                "room": "Northern Treeline", "key": "frayed red cord",
            }},
            "known_landmarks": lambda _raw: [{"id": "red_cord"}],
            "_square": lambda: square,
            "_day_hour": lambda: (3, 12),
            "route_surveys": SimpleNamespace(
                field_decision=lambda *_args: ({"field_decisions": {}}, True, None)
            ),
            "publish_world_event": publish,
            "transaction": SimpleNamespace(atomic=nullcontext),
            "record_participation": participation,
        }
        exec(code, namespace)
        for scenario in ("role", "inspection", "access"):
            with self.subTest(scenario=scenario):
                roles[0] = "hound"
                can_view[0] = True
                mask.db.landmark_latest_view = {"red_cord": {"day": 3}}
                square.db.daily_route_survey = None
                cord.db.route_caution = None
                participation.reset_mock()
                mode[0] = scenario
                result, error = namespace["field_action"](mask, "protect")
                self.assertIsNone(result)
                self.assertTrue(error)
                self.assertIsNone(cord.db.route_caution)
                self.assertIsNone(square.db.daily_route_survey)
                participation.assert_not_called()

        # The same real command body still commits a valid action.
        roles[0] = "hound"
        can_view[0] = True
        mask.db.landmark_latest_view = {"red_cord": {"day": 3}}
        mode[0] = "none"
        result, error = namespace["field_action"](mask, "protect")
        self.assertIsNone(error)
        self.assertEqual(result["event_id"], 44)
        self.assertEqual(cord.db.route_caution["event_id"], 44)
        participation.assert_called_once()



    def test_civic_report_rechecks_firsthand_authority_at_commit(self):
        """A revoked observation cannot create a public signed report."""
        from contextlib import nullcontext

        source = (Path(__file__).resolve().parents[2]
                  / "spike/fvillage/world/route_work.py")
        tree = ast.parse(source.read_text(encoding="utf-8"), filename=str(source))
        functions = {
            node.name: node for node in tree.body
            if isinstance(node, ast.FunctionDef)
        }
        code = compile(ast.fix_missing_locations(ast.Module(
            body=[functions["_inspected_today"], functions["report"]],
            type_ignores=[],
        )), str(source), "exec")
        mode = ["valid"]
        can_view = [True]
        discovered = [True]
        clue = SimpleNamespace(
            key="frayed red cord",
            db=SimpleNamespace(landmark_id="red_cord"),
            access=lambda *_args, **_kwargs: can_view[0],
        )
        room = SimpleNamespace(
            key="Northern Treeline",
            tags=SimpleNamespace(has=lambda *_args, **_kwargs: True),
            contents=[clue],
        )
        clue.location = room
        mask = SimpleNamespace(
            account=SimpleNamespace(id=7), key="Witness", location=room,
            db=SimpleNamespace(
                landmark_discoveries=[],
                landmark_latest_view={"red_cord": {"day": 3}},
            ),
        )
        square = SimpleNamespace(db=SimpleNamespace(daily_route_survey=None))
        signed = Mock()

        def refresh(raw, day):
            return raw if isinstance(raw, dict) else {"day": day, "reports": {}}

        def record(raw, day, site, account_id, name, event_id):
            signed()
            state = {"day": day, "reports": {
                site: {"account_id": account_id, "mask": name,
                       "event_id": event_id}
            }}
            return state, True, None

        def publish(_kind, **kwargs):
            if mode[0] == "account":
                mask.account = SimpleNamespace(id=8)
            elif mode[0] == "inspection":
                mask.db.landmark_latest_view.clear()
            elif mode[0] == "discovery":
                discovered[0] = False
            elif mode[0] == "view":
                can_view[0] = False
            kwargs["consequence"]({"id": 44})
            return {"id": 44}

        namespace = {
            "Mapping": Mapping,
            "LANDMARKS": {"red_cord": {
                "room": "Northern Treeline", "key": "frayed red cord",
            }},
            "known_landmarks": lambda _raw: (
                [{"id": "red_cord"}] if discovered[0] else []
            ),
            "_square": lambda: square,
            "_day_hour": lambda: (3, 12),
            "route_surveys": SimpleNamespace(
                SITES=("red_cord",), refresh=refresh, report=record,
                complete=lambda _state: True,
            ),
            "publish_world_event": publish,
            "transaction": SimpleNamespace(atomic=nullcontext),
            "active_calling": lambda _mask: None,
            "record_participation": Mock(),
            "SCOUT_ROLES": frozenset(),
        }
        exec(code, namespace)
        for scenario in ("account", "inspection", "discovery", "view"):
            with self.subTest(scenario=scenario):
                mask.account = SimpleNamespace(id=7)
                mask.db.landmark_latest_view = {"red_cord": {"day": 3}}
                discovered[0] = True
                can_view[0] = True
                square.db.daily_route_survey = None
                signed.reset_mock()
                mode[0] = scenario
                result, error = namespace["report"](mask)
                self.assertIsNone(result)
                self.assertTrue(error)
                self.assertIsNone(square.db.daily_route_survey)
                signed.assert_not_called()

        mask.account = SimpleNamespace(id=7)
        mask.db.landmark_latest_view = {"red_cord": {"day": 3}}
        discovered[0] = True
        can_view[0] = True
        mode[0] = "valid"
        result, error = namespace["report"](mask)
        self.assertIsNone(error)
        self.assertEqual(result["event_id"], 44)
        self.assertEqual(
            square.db.daily_route_survey["reports"]["red_cord"]["account_id"], 7
        )
        signed.assert_called_once()


if __name__ == "__main__":
    unittest.main()
