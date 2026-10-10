#!/usr/bin/env python3
"""Portable, deterministic continuity and moderation tests for followed notes."""

from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "fvillage"))
from world import commons_follow as follow, commons_state as board


def actor(account, mask, name):
    return {"account_id": account, "mask_id": mask, "mask": name}


def post(state, by, text):
    next_state, record, error = board.post(
        state, by, "need", text, day=4, hour=20
    )
    assert error is None
    return next_state, record


def main():
    alice, bob = actor(11, 101, "Alice"), actor(12, 201, "Bob")
    state, item = post(
        board.fresh(), alice, "Someone to carry parcels to the church."
    )
    saved, created, error = follow.follow(None, state, 1)
    assert created and error is None
    assert follow.summaries(saved, state)[0]["new_replies"] == 0

    # Idempotence: following twice must not erase an already-unread reply.
    state, response, error = board.reply(
        state, 1, bob, "I can take the morning cart.", day=5, hour=7
    )
    assert error is None
    saved2, created, error = follow.follow(saved, state, 1)
    assert not created and not error and saved2 == saved
    unread = follow.summaries(saved, state)[0]
    assert unread["new_replies"] == 1
    assert unread["status"] == "open" and unread["from"] == "Alice"
    assert follow.summaries(saved, state)[0]["new_replies"] == 1, (
        "Status observation acknowledged an update without player consent"
    )

    acked, ok, error = follow.acknowledge(saved, state, 1)
    assert ok and not error and follow.summaries(acked, state)[0]["new_replies"] == 0
    assert follow.summaries(saved, state)[0]["new_replies"] == 1, (
        "Reading mutated the saved input instead of returning an independent copy"
    )

    state, _, error = board.close(
        state, 1, alice, "The cart reached the church.", day=5, hour=10
    )
    assert not error
    row = follow.summaries(acked, state)[0]
    assert row["new_closure"] and row["status"] == "closed"
    assert not follow.summaries(acked, state)[0]["new_replies"]
    restored = json.loads(json.dumps(acked))
    assert follow.summaries(restored, state)[0]["new_closure"], (
        "A closing account was lost on serialization/restart"
    )
    acked, ok, error = follow.acknowledge(restored, state, 1)
    assert ok and not error
    row = follow.summaries(acked, state)[0]
    assert not row["new_closure"] and row["status"] == "closed"

    # Staff concealment dominates any saved per-mask subscription. Hidden
    # text, author, status and moderation reason MUST NOT appear in summaries.
    state, _, error = board.hide(
        state, 1, actor(99, 999, "Human Staff"),
        "Moderator removed the correspondence.", day=5, hour=11
    )
    assert not error
    row = follow.summaries(acked, state)[0]
    assert row["available"] is False
    assert row["status"] is None and "from" not in row
    assert "body" not in str(row).lower() and "alice" not in str(row).lower()
    unchanged, ok, error = follow.acknowledge(acked, state, 1)
    assert not ok and error and unchanged == acked
    _, created, error = follow.follow(None, state, 1)
    assert not created and error

    # An author's second mask must never inherit the first mask's watches.
    second_mask = follow.fresh()
    assert not follow.summaries(second_mask, state)
    assert follow.summaries(acked, state)
    _, removed = follow.unfollow(second_mask, 1)
    assert not removed
    emptied, removed = follow.unfollow(acked, 1)
    assert removed and not emptied["items"]

    # Bounded interest ledger; failure never evicts the oldest open concern.
    public = board.fresh()
    for index in range(follow.MAX_FOLLOWS + 1):
        public, _ = post(
            public, actor(index + 100, index + 200, f"Local {index}"),
            f"A neighbor needs help with task {index} tomorrow."
        )
    watches = follow.fresh()
    for index in range(1, follow.MAX_FOLLOWS + 1):
        watches, created, error = follow.follow(watches, public, index)
        assert created and not error
    full, created, error = follow.follow(
        watches, public, follow.MAX_FOLLOWS + 1
    )
    assert not created and error and full == watches
    assert len(follow.summaries(watches, public)) == 8
    assert follow.normalize({"items": [
        {"id": 1, "seen_replies": -100, "seen_closed": False},
        {"id": 1, "seen_replies": 99, "seen_closed": True},
        {"id": "NaN", "seen_replies": 1},
    ]})["items"] == [{"id": 1, "seen_replies": 0, "seen_closed": False}]

    print("COMMONS_FOLLOWUP_SIM_GREEN")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
