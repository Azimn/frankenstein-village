#!/usr/bin/env python3
"""GDD T-03: a real post-restart lamp repair retry cannot reopen the case.

The first playthrough already completed the Smith/Merchant repair. After an
actual Evennia server process restart, the same authenticated Smith attempts
the ordinary repair verb again. No offline fixture performs the action.
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

    smith = merchant = None
    try:
        smith = connect(
            args.host, args.port, "qa_smith_repair",
            os.environ["FV_QA_REPAIR_PASSWORD"], "SmithTester",
            "The Blood of the Vine",
        )
        before = smith.command("repair")
        require_all(before, "repair complete", "north-square gas lamp is working again")
        require(smith.command("west"), "village square")
        require(smith.command("calling"), "repair completions 1")

        retry = smith.command("repair finish north-square gas lamp")
        require(retry, "already complete")
        after = smith.command("repair")
        require_all(after, "repair complete", "north-square gas lamp is working again")
        require(smith.command("calling"), "repair completions 1")
        smith_agenda = smith.command("agenda")
        # The original Smith actually completed the repair. The agenda must
        # acknowledge this mask's signed contribution, not misattribute it
        # to another account. The case must still remain closed after restart.
        require(smith_agenda, "Your contribution is recorded")
        require_all(smith_agenda, "north-square gas lamp is repaired",
                    "no repeat repair is needed")
        print("TELNET_GDD_T16_POST_RESTART_COMMISSION_OUTCOME_GREEN")
        print("TELNET_GDD_T03_POST_RESTART_REPAIR_RETRY_DENIED_GREEN")

        # A different authenticated player must not reopen the already
        # completed cross-Calling transaction or spend a second part.
        merchant = connect(
            args.host, args.port, "qa_merchant_repair",
            os.environ["FV_QA_REPAIR_PASSWORD"], "MerchantTester",
            "The Blood of the Vine",
        )
        require(merchant.command("repair"), "repair complete")
        require(merchant.command("calling"), "repair procurements 1")
        require(merchant.command("repair procure"), "already procured")
        require(merchant.command("west"), "village square")
        require(
            merchant.command("repair finish north-square gas lamp"),
            "already complete",
        )
        require(merchant.command("calling"), "repair procurements 1")
        require(merchant.command("repair"), "working again")
        require_all(merchant.command("agenda"),
                    "north-square gas lamp is repaired",
                    "no repeat repair is needed")
        require(smith.command("calling"), "repair completions 1")
        print("TELNET_GDD_T16_POST_RESTART_LAMP_AGENDA_GREEN")
        print("TELNET_GDD_T03_TWO_ROLE_POST_RESTART_REPLAY_DENIED_GREEN")
    finally:
        for client in (merchant, smith):
            if client is not None:
                client.close()


if __name__ == "__main__":
    main()
