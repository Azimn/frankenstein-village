#!/usr/bin/env python3
"""Portable multiplayer commons test without Evennia or user databases."""

from __future__ import annotations

import copy
import importlib.util
import json
from pathlib import Path


PATH = Path(__file__).resolve().parents[1] / "fvillage" / "world" / "commons_state.py"
spec = importlib.util.spec_from_file_location("commons_state", PATH)
commons = importlib.util.module_from_spec(spec)
spec.loader.exec_module(commons)


def who(account_id, mask_id, name):
    return {"account_id": account_id, "mask_id": mask_id, "mask": name}


def test_shared_correspondence():
    alice = who(11, 101, "Alice")
    alice_alt = who(11, 102, "Another Alice")
    bram = who(12, 201, "Bram")
    clara = who(13, 301, "Clara")

    state = commons.fresh()
    state, note, err = commons.post(
        state, alice, "need", "The cold square needs extra blankets.",
        day=4, hour=21
    )
    assert not err and note["id"] == 1
    assert note["author"]["account_id"] == 11
    assert len(commons.notices(state, include_closed=False)) == 1

    state, response, err = commons.reply(
        state, note["id"], bram, "I can bring wool tomorrow.", day=5, hour=8
    )
    assert not err and response["by"]["account_id"] == 12
    state, response, err = commons.reply(
        state, note["id"], clara, "I can ask the church.", day=5, hour=9
    )
    assert not err and response["by"]["account_id"] == 13
    assert len(commons.get_notice(state, 1)["replies"]) == 2

    snapshot = json.loads(json.dumps(state))
    state, _, err = commons.close(
        state, 1, alice_alt, "They have agreed to meet again.",
        day=5, hour=12
    )
    assert not err, "another mask of the same account should retain authorship"
    assert commons.get_notice(snapshot, 1)["status"] == "open"
    assert commons.get_notice(state, 1)["status"] == "closed"
    assert len(commons.notices(state, include_closed=False)) == 0
    state, _, err = commons.reply(
        state, 1, bram, "I will do another thing.", day=5, hour=13
    )
    assert err and len(commons.get_notice(state, 1)["replies"]) == 2

    state, second, err = commons.post(
        state, bram, "offer", "I can help with deliveries on market day.",
        day=6, hour=7
    )
    assert not err and second["id"] == 2
    state, denied, err = commons.close(
        state, 2, clara, "I will close your offer.", day=6, hour=8
    )
    assert err and denied is None
    assert commons.get_notice(state, 2)["status"] == "open"
    return state


def test_limits_and_moderation():
    state = commons.fresh()
    alice = who(1, 10, "Alice")
    others = who(2, 20, "Bram")
    human_staff = who(3, 30, "Human Staff")
    for index in range(commons.MAX_OPEN_PER_ACCOUNT):
        state, note, error = commons.post(
            state, alice, "notice", f"Notice {index}: offering help at market.",
            day=1, hour=index
        )
        assert not error
    state, note, error = commons.post(
        state, who(1, 11, "Alice's other mask"), "need",
        "This fourth notice must not be accepted.", day=1, hour=5
    )
    assert note is None and error
    assert len(commons.notices(state, include_closed=False)) == 3

    for i in range(commons.MAX_REPLIES_PER_ACCOUNT):
        state, response, error = commons.reply(
            state, 1, others, f"Response {i}.", day=2, hour=i
        )
        assert not error
    state, response, error = commons.reply(
        state, 1, who(2, 21, "Other Bram"),
        "Another answer.", day=2, hour=4
    )
    assert response is None and error, "an alternate mask bypassed reply cap"

    state, hidden, err = commons.hide(
        state, 1, human_staff, "Offensive notice under review.",
        day=2, hour=5
    )
    assert not err and hidden["hidden"]
    assert commons.get_notice(state, 1)["body"].startswith("Notice")
    assert not any(item["id"] == 1 for item in commons.notices(state))
    state, _, err = commons.reply(
        state, 1, others, "Cannot reply to hidden posts.", day=2, hour=6
    )
    assert err

    # Plain-text sanitization is stable across serialization boundaries.
    state, note, err = commons.post(
        state, others, "need", "Help|r with\n two parcels, please.\x1b[1m",
        day=3, hour=5
    )
    assert not err
    assert "|" not in note["body"] and "\n" not in note["body"]
    assert "\x1b" not in note["body"]
    return state


def test_archival_pressure():
    state = commons.fresh()
    # Occupy every open slot from distinct accounts, then verify a new post
    # cannot silently push someone else's unfinished work out of the ledger.
    for index in range(commons.MAX_OPEN):
        actor = who(index + 1, index + 100, f"Resident {index}")
        state, item, error = commons.post(
            state, actor, "gathering", "Meet for a conversation after market.",
            day=1, hour=1
        )
        assert not error
    state, item, error = commons.post(
        state, who(900, 901, "Visitor"), "notice",
        "This post must not push an open one out.",
        day=2, hour=1
    )
    assert error and item is None
    assert len(commons.notices(state, include_closed=False)) == commons.MAX_OPEN
    assert {x["id"] for x in commons.notices(state, include_closed=False)} == (
        set(range(1, commons.MAX_OPEN + 1))
    )
    return state


def main():
    recovered = test_shared_correspondence()
    assert commons.get_notice(
        json.loads(json.dumps(recovered)), 2
    )["status"] == "open"
    test_limits_and_moderation()
    test_archival_pressure()
    print("COMMONS_MULTIPLAYER_SIM_GREEN")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
