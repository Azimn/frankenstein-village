#!/usr/bin/env python3
"""EDGE-02: real later-day Smith fitting and independent Innkeep service.

This is executed after T-13's day-four recovery and its restart assertions.
Only authenticated ordinary-player commands perform the physical repair.
The village clock is observed, never reset or backdated by this client.
"""
import argparse
import os
import re

from telnet_playthrough import require, require_all
from telnet_t13_cancel import connect


def workshop_stock(text):
    match = re.search(r"Village day (\d+): (\d+) of 2 iron offcuts", text, re.I)
    assert match, "The public Workshop did not expose its finite daily stock"
    return int(match.group(1)), int(match.group(2))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=4000)
    args = parser.parse_args()
    smith = inn = None
    try:
        smith = connect(args.host, args.port, "qa_smith_kitchen",
                        os.environ["FV_QA_REPAIR_PASSWORD"],
                        "KitchenSmithTester", "market workshop")
        inn = connect(args.host, args.port, "qa_innkeep_care",
                      "InnkeepSmoke2026!", "InnkeepTester",
                      "blood of the vine")
        day, before = workshop_stock(smith.command("workshop"))
        assert day >= 4, "The kitchen fitting was not deferred beyond day one"
        assert 1 <= before <= 2, "No finite iron remains for the kitchen repair"
        require(inn.command("soup simmer"),
                "restricted until the real kitchen pot is repaired")
        require(smith.command("soup repair"),
                "physically at The Blood of the Vine")
        out = smith.command("workshop forge")
        require_all(out, "real transferable iron market hinge",
                    "world event")
        next_day, after = workshop_stock(smith.command("workshop"))
        assert next_day == day and after == before - 1, (
            "The signed kitchen forge did not spend exactly one real offcut"
        )
        require(smith.command("inventory"), "forged market hinge")
        for direction, expected in (
            ("west", "market lane"), ("north", "lamp shop"),
            ("north", "village square"), ("east", "blood of the vine"),
        ):
            require(smith.command(direction), expected)
        require(inn.command("soup repair"), "active Smith Calling")
        out = smith.command("soup repair")
        require_all(out, "install and consume the physical forged hinge",
                    "signed world event")
        require_all(inn.command("look soup pot"),
                    "physically repaired by kitchensmithtester", "signed event")
        require(inn.command("soup simmer"), "carry one real prepared packet")
        require(inn.command("soup restrict"),
                "already restricted, repaired, or invalid")
        assert "forged market hinge" not in smith.command("inventory").lower()
        require(smith.command("soup repair"), "carry one real forged iron hinge")
        print(f"TELNET_GDD_EDGE02_LATER_DAY_TWO_ACCOUNT_FINITE_KITCHEN_GREEN day={day}")
    finally:
        for client in (inn, smith):
            if client is not None:
                client.close()


if __name__ == "__main__":
    main()
