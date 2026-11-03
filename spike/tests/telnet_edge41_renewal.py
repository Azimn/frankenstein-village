#!/usr/bin/env python3
"""Two ordinary authenticated accounts renew a physical Hound warning next day."""
import argparse
import os
from telnet_playthrough import Client, require, require_all

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--host", required=True)
    parser.add_argument("--port", required=True, type=int)
    parser.add_argument("--third-day", action="store_true")
    args = parser.parse_args()
    hound = Client(args.host, args.port)
    performer = Client(args.host, args.port)
    try:
        for client in (hound, performer):
            require(client.sync_login_screen(), "frankenstein village")
        password = os.environ["FV_QA_REPAIR_PASSWORD"]
        require(hound.command(f"connect qa_hound_protection {password}", wait=4),
                "connected", "account qa_hound_protection")
        require(performer.command(f"connect qa_performer_stage {password}", wait=4),
                "connected", "account qa_performer_stage")
        require(hound.command("ic HoundTester", wait=4), "blood of the vine")
        require(performer.command("ic PerformerTester", wait=4), "blood of the vine")
        require(performer.command("stage adapt cancel"),
                "no verified current physical source")
        for move, destination in (
            ("west", "village square"), ("west", "st. lazarus church"),
            ("west", "churchyard"), ("north", "northern treeline"),
        ):
            require(hound.command(move), destination)
        require(hound.command("survey protect"), "examine the physical red cord")
        require_all(hound.command("look cord"), "scarlet cord", "caution marker")
        require_all(hound.command("survey protect"), "visible warning", "signed event")
        require(hound.command("survey protect"), "already signed today")
        require_all(hound.command("survey"), "re-tied", "signed event")
        for move, destination in (
            ("south", "churchyard"), ("east", "st. lazarus church"),
            ("east", "village square"), ("east", "blood of the vine"),
        ):
            require(hound.command(move), destination)
        require_all(hound.command("stage warn"), "verified", "world event")
        require_all(performer.command("stage adapt cancel"), "cancel", "world event")
        require(performer.command("stage perform ballad"), "cancelled")
        require_all(performer.command("stage"), "hound signed", "performer chose cancel",
                    "no public performance")
        if args.third_day:
            print("TELNET_GDD_EDGE41_THIRD_DAY_SIGNED_WARNING_AND_CANCEL_GREEN")
        else:
            print("TELNET_GDD_EDGE41_LATER_DAY_SIGNED_WARNING_AND_CANCEL_GREEN")
    finally:
        hound.close()
        performer.close()

if __name__ == "__main__":
    main()
