"""Disposable restore rehearsal, not a claim of production or off-host proof."""

from __future__ import annotations

import importlib.util
from pathlib import Path
import shutil
import sqlite3
import sys
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "ops"))
spec = importlib.util.spec_from_file_location(
    "fv_alpha_restore_rehearsal", ROOT / "ops/deploy/alpha_restore_rehearsal.py"
)
rehearsal = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = rehearsal
spec.loader.exec_module(rehearsal)
from sqlite_snapshot import (  # noqa: E402
    SnapshotError, backup_database, _manifest_path, _sha256
)


class RestoreDrillTests(unittest.TestCase):
    def setUp(self):
        self.context = tempfile.TemporaryDirectory(prefix="fv-gate-a-test-")
        self.addCleanup(self.context.cleanup)
        self.root = Path(self.context.name)
        self.live = self.root / "production-not-really.db3"
        with sqlite3.connect(self.live) as db:
            db.executescript("""
            CREATE TABLE objects_objectdb (
                id INTEGER PRIMARY KEY,
                db_key TEXT NOT NULL,
                db_typeclass_path TEXT NOT NULL
            );
            CREATE TABLE scripts_scriptdb (
                id INTEGER PRIMARY KEY,
                db_key TEXT NOT NULL
            );
            CREATE TABLE accounts_accountdb (id INTEGER PRIMARY KEY);
            INSERT INTO accounts_accountdb VALUES(1);
            INSERT INTO objects_objectdb VALUES
                (1, 'AlphaMask', 'typeclasses.characters.Character'),
                (2, 'Private Room', 'typeclasses.rooms.PrivateRoom'),
                (3, 'a loaf of bread', 'typeclasses.objects.Object');
            INSERT INTO scripts_scriptdb VALUES
                (1, 'world_event_ledger'),
                (2, 'resident_population'),
                (3, 'public_records'),
                (4, 'timed_incident_registry');
            """)
        self.snapshot = backup_database(self.live, self.root / "snapshots")
        self.retrieved = self.root / "retrieved" / self.snapshot.name
        self.retrieved.parent.mkdir()
        shutil.copy2(self.snapshot, self.retrieved)
        shutil.copy2(_manifest_path(self.snapshot), _manifest_path(self.retrieved))

    def test_exact_restoration_and_real_rollback_without_mutating_source(self):
        before = _sha256(self.live)
        outcome = rehearsal.perform(
            self.snapshot, self.retrieved, self.root / "evidence.json"
        )
        self.assertEqual(_sha256(self.live), before)
        self.assertEqual(outcome["source_sha256"], outcome["restored_sha256"])
        self.assertEqual(outcome["modified_sha256"], outcome["rollback_sha256"])
        self.assertNotEqual(outcome["source_sha256"], outcome["rollback_sha256"])
        self.assertTrue(outcome["exact_restore"])
        self.assertTrue(outcome["rollback_tested"])
        self.assertTrue(outcome["final_original_state_recovered"])
        self.assertTrue(outcome["all_categories_present"])
        self.assertFalse(outcome["host_drill_certified"])
        self.assertTrue((self.root / "evidence.json").exists())

    def test_never_treat_same_path_as_offhost_copy(self):
        with self.assertRaisesRegex(SnapshotError, "different paths"):
            rehearsal.perform(self.snapshot, self.snapshot, self.root / "bad.json")
        self.assertFalse((self.root / "bad.json").exists())

    def test_bad_retrieved_copy_does_not_produce_success_evidence(self):
        self.retrieved.write_bytes(self.retrieved.read_bytes() + b"corruption")
        with self.assertRaises(SnapshotError):
            rehearsal.perform(self.snapshot, self.retrieved, self.root / "bad.json")
        self.assertFalse((self.root / "bad.json").exists())

    def test_refuses_overwrite_of_evidence(self):
        existing = self.root / "existing.json"
        existing.write_text("untouched")
        with self.assertRaisesRegex(SnapshotError, "already exists"):
            rehearsal.perform(self.snapshot, self.retrieved, existing)
        self.assertEqual(existing.read_text(), "untouched")


if __name__ == "__main__":
    unittest.main()
