#!/usr/bin/env python3
"""GDD-EDGE-18: live supported care for a later visitor on the certified cot.

The QA setup begins on village day two, but the actual Evennia clock may
advance while the authenticated negative and real restart tests execute.
Read the observed day rather than rewinding the clock or inventing a patient.
Every patient action uses normal telnet commands, not a shell bypass.
"""
import argparse
import re
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
        require(public, "clinically approved")
        match = re.search(r"village day (\\d+):", public, re.IGNORECASE)
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

        # The original day-one compress does not count as care for the
        # later visitor, whatever real village day the server has reached.
        require(healer.command("clinic treat supported"),
                "examine the actual patient first")
        out = healer.command("clinic assess")
        require_all(out, "assess the visiting patient", condition,
                    "signed world event")
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
        print(f"TELNET_GDD_EDGE18_LATER_DAY_SUPPORTED_CARE_TWO_ACCOUNT_GREEN day={patient_day}")
        if patient_day == 2:
            print("TELNET_GDD_EDGE18_DAY_TWO_SUPPORTED_CARE_TWO_ACCOUNT_GREEN")
    finally:
        for client in (smith, healer):
            if client is not None:
                client.close()


if __name__ == "__main__":
    main()
