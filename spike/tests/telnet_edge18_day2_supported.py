#!/usr/bin/env python3
"""GDD-EDGE-18: live supported care for a later visitor on the certified cot.

The QA setup begins on village day two, but the actual Evennia clock may
advance while the authenticated negative and real restart tests execute.
Read the observed day rather than rewinding the clock or inventing a patient.
Every patient action uses normal telnet commands, not a shell bypass.
"""
import argparse
import re
from telnet_playthrough import Client, require, require_all
from telnet_t13_cancel import connect


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=4000)
    args = parser.parse_args()
    healer = smith = cot_smith = None
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

        # The Market and stage consumed both offcuts on day one.
        # A new ordinary Smith uses one actual offcut on this later day.
        cot_smith = Client(args.host, args.port)
        require(cot_smith.sync_login_screen(), "frankenstein village")
        password = __import__("os").environ["FV_QA_REPAIR_PASSWORD"]
        out = cot_smith.command(f"connect qa_smith_cot {password}", wait=4.0)
        require(out, "connected", "account qa_smith_cot")
        cot_smith.command("charcreate CotSmithTester", wait=3.0)
        require(cot_smith.command("ic CotSmithTester", wait=4.0), "private room")
        require(cot_smith.command("calling choose smith"),
                "smith is now your active calling")
        for move, destination in (
            ("down", "inn common room"), ("east", "inn hallway"),
            ("south", "village square"), ("south", "lamp shop"),
            ("south", "market lane"), ("east", "market workshop"),
        ):
            require(cot_smith.command(move), destination)
        out = cot_smith.command("workshop forge")
        require_all(out, "real transferable iron market hinge",
                    "1 iron offcut remains")
        for move, destination in (
            ("west", "market lane"), ("north", "lamp shop"),
            ("north", "village square"), ("west", "st. lazarus church"),
        ):
            require(cot_smith.command(move), destination)
        require(cot_smith.command("look clinic cot"), "worn hinge")
        require(cot_smith.command("clinic certify"), "active healer")
        require(healer.command("clinic brace"), "active smith")
        require_all(cot_smith.command("clinic brace"),
                    "physically brace", "signed world event")
        assert "forged market hinge" not in cot_smith.command("inventory").lower()
        require(cot_smith.command("clinic brace"), "carry one real")
        require(cot_smith.command("clinic treat supported"), "active healer")

        public = smith.command("clinic")
        require(public, "An independent Healer must assess today\'s patient")
        match = re.search(r"village day (\d+):", public, re.IGNORECASE)
        assert match, "Clinic status did not report its actual village day"
        patient_day = int(match.group(1))
        assert patient_day >= 2, "The later patient was not available"
        # Patient condition rotates in the existing clinic_state service.
        # This test must not forge an earlier day just to expect a sprain.
        condition = ("cold", "sprain", "fever")[(patient_day - 1) % 3]
        assert condition not in public.lower(), "Public status leaked patient details"
        require(smith.command("clinic records"), "attending healer")
        require(smith.command("clinic treat supported"), "active healer")
        require(smith.command("clinic assess"), "active healer")

        # The old patient's care cannot certify this new patient.
        require(healer.command("clinic treat supported"),
                "independently certified cot")
        out = healer.command("clinic assess")
        require_all(out, "assess the visiting patient", condition,
                    "signed world event")
        require_all(healer.command("clinic certify"),
                    "clinically approve", "signed world event")
        require(smith.command("clinic"), "clinically approved")
        require(healer.command("clinic certify"),
                "real smith fitting must be installed before approval")
        require(healer.command("clinic records"), "patient's signed permission")
        out = healer.command("clinic treat supported")
        require_all(out, "carry out supported treatment", condition,
                    "signed as world event")
        require(healer.command("clinic treat supported"),
                "already received treatment")
        require(healer.command("clinic assess"), "already assessed")

        smith.read_quiet()
        public = smith.command("clinic")
        require_all(public, "care has been provided", "clinically approved")
        assert condition not in public.lower(), "Public care leaked patient finding"
        assert "healertester" not in public.lower(), "Public care leaked examiner"
        require(smith.command("clinic records"), "attending healer")
        # Keep the shared QA Healer at the Tavern for subsequent scripted
        # tests; relocation is performed by the real logged-in character.
        require(healer.command("east"), "village square")
        require(healer.command("east"), "blood of the vine")
        print(f"TELNET_GDD_EDGE18_LATER_DAY_SUPPORTED_CARE_TWO_ACCOUNT_GREEN day={patient_day}")
        if patient_day == 2:
            print("TELNET_GDD_EDGE18_DAY_TWO_SUPPORTED_CARE_TWO_ACCOUNT_GREEN")
    finally:
        for client in (cot_smith, smith, healer):
            if client is not None:
                client.close()


if __name__ == "__main__":
    main()
