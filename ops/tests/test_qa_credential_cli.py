"""Prevent intermittent CLI failures from option-looking random QA passwords."""
from __future__ import annotations

import importlib.util
import io
import sys
import unittest
from contextlib import redirect_stderr
from pathlib import Path
from unittest.mock import patch


RUNNER = Path(__file__).resolve().parents[2] / "spike" / "tests" / "run_all.py"
spec = importlib.util.spec_from_file_location("regression_runner", RUNNER)
runner = importlib.util.module_from_spec(spec)
spec.loader.exec_module(runner)


class TestRunnerPassword(unittest.TestCase):
    def test_leading_dash_from_random_source_is_safe_for_argparse(self):
        # This exact random shape broke main's clean checkout after PR #50.
        with patch.object(runner.secrets, "token_urlsafe", return_value="-unlucky"):
            password = runner.qa_cli_password()
        self.assertEqual(password, "qa_-unlucky")
        self.assertTrue(password[0].isalpha())
        self.assertFalse(password.startswith("-"))

    def test_random_secret_is_still_present(self):
        with patch.object(runner.secrets, "token_urlsafe", return_value="abC_123"):
            self.assertEqual(runner.qa_cli_password(), "qa_abC_123")



class TestEvenniaReplayCleanup(unittest.TestCase):
    def test_cleanup_failure_keeps_original_player_failure(self):
        output = io.StringIO()
        with patch.object(runner, "run", side_effect=RuntimeError("stop failed")) as stop:
            with redirect_stderr(output):
                with self.assertRaisesRegex(ValueError, "player assertion failed"):
                    try:
                        raise ValueError("player assertion failed")
                    finally:
                        runner.stop_evennia_after_phase(
                            Path("evennia"), game=Path("game"), env={},
                            phase_failed=sys.exc_info()[0] is not None,
                        )
        stop.assert_called_once()
        self.assertIn("stop failed", output.getvalue())
        self.assertIn("original gameplay failure retained", output.getvalue())

    def test_cleanup_failure_alone_is_not_silently_accepted(self):
        with patch.object(runner, "run", side_effect=RuntimeError("stop failed")):
            with self.assertRaisesRegex(RuntimeError, "stop failed"):
                runner.stop_evennia_after_phase(
                    Path("evennia"), game=Path("game"), env={},
                    phase_failed=False,
                )

    def test_successful_stop_keeps_successful_phase_green(self):
        with patch.object(runner, "run", return_value=None) as stop:
            runner.stop_evennia_after_phase(
                Path("evennia"), game=Path("game"), env={},
                phase_failed=False,
            )
        stop.assert_called_once()

    def test_all_three_migrated_replay_phases_preserve_original_failure(self):
        # Include the pre-restart normal-client phase as well as after/release.
        # A second stop error must not replace the first gameplay exception.
        source = RUNNER.read_text(encoding="utf-8")
        replay = source.split("            # After the hostile decoy is seeded", 1)[1]
        replay = replay.split("            migrated_post_client_proof =", 1)[0]
        self.assertEqual(replay.count("stop_evennia_after_phase("), 3)
        self.assertEqual(replay.count("phase_failed=sys.exc_info()[0] is not None"), 3)
        self.assertNotIn('run([evennia, "stop"]', replay)

    def test_pre_restart_failure_and_stop_failure_keep_player_exception(self):
        # Exercise the exact finally expression used by the before phase.
        with patch.object(runner, "run", side_effect=RuntimeError("stop failed")):
            with redirect_stderr(io.StringIO()):
                with self.assertRaisesRegex(ValueError, "before-phase player failure"):
                    try:
                        raise ValueError("before-phase player failure")
                    finally:
                        runner.stop_evennia_after_phase(
                            Path("evennia"), game=Path("game"), env={},
                            phase_failed=sys.exc_info()[0] is not None,
                        )


if __name__ == "__main__":
    unittest.main()
