"""Fail-closed, operator-attested public-launch evidence gate.

This validates format, deployment identity, freshness and completeness.
It NEVER executes checks, verifies remote URL contents, signs evidence,
approves spending, or certifies a real host on its own.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timedelta, timezone
import ipaddress
import json
from pathlib import Path
import re
from urllib.parse import urlsplit

REQUIRED = (
    "exact_deployed_sha", "main_ci_pass", "persistent_volume_restart",
    "snapshot_integrity", "disposable_restore", "off_host_encrypted_backup",
    "external_https", "external_wss", "ordinary_client_reconnect",
    "ordinary_account_access", "secure_telnet_policy", "new_account_consent",
    "mask_front_door", "world_state_restart", "moderation_review",
    "clock_restart", "rollback_drill", "operator_alerting",
    "uncoached_gameplay", "cross_player_consequence", "return_session",
    # Hosting, ordinary account access and reconnect are mandatory. An LLM,
    # local model, agent framework or model-led playtest is never a runtime,
    # CI or release requirement. Optional agent clients use ordinary rules.
    # Hosted soak and uncoached normal-player issue triage remain mandatory.
    "continuous_multiplayer_soak", "event_tick_under_load",
    "player_reported_blockers_cleared", "full_launch_content_coverage",
)
MAX_EVIDENCE_AGE = timedelta(days=30)
FUTURE_TOLERANCE = timedelta(minutes=5)
_SHA = re.compile(r"^[0-9a-fA-F]{40}$")
_PLACEHOLDER_HOSTS = frozenset({
    "example.com", "example.org", "example.net", "localhost",
})


def _is_evidence_url(url):
    if not isinstance(url, str) or len(url) > 2048 or url.strip() != url:
        return False
    try:
        parsed = urlsplit(url)
        host = (parsed.hostname or "").lower()
        port = parsed.port  # Raises on malformed port.
    except ValueError:
        return False
    if (parsed.scheme != "https" or not host or parsed.username
            or parsed.password or parsed.fragment or not parsed.path
            or parsed.path == "/" or any(c.isspace() for c in url)):
        return False
    if (host in _PLACEHOLDER_HOSTS
            or host.endswith((".example", ".invalid", ".test", ".local"))
            or host.endswith((".example.org", ".example.com", ".example.net"))):
        return False
    try:
        address = ipaddress.ip_address(host)
    except ValueError:
        return bool(re.fullmatch(r"[a-z0-9.-]{3,253}", host))
    return address.is_global


def _fresh_utc(value, now):
    if not isinstance(value, str) or not value.strip():
        return False
    try:
        # Date-only and timezone-naive attestations are not adequate.
        checked = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return False
    if checked.tzinfo is None or checked.utcoffset() is None:
        return False
    verified = checked.astimezone(timezone.utc)
    return now - MAX_EVIDENCE_AGE <= verified <= now + FUTURE_TOLERANCE


def assess(data, *, now=None):
    """Return operator-approval eligibility, never a production launch grant."""
    now = now or datetime.now(timezone.utc)
    if now.tzinfo is None or now.utcoffset() is None:
        raise ValueError("Clock must be timezone-aware")
    now = now.astimezone(timezone.utc)
    if not isinstance(data, dict):
        return {
            "decision": "NO-GO",
            "errors": ["evidence: expected a JSON object"],
            "deployed_sha": "",
        }
    errors = []
    sha = data.get("deployed_sha")
    if not isinstance(sha, str) or not _SHA.fullmatch(sha):
        errors.append("deployed_sha: expected exact 40-character Git SHA")
        sha = str(sha or "")[:40]
    checks = data.get("checks")
    if not isinstance(checks, dict):
        checks = {}
        errors.append("checks: expected a JSON object")
    for key in REQUIRED:
        entry = checks.get(key)
        if not isinstance(entry, dict) or entry.get("passed") is not True:
            errors.append(f"{key}: missing or not passed")
            continue
        if not _is_evidence_url(entry.get("evidence_url")):
            errors.append(
                f"{key}: non-placeholder HTTPS evidence URL with a specific path required"
            )
        if not _fresh_utc(entry.get("verified_at"), now):
            errors.append(
                f"{key}: verified_at must be recent, timezone-aware ISO8601 UTC"
            )
        if entry.get("sha") != sha:
            errors.append(f"{key}: SHA mismatch")
    operator = data.get("operator")
    if (not isinstance(operator, str) or not operator.strip()
            or operator.strip().lower() in {"todo", "tbd", "unknown", "operator"}
            or len(operator) > 150):
        errors.append("operator: accountable human name required")
    return {
        "decision": "NO-GO" if errors else "READY_FOR_OPERATOR_APPROVAL",
        "errors": errors,
        "deployed_sha": sha,
        "note": (
            "Format and freshness only. A human must independently inspect "
            "evidence links and verify the deployed service before approval."
        ),
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("evidence", type=Path)
    args = parser.parse_args()
    try:
        record = json.loads(args.evidence.read_text(encoding="utf-8"))
        result = assess(record)
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        result = {
            "decision": "NO-GO",
            "errors": ["evidence: invalid or unreadable JSON file"],
            "deployed_sha": "",
        }
    print(json.dumps(result, indent=2))
    return 1 if result["errors"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
