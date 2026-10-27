"""Pure, finite rules for the shared Square warming-brazier project.

The public brazier has one physical owner, no second fuel inventory. A player
must spend an existing, traceable Square firewood bundle to light or maintain
it. All time uses the single village clock; no wall-time or offline catch-up.
"""
from __future__ import annotations

import copy

LIGHT_HOURS = 6
FEED_HOURS = 4
MAX_REMAINING_HOURS = 12
MAX_HISTORY = 18


def hour_index(day, hour):
    return (max(1, int(day)) - 1) * 24 + int(hour)


def normalize(raw):
    raw = copy.deepcopy(dict(raw or {}))
    return {
        "warm_until": max(0, int(raw.get("warm_until") or 0)),
        "last_action_at": max(0, int(raw.get("last_action_at") or 0)),
        "history": list(raw.get("history") or [])[-MAX_HISTORY:],
    }


def remaining(raw, day, hour):
    state = normalize(raw)
    now = hour_index(day, hour)
    if now < state["last_action_at"]:
        return 0  # rewinding a clock cannot make a future fire observable
    return max(0, state["warm_until"] - now)


def active(raw, day, hour):
    return remaining(raw, day, hour) > 0


def contribute(raw, day, hour, *, mode, actor, bundle_id, gather_event_id,
               event_id):
    """Spend one physical bundle: light cold embers or feed a burning fire.

    Returns (updated, accepted, reason). On refusal, returns an unchanged
    normalized copy; the caller must retain the actual bundle and its owner.
    """
    state = normalize(raw)
    now = hour_index(day, hour)
    if now < state["last_action_at"]:
        return state, False, "The brazier ledger comes from a later village hour."
    if mode not in {"light", "feed"}:
        return state, False, "Use brazier light or brazier feed."
    if any(row.get("event_id") == event_id for row in state["history"]):
        return state, False, "That signed bundle was already accounted for."
    left = remaining(state, day, hour)
    if mode == "light":
        if left:
            return state, False, "The Square brazier is already burning; use brazier feed."
        until = now + LIGHT_HOURS
    else:
        if not left:
            return state, False, "The Square brazier is cold; light it before feeding."
        if left + FEED_HOURS > MAX_REMAINING_HOURS:
            return state, False, "The brazier is well supplied; keep that bundle for later."
        until = state["warm_until"] + FEED_HOURS
    state["warm_until"] = until
    state["last_action_at"] = now
    state["history"].append({
        "event_id": int(event_id),
        "gather_event_id": int(gather_event_id),
        "bundle_id": int(bundle_id),
        "day": int(day),
        "hour": int(hour),
        "mode": mode,
        "mask_id": int(actor["mask_id"]),
        "mask": str(actor["mask"])[:70],
    })
    state["history"] = state["history"][-MAX_HISTORY:]
    return state, True, None
