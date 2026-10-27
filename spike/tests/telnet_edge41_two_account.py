#!/usr/bin/env python3
"""EDGE-41 authenticated two-account scene, real travel and signed actions."""
import argparse
import os
from telnet_playthrough import Client, require, require_all

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--host", required=True)
    parser.add_argument("--port", required=True, type=int)
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
        require(hound.command("ic HoundTester", wait=4), "village square")
        require(performer.command("ic PerformerTester", wait=4), "village square")
        require(performer.command("east"), "blood of the vine")
        require(performer.command("stage adapt indoor"), "no verified current physical source")
        require(performer.command("stage warn"), "only an active hound")
        require(hound.command("stage warn"), "visit the real stage")
        for move, destination in (
            ("west", "st. lazarus church"), ("west", "churchyard"),
            ("north", "northern treeline"),
        ):
            require(hound.command(move), destination)
        require(hound.command("survey protect"), "examine the physical red cord")
        require(hound.command("look cord"), "scarlet cord")
        require_all(hound.command("survey protect"), "visible warning", "signed event")
        for move, destination in (
            ("south", "churchyard"), ("east", "st. lazarus church"),
            ("east", "village square"), ("east", "blood of the vine"),
        ):
            require(hound.command(move), destination)
        require(hound.command("stage adapt indoor"), "only an active hound")
        require_all(hound.command("stage warn"), "verified", "world event")
        require(hound.command("stage warn"), "already signed")
        require(performer.command("stage perform ballad"), "rehearse that piece")
        require(performer.command("stage rehearse ballad"), "rehearse the ballad")
        require_all(performer.command("stage adapt indoor"), "indoor", "world event")
        require(performer.command("stage adapt cancel"), "already signed")
        require_all(performer.command("stage perform ballad"), "actually perform", "world event")
        require(performer.command("stage warn"), "only an active hound")
        require_all(performer.command("stage"), "hound signed", "performer chose indoor",
                    "actually performed")
        require(hound.command("stage witness"), "actually witnessed")
        require(hound.command("stage witness"), "already witnessed")
        print("TELNET_GDD_EDGE41_INDEPENDENT_HOUND_PERFORMER_INDOOR_SHOW_GREEN")
    finally:
        hound.close()
        performer.close()

if __name__ == "__main__":
    main()
