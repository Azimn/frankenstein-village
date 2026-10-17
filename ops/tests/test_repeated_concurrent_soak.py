"""Deterministic no-host tests for repeated concurrent session burn-in."""
import math
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "ops"))
import repeated_concurrent_soak as soak


def player(ok=True, p95=120, latency=180):
    return {
        "connect_success": ok, "error": None if ok else "ConnectionError",
        "commands": 12 if ok else 0,
        "latency_ms_p95": p95 if ok else None,
        "latency_ms_max": latency if ok else None,
        "relogin_recovered": True if ok else False,
        "account": "should_not_leak_username",
        "quotable": "should_not_leak_private_scene",
    }


class Clock:
    def __init__(self):
        self.now = 0
        self.calls = []
    def monotonic(self):
        return self.now
    def sleep(self, seconds):
        self.calls.append(seconds)
        self.now += seconds


class SoakTests(unittest.TestCase):
    def test_normal_run_is_measured_but_never_certifies_a_public_host(self):
        clock = Clock()
        recorded_indexes = []
        def runner(index):
            recorded_indexes.append(index)
            return [player(), player()]
        rounds, elapsed = soak.repeated_cycles(
            duration_s=12, interval_s=5, accounts_count=2,
            round_fn=runner, clock=clock.monotonic, sleeper=clock.sleep,
        )
        self.assertEqual(recorded_indexes, [0, 1, 2, 3])
        self.assertEqual(elapsed, 12)
        report = soak.aggregate(
            rounds, elapsed, required_duration_s=10, min_rounds=3,
            max_error_rate=0.01, max_session_p95_ms=300,
        )
        self.assertTrue(report["technical_thresholds_met"])
        self.assertFalse(report["public_launch_certified"])
        self.assertEqual(report["rounds"], 4)
        self.assertEqual(report["successful_sessions"], 8)
        self.assertEqual(report["command_total"], 96)
        self.assertEqual(report["worst_session_p95_ms"], 120)
        self.assertEqual(report["reconnects_verified"], 8)
        self.assertNotIn("should_not_leak", repr(report))
        self.assertEqual(report["kind"],
                         "REPEATED_SHORT_CONNECTIONS_NOT_CONTINUOUS_SOAK")

    def test_failures_and_partial_metrics_are_fail_closed(self):
        row = soak.record_cycle([player(), player(ok=False)], 2)
        report = soak.aggregate(
            [row], 2000, required_duration_s=1800, min_rounds=1,
            max_error_rate=0.01,
        )
        self.assertEqual(report["failed_sessions"], 1)
        self.assertFalse(report["technical_thresholds_met"])
        with self.assertRaises(ValueError):
            soak.record_cycle([player()], 2)
        bad = soak.record_cycle([player(p95=float("nan"))], 1)
        self.assertEqual(bad["successful_sessions"], 0)
        self.assertIsNone(bad["highest_session_p95_ms"])
        self.assertIsNone(soak.finite_ms(True))
        self.assertIsNone(soak.finite_ms(-4))
        self.assertIsNone(soak.finite_ms(math.inf))

    def test_runner_exception_cannot_hide_load_failures(self):
        clock = Clock()
        def broken(index):
            if index == 1:
                raise RuntimeError("secret private login string")
            return [player(), player()]
        rounds, elapsed = soak.repeated_cycles(
            duration_s=7, interval_s=5, accounts_count=2,
            round_fn=broken, clock=clock.monotonic, sleeper=clock.sleep,
        )
        self.assertEqual(elapsed, 7)
        self.assertEqual(len(rounds), 3)
        self.assertEqual(rounds[1]["successful_sessions"], 0)
        report = soak.aggregate(
            rounds, elapsed, required_duration_s=1,
            min_rounds=1, max_error_rate=0,
        )
        self.assertEqual(report["failed_sessions"], 2)
        self.assertFalse(report["technical_thresholds_met"])
        self.assertNotIn("secret", repr(report))

    def test_short_successful_probe_not_a_thirty_minute_burnin(self):
        report = soak.aggregate(
            [soak.record_cycle([player()], 1)] * 5, 40,
        )
        self.assertFalse(report["minimum_duration_met"])
        self.assertFalse(report["technical_thresholds_met"])
        self.assertFalse(report["public_launch_certified"])
        with self.assertRaises(ValueError):
            soak.repeated_cycles(
                duration_s=0, interval_s=5, accounts_count=2,
                round_fn=lambda _: [player(), player()],
            )
        with self.assertRaises(ValueError):
            soak.aggregate([], 0)


if __name__ == "__main__":
    unittest.main()
