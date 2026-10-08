"""Bounded public civic correspondence, without Evennia or autonomous questing.

A notice records what a player has said, not an objective claim or a quest.
No notice grants currency, character rank, or automatic completion. Distinct
accounts may answer across sessions. Active notices are never silently evicted.
"""

from __future__ import annotations

import copy
import re


KINDS = frozenset({"need", "offer", "gathering", "notice"})
MAX_OPEN = 48
MAX_OPEN_PER_ACCOUNT = 3
MAX_HISTORY = 160
MAX_REPLIES = 16
MAX_REPLIES_PER_ACCOUNT = 3


def fresh():
    return {"schema_version": 1, "next_id": 1, "entries": []}


def normalize(state):
    result = copy.deepcopy(dict(state or fresh()))
    result.setdefault("next_id", 1)
    result.setdefault("entries", [])
    result["schema_version"] = 1
    return result


def clean(value, maximum):
    # Do not permit Evennia pipes, terminal escapes, or multi-line spoofing
    # in player-generated public text.
    raw = str(value or "").replace("|", " ")
    raw = "".join(ch if ch.isprintable() else " " for ch in raw)
    raw = re.sub(r"\s+", " ", raw).strip()
    if not raw or len(raw) > maximum:
        return None
    return raw


def _who(actor):
    return {
        "account_id": int(actor["account_id"]),
        "mask_id": int(actor["mask_id"]),
        "mask": clean(actor["mask"], 70) or "a traveler",
    }


def _find(state, notice_id):
    for entry in state["entries"]:
        if entry["id"] == int(notice_id):
            return entry
    return None


def get_notice(state, notice_id):
    state = normalize(state)
    entry = _find(state, notice_id)
    return copy.deepcopy(entry) if entry else None


def notices(state, *, include_closed=True):
    state = normalize(state)
    return [
        item for item in reversed(state["entries"])
        if not item.get("hidden") and (include_closed or item["status"] == "open")
    ]


def post(state, actor, kind, message, *, day, hour):
    state = normalize(state)
    kind = str(kind or "").lower().strip()
    body = clean(message, 180)
    if kind not in KINDS:
        return state, None, "Choose need, offer, gathering, or notice."
    if not body or len(body) < 12:
        return state, None, "Use 12 to 180 plain-text characters."
    ident = int(actor["account_id"])
    open_items = [x for x in state["entries"] if x["status"] == "open"]
    if len(open_items) >= MAX_OPEN:
        return state, None, "The commons is full of unsettled notices."
    if sum(x["author"]["account_id"] == ident for x in open_items) >= MAX_OPEN_PER_ACCOUNT:
        return state, None, "You already have three open notices. Close one first."

    if len(state["entries"]) >= MAX_HISTORY:
        # Recycle only an already closed or staff-hidden record. Never erase
        # another person's unfinished request to make room for new content.
        index = next(
            (i for i, x in enumerate(state["entries"])
             if x["status"] != "open" or x.get("hidden")), None
        )
        if index is None:
            return state, None, "The commons archive needs human attention."
        del state["entries"][index]

    entry = {
        "id": int(state["next_id"]),
        "kind": kind,
        "body": body,
        "author": _who(actor),
        "day": int(day),
        "hour": int(hour),
        "status": "open",
        "replies": [],
        "resolution": None,
        "hidden": False,
        "moderation": None,
    }
    state["next_id"] += 1
    state["entries"].append(entry)
    return state, copy.deepcopy(entry), None


def reply(state, notice_id, actor, message, *, day, hour):
    state = normalize(state)
    entry = _find(state, notice_id)
    if not entry or entry.get("hidden"):
        return state, None, "There is no public notice with that number."
    if entry["status"] != "open":
        return state, None, "That notice is closed. Its history remains readable."
    body = clean(message, 180)
    if not body or len(body) < 3:
        return state, None, "Use 3 to 180 plain-text characters."
    if len(entry["replies"]) >= MAX_REPLIES:
        return state, None, "This notice's correspondence is full."
    ident = int(actor["account_id"])
    if sum(x["by"]["account_id"] == ident for x in entry["replies"]) >= MAX_REPLIES_PER_ACCOUNT:
        return state, None, "You have already replied three times to this notice."
    response = {
        "id": len(entry["replies"]) + 1,
        "by": _who(actor),
        "body": body,
        "day": int(day),
        "hour": int(hour),
    }
    entry["replies"].append(response)
    return state, copy.deepcopy(response), None


def close(state, notice_id, actor, message, *, day, hour):
    state = normalize(state)
    entry = _find(state, notice_id)
    if not entry or entry.get("hidden"):
        return state, None, "There is no public notice with that number."
    if entry["status"] != "open":
        return state, None, "That notice is already closed."
    if entry["author"]["account_id"] != int(actor["account_id"]):
        return state, None, "Only the author can close this notice."
    body = clean(message, 180)
    if not body or len(body) < 3:
        return state, None, "Leave a closing account of 3 to 180 characters."
    entry["status"] = "closed"
    entry["resolution"] = {
        "by": _who(actor),
        "body": body,
        "day": int(day),
        "hour": int(hour),
    }
    return state, copy.deepcopy(entry), None


def hide(state, notice_id, moderator, reason, *, day, hour):
    state = normalize(state)
    entry = _find(state, notice_id)
    if not entry:
        return state, None, "There is no notice with that number."
    if entry["hidden"]:
        return state, None, "That notice is already hidden."
    body = clean(reason, 180)
    if not body:
        return state, None, "Supply a moderation reason."
    entry["hidden"] = True
    entry["moderation"] = {
        "by_account_id": int(moderator["account_id"]),
        "reason": body,
        "day": int(day),
        "hour": int(hour),
    }
    return state, copy.deepcopy(entry), None
