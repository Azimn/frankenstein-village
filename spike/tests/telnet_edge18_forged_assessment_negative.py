#!/usr/bin/env python3
"""EDGE-18: real authenticated player cannot treat using forged clinic history.

A stopped-server QA fixture has replaced today's patient assessment with a
well-formed replay of a prior patient's genuine signed event. This client exercises
the normal telnet login, active Healer Calling and clinic command dispatch.
"""
import argparse
from telnet_playthrough import require, require_all
from telnet_t13_cancel import connect


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=4000)
    args = parser.parse_args()
    healer = None
    try:
        healer = connect(
            args.host, args.port, "qa_healer_assessor",
            "HealerSmoke2026!", "HealerTester", "The Blood of the Vine",
        )
        require(healer.command("west"), "village square")
        require(healer.command("west"), "st. lazarus church")
        public = healer.command("clinic")
        require_all(public, "village day", "clinically approved",
                    "assessment has been recorded")
        assert all(x not in public.lower() for x in ("cold", "sprain", "fever")), (
            "Public status leaked private patient details"
        )
        require(healer.command("clinic records"), "patient's signed permission")
        out = healer.command("clinic treat supported")
        require(out, "assessment lacks a signed healer event")
        # The failure must not consume the treatment slot or create a receipt.
        require(healer.command("clinic treat supported"),
                "assessment lacks a signed healer event")
        require(healer.command("clinic assess"), "already assessed")
        # Leave the shared QA Healer at the Tavern using ordinary
        # player movement, never an offline fixture teleport.
        require(healer.command("east"), "village square")
        require(healer.command("east"), "blood of the vine")
        print("TELNET_GDD_EDGE18_AUTHENTICATED_FORGED_ASSESSMENT_REFUSED_GREEN")
    finally:
        if healer is not None:
            healer.close()


if __name__ == "__main__":
    main()
