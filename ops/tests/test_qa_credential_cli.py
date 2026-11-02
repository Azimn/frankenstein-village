"""Prevent intermittent CLI failures from option-looking random QA passwords."""
from __future__ import annotations

import importlib.util
import io
import sys
import unittest
from contextlib import redirect_stderr, redirect_stdout
import subprocess
from pathlib import Path
from unittest.mock import patch
import socket
import threading
import time


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

    def test_timeout_preserves_partial_authenticated_client_transcript(self):
        failure = subprocess.TimeoutExpired(
            cmd=["client"], timeout=1, output=b"CLIENT_PROGRESS_BEFORE_TIMEOUT\n"
        )
        output, errors = io.StringIO(), io.StringIO()
        with patch.object(runner.subprocess, "run", side_effect=failure):
            with redirect_stdout(output), redirect_stderr(errors):
                with self.assertRaises(subprocess.TimeoutExpired):
                    runner.run(["client"], cwd=Path("."), env={}, timeout=1)
        self.assertIn("CLIENT_PROGRESS_BEFORE_TIMEOUT", output.getvalue())
        self.assertIn("exceeded 1s", errors.getvalue())



class TestTelnetReadQuiet(unittest.TestCase):
    def test_ansi_only_chunk_does_not_end_wait_before_actual_reply(self):
        """A negotiation/formatting chunk must not masquerade as command output."""
        path = Path(__file__).resolve().parents[2] / "spike/tests/telnet_playthrough.py"
        telnet_spec = importlib.util.spec_from_file_location("fv_telnet_client", path)
        telnet = importlib.util.module_from_spec(telnet_spec)
        telnet_spec.loader.exec_module(telnet)
        client_sock, server_sock = socket.socketpair()
        client_sock.settimeout(0.05)
        client = telnet.Client.__new__(telnet.Client)
        client.sock = client_sock
        client.transcript = []

        def deliver():
            server_sock.sendall(b"\x1b[0m")
            time.sleep(0.38)
            server_sock.sendall(b"Accusation is now public\n")

        thread = threading.Thread(target=deliver, daemon=True)
        thread.start()
        try:
            response = client.read_quiet(max_wait=1.2, quiet=0.18)
            self.assertIn("Accusation is now public", response)
        finally:
            thread.join(timeout=1)
            client_sock.close()
            server_sock.close()


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

    def test_all_nine_actual_restart_phases_preserve_original_failure(self):
        # Verify the current main runner, not a removed candidate-only replay.
        # All nine real finally blocks must retain the player exception.
        source = RUNNER.read_text(encoding="utf-8")
        self.assertEqual(source.count("stop_evennia_after_phase("), 10)
        self.assertEqual(source.count("phase_failed=sys.exc_info()[0] is not None"), 9)
        self.assertNotIn('finally:\n                run([evennia, "stop"]', source)

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
