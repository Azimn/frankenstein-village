#!/usr/bin/env python3
"""Two ordinary-player sockets light and maintain the public Square fire.

This is a nonprofessional activity. All state-changing actions go through
normal authenticated telnet commands and physically carried wood, never a
builder shell or a hidden AI-only action.
"""
import argparse
import os

from telnet_playthrough import agent_json, require, require_all
from telnet_t13_cancel import connect


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--host", default="127.0.0.1")
    p.add_argument("--port", type=int, default=4000)
    args = p.parse_args()
    smith = merchant = None
    try:
        pw = os.environ["FV_QA_REPAIR_PASSWORD"]
        smith = connect(
            args.host, args.port, "qa_smith_repair", pw,
            "SmithTester", "Village Square",
        )
        merchant = connect(
            args.host, args.port, "qa_merchant_repair", pw,
            "MerchantTester", "Village Square",
        )
        require_all(smith.command("guide"), "another shared village project",
                    "brazier light", "public")
        require_all(smith.command("look brazier"),
                    "broad iron basin", "cold", "woodpile")
        require_all(smith.command("brazier"), "warming brazier",
                    "cold", "hearth gather")
        before = smith.command("score deep")
        require_all(before, "a moment inside your character's body", "shivering")
        require(smith.command("brazier feed"), "cold; light it before feeding")

        light = smith.command("brazier light")
        require_all(light, "real bundle of firewood",
                    "6 village hour(s)", "signed world event")
        require_all(smith.command("look brazier"), "logs glow", "6 more")
        require_all(smith.command("brazier"), "last supplied by smithtester",
                    "6 more")
        # This is a new low-population warmth alternative; no role checks.
        body = smith.command("score deep")
        require_all(body, "public square brazier is actually burning nearby",
                    "finite hours")
        agent = agent_json(smith.command("agent"))
        assert any("public square brazier" in text.lower()
                   for text in agent["embodiment"]["possible_relief"]), (
            "Human first-person and agent body advice disagree"
        )

        carried = merchant.command("inventory")
        if "bundle of firewood" not in carried.lower():
            require(merchant.command("hearth gather"), "real bundle")
        fed = merchant.command("brazier feed")
        require_all(fed, "real bundle of firewood",
                    "10 village hour(s)", "signed world event")
        require_all(smith.command("look"), "logs glow", "10 more")
        require_all(merchant.command("brazier"),
                    "last supplied by merchanttester", "10 more")
        # Neither can spend the same item twice. Errors are ordinary
        # actionable text, not traceback or free virtual firewood.
        second = smith.command("brazier light")
        require(second, "carry a real bundle")
        second = merchant.command("brazier feed")
        require(second, "carry a real bundle")
        require(merchant.command("east"), "blood of the vine")
        require(merchant.command("brazier feed"), "travel to village square")
        require(merchant.command("west"), "village square")
        print("TELNET_SQUARE_BRAZIER_TWO_PLAYER_REAL_WOOD_AND_WARMTH_GREEN")
    finally:
        for client in (merchant, smith):
            if client is not None:
                client.close()


if __name__ == "__main__":
    main()
