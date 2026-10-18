#!/usr/bin/env python3
"""Operator-run repeated concurrent AI player burn-in, never release approval.

Repeated short authenticated connections are NOT equivalent to continuously
connected players or a hosted 24-hour soak. The same public player interface,
consent gates and TLS rules as the normal headless client are used. Never run
with actual player or staff credentials, or on live production without an
authorized load-test window.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
import math
from pathlib import Path
import time

from headless_ai_client import is_loopback, load_accounts, run_sessions


def finite_ms(value):
    if isinstance(value, bool) or not isinstance(value, (float, int)):
        return None
    amount = float(value)
    if not math.isfinite(amount) or amount < 0:
        return None
    return amount


def record_cycle(results, expected):
    """Never treat a partial or malformed account result as a successful run."""
    if not isinstance(results, list) or len(results) != expected:
        raise ValueError("Concurrent cycle returned an incomplete account set")
    good, commands, p95, worst, reconnect = 0, 0, [], [], 0
    for result in results:
        if not isinstance(result, dict):
            continue
        count = result.get("commands")
        latency = finite_ms(result.get("latency_ms_p95"))
        maximum = finite_ms(result.get("latency_ms_max"))
        success = (
            result.get("connect_success") is True
            and result.get("error") is None
            and type(count) is int and count > 0
            and latency is not None and maximum is not None
        )
        if success:
            good += 1
        commands += count if type(count) is int and count >= 0 else 0
        if latency is not None:
            p95.append(latency)
        if maximum is not None:
            worst.append(maximum)
        if result.get("relogin_recovered") is True:
            reconnect += 1
    return {
        "attempts": expected, "successful_sessions": good,
        "commands": commands,
        "highest_session_p95_ms": max(p95) if p95 else None,
        "highest_command_latency_ms": max(worst) if worst else None,
        "reconnects_verified": reconnect,
    }


def aggregate(rounds, elapsed_s, *,
              required_duration_s=1800, min_rounds=3,
              max_error_rate=0.01, max_session_p95_ms=3500):
    if not rounds or elapsed_s < 0:
        raise ValueError("A measurable concurrent session run is required")
    attempts = sum(row["attempts"] for row in rounds)
    successes = sum(row["successful_sessions"] for row in rounds)
    values = [
        row["highest_session_p95_ms"] for row in rounds
        if row["highest_session_p95_ms"] is not None
    ]
    highs = [
        row["highest_command_latency_ms"] for row in rounds
        if row["highest_command_latency_ms"] is not None
    ]
    failure_rate = (attempts - successes) / attempts if attempts else 1.0
    max_p95 = max(values) if values else None
    min_duration_met = elapsed_s >= required_duration_s
    thresholds_met = (
        min_duration_met and len(rounds) >= min_rounds
        and attempts > 0 and max_p95 is not None
        and failure_rate <= max_error_rate
        and max_p95 <= max_session_p95_ms
    )
    return {
        "schema": "fvillage.repeated_sessions_burnin.v1",
        "kind": "REPEATED_SHORT_CONNECTIONS_NOT_CONTINUOUS_SOAK",
        "duration_seconds_observed": round(elapsed_s, 2),
        "minimum_duration_met": min_duration_met,
        "rounds": len(rounds),
        "session_attempts": attempts,
        "successful_sessions": successes,
        "failed_sessions": attempts - successes,
        "failure_rate": round(failure_rate, 5),
        "command_total": sum(row["commands"] for row in rounds),
        "worst_session_p95_ms": max_p95,
        "worst_command_latency_ms": max(highs) if highs else None,
        "reconnects_verified": sum(row["reconnects_verified"] for row in rounds),
        "technical_thresholds_met": thresholds_met,
        "public_launch_certified": False,
        "qualification": (
            "Needs continuous-connection soak, outside-network tests, "
            "host restart, encrypted off-host restore and independent "
            "human/AI return-play evidence."
        ),
    }


def repeated_cycles(*, duration_s, interval_s, accounts_count,
                    round_fn, clock=time.monotonic, sleeper=time.sleep):
    if duration_s <= 0 or interval_s <= 0 or not 1 <= accounts_count <= 32:
        raise ValueError("Positive duration/interval and 1..32 accounts required")
    started = clock()
    rounds = []
    while True:
        # No exception text, credentials, transcripts or individual character
        # names are copied into an operator-shareable burn-in measurement.
        try:
            results = round_fn(len(rounds))
            measurement = record_cycle(results, accounts_count)
        except Exception:
            measurement = {
                "attempts": accounts_count, "successful_sessions": 0,
                "commands": 0, "highest_session_p95_ms": None,
                "highest_command_latency_ms": None, "reconnects_verified": 0,
            }
        rounds.append(measurement)
        remaining = duration_s - (clock() - started)
        if remaining <= 0:
            break
        sleeper(min(interval_s, remaining))
    return rounds, max(0, clock() - started)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=4000)
    parser.add_argument("--tls", action="store_true")
    parser.add_argument("--accounts", type=Path, required=True)
    parser.add_argument("--sessions", type=int, default=2)
    parser.add_argument("--minutes", type=float, default=30)
    parser.add_argument("--interval-seconds", type=float, default=10)
    parser.add_argument("--steps", type=int, default=3)
    parser.add_argument("--seed", type=int, default=1017)
    parser.add_argument("--timeout", type=float, default=8.0)
    parser.add_argument("--max-error-rate", type=float, default=0.01)
    parser.add_argument("--max-p95-ms", type=float, default=3500)
    parser.add_argument("--test-one-disconnect", action="store_true")
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args(argv)
    if not 1 <= args.sessions <= 32 or not 1 <= args.minutes <= 180:
        parser.error("1..32 sessions, duration 1..180 minutes required")
    if not 1 <= args.interval_seconds <= 120 or not 0 <= args.steps <= 30:
        parser.error("Interval 1..120s and steps 0..30 required")
    if not 0 < args.timeout <= 30 or not 1 <= args.port <= 65535:
        parser.error("Invalid timeout or port")
    if (not 0 <= args.max_error_rate <= 1 or
            not 100 <= args.max_p95_ms <= 60000):
        parser.error("Invalid load-test thresholds")
    if not args.tls and not is_loopback(args.host):
        parser.error("Remote player credentials require verified TLS")
    accounts = load_accounts(args.accounts, args.sessions)

    def perform(index):
        return run_sessions(
            accounts, host=args.host, port=args.port,
            tls=args.tls, timeout=args.timeout,
            seed=args.seed + index * 101, steps=args.steps,
            recover_index=0 if args.test_one_disconnect and index == 0 else None,
        )

    wall_started = datetime.now(timezone.utc).isoformat()
    rows, elapsed = repeated_cycles(
        duration_s=args.minutes * 60,
        interval_s=args.interval_seconds,
        accounts_count=args.sessions, round_fn=perform,
    )
    summary = aggregate(
        rows, elapsed, max_error_rate=args.max_error_rate,
        max_session_p95_ms=args.max_p95_ms,
    )
    summary["started_utc"] = wall_started
    summary["finished_utc"] = datetime.now(timezone.utc).isoformat()
    summary["transport"] = "TLS" if args.tls else "loopback_telnet"
    summary["concurrent_sessions_per_round"] = args.sessions
    output = args.output
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(summary, indent=2))
    return 0 if summary["technical_thresholds_met"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
