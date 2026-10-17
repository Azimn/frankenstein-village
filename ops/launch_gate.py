"""Fail-closed launch evidence gate. Standard library only.

Run with a JSON evidence record. Missing evidence always means NO-GO.
This is an operator attestation checker, not a substitute for executing tests.
"""
import argparse
import json
from pathlib import Path

REQUIRED = (
    "exact_deployed_sha", "main_ci_pass", "persistent_volume_restart",
    "snapshot_integrity", "disposable_restore", "off_host_encrypted_backup",
    "external_https", "external_wss", "ai_external_reconnect",
    "ai_account_access", "secure_telnet_policy", "new_account_consent",
    "mask_front_door", "world_state_restart", "moderation_review",
    "clock_restart", "rollback_drill", "operator_alerting",
    "uncoached_gameplay", "cross_player_consequence", "return_session",
)

def assess(data):
    errors = []
    sha = str(data.get("deployed_sha") or "")
    if len(sha) != 40 or any(c not in "0123456789abcdef" for c in sha.lower()):
        errors.append("deployed_sha: expected exact 40-character Git SHA")
    for key in REQUIRED:
        entry = data.get("checks", {}).get(key)
        if not isinstance(entry, dict) or entry.get("passed") is not True:
            errors.append(f"{key}: missing or not passed")
            continue
        if not str(entry.get("evidence_url") or "").startswith(("https://", "http://")):
            errors.append(f"{key}: evidence_url required")
        if not str(entry.get("verified_at") or "").strip():
            errors.append(f"{key}: verified_at required")
        if key in ("exact_deployed_sha", "main_ci_pass") and entry.get("sha") != sha:
            errors.append(f"{key}: SHA mismatch")
    if not str(data.get("operator") or "").strip():
        errors.append("operator: named accountable operator required")
    return {"decision": "NO-GO" if errors else "READY_FOR_OPERATOR_APPROVAL",
            "errors": errors, "deployed_sha": sha}

def main():
    p = argparse.ArgumentParser()
    p.add_argument("evidence", type=Path)
    args = p.parse_args()
    result = assess(json.loads(args.evidence.read_text(encoding="utf-8")))
    print(json.dumps(result, indent=2))
    raise SystemExit(1 if result["errors"] else 0)

if __name__ == "__main__":
    main()
