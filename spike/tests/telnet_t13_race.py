#!/usr/bin/env python3
"""Send real competing commission commands from two authenticated telnet sockets.

The barrier synchronizes CLIENT sends, not server-side database execution.
The read-only Evennia assertions independently verify signed world state.
"""
import argparse
from concurrent.futures import ThreadPoolExecutor
from threading import Barrier

from telnet_playthrough import require, require_all
from telnet_t13_cancel import connect


def compete(client, command, barrier):
    barrier.wait(timeout=8)
    print(f"\n> [simultaneous client send] {command}", flush=True)
    client.sock.sendall((command + "\n").encode("utf-8"))
    return client.read_quiet(max_wait=8, quiet=0.5)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=4000)
    args = parser.parse_args()
    import os
    password = os.environ["FV_QA_REPAIR_PASSWORD"]
    supplier = carrier = None
    try:
        supplier = connect(args.host, args.port, "qa_smith_repair", password,
                           "SmithTester", "Village Square")
        carrier = connect(args.host, args.port, "qa_merchant_repair", password,
                          "MerchantTester", "The Blood of the Vine")
        require_all(supplier.command("commission"), "village commission", "open")
        require(supplier.command("hearth gather"), "bundles remain today")
        require_all(supplier.command("commission pledge"),
                    "pledge your physical", "another player")
        require(carrier.command("west"), "village square")
        require(supplier.command("give firewood = MerchantTester"), "you give")
        require(carrier.command("east"), "blood of the vine")
        # Drain movement broadcasts before the contested commands.
        supplier.read_quiet(max_wait=0.8)
        carrier.read_quiet(max_wait=0.8)

        barrier = Barrier(3)
        with ThreadPoolExecutor(max_workers=2) as pool:
            cancel_future = pool.submit(compete, supplier, "commission cancel", barrier)
            deliver_future = pool.submit(compete, carrier, "commission deliver", barrier)
            barrier.wait(timeout=8)
            cancel_output = cancel_future.result(timeout=15)
            deliver_output = deliver_future.result(timeout=15)

        cancelled = "signed firewood pledge is cancelled" in cancel_output.lower()
        delivered = "commission complete" in deliver_output.lower()
        assert cancelled != delivered, (
            "Exactly one competing terminal command must succeed",
            cancel_output, deliver_output,
        )
        if cancelled:
            require(deliver_output, "must first pledge")
        else:
            require(cancel_output, "only an outstanding commission")
        status = supplier.command("commission")
        require_all(status, "village commission",
                    "cancelled" if cancelled else "complete")
        print("TELNET_GDD_T13_TWO_SOCKET_RACE_SINGLE_WINNER_GREEN")
    finally:
        for client in (carrier, supplier):
            if client is not None:
                client.close()


if __name__ == "__main__":
    main()
