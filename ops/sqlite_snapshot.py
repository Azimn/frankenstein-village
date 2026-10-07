#!/usr/bin/env python3
"""Atomic, checked SQLite snapshots for Frankenstein Village alpha operations.

The backup command uses SQLite's online backup API so a running database can
be snapshotted consistently. Restore is deliberately offline-only and creates
a recoverable pre-restore snapshot before replacing an existing database.
"""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import shutil
import sqlite3
import tempfile
import uuid


class SnapshotError(Exception):
    """A backup or restore safety check failed."""


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _checked(path: Path) -> None:
    if not path.is_file():
        raise SnapshotError(f"SQLite file not found: {path}")
    try:
        with sqlite3.connect(path.as_uri() + "?mode=ro", uri=True) as connection:
            result = connection.execute("PRAGMA integrity_check").fetchone()
    except sqlite3.DatabaseError as exc:
        raise SnapshotError(f"SQLite cannot be read: {path}") from exc
    if not result or result[0] != "ok":
        raise SnapshotError(f"SQLite integrity check failed: {path}")


def _manifest_path(snapshot: Path) -> Path:
    return snapshot.with_name(snapshot.name + ".manifest.json")


def _write_manifest(snapshot: Path, database: Path) -> None:
    manifest = {
        "format": "frankenstein-village-sqlite-snapshot-v1",
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "source_filename": database.name,
        "snapshot_filename": snapshot.name,
        "size_bytes": snapshot.stat().st_size,
        "sha256": _sha256(snapshot),
        "sqlite_integrity": "ok",
    }
    dst = _manifest_path(snapshot)
    fd, temp = tempfile.mkstemp(prefix=".manifest-", dir=dst.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            json.dump(manifest, handle, sort_keys=True, indent=2)
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temp, dst)
    finally:
        if os.path.exists(temp):
            os.unlink(temp)


def _verify_manifest(snapshot: Path) -> None:
    manifest_file = _manifest_path(snapshot)
    if not manifest_file.is_file():
        raise SnapshotError("Snapshot manifest is missing; restore refused.")
    try:
        data = json.loads(manifest_file.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        raise SnapshotError("Snapshot manifest is unreadable.") from exc
    if data.get("format") != "frankenstein-village-sqlite-snapshot-v1":
        raise SnapshotError("Unsupported snapshot manifest format.")
    if data.get("snapshot_filename") != snapshot.name:
        raise SnapshotError("Manifest filename does not match snapshot.")
    if int(data.get("size_bytes", -1)) != snapshot.stat().st_size:
        raise SnapshotError("Snapshot size does not match manifest.")
    if data.get("sha256") != _sha256(snapshot):
        raise SnapshotError("Snapshot digest does not match manifest.")
    _checked(snapshot)


def backup_database(database: Path, output_dir: Path) -> Path:
    """Create a verified SQLite copy without mutating the live DB."""
    database = Path(database).expanduser().resolve()
    output_dir = Path(output_dir).expanduser().resolve()
    if not database.is_file():
        raise SnapshotError(f"Source database not found: {database}")
    output_dir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
    snapshot = output_dir / f"{database.stem}-{stamp}-{uuid.uuid4().hex[:8]}.db3"
    fd, temp = tempfile.mkstemp(prefix=".snapshot-", dir=output_dir)
    os.close(fd)
    try:
        with sqlite3.connect(
            database.as_uri() + "?mode=ro", uri=True, timeout=30
        ) as source:
            with sqlite3.connect(temp, timeout=30) as target:
                source.backup(target)
        _checked(Path(temp))
        os.replace(temp, snapshot)
        _write_manifest(snapshot, database)
        return snapshot
    except (sqlite3.Error, OSError) as exc:
        raise SnapshotError(f"Backup failed: {exc}") from exc
    finally:
        if os.path.exists(temp):
            os.unlink(temp)


def restore_database(
    database: Path,
    snapshot: Path,
    rollback_dir: Path,
    *,
    server_stopped: bool = False,
) -> Path | None:
    """Restore a verified snapshot after explicitly confirming server shutdown."""
    if not server_stopped:
        raise SnapshotError("Restore requires --confirm-server-stopped.")
    database = Path(database).expanduser().resolve()
    snapshot = Path(snapshot).expanduser().resolve()
    rollback_dir = Path(rollback_dir).expanduser().resolve()
    if database == snapshot:
        raise SnapshotError("Source snapshot cannot also be the target database.")
    _verify_manifest(snapshot)
    for suffix in ("-wal", "-shm", "-journal"):
        if Path(str(database) + suffix).exists():
            raise SnapshotError(
                f"Database sidecar present ({suffix}); ensure the server is stopped "
                "and resolve the sidecar before restore."
            )
    if not database.parent.is_dir():
        raise SnapshotError("Target database directory does not exist.")

    rollback = None
    if database.exists():
        rollback = backup_database(database, rollback_dir)

    fd, temp = tempfile.mkstemp(prefix=".restore-", dir=database.parent)
    os.close(fd)
    try:
        shutil.copyfile(snapshot, temp)
        _checked(Path(temp))
        os.replace(temp, database)
        return rollback
    except (OSError, sqlite3.Error) as exc:
        raise SnapshotError(f"Restore failed; rollback snapshot: {rollback}") from exc
    finally:
        if os.path.exists(temp):
            os.unlink(temp)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="action", required=True)
    backup = sub.add_parser("backup", help="Consistent online SQLite snapshot")
    backup.add_argument("--database", type=Path, required=True)
    backup.add_argument("--output-dir", type=Path, required=True)
    restore = sub.add_parser("restore", help="Offline checked restoration")
    restore.add_argument("--database", type=Path, required=True)
    restore.add_argument("--snapshot", type=Path, required=True)
    restore.add_argument("--rollback-dir", type=Path, required=True)
    restore.add_argument("--confirm-server-stopped", action="store_true")

    args = parser.parse_args()
    try:
        if args.action == "backup":
            snapshot = backup_database(args.database, args.output_dir)
            print(f"SNAPSHOT_BACKUP_GREEN: {snapshot}")
        else:
            rollback = restore_database(
                args.database,
                args.snapshot,
                args.rollback_dir,
                server_stopped=args.confirm_server_stopped,
            )
            print(f"SNAPSHOT_RESTORE_GREEN: {args.database}")
            if rollback:
                print(f"Pre-restore rollback snapshot: {rollback}")
    except SnapshotError as exc:
        parser.exit(2, f"Snapshot safety check failed: {exc}\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
