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
    h = None
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

        # Calling foundation: a mask can choose a social profession before
        # crossing IC. Selection begins at Apprentice and exposes no free
        # promotion command or combat power.
        out = c.command("calling")
        require(out, "no active calling")
        out = c.command("calling list")
        require(out, "chronicler")
        require(out, "hound")
        require(out, "social professions")
        out = c.command("calling choose chronicler")
        require(out, "chronicler is now your active calling")
        require(out, "apprentice rank")
        require(out, "later respecialization requires an authored opportunity")
        out = c.command("calling")
        require(out, "active calling: chronicler")
        require(out, "rank: apprentice")
        require(out, "no professional participation")

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

        # Systemic object foundation: the ordinary eat verb now reads the
        # bread's worth and uses properties. The player-facing behavior stays
        # natural while the underlying rule is object data rather than item ID.
        out = c.command("purse")
        require(out, "2 ft")
        out = c.command("eat bread")
        require(out, "4 kr", "purse: 1 ft 96 kr")
        out = c.command("purse")
        require(out, "1 ft 96 kr")

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
        strongbox_story_match = re.search(
            r"\[H(\d+)\]\s+Church Strongbox Loss Made Public",
            out,
            re.I,
        )
        if not strongbox_story_match:
            raise AssertionError(
                "strongbox Harbinger story exposed no stable public handle"
            )
        strongbox_story_id = strongbox_story_match.group(1)

        # Harbinger Section 3.22, The Correction: file a correction claiming
        # prior wording that the surviving archive copy does not contain.
        missing_wording = "The vestry window was broken before the coins disappeared."
        out = c.command(
            f"harbinger correction H{strongbox_story_id} = {missing_wording}"
        )
        require(
            out,
            "correction dispute cd",
            "surviving copy does not contain",
            "old issue is not rewritten",
            "archive discrepancy",
        )
        correction_dispute_match = re.search(r"CD(\d+)", out, re.I)
        response_story_match = re.search(r"Harbinger H(\d+)", out, re.I)
        if not correction_dispute_match or not response_story_match:
            raise AssertionError(
                "The Correction exposed no stable dispute/response handles"
            )
        correction_dispute_id = correction_dispute_match.group(1)
        correction_response_story_id = response_story_match.group(1)

        out = c.command(f"harbinger H{strongbox_story_id}")
        require(
            out,
            f"disputed correction cd{correction_dispute_id}",
            "claimed prior wording",
            "absent from the surviving copy",
            "archived story remains unchanged",
        )

        out = c.command(
            f"harbinger correction H{strongbox_story_id} = {missing_wording}"
        )
        require(
            out,
            "already preserved",
            "repetition does not alter the surviving copy",
        )

        # Harbinger Section 3.22, Tomorrow's Obituary: submit a death notice
        # for a resident who is currently alive, inspect the editorial dilemma,
        # and choose investigation rather than allowing the notice to become
        # world truth.
        out = c.command("harbinger obituary Miklós Farkas")
        require(
            out,
            "premature obituary tob",
            "still recorded as living and active",
            "copy desk",
        )
        obituary_match = re.search(r"TOB(\d+)", out, re.I)
        if not obituary_match:
            raise AssertionError(
                "Tomorrow's Obituary exposed no stable editorial handle"
            )
        obituary_id = obituary_match.group(1)

        out = c.command(f"harbinger obituary TOB{obituary_id}")
        require(
            out,
            "editorial status: open",
            "recorded as active",
            "print",
            "investigate",
            "suppress",
            "mock",
            "does not change",
        )

        out = c.command(
            f"harbinger obituary TOB{obituary_id} investigate"
        )
        require(
            out,
            "is closed with decision investigate",
            "harbinger h",
            "remains recorded as active",
            "does not alter world truth",
        )
        obituary_story_match = re.search(r"Harbinger H(\d+)", out, re.I)
        if not obituary_story_match:
            raise AssertionError(
                "Tomorrow's Obituary investigation queued no Harbinger story"
            )
        obituary_story_id = obituary_story_match.group(1)

        out = c.command(f"harbinger obituary TOB{obituary_id}")
        require(
            out,
            "editorial status: closed",
            "decision: investigate",
            "lifecycle at decision: active",
            f"harbinger h{obituary_story_id}",
        )

        out = c.command("chronicle")
        require(out, "church strongbox loss made public", "verified")
        require(out, "numbered sequence is missing", "chronicle gap")
        strongbox_entry_match = re.search(
            r"\[C(\d+)\]\s+Church Strongbox Loss Made Public",
            out,
            re.I,
        )
        if not strongbox_entry_match:
            raise AssertionError(
                "strongbox Chronicle entry exposed no stable public handle"
            )
        strongbox_entry_id = strongbox_entry_match.group(1)

        # Chronicler Section 3.23, Revision by Evidence: only evidence this
        # mask actually discovered is offered for an append-only amendment.
        out = c.command(f"chronicle evidence C{strongbox_entry_id}")
        require(
            out,
            "strongbox/lock",
            "strongbox/roll",
            "documentary",
            "does not rewrite the original entry",
        )

        out = c.command(
            f"chronicle revise C{strongbox_entry_id} = strongbox/roll"
        )
        require(
            out,
            "receives annotation",
            "tithe roll",
            "original entry",
            "prior claim status are preserved",
        )

        out = c.command(f"chronicle C{strongbox_entry_id}")
        require(
            out,
            "verified event",
            "evidence submitted by smoketester",
            "tithe roll",
            "evidence source",
            "documentary",
        )

        out = c.command(
            f"chronicle revise C{strongbox_entry_id} = strongbox/roll"
        )
        require(out, "already cited", "does not duplicate")

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
        require(out, "1 ft 96 kr")

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

        # Chronicler Section 3.23, The Refused Entry: petition a popular canon
        # rumor that has no event-backed Chronicle authority. The institution
        # may preserve the refusal while refusing to certify the claim.
        refusal_candidates = []
        for match in re.finditer(r"\[R(\d+)\]\s+([^\n]+)", out, re.I):
            claim = match.group(2).lower()
            if "arrivals register" in claim or "confessional" in claim:
                refusal_candidates.append(match.group(1))
        if not refusal_candidates:
            raise AssertionError("no suitable public rumor was exposed for Refused Entry")

        refusal_out = None
        refused_rumor_id = None
        for candidate in refusal_candidates:
            attempt = c.command(f"chronicle petition R{candidate}")
            if "refuses to canonize" in attempt.lower():
                refusal_out = attempt
                refused_rumor_id = candidate
                break
        if not refusal_out:
            raise AssertionError(
                "no canon rumor met the live Refused Entry popularity threshold"
            )
        require(
            refusal_out,
            "records the refusal itself",
            "not the rumor's truth",
            "residents",
            "affected by the decision",
        )
        refused_entry_match = re.search(r"Chronicle C(\d+)", refusal_out, re.I)
        if not refused_entry_match:
            raise AssertionError("Refused Entry exposed no Chronicle handle")
        refused_entry_id = refused_entry_match.group(1)

        out = c.command(f"chronicle C{refused_entry_id}")
        require(
            out,
            "refused canonization",
            "petition asked the chronicle to canonize",
            "does not certify the rumor as true or false",
        )

        out = c.command(f"chronicle petition R{refused_rumor_id}")
        require(
            out,
            "already refused",
            "preserves that institutional decision",
            "without certifying the underlying claim",
        )

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

        out = c.command("calling")
        require(out, "active calling: chronicler")
        require(out, "evidence revisions 1")
        require(out, "signed accounts 1")

        # Free profession swapping is rejected. Respecialization is supported
        # by the persistent model but must be opened by authored world logic.
        out = c.command("calling choose performer")
        require(out, "established professional history")
        require(out, "authored respecialization opportunity")
        out = c.command("calling history")
        require(out, "joined calling chronicler")
        if "respecialized performer" in out.lower():
            raise AssertionError(
                "player command bypassed the authored respecialization gate"
            )
        out = c.command("calling")
        require(out, "active calling: chronicler")
        require(out, "evidence revisions 1")
        require(out, "signed accounts 1")

        out = c.command("chronicle")
        require(out, "deposition from smoketester")
        require(out, "account")

        out = c.command("west")
        require(out, "village square")

        # Hidden object properties: ordinary look does not label the toxin.
        # Direct consequences teach only this mask, and examine then recalls
        # the learned fact without changing the mushroom's public description.
        out = c.command("look mushrooms")
        require(out, "cluster of pale mushrooms")
        require(out, "grandmother")
        if "toxic" in out.lower():
            raise AssertionError("ordinary look leaked the hidden toxin property")

        out = c.command("examine mushrooms")
        require(out, "cluster of pale mushrooms")
        if "what this mask has learned" in out.lower():
            raise AssertionError(
                "examine revealed hidden toxin before this mask learned it"
            )

        out = c.command("eat mushrooms")
        require(out, "your own reaction teaches you something")
        require(out, "can be toxic")
        require(out, "examine it again")

        out = c.command("examine mushrooms")
        require(out, "what this mask has learned")
        require(out, "can be toxic")
        require(out, "learned by direct effect")

        # A second independent player account proves the positive Healer path
        # without replacing SmokeTester's accepted Chronicler coverage.
        h = Client(args.host, args.port)
        healer_banner = h.sync_login_screen()
        require(healer_banner, "frankenstein village")
        healer_user = "qa_healer_assessor"
        healer_password = "HealerSmoke2026!"
        create_out = h.command(
            f"create {healer_user} {healer_password}",
            wait=4.0,
        )
        if (
            "account qa_healer_assessor" not in create_out.lower()
            and "connected" not in create_out.lower()
        ):
            h.command(
                f"connect {healer_user} {healer_password}",
                wait=4.0,
            )

        out = h.command("substrate ai")
        if "gate is open" not in out.lower() and "substrate recorded" not in out.lower():
            h.command(
                f"connect {healer_user} {healer_password}",
                wait=4.0,
            )
            out = h.command("substrate ai")
        require(out, "gate is open", "substrate recorded")

        h.command("charcreate HealerTester", wait=3.0)
        out = h.command("ic HealerTester", wait=4.0)
        require(out, "private room")

        out = h.command("calling choose healer")
        require(out, "healer is now your active calling")
        require(out, "apprentice rank")

        out = h.command("down")
        require(out, "inn common room")
        out = h.command("east")
        require(out, "inn hallway")
        out = h.command("south")
        require(out, "village square")

        out = h.command("look mushrooms")
        require(out, "cluster of pale mushrooms")
        if "toxic" in out.lower():
            raise AssertionError(
                "ordinary look leaked hidden toxin to the Healer"
            )

        out = h.command("assess mushrooms")
        require(out, "healer assessment identifies a toxic property")
        require(out, "without requiring you to taste it")
        require(out, "this mask now remembers")

        out = h.command("examine mushrooms")
        require(out, "what this mask has learned")
        require(out, "can be toxic")
        require(out, "learned by healer assessment")

        out = h.command("calling")
        require(out, "active calling: healer")
        require(out, "recorded participation")
        require(out, "assessments 1")

        out = h.command("assess mushrooms")
        require(out, "confirms what this mask already learned")
        out = h.command("calling")
        require(out, "assessments 1")

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
        if h is not None:
            print("\nHEALER TRANSCRIPT\n" + "\n".join(h.transcript))
        raise
    finally:
        if h is not None:
            h.close()
        c.close()


if __name__ == "__main__":
    raise SystemExit(main())
