"""Fail-closed public deployment profile, exercised without Evennia."""

from __future__ import annotations

import importlib.util
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[2]
MODULE = (
    ROOT / "spike" / "fvillage" / "server" / "conf" / "deployment_profile.py"
)
spec = importlib.util.spec_from_file_location("fv_deployment_profile", MODULE)
profile = importlib.util.module_from_spec(spec)
spec.loader.exec_module(profile)


class DeploymentProfileTests(unittest.TestCase):
    def test_local_development_has_no_forced_overrides(self):
        self.assertEqual(profile.public_profile({}), {})
        self.assertEqual(
            profile.public_profile({"FV_DEPLOYMENT_MODE": "development"}), {}
        )

    def test_public_is_secure_and_host_bound(self):
        settings = profile.public_profile({
            "FV_DEPLOYMENT_MODE": "public",
            "FV_PUBLIC_HOST": "Village.Example.org",
            "WEBCLIENT_CLIENT_PROXY_PORT": "4042",
        })
        self.assertEqual(settings["SERVER_HOSTNAME"], "village.example.org")
        self.assertEqual(settings["ALLOWED_HOSTS"], ["village.example.org"])
        self.assertEqual(
            settings["WEBSOCKET_CLIENT_URL"], "wss://village.example.org"
        )
        self.assertEqual(
            settings["CSRF_TRUSTED_ORIGINS"], ["https://village.example.org"]
        )
        self.assertEqual(settings["TELNET_INTERFACES"], ["127.0.0.1"])
        self.assertEqual(settings["WEBSERVER_INTERFACES"], ["127.0.0.1"])
        self.assertEqual(settings["WEBSOCKET_CLIENT_INTERFACE"], "127.0.0.1")
        self.assertFalse(settings["LOCKDOWN_MODE"])
        self.assertTrue(settings["SECURE_SSL_REDIRECT"])
        self.assertTrue(settings["SESSION_COOKIE_SECURE"])
        self.assertTrue(settings["CSRF_COOKIE_SECURE"])
        self.assertFalse(settings["DEBUG"])
        self.assertFalse(settings["GUEST_ENABLED"])
        self.assertFalse(settings["NEW_ACCOUNT_REGISTRATION_ENABLED"])
        self.assertNotIn("*", settings["ALLOWED_HOSTS"])

    def test_explicit_public_registration_opt_in(self):
        settings = profile.public_profile({
            "FV_DEPLOYMENT_MODE": "public",
            "FV_PUBLIC_HOST": "village.example.org",
            "WEBCLIENT_CLIENT_PROXY_PORT": "4042",
            "FV_PUBLIC_REGISTRATION": "1",
        })
        self.assertTrue(settings["NEW_ACCOUNT_REGISTRATION_ENABLED"])

    def test_missing_wss_proxy_port_blocks_public_startup(self):
        with self.assertRaisesRegex(
            profile.DeploymentConfigurationError, "WEBCLIENT_CLIENT_PROXY_PORT"
        ):
            profile.public_profile({
                "FV_DEPLOYMENT_MODE": "public",
                "FV_PUBLIC_HOST": "village.example.org",
            })

    def test_insecure_or_ambiguous_configuration_fails(self):
        bad_cases = [
            {"FV_DEPLOYMENT_MODE": "publc", "FV_PUBLIC_HOST": "village.example.org"},
            {"FV_DEPLOYMENT_MODE": "public"},
            {"FV_DEPLOYMENT_MODE": "public", "FV_PUBLIC_HOST": "localhost"},
            {"FV_DEPLOYMENT_MODE": "public", "FV_PUBLIC_HOST": "127.0.0.1"},
            {"FV_DEPLOYMENT_MODE": "public", "FV_PUBLIC_HOST": "village.localhost"},
            {"FV_DEPLOYMENT_MODE": "public", "FV_PUBLIC_HOST": "*.example.org"},
            {"FV_DEPLOYMENT_MODE": "public", "FV_PUBLIC_HOST": "http://example.org"},
            {"FV_DEPLOYMENT_MODE": "public", "FV_PUBLIC_HOST": "example.org:443"},
            {"FV_DEPLOYMENT_MODE": "public", "FV_PUBLIC_HOST": "a..org"},
            {"FV_DEPLOYMENT_MODE": "public", "FV_PUBLIC_HOST": "-a.example.org"},
            {"FV_DEPLOYMENT_MODE": "public", "FV_PUBLIC_HOST": "example.org/path"},
            {
                "FV_DEPLOYMENT_MODE": "public",
                "FV_PUBLIC_HOST": "example.org",
                "FV_PUBLIC_REGISTRATION": "yes",
            },
        ]
        for config in bad_cases:
            with self.subTest(config=config), self.assertRaises(
                profile.DeploymentConfigurationError
            ):
                profile.public_profile(config)


if __name__ == "__main__":
    unittest.main()
