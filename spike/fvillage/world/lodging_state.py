"""Pure, privacy-bounded Innkeep and Detective inquiry on the original Tavern register.

No guest identity, room access, culprit, or supernatural claim is generated.
The finite public authorization is one redacted entry per village day.
"""
from __future__ import annotations

import copy

MAX_RECORDS = 32
MAX_AGE_HOURS = 48
SCOPE = "room_six_entry_redacted"


def positive(value):
    if isinstance(value, bool):
        return None
    try:
        number = int(value)
    except (TypeError, ValueError, OverflowError):
        return None
    return number if number > 0 else None


def valid_time(day, hour):
    d = positive(day)
    if isinstance(hour, bool):
        return None
    try:
        h = int(hour)
    except (TypeError, ValueError, OverflowError):
        return None
    return (d, h) if d and 0 <= h <= 23 else None


def absolute(day, hour):
    return (day - 1) * 24 + hour


def fresh():
    return {"records": [], "last_day": 0, "last_hour": 0}


def normalize(raw):
    state = fresh()
    if not hasattr(raw, "get"):
        return state
    seen_days, seen_events = set(), set()
    for item in list(raw.get("records") or [])[-MAX_RECORDS * 2:]:
        if not hasattr(item, "get"):
            continue
        t = valid_time(item.get("day"), item.get("hour"))
        ids = [positive(item.get(k)) for k in
               ("account_id", "mask_id", "event_id", "register_id", "room_id")]
        if not t or not all(ids) or t[0] in seen_days or ids[2] in seen_events:
            continue
        row = {
            "day": t[0], "hour": t[1],
            "account_id": ids[0], "mask_id": ids[1], "event_id": ids[2],
            "register_id": ids[3], "room_id": ids[4],
            "mask": str(item.get("mask") or "")[:70],
            "scope": SCOPE, "inquiry": None,
        }
        inquiry = item.get("inquiry")
        if hasattr(inquiry, "get"):
            it = valid_time(inquiry.get("day"), inquiry.get("hour"))
            ii = [positive(inquiry.get(k)) for k in
                  ("account_id", "mask_id", "event_id", "source_event_id")]
            if (it and all(ii) and ii[0] != ids[0] and ii[2] != ids[2]
                    and ii[3] == ids[2]
                    and 0 <= absolute(*it) - absolute(*t) <= MAX_AGE_HOURS):
                row["inquiry"] = {
                    "day": it[0], "hour": it[1], "account_id": ii[0],
                    "mask_id": ii[1], "event_id": ii[2],
                    "source_event_id": ii[3],
                    "mask": str(inquiry.get("mask") or "")[:70],
                    "finding": "qualified_register_observation",
                }
        state["records"].append(row)
        seen_days.add(t[0])
        seen_events.add(ids[2])
    state["records"] = state["records"][-MAX_RECORDS:]
    times = []
    for row in state["records"]:
        times.append((row["day"], row["hour"]))
        if row["inquiry"]:
            times.append((row["inquiry"]["day"], row["inquiry"]["hour"]))
    if times:
        state["last_day"], state["last_hour"] = max(times)
    return state


def _guard(state, day, hour, account_id, mask_id, event_id, register_id, room_id):
    now = valid_time(day, hour)
    ids = [positive(x) for x in
           (account_id, mask_id, event_id, register_id, room_id)]
    if not now or not all(ids):
        return "A real account, original register and valid village time are required."
    if now < (state["last_day"], state["last_hour"]):
        return "The village clock cannot be rewound behind signed register work."
    if any(row["event_id"] == ids[2] or
           (row["inquiry"] and row["inquiry"]["event_id"] == ids[2])
           for row in state["records"]):
        return "That signed event was already used."
    return None


def disclose(raw, *, day, hour, account_id, mask_id, mask, event_id,
             register_id, room_id):
    state = normalize(raw)
    error = _guard(state, day, hour, account_id, mask_id, event_id,
                   register_id, room_id)
    if error:
        return state, False, error
    if any(row["day"] == day for row in state["records"]):
        return state, False, "The Innkeep already authorized one redacted entry today."
    state["records"].append({
        "day": day, "hour": hour, "account_id": account_id,
        "mask_id": mask_id, "mask": str(mask)[:70],
        "event_id": event_id, "register_id": register_id,
        "room_id": room_id, "scope": SCOPE, "inquiry": None,
    })
    state["records"] = state["records"][-MAX_RECORDS:]
    state["last_day"], state["last_hour"] = day, hour
    return state, True, None


def inquire(raw, *, day, hour, account_id, mask_id, mask, event_id,
            register_id, room_id, source_event_id):
    state = normalize(raw)
    error = _guard(state, day, hour, account_id, mask_id, event_id,
                   register_id, room_id)
    if error:
        return state, False, error
    source_id = positive(source_event_id)
    row = next((r for r in state["records"]
                if r["event_id"] == source_id), None)
    if row is None:
        return state, False, "No signed Innkeep disclosure matches that source."
    if (row["register_id"], row["room_id"]) != (register_id, room_id):
        return state, False, "The disclosure concerns another physical register."
    if row["account_id"] == account_id:
        return state, False, "The same account cannot sign both professional roles."
    if row["inquiry"]:
        return state, False, "That redacted entry already has a signed inquiry."
    age = absolute(day, hour) - absolute(row["day"], row["hour"])
    if age < 0:
        return state, False, "The inquiry cannot precede its actual disclosure."
    if age > MAX_AGE_HOURS:
        return state, False, "The disclosure is stale; seek a new daily authorization."
    row["inquiry"] = {
        "day": day, "hour": hour, "account_id": account_id,
        "mask_id": mask_id, "mask": str(mask)[:70],
        "event_id": event_id, "source_event_id": source_id,
        "finding": "qualified_register_observation",
    }
    state["last_day"], state["last_hour"] = day, hour
    return state, True, None


def source_is_valid(event, row):
    """Require the original completed ledger receipt, not a copied claim."""
    if not hasattr(event, "get") or not hasattr(row, "get"):
        return False
    actor, payload, consequence = (
        event.get("actor"), event.get("payload"), event.get("consequence")
    )
    if not all(hasattr(x, "get") for x in (actor, payload, consequence)):
        return False
    return (
        event.get("kind") == "village.lodging_disclosure"
        and event.get("status") == "complete"
        and positive(event.get("id")) == row.get("event_id")
        and positive(actor.get("account_id")) == row.get("account_id")
        and positive(actor.get("mask_id")) == row.get("mask_id")
        and actor.get("mask") == row.get("mask")
        and payload.get("calling") == "innkeep"
        and payload.get("scope") == SCOPE
        and payload.get("day") == row.get("day")
        and payload.get("hour") == row.get("hour")
        and payload.get("register_id") == row.get("register_id")
        and payload.get("room_id") == row.get("room_id")
        and consequence.get("scope") == SCOPE
        and consequence.get("register_id") == row.get("register_id")
        and consequence.get("room_id") == row.get("room_id")
        and consequence.get("source_event_id") == row.get("event_id")
    )


def public_lines(raw):
    state = normalize(raw)
    lines = [
        "The Tavern guest register: professional inquiry",
        "The Room Six entry exists in the original register. No guest identity is established.",
        "An Innkeep who has examined it may use lodging disclose once per village day.",
        "A different Detective must look at the same register, then use lodging inquire within 48 hours.",
        "No disclosure grants room access or proves who wrote the entry.",
    ]
    if state["records"]:
        row = state["records"][-1]
        lines.append("Latest redacted authorization: village day %s, event %s." %
                     (row["day"], row["event_id"]))
        if row["inquiry"]:
            lines.append("Independent qualified inquiry: signed event %s, source %s." %
                         (row["inquiry"]["event_id"], row["event_id"]))
        else:
            lines.append("No independent Detective inquiry is recorded for that entry.")
    else:
        lines.append("No signed redacted authorization has been made.")
    return "\n".join(lines)
