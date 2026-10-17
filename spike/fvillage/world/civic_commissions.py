"""Pure renewable civic commission state machine.

One finite commission per village day. Distinct accounts must supply and
complete work. World integration must persist the returned state atomically
alongside material inventory changes and the authoritative event ledger.
"""
from __future__ import annotations

import copy

DAILY_LIMIT = 1
MAX_HISTORY = 32
KINDS = ("lamp_oil", "hearth_wood", "church_candles")


def normalize(raw):
    state = copy.deepcopy(raw or {})
    state.setdefault("day", 0)
    state.setdefault("commission", None)
    state.setdefault("history", [])
    state["history"] = state["history"][-MAX_HISTORY:]
    return state


def refresh(raw, day):
    state = normalize(raw)
    day = int(day)
    if day < state["day"]:
        return state
    if day > state["day"]:
        old = state["commission"]
        if old and old["status"] != "complete":
            state["history"].append({**old, "status": "expired"})
        state["day"] = day
        state["commission"] = {
            "id": f"civic-{day}",
            "kind": KINDS[(day - 1) % len(KINDS)],
            "status": "open",
            "supplier_account": None,
            "finisher_account": None,
            "event_ids": [],
        }
        state["history"] = state["history"][-MAX_HISTORY:]
    return state


def supply(raw, day, account_id, *, material_available, event_id):
    state = refresh(raw, day)
    item = state["commission"]
    if not item or item["status"] != "open":
        return state, False, "No open commission."
    if not material_available:
        return state, False, "Required material is unavailable."
    item["supplier_account"] = int(account_id)
    item["status"] = "supplied"
    item["event_ids"].append(int(event_id))
    return state, True, None


def finish(raw, day, account_id, *, at_destination, event_id):
    state = refresh(raw, day)
    item = state["commission"]
    if not item or item["status"] != "supplied":
        return state, False, "The commission awaits supplies."
    if int(account_id) == item["supplier_account"]:
        return state, False, "A second player must complete this work."
    if not at_destination:
        return state, False, "Travel to the commission destination."
    item["finisher_account"] = int(account_id)
    item["status"] = "complete"
    item["event_ids"].append(int(event_id))
    state["history"].append(copy.deepcopy(item))
    state["history"] = state["history"][-MAX_HISTORY:]
    return state, True, None
