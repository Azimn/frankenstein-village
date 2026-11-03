"""B17/B19 socket-level regressions for unsolicited Evennia telnet output.

Pure stdlib tests: no server, account, model or network dependency.  They
exercise the real production regression client without changing game rules.
"""
from __future__ import annotations

from contextlib import redirect_stdout
import importlib.util
import io
from pathlib import Path
import socket
import threading
import time
import unittest


MODULE_PATH = Path(__file__).resolve().parents[2] / "spike" / "tests" / "telnet_playthrough.py"
SPEC = importlib.util.spec_from_file_location("fv_telnet_playthrough", MODULE_PATH)
telnet = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(telnet)


class TelnetReplyFramingTests(unittest.TestCase):
    def setUp(self):
        self.client_sock, self.server_sock = socket.socketpair()
        self.client_sock.settimeout(0.015)
        self.server_sock.settimeout(0.5)
        self.client = telnet.Client.__new__(telnet.Client)
        self.client.sock = self.client_sock
        self.client.transcript = []

    def tearDown(self):
        self.client_sock.close()
        self.server_sock.close()

    def send_later(self, segments):
        def send():
            for delay, data in segments:
                time.sleep(delay)
                try:
                    self.server_sock.sendall(data)
                except OSError:
                    return
        thread = threading.Thread(target=send, daemon=True)
        thread.start()
        return thread

    def test_unsolicited_invite_does_not_complete_decline(self):
        thread = self.send_later([
            (0.01, b"SmokeTester challenges you to dice. (roll dice answer / roll dice decline)\r\n"),
            (0.12, b"You push the cup back. Another night, perhaps.\r\n"),
        ])
        with redirect_stdout(io.StringIO()) as output:
            result = self.client.read_quiet(
                max_wait=0.55, quiet=0.04,
                expected=("pushes the cup back", "another night"),
            )
        thread.join(0.4)
        self.assertIn("Another night", result)
        self.assertIn("challenges you", result)
        self.assertIn("matched=True", output.getvalue())

    def test_split_negotiation_ansi_and_delayed_market_description(self):
        thread = self.send_later([
            (0.01, b"\xff\xfd\x01\x1b[31m"),
            (0.08, b"Someone enters Market Lane.\r\n"),
            (0.11, b"The crooked scale has brass pans and two prices.\r\n"),
        ])
        with redirect_stdout(io.StringIO()):
            result = self.client.read_quiet(
                max_wait=0.55, quiet=0.04, expected=("two prices",),
            )
        thread.join(0.4)
        self.assertIn("two prices", result)
        self.assertNotIn("\x1b[31m", result)

    def test_missing_expected_reply_exhausts_original_deadline(self):
        thread = self.send_later([(0.01, b"Someone else arrives.\r\n")])
        started = time.monotonic()
        with redirect_stdout(io.StringIO()) as output:
            result = self.client.read_quiet(
                max_wait=0.18, quiet=0.03, expected=("two prices",),
            )
        elapsed = time.monotonic() - started
        thread.join(0.3)
        self.assertGreaterEqual(elapsed, 0.16)
        self.assertIn("Someone else arrives", result)
        self.assertIn("matched=False", output.getvalue())

    def test_silent_server_does_not_fabricate_response(self):
        started = time.monotonic()
        with redirect_stdout(io.StringIO()) as output:
            result = self.client.read_quiet(
                max_wait=0.13, quiet=0.03, expected=("another night",),
            )
        self.assertEqual(result, "")
        self.assertGreaterEqual(time.monotonic() - started, 0.11)
        self.assertIn("raw_bytes=0", output.getvalue())

    def test_connect_credentials_are_sent_once_but_never_logged(self):
        with redirect_stdout(io.StringIO()) as output:
            self.client.command("connect qa_test secret_password", wait=0.08)
        self.assertEqual(self.server_sock.recv(4096), b"connect qa_test secret_password\n")
        self.assertIn("credentials redacted", output.getvalue())
        self.assertNotIn("secret_password", output.getvalue())


if __name__ == "__main__":
    unittest.main()
