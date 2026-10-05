#!/usr/bin/env python3
"""Player-level telnet regression path for the Frankenstein Village spike."""

from __future__ import annotations

import argparse
import re
import socket
import time


ANSI = re.compile(r"\x1b\[[0-?]*[ -/]*[@-~]")


def clean(data: bytes) -> str:
    text = data.decode("utf-8", errors="ignore")
    text = ANSI.sub("", text)
    return "".join(
        ch for ch in text
        if ch in "\n\r\t" or ord(ch) >= 32
    )


class Client:
    def __init__(self, host: str, port: int):
        self.sock = socket.create_connection((host, port), timeout=5)
        self.sock.settimeout(0.15)
        self.transcript = []

    def read_quiet(self, max_wait: float = 2.5, quiet: float = 0.35) -> str:
        deadline = time.monotonic() + max_wait
        last_data = time.monotonic()
        chunks = []
        while time.monotonic() < deadline:
            try:
                chunk = self.sock.recv(65536)
                if not chunk:
                    break
                chunks.append(chunk)
                last_data = time.monotonic()
            except socket.timeout:
                if chunks and time.monotonic() - last_data >= quiet:
                    break
        out = clean(b"".join(chunks))
        if out:
            self.transcript.append(out)
            print(out)
        return out

    def command(self, line: str, *, wait: float = 2.5) -> str:
        print(f"\n> {line}")
        self.sock.sendall(line.encode("utf-8") + b"\n")
        return self.read_quiet(max_wait=wait)

    def sync_login_screen(self) -> str:
        """Wait for Evennia's connection screen before sending credentials."""
        deadline = time.monotonic() + 6.0
        gathered = []
        poked = False
        while time.monotonic() < deadline:
            out = self.read_quiet(max_wait=1.0, quiet=0.25)
            if out:
                gathered.append(out)
            joined = "\n".join(gathered)
            if "Frankenstein Village" in joined and "connect <username>" in joined:
                return joined
            if not poked:
                self.sock.sendall(b"look\n")
                poked = True
        return "\n".join(gathered)

    def close(self):
        self.sock.close()


def require(text: str, *needles: str) -> None:
    low = text.lower()
    if not any(needle.lower() in low for needle in needles):
        raise AssertionError(
            "expected one of "
            + repr(needles)
            + " in output, got:\n"
            + text[-3000:]
        )


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--host", required=True)
    parser.add_argument("--port", type=int, required=True)
    parser.add_argument("--username", required=True)
    parser.add_argument("--password", required=True)
    args = parser.parse_args()

    c = Client(args.host, args.port)
    try:
        banner = c.sync_login_screen()
        require(banner, "frankenstein village")

        out = c.command(f"connect {args.username} {args.password}", wait=4.0)
        require(out, "disclosure gate", "substrate human", "substrate ai")

        out = c.command("substrate ai")
        require(out, "gate is open", "substrate recorded")

        c.command("charcreate SmokeTester", wait=3.0)
        out = c.command("ic SmokeTester", wait=4.0)
        require(out, "private room")

        out = c.command("chronicle")
        require(out, "in-character village record", "cross the front door")

        out = c.command("down")
        require(out, "inn common room")

        out = c.command("talk M.")
        require(out, "m. says", "m. leans", "m. looks")

        out = c.command("east")
        require(out, "inn hallway")

        out = c.command("south")
        require(out, "village square")

        # Canon incident #6 is discovered through the physical world, not a
        # quest marker. Evidence remains mask-specific until somebody makes a
        # shared door-closing choice.
        out = c.command("west")
        require(out, "st. lazarus church")

        out = c.command("look strongbox")
        require(out, "open beneath the vestry table", "lock is not forced")

        out = c.command("journal strongbox")
        require(out, "tithe strongbox", "unforced lock")
        if "tithe roll" in out.lower():
            raise AssertionError("journal leaked undiscovered documentary evidence")

        out = c.command("read tithe roll")
        require(out, "balanced through the previous evening", "not an accounting error")

        out = c.command("journal strongbox")
        require(out, "unforced lock", "tithe roll", "decide strongbox")

        out = c.command("east")
        require(out, "village square")

        # A generic background resident uses the same player-facing interface
        # as authored NPCs. Miklós is scheduled in the square at this hour, so
        # the network playtest follows world state instead of teleporting a QA
        # subject into place.
        first_miklos = c.command("talk Miklós Farkas")
        require(first_miklos, "miklós farkas says", "work as lamplighter")
        last_miklos = first_miklos
        for _ in range(7):
            last_miklos = c.command("talk Miklós Farkas")
        require(last_miklos, "back again")

        out = c.command("ask Miklós Farkas about interests")
        require(out, "weakness for")
        out = c.command("ask Miklós Farkas about history")
        require(out, "since you keep asking")

        out = c.command("east")
        require(out, "blood of the vine")

        out = c.command("ask Father Andrei about the strongbox")
        require(out, "key was hanging where it belongs", "will not turn every")

        out = c.command("journal strongbox")
        require(out, "father andrei", "tithe roll", "unforced lock")

        out = c.command("decide strongbox openly", wait=3.0)
        require(out, "accusation is now public", "quiet road is closed")

        out = c.command("journal strongbox")
        require(out, "aftermath", "two keys")

        out = c.command("harbinger")
        require(out, "special edition", "church strongbox loss made public")

        out = c.command("chronicle")
        require(out, "church strongbox loss made public", "verified")

        out = c.command("purse")
        require(out, "2 ft")

        out = c.command("rumors")
        require(out, "confessional")
        require(out, "well steams")
        require(out, "arrivals register", "register")
        handles = re.findall(r"\[R(\d+)\]", out)
        if not handles:
            raise AssertionError("rumor output did not expose a retellable handle")
        rumor_id = handles[0]

        out = c.command(f"rumors R{rumor_id}")
        require(out, "telling trail", "reconstructable")
        require(out, "retell it with")

        out = c.command(f"retell Bram R{rumor_id}")
        require(out, "you tell bram")

        out = c.command("roll dice vs Bram")
        require(out, "dice settle")
        if "0 kr" in out:
            raise AssertionError("a real wager paid zero coin")

        out = c.command("look register")
        require(out, "last michaelmas")
        require(out, "rm 6")

        out = c.command("north")
        require(out, "tavern back hall")

        out = c.command("look room six door")
        require(out, "folded note")

        out = c.command("take note")
        require(out, "before anyone else can")

        out = c.command("south")
        require(out, "blood of the vine")

        out = c.command("drop note", wait=3.0)
        require(out, "pins the note behind", "pinned behind")

        out = c.command("harbinger")
        require(out, "special edition", "folded note posted")
        story_match = re.search(r"\[H(\d+)\].*Folded Note", out, re.I)
        if not story_match:
            raise AssertionError("Room Six special edition had no stable H handle")
        story_id = story_match.group(1)

        out = c.command(f"harbinger H{story_id}")
        require(out, "filed from a recorded event")
        require(out, "folded note")

        out = c.command("chronicle")
        require(out, "public chronicle index")
        require(out, "folded note", "verified")

        out = c.command("rumors")
        require(out, "room six behind the tavern")
        room_six_rumor_id = None
        for match in re.finditer(r"\[R(\d+)\]\s+([^\n]+)", out, re.I):
            if "room six" in match.group(2).lower():
                room_six_rumor_id = match.group(1)
                break
        if not room_six_rumor_id:
            raise AssertionError("Room Six rumor had no provenance handle")

        out = c.command(f"chronicle submit R{room_six_rumor_id}")
        require(out, "the record preserves that you said it")
        require(out, "does not certify", "not certify")

        out = c.command("chronicle")
        require(out, "deposition from smoketester")
        require(out, "account")

        out = c.command("west")
        require(out, "village square")
        out = c.command("north")
        require(out, "inn hallway")
        out = c.command("west")
        require(out, "inn common room")

        out = c.command("talk M.")
        require(out, "my register", "reading my register aloud")

        out = c.command("up")
        require(out, "private room")

        print("\nTELNET_PLAYTHROUGH_GREEN")
        return 0
    except Exception:
        print("\nFULL TRANSCRIPT\n" + "\n".join(c.transcript))
        raise
    finally:
        c.close()


if __name__ == "__main__":
    raise SystemExit(main())
