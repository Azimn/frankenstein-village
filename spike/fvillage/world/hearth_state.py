"""Pure finite-resource rules for the repeatable village-hearth activity.

No Evennia imports. The world owns state; masks carry real bundle objects.
Clock units are the village's existing day/hour, not host wall-clock time.
"""

from __future__ import annotations

import copy

DAILY_WOOD = 3
MAX_RESERVE = 6
WARM_HOURS = 8
MAX_HISTORY = 12


def absolute_hour(day, hour):
    return (int(day) - 1) * 24 + int(hour)


def source(raw, day):
    """Daily replacement, no catch-up accumulation, no rewind refill."""
    state = dict(raw or {})
    last = int(state.get("day") or 0)
    if not last or int(day) > last:
        return {"day": int(day), "remaining": DAILY_WOOD}
    return {
        "day": last,
        "remaining": max(0, min(DAILY_WOOD, int(state.get("remaining") or 0))),
    }


def take(raw, day):
    state = source(raw, day)
    if state["remaining"] < 1:
        return state, False
    state["remaining"] -= 1
    return state, True


def hearth(raw):
    state = copy.deepcopy(dict(raw or {}))
    return {
        "reserve": max(0, min(MAX_RESERVE, int(state.get("reserve") or 0))),
        "warm_until": max(0, int(state.get("warm_until") or 0)),
        "history": list(state.get("history") or [])[-MAX_HISTORY:],
    }


def deliver(raw):
    state = hearth(raw)
    if state["reserve"] >= MAX_RESERVE:
        return state, False
    state["reserve"] += 1
    return state, True


def active(raw, day, hour):
    return absolute_hour(day, hour) < hearth(raw)["warm_until"]


def stoke(raw, day, hour, *, actor, source_event_id):
    state = hearth(raw)
    now = absolute_hour(day, hour)
    if state["reserve"] < 1 or now < state["warm_until"]:
        return state, False
    state["reserve"] -= 1
    state["warm_until"] = now + WARM_HOURS
    state["history"].append({
        "mask_id": int(actor["mask_id"]),
        "mask": str(actor["mask"])[:70],
        "day": int(day),
        "hour": int(hour),
        "event_id": int(source_event_id),
    })
    state["history"] = state["history"][-MAX_HISTORY:]
    return state, True
