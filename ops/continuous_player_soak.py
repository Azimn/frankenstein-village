#!/usr/bin/env python3
"""Hold multiple ordinary Evennia character sessions open while measuring gameplay.

Unlike repeated_concurrent_soak.py, each authenticated TCP connection remains
open for the entire observation window. This is an operator-run instrument,
NOT an executed production soak, proof of server capacity, or launch approval.
Never use real player or administrator accounts.
"""
from __future__ import annotations

import argparse
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
import json
import math
from pathlib import Path
from threading import Barrier
import time

from headless_ai_client import (
    Player, context_of, is_loopback, load_accounts, process_delta,
    process_sample,
)

READ_ONLY_ACTIONS = (
    "agent", "look", "calendar", "survey", "journal discoveries", "guide",
)


def _finite_ms(value):
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return None
    value = float(value)
    return value if math.isfinite(value) and value >= 0 else None


def hold_player(player, barrier, *, duration_s, interval_s,
                clock=time.monotonic, sleeper=time.sleep):
    """Run read-only ordinary commands on ONE continuously open connection.

    The barrier ensures that all clients finish authentication before the
    timed observation begins. No automatic reconnect can silently conceal
    lost connections or turn this into a repeated-session load test.
    """
    registered = False
    started = None
    samples = 0
    error = None
    initial_commands = 0
    initial_lag_count = 0
    try:
        state = player.arrive(player.login())
        if state.get("side") != "ic":
            raise RuntimeError("Account did not enter the game world")
        initial_commands = player.commands
        initial_lag_count = len(player.lags)
        barrier.wait(timeout=90)
        registered = True
        started = clock()
        deadline = started + duration_s
        while clock() < deadline:
            verb = READ_ONLY_ACTIONS[samples % len(READ_ONLY_ACTIONS)]
            response = player.cmd(verb)
            if not isinstance(response, str) or not response.strip():
                raise RuntimeError("Empty game command response")
            if verb == "agent":
                envelope = context_of(response, "fvillage.agent_context.v1")
                if envelope.get("side") != "ic":
                    raise RuntimeError("Agent left the in-character world")
            samples += 1
            remaining = deadline - clock()
            if remaining > 0:
                sleeper(min(interval_s, remaining))
        # Require a final real response after the elapsed connection window.
        last = context_of(player.cmd("agent"), "fvillage.agent_context.v1")
        if last.get("side") != "ic":
            raise RuntimeError("Player no longer has an in-character mask")
    except Exception as exc:
        error = type(exc).__name__  # NEVER copy a credential-bearing message
        if not registered:
            try:
                barrier.abort()
            except Exception:
                pass
    finally:
        held_s = max(0, clock() - started) if started is not None else 0
        if getattr(player, "session", None) is not None:
            try:
                player.session.close()
            except Exception:
                error = error or "SessionCloseError"
        latencies = sorted(
            x for x in (
                _finite_ms(x) for x in player.lags[initial_lag_count:]
            ) if x is not None
        )
        idx = min(len(latencies) - 1, math.ceil(len(latencies) * .95) - 1)
    return {
        "connected_for_window": registered,
        "held_seconds": round(held_s, 3),
        "read_only_samples": samples,
        "in_window_commands": player.commands - initial_commands,
        "p95_ms": latencies[idx] if latencies else None,
        "maximum_command_ms": latencies[-1] if latencies else None,
        "error_type": error,
        "unexpected_disconnect": error is not None and registered,
    }


def run_concurrent(accounts, *, host, port, tls, timeout, duration_s,
                   interval_s, player_factory=Player):
    if not accounts or len(accounts) > 32:
        raise ValueError("Between 1 and 32 test accounts required")
    if len({a.username for a in accounts}) != len(accounts):
        raise ValueError("Concurrent players require distinct accounts")
    if not tls and not is_loopback(host):
        raise ValueError("External game endpoints require validated TLS")
    gate = Barrier(len(accounts))
    with ThreadPoolExecutor(max_workers=len(accounts)) as pool:
        jobs = [
            pool.submit(
                hold_player,
                player_factory(
                    account, host=host, port=port, tls=tls, timeout=timeout,
                    seed=173 + index, steps=0,
                ),
                gate, duration_s=duration_s, interval_s=interval_s,
            )
            for index, account in enumerate(accounts)
        ]
        return [future.result() for future in jobs]


def summarize(results, *, duration_s, max_p95_ms=3500,
              smoke_mode=False, resource_metrics=None):
    """Fail closed for incomplete, disconnected, short or slow held sessions."""
    if not isinstance(results, list) or not results:
        raise ValueError("No continuous-player observations available")
    valid = all(isinstance(result, dict) for result in results)
    if not valid:
        raise ValueError("Malformed session data")
    complete = [
        bool(
            item.get("connected_for_window") is True
            and item.get("error_type") is None
            and type(item.get("read_only_samples")) is int
            and item["read_only_samples"] >= 2
            and type(item.get("in_window_commands")) is int
            and item["in_window_commands"] >= 3
            and _finite_ms(item.get("p95_ms")) is not None
            and item["p95_ms"] <= max_p95_ms
            and _finite_ms(item.get("held_seconds")) is not None
            and item["held_seconds"] >= duration_s
        )
        for item in results
    ]
    longest = max(
        (_finite_ms(row.get("maximum_command_ms")) or 0 for row in results),
        default=0,
    )
    p95s = [value for row in results
            if (value := _finite_ms(row.get("p95_ms"))) is not None]
    all_held = all(complete)
    technical = (
        all_held and len(results) >= 2 and duration_s >= 1800
        and not smoke_mode
    )
    return {
        "schema": "fvillage.continuous_player_soak.v1",
        "kind": "REAL_CONCURRENT_HELD_CONNECTIONS_NOT_HOST_CERTIFICATION",
        "sessions_attempted": len(results),
        "sessions_passed": sum(complete),
        "sessions_failed": len(results) - sum(complete),
        "uninterrupted_window_seconds_required": duration_s,
        "shortest_held_seconds": min(
            _finite_ms(row.get("held_seconds")) or 0 for row in results
        ),
        "total_read_only_samples": sum(
            row.get("read_only_samples", 0)
            for row in results if type(row.get("read_only_samples")) is int
        ),
        "worst_session_p95_ms": max(p95s) if p95s else None,
        "maximum_command_ms": longest,
        "lost_connections": sum(bool(row.get("unexpected_disconnect"))
                                for row in results),
        "passed_short_smoke": all_held,
        "technical_thresholds_met": technical,
        "public_launch_certified": False,
        "resource_metrics": resource_metrics,
        "qualification": (
            "Real selected-host soak, external TLS/WSS, event tick latency, "
            "off-host encrypted recovery, moderation and uncoached return "
            "play remain separately necessary."
        ),
    }


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=4000)
    parser.add_argument("--tls", action="store_true")
    parser.add_argument("--accounts", type=Path, required=True)
    parser.add_argument("--sessions", type=int, default=2)
    parser.add_argument("--minutes", type=float, default=30)
    parser.add_argument("--smoke-seconds", type=int, default=None,
                        help="5..60s short regression; never passes 30m gate")
    parser.add_argument("--interval-seconds", type=float, default=5)
    parser.add_argument("--timeout", type=float, default=8)
    parser.add_argument("--max-p95-ms", type=float, default=3500)
    parser.add_argument("--server-pid", type=int, action="append", default=[])
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args(argv)
    if not 2 <= args.sessions <= 32 or not 1 <= args.minutes <= 180:
        parser.error("2..32 sessions and 1..180 minute duration required")
    if args.smoke_seconds is not None and not 5 <= args.smoke_seconds <= 60:
        parser.error("Short CI probe must run 5..60 seconds")
    if not 1 <= args.interval_seconds <= 30:
        parser.error("Read-only poll interval must be 1..30 seconds")
    if not 0 < args.timeout <= 30 or not 1 <= args.port <= 65535:
        parser.error("Invalid endpoint or session timeout")
    if not 100 <= args.max_p95_ms <= 60000:
        parser.error("Maximum p95 limit must be 100..60000 ms")
    if any(pid <= 0 for pid in args.server_pid):
        parser.error("Server process identifiers must be positive")
    if not args.tls and not is_loopback(args.host):
        parser.error("External player sessions require certificate-verified TLS")
    accounts = load_accounts(args.accounts, args.sessions)
    duration = args.smoke_seconds if args.smoke_seconds is not None else args.minutes * 60
    before = process_sample(args.server_pid)
    started_utc = datetime.now(timezone.utc).isoformat()
    results = run_concurrent(
        accounts, host=args.host, port=args.port, tls=args.tls,
        timeout=args.timeout, duration_s=duration,
        interval_s=args.interval_seconds,
    )
    resource = process_delta(before, process_sample(args.server_pid))
    report = summarize(
        results, duration_s=duration, max_p95_ms=args.max_p95_ms,
        smoke_mode=args.smoke_seconds is not None, resource_metrics=resource,
    )
    report["started_utc"] = started_utc
    report["finished_utc"] = datetime.now(timezone.utc).isoformat()
    report["transport"] = "TLS" if args.tls else "loopback_telnet"
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2))
    return 0 if (report["passed_short_smoke"]
                 if args.smoke_seconds is not None
                 else report["technical_thresholds_met"]) else 1


if __name__ == "__main__":
    raise SystemExit(main())
