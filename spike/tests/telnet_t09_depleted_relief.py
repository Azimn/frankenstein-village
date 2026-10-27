#!/usr/bin/env python3
"""GDD T-09: normal, authenticated client survives depleted body-need relief.

Run AFTER the disposable QA setup. The sole connected player is a Smith,
not an Innkeep, with bread/cheese/stew exhausted. He cooks and eats a real
one-serving alternative from the same finite kitchen pantry, without an
agent-only privilege or offline mutation of the game's outcome.
"""
import argparse
import os
from telnet_playthrough import require, require_all
from telnet_t13_cancel import connect


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=4000)
    args = parser.parse_args()
    smith = None
    try:
        smith = connect(
            args.host, args.port, "qa_smith_repair",
            os.environ["FV_QA_REPAIR_PASSWORD"],
            "SmithTester", "The Blood of the Vine",
        )
        require(smith.command("calling"), "active calling: smith")
        initial = smith.command("score deep")
        require_all(initial, "hollow pressure", "hunger")

        for food in ("bread", "cheese", "stew"):
            out = smith.command(f"eat {food}")
            require_all(out, "all gone for now", "bram can replenish")

        guidance = smith.command("score deep")
        require_all(guidance, "soup ration", "eat plain broth",
                    "ingredients", "finite")
        kitchen = smith.command("soup")
        require_all(kitchen, "pantry day 4", "barley 1", "salt 1",
                    "soup ration")

        result = smith.command("soup ration")
        require_all(result, "real bowl of plain kitchen broth",
                    "barley", "salt", "world event")
        require(smith.command("inventory"), "a bowl of plain kitchen broth")

        second = smith.command("soup ration")
        require(second, "no complete broth ingredients")
        empty = smith.command("score deep")
        assert "soup ration" not in empty.lower(), (
            "Body guidance advertised depleted relief as available"
        )

        eaten = smith.command("eat plain broth")
        require_all(eaten, "plain broth", "settles a little of your hunger")
        reduced = smith.command("score deep")
        require_all(reduced, "empty, tugging sensation", "need a meal")
        repeated = smith.command("eat plain broth")
        require_all(repeated, "no serving left", "cannot eat")
        assert "hollow pressure" not in reduced.lower(), (
            "Physical broth did not reduce the hungriest body band"
        )
        print("TELNET_GDD_T09_ALL_FARE_DEPLETED_PANTRY_RELIEF_GREEN")
    finally:
        if smith is not None:
            smith.close()


if __name__ == "__main__":
    main()
