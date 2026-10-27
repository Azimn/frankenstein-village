#!/usr/bin/env python3
"""Player-level telnet regression path for the Frankenstein Village spike."""

from __future__ import annotations

import argparse
from concurrent.futures import ThreadPoolExecutor
import json
import os
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


def agent_json(text: str) -> dict:
    """Verify the agent response really contains parseable single-line JSON."""
    found = re.search(r"FV_AGENT_JSON\s+(\{[^\r\n]+\})", text)
    if not found:
        raise AssertionError("No complete FV_AGENT_JSON record in response")
    return json.loads(found.group(1))


def require(text: str, *needles: str) -> None:
    low = text.lower()
    if not any(needle.lower() in low for needle in needles):
        raise AssertionError(
            "expected one of "
            + repr(needles)
            + " in output, got:\n"
            + text[-3000:]
        )


def require_all(text: str, *needles: str) -> None:
    """Every cited gameplay invariant must appear; require() accepts ANY."""
    for needle in needles:
        require(text, needle)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--host", required=True)
    parser.add_argument("--port", type=int, required=True)
    parser.add_argument("--username", required=True)
    parser.add_argument("--password", required=True)
    args = parser.parse_args()

    c = Client(args.host, args.port)
    h = None
    inn = None
    smith = None
    merchant = None
    mystic = None
    performer = None
    wanderer = None
    hound = None
    try:
        banner = c.sync_login_screen()
        require(banner, "frankenstein village")

        out = c.command(f"connect {args.username} {args.password}", wait=4.0)
        require(out, "disclosure gate", "substrate human", "substrate ai")

        out = c.command("agentlogin")
        require(out, "FV_AGENT_JSON")
        require(out, '"schema":"fvillage.agent_login.v1"')
        require(out, '"disclosure_declared":false')
        assert agent_json(out)["disclosure_declared"] is False
        require(out, "substrate ai")

        out = c.command("substrate ai")
        require(out, "gate is open", "substrate recorded")

        out = c.command("agentlogin")
        require(out, '"disclosure_declared":true')
        assert agent_json(out)["disclosure_declared"] is True
        require(out, "charcreate")
        c.command("charcreate SmokeTester", wait=3.0)
        out = c.command("ic SmokeTester", wait=4.0)
        require(out, "private room")

        out = c.command("agent")
        require(out, "FV_AGENT_JSON")
        require(out, '"schema":"fvillage.agent_context.v1"')
        require(out, '"side":"ooc"')
        assert agent_json(out)["side"] == "ooc"
        require(out, '"world_entry":"follow the Inn front door"')

        out = c.command("guide")
        require(out, "a way into the village")
        require(out, "front door")
        # Keep one personal intention across logout and restart.
        out = c.command("agenda")
        require_all(out, "your next visit", "private reminder: none yet")
        out = c.command(
            "agenda note = Return to the Square and speak with Bram about the river."
        )
        require(out, "private reminder was saved")
        out = c.command("resume")
        require(out, "speak with Bram about the river")

        # Calling foundation: a mask can choose a social profession before
        # crossing IC. Selection begins at Apprentice and exposes no free
        # promotion command or combat power.
        out = c.command("calling")
        require(out, "no active calling")
        out = c.command("calling list")
        require(out, "chronicler")
        require(out, "hound")
        require(out, "social professions")
        require(out, "mystic")
        out = c.command("calling choose chronicler")
        require(out, "chronicler is now your active calling")
        require(out, "apprentice rank")
        require(out, "later respecialization requires an authored opportunity")
        out = c.command("calling")
        require(out, "active calling: chronicler")
        require(out, "rank: apprentice")
        require(out, "no professional participation")
        out = c.command("calling work")
        require_all(out, "trade attest", "Market Lane", "chronicle")

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

        out = c.command("agent")
        require(out, "FV_AGENT_JSON")
        require(out, '"side":"ic"')
        require(out, '"social":"commons"')
        require(out, '"location":"Village Square"')
        assert agent_json(out)["location"] == "Village Square"
        require(out, '"exits":')
        require(out, '"east"')
        square_view = agent_json(out)
        assert square_view["exit_targets"]["east"] == "The Blood of the Vine"
        assert square_view["exit_targets"]["west"] == "St. Lazarus Church"
        assert "Offstage" not in str(square_view)
        assert any("woodpile" in obj.lower()
                   for obj in square_view["visible_nearby"])
        assert square_view["commands"]["firewood"] == "hearth gather"
        assert square_view["commands"]["community_work"] == "commission"
        # Emic-first GDD: the machine-readable view of this mask's embodied
        # experience is the same state accessible to humans via score deep.
        assert square_view["commands"]["embodied_senses"] == "score deep"
        assert square_view["embodiment"]["body_model"] == (
            "represented_character_sensations_not_ai_biology"
        )
        assert len(square_view["embodiment"]["first_person"]) >= 2
        assert "hunger" in square_view["embodiment"]["bands"]
        out = c.command("score deep")
        require_all(out, "a moment inside your character's body",
                    "what might help", "simulated character sensations")
        assert "hunger 50" not in out.lower()
        print("TELNET_AI_RICH_FIRST_PERSON_BODILY_SENSES_GREEN")
        # The same local observation used by model-led players must expose
        # legitimate, scheduled and conversation-capable villagers without
        # leaking invisible or private offstage residents.
        assert "Miklós Farkas" in square_view["visible_residents"]
        assert "Offstage" not in str(square_view["visible_residents"])
        assert not any("Private Room" in key for key in square_view["visible_residents"])


        # Exercise the real Gothic window early in the shared playthrough,
        # before unrelated professions and plots consume village-clock hours.
        mystic = Client(args.host, args.port)
        require(mystic.sync_login_screen(), "frankenstein village")
        mu, mp = "qa_mystic_study", os.environ["FV_QA_REPAIR_PASSWORD"]
        out = mystic.command(f"connect {mu} {mp}", wait=4.0)
        require(out, "connected", "account qa_mystic_study")
        mystic.command("charcreate MysticTester", wait=3.0)
        out = mystic.command("ic MysticTester", wait=4.0)
        require(out, "private room")
        out = mystic.command("calling choose mystic")
        require_all(out, "mystic is now your active calling", "apprentice rank")
        for direction, expected in (
            ("down", "inn common room"),
            ("east", "inn hallway"),
            ("south", "village square"),
            ("west", "st. lazarus church"),
            ("west", "churchyard"),
        ):
            out = mystic.command(direction)
            require(out, expected)
        # The autonomous residents may move when obligations, weather or
        # need overrides occur. Their guild dispute is still available as a
        # physical, nonportable folio at the actual churchyard.
        out = mystic.command("look guild folio")
        require_all(out, "Beatrice Harcourt", "Mirela Dobre", "oral account", "witness times")
        out = mystic.command("mystic")
        require_all(out, "correspondents", "hearth circle", "grave")
        # Actual conversational lines remain tested independently in the
        # NPC dialogue and recurring schedule simulations.

        out = mystic.command("mystic study vigil")
        require(out, "look grave marker")
        out = mystic.command("look grave marker")
        require_all(out, "older engraved date advances", "chisel")
        out = mystic.command("mystic study measure")
        require_all(out, "signed measure study", "world event")
        out = mystic.command("mystic study vigil")
        require(out, "already filed a study")
        out = mystic.command("calling")
        require_all(out, "active calling: mystic", "mystic grave studies 1")
        out = c.command("mystic")
        require_all(out, "mystictester", "signed measured study")
        print("TELNET_MYSTIC_GUILD_AND_GOTHIC_OBSERVATION_GREEN")

        out = c.command("next")
        require(out, "first lead: the village square")
        # This mask already chose Chronicler earlier. The guide must not
        # advertise a new first-time Calling choice as still available.
        require(out, "current calling is chronicler")
        require(out, "calling work")
        if "calling choose" in out.lower():
            raise AssertionError("Guide offers a new Calling to an established mask")
        require(out, "a shared village need")
        require(out, "repair diagnose north-square gas lamp")
        require(out, "commons post need")
        # A newcomer without an online partner has an executable solo loop
        # and a location-based investigation path, not only finite cases.
        require_all(out, "hearth gather", "hearth deliver", "survey")

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

        # Being merely present in the Square does not earn signed civic
        # recognition. The public board honestly records zero inspections.
        out = c.command("ask Miklós Farkas about route survey")
        require_all(out, "public board", "0 of 4")

        out = c.command("east")
        require(out, "blood of the vine")

        # First evening: Bram offers a genuine local lead, not a quest popup.
        # The same mask's interests persist across visits, not across accounts.
        out = c.command("talk Bram")
        require_all(out, "new to my bar")
        require_all(out, "ask me about work")
        out = c.command("ask Bram about work")
        require_all(out, "dark lamp", "smith and a merchant")
        require_all(out, "commons")
        out = c.command("ask Bram about lamp")
        require_all(out, "one lamp in the square is dark")
        require_all(out, "a smith ought")
        out = c.command("ask Bram about Silas")
        require_all(out, "silas came in soaked")
        require_all(out, "healer")
        out = c.command("ask Bram about news")
        require_all(out, "public stories")
        require_all(out, "story isn't a witness")

        # Second real-world public mystery: travel physically to the bridge,
        # look at its missing plaque, preserve witness and provisional theory.
        out = c.command("east")
        require(out, "riverside path")
        out = c.command("east")
        require(out, "old stone bridge")
        out = c.command("guide")
        require(out, "empty plaque socket")
        out = c.command("look plaque")
        require_all(out, "screws", "who removed it")
        out = c.command("bridgework display")
        require(out, "river gauge")
        out = c.command("mystery bridge")
        require_all(out, "who removed the old bridge plaque", "physical reports")
        out = c.command(
            "theory bridge = The missing inscription could name a former ferry keeper."
        )
        require(out, "provisional public interpretation")
        out = c.command("mystery bridge")
        require_all(out, "provisional theories", "former ferry keeper")
        out = c.command("west")
        require(out, "riverside path")
        out = c.command("west")
        require(out, "blood of the vine")

        # Systemic object foundation: the ordinary eat verb now reads the
        # bread's worth and uses properties. The player-facing behavior stays
        # natural while the underlying rule is object data rather than item ID.
        out = c.command("purse")
        require(out, "2 ft")
        hunger_before_eating = agent_json(c.command("agent"))["embodiment"]
        out = c.command("eat bread")
        require(out, "4 kr", "purse: 1 ft 96 kr")
        hunger_after_eating = agent_json(c.command("agent"))["embodiment"]
        assert hunger_after_eating["bands"]["hunger"] != "famished" or (
            hunger_before_eating["bands"]["hunger"] == "famished"
        ), "A physical meal did not return updated body perception"
        assert hunger_after_eating["first_person"], "Body perception went blank"
        out = c.command("score deep")
        require_all(out, "a moment inside your character's body",
                    "what might help")
        print("TELNET_GDD_T09_MEAL_CHANGES_EXISTING_EMBODIED_STATE_GREEN")
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

        decision_started = time.monotonic()
        # A shared decision writes multiple independent public projections.
        # Do not resend it on a read timeout: that would hide idempotency
        # and duplicate-event bugs. Instead observe the full response time.
        out = c.command("decide strongbox openly", wait=12.0)
        decision_ms = (time.monotonic() - decision_started) * 1000
        print(f"STRONGBOX_DECISION_RESPONSE_MS={decision_ms:.1f}")
        if not out:
            raise AssertionError(
                f"Strongbox decision returned no reply after {decision_ms:.0f}ms"
            )
        if decision_ms > 3000:
            print("STRONGBOX_DECISION_LATENCY_WARNING")
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

        out = c.command("decide chronicle reconstruct", wait=4.0)
        if not out.strip():
            # A slow CI socket can lose the one-off reply. Never blindly
            # REPLAY a potentially consequential decide action to obtain
            # pleasant text: inspect the actual public Chronicle projection.
            delayed = c.read_quiet(max_wait=3.0)
            if delayed.strip():
                out = delayed
            else:
                check = c.command("chronicle gap", wait=4.0)
                require_all(check, "derived from harbinger files",
                            "source difference is not hidden")
        if out.strip():
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

        out = c.command("guide")
        require(out, "first lead: the blood of the vine")
        require(out, "rumors R<number>")
        require_all(out, "ask Bram about work")
        require(out, "care")

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

        # The drop command's room broadcast can arrive before the telnet
        # command capture window closes. The persistent Harbinger state below
        # is the authoritative proof that the note was posted.
        c.command("drop note", wait=3.0)

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

        # Chronicler knowledge alone cannot manufacture a professional health
        # warning. A Healer contribution must exist first.
        out = c.command("chronicle health publish")
        require(out, "until a healer has filed")
        out = c.command("chronicle health")
        require(out, "no professional healer finding is on file")

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

        # The Healer files the professional half. This still does not create a
        # public warning until the Chronicler performs the institutional half.
        out = h.command("chronicle health submit mushrooms")
        require(out, "healer finding")
        require(out, "is filed with the chronicle desk")
        require(out, "not public yet")
        require(out, "active chronicler must publish")

        out = h.command("calling")
        require(out, "assessments 1")
        require(out, "public health findings 1")

        out = c.command("chronicle health")
        require(out, "healertester")
        require(out, "can be toxic")
        require(out, "not yet a public institutional warning")

        out = c.command("chronicle health publish")
        require(out, "public health warning is now part of the record")
        warning_c = re.search(r"Chronicle C(\d+)", out, re.I)
        warning_h = re.search(r"Harbinger H(\d+)", out, re.I)
        if not warning_c or not warning_h:
            raise AssertionError(
                "cross-calling warning exposed no Chronicle/Harbinger handles"
            )
        warning_chronicle_id = warning_c.group(1)
        warning_story_id = warning_h.group(1)

        out = c.command(f"chronicle C{warning_chronicle_id}")
        require(out, "health warning issued for well mushrooms")
        require(out, "healertester")
        require(out, "can be toxic")
        require(out, "does not certify other mushrooms as safe")
        require(out, "record status: verified event")
        if "25" in out:
            raise AssertionError(
                "public Chronicle leaked internal toxin magnitude"
            )

        # The Harbinger item follows the ordinary publication cadence.
        # Before press time it is queued, not readable from the public archive.
        out = c.command("chronicle health")
        require(out, f"chronicle c{warning_chronicle_id}")
        require(out, f"harbinger h{warning_story_id}")
        require(out, "queued or printed")
        if "25" in out:
            raise AssertionError(
                "public health desk leaked internal toxin magnitude"
            )

        out = c.command("calling")
        require(out, "public health records 1")

        out = h.command("chronicle health submit mushrooms")
        require(out, "already on file")
        out = h.command("calling")
        require(out, "public health findings 1")

        # Second structural interdependence case: an ordinary Resident Life
        # participant needs two professions and one real finite tavern resource.
        out = h.command("east")
        require(out, "blood of the vine")
        out = h.command("care")
        require(out, "cold hunter at supper")
        require(out, "silas crowe")
        require(out, "no healer assessment is on file")

        out = h.command("care serve Silas Crowe")
        require(out, "active innkeep calling")

        out = h.command("care assess Silas Crowe")
        require(out, "assess silas crowe's cold exposure")
        require(out, "warm food")
        require(out, "still needs an innkeep")

        out = h.command("calling")
        require(out, "resident assessments 1")

        out = h.command("care assess Silas Crowe")
        require(out, "already on file")
        out = h.command("calling")
        require(out, "resident assessments 1")

        # A third independent account proves the Innkeep contribution cannot
        # be replaced by the Healer or the existing Chronicler mask.
        inn = Client(args.host, args.port)
        inn_banner = inn.sync_login_screen()
        require(inn_banner, "frankenstein village")
        inn_user = "qa_innkeep_care"
        inn_password = "InnkeepSmoke2026!"
        create_out = inn.command(
            f"create {inn_user} {inn_password}",
            wait=4.0,
        )
        if (
            "account qa_innkeep_care" not in create_out.lower()
            and "connected" not in create_out.lower()
        ):
            inn.command(
                f"connect {inn_user} {inn_password}",
                wait=4.0,
            )

        out = inn.command("substrate ai")
        if "gate is open" not in out.lower() and "substrate recorded" not in out.lower():
            inn.command(
                f"connect {inn_user} {inn_password}",
                wait=4.0,
            )
            out = inn.command("substrate ai")
        require(out, "gate is open", "substrate recorded")

        inn.command("charcreate InnkeepTester", wait=3.0)
        out = inn.command("ic InnkeepTester", wait=4.0)
        require(out, "private room")

        out = inn.command("calling choose innkeep")
        require(out, "innkeep is now your active calling")
        require(out, "apprentice rank")

        out = inn.command("down")
        require(out, "inn common room")
        out = inn.command("east")
        require(out, "inn hallway")
        out = inn.command("south")
        require(out, "village square")
        out = inn.command("east")
        require(out, "blood of the vine")

        # Shared soup work: finite kitchen stock, real packets, real edible
        # bowls, a restart-safe recipe notebook, and no automatic promotion.
        out = inn.command("look soup pot")
        require_all(out, "large, shared iron soup pot", "pantry day", "turnip")
        out = h.command("soup prep turnip salt")
        require(out, "active innkeep")
        out = inn.command("soup prep turnip thyme")
        require_all(out, "measure real turnip and thyme", "shared pantry stock decreases")
        out = inn.command("soup prep barley salt")
        require(out, "already carry a prepared packet")
        out = inn.command("soup simmer")
        require_all(out, "real, shareable bowl", "quality", "world event")
        out = inn.command("soup notebook")
        require_all(out, "signed soup notebook", "turnip with thyme")
        out = inn.command("eat homemade soup")
        require_all(out, "taste", "earthy turnip")
        out = inn.command("eat homemade soup")
        require(out, "all gone")
        print("TELNET_SHARED_SOUP_RECIPE_CRAFTING_GREEN")

        # A distinct Performer account exercises the real Tavern stage.
        performer = Client(args.host, args.port)
        require(performer.sync_login_screen(), "frankenstein village")
        perf_password = os.environ["FV_QA_REPAIR_PASSWORD"]
        out = performer.command(f"connect qa_performer_stage {perf_password}", wait=4.0)
        require(out, "connected", "account qa_performer_stage")
        performer.command("charcreate PerformerTester", wait=3.0)
        out = performer.command("ic PerformerTester", wait=4.0)
        require(out, "private room")
        out = performer.command("calling choose performer")
        require_all(out, "performer is now your active calling", "apprentice rank")
        for move, destination in (
            ("down", "inn common room"), ("east", "inn hallway"),
            ("south", "village square"), ("east", "blood of the vine"),
        ):
            out = performer.command(move)
            require(out, destination)
        out = performer.command("look performance platform")
        require_all(out, "raised wooden stage", "actual musicians")
        out = performer.command("stage perform ballad")
        require(out, "rehearse that piece")
        out = inn.command("stage rehearse ballad")
        require(out, "active performer")
        out = performer.command("stage rehearse ballad")
        require_all(out, "rehearse the ballad", "world event")
        out = performer.command("stage rehearse ballad")
        require(out, "already rehearsed")
        # A real Healer leaves BEFORE the show, so no one can credit that
        # later-arriving account with witnessing this actual performance.
        out = h.command("west")
        require(out, "village square")
        out = performer.command("stage perform ballad")
        require_all(out, "actually perform the ballad", "world event")
        out = performer.command("look")
        require_all(out, "raised stage remembers", "performertester", "ballad")
        out = performer.command("stage witness")
        require(out, "own audience")
        out = inn.command("stage witness")
        require(out, "actually witnessed")
        out = inn.command("stage witness")
        require(out, "already witnessed")
        # T-06: This character was in the village but not in the room when
        # the show actually occurred; arriving within the same hour must
        # never confer a fabricated firsthand audience record.
        out = h.command("east")
        require(out, "blood of the vine")
        out = h.command("stage witness")
        require(out, "only an audience member present for the actual performance")
        out = performer.command("stage")
        require_all(out, "performertester", "1 other player account")
        print("TELNET_GDD_T06_LATE_ARRIVAL_WITNESS_DENIED_GREEN")
        out = performer.command("agent")
        assert agent_json(out)["commands"]["public_stage"] == "stage"
        print("TELNET_RENEWABLE_PERFORMER_AND_REAL_AUDIENCE_GREEN")

        # The Healer's return generated an unsolicited room-arrival broadcast
        # for the Innkeep. Drain that queued notification before requesting
        # a care response; otherwise the telnet reader can mistake the
        # broadcast for the next command's reply.
        inn.read_quiet()
        out = inn.command("care")
        require(out, "healer assessment filed by healertester")
        require(out, "hospitality is still needed")
        require(out, "spends one actual serving of stew")

        out = inn.command("care serve Silas Crowe")
        require(out, "hot bowl from the tavern stock")
        require(out, "one stew serving is spent")
        require(out, "care case is complete")
        out = h.command("ask Bram about Silas")
        require_all(out, "silas has had his supper")
        require_all(out, "a good evening")

        out = inn.command("calling")
        require(out, "recovery hospitality 1")

        out = inn.command("care")
        require(out, "care complete")
        require(out, "healer assessed him")
        require(out, "innkeep spent a real tavern meal")

        out = inn.command("care serve Silas Crowe")
        require(out, "tavern care is already complete")
        out = inn.command("calling")
        require(out, "recovery hospitality 1")

        out = h.command("care")
        require(out, "care complete")
        out = h.command("guide")
        require(out, "care case has ended")
        require(out, "outcome")

        # Healer career depth: an actual Church cot, renewable per-day
        # professional assessment and physical, consumable linen dressings.
        out = h.command("clinic assess")
        require(out, "st. lazarus church")
        out = h.command("west")
        require(out, "village square")
        out = h.command("west")
        require(out, "st. lazarus church")
        out = h.command("guide")
        require_all(out, "clinic assess", "clinic treat")
        out = h.command("look clinic cot")
        require_all(out, "visiting patient", "fresh linen", "village day")
        out = h.command("clinic treat rest")
        require(out, "examine the actual patient first")
        out = h.command("clinic assess")
        require_all(out, "assess the visiting patient", "signed world event")
        out = h.command("clinic assess")
        require(out, "already assessed")
        out = h.command("clinic prepare")
        require_all(out, "real linen compress", "signed world event")
        out = h.command("inventory")
        require(out, "fresh linen compress")
        out = h.command("clinic treat compress")
        require_all(out, "carry out compress treatment", "signed as world event")
        out = h.command("inventory")
        assert "fresh linen compress" not in out.lower(), (
            "Clinical dressing was not consumed by actual treatment"
        )
        out = h.command("clinic treat rest")
        require(out, "already received treatment")
        # GDD T-08: the public clinic cannot disclose today's notes.
        # A signed assessment is not blanket permission to open records.
        out = h.command("clinic")
        require_all(out, "visiting patient", "care has been provided")
        assert "healertester" not in out.lower()
        assert "less suited" not in out.lower()
        assert "cold" not in out.lower()
        out = h.command("clinic records")
        require(out, "patient's signed permission")
        assert "cold" not in out.lower()
        out = h.command("clinic request records")
        require_all(out, "grants this examining healer", "signed event")
        out = h.command("clinic records")
        require_all(out, "confidential", "cold", "healertester", "compress",
                    "less suited", "patient permission")
        # A completely different logged-in account can see only the
        # shared workboard, even while standing by the same physical cot.
        inn.read_quiet()
        out = inn.command("west")
        require(out, "village square")
        out = inn.command("west")
        require(out, "st. lazarus church")
        out = inn.command("clinic")
        require_all(out, "visiting patient", "care has been provided")
        assert "cold" not in out.lower()
        assert "used compress" not in out.lower()
        assert "healertester" not in out.lower()
        out = inn.command("look clinic cot")
        require_all(out, "clinic", "visiting patient")
        assert "cold" not in out.lower()
        assert "healertester" not in out.lower()
        out = inn.command("clinic records")
        require(out, "private clinical notes require an attending healer")
        out = inn.command("clinic request records")
        require(out, "active healer")
        out = inn.command("east")
        require(out, "village square")
        out = inn.command("east")
        require(out, "blood of the vine")
        h.read_quiet()
        print("TELNET_GDD_T08_CONSENTED_CLINIC_RECORDS_PRIVATE_GREEN")
        out = h.command("calling")
        require_all(out, "clinic assess 1", "clinic prepare 1", "clinic treat 1")
        out = h.command("agent")
        assert agent_json(out)["commands"]["clinic_care"] == "clinic"
        out = h.command("east")
        require(out, "village square")
        out = h.command("east")
        require(out, "blood of the vine")
        print("TELNET_HEALER_RENEWABLE_CLINIC_GREEN")

        # Third structural interdependence case: independent QA accounts each
        # own exactly one mask. The fixture provisions them before telnet so
        # public account creation rate limits remain fully enforced.
        repair_password = os.environ["FV_QA_REPAIR_PASSWORD"]
        smith = Client(args.host, args.port)
        smith_banner = smith.sync_login_screen()
        require(smith_banner, "frankenstein village")
        smith_out = smith.command(
            f"connect qa_smith_repair {repair_password}",
            wait=4.0,
        )
        require(smith_out, "connected", "account qa_smith_repair")
        smith.command("charcreate SmithTester", wait=3.0)
        out = smith.command("ic SmithTester", wait=4.0)
        require(out, "private room")
        out = smith.command("calling choose smith")
        require(out, "smith is now your active calling")
        require(out, "apprentice rank")
        out = smith.command("down")
        require(out, "inn common room")
        out = smith.command("east")
        require(out, "inn hallway")
        out = smith.command("south")
        require(out, "village square")

        out = smith.command("repair")
        require(out, "the broken mantle")
        require(out, "no smith diagnosis is on file")
        out = smith.command("guide")
        require(out, "a shared village need")
        require(out, "repair diagnose north-square gas lamp")
        require(out, "commons post need")
        out = smith.command("repair procure")
        require(out, "active merchant calling")
        out = smith.command("repair diagnose north-square gas lamp")
        require(out, "mantle collar is cracked")
        require(out, "merchant must procure")
        out = h.command("ask Bram about the lamp")
        require_all(out, "smith found the crack")
        require_all(out, "merchant")
        out = smith.command("repair finish north-square gas lamp")
        require(out, "merchant must procure the replacement collar")
        out = smith.command("agenda")
        require_all(out, "your smith diagnosis", "merchant must procure",
                    "lamp shop")
        out = smith.command("calling")
        require(out, "repair diagnoses 1")
        out = smith.command("repair diagnose north-square gas lamp")
        require(out, "already on file")
        out = smith.command("calling")
        require(out, "repair diagnoses 1")

        merchant = Client(args.host, args.port)
        merchant_banner = merchant.sync_login_screen()
        require(merchant_banner, "frankenstein village")
        merchant_out = merchant.command(
            f"connect qa_merchant_repair {repair_password}",
            wait=4.0,
        )
        require(merchant_out, "connected", "account qa_merchant_repair")
        merchant.command("charcreate MerchantTester", wait=3.0)
        out = merchant.command("ic MerchantTester", wait=4.0)
        require(out, "private room")
        out = merchant.command("calling choose merchant")
        require(out, "merchant is now your active calling")
        require(out, "apprentice rank")
        out = merchant.command("down")
        require(out, "inn common room")
        out = merchant.command("east")
        require(out, "inn hallway")
        out = merchant.command("south")
        require(out, "village square")

        out = merchant.command("repair diagnose north-square gas lamp")
        require(out, "active smith calling")
        out = merchant.command("guide")
        require(out, "smith identified the damage")
        require(out, "repair procure")
        require(out, "lamp shop")
        out = merchant.command("south")
        require(out, "lamp shop")
        out = merchant.command("guide")
        require(out, "merchant here")
        require(out, "repair procure")
        out = merchant.command("repair")
        require(out, "smith diagnosis filed by smithtester")
        require(out, "merchant must procure")
        out = merchant.command("repair procure")
        require(out, "procure one brass mantle collar")
        require(out, "one real stock unit")
        require(out, "smith must install")
        out = merchant.command("agenda")
        require_all(out, "your merchant procurement", "smith must install")
        out = smith.command("agenda")
        require_all(out, "merchant has procured",
                    "repair finish north-square gas lamp")
        out = h.command("ask Bram about the lamp")
        require_all(out, "got the collar")
        require_all(out, "lamp's still dark")
        out = merchant.command("calling")
        require(out, "repair procurements 1")
        out = merchant.command("repair procure")
        require(out, "already procured")
        out = merchant.command("guide")
        require(out, "already reserved")
        require(out, "repair finish north-square gas lamp")
        out = merchant.command("calling")
        require(out, "repair procurements 1")

        out = smith.command("repair")
        require(out, "replacement collar procured by merchanttester")
        out = smith.command("guide")
        require(out, "part has been procured")
        require(out, "repair finish north-square gas lamp")
        out = smith.command("repair finish north-square gas lamp")
        require(out, "install the procured collar")
        require(out, "lamp is working again")
        out = h.command("ask Bram about lamp")
        require_all(out, "lamp's burning")
        require_all(out, "two sets of hands")
        out = smith.command("calling")
        require(out, "repair diagnoses 1")
        require(out, "repair completions 1")
        out = smith.command("repair finish north-square gas lamp")
        require(out, "already complete")
        out = smith.command("calling")
        require(out, "repair completions 1")
        out = merchant.command("repair")
        require(out, "repair complete")
        require(out, "smithtester")
        require(out, "merchanttester")
        for participant in (smith, merchant):
            out = participant.command("agenda")
            require_all(out, "north-square gas lamp is repaired",
                        "no repeat repair is needed")
        print("TELNET_GDD_T16_LAMP_REPAIR_RETURN_AGENDA_GREEN")
        out = smith.command("guide")
        require(out, "lamp is burning again")
        require(out, "no longer an open job")
        # A finished one-time case must offer a real alternate route based
        # on the still-stocked Square woodpile, never reopen the old case.
        require(out, "alternative available now")
        require(out, "hearth gather")
        if "repair diagnose" in out.lower() or "repair procure" in out.lower():
            raise AssertionError("Guide advertises completed repair as open work")

        # Renewable civic work beyond one-shot cases: real stock from the
        # Square reaches the Tavern through an ordinary player's inventory.
        out = smith.command("look woodpile")
        require_all(out, "today's 3", "bundles remain")
        out = smith.command("hearth")
        require_all(out, "tavern firewood reserve: 0", "woodpile: 3")
        out = smith.command("hearth gather")
        require_all(out, "real bundle", "2 bundles remain today")
        out = smith.command("hearth gather")
        require(out, "already carry a firewood bundle")
        out = smith.command("hearth deliver")
        require(out, "must be in the blood of the vine")
        out = smith.command("east")
        require(out, "blood of the vine")
        out = smith.command("hearth tend")
        require(out, "active innkeep")
        out = smith.command("hearth deliver")
        require_all(out, "shared rack now holds 1", "someone with the innkeep")
        out = smith.command("hearth deliver")
        require(out, "bring a real bundle")
        out = inn.command("hearth")
        require_all(out, "reserve: 1", "embers")
        out = inn.command("hearth tend")
        require_all(out, "hearth catches", "0 bundles remain")
        out = inn.command("hearth tend")
        require(out, "already blazing")
        out = inn.command("hearth")
        require_all(out, "fresh logs blaze", "reserve: 0", "last tended by innkeeptester")
        out = inn.command("look hearth")
        require(out, "fresh logs blaze")
        out = inn.command("look")
        require(out, "fresh logs blaze")
        out = inn.command("calling")
        require(out, "hearth tendings 1")
        out = smith.command("west")
        require(out, "village square")
        out = smith.command("look woodpile")
        require(out, "2 of today's 3 bundles remain")

        # Cooperative daily commission: pledge one physical object in the
        # Square and let a distinct account carry it to the Tavern.
        out = smith.command("commission")
        require_all(out, "village commission", "commission pledge")
        out = smith.command("commission pledge")
        require(out, "first gather a physical")
        out = smith.command("hearth gather")
        require(out, "1 bundles remain today")
        # The guide reads actual inventory and does not offer duplicate
        # gathering while the player already carries a real bundle.
        out = smith.command("guide")
        require(out, "hearth deliver")
        if "|whearth gather|n" in out.lower() or "hearth gather" in out.lower():
            raise AssertionError("Guide offers duplicate firewood while carrying")
        out = smith.command("commission pledge")
        require_all(out, "pledge your physical", "another player")
        out = smith.command("commission pledge")
        require(out, "no longer open")
        out = smith.command("commission deliver")
        require(out, "travel to the blood of the vine")
        out = merchant.command("north")
        require(out, "village square")
        out = smith.command("give firewood = MerchantTester")
        require(out, "you give")
        out = merchant.command("commission")
        require_all(out, "pledged", "commission deliver")
        out = merchant.command("commission deliver")
        require(out, "travel to the blood of the vine")
        out = merchant.command("east")
        require(out, "blood of the vine")
        out = merchant.command("commission deliver")
        require_all(out, "commission complete", "now holds 1 bundles")
        out = merchant.command("commission deliver")
        require(out, "must first pledge")
        # GDD T-13, real two-account ordering A: the carrier finishes first.
        # Neither the original supplier nor the carrier can then cancel or
        # reopen the signed order. A refused command must not credit fuel.
        out = smith.command("commission cancel")
        require(out, "only an outstanding commission pledge can be cancelled")
        out = merchant.command("commission cancel")
        require(out, "only an outstanding commission pledge can be cancelled")
        out = merchant.command("commission deliver")
        require(out, "must first pledge")
        out = merchant.command("hearth")
        require(out, "reserve: 1")
        out = smith.command("commission")
        require_all(out, "completed by", "smithtester", "merchanttester")
        print("TELNET_GDD_T13_COMPLETE_BEFORE_CANCEL_TWO_ACCOUNT_GREEN")

        # Restore Merchant's earlier Lamp Shop position so independent
        # Commons tests keep their original room-isolation expectations.
        out = merchant.command("west")
        require(out, "village square")
        out = merchant.command("south")
        require(out, "lamp shop")

        # Player-authored civic activity persists across accounts and rooms.
        out = smith.command("commons")
        require(out, "village commons")
        out = smith.command(
            "commons post need = Neighbors sought to share the night lamp watch."
        )
        require(out, "commons #1 posted")
        out = smith.command("commons 1")
        require(out, "neighbors sought")
        require(out, "no one has written a response yet")
        out = smith.command("commons follow 1")
        require(out, "in this mask's keeping")
        out = smith.command("commons followed")
        require(out, "commons #1")
        require(out, "no unread changes")
        out = smith.command("commons follow 1")
        require(out, "already followed")
        out = merchant.command("commons")
        require(out, "noticeboard is in the village square")
        out = merchant.command("north")
        require(out, "village square")
        out = merchant.command("east")
        require(out, "blood of the vine")
        out = merchant.command("commons")
        require(out, "neighbors sought")
        out = merchant.command("commons followed")
        require(out, "no commons threads")
        out = merchant.command("ask Bram about commons")
        require(out, "commons #1")
        require(out, "smithtester")
        require(out, "their word, not mine")
        out = merchant.command(
            "commons reply 1 = I can take the first watch tomorrow morning."
        )
        require(out, "signed response")
        out = smith.command("commons followed")
        require_all(out, "commons #1", "1 new signed reply")
        out = smith.command("commons followed")
        require(out, "1 new signed reply")
        out = smith.command("commons check 1")
        require_all(out, "first watch tomorrow", "updates noted by this mask")
        out = smith.command("commons followed")
        require(out, "no unread changes")
        out = smith.command("commons 1")
        require(out, "merchanttester")
        require(out, "first watch tomorrow")
        out = merchant.command(
            "commons close 1 = An answer from another player's account."
        )
        require(out, "only the author")
        out = smith.command(
            "commons close 1 = We spoke and agreed to meet again tomorrow."
        )
        require(out, "closed with your account")
        out = smith.command("commons followed")
        require_all(out, "commons #1", "closing account added")
        out = smith.command("commons check 1")
        require_all(out, "we spoke and agreed", "updates noted by this mask")
        out = smith.command("commons followed")
        require_all(out, "commons #1", "no unread changes")
        out = merchant.command("commons archive")
        require(out, "past correspondence")
        require(out, "neighbors sought")

        # A separate open offer survives logout and a real server restart.
        out = merchant.command("west")
        require(out, "village square")
        out = merchant.command(
            "commons post offer = I can carry parcels for neighbors after market."
        )
        require(out, "commons #2 posted")
        out = smith.command("commons follow 2")
        require(out, "in this mask's keeping")
        out = smith.command("commons followed")
        require_all(out, "commons #1", "commons #2")
        out = smith.command("commons")
        require(out, "carry parcels")
        out = smith.command("commons 2")
        require(out, "merchanttester")

        # Unified gameplay regression: PvP dice must invite real players,
        # never route nonkeeper names into the keeper-only refusal.
        out = merchant.command("east")
        require(out, "blood of the vine")
        out = smith.command("east")
        require(out, "blood of the vine")
        out = c.command("east")
        require(out, "blood of the vine")
        out = c.command("roll dice vs MerchantTester")
        require(out, "merchanttester", "dice")
        out = merchant.command("roll dice decline")
        require(out, "pushes the cup back", "another night")

        # An existing wrestling invite must not be silently overwritten.
        out = smith.command("wrestle MerchantTester")
        require(out, "arm wrestling")
        out = c.command("wrestle MerchantTester")
        require(out, "already has a wrestling challenge")
        out = merchant.command("wrestle answer")
        require(out, "hands grip")
        out = smith.command("wrestle quit")
        require(out, "steps back")
        out = merchant.command("wrestle push")
        require(out, "not wrestling anyone")

        # A half-abandoned bout cannot be revived by logging in later.
        out = smith.command("wrestle MerchantTester")
        require(out, "arm wrestling")
        out = merchant.command("wrestle answer")
        require(out, "hands grip")
        merchant.close()
        out = smith.command("wrestle quit")
        require(out, "gone cold", "steps back")
        merchant = Client(args.host, args.port)
        merchant_banner = merchant.sync_login_screen()
        require(merchant_banner, "frankenstein village")
        out = merchant.command(
            f"connect qa_merchant_repair {repair_password}", wait=4.0
        )
        require(out, "connected")
        out = merchant.command("ic MerchantTester", wait=4.0)
        require(out, "blood of the vine")
        out = merchant.command("wrestle push")
        require(out, "bout's gone cold", "not wrestling anyone")

        # Actual concurrent socket clients sharing one authoritative game.
        # No fake transport, admin shell calls or sequential-only promises.
        participants = (
            ("SmokeTester", c),
            ("HealerTester", h),
            ("InnkeepTester", inn),
            ("SmithTester", smith),
            ("MerchantTester", merchant),
        )
        def _simultaneous_observation(participant):
            name, client = participant
            rows = []
            for _ in range(2):
                output = client.command("agent", wait=5.0)
                state = agent_json(output)
                assert state["schema"] == "fvillage.agent_context.v1"
                assert state["side"] in {"ic", "ooc"}
                out_calendar = client.command("calendar", wait=5.0)
                require(out_calendar, "village calendar")
                rows.append(state["location"])
            return name, rows
        with ThreadPoolExecutor(max_workers=5) as pool:
            concurrent_results = list(pool.map(
                _simultaneous_observation, participants
            ))
        assert len(concurrent_results) == 5
        assert len({name for name, _rows in concurrent_results}) == 5
        assert all(len(rows) == 2 and all(rows) for _name, rows in concurrent_results)
        print("CONCURRENT_FIVE_PLAYER_OBSERVATION_GREEN")

        # Different accounts answer one persistent public thread at once.
        # Both posts must survive; the Commons cannot drop one update.
        def _answer_commons(client, words):
            return client.command("commons reply 2 = " + words, wait=5.0)
        with ThreadPoolExecutor(max_workers=2) as pool:
            one_post = pool.submit(
                _answer_commons, smith,
                "I will help carry parcels on the market road tomorrow."
            )
            other_post = pool.submit(
                _answer_commons, inn,
                "I can provide a dry place to sort the delivered crates."
            )
            result_one, result_two = one_post.result(), other_post.result()
        require(result_one, "signed response")
        require(result_two, "signed response")
        out = merchant.command("commons 2")
        require_all(out, "help carry parcels", "dry place to sort")
        out = smith.command("commons followed")
        require(out, "2 new signed replies")
        out = smith.command("commons check 2")
        require(out, "updates noted by this mask")
        print("CONCURRENT_COMMONS_PERSISTENCE_GREEN")

        # A first-hand field log is earned through real four-district travel,
        # not by following a rumour or reading a public mystery elsewhere.
        # A second account independently checks one real river landmark.
        # Shared route reports are signed public facts of inspection, not
        # automatic quest progress generated by someone's conversation.
        out = smith.command("east")
        require(out, "riverside path")
        out = smith.command("survey report")
        require(out, "first examine")
        out = smith.command("look river gauge")
        require(out, "flood marks")
        out = smith.command("survey report")
        require_all(out, "report signed", "1 of 4")
        out = smith.command("survey report")
        require(out, "already signed")
        out = smith.command("west")
        require(out, "blood of the vine")
        out = c.command("survey")
        require_all(out, "1 of 4", "smithtester", "not yet inspected")

        out = c.command("journal discoveries")
        require(out, "not personally inspected")
        out = c.command("west")
        require(out, "village square")
        out = c.command("west")
        require(out, "st. lazarus church")
        out = c.command("west")
        require(out, "churchyard")
        out = c.command("look grave marker")
        require_all(out, "initials", "different hands")
        out = c.command("mystic")
        require_all(out, "correspondents", "hearth circle", "grave")
        out = c.command("mystic study measure")
        require(out, "only an active mystic")
        out = c.command("survey report")
        require_all(out, "report signed", "2 of 4")
        out = c.command("north")
        require(out, "northern treeline")
        out = c.command("look cord")
        require_all(out, "scarlet cord", "cut cleanly")
        out = c.command("survey report")
        require_all(out, "report signed", "3 of 4")
        out = c.command("south")
        require(out, "churchyard")
        out = c.command("east")
        require(out, "st. lazarus church")
        out = c.command("east")
        require(out, "village square")
        out = c.command("south")
        require(out, "lamp shop")
        out = c.command("south")
        require(out, "market lane")
        out = c.command("look market scale")
        require_all(out, "brass pans", "two prices")
        out = c.command("trade")
        require_all(out, "Market Lane", "crooked", "trade calibrate")
        out = c.command("trade attest")
        require(out, "documented Merchant decision and Smith calibration")

        # Three distinct active Callings intervene in the same recurring
        # physical market dispute. A held distribution blocks REAL stock,
        # and Smith calibration releases it without resetting inventory.
        for direction, expected in (
            ("west", "village square"),
            ("south", "lamp shop"),
            ("south", "market lane"),
        ):
            out = merchant.command(direction)
            require(out, expected)
        out = merchant.command("calling work")
        require_all(out, "trade honor", "trade hold")
        out = merchant.command("trade hold")
        require(out, "First inspect the actual crooked market scale")
        out = merchant.command("look market scale")
        require(out, "two prices")
        out = merchant.command("trade hold")
        require_all(out, "signed", "temporarily on hold")
        require_all(merchant.command("agenda"),
                    "your merchant market hold remains active", "trade release")
        out = merchant.command("soup procure")
        require_all(out, "physical crate of kitchen roots", "market crates remain")
        out = merchant.command("soup procure")
        require(out, "already carry a kitchen delivery")
        out = c.command("bridgework collect preserve")
        require(out, "holding construction supplies")
        out = c.command("trade attest")
        require(out, "documented Merchant decision and Smith calibration")
        for direction, expected in (
            ("west", "village square"),
            ("south", "lamp shop"),
            ("south", "market lane"),
        ):
            out = smith.command(direction)
            require(out, expected)
        out = smith.command("trade honor")
        require(out, "Merchant Calling")
        out = smith.command("look market scale")
        require(out, "two prices")
        out = smith.command("trade calibrate")
        require_all(out, "signed", "physically recalibrated")
        require_all(merchant.command("agenda"),
                    "your merchant market hold was resolved", "smith calibrated")
        require_all(smith.command("agenda"),
                    "your smith calibration", "chronicler can attest")
        out = smith.command("trade calibrate")
        require(out, "already been calibrated")
        out = c.command("trade attest")
        require_all(out, "signed", "attested both source events")
        require_all(c.command("agenda"),
                    "your chronicler attestation", "both source events")
        print("TELNET_GDD_T16_MARKET_THREE_CALLING_AGENDA_GREEN")
        out = c.command("trade attest")
        require(out, "already attested")
        out = c.command("look market scale")
        require_all(out, "physically recalibrated", "MerchantTester", "SmithTester")
        out = c.command("look")
        require(out, "physically recalibrated")

        # Ordinary Smith craftsmanship creates exactly one real repair
        # object, which can be handed to another account for installation.
        # The shared Market board changes only after physical custody.
        out = merchant.command("workshop")
        require_all(out, "2 of 2 iron offcuts", "uninstalled")
        out = smith.command("workshop forge")
        require(out, "at the real Market Workshop bench")
        out = smith.command("east")
        require(out, "market workshop")
        out = smith.command("guide")
        require_all(out, "smithing bench", "workshop forge")
        out = smith.command("look smithing bench")
        require_all(out, "repair docket", "2 of 2 iron offcuts")
        out = smith.command("workshop forge")
        require_all(out, "real transferable iron market hinge", "1 iron offcut remains")
        out = smith.command("workshop forge")
        require(out, "already carry a forged market hinge")
        out = merchant.command("workshop install")
        require(out, "carry an actual forged market hinge")
        out = smith.command("west")
        require(out, "market lane")
        out = smith.command("give forged market hinge = MerchantTester")
        require(out, "forged market hinge")
        out = merchant.command("inventory")
        require(out, "forged market hinge")
        out = merchant.command("workshop install")
        require_all(out, "physically install", "signed world event", "forging source")
        out = merchant.command("inventory")
        assert "forged market hinge" not in out.lower(), (
            "Installed hinge is still a portable item"
        )
        out = merchant.command("workshop install")
        require(out, "carry an actual forged market hinge")
        out = c.command("look market fittings board")
        require_all(out, "MerchantTester", "signed", "forged source")
        out = smith.command("agent")
        assert agent_json(out)["commands"]["install_market_repair"] == "workshop install"
        print("TELNET_TWO_ACCOUNT_PHYSICAL_MARKET_WORKSHOP_GREEN")

        for actor in (merchant, smith):
            for direction, expected in (
                ("north", "lamp shop"),
                ("north", "village square"),
                ("east", "blood of the vine"),
            ):
                out = actor.command(direction)
                require(out, expected)
        out = merchant.command("soup deliver")
        require_all(out, "actual crate enters the tavern pantry", "portions of turnip")
        out = inn.command("look soup pot")
        require_all(out, "pantry day", "Last completed batch: InnkeepTester")
        print("TELNET_MARKET_TO_TAVERN_SOUP_SUPPLY_GREEN")

        # A real Wanderer moves a finite, non-magical parcel between rooms.
        wanderer = Client(args.host, args.port)
        require(wanderer.sync_login_screen(), "frankenstein village")
        travel_pw = os.environ["FV_QA_REPAIR_PASSWORD"]
        out = wanderer.command(f"connect qa_wanderer_mail {travel_pw}", wait=4.0)
        require(out, "connected", "account qa_wanderer_mail")
        wanderer.command("charcreate WandererTester", wait=3.0)
        out = wanderer.command("ic WandererTester", wait=4.0)
        require(out, "private room")
        out = wanderer.command("calling choose wanderer")
        require_all(out, "wanderer is now your active calling", "apprentice rank")
        for move, destination in (
            ("down", "inn common room"), ("east", "inn hallway"),
            ("south", "village square"), ("south", "lamp shop"),
            ("south", "market lane"),
        ):
            out = wanderer.command(move)
            require(out, destination)
        out = wanderer.command("look ferry postbag")
        require_all(out, "two sealed outgoing parcels", "courier collect")
        out = wanderer.command("courier")
        require_all(out, "2 real parcels left", "Market Lane")
        out = wanderer.command("courier deliver")
        require(out, "deliver an actual post parcel from Riverside Path")
        out = inn.command("courier collect")
        require(out, "collect ferry post in Market Lane")
        out = wanderer.command("courier collect")
        require_all(out, "actual sealed ferry-post parcel", "world event")
        out = wanderer.command("courier collect")
        require(out, "already carry a post parcel")
        out = wanderer.command("inventory")
        require(out, "sealed village mail parcel")
        for move, destination in (
            ("north", "lamp shop"), ("north", "village square"),
            ("east", "blood of the vine"), ("east", "riverside path"),
        ):
            out = wanderer.command(move)
            require(out, destination)
        out = wanderer.command("look riverside post chest")
        require_all(out, "public chest", "signed public receipt")
        out = wanderer.command("courier deliver")
        require_all(out, "actual parcel enters", "signed")
        out = wanderer.command("inventory")
        assert "sealed village mail parcel" not in out.lower()
        out = wanderer.command("courier deliver")
        require(out, "must carry an actual sealed parcel")
        out = wanderer.command("courier")
        require_all(out, "wanderertester", "signed recent deliveries")
        out = wanderer.command("agent")
        assert agent_json(out)["commands"]["ferry_post_delivery"] == "courier deliver"
        print("TELNET_WANDERER_REAL_FERRY_POST_GREEN")

        # GDD-EDGE-31: Merchant spends the remaining finite postbag slot
        # on an actual parcel, another ordinary account accepts custody,
        # physically travels the route and signs the source-linked receipt.
        out = merchant.command("courier consign")
        require(out, "merchant must consign freight in market lane")
        for move, destination in (
            ("west", "village square"), ("south", "lamp shop"),
            ("south", "market lane"),
        ):
            out = merchant.command(move)
            require(out, destination)
        out = merchant.command("courier accept")
        require(out, "active wanderer")
        out = merchant.command("courier consign")
        require_all(out, "actual merchant freight", "world event", "1")
        # The first solo mail delivery used one slot. Freight consumes
        # the second, never creates a second inventory or phantom stock.
        out = merchant.command("courier consign")
        require(out, "shared market postbag is depleted")
        out = wanderer.command("courier accept")
        require(out, "active wanderer must accept freight in market lane")
        for move, destination in (
            ("west", "blood of the vine"), ("west", "village square"),
            ("south", "lamp shop"), ("south", "market lane"),
        ):
            out = wanderer.command(move)
            require(out, destination)
        out = wanderer.command("courier consign")
        require(out, "active merchant")
        out = wanderer.command("courier accept")
        require_all(out, "merchant's physical freight", "consignment")
        out = wanderer.command("courier accept")
        require(out, "already carry a post parcel")
        out = wanderer.command("inventory")
        require(out, "sealed village mail parcel")
        for move, destination in (
            ("north", "lamp shop"), ("north", "village square"),
            ("east", "blood of the vine"), ("east", "riverside path"),
        ):
            out = wanderer.command(move)
            require(out, destination)
        out = wanderer.command("courier deliver")
        require_all(out, "actual parcel enters", "signed")
        out = wanderer.command("courier")
        require_all(out, "2 signed recent deliveries", "freight consignment",
                    "wanderer acceptance")
        out = wanderer.command("courier deliver")
        require(out, "must carry an actual sealed parcel")
        print("TELNET_GDD_EDGE31_MERCHANT_WANDERER_FREIGHT_GREEN")

        # GDD T-07: two independent ordinary accounts, same physical cord.
        # Travel, inspect, and act from their real locations. The Wanderer
        # records logistical caution before a Hound physically marks it;
        # a later Hound action must not rewrite the earlier field observation.
        for move, destination in (
            ("west", "blood of the vine"),
            ("west", "village square"),
            ("west", "st. lazarus church"),
            ("west", "churchyard"),
            ("north", "northern treeline"),
        ):
            out = wanderer.command(move)
            require(out, destination)
        out = wanderer.command("survey passability")
        require(out, "examine the physical red cord")
        out = wanderer.command("look cord")
        require_all(out, "scarlet cord", "cut cleanly")
        out = wanderer.command("survey protect")
        require(out, "only a hound")
        out = wanderer.command("survey passability")
        require(out, "record firsthand passability evidence")
        out = wanderer.command("survey passability")
        require(out, "already signed today")

        hound = Client(args.host, args.port)
        require(hound.sync_login_screen(), "frankenstein village")
        hound_pass = os.environ["FV_QA_REPAIR_PASSWORD"]
        hound_user = "qa_hound_protection"
        out = hound.command(f"connect {hound_user} {hound_pass}", wait=4.0)
        require(out, "connected", "account qa_hound_protection")
        hound.command("charcreate HoundTester", wait=3.0)
        out = hound.command("ic HoundTester", wait=4.0)
        require(out, "private room")
        out = hound.command("calling choose hound")
        require_all(out, "hound is now your active calling", "apprentice rank")
        for move, destination in (
            ("down", "inn common room"), ("east", "inn hallway"),
            ("south", "village square"), ("west", "st. lazarus church"),
            ("west", "churchyard"), ("north", "northern treeline"),
        ):
            out = hound.command(move)
            require(out, destination)
        out = hound.command("survey protect")
        require(out, "examine the physical red cord")
        out = hound.command("look cord")
        require(out, "scarlet cord")
        out = hound.command("survey passability")
        require(out, "only a hound")
        out = hound.command("survey protect")
        require_all(out, "tie the original frayed cord", "visible warning", "signed event")
        out = hound.command("survey protect")
        require(out, "already signed today")
        # The Hound's movement and action notified the nearby Wanderer.
        # Drain unsolicited room broadcasts before testing object look.
        wanderer.read_quiet()
        out = wanderer.command("look cord")
        require_all(out, "cut cleanly", "clear caution marker")
        out = wanderer.command("survey")
        require_all(out, "houndtester", "wanderertester", "unmarked cord",
                    "does not repair the cord")
        print("TELNET_GDD_T07_HOUND_WANDERER_SHARED_PHYSICAL_ROUTE_GREEN")

        print("TELNET_PROFESSIONAL_MARKET_CAUSAL_LOOP_GREEN")
        out = c.command("guide")
        require_all(out, "civic material table", "bridgework collect preserve")
        out = c.command("look civic material table")
        require_all(out, "2 canvas kits", "2 inquiry boards")
        out = c.command("bridgework collect preserve")
        require_all(out, "real preserve kit", "1 matching kits remain")
        out = c.command("bridgework collect display")
        require(out, "already carry bridge supplies")
        out = c.command("look civic material table")
        require_all(out, "1 canvas kits", "2 inquiry boards")
        out = c.command("survey report")
        require_all(out, "report signed", "4 of 4", "now complete")
        out = c.command("north")
        require(out, "lamp shop")
        out = c.command("north")
        require(out, "village square")
        out = c.command("east")
        require(out, "blood of the vine")
        out = c.command("east")
        require(out, "riverside path")
        out = c.command("look river gauge")
        require_all(out, "flood marks", "winter level")
        out = c.command("survey report")
        require(out, "already signed")
        out = c.command("survey")
        require_all(out, "4 of 4", "smithtester", "smoketester",
                    "route is complete")

        # A real solo mystery branch changes shared physical scenery.
        # Earlier plaque inspection and this in-person gauge observation
        # provide different evidence; writing a theory never grants either.
        out = c.command("east")
        require(out, "old stone bridge")
        out = c.command("bridgework")
        require_all(out, "firsthand evidence", "bridgework preserve",
                    "bridgework display")
        # Possession matters: a kit lying at the bridge cannot build itself.
        out = c.command("drop canvas preservation kit")
        require(out, "canvas preservation kit")
        out = c.command("bridgework preserve")
        require(out, "bring the matching real kit")
        out = c.command("get canvas preservation kit")
        require(out, "canvas preservation kit")
        out = c.command("bridgework preserve")
        require_all(out, "physically changed", "canvas cover", "world event")
        out = c.command("inventory")
        assert "canvas preservation kit" not in out.lower(), (
            "Bridge kit survived consumption and can be reused"
        )
        out = c.command("look")
        require(out, "canvas cover")
        out = c.command("look plaque")
        require_all(out, "screws", "canvas cover")
        out = c.command("bridgework display")
        require(out, "already settled")
        out = c.command("bridgework check")
        require_all(out, "signed world event", "upkeep inspection")
        out = c.command("bridgework check")
        require(out, "already inspected")
        out = c.command("west")
        require(out, "riverside path")
        out = c.command("west")
        require(out, "blood of the vine")
        print("TELNET_BRANCHING_BRIDGE_CASE_GREEN")
        out = c.command("journal discoveries")
        require_all(out,
                    "weathered grave marker", "frayed red cord",
                    "crooked market scale", "river gauge",
                    "these are observations", "firsthand field discoveries")
        assert out.lower().count("day ") == 4, (
            "Repeat or remote looks duplicated field discoveries"
        )
        out = c.command("journal")
        require(out, "4 personally examined district")
        print("TELNET_FIRSTHAND_LANDMARK_DISCOVERIES_GREEN")
        print("TELNET_COOPERATIVE_DAILY_SURVEY_GREEN")

        # GDD T-09: Bram's existing routine can refill the physical
        # sideboard when he is present. Consume a bounded number of real
        # servings, check for truthful shortage, then eat alternate food.
        # Do not create a second stock owner or promise next-day magic.
        # Earlier a genuine hidden mushroom toxin caused queasiness.
        # If it still blocks eating, use the existing free well-water item
        # for bounded, actually measured relief rather than a fake cure.
        # Use the Innkeep account to test physical depletion so the
        # Chronicler's established conversation history with Bram is not
        # artificially evicted by a QA-only run of repetitive meals.
        inn.read_quiet()
        prior_body = inn.command("score deep")
        if "a small wave of queasiness" in prior_body.lower():
            relieved = False
            for _ in range(5):
                out = inn.command("drink water")
                require(out, "cold water")
                after_water = inn.command("score deep")
                if "a small wave of queasiness" not in after_water.lower():
                    relieved = True
                    break
            assert relieved, "Finite nausea had no playable relief through real water"
        bread_depleted = False
        for _ in range(7):  # source mechanical capacity is six
            out = inn.command("eat bread")
            if "all gone for now" in out.lower():
                bread_depleted = True
                require(out, "bram can replenish")
                break
            require(out, "bread", "rye")
        assert bread_depleted, "Repeated eating never depleted finite real bread"
        out = inn.command("eat cheese")
        require(out, "cheese bites back")
        print("TELNET_GDD_T09_DEPLETED_BREAD_ALTERNATE_REAL_FOOD_GREEN")
        out = c.command("west")
        require(out, "village square")
        # Only a co-located resident who can consult public signed evidence
        # recognizes actual work. The NPC's help bonus fires once per day,
        # while normal conversation remains possible and persistent.
        out = c.command("ask Miklós Farkas about route survey")
        require_all(
            out, "your signed inspection", "st. lazarus churchyard",
            "somebody actually walked",
        )
        out = c.command("talk Miklós Farkas")
        require(out, "already put your name")
        out = c.command("ask Miklós Farkas about survey")
        require(out, "your signed inspection")
        print("TELNET_RESIDENT_CIVIC_RECOGNITION_GREEN")
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
        if inn is not None:
            print("\nINNKEEP TRANSCRIPT\n" + "\n".join(inn.transcript))
        if smith is not None:
            print("\nSMITH TRANSCRIPT\n" + "\n".join(smith.transcript))
        if merchant is not None:
            print("\nMERCHANT TRANSCRIPT\n" + "\n".join(merchant.transcript))
        if mystic is not None:
            print("\nMYSTIC TRANSCRIPT\n" + "\n".join(mystic.transcript))
        if performer is not None:
            print("\nPERFORMER TRANSCRIPT\n" + "\n".join(performer.transcript))
        if wanderer is not None:
            print("\nWANDERER TRANSCRIPT\n" + "\n".join(wanderer.transcript))
        if hound is not None:
            print("\nHOUND TRANSCRIPT\n" + "\n".join(hound.transcript))
        raise
    finally:
        if hound is not None:
            hound.close()
        if wanderer is not None:
            wanderer.close()
        if performer is not None:
            performer.close()
        if mystic is not None:
            mystic.close()
        if merchant is not None:
            merchant.close()
        if smith is not None:
            smith.close()
        if inn is not None:
            inn.close()
        if h is not None:
            h.close()
        c.close()


if __name__ == "__main__":
    raise SystemExit(main())
