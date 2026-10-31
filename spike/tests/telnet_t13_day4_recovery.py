#!/usr/bin/env python3
"""Exercise a fresh commission after the previous day's two-socket contest.

Every gameplay action uses an authenticated normal telnet account. The
previous day's terminal order must not block today's legitimate work.
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
    args = parser.parse_args()
    supplier = None
    try:
        supplier = connect(
            args.host, args.port, "qa_smith_repair",
            os.environ["FV_QA_REPAIR_PASSWORD"],
            "SmithTester", "Village Square",
        )
        status = supplier.command("commission")
        match = re.search(r"day\s+(\d+),\s+hour\s+\d+\.\s+commission\s+(civic-\d+):\s+open\.", status, re.I)
        assert match is not None, ("Expected an open signed daily commission", status)
        recovery_day = int(match.group(1))
        commission_id = match.group(2)
        assert recovery_day >= 4 and commission_id == f"civic-{recovery_day}", status
        require(supplier.command("hearth gather"), "bundles remain today")
        require_all(
            supplier.command("commission pledge"),
            "pledge your physical", "another player",
        )
        require_all(supplier.command("commission"), commission_id, "pledged")
        require_all(
            supplier.command("commission cancel"),
            "signed firewood pledge is cancelled", "remains",
        )
        require_all(supplier.command("commission"), commission_id, "cancelled")
        require(supplier.command("commission cancel"), "only an outstanding commission")
        print("TELNET_GDD_T13_NEXT_DAY_RECOVERY_GREEN")
    finally:
        if supplier is not None:
            supplier.close()


if __name__ == "__main__":
    main()
