#!/usr/bin/env python3
"""EDGE-28 migrated-world normal-client replay on both sides of a real restart.

The legacy decoy is seeded by the runner after the first telnet suite. This
script uses two separate authenticated player sockets, never an admin command.
The runner's independent shell checks validate which physical object moved.
"""
import argparse
import os
import re

from telnet_playthrough import require, require_all
from telnet_t13_cancel import connect


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=4000)
    parser.add_argument("--phase", choices=("before", "after", "release"), required=True)
    args = parser.parse_args()

    healer = detective = None
    try:
        healer = connect(
            args.host, args.port, "qa_healer_assessor", "HealerSmoke2026!",
            "HealerTester",
            ("The Blood of the Vine" if args.phase == "before" else
             "Village Square" if args.phase == "release" else "St. Lazarus Church"),
        )
        if args.phase != "release":
            detective = connect(
                args.host, args.port, "qa_detective_clinic",
                os.environ["FV_QA_REPAIR_PASSWORD"],
                "DetectiveClinicTester", "St. Lazarus Church",
            )

        if args.phase == "before":
            require(healer.command("west"), "village square")
            require(healer.command("west"), "st. lazarus church")

        if args.phase != "release":
            # Two independently signed roles see the same public record. Neither
            # role can substitute for the other's permission or create a second
            # signed inquiry for an already completed cot.
            public = detective.command("clinic")
            # Room-arrival broadcasts may precede the command reply on telnet.
            # Privacy applies to the actual clinic report, not public movement.
            require(public, "St. Lazarus village clinic")
            clinic_report = public.lower().split("st. lazarus village clinic", 1)[1]
            assert "healertester" not in clinic_report
            assert "cold" not in clinic_report
            signed_today = "independent procedural clinic inquiry signed" in clinic_report
            if signed_today:
                require_all(clinic_report, "competing interpretations",
                            "physical specimen",
                            "neither causal explanation is proven")
            else:
                # Real elapsed-time restart can advance the village clock.
                # Yesterday's signed inquiry remains in the persistent cot and
                # canonical ledger (verified by post_restart_assertions.py),
                # but must NEVER be presented as today's patient inquiry.
                assert args.phase == "after", clinic_report
                match = re.search(r"village day (\d+)", clinic_report)
                assert match and int(match.group(1)) > 1, clinic_report
                require_all(clinic_report,
                            "no examination has been completed yet",
                            "no independent detective inquiry has been signed for today's")
            require(detective.command("clinic records"),
                    "private clinical notes require an attending healer")
            attempted = detective.command("clinic investigate illness")
            require(attempted, "already has an independent inquiry" if signed_today
                    else "look at the original clinic cot before investigating")
            require(healer.command("clinic investigate exposure"),
                    "only an active detective")
            private = healer.command("clinic records")
            if signed_today:
                require_all(private, "confidential", "patient permission")
            else:
                require(private, "signed permission")
                assert "healertester" not in private.lower()
                assert "cold" not in private.lower()
            require(healer.command("calling"), "clinic assess 1")
            require(detective.command("calling"), "clinic inquiry 1")

        if args.phase == "before":
            require(healer.command("east"), "village square")
            # The square contains the deliberately forged same-name, copied-
            # source/toxin decoy AND genuine registered well growth. Ordinary
            # unnumbered pickup must prefer the latter, verified by the
            # runner's exact-ID physical custody assertion after disconnect.
            require(healer.command("get mushrooms"), "pick up")
            require(healer.command("inventory"), "cluster of mushrooms")
            require(healer.command("west"), "st. lazarus church")
            print("TELNET_GDD_EDGE28_MIGRATED_PRE_RESTART_TWO_ACCOUNT_GREEN")
        elif args.phase == "after":
            # Stop with the re-picked specimen still in custody. The runner
            # must inspect the exact persistent ID and reject the forged decoy
            # BEFORE allowing the final ordinary-client drop.
            require(healer.command("inventory"), "cluster of mushrooms")
            require(healer.command("east"), "village square")
            require(healer.command("drop mushrooms"), "drop")
            require(healer.command("get mushrooms"), "pick up")
            require(healer.command("inventory"), "cluster of mushrooms")
            print("TELNET_GDD_EDGE28_MIGRATED_REPICK_PENDING_ID_PROOF_GREEN")
        else:
            # Reconnect the same account after the independent stopped-server
            # custody oracle and return the genuine item through normal play.
            require(healer.command("inventory"), "cluster of mushrooms")
            require(healer.command("drop mushrooms"), "drop")
            require(healer.command("west"), "st. lazarus church")
            print("TELNET_GDD_EDGE28_MIGRATED_POST_RESTART_TWO_ACCOUNT_GREEN")
    finally:
        for client in (detective, healer):
            if client is not None:
                client.close()


if __name__ == "__main__":
    main()
