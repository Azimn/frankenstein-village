"""Loopback transport and disposable-recovery preflight regression coverage."""

from __future__ import annotations

from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
import socket
import sqlite3
import sys
import tempfile
import threading
import unittest


ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "ops"))
from sqlite_snapshot import backup_database
from alpha_preflight import (
    PreflightError,
    _telnet_text,
    probe_telnet,
    probe_web,
    run_preflight,
    verify_disposable_restore,
)


class WebHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header("Content-Type", "text/html")
        self.end_headers()
        self.wfile.write(b"<html><title>Village web client</title></html>")

    def log_message(self, *_args):
        pass


class PreflightTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        root = Path(self.tmp.name)
        self.database = root / "evennia.db3"
        with sqlite3.connect(self.database) as connection:
            connection.execute("CREATE TABLE markers (name TEXT)")
            connection.execute("INSERT INTO markers VALUES ('persistent')")
        self.snapshot = backup_database(self.database, root / "backups")

    def _start_tcp_banner(self, banner=b"\xff\xfb\x01\x1b[35mFrankenstein Village\x1b[0m\r\n"):
        listener = socket.socket()
        listener.bind(("127.0.0.1", 0))
        listener.listen(1)
        self.addCleanup(listener.close)
        port = listener.getsockname()[1]
        def serve():
            try:
                connection, _ = listener.accept()
                with connection:
                    connection.sendall(banner)
            except OSError:
                pass
        worker = threading.Thread(target=serve, daemon=True)
        worker.start()
        self.addCleanup(lambda: worker.join(1))
        return port

    def _start_web(self):
        server = HTTPServer(("127.0.0.1", 0), WebHandler)
        worker = threading.Thread(target=server.serve_forever, daemon=True)
        worker.start()
        self.addCleanup(server.server_close)
        self.addCleanup(server.shutdown)
        self.addCleanup(lambda: worker.join(1))
        return "http://127.0.0.1:%d/" % server.server_port

    def test_snapshot_copy_is_valid_and_original_untouched(self):
        result = verify_disposable_restore(self.snapshot)
        self.assertEqual(result["status"], "pass")
        with sqlite3.connect(self.database) as connection:
            self.assertEqual(
                connection.execute("SELECT name FROM markers").fetchone()[0],
                "persistent",
            )

    def test_modified_manifest_or_bytes_cannot_pass(self):
        with self.snapshot.open("ab") as handle:
            handle.write(b"modified")
        with self.assertRaisesRegex(PreflightError, "verification failed"):
            verify_disposable_restore(self.snapshot)

    def test_telnet_strips_negotiation_and_ansi(self):
        self.assertIn(
            "frankenstein village",
            _telnet_text(b"\xff\xfb\x01\x1b[35mFrankenstein Village\x1b[0m"),
        )
        port = self._start_tcp_banner()
        self.assertEqual(probe_telnet("127.0.0.1", port)["status"], "pass")

    def test_wrong_telnet_banner_fails(self):
        port = self._start_tcp_banner(b"Unrelated server\r\n")
        with self.assertRaisesRegex(PreflightError, "expected village login banner"):
            probe_telnet("127.0.0.1", port, timeout=1)

    def test_no_remote_plaintext_telnet(self):
        with self.assertRaisesRegex(PreflightError, "only on loopback"):
            probe_telnet("192.0.2.1", 4000)

    def test_local_web_and_public_http_policy(self):
        self.assertEqual(probe_web(self._start_web())["status"], "pass")
        with self.assertRaisesRegex(PreflightError, "must use HTTPS"):
            probe_web("http://example.org/")

    def test_https_preflight_requires_wss(self):
        with self.assertRaisesRegex(PreflightError, "requires --websocket-url"):
            run_preflight(
                self.snapshot, "127.0.0.1", 4000,
                "https://village.example.org"
            )

    def test_full_preflight_cannot_certify_launch(self):
        port = self._start_tcp_banner()
        web = self._start_web()
        report = run_preflight(self.snapshot, "127.0.0.1", port, web)
        self.assertEqual(len(report["checks"]), 3)
        self.assertFalse(report["launch_certified"])
        self.assertEqual(report["result"], "transport_and_recovery_checks_passed")


if __name__ == "__main__":
    unittest.main()
