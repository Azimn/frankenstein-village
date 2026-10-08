"""Explicit, fail-closed settings for hosting behind a local reverse proxy.

Pure Python on purpose: release validation does not need to start Evennia.
Developer checkouts retain the existing settings unless a deployment mode is
explicitly selected. Do not put secrets, certificates, or player data here.
"""

from __future__ import annotations

import re
from urllib.parse import urlsplit


class DeploymentConfigurationError(ValueError):
    """The requested public deployment has an unsafe or incomplete setting."""


_HOST_LABEL = re.compile(r"^[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?$")


def _public_hostname(raw: str) -> str:
    host = str(raw or "").strip().lower()
    if (
        not host or len(host) > 253 or host.endswith(".")
        or "://" in host or "/" in host or ":" in host or "@" in host
    ):
        raise DeploymentConfigurationError(
            "FV_PUBLIC_HOST must be a plain DNS hostname, not a URL or IP:port."
        )
    if host in {"localhost", "localhost.localdomain"} or host.endswith(".localhost"):
        raise DeploymentConfigurationError(
            "FV_PUBLIC_HOST must be a real public hostname."
        )
    labels = host.split(".")
    if len(labels) < 2 or any(not _HOST_LABEL.fullmatch(label) for label in labels):
        raise DeploymentConfigurationError(
            "FV_PUBLIC_HOST must be a valid fully qualified DNS hostname."
        )
    if labels[-1].isdigit():
        raise DeploymentConfigurationError(
            "FV_PUBLIC_HOST must be a DNS name, not an unvalidated IP address."
        )
    return host


def public_profile(environ) -> dict:
    """Produce settings only after all public-mode requirements pass.

    Public mode requires an explicit hostname, with loopback-only Evennia
    listeners behind an HTTPS/WSS reverse proxy. No plaintext telnet is
    exposed directly. The proxy is responsible for public certificates.
    """
    mode = str(environ.get("FV_DEPLOYMENT_MODE", "development")).strip().lower()
    if mode in {"development", "dev"}:
        return {}
    if mode != "public":
        raise DeploymentConfigurationError(
            "FV_DEPLOYMENT_MODE must be development or public."
        )

    host = _public_hostname(environ.get("FV_PUBLIC_HOST", ""))
    if str(environ.get("WEBCLIENT_CLIENT_PROXY_PORT", "")).strip() != "4042":
        raise DeploymentConfigurationError(
            "Public mode requires WEBCLIENT_CLIENT_PROXY_PORT=4042 "
            "for the TLS WebSocket gateway."
        )
    registration = str(environ.get("FV_PUBLIC_REGISTRATION", "0")).strip()
    if registration not in {"0", "1"}:
        raise DeploymentConfigurationError(
            "FV_PUBLIC_REGISTRATION must be 0 or 1."
        )
    proxy_host = "https://" + host
    # Evennia's browser appends the client-facing proxy port itself.
    # Do not embed a path in WEBSOCKET_CLIENT_URL.
    websocket = "wss://" + host
    # Validate generated absolute URLs too; never accept a proxy URL from
    # arbitrary environment input.
    if urlsplit(websocket).hostname != host:
        raise DeploymentConfigurationError("Invalid secure websocket endpoint.")

    return {
        "SERVER_HOSTNAME": host,
        "ALLOWED_HOSTS": [host],
        "CSRF_TRUSTED_ORIGINS": [proxy_host],
        "DEBUG": False,
        "GUEST_ENABLED": False,
        "NEW_ACCOUNT_REGISTRATION_ENABLED": registration == "1",
        # Loopback listeners provide the ingress boundary; LOCKDOWN_MODE
        # should not block real remote sessions through the reverse proxy.
        "LOCKDOWN_MODE": False,
        "TELNET_ENABLED": True,
        "TELNET_INTERFACES": ["127.0.0.1"],
        "WEBSERVER_INTERFACES": ["127.0.0.1"],
        "WEBSOCKET_CLIENT_INTERFACE": "127.0.0.1",
        "WEBSOCKET_CLIENT_URL": websocket,
        "UPSTREAM_IPS": ["127.0.0.1"],
        "SECURE_PROXY_SSL_HEADER": ("HTTP_X_FORWARDED_PROTO", "https"),
        "USE_X_FORWARDED_HOST": False,
        "SESSION_COOKIE_SECURE": True,
        "CSRF_COOKIE_SECURE": True,
        "SECURE_SSL_REDIRECT": True,
        "SECURE_HSTS_SECONDS": 3600,
        "SECURE_HSTS_INCLUDE_SUBDOMAINS": False,
        "SECURE_HSTS_PRELOAD": False,
    }
