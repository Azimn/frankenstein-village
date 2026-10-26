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
