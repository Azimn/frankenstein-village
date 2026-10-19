"""Pure rules for the shared, renewable tavern soup kitchen.

No private per-player instancing: the Tavern owns a finite pantry, actual
preparations are objects, and village days renew a baseline without catch-up.
"""
from __future__ import annotations

import copy

BASE_STOCK = {"turnip": 3, "barley": 2, "thyme": 2, "salt": 4, "pepper": 1}
CAPACITY = {"turnip": 7, "barley": 5, "thyme": 5, "salt": 7, "pepper": 3}
BASES = ("turnip", "barley")
SEASONINGS = ("thyme", "salt", "pepper")
HISTORY_MAX = 24
NOTEBOOK_MAX = 24

# Food quality is deterministic, not a gambling roll. The warmer hearth
# creates a genuine service advantage, but no Innkeep is required to keep
# an NPC-operated baseline kitchen open.
QUALITY = {
    ("turnip", "thyme"): 34,
    ("turnip", "salt"): 25,
    ("turnip", "pepper"): 32,
    ("barley", "thyme"): 33,
    ("barley", "salt"): 24,
    ("barley", "pepper"): 36,
}
FLAVOR = {
    ("turnip", "thyme"): "earthy turnip with a green, herbal finish",
    ("turnip", "salt"): "plain turnip, warm and comforting",
    ("turnip", "pepper"): "sweet roots with a lively pepper bite",
    ("barley", "thyme"): "nutty barley with a woody herb aroma",
    ("barley", "salt"): "a simple bowl of barley and broth",
    ("barley", "pepper"): "toasted grain with a sharp, warming finish",
}


def pantry(raw, day):
    """Return canonical stock, retaining scarce inventory on clock rewind."""
    day = max(1, int(day))
    state = copy.deepcopy(dict(raw or {}))
    old_day = int(state.get("day") or 0)
    if old_day == 0 or day > old_day:
        return {"day": day, "stock": dict(BASE_STOCK),
                "history": list(state.get("history") or [])[-HISTORY_MAX:]}
    stored = dict(state.get("stock") or {})
    stock = {}
    for item in BASE_STOCK:
        stock[item] = max(0, min(CAPACITY[item], int(stored.get(item) or 0)))
    return {"day": old_day, "stock": stock,
            "history": list(state.get("history") or [])[-HISTORY_MAX:]}


def reserve(raw, day, base, seasoning):
    state = pantry(raw, day)
    key = (base, seasoning)
    if key not in QUALITY:
        return state, False, "Choose turnip or barley with thyme, salt or pepper."
    if int(day) < state["day"]:
        return state, False, "The pantry ledger is dated after this hour."
    if state["stock"][base] < 1 or state["stock"][seasoning] < 1:
        return state, False, "The shared pantry lacks those ingredients."
    state["stock"][base] -= 1
    state["stock"][seasoning] -= 1
    return state, True, None


def produce(base, seasoning, *, warmed):
    if (base, seasoning) not in QUALITY:
        return None
    score = min(50, QUALITY[(base, seasoning)] + (5 if warmed else 0))
    return {
        "base": base, "seasoning": seasoning, "quality": score,
        "nourish": score, "warmed": bool(warmed),
        "flavor": FLAVOR[(base, seasoning)],
    }


def archive(raw, day, *, maker_id, maker, source_event_id,
            cook_event_id, recipe):
    state = pantry(raw, day)
    entry = {
        "day": int(day), "maker_id": int(maker_id),
        "maker": str(maker)[:70], "prep_event_id": int(source_event_id),
        "cook_event_id": int(cook_event_id),
        **{name: recipe[name] for name in
           ("base", "seasoning", "quality", "warmed")},
    }
    state["history"].append(entry)
    state["history"] = state["history"][-HISTORY_MAX:]
    return state


def notebook(raw, entry):
    items = [dict(x) for x in list(raw or []) if hasattr(x, "get")]
    if not any(int(x.get("cook_event_id") or -1) == entry["cook_event_id"]
               for x in items):
        items.append(copy.deepcopy(entry))
    return items[-NOTEBOOK_MAX:]


def market_source(raw, day):
    day = max(1, int(day))
    state = dict(raw or {})
    previous_day = int(state.get("day") or 0)
    if not previous_day or day > previous_day:
        return {"day": day, "remaining": 2}
    return {"day": previous_day,
            "remaining": max(0, min(2, int(state.get("remaining") or 0)))}


def issue_crate(raw, day):
    stock = market_source(raw, day)
    if day < stock["day"] or stock["remaining"] < 1:
        return stock, False
    stock["remaining"] -= 1
    return stock, True


def deliver(raw, day, *, units=2):
    state = pantry(raw, day)
    if day < state["day"]:
        return state, False
    if state["stock"]["turnip"] + units > CAPACITY["turnip"]:
        return state, False
    state["stock"]["turnip"] += units
    return state, True
