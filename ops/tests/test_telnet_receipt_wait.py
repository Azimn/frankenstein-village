"""Regression contract: do not replay side-effecting telnet commands on slow replies.

This tests the real player-client framing helper in isolation. Authenticated
Evennia gameplay and restart persistence remain separate release gates.
"""
import importlib.util
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[2]
DRIVER = ROOT / "spike" / "tests" / "telnet_playthrough.py"
spec = importlib.util.spec_from_file_location("fv_telnet_receipt_driver", DRIVER)
driver = importlib.util.module_from_spec(spec)
spec.loader.exec_module(driver)


class RecordingSocket:
    def __init__(self):
        self.sent = []

    def sendall(self, payload):
        self.sent.append(payload)


class ReceiptWaitTests(unittest.TestCase):
    def client(self, responses):
        client = driver.Client.__new__(driver.Client)
        client.sock = RecordingSocket()
        client.transcript = []
        remaining = iter(responses)

        def read_quiet(*, max_wait):
            self.assertGreater(max_wait, 0)
            return next(remaining, "")
        client.read_quiet = read_quiet
        return client

    def test_delayed_receipt_sends_only_one_care_action(self):
        client = self.client([
            "", "HealerTester enters the Tavern.",
            "You serve Silas a hot bowl from the tavern stock; care is complete.",
        ])
        result = client.command_expect(
            "care serve Silas Crowe", "hot bowl from the tavern stock", wait=0.5
        )
        self.assertIn("hot bowl from the tavern stock", result)
        self.assertEqual(client.sock.sent, [b"care serve Silas Crowe\n"])
        self.assertIn("HealerTester enters", result)

    def test_silence_is_not_a_receipt_or_permission_to_retry(self):
        client = self.client([])
        result = client.command_expect(
            "care serve Silas Crowe", "hot bowl from the tavern stock", wait=0.002
        )
        self.assertEqual(result, "")
        self.assertEqual(client.sock.sent, [b"care serve Silas Crowe\n"])


if __name__ == "__main__":
    unittest.main()
