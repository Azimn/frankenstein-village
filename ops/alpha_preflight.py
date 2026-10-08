#!/usr/bin/env python3
"""Read-only alpha transport and recovery preflight for Frankenstein Village.

This tool verifies a checked SQLite snapshot can be read from an isolated
copy, and that configured telnet and web entry points respond. It does not
authenticate, modify live gameplay state, or declare the world launch-ready.
"""

from __future__ import annotations

import argparse
import ipaddress
import json
from pathlib import Path
import re
import shutil
import socket
import sqlite3
import ssl
import tempfile
import time
from urllib.error import HTTPError, URLError
from urllib.parse import urlparse
from urllib.request import Request, urlopen

from sqlite_snapshot import SnapshotError, _checked, _verify_manifest


class PreflightError(RuntimeError):
    """A required alpha release preflight check did not pass."""


def _loopback(host: str) -> bool:
    if str(host).strip().lower() == "localhost":
        return True
    try:
        return ipaddress.ip_address(host).is_loopback
    except ValueError:
        return False


def verify_disposable_restore(snapshot: Path) -> dict:
    """Verify manifest and the database from an isolated disposable copy."""
    snapshot = Path(snapshot).expanduser().resolve()
    try:
        _verify_manifest(snapshot)
        with tempfile.TemporaryDirectory(prefix="fvillage-restore-drill-") as tmp:
            restored = Path(tmp) / "restored.db3"
            shutil.copyfile(snapshot, restored)
            _checked(restored)
            with sqlite3.connect(restored.as_uri() + "?mode=ro", uri=True) as db:
                db.execute("SELECT 1").fetchone()
    except (OSError, sqlite3.Error, SnapshotError) as exc:
        raise PreflightError(f"disposable snapshot verification failed: {exc}") from exc
    return {"name": "disposable_snapshot_restore", "status": "pass"}


def _telnet_text(data: bytes) -> str:
    """Strip telnet option negotiation and ANSI styling from a received banner."""
    out = bytearray()
    i = 0
    while i < len(data):
        current = data[i]
        if current != 255:
            out.append(current)
            i += 1
            continue
        if i + 1 >= len(data):
            break
        command = data[i + 1]
        if command == 255:
            out.append(255)
            i += 2
        elif command in (251, 252, 253, 254):
            i += 3
        elif command == 250:
            end = data.find(b"\xff\xf0", i + 2)
            if end < 0:
                break
            i = end + 2
        else:
            i += 2
    visible = re.sub(r"\x1b\[[0-9;?]*[ -/]*[@-~]", "", out.decode("utf-8", "replace"))
    return visible.lower()


def probe_telnet(
    host: str,
    port: int = 4000,
    *,
    timeout: float = 8.0,
    tls: bool = False,
) -> dict:
    """Read the login banner; never send credentials or game commands."""
    if not host:
        raise PreflightError("telnet host must be provided")
    if not 1 <= port <= 65535:
        raise PreflightError("telnet port must be between 1 and 65535")
    if timeout <= 0:
        raise PreflightError("timeout must be positive")
    if not tls and not _loopback(host):
        raise PreflightError(
            "plaintext telnet verification is allowed only on loopback; "
            "use a verified TLS endpoint for remote connectivity"
        )
    deadline = time.monotonic() + timeout
    try:
        with socket.create_connection((host, port), timeout=timeout) as raw:
            if tls:
                context = ssl.create_default_context()
                connection = context.wrap_socket(raw, server_hostname=host)
            else:
                connection = raw
            with connection if connection is not raw else _borrowed(connection):
                buffer = bytearray()
                while time.monotonic() < deadline and len(buffer) < 16384:
                    connection.settimeout(max(0.1, min(1.0, deadline - time.monotonic())))
                    try:
                        received = connection.recv(4096)
                    except socket.timeout:
                        continue
                    if not received:
                        break
                    buffer.extend(received)
                    if "frankenstein village" in _telnet_text(buffer):
                        return {
                            "name": "telnet_banner",
                            "status": "pass",
                            "transport": "tls" if tls else "loopback_plaintext",
                        }
    except (OSError, ssl.SSLError) as exc:
        raise PreflightError(f"telnet transport failed: {type(exc).__name__}") from exc
    raise PreflightError("telnet endpoint did not return the expected village login banner")


class _borrowed:
    """Context manager that does not double-close a socket owned by a caller."""

    def __init__(self, item):
        self.item = item

    def __enter__(self):
        return self.item

    def __exit__(self, *_args):
        return False


def probe_web(url: str, *, timeout: float = 8.0) -> dict:
    """GET the public landing page without logging in or modifying state."""
    parsed = urlparse(url)
    if parsed.scheme not in {"http", "https"} or not parsed.hostname:
        raise PreflightError("web URL must be absolute http(s)")
    if parsed.username or parsed.password or parsed.fragment:
        raise PreflightError("web URL cannot contain credentials or a fragment")
    if parsed.scheme == "http" and not _loopback(parsed.hostname):
        raise PreflightError(
            "a public web endpoint must use HTTPS; plaintext HTTP is "
            "permitted only on loopback"
        )
    try:
        request = Request(url, headers={"User-Agent": "FrankensteinVillageAlphaPreflight/1"})
        with urlopen(request, timeout=timeout) as response:
            final_url = urlparse(response.geturl())
            if final_url.scheme == "http" and not _loopback(final_url.hostname or ""):
                raise PreflightError("web redirect downgraded to public HTTP")
            if response.status != 200:
                raise PreflightError(f"web endpoint returned HTTP {response.status}")
            body = response.read(65536)
            if not body.strip():
                raise PreflightError("web landing page returned an empty body")
            return {
                "name": "web_landing",
                "status": "pass",
                "transport": final_url.scheme,
            }
    except (HTTPError, URLError, TimeoutError, OSError) as exc:
        raise PreflightError(f"web transport failed: {type(exc).__name__}") from exc


def run_preflight(
    snapshot: Path,
    telnet_host: str,
    telnet_port: int,
    web_url: str,
    *,
    timeout: float = 8.0,
    telnet_tls: bool = False,
) -> dict:
    """Require all three independent checks; return no launch certification."""
    checks = [
        verify_disposable_restore(snapshot),
        probe_telnet(telnet_host, telnet_port, timeout=timeout, tls=telnet_tls),
        probe_web(web_url, timeout=timeout),
    ]
    return {
        "result": "transport_and_recovery_checks_passed",
        "launch_certified": False,
        "checks": checks,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--snapshot", type=Path, required=True)
    parser.add_argument("--telnet-host", required=True)
    parser.add_argument("--telnet-port", type=int, default=4000)
    parser.add_argument("--telnet-tls", action="store_true")
    parser.add_argument("--web-url", required=True)
    parser.add_argument("--timeout", type=float, default=8.0)
    args = parser.parse_args()
    try:
        report = run_preflight(
            args.snapshot,
            args.telnet_host,
            args.telnet_port,
            args.web_url,
            timeout=args.timeout,
            telnet_tls=args.telnet_tls,
        )
    except PreflightError as exc:
        parser.exit(2, f"ALPHA_PREFLIGHT_FAILED: {exc}\n")
    print(json.dumps(report, sort_keys=True, indent=2))
    print("ALPHA_TRANSPORT_RECOVERY_GREEN")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
