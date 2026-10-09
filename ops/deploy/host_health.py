#!/usr/bin/env python3
"""Read-only host health probe for the invited-alpha operator.

No account login, game mutations or privileged in-world endpoints. Designed
for cron/systemd watchdog use. JSON output, exit 2 on failed required checks.
Backups are checked for FRESHNESS only; off-host receipt is a separate gate.
"""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import shutil
import socket
import time


def probe_port(host: str, port: int, timeout: float = 1.5) -> bool:
    try:
        with socket.create_connection((host, port), timeout=timeout):
            return True
    except OSError:
        return False


def check(
    database: Path, backup_receipt: Path, *,
    port_checks: tuple[tuple[str, int], ...] = (
        ("127.0.0.1", 4000),
        ("127.0.0.1", 4001),
        ("127.0.0.1", 4002),
    ),
    max_backup_age_hours: float = 26,
    min_free_gib: float = 2,
    now: float | None = None,
) -> dict:
    now = time.time() if now is None else now
    results = {}
    db = Path(database)
    if db.is_file():
        results["sqlite_file"] = {
            "ok": True, "bytes": db.stat().st_size,
        }
    else:
        results["sqlite_file"] = {"ok": False, "reason": "Missing DB path"}

    for host, port in port_checks:
        if not (host in {"127.0.0.1", "::1", "localhost"}):
            raise ValueError("Host health must probe loopback listeners only")
        if not 1 <= port <= 65535:
            raise ValueError("Invalid port")
        results[f"loopback_{port}"] = {"ok": probe_port(host, port)}

    receipt = Path(backup_receipt)
    if receipt.is_file():
        age = (now - receipt.stat().st_mtime) / 3600
        results["backup_receipt"] = {
            "ok": 0 <= age <= max_backup_age_hours,
            "age_hours": round(age, 2),
            "caution": "Age only: off-host integrity requires a separate drill",
        }
    else:
        results["backup_receipt"] = {
            "ok": False, "reason": "No successful off-host backup receipt"
        }
    check_path = db.parent if db.parent.is_dir() else Path("/")
    free = shutil.disk_usage(check_path).free / (1024 ** 3)
    results["disk_space"] = {
        "ok": free >= min_free_gib,
        "free_gib": round(free, 3),
    }
    return {
        "schema": "fvillage.alpha_host_health.v1",
        "generated_utc": datetime.fromtimestamp(now, tz=timezone.utc).isoformat(),
        "healthy": all(check["ok"] for check in results.values()),
        "checks": results,
        "scope": "host-readiness watchdog, not transport auth or world state proof",
    }


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--database", required=True, type=Path)
    p.add_argument("--backup-receipt", required=True, type=Path)
    p.add_argument("--max-backup-age-hours", type=float, default=26)
    p.add_argument("--min-free-gib", type=float, default=2)
    p.add_argument("--port", type=int, action="append")
    args = p.parse_args(argv)
    if args.max_backup_age_hours <= 0 or args.min_free_gib < 0:
        p.error("Invalid thresholds")
    ports = args.port if args.port is not None else [4000, 4001, 4002]
    result = check(
        args.database, args.backup_receipt,
        port_checks=tuple(("127.0.0.1", port) for port in ports),
        max_backup_age_hours=args.max_backup_age_hours,
        min_free_gib=args.min_free_gib,
    )
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if result["healthy"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
