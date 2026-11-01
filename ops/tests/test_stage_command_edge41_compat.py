"""EDGE-41 command compatibility with merged Tavern player-facing mechanics.

Load the actual CmdStage class from source without requiring Evennia. These
tests exercise ordinary command routing and visible denial, not ledger proof.
Authenticated multi-account and restart acceptance are separate CI gates.
"""
import ast
from pathlib import Path
import sys
import types
import unittest
from unittest.mock import patch

SOURCE = Path(__file__).resolve().parents[2] / "spike/fvillage/commands/stage_cmd.py"


def load_command():
    tree = ast.parse(SOURCE.read_text(encoding="utf-8"), filename=str(SOURCE))
    classes = [node for node in tree.body
               if isinstance(node, ast.ClassDef) and node.name == "CmdStage"]
    if len(classes) != 1:
        raise AssertionError("Actual CmdStage must exist exactly once")
    namespace = {"Command": object}
    exec(compile(ast.Module(body=classes, type_ignores=[]),
                 str(SOURCE), "exec"), namespace)
    return namespace["CmdStage"]


class StageCommandCompatibilityTests(unittest.TestCase):
    def setUp(self):
        self.calls = []
        self.messages = []
        self.public = []
        self.error = None

        def safety_action(caller, action, choice=None):
            self.calls.append(("safety", action, choice))
            if self.error:
                return None, self.error
            return {"action": action, "choice": choice, "event_id": 71}, None

        def act(caller, action, arg=None):
            self.calls.append(("stage", action, arg))
            return {"action": action, "event_id": 72, "tune": arg or "ballad"}, None

        def cater(caller):
            self.calls.append(("cater",))
            return {"event_id": 73, "bowl_id": 9, "performance_event_id": 70}, None

        def fitting(caller, action, tune=None):
            self.calls.append(("fitting", action, tune))
            return {"event_id": 74}, None

        self.stage_work = types.SimpleNamespace(
            safety_action=safety_action, act=act, cater=cater,
            archive=lambda caller: "Signed stage archive",
            status=lambda caller: "Stage status",
        )
        self.fitting = types.SimpleNamespace(act=fitting)
        self.world = types.ModuleType("world")
        self.world.stage_work = self.stage_work
        self.world.stage_fitting_work = self.fitting
        self.caller = types.SimpleNamespace(
            key="Tester", msg=self.messages.append,
            location=types.SimpleNamespace(
                msg_contents=lambda message, exclude=None: self.public.append(message)
            ),
        )
        self.command_class = load_command()

    def invoke(self, command):
        cmd = self.command_class()
        cmd.caller = self.caller
        cmd.args = command
        with patch.dict(sys.modules, {"world": self.world}):
            cmd.func()

    def test_hound_warning_and_both_independent_performer_choices(self):
        for args, action, choice in (
            ("warn", "warn", None),
            ("adapt indoor", "adapt", "indoor"),
            ("adapt cancel", "adapt", "cancel"),
        ):
            with self.subTest(args=args):
                self.calls.clear()
                self.messages.clear()
                self.public.clear()
                self.invoke(args)
                self.assertEqual(self.calls, [("safety", action, choice)])
                self.assertIn("world event 71", self.messages[-1])
                self.assertEqual(len(self.public), 1)

    def test_rejected_warning_never_broadcasts_success(self):
        self.error = "Original signed route evidence is missing."
        self.invoke("warn")
        self.assertEqual(self.calls, [("safety", "warn", None)])
        self.assertEqual(self.messages, [self.error])
        self.assertEqual(self.public, [])

    def test_merged_catering_archive_and_stage_fitting_still_dispatch(self):
        for args, expected in (
            ("cater", ("cater",)),
            ("fit", ("fitting", "fit", None)),
            ("soundcheck", ("fitting", "soundcheck", None)),
            ("acoustic reel", ("fitting", "acoustic", "reel")),
            ("review praise", ("stage", "review", "praise")),
            ("contest 51", ("stage", "contest", "51")),
            ("witness", ("stage", "witness", None)),
            ("perform ballad", ("stage", "perform", "ballad")),
        ):
            with self.subTest(args=args):
                self.calls.clear()
                self.messages.clear()
                self.invoke(args)
                self.assertEqual(self.calls, [expected])
                self.assertTrue(self.messages)
        self.messages.clear()
        self.invoke("archive")
        self.assertEqual(self.messages, ["Signed stage archive"])

    def test_public_help_preserves_all_player_paths(self):
        self.invoke("unknown")
        message = self.messages[-1]
        for command in ("stage warn", "stage adapt indoor", "stage adapt cancel",
                        "stage cater", "stage archive", "stage review",
                        "stage contest", "stage fit", "stage soundcheck",
                        "stage acoustic", "stage rehearse", "stage perform"):
            with self.subTest(command=command):
                self.assertIn(command, message)


if __name__ == "__main__":
    unittest.main()
