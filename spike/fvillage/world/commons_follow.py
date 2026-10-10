"""Mask-owned, bounded prospective attention to public Commons correspondence.

This is a pure state projection: following is *not* an NPC quest, a promise to
help, an event subscription, or a claim that the notice text is true. Reading
status never consumes or acknowledges updates. Public moderation takes
precedence; hidden/expired notices are not redisclosed via follow records.
"""

from __future__ import annotations

import copy

MAX_FOLLOWS = 8
SCHEMA_VERSION = 1


def fresh():
    return {"schema_version": SCHEMA_VERSION, "items": []}


def normalize(raw):
    """Copy persisted mask data, preserving at most eight well-formed watches."""
    try:
        entries = list(dict(raw or {}).get("items") or [])
    except (TypeError, ValueError):
        entries = []
    result = fresh()
    seen = set()
    for value in entries:
        if not hasattr(value, "get"):
            continue
        try:
            ident = int(value.get("id"))
            replies = max(0, int(value.get("seen_replies") or 0))
        except (TypeError, ValueError, OverflowError):
            continue
        if ident < 1 or ident in seen:
            continue
        seen.add(ident)
        result["items"].append({
            "id": ident,
            "seen_replies": replies,
            "seen_closed": bool(value.get("seen_closed")),
        })
        if len(result["items"]) == MAX_FOLLOWS:
            break
    return result


def _visible_notice(public_state, ident):
    # Reuse the canonical moderated public visibility filter. Never inspect
    # hidden originals or show archived text from the mask's follow record.
    from world.commons_state import notices

    return next(
        (entry for entry in notices(public_state)
         if entry.get("id") == ident), None
    )


def follow(saved, public_state, notice_id):
    state = normalize(saved)
    try:
        ident = int(notice_id)
    except (TypeError, ValueError):
        return state, False, "Choose a numbered Commons notice."
    entry = _visible_notice(public_state, ident)
    if entry is None:
        return state, False, "No public notice has that number."
    if any(item["id"] == ident for item in state["items"]):
        return state, False, None
    if len(state["items"]) >= MAX_FOLLOWS:
        return state, False, "You already follow eight notices. Unfollow one first."
    state["items"].append({
        "id": ident,
        "seen_replies": len(entry.get("replies") or []),
        "seen_closed": entry.get("status") == "closed",
    })
    return state, True, None


def unfollow(saved, notice_id):
    state = normalize(saved)
    try:
        ident = int(notice_id)
    except (TypeError, ValueError):
        return state, False
    previous = len(state["items"])
    state["items"] = [item for item in state["items"] if item["id"] != ident]
    return state, len(state["items"]) != previous


def summaries(saved, public_state):
    """Snapshot current readable changes WITHOUT marking them seen."""
    result = []
    for item in normalize(saved)["items"]:
        entry = _visible_notice(public_state, item["id"])
        if entry is None:
            result.append({
                "id": item["id"], "available": False,
                "status": None, "new_replies": 0, "new_closure": False,
                "total_replies": None,
            })
            continue
        count = len(entry.get("replies") or [])
        result.append({
            "id": item["id"],
            "available": True,
            "status": entry.get("status"),
            "kind": entry.get("kind"),
            "from": (entry.get("author") or {}).get("mask"),
            "new_replies": max(0, count - item["seen_replies"]),
            "new_closure": (
                entry.get("status") == "closed" and not item["seen_closed"]
            ),
            "total_replies": count,
        })
    return result


def acknowledge(saved, public_state, notice_id):
    """Mark a visible watched notice read; never acknowledge hidden ones."""
    state = normalize(saved)
    try:
        ident = int(notice_id)
    except (TypeError, ValueError):
        return state, False, "Choose a numbered Commons notice."
    watch = next((w for w in state["items"] if w["id"] == ident), None)
    if watch is None:
        return state, False, "Follow that notice first."
    entry = _visible_notice(public_state, ident)
    if entry is None:
        return state, False, "That notice is no longer publicly available."
    watch["seen_replies"] = max(
        watch["seen_replies"], len(entry.get("replies") or [])
    )
    watch["seen_closed"] = watch["seen_closed"] or entry.get("status") == "closed"
    return copy.deepcopy(state), True, None
