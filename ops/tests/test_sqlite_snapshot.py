"""Pure standard-library recovery tests on temporary synthetic databases."""

from __future__ import annotations

import sqlite3
import tempfile
import unittest
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "ops"))
from sqlite_snapshot import SnapshotError, backup_database, restore_database


class SQLiteSnapshotTests(unittest.TestCase):
    def setUp(self):
        self.tempdir = tempfile.TemporaryDirectory()
        self.addCleanup(self.tempdir.cleanup)
        self.root = Path(self.tempdir.name)
        self.db = self.root / "evennia.db3"
        self.backups = self.root / "safe-backups"
        self.rollbacks = self.root / "rollback-backups"
        with sqlite3.connect(self.db) as conn:
            conn.execute("CREATE TABLE world_state (value TEXT)")
            conn.execute("INSERT INTO world_state VALUES ('original')")

    def value(self):
        with sqlite3.connect(self.db) as conn:
            return conn.execute("SELECT value FROM world_state").fetchone()[0]

    def test_backup_restore_and_preserve_rollback(self):
        snapshot = backup_database(self.db, self.backups)
        self.assertTrue(snapshot.exists())
        self.assertTrue(Path(str(snapshot) + ".manifest.json").exists())
        with sqlite3.connect(self.db) as conn:
            conn.execute("UPDATE world_state SET value='changed'")
        self.assertEqual(self.value(), "changed")
        rollback = restore_database(
            self.db, snapshot, self.rollbacks, server_stopped=True
        )
        self.assertEqual(self.value(), "original")
        self.assertIsNotNone(rollback)
        with sqlite3.connect(rollback) as conn:
            self.assertEqual(
                conn.execute("SELECT value FROM world_state").fetchone()[0],
                "changed",
            )

    def test_restore_requires_shutdown_acknowledgment(self):
        snapshot = backup_database(self.db, self.backups)
        with self.assertRaisesRegex(SnapshotError, "confirm-server-stopped"):
            restore_database(self.db, snapshot, self.rollbacks)
        self.assertEqual(self.value(), "original")

    def test_corrupt_or_modified_snapshot_is_refused(self):
        snapshot = backup_database(self.db, self.backups)
        with snapshot.open("ab") as handle:
            handle.write(b"untrusted modification")
        with self.assertRaisesRegex(SnapshotError, "digest|size"):
            restore_database(
                self.db, snapshot, self.rollbacks, server_stopped=True
            )
        self.assertEqual(self.value(), "original")

    def test_active_journal_sidecar_blocks_restore(self):
        snapshot = backup_database(self.db, self.backups)
        journal = Path(str(self.db) + "-journal")
        journal.write_bytes(b"possibly active")
        with self.assertRaisesRegex(SnapshotError, "sidecar present"):
            restore_database(
                self.db, snapshot, self.rollbacks, server_stopped=True
            )
        self.assertEqual(self.value(), "original")

    def test_original_remains_writable_after_online_backup(self):
        backup_database(self.db, self.backups)
        with sqlite3.connect(self.db) as conn:
            conn.execute("INSERT INTO world_state VALUES ('still live')")
        with sqlite3.connect(self.db) as conn:
            count = conn.execute("SELECT COUNT(*) FROM world_state").fetchone()[0]
        self.assertEqual(count, 2)


if __name__ == "__main__":
    unittest.main()
