"""Real loopback WebSocket handshake and transport safety tests."""

from __future__ import annotations

import base64
import hashlib
from pathlib import Path
import re
import socket
import sys
import threading
import unittest


sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "ops"))
from websocket_probe import WebSocketProbeError, probe_websocket


class HandshakeTests(unittest.TestCase):
    def _server(self, *, correct=True):
        listener = socket.socket()
        listener.bind(("127.0.0.1", 0))
        listener.listen(1)
        self.addCleanup(listener.close)
        port = listener.getsockname()[1]

        def serve():
            try:
                with listener.accept()[0] as connection:
                    connection.settimeout(3)
                    buf = bytearray()
                    while b"\r\n\r\n" not in buf:
                        part = connection.recv(4096)
                        if not part:
                            return
                        buf.extend(part)
                    match = re.search(rb"Sec-WebSocket-Key:\s*([^\r\n]+)", buf, re.I)
                    if not match:
                        return
                    key = match.group(1).strip().decode("ascii")
                    accept = base64.b64encode(hashlib.sha1(
                        (key + "258EAFA5-E914-47DA-95CA-C5AB0DC85B11").encode("ascii")
                    ).digest()).decode("ascii")
                    if not correct:
                        accept = "corrupted"
                    response = (
                        "HTTP/1.1 101 Switching Protocols\r\n"
                        "Upgrade: websocket\r\n"
                        "Connection: Upgrade\r\n"
                        f"Sec-WebSocket-Accept: {accept}\r\n\r\n"
                    )
                    connection.sendall(response.encode("ascii"))
            except OSError:
                pass
        thread = threading.Thread(target=serve, daemon=True)
        thread.start()
        self.addCleanup(lambda: thread.join(3))
        return port

    def test_valid_loopback_upgrade(self):
        port = self._server()
        report = probe_websocket(f"ws://127.0.0.1:{port}/")
        self.assertEqual(report["status"], "pass")
        self.assertEqual(report["transport"], "loopback_ws")

    def test_invalid_accept_rejected(self):
        port = self._server(correct=False)
        with self.assertRaisesRegex(WebSocketProbeError, "accept value"):
            probe_websocket(f"ws://127.0.0.1:{port}/")

    def test_remote_plaintext_and_credentials_rejected_without_network(self):
        for url in (
            "ws://village.example.org:4042/",
            "wss://user:password@village.example.org/",
            "wss://village.example.org/?secret=123",
            "wss://village.example.org/#anchor",
        ):
            with self.subTest(url=url), self.assertRaises(WebSocketProbeError):
                probe_websocket(url)


if __name__ == "__main__":
    unittest.main()
