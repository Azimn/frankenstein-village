#!/usr/bin/env python3
"""Exercise day-two cancellation with two authenticated, ordinary telnet clients."""
import argparse
import os
from telnet_playthrough import Client, require, require_all

def connect(host, port, username, password, character, expected_room):
    client = Client(host, port)
    require(client.sync_login_screen(), "frankenstein village")
    # Do not echo test credentials in the CI command transcript.
    client.sock.sendall(f"connect {username} {password}\n".encode("utf-8"))
    require(client.read_quiet(max_wait=4), "connected", "account")
    out = client.command(f"ic {character}", wait=4)
    require(out, expected_room.lower())
    return client

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=4000)
    args = parser.parse_args()
    password = os.environ["FV_QA_REPAIR_PASSWORD"]
    supplier = carrier = None
    try:
        supplier = connect(args.host, args.port, "qa_smith_repair", password,
                           "SmithTester", "Village Square")
        carrier = connect(args.host, args.port, "qa_merchant_repair", password,
                          "MerchantTester", "The Blood of the Vine")
        # The server was genuinely restarted and the village clock is now
        # on day two. Earlier players' signed route work must remain legible
        # to an ordinary account, without treating dated caution as truth now.
        history = supplier.command("survey history")
        require_all(history, "signed village route history", "village day 1",
                    "wanderertester", "houndtester", "unmarked cord",
                    "not proof of what caused a hazard")
        # Exact-day history uses the same persisted Square records, not a
        # separately fabricated answer. Both clients are authenticated after
        # the actual Evennia process restart.
        dated = carrier.command("survey history 1")
        require_all(dated, "village day 1", "wanderertester",
                    "houndtester", "unmarked cord",
                    "not proof of what caused a hazard")
        missing = supplier.command("survey history 999")
        require_all(missing, "no signed route archive", "village day 999")
        invalid = supplier.command("survey history tomorrow")
        require(invalid, "survey history <positive village day>")
        # The public daily board must also project the persisted previous
        # day safely, without changing signed archive or current reports.
        board = supplier.command("survey")
        require_all(board, "previous surveyed day 1", "use survey history")
        print("TELNET_POST_RESTART_ROUTE_BOARD_SUMMARY_GREEN")
        print("TELNET_POST_RESTART_EXACT_DAY_ROUTE_HISTORY_GREEN")
        print("TELNET_POST_RESTART_SIGNED_ROUTE_HISTORY_GREEN")
        out = supplier.command("commission")
        require_all(out, "village commission", "open")
        out = supplier.command("hearth gather")
        require(out, "bundles remain today")
        out = supplier.command("commission pledge")
        require_all(out, "pledge your physical", "another player")
        require_all(supplier.command("agenda"), "your firewood pledge is pending", "commission cancel")
        out = carrier.command("west")
        require(out, "village square")
        out = supplier.command("give firewood = MerchantTester")
        require(out, "you give")
        require(carrier.command("agenda"), "you carry the exact pledged bundle")
        out = carrier.command("east")
        require(out, "blood of the vine")
        out = carrier.command("commission cancel")
        require(out, "only the original supplier")
        out = supplier.command("commission cancel")
        require_all(out, "signed firewood pledge is cancelled", "remains")
        require(supplier.command("agenda"), "your pledge was cancelled")
        # T-16: the distinct account still holding the physical bundle
        # must discover the honest recovery route, not a phantom commission.
        out = carrier.command("agenda")
        require_all(out, "supplier cancelled the pledge", "hearth deliver")
        if "commission deliver" in out.lower():
            raise AssertionError("Cancelled commission still offered as live carrier work")
        out = carrier.command("commission deliver")
        require(out, "must first pledge")
        out = carrier.command("hearth deliver")
        require(out, "shared rack now holds")
        out = carrier.command("hearth deliver")
        require(out, "bring a real bundle")
        out = supplier.command("commission cancel")
        require(out, "only an outstanding commission")
        out = supplier.command("commission")
        require_all(out, "cancelled", "hearth deliver")
        print("TELNET_GDD_T16_COMMISSION_RETURN_AGENDA_GREEN")
        print("TELNET_GDD_T13_CANCEL_BEFORE_DELIVER_TWO_ACCOUNT_GREEN")
    finally:
        for client in (carrier, supplier):
            if client is not None:
                client.close()

if __name__ == "__main__":
    main()
