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

        out = c.command("secrets")
        require(out, "in-character village record", "cross the front door")

        # The public calendar is intentionally available backstage so groups
        # can plan around predictable village rhythms before crossing IC.
        out = c.command("calendar")
        require(out, "village calendar")
        require(out, "harbinger normally appears daily at 08:00")
        require(out, "market morning is saturday")
        require(out, "sunday mass is held at st. lazarus")
        require(out, "seasonal chapter", "weeks of long shadows")

        out = c.command("down")
        require(out, "inn common room")

        out = c.command("talk M.")
        require(out, "m. says", "m. leans", "m. looks")

        out = c.command("east")
        require(out, "inn hallway")

        out = c.command("south")
        require(out, "village square")
        require(out, "one gas lamp", "neighboring lamps burn steadily")
        require(out, "blackout has swallowed", "dark gas standards")
        require(out, "season of long shadows", "fog gathers early")

        out = c.command("event")
        require(out, "the long blackout", "0 of 4", "event lamps")

        out = c.command("event lamps")
        require(out, "street lamps stabilized")

        out = c.command("event")
        require(out, "the long blackout", "1 of 4", "street lamps stabilized")

        # The public Manor mystery is discovered by looking at an object already
        # named in the square, not by accepting a quest or opening a menu.
        out = c.command("look manor")
        require(out, "manor stands above the village", "distance does not supply the answer")

        out = c.command("mystery manor")
        require(out, "why are the manor lights returning", "shared observations")
        require(out, "no metaphysical explanation is certified")

        out = c.command(
            "theory manor = The lights may follow an old maintenance schedule."
        )
        require(out, "provisional public interpretation", "not been certified as truth")

        out = c.command("mystery manor")
        require(out, "provisional theories", "old maintenance schedule")

        # A timed world window is already live. Firsthand evidence is earned by
        # being present during the window and observing the physical world.
        out = c.command("look well")
        require(out, "white vapor", "rope shiver", "slick and warm")

        out = c.command("journal well")
        require(out, "the well boils", "firsthand witness", "live steam surge")
        require(out, "rope trembled")

        out = c.command("journal")
        require(out, "the well boils", "firsthand evidence")

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

        # Private mysteries belong to this exact mask until the player chooses
        # to disclose them. János is here by his ordinary evening schedule.
        out = c.command("ask Janos about Hounds")
        require(out, "hounds keep some things off the bar", "private p1")
        invitation_match = re.search(r"rumor R(\d+)", out, re.I)
        if not invitation_match:
            raise AssertionError("private invitation exposed no rumor handle")
        invitation_rumor_id = invitation_match.group(1)

        out = c.command("secrets")
        require(out, "a private invitation", "invited")
        require(out, f"invitation rumor: r{invitation_rumor_id}")

        out = c.command("ask Janos about east patrol")
        require(out, "three mornings", "same chalk ring", "we do not know")
        followup_match = re.search(r"rumor R(\d+)", out, re.I)
        if not followup_match:
            raise AssertionError("private follow-up exposed no rumor handle")
        private_rumor_id = followup_match.group(1)

        out = c.command(f"rumors R{private_rumor_id}")
        require(out, "chalk ring", "telling trail", "janos")

        out = c.command(f"retell Bram R{private_rumor_id}")
        require(out, "you tell bram", "chalk ring")

        out = c.command("secrets")
        require(out, "opened", "follow-up rumor")
        require(out, "bram")

        out = c.command("journal strongbox")
        require(out, "tithe roll", "unforced lock")

        out = c.command("decide strongbox openly", wait=3.0)
        require(out, "accusation is now public", "quiet road is closed")

        out = c.command("journal strongbox")
        require(out, "aftermath", "two keys")

        out = c.command("harbinger")
        require(out, "special edition", "church strongbox loss made public")

        out = c.command("chronicle")
        require(out, "church strongbox loss made public", "verified")
        require(out, "numbered sequence is missing", "chronicle gap")

        out = c.command("journal chronicle")
        require(out, "nothing about that situation")

        out = c.command("chronicle gap")
        require(out, "cut out cleanly", "numbered run")

        out = c.command("journal chronicle")
        require(out, "numbered page stubs")
        if "surviving harbinger files" in out.lower():
            raise AssertionError(
                "journal leaked undiscovered Harbinger archive evidence"
            )

        out = c.command("harbinger archive")
        require(out, "older bound harbinger files", "newspaper records")

        out = c.command("journal chronicle")
        require(out, "numbered page stubs", "surviving harbinger files")
        require(out, "reconstruct or preserve")

        out = c.command("decide chronicle reconstruct", wait=3.0)
        require(out, "reconstruction from the harbinger archive")
        require(out, "press-derived")

        out = c.command("chronicle gap")
        require(out, "derived from harbinger files")
        require(out, "source difference is not hidden")

        out = c.command("harbinger")
        require(out, "special edition", "missing chronicle sequence reconstructed")

        out = c.command("chronicle")
        require(out, "missing chronicle sequence reconstructed", "verified")

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

        well_rumor_id = None
        for match in re.finditer(r"\[R(\d+)\]\s+([^\n]+)", out, re.I):
            claim = match.group(2).lower()
            if "well" in claim and "steam" in claim:
                well_rumor_id = match.group(1)
                break
        if not well_rumor_id:
            raise AssertionError("well rumor had no public provenance handle")

        out = c.command(f"chronicle compare R{well_rumor_id}")
        require(
            out,
            "conflicting versions survive",
            "old vasile",
            "jános",
            "magda",
        )
        require(out, "no version is certified as truth")

        # Harbinger Section 3.22, Stop the Press: the same incompatible signed
        # accounts become a real editorial decision. Selecting one version
        # changes what the paper will print, but never certifies it as truth.
        out = c.command(f"harbinger desk R{well_rumor_id}")
        require(
            out,
            "editorial status: open",
            "old vasile",
            "jános",
            "magda",
            "not certified",
        )
        stop_press_match = re.search(r"STP(\d+)", out, re.I)
        vasile_deposition = re.search(r"D(\d+)\s+Old Vasile:", out, re.I)
        if not stop_press_match or not vasile_deposition:
            raise AssertionError(
                "Stop the Press did not expose stable editorial/deposition handles"
            )
        stop_press_id = stop_press_match.group(1)
        deposition_id = vasile_deposition.group(1)

        out = c.command(
            f"harbinger choose STP{stop_press_id} D{deposition_id}"
        )
        require(
            out,
            "is closed",
            "will be printed",
            "other signed accounts remain on record",
            "not certified as fact",
        )

        out = c.command(f"harbinger desk STP{stop_press_id}")
        require(out, "editorial status: selected", "queued harbinger h")

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
