#!/usr/bin/env python3
"""GDD-EDGE-18: live day-two supported care on the original certified cot.

The disposable QA clock is advanced by the existing T-13 fixture. Every
patient action here uses ordinary authenticated telnet commands. This is
scripted verification, not an uncoached acceptance session.
"""
import argparse
from telnet_playthrough import require, require_all
from telnet_t13_cancel import connect


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=4000)
    args = parser.parse_args()
    healer = smith = None
    try:
        healer = connect(args.host, args.port, "qa_healer_assessor",
                         "HealerSmoke2026!", "HealerTester",
                         "The Blood of the Vine")
        smith = connect(args.host, args.port, "qa_smith_repair",
                        __import__("os").environ["FV_QA_REPAIR_PASSWORD"],
                        "SmithTester", "Village Square")
        require(healer.command("clinic assess"), "st. lazarus church")
        require(healer.command("west"), "village square")
        require(healer.command("west"), "st. lazarus church")
        require(smith.command("west"), "st. lazarus church")

        public = smith.command("clinic")
        require_all(public, "village day 2", "clinically approved")
        assert "sprain" not in public.lower(), "Public status leaked day-two diagnosis"
        require(smith.command("clinic records"), "attending healer")
        require(smith.command("clinic treat supported"), "active healer")
        require(smith.command("clinic assess"), "active healer")

        # The original day-one compress does not count as treatment of the
        # day-two visitor. A real new assessment is mandatory.
        require(healer.command("clinic treat supported"),
                "examine the actual patient first")
        out = healer.command("clinic assess")
        require_all(out, "assess the visiting patient", "sprain",
                    "signed world event")
        require(healer.command("clinic records"), "patient's signed permission")
        out = healer.command("clinic treat supported")
        require_all(out, "carry out supported treatment", "sprain",
                    "signed as world event")
        require(healer.command("clinic treat supported"),
                "already received treatment")
        require(healer.command("clinic assess"), "already assessed")

        smith.read_quiet()
        public = smith.command("clinic")
        require_all(public, "care has been provided", "clinically approved")
        assert "sprain" not in public.lower(), "Public care leaked patient finding"
        assert "healertester" not in public.lower(), "Public care leaked examiner"
        require(smith.command("clinic records"), "attending healer")
        print("TELNET_GDD_EDGE18_DAY_TWO_SUPPORTED_CARE_TWO_ACCOUNT_GREEN")
    finally:
        for client in (smith, healer):
            if client is not None:
                client.close()


if __name__ == "__main__":
    main()
