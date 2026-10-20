"""Day-scoped, evidence-based village care with bounded signed history.

A new visiting patient occupies the church clinic cot each village day.
The patient is a limited recurring service role, not a scheduled resident.
No medical diagnosis follows from a player's narrative assertion.
"""
from __future__ import annotations
import copy

CONDITIONS = ("cold", "sprain", "fever")
METHODS = ("rest", "compress")
MAX_HISTORY = 36
DAILY_LINEN = 2


def ident(value):
    if isinstance(value, bool):
        return None
    try:
        n = int(value)
    except (ValueError, TypeError, OverflowError):
        return None
    return n if n > 0 else None


def hour_value(value):
    if isinstance(value, bool):
        return None
    try:
        n = int(value)
    except (ValueError, TypeError, OverflowError):
        return None
    return n if 0 <= n <= 23 else None


def _day_state(day):
    return {"day": day, "condition": CONDITIONS[(day - 1) % len(CONDITIONS)],
            "linen": DAILY_LINEN, "assessment": None, "treatment": None,
            "history": []}


def normalize(raw):
    if not hasattr(raw, "get"):
        return _day_state(1)
    day = ident(raw.get("day")) or 1
    state = _day_state(day)
    condition = raw.get("condition")
    if condition == state["condition"]:
        try:
            state["linen"] = max(0, min(DAILY_LINEN, int(raw.get("linen"))))
        except (TypeError, ValueError, OverflowError):
            state["linen"] = DAILY_LINEN
    for key in ("assessment", "treatment"):
        row = raw.get(key)
        if (hasattr(row, "get") and ident(row.get("event_id"))
                and ident(row.get("account_id"))
                and ident(row.get("mask_id"))
                and row.get("day") == day and
                hour_value(row.get("hour")) is not None):
            if key == "assessment" or row.get("method") in METHODS:
                state[key] = copy.deepcopy(dict(row))
    if state["treatment"] and not state["assessment"]:
        state["treatment"] = None
    state["history"] = [
        copy.deepcopy(dict(row)) for row in list(raw.get("history") or [])[-MAX_HISTORY * 2:]
        if hasattr(row, "get") and ident(row.get("day"))
    ][-MAX_HISTORY:]
    return state


def refresh(raw, day):
    day = ident(day)
    if day is None:
        raise ValueError("Village day must be positive.")
    state = normalize(raw)
    if day <= state["day"]:
        return state
    if state["assessment"] or state["treatment"]:
        state["history"].append({
            "day": state["day"], "condition": state["condition"],
            "assessment": copy.deepcopy(state["assessment"]),
            "treatment": copy.deepcopy(state["treatment"]),
        })
    future = _day_state(day)
    future["history"] = state["history"][-MAX_HISTORY:]
    return future


def _actor(day, hour, account_id, mask_id, mask, event_id):
    if not (ident(day) and ident(account_id) and ident(mask_id)
            and ident(event_id) and hour_value(hour) is not None):
        return None
    return {"day": day, "hour": hour, "account_id": int(account_id),
            "mask_id": int(mask_id), "mask": str(mask or "")[:70],
            "event_id": int(event_id)}


def assess(raw, *, day, hour, account_id, mask_id, mask, event_id):
    state = refresh(raw, day)
    if day < state["day"]:
        return state, False, "A newer day is already on the clinic register."
    actor = _actor(day, hour, account_id, mask_id, mask, event_id)
    if not actor:
        return state, False, "A signed, present player is required."
    if state["assessment"]:
        return state, False, "Today's visiting patient was already assessed."
    actor["finding"] = state["condition"]
    state["assessment"] = actor
    return state, True, None


def prepare(raw, *, day):
    state = refresh(raw, day)
    if day < state["day"] or not state["linen"]:
        return state, False, "The shared clinic cabinet has no fresh linen today."
    state["linen"] -= 1
    return state, True, None


def treat(raw, *, day, hour, account_id, mask_id, mask, event_id, method):
    state = refresh(raw, day)
    if day < state["day"]:
        return state, False, "The patient already belongs to a later day."
    actor = _actor(day, hour, account_id, mask_id, mask, event_id)
    if not actor:
        return state, False, "A signed, present player is required."
    if method not in METHODS:
        return state, False, "Choose rest or compress."
    if not state["assessment"]:
        return state, False, "A Healer must examine the actual patient first."
    if state["treatment"]:
        return state, False, "Today's patient has already received treatment."
    best = {"cold": "rest", "sprain": "compress", "fever": "rest"}
    actor["method"] = method
    actor["assessment_event_id"] = state["assessment"]["event_id"]
    actor["improvement"] = 25 if method == best[state["condition"]] else 10
    actor["outcome"] = (
        "The patient is more comfortable after appropriate care."
        if actor["improvement"] == 25
        else "The visitor rests more easily, although the care was less suited to the complaint."
    )
    state["treatment"] = actor
    return state, True, None


def public_lines(raw, day):
    state = refresh(raw, day)
    lines = [
        "|wSt. Lazarus village clinic|n",
        f"Village day {state['day']}: a visiting patient presents with {state['condition']}.",
        f"Fresh linen in the shared cabinet: {state['linen']} of {DAILY_LINEN}.",
    ]
    if state["assessment"]:
        lines.append(
            f"Assessment signed by {state['assessment']['mask']} "
            f"(event {state['assessment']['event_id']})."
        )
    else:
        lines.append("Nobody has completed a professional examination today.")
    if state["treatment"]:
        t = state["treatment"]
        lines.append(
            f"{t['mask']} used {t['method']} (event {t['event_id']}). {t['outcome']}"
        )
    else:
        lines.append("Treatment remains available after assessment.")
    if state["history"]:
        recent = state["history"][-1]
        care = recent.get("treatment") or {}
        lines.append(
            f"Last archived patient: day {recent['day']}, {recent['condition']}; "
            + (f"care recorded by {care['mask']}." if care else "no completed care.")
        )
    lines.append(
        "Healers: clinic assess | clinic prepare | clinic treat rest|compress. "
        "A fresh, physically carried linen compress is needed for compress care."
    )
    return "\n".join(lines)
