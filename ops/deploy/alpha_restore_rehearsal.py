#!/usr/bin/env python3
"""Rehearse off-host SQLite restoration and rollback using ISOLATED copies.

Requires a source online snapshot and the same snapshot retrieved from actual
off-host storage (each with its JSON manifest). Neither source is mutated.
This cannot independently prove that the copy traversed an external network,
that live Evennia starts, or that the operator owns working host credentials.
"""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import sqlite3
import sys
import tempfile

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from sqlite_snapshot import (  # noqa: E402
    SnapshotError,
    _checked,
    _sha256,
    _verify_manifest,
    restore_database,
)


SCHEMA = "fvillage.alpha_restore_rehearsal.v1"
# Category witnesses are probes, not invented evidence of user content.
# 'public_records' covers both Chronicle and Harbinger persisted records.
CATEGORIES = {
    "masks": ("objects_objectdb", "db_typeclass_path",
              "LIKE", "%characters%"),
    "private_rooms": ("objects_objectdb", "db_key", "=", "Private Room"),
    "event_ledger": ("scripts_scriptdb", "db_key", "=", "world_event_ledger"),
    "resident_facts": ("scripts_scriptdb", "db_key", "=", "resident_population"),
    "chronicle_and_harbinger": ("scripts_scriptdb", "db_key", "=", "public_records"),
    "timed_content": ("scripts_scriptdb", "db_key", "=", "timed_incident_registry"),
    "resource_items": ("objects_objectdb", "db_key", "IN", (
        "a loaf of bread", "a cluster of mushrooms",
        "a wedge of cheese", "a bowl of stew",
    )),
}
SUPPORTED_IDENTIFIERS = {
    "objects_objectdb", "scripts_scriptdb", "db_key", "db_typeclass_path"
}


def category_witnesses(database: Path) -> dict:
    """Read-only entity presence counts; no names, prose or secrets exported."""
    witnesses = {}
    with sqlite3.connect(database.as_uri() + "?mode=ro", uri=True) as db:
        tables = {
            row[0] for row in db.execute(
                "SELECT name FROM sqlite_master WHERE type='table'"
            )
        }
        for key, (table, column, operator, value) in CATEGORIES.items():
            if table not in tables:
                witnesses[key] = {"available": False, "count": None}
                continue
            columns = {row[1] for row in db.execute(f"PRAGMA table_info({table})")}
            if column not in columns or table not in SUPPORTED_IDENTIFIERS:
                witnesses[key] = {"available": False, "count": None}
                continue
            if operator == "IN":
                placeholders = ",".join("?" for _ in value)
                query = f"SELECT COUNT(*) FROM {table} WHERE {column} IN ({placeholders})"
                params = value
            else:
                query = f"SELECT COUNT(*) FROM {table} WHERE {column} {operator} ?"
                params = (value,)
            witnesses[key] = {
                "available": True,
                "count": int(db.execute(query, params).fetchone()[0]),
            }
    return witnesses


def _logical_sha256(database: Path) -> str:
    """Compare SQLite content, not change counters or physical page layout.

    SQLite online backup promises a logically faithful database copy, not
    necessarily an identical physical byte layout or page header.
    """
    digest = hashlib.sha256()
    with sqlite3.connect(database.as_uri() + "?mode=ro", uri=True) as db:
        for statement in db.iterdump():
            digest.update(statement.encode("utf-8"))
            digest.update(b"\n")
    return digest.hexdigest()


def _marker_exists(database: Path) -> bool:
    with sqlite3.connect(database) as db:
        found = db.execute(
            "SELECT name FROM sqlite_master WHERE type='table' "
            "AND name='fv_restore_drill_marker'"
        ).fetchone()
        return bool(found)


def perform(source: Path, retrieved: Path, evidence_file: Path) -> dict:
    """Only mutate disposable copies under a private TemporaryDirectory."""
    source = source.expanduser().resolve()
    retrieved = retrieved.expanduser().resolve()
    evidence_file = evidence_file.expanduser().resolve()
    if source == retrieved:
        raise SnapshotError("Source and off-host retrieved snapshot must be different paths.")
    if source.name != retrieved.name:
        raise SnapshotError("Retrieved snapshot must preserve the original filename.")
    if evidence_file in (source, retrieved):
        raise SnapshotError("Evidence cannot overwrite a snapshot.")
    if evidence_file.exists():
        raise SnapshotError("Evidence file already exists; refusing overwrite.")
    _verify_manifest(source)
    _verify_manifest(retrieved)
    expected_hash = _sha256(source)
    if _sha256(retrieved) != expected_hash:
        raise SnapshotError("Off-host retrieved snapshot differs from source.")
    witnessed = category_witnesses(source)

    with tempfile.TemporaryDirectory(prefix="fv-offhost-restore-") as folder:
        workspace = Path(folder)
        staged = workspace / "evennia.db3"
        rollback_dir = workspace / "rollback"
        # This staged target does not belong to a running process.
        staged.write_bytes(source.read_bytes())
        with sqlite3.connect(staged) as db:
            db.execute(
                "CREATE TABLE fv_restore_drill_marker "
                "(id INTEGER PRIMARY KEY, interrupted TEXT NOT NULL)"
            )
            db.execute(
                "INSERT INTO fv_restore_drill_marker (interrupted) "
                "VALUES ('rollback sentinel')"
            )
            db.commit()
        modified_hash = _sha256(staged)
        modified_logical_hash = _logical_sha256(staged)
        if modified_hash == expected_hash:
            raise SnapshotError("Could not simulate a changed database.")

        rollback = restore_database(
            staged, retrieved, rollback_dir, server_stopped=True
        )
        if not rollback or not rollback.exists():
            raise SnapshotError("No pre-restore rollback snapshot was retained.")
        _verify_manifest(rollback)
        rollback_snapshot_hash = _sha256(rollback)
        if not _marker_exists(rollback):
            raise SnapshotError("Rollback omitted the modified state.")
        if _sha256(staged) != expected_hash or _marker_exists(staged):
            raise SnapshotError("Restore did not recover the exact original state.")
        if category_witnesses(staged) != witnessed:
            raise SnapshotError("Category witness counts changed after restoration.")

        # Verify reverse operation, not simply that a rollback FILE exists.
        restore_database(staged, rollback, workspace / "rollback-again",
                         server_stopped=True)
        if not _marker_exists(staged):
            raise SnapshotError("Rollback failed to recover the simulated change.")
        if _logical_sha256(staged) != modified_logical_hash:
            raise SnapshotError("Rollback did not recover identical logical rows.")

        # Finish with the original verified state in the disposable workspace.
        restore_database(staged, retrieved, workspace / "final-rollback",
                         server_stopped=True)
        if _sha256(staged) != expected_hash:
            raise SnapshotError("Final restore does not match the original.")

    record = {
        "schema": SCHEMA,
        "generated_utc": datetime.now(timezone.utc).isoformat(),
        "type": "isolated_rehearsal_with_operator_supplied_retrieved_copy",
        "host_drill_certified": False,
        "source_sha256": expected_hash,
        "retrieved_sha256": expected_hash,
        "restored_sha256": expected_hash,
        "modified_sha256": modified_hash,
        "modified_logical_sha256": modified_logical_hash,
        "rollback_snapshot_sha256": rollback_snapshot_hash,
        "rollback_logical_sha256": modified_logical_hash,
        "exact_restore": True,
        "rollback_tested": True,
        "final_original_state_recovered": True,
        "category_witnesses": witnessed,
        "all_categories_present": all(
            item["available"] and item["count"] > 0
            for item in witnessed.values()
        ),
        "requires_operator_evidence": [
            "independent off-host upload/download and destination receipt",
            "host identity and storage device/volume identity",
            "actual player/content category witnesses (not only registry existence)",
            "actual service stop/start and game-protocol login after restore",
            "host monitoring, alerts, backup freshness and retention proofs",
        ],
    }
    evidence_file.parent.mkdir(parents=True, exist_ok=True)
    # Keep evidence private by default; it contains no account identifiers.
    fd = os.open(str(evidence_file), os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
    with os.fdopen(fd, "w", encoding="utf-8") as handle:
        json.dump(record, handle, sort_keys=True, indent=2)
        handle.write("\n")
    return record


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-snapshot", type=Path, required=True)
    parser.add_argument("--retrieved-snapshot", type=Path, required=True)
    parser.add_argument("--evidence-out", type=Path, required=True)
    args = parser.parse_args(argv)
    try:
        result = perform(
            args.source_snapshot, args.retrieved_snapshot, args.evidence_out
        )
    except (SnapshotError, OSError, sqlite3.Error, ValueError) as exc:
        parser.exit(2, f"Restore rehearsal FAILED: {exc}\n")
    print(json.dumps(result, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
