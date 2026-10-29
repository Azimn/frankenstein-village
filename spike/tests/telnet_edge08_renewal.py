#!/usr/bin/env python3
"""Two independently authenticated ordinary players renew EDGE-08 next day."""
import argparse
import os
from telnet_playthrough import Client, require, require_all

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
        require(hound.command("ic HoundTester", wait=4), "blood of the vine")
        require(inn.command("ic InnkeepTester", wait=4), "blood of the vine")
        # Actual travel, no privileged movement or fabricated observation.
        for move, destination in (
            ("west", "village square"), ("west", "st. lazarus church"),
            ("west", "churchyard"), ("north", "northern treeline"),
        ):
            require(hound.command(move), destination)
        require(hound.command("survey protect"), "examine the physical red cord")
        require_all(hound.command("look cord"), "scarlet cord", "caution marker")
        # Old marker cannot be passed off as a current-day signed inspection.
        require(hound.command("survey dispatch"), "look at the physical signed red cord after")
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
        require(inn.command("soup refuge HoundTester"), "named logged-in hound is not here")
        for move, destination in (
            ("south", "churchyard"), ("east", "st. lazarus church"),
            ("east", "village square"), ("east", "blood of the vine"),
        ):
            require(hound.command(move), destination)
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
