#!/usr/bin/env python3
"""Ordinary-account AI MUD client and bounded functional probe. NOT a soak test.

Use distinct, operator-controlled accounts. No privileged game verbs, no
special server hooks, no hidden world-state access. Python 3.12+ stdlib only.
"""

from __future__ import annotations

import argparse
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field
import ipaddress
import json
import os
from pathlib import Path
import random
import re
import socket
import ssl
import statistics
import struct
import time

ANSI = re.compile(r"\x1b\[[0-?]*[ -/]*[@-~]")
AGENT_JSON = re.compile(r"FV_AGENT_JSON\s+(\{[^\r\n]+\})")
IAC, WILL, WONT, DO, DONT, SB, SE = 255, 251, 252, 253, 254, 250, 240


def is_loopback(host):
    if host.lower() == "localhost":
        return True
    try:
        return ipaddress.ip_address(host).is_loopback
    except ValueError:
        return False


def context_of(text, schema):
    match = AGENT_JSON.search(text)
    if not match:
        raise ValueError("Missing machine-readable agent context")
    data = json.loads(match[1])
    if data.get("version") != 1 or data.get("schema") != schema:
        raise ValueError("Unexpected agent context schema")
    return data


def process_sample(pids):
    """Host-local shared-process observation, not per-account attribution."""
    if not pids:
        return None
    observed = {}
    for pid in pids:
        try:
            fields = Path(f"/proc/{pid}/stat").read_text().rsplit(")", 1)[1].split()
            cpu = (int(fields[11]) + int(fields[12])) / os.sysconf("SC_CLK_TCK")
            status = Path(f"/proc/{pid}/status").read_text()
            rss = re.search(r"^VmRSS:\s+(\d+)", status, re.M)
            observed[str(pid)] = [cpu, int(rss[1]) if rss else None]
        except (OSError, ValueError, IndexError):
            observed[str(pid)] = None
    return observed


def process_delta(before, after):
    if before is None or after is None:
        return {"available": False, "reason": "No local server PIDs supplied"}
    out = {}
    for pid, previous in before.items():
        current = after.get(pid)
        out[pid] = (
            {"cpu_seconds_delta": round(max(0, current[0] - previous[0]), 4),
             "rss_kib_start": previous[1], "rss_kib_end": current[1]}
            if previous and current else None
        )
    return {"available": True,
            "scope": "Shared server-process observation window, not isolated per-client CPU",
            "processes": out}


class Transport:
    """Tiny telnet option filter supporting TLS and bounded text responses."""

    def __init__(self, host, port, *, tls, timeout):
        if not tls and not is_loopback(host):
            raise ValueError("Remote telnet requires certificate-validated TLS")
        self.timeout = timeout
        sock = socket.create_connection((host, port), timeout=timeout)
        try:
            self.sock = ssl.create_default_context().wrap_socket(
                sock, server_hostname=host
            ) if tls else sock
        except Exception:
            sock.close()
            raise
        self.sock.settimeout(0.25)
        self.state = "text"
        self.option = None

    def _telnet_text(self, raw):
        data = bytearray()
        for byte in raw:
            if self.state == "text":
                if byte == IAC:
                    self.state = "iac"
                else:
                    data.append(byte)
            elif self.state == "iac":
                if byte == IAC:
                    data.append(byte)
                    self.state = "text"
                elif byte in (WILL, WONT, DO, DONT):
                    self.option = byte
                    self.state = "option"
                else:
                    self.state = "sub" if byte == SB else "text"
            elif self.state == "option":
                if self.option == DO:
                    self.sock.sendall(bytes((IAC, WONT, byte)))
                if self.option == WILL:
                    self.sock.sendall(bytes((IAC, DONT, byte)))
                self.state = "text"
            elif self.state == "sub":
                if byte == IAC:
                    self.state = "sub_iac"
            else:
                self.state = "text" if byte == SE else "sub"
        return bytes(data)

    def read(self):
        buffer = bytearray()
        end = time.monotonic() + self.timeout
        seen_at = None
        while time.monotonic() < end:
            try:
                raw = self.sock.recv(65536)
            except socket.timeout:
                if seen_at is not None and time.monotonic() - seen_at > 0.3:
                    break
                continue
            if not raw:
                if not buffer:
                    raise ConnectionError("Telnet connection closed")
                break
            payload = self._telnet_text(raw)
            if payload:
                buffer.extend(payload)
                seen_at = time.monotonic()
            if len(buffer) > 131072:
                raise ValueError("Oversized game response")
        if not buffer:
            raise TimeoutError("Game command did not answer")
        return ANSI.sub("", buffer.decode("utf-8", "replace")).replace("\r", "")

    def send(self, command):
        if "\r" in command or "\n" in command:
            raise ValueError("Multiline command is not permitted")
        start = time.monotonic()
        self.sock.sendall(command.encode() + b"\n")
        return self.read(), round((time.monotonic() - start) * 1000, 2)

    def drop(self):
        """Abrupt disconnect, preserving all work solely on the server."""
        try:
            self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_LINGER,
                                 struct.pack("ii", 1, 0))
        finally:
            self.sock.close()

    def close(self):
        self.sock.close()


@dataclass(frozen=True)
class Account:
    username: str
    character: str
    password: str = field(repr=False)

    def __post_init__(self):
        for label, value in (("username", self.username), ("character", self.character)):
            if not re.fullmatch(r"[A-Za-z0-9_-]{3,32}", value):
                raise ValueError(f"Invalid {label}, use a simple 3-32 character token")
        if not self.password or any(ch.isspace() for ch in self.password):
            raise ValueError("Password must be a nonempty, single command token")


def load_accounts(path, count):
    entries = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(entries, list) or not 1 <= count <= len(entries):
        raise ValueError("Insufficient configured independent accounts")
    chosen = entries[:count]
    if len({item["username"] for item in chosen}) != count:
        raise ValueError("Each concurrent session must use a DISTINCT account")
    accounts = []
    for item in chosen:
        secret = os.environ.get(item["password_env"])
        if secret is None:
            raise ValueError("Missing secret environment variable: " + item["password_env"])
        accounts.append(Account(item["username"], item["character"], secret))
    return accounts


def quote_from(text):
    for line in text.splitlines():
        line = line.strip()
        if 20 <= len(line) <= 220 and not line.startswith("[MudInfo]"):
            return line
    return ""


def spoons(text):
    """Count the physical crafted object in a plain inventory response."""
    return len(re.findall(r"\bwooden spoon\b", text, re.I))


class Player:
    def __init__(self, account, *, host, port, tls, timeout, seed, steps, pids=(),
                 factory=Transport):
        self.account = account
        self.host, self.port, self.tls, self.timeout = host, port, tls, timeout
        self.factory, self.steps, self.pids = factory, steps, tuple(pids)
        self.rng = random.Random(seed)
        self.session = None
        self.lags = []
        self.commands = 0
        self.connect_attempts = 0
        self.disconnections = 0
        self.quotable = ""
        self.rooms = set()

    def cmd(self, line):
        output, latency = self.session.send(line)
        self.commands += 1
        self.lags.append(latency)
        return output

    def login(self, *, returning=False):
        self.connect_attempts += 1
        self.session = self.factory(self.host, self.port, tls=self.tls,
                                    timeout=self.timeout)
        self.session.read()
        response = self.cmd(
            f"connect {self.account.username} {self.account.password}"
        )
        if "connected" not in response.lower():
            raise RuntimeError("Login rejected")
        lobby = context_of(self.cmd("agentlogin"), "fvillage.agent_login.v1")
        if not lobby.get("disclosure_declared"):
            if returning or "gate is open" not in self.cmd("substrate ai").lower():
                raise RuntimeError("Disclosure consent gate not satisfied")
        self.cmd(f"ic {self.account.character}")
        # IC gives different descriptions for a fresh Private Room and a
        # returning Tavern player. Trust agent context, not brittle prose.
        try:
            state = context_of(self.cmd("agent"), "fvillage.agent_context.v1")
        except ValueError:
            if returning:
                raise RuntimeError("Returning mask cannot be re-entered")
            # Normal account commands, never direct database creation.
            created = self.cmd(f"charcreate {self.account.character}")
            if "created" not in created.lower():
                raise RuntimeError("Character creation failed")
            self.cmd(f"ic {self.account.character}")
            state = context_of(self.cmd("agent"), "fvillage.agent_context.v1")
        if state["side"] not in ("ic", "ooc"):
            raise RuntimeError("Character never entered a valid OOC/IC state")
        return state

    def move(self, state, direction):
        if direction not in state.get("exits", []):
            raise RuntimeError(f"Cannot traverse undisclosed exit: {direction}")
        self.cmd(direction)
        state = context_of(self.cmd("agent"), "fvillage.agent_context.v1")
        self.rooms.add(state.get("location"))
        return state

    def arrive(self, state):
        """Ordinary arrival: private room, M., front door, shared Tavern."""
        for _ in range(8):
            place, side = state.get("location"), state.get("side")
            self.rooms.add(place)
            if side == "ic" and place == "The Blood of the Vine":
                return state
            if side == "ooc" and "Private Room" in str(place):
                state = self.move(state, "down")
            elif side == "ooc" and place == "Inn Common Room":
                response = self.cmd("talk M.")
                self.quotable = self.quotable or quote_from(response)
                state = self.move(state, "east")
            elif side == "ooc" and place == "Inn Hallway":
                state = self.move(state, "south")
            elif side == "ic" and place == "Village Square":
                state = self.move(state, "east")
            elif side == "ic" and "west" in state.get("exits", []):
                state = self.move(state, "west")
            else:
                raise RuntimeError(f"Unreachable first-session social loop at {place}")
        raise RuntimeError("Arrival exceeded eight moves")

    def random_loop(self, state):
        self.cmd("look")
        words = self.cmd("talk Bram")
        self.quotable = self.quotable or quote_from(words)
        # Avoid whittling here: the interruption test exclusively owns
        # three crafting steps, preventing random actions from duplicating it.
        for _ in range(self.steps):
            self.cmd(self.rng.choice(
                ("look", "talk Bram", "roll dice", "rumors", "look dice cup")
            ))
        state = self.move(state, "west")
        self.cmd("look")
        return self.move(state, "east")

    def reconnect_recovery(self, state):
        """One forced connection loss, one resumed craft, zero duplicate items."""
        if state.get("location") != "The Blood of the Vine":
            raise RuntimeError("Recovery check must happen at shared Tavern")
        beginning = self.cmd("whittle spoon")
        if not any(token in beginning.lower() for token in ("whittle", "carv", "stick")):
            raise RuntimeError("Could not begin a new piece of whittling")
        before = spoons(self.cmd("inventory"))
        self.session.drop()
        self.disconnections += 1
        self.session = None
        time.sleep(0.4)
        reentered = self.login(returning=True)
        if reentered.get("location") != state.get("location"):
            raise RuntimeError("Existing mask location lost across disconnection")
        if spoons(self.cmd("inventory")) != before:
            raise RuntimeError("Inventory changed during abrupt disconnect")
        self.cmd("whittle")
        self.cmd("whittle")
        after = spoons(self.cmd("inventory"))
        if after != before + 1:
            raise RuntimeError(
                f"Expected one crafted spoon after recovery, got {after - before}"
            )
        self.cmd("look")
        if spoons(self.cmd("inventory")) != after:
            raise RuntimeError("Craft inventory duplicated without an action")
        return reentered

    def run(self, recovery=False):
        started = time.monotonic()
        before = process_sample(self.pids)
        err = None
        recovery_ok = None
        connected = False
        try:
            state = self.login()
            connected = True
            state = self.arrive(state)
            if recovery:
                state = self.reconnect_recovery(state)
                recovery_ok = True
            self.random_loop(state)
        except Exception as exc:
            err = type(exc).__name__ + ": " + str(exc)
            if recovery and recovery_ok is None:
                recovery_ok = False
        finally:
            if self.session is not None:
                self.session.close()
            after = process_sample(self.pids)
        sorted_lags = sorted(self.lags)
        p95_index = max(0, (95 * len(sorted_lags) + 99) // 100 - 1)
        return {
            "account": self.account.username, "character": self.account.character,
            "connect_success": connected, "connect_attempts": self.connect_attempts,
            "connect_failures": int(not connected), "commands": self.commands,
            "latency_ms_p50": round(statistics.median(sorted_lags), 2) if sorted_lags else None,
            "latency_ms_p95": sorted_lags[p95_index] if sorted_lags else None,
            "latency_ms_max": sorted_lags[-1] if sorted_lags else None,
            "disconnects": self.disconnections,
            "relogin_recovered": recovery_ok,
            "resource_metrics": process_delta(before, after),
            "duration_s": round(time.monotonic() - started, 2),
            "visited": sorted(self.rooms), "quotable": self.quotable,
            "error": err,
        }


def run_sessions(accounts, *, host, port, tls, timeout, seed, steps,
                 pids=(), recover_index=None, factory=Transport):
    if not tls and not is_loopback(host):
        raise ValueError("Remote connections need TLS")
    if len(set(a.username for a in accounts)) != len(accounts):
        raise ValueError("Concurrent sessions must use unique accounts")
    if recover_index is not None and not 0 <= recover_index < len(accounts):
        raise ValueError("Recovery index is out of range")
    with ThreadPoolExecutor(max_workers=len(accounts)) as pool:
        pending = [
            pool.submit(
                Player(
                    account, host=host, port=port, tls=tls, timeout=timeout,
                    seed=seed + i * 1009, steps=steps, pids=pids, factory=factory
                ).run,
                recovery=(i == recover_index),
            )
            for i, account in enumerate(accounts)
        ]
        return [job.result() for job in pending]


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--host", required=True)
    parser.add_argument("--port", type=int, default=4040)
    parser.add_argument("--tls", action="store_true")
    parser.add_argument("--accounts", type=Path, required=True)
    parser.add_argument("--sessions", type=int, default=2)
    parser.add_argument("--seed", type=int, default=314159)
    parser.add_argument("--steps", type=int, default=6)
    parser.add_argument("--timeout", type=float, default=8.0)
    parser.add_argument("--recover-index", type=int, default=None)
    parser.add_argument("--server-pid", action="append", type=int, default=[])
    parser.add_argument("--output", type=Path)
    args = parser.parse_args(argv)
    if not 1 <= args.sessions <= 32 or not 0 <= args.steps <= 100:
        parser.error("Bounded smoke runs only: sessions 1..32, steps 0..100")
    if not 0 < args.timeout <= 30 or not 1 <= args.port <= 65535:
        parser.error("Invalid timeout or TCP port")
    try:
        accounts = load_accounts(args.accounts, args.sessions)
        results = run_sessions(
            accounts, host=args.host, port=args.port, tls=args.tls,
            timeout=args.timeout, steps=args.steps, seed=args.seed,
            pids=tuple(args.server_pid), recover_index=args.recover_index,
        )
    except (OSError, ValueError, KeyError) as exc:
        parser.error(str(exc))
    report = {
        "schema": "fvillage.headless_smoke.v1",
        "kind": "targeted_functional_probe_NOT_MULTIPLAYER_SOAK",
        "host": args.host, "seed": args.seed, "session_count": len(accounts),
        "results": results,
        "passed": all(r["connect_success"] and r["error"] is None for r in results),
    }
    text = json.dumps(report, indent=2, sort_keys=True)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(text + "\n", encoding="utf-8")
    print(text)
    return 0 if report["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
