"""Concurrent held-session soak tests without external players or server."""
from __future__ import annotations

import json
from pathlib import Path
import sys
import threading
import time
import unittest
from types import SimpleNamespace

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "ops"))
from headless_ai_client import Account
import continuous_player_soak as soak


class StubPlayer:
    sessions = []
    lock = threading.Lock()
    def __init__(self, account, *, host, port, tls, timeout, seed, steps):
        self.account = account
        self.commands = 0
        self.lags = []
        self.closed = False
        self.command_log = []
        self.session = SimpleNamespace(close=self.close)
        with self.lock:
            self.sessions.append(self)
    def login(self):
        self.commands += 1
        self.lags.append(10)
        return {"side": "ic", "location": "The Blood of the Vine"}
    def arrive(self, state):
        return state
    def cmd(self, command):
        self.command_log.append(command)
        self.commands += 1
        self.lags.append(12)
        if command == "agent":
            return "FV_AGENT_JSON " + json.dumps({
                "version": 1, "schema": "fvillage.agent_context.v1",
                "side": "ic", "location": "The Blood of the Vine",
                "exits": ["west"],
            })
        return "The village continues to live around you."
    def close(self):
        self.closed = True


class CrashPlayer(StubPlayer):
    def cmd(self, command):
        if command == "look":
            raise ConnectionResetError("password SECRET123")
        return super().cmd(command)


def account(name):
    return Account(name, "Mask_" + name, "not_exported_password")


class ContinuousSoakTests(unittest.TestCase):
    def setUp(self):
        StubPlayer.sessions = []

    def test_held_connections_overlap_without_reconnect_or_secrets(self):
        names = [account("smith_bot"), account("healer_bot")]
        start = time.monotonic()
        rows = soak.run_concurrent(
            names, host="127.0.0.1", port=4000, tls=False,
            timeout=1, duration_s=.12, interval_s=.015,
            player_factory=StubPlayer,
        )
        elapsed = time.monotonic() - start
        self.assertEqual(len(rows), 2)
        self.assertLess(elapsed, .32, "Threads were not truly simultaneous")
        self.assertTrue(all(p.closed for p in StubPlayer.sessions))
        self.assertEqual(len(StubPlayer.sessions), 2, "An account reconnected")
        self.assertTrue(all(row["connected_for_window"] for row in rows))
        self.assertTrue(all(row["held_seconds"] >= .12 for row in rows))
        self.assertTrue(all(row["read_only_samples"] >= 2 for row in rows))
        self.assertTrue(all(set(p.command_log).issubset(soak.READ_ONLY_ACTIONS)
                            for p in StubPlayer.sessions))
        report = soak.summarize(rows, duration_s=.12, smoke_mode=True)
        self.assertTrue(report["passed_short_smoke"])
        self.assertFalse(report["technical_thresholds_met"])
        self.assertFalse(report["public_launch_certified"])
        self.assertNotIn("not_exported_password", repr(report))
        self.assertNotIn("smith_bot", repr(report))

    def test_disconnection_is_not_hidden_by_automatic_relogin(self):
        rows = soak.run_concurrent(
            [account("one_bot"), account("two_bot")],
            host="127.0.0.1", port=4000, tls=False,
            timeout=1, duration_s=.09, interval_s=.01,
            player_factory=CrashPlayer,
        )
        self.assertEqual(len(StubPlayer.sessions), 2)
        report = soak.summarize(rows, duration_s=.09, smoke_mode=True)
        self.assertFalse(report["passed_short_smoke"])
        self.assertEqual(report["sessions_failed"], 2)
        self.assertEqual(report["lost_connections"], 2)
        self.assertNotIn("SECRET123", repr(rows) + repr(report))
        self.assertTrue(all(p.closed for p in StubPlayer.sessions))

    def test_technical_duration_requires_actual_held_time_and_two_accounts(self):
        good = {
            "connected_for_window": True, "error_type": None,
            "held_seconds": 1800.05, "read_only_samples": 22,
            "in_window_commands": 23, "p95_ms": 42,
            "maximum_command_ms": 88, "unexpected_disconnect": False,
        }
        report = soak.summarize([good, good], duration_s=1800)
        self.assertTrue(report["technical_thresholds_met"])
        self.assertFalse(report["public_launch_certified"])
        self.assertFalse(soak.summarize([good], duration_s=1800)[
            "technical_thresholds_met"
        ])
        self.assertFalse(soak.summarize([good, good], duration_s=5)[
            "technical_thresholds_met"
        ])
        insufficient = dict(good, held_seconds=1799)
        self.assertFalse(soak.summarize([good, insufficient], duration_s=1800)[
            "technical_thresholds_met"
        ])
        slow = dict(good, p95_ms=9000)
        self.assertFalse(soak.summarize([good, slow], duration_s=1800)[
            "technical_thresholds_met"
        ])

    def test_malformed_metrics_fail_closed(self):
        self.assertIsNone(soak._finite_ms(float("nan")))
        self.assertIsNone(soak._finite_ms(float("inf")))
        self.assertIsNone(soak._finite_ms(True))
        self.assertIsNone(soak._finite_ms(-1))
        broken = {
            "connected_for_window": True, "error_type": None,
            "held_seconds": 1800, "read_only_samples": 20,
            "in_window_commands": 21, "p95_ms": float("nan"),
            "maximum_command_ms": None,
        }
        result = soak.summarize([broken, broken], duration_s=1800)
        self.assertEqual(result["sessions_passed"], 0)
        self.assertFalse(result["technical_thresholds_met"])
        with self.assertRaises(ValueError):
            soak.summarize([], duration_s=1800)
        with self.assertRaises(ValueError):
            soak.run_concurrent(
                [account("same_bot"), account("same_bot")],
                host="localhost", port=4000, tls=False, timeout=1,
                duration_s=.1, interval_s=.02, player_factory=StubPlayer,
            )
        with self.assertRaises(ValueError):
            soak.run_concurrent(
                [account("bot_1"), account("bot_2")],
                host="some-remote-server.example", port=4000, tls=False,
                timeout=1, duration_s=.1, interval_s=.02,
                player_factory=StubPlayer,
            )


if __name__ == "__main__":
    unittest.main()
