"""Deterministic external-protocol tests, with NO game-code test hooks.

A fake ordinary telnet peer exercises client logic without starting a
multiplayer soak or connecting any real AI players to a host.
"""

from __future__ import annotations

import importlib.util
import json
import os
from pathlib import Path
import tempfile
import threading
import unittest


ROOT = Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location(
    "headless_ai_client", ROOT / "ops" / "headless_ai_client.py"
)
client = importlib.util.module_from_spec(spec)
import sys
sys.modules[spec.name] = client
spec.loader.exec_module(client)


class FakeTransport:
    """A threaded stand-in for the public wire protocol, not game internals."""

    lock = threading.RLock()
    states = {}
    created = 0
    connections = 0

    @classmethod
    def reset(cls):
        with cls.lock:
            cls.states = {}
            cls.created = 0
            cls.connections = 0

    def __init__(self, host, port, *, tls, timeout):
        self.username = None
        self.active = True
        with self.lock:
            type(self).connections += 1

    def read(self):
        return "Frankenstein Village. connect <username> <password>"

    def send(self, raw):
        words = raw.split()
        verb = words[0]
        with self.lock:
            if verb == "connect":
                self.username = words[1]
                state = self.states.setdefault(
                    self.username,
                    {"room": "Private Room", "made": False,
                     "spoons": 0, "whittle": 0, "consent": False},
                )
                return f"Connected to account {self.username}", 1.0
            state = self.states[self.username]
            if verb == "agentlogin":
                return self.agent({"schema": "fvillage.agent_login.v1",
                                   "side": "account_ooc",
                                   "disclosure_declared": state["consent"]}), 1.0
            if verb == "substrate":
                state["consent"] = True
                return "The disclosure gate is open", 1.0
            if verb == "ic":
                return (
                    state["room"] if state["made"] else "No character of that name",
                    1.0,
                )
            if verb == "charcreate":
                state["made"] = True
                type(self).created += 1
                return "Character Created", 1.0
            if verb == "agent":
                if not state["made"]:
                    return "Agent command not available", 1.0
                room = state["room"]
                exits = {
                    "Private Room": ["down"], "Inn Common Room": ["east"],
                    "Inn Hallway": ["south"], "Village Square": ["east"],
                    "The Blood of the Vine": ["west"],
                }[room]
                side = "ooc" if room.startswith("Inn ") or room == "Private Room" else "ic"
                return self.agent({
                    "schema": "fvillage.agent_context.v1", "side": side,
                    "location": room, "exits": exits,
                }), 1.0
            if verb in ("down", "east", "south", "west"):
                routes = {
                    ("Private Room", "down"): "Inn Common Room",
                    ("Inn Common Room", "east"): "Inn Hallway",
                    ("Inn Hallway", "south"): "Village Square",
                    ("Village Square", "east"): "The Blood of the Vine",
                    ("The Blood of the Vine", "west"): "Village Square",
                }
                state["room"] = routes[(state["room"], verb)]
                return state["room"], 1.0
            if raw == "talk M.":
                return 'M. looks up: "The register keeps the debts. You keep the stories."', 1.0
            if raw == "talk Bram":
                return 'Bram: "Everyone owes the village a second evening."', 1.0
            if raw == "whittle spoon":
                if state["whittle"] == 0:
                    state["whittle"] = 1
                    return "You take a stick and begin to carve a wooden spoon.", 1.0
            if raw == "whittle":
                if state["whittle"] >= 1:
                    state["whittle"] += 1
                    if state["whittle"] == 3:
                        state["whittle"] = 0
                        state["spoons"] += 1
                        return "You hold up a finished wooden spoon.", 1.0
                return "Wood curls beneath your knife.", 1.0
            if verb == "inventory":
                return (
                    "You are carrying:\n" +
                    "\n".join("a rough wooden spoon" for _ in range(state["spoons"])),
                    1.0,
                )
            if verb in ("look", "roll", "rumors"):
                return "The room and its neighbors go about their day.", 1.0
            return "Unknown command", 1.0

    @staticmethod
    def agent(data):
        return "FV_AGENT_JSON " + json.dumps({
            "version": 1, **data,
        }, separators=(",", ":"))

    def drop(self):
        self.active = False

    def close(self):
        self.active = False


class HeadlessClientTests(unittest.TestCase):
    def setUp(self):
        FakeTransport.reset()

    def test_independent_accounts_recover_without_duplicate_items(self):
        accounts = [
            client.Account("alpha_bot", "AlphaMask", "secretA"),
            client.Account("beta_bot", "BetaMask", "secretB"),
        ]
        result = client.run_sessions(
            accounts, host="127.0.0.1", port=4000, tls=False, timeout=1.0,
            seed=42, steps=3, recover_index=0, factory=FakeTransport,
        )
        self.assertEqual(len(result), 2)
        self.assertTrue(all(x["connect_success"] and not x["error"] for x in result))
        self.assertTrue(result[0]["relogin_recovered"])
        self.assertEqual(result[0]["disconnects"], 1)
        self.assertEqual(result[0]["connect_attempts"], 2)
        self.assertEqual(result[1]["connect_attempts"], 1)
        self.assertIn("The Blood of the Vine", result[0]["visited"])
        self.assertTrue(result[0]["quotable"])
        self.assertEqual(FakeTransport.states["alpha_bot"]["spoons"], 1)
        self.assertEqual(FakeTransport.states["beta_bot"]["spoons"], 0)
        self.assertEqual(FakeTransport.created, 2)
        self.assertEqual(FakeTransport.connections, 3)
        self.assertGreater(result[0]["commands"], 10)
        self.assertIsNotNone(result[0]["latency_ms_p95"])

    def test_same_seed_is_reproducible_with_independent_sessions(self):
        accounts = [
            client.Account("test_bot", "TestMask", "secretA"),
        ]
        first = client.run_sessions(
            accounts, host="localhost", port=4000, tls=False,
            timeout=1, seed=101, steps=5, factory=FakeTransport,
        )
        FakeTransport.reset()
        second = client.run_sessions(
            accounts, host="localhost", port=4000, tls=False,
            timeout=1, seed=101, steps=5, factory=FakeTransport,
        )
        self.assertEqual(first[0]["commands"], second[0]["commands"])
        self.assertEqual(first[0]["visited"], second[0]["visited"])

    def test_distinct_credentials_and_public_tls_policy(self):
        account = client.Account("test_bot", "TestMask", "testsecret")
        with self.assertRaisesRegex(ValueError, "unique accounts"):
            client.run_sessions(
                [account, account], host="localhost", port=4000,
                tls=False, timeout=1, seed=1, steps=1, factory=FakeTransport,
            )
        with self.assertRaisesRegex(ValueError, "need TLS"):
            client.run_sessions(
                [account], host="example.org", port=4000,
                tls=False, timeout=1, seed=1, steps=1, factory=FakeTransport,
            )

    def test_telnet_transport_negotiates_options_without_exposing_passwords(self):
        import socket

        listener = socket.socket()
        listener.bind(("127.0.0.1", 0))
        listener.listen(1)
        port = listener.getsockname()[1]

        def peer():
            try:
                with listener.accept()[0] as conn:
                    conn.settimeout(3)
                    conn.sendall(bytes((255, 251, 1)) + b"Frankenstein Village\r\n")
                    buffer = bytearray()
                    while b"look\n" not in buffer:
                        block = conn.recv(1024)
                        if not block:
                            break
                        buffer.extend(block)
                    conn.sendall(b"The village square remains foggy.\r\n")
            finally:
                listener.close()

        worker = threading.Thread(target=peer, daemon=True)
        worker.start()
        wire = client.Transport("127.0.0.1", port, tls=False, timeout=3)
        try:
            self.assertIn("Frankenstein Village", wire.read())
            text, elapsed = wire.send("look")
            self.assertIn("square remains foggy", text)
            self.assertGreaterEqual(elapsed, 0)
        finally:
            wire.close()
            worker.join(3)
        self.assertFalse(worker.is_alive())

    def test_credentials_only_from_environment(self):
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp) / "accounts.json"
            p.write_text(json.dumps([
                {"username": "test_bot", "character": "TestMask",
                 "password_env": "FV_TEST_AI_CLIENT_PASSWORD"}
            ]))
            key = "FV_TEST_AI_CLIENT_PASSWORD"
            before = os.environ.get(key)
            try:
                os.environ[key] = "secretA"
                accounts = client.load_accounts(p, 1)
                self.assertEqual(accounts[0].password, "secretA")
                self.assertNotIn("secretA", repr(accounts[0]))
            finally:
                if before is None:
                    os.environ.pop(key, None)
                else:
                    os.environ[key] = before


if __name__ == "__main__":
    unittest.main()
