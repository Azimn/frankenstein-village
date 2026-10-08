"""Read-only WebSocket transport check for the externally proxied client.

Checks a standards-compliant handshake, not user authentication or gameplay.
Remote plaintext ws:// is forbidden. Certificate verification uses system trust.
"""

from __future__ import annotations

import base64
import hashlib
import os
import socket
import ssl
from urllib.parse import urlsplit


class WebSocketProbeError(RuntimeError):
    pass


def _is_loopback(name: str) -> bool:
    import ipaddress
    if name.lower() == "localhost":
        return True
    try:
        return ipaddress.ip_address(name).is_loopback
    except ValueError:
        return False


def probe_websocket(url: str, *, timeout: float = 8.0) -> dict:
    parsed = urlsplit(url)
    if parsed.scheme not in {"ws", "wss"} or not parsed.hostname:
        raise WebSocketProbeError("WebSocket URL must be absolute ws(s).")
    if parsed.username or parsed.password or parsed.fragment or parsed.query:
        raise WebSocketProbeError(
            "WebSocket URL must not contain credentials, a query, or a fragment."
        )
    if parsed.scheme == "ws" and not _is_loopback(parsed.hostname):
        raise WebSocketProbeError("Remote WebSocket connections must use WSS.")
    if timeout <= 0:
        raise WebSocketProbeError("Timeout must be positive.")
    try:
        port = parsed.port or (443 if parsed.scheme == "wss" else 80)
    except ValueError as exc:
        raise WebSocketProbeError("Invalid WebSocket port.") from exc
    path = parsed.path or "/"
    # Python urlsplit does not reject all embedded CR/LF in input.
    if any(ord(ch) < 33 or ord(ch) > 126 for ch in path):
        raise WebSocketProbeError("Unsafe WebSocket path.")
    host = parsed.hostname
    if not host or any(ch in host for ch in "\r\n"):
        raise WebSocketProbeError("Unsafe WebSocket hostname.")

    key = base64.b64encode(os.urandom(16)).decode("ascii")
    expected = base64.b64encode(
        hashlib.sha1(
            (key + "258EAFA5-E914-47DA-95CA-C5AB0DC85B11").encode("ascii")
        ).digest()
    ).decode("ascii")
    host_header = (
        "[" + host + "]" if ":" in host else host
    ) + (":" + str(port) if port not in (80, 443) else "")
    origin = ("https://" if parsed.scheme == "wss" else "http://") + host_header
    request = (
        f"GET {path} HTTP/1.1\r\n"
        f"Host: {host_header}\r\n"
        "Upgrade: websocket\r\n"
        "Connection: Upgrade\r\n"
        f"Sec-WebSocket-Key: {key}\r\n"
        "Sec-WebSocket-Version: 13\r\n"
        f"Origin: {origin}\r\n"
        "\r\n"
    ).encode("ascii")
    try:
        with socket.create_connection((host, port), timeout=timeout) as base:
            if parsed.scheme == "wss":
                with ssl.create_default_context().wrap_socket(
                    base, server_hostname=host
                ) as conn:
                    headers = _handshake(conn, request, timeout)
            else:
                headers = _handshake(base, request, timeout)
    except (OSError, ssl.SSLError) as exc:
        raise WebSocketProbeError(
            "WebSocket transport unavailable: " + type(exc).__name__
        ) from exc

    first, *rest = headers.split("\r\n")
    if not first.startswith("HTTP/1.1 101 ") and first != "HTTP/1.1 101":
        raise WebSocketProbeError("WebSocket did not return HTTP 101.")
    fields = {}
    for line in rest:
        if ":" in line:
            name, value = line.split(":", 1)
            fields[name.strip().lower()] = value.strip()
    if fields.get("sec-websocket-accept") != expected:
        raise WebSocketProbeError("WebSocket handshake accept value was invalid.")
    if fields.get("upgrade", "").lower() != "websocket":
        raise WebSocketProbeError("WebSocket upgrade header was missing.")
    if "upgrade" not in [
        word.strip().lower()
        for word in fields.get("connection", "").split(",")
    ]:
        raise WebSocketProbeError("WebSocket connection upgrade was missing.")
    return {
        "name": "websocket_handshake",
        "status": "pass",
        "transport": "wss" if parsed.scheme == "wss" else "loopback_ws",
    }


def _handshake(conn, request: bytes, timeout: float) -> str:
    conn.settimeout(timeout)
    conn.sendall(request)
    buffer = bytearray()
    while b"\r\n\r\n" not in buffer and len(buffer) < 16384:
        data = conn.recv(2048)
        if not data:
            break
        buffer.extend(data)
    if b"\r\n\r\n" not in buffer:
        raise WebSocketProbeError("WebSocket response headers were incomplete.")
    return buffer.partition(b"\r\n\r\n")[0].decode("latin-1")
