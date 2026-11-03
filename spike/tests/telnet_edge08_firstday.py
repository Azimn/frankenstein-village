#!/usr/bin/env python3
"""Authenticated EDGE-08 first-day source, dispatch, finite meal and denial."""
import argparse
import os
from telnet_playthrough import Client, require, require_all


def entry_room(response, mask):
    marker = f"You become {mask}."
    if marker not in response:
        raise AssertionError(f"Missing ordinary IC entry for {mask}: {response[-600:]}")
    lines = (line.strip().lower() for line in response.split(marker, 1)[1].splitlines())
    return next((line for line in lines if line), "")


def move_path(client, steps):
    for direction, expected in steps:
        require(client.command(direction), expected)


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
        require(hound.command(f"connect qa_refuge_hound {password}", wait=4),
                "connected", "account qa_refuge_hound")
        require(hound.command("charcreate RefugeHoundTester", wait=3),
                "refugehoundtester")
        entry = hound.command("ic RefugeHoundTester", wait=4)
        assert "private room" in entry_room(entry, "RefugeHoundTester")
        require(hound.command("calling choose hound"),
                "hound is now your active calling")
        move_path(hound, (
            ("down", "inn common room"), ("east", "inn hallway"),
            ("south", "village square"), ("west", "st. lazarus church"),
            ("west", "churchyard"), ("north", "northern treeline"),
        ))
        # A different ordinary Hound account already signed the marker in
        # the main playthrough. The new Hound must look AFTER that event.
        require(hound.command("survey dispatch"), "look at the physical red cord")
        require_all(hound.command("look cord"), "scarlet cord", "caution marker")
        require_all(hound.command("survey dispatch"),
                    "physical signed treeline refuge dispatch", "event")
        require(hound.command("survey dispatch"), "already left this cord today")
        require(hound.command("inventory"), "signed treeline refuge dispatch")

        require(inn.command("connect qa_innkeep_care InnkeepSmoke2026!", wait=4),
                "connected", "account qa_innkeep_care")
        inn_entry = inn.command("ic InnkeepTester", wait=4)
        start = entry_room(inn_entry, "InnkeepTester")
        paths = {
            "the blood of the vine": (),
            "village square": (("east", "blood of the vine"),),
            "inn common room": (("east", "inn hallway"),
                                ("south", "village square"),
                                ("east", "blood of the vine")),
        }
        if "private room" in start:
            steps = (("down", "inn common room"),) + paths["inn common room"]
        elif start in paths:
            steps = paths[start]
        else:
            raise AssertionError(f"Unexpected Innkeep location {start!r}")
        move_path(inn, steps)
        require(inn.command("soup refuge RefugeHoundTester"),
                "named logged-in hound is not here")
        move_path(hound, (
            ("south", "churchyard"), ("east", "st. lazarus church"),
            ("east", "village square"), ("east", "blood of the vine"),
        ))
        hound.read_quiet()
        inn.read_quiet()
        require(hound.command("soup refuge RefugeHoundTester"),
                "only an active innkeep")
        require_all(inn.command("soup refuge RefugeHoundTester"),
                    "one real bowl of refuge soup", "dispatch is consumed",
                    "turnip portions remain")
        inventory = hound.command("inventory")
        require(inventory, "bowl of hound refuge soup")
        assert "signed treeline refuge dispatch" not in inventory.lower()
        require(inn.command("soup refuge RefugeHoundTester"),
                "exactly one physical refuge dispatch")
        require_all(inn.command("look soup pot"),
                    "1 signed hound arrival meal", "pantry day")
        print("TELNET_GDD_EDGE08_TWO_ACCOUNT_FINITE_HOUND_REFUGE_GREEN")
    finally:
        hound.close()
        inn.close()


if __name__ == "__main__":
    main()
