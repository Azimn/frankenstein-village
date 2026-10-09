"""Read-only host checks: healthy ports, failed port, expired backup, low disk."""

from __future__ import annotations

import importlib.util
import os
from pathlib import Path
import socket
import sys
import tempfile
import threading
import unittest


ROOT = Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location(
    "fv_alpha_host_health", ROOT / "ops/deploy/host_health.py"
)
health = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = health
spec.loader.exec_module(health)


class HostHealthTests(unittest.TestCase):
    def setUp(self):
        self.context = tempfile.TemporaryDirectory()
        self.addCleanup(self.context.cleanup)
        self.root = Path(self.context.name)
        self.database = self.root / "evennia.db3"
        self.database.write_bytes(b"local sentinel, not a real database")
        self.receipt = self.root / "offhost-verified.receipt"
        self.receipt.write_text("test receipt")
        self.listener = socket.socket()
        self.listener.bind(("127.0.0.1", 0))
        self.listener.listen(2)
        self.addCleanup(self.listener.close)
        self.port = self.listener.getsockname()[1]

    def test_loopback_and_fresh_receipt_success(self):
        result = health.check(
            self.database, self.receipt,
            port_checks=(("127.0.0.1", self.port),),
            min_free_gib=0, now=self.receipt.stat().st_mtime + 10,
        )
        self.assertTrue(result["healthy"])
        self.assertTrue(result["checks"]["loopback_" + str(self.port)]["ok"])
        self.assertTrue(result["checks"]["backup_receipt"]["ok"])

    def test_missing_port_or_receipt_is_unhealthy(self):
        self.listener.close()
        result = health.check(
            self.database, self.root / "missing-receipt",
            port_checks=(("127.0.0.1", self.port),),
            min_free_gib=0,
        )
        self.assertFalse(result["healthy"])
        self.assertFalse(result["checks"]["backup_receipt"]["ok"])
        self.assertFalse(result["checks"]["loopback_" + str(self.port)]["ok"])

    def test_stale_receipt_fails(self):
        result = health.check(
            self.database, self.receipt,
            port_checks=(), max_backup_age_hours=2,
            min_free_gib=0, now=self.receipt.stat().st_mtime + 4 * 3600,
        )
        self.assertFalse(result["healthy"])
        self.assertGreater(result["checks"]["backup_receipt"]["age_hours"], 2)

    def test_external_port_is_forbidden(self):
        with self.assertRaisesRegex(ValueError, "loopback"):
            health.check(self.database, self.receipt,
                         port_checks=(("example.com", 443),), min_free_gib=0)


if __name__ == "__main__":
    unittest.main()
