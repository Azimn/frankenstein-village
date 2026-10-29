#!/usr/bin/env python3
"""Two independently authenticated ordinary players renew EDGE-08 next day."""
import argparse
import os
from telnet_playthrough import Client, require, require_all

def entered_room(response, mask):
    """Use the room title after successful IC, not exit hints in its prose."""
    marker = f"You become {mask}."
    if marker not in response:
        raise AssertionError(f"No authenticated IC entry for {mask}: {response[-600:]}")
    lines = (line.strip() for line in response.split(marker, 1)[1].splitlines())
    room = next((line for line in lines if line), "")
    if not room:
        raise AssertionError(f"No room heading after IC entry for {mask}")
    return room.lower()

def assert_room(client, title):
    """Require the ordinary client's current look to show an exact room heading."""
    response = client.command("look")
    headings = {line.strip().lower() for line in response.splitlines()}
    if title.lower() not in headings:
        raise AssertionError(f"Expected current room {title!r}, got: {response[-700:]}")

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--host", required=True)
    parser.add_argument("--port", required=True, type=int)
    args = parser.parse_args()
    hound = Client(args.host, args.port)
    inn = Client(args.host, args.port)
    try:
        for client in (hound, inn):
            require(client.sync_login_screen(), "frankenstein village")
        password = os.environ["FV_QA_REPAIR_PASSWORD"]
        require(hound.command(f"connect qa_hound_protection {password}", wait=4),
                "connected", "account qa_hound_protection")
        inn_password = "Innkeep" + "Smoke" + "2026!"
        require(inn.command(f"connect qa_innkeep_care {inn_password}", wait=4),
                "connected", "account qa_innkeep_care")
        entry = hound.command("ic HoundTester", wait=4)
        inn_entry = inn.command("ic InnkeepTester", wait=4)
        inn_room = entered_room(inn_entry, "InnkeepTester")
        hound_room = entered_room(entry, "HoundTester")
        # An unplaced returning mask must recover backstage and walk through
        # the same public front door as every other player.
        if "private room" in inn_room:
            inn_steps = (
                ("down", "inn common room"), ("east", "inn hallway"),
                ("south", "village square"), ("east", "blood of the vine"),
            )
        elif inn_room == "inn common room":
            inn_steps = (
                ("east", "inn hallway"), ("south", "village square"),
                ("east", "blood of the vine"),
            )
        elif inn_room == "village square":
            inn_steps = (("east", "blood of the vine"),)
        elif inn_room == "the blood of the vine":
            inn_steps = ()
        else:
            raise AssertionError("Unexpected Innkeep starting room: " + inn_entry[-600:])
        for move, destination in inn_steps:
            require(inn.command(move), destination)
        # Respect the actual persisted Hound location after prior independent
        # regressions. All travel uses ordinary room exits, never shell moves.
        if hound_room == "the blood of the vine":
            steps = (
                ("west", "village square"), ("west", "st. lazarus church"),
                ("west", "churchyard"), ("north", "northern treeline"),
            )
        elif "private room" in hound_room:
            steps = (
                ("down", "inn common room"), ("east", "inn hallway"),
                ("south", "village square"), ("west", "st. lazarus church"),
                ("west", "churchyard"), ("north", "northern treeline"),
            )
        elif hound_room == "village square":
            steps = (
                ("west", "st. lazarus church"), ("west", "churchyard"),
                ("north", "northern treeline"),
            )
        elif hound_room == "the northern treeline":
            steps = ()
        else:
            raise AssertionError("Unexpected Hound starting room: " + entry[-600:])
        for move, destination in steps:
            require(hound.command(move), destination)
        assert_room(inn, "The Blood of the Vine")
        assert_room(hound, "The Northern Treeline")
        require(hound.command("survey protect"), "examine the physical red cord")
        require_all(hound.command("look cord"), "scarlet cord", "caution marker")
        # Old marker cannot be passed off as a current-day signed inspection.
        require(hound.command("survey dispatch"), "A fresh signed Hound warning is required today")
        require_all(hound.command("survey protect"),
                    "tie the original frayed cord", "visible warning", "signed event")
        require(hound.command("survey protect"), "already signed today")
        require_all(hound.command("survey"), "re-tied", "signed event")
        # The pre-renewal look was not an observation of the NEW marker.
        require(hound.command("survey dispatch"), "look at the physical signed red cord after")
        require_all(hound.command("look cord"), "scarlet cord", "clear caution marker")
        require_all(hound.command("survey dispatch"),
                    "physical signed treeline refuge dispatch", "event")
        require(hound.command("survey dispatch"), "already left this cord today")
        require(hound.command("inventory"), "signed treeline refuge dispatch")
        # The Innkeep must really remain in the Tavern while the Hound is remote.
        assert_room(inn, "The Blood of the Vine")
        assert_room(hound, "The Northern Treeline")
        require(inn.command("soup refuge HoundTester"), "named logged-in hound is not here")
        for move, destination in (
            ("south", "churchyard"), ("east", "st. lazarus church"),
            ("east", "village square"), ("east", "blood of the vine"),
        ):
            require(hound.command(move), destination)
        assert_room(hound, "The Blood of the Vine")
        assert_room(inn, "The Blood of the Vine")
        hound.read_quiet()
        inn.read_quiet()
        require(hound.command("soup refuge HoundTester"), "only an active innkeep")
        require_all(inn.command("soup refuge HoundTester"),
                    "one real bowl of refuge soup", "dispatch is consumed",
                    "turnip portions remain")
        require(inn.command("soup refuge HoundTester"),
                "exactly one physical refuge dispatch")
        require_all(inn.command("look soup pot"),
                    "2 signed hound arrival meal(s)", "pantry day")
        print("TELNET_GDD_EDGE08_LATER_DAY_TWO_ACCOUNT_RENEWAL_GREEN")
    finally:
        hound.close()
        inn.close()

if __name__ == "__main__":
    main()
