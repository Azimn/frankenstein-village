"""Finite, renewable, cooperative tavern supply commission rules.

Pure Python. Actual firewood is owned by Evennia; this state machine binds
one specific bundle ID to the supplier. A separate account must carry that
same object to the tavern and deliver it. Unfinished pledges expire at the
next village day without consuming the player's item.
"""
from __future__ import annotations

import copy

MAX_HISTORY = 32
KIND = "tavern_firewood"


def normalize(raw):
    state = copy.deepcopy(dict(raw or {}))
    state.setdefault("day", 0)
    state.setdefault("commission", None)
    state.setdefault("history", [])
    state["history"] = list(state["history"])[-MAX_HISTORY:]
    return state


def refresh(raw, day):
    state = normalize(raw)
    day = int(day)
    if day < 1:
        raise ValueError("Village day must be positive")
    if day <= int(state["day"]):
        return state
    old = state["commission"]
    if old and old["status"] not in {"complete", "cancelled"}:
        state["history"].append({**copy.deepcopy(old), "status": "expired"})
    state["day"] = day
    state["commission"] = {
        "id": f"civic-{day}",
        "kind": KIND,
        "status": "open",
        "supplier_account": None,
        "supplier_mask": None,
        "bundle_id": None,
        "finisher_account": None,
        "finisher_mask": None,
        "event_ids": [],
    }
    state["history"] = state["history"][-MAX_HISTORY:]
    return state


def pledge(raw, day, account_id, mask, *, bundle_id, event_id):
    state = refresh(raw, day)
    item = state["commission"]
    if int(day) < state["day"]:
        return state, False, "The village clock cannot reopen an earlier commission."
    if not item or item["status"] != "open":
        return state, False, "Today's commission is no longer open."
    if not isinstance(account_id, int) or isinstance(account_id, bool) or account_id < 1:
        return state, False, "A signed supplier account is required."
    if not isinstance(bundle_id, int) or isinstance(bundle_id, bool) or bundle_id < 1:
        return state, False, "A real firewood bundle is required."
    if not isinstance(event_id, int) or isinstance(event_id, bool) or event_id < 1:
        return state, False, "A signed pledge event is required."
    item["supplier_account"] = account_id
    item["supplier_mask"] = str(mask)[:70]
    item["bundle_id"] = bundle_id
    item["status"] = "pledged"
    item["event_ids"].append(int(event_id))
    return state, True, None


def finish(raw, day, account_id, mask, *, carried_bundle_id, reserve_has_space, event_id):
    state = refresh(raw, day)
    item = state["commission"]
    if int(day) < state["day"]:
        return state, False, "The village clock cannot complete an earlier commission."
    if not item or item["status"] != "pledged":
        return state, False, "A neighbor must first pledge a bundle in the Square."
    if not isinstance(account_id, int) or isinstance(account_id, bool) or account_id < 1:
        return state, False, "A signed delivery account is required."
    if account_id == item["supplier_account"]:
        return state, False, "Another account must deliver the pledged bundle."
    if (not isinstance(carried_bundle_id, int)
            or isinstance(carried_bundle_id, bool)
            or carried_bundle_id < 1
            or carried_bundle_id != item["bundle_id"]):
        return state, False, "Carry the actual pledged bundle to the Tavern."
    if not reserve_has_space:
        return state, False, "The Tavern rack is full. Try again when space opens."
    if not isinstance(event_id, int) or isinstance(event_id, bool) or event_id < 1:
        return state, False, "A signed delivery event is required."
    item["finisher_account"] = account_id
    item["finisher_mask"] = str(mask)[:70]
    item["status"] = "complete"
    item["event_ids"].append(int(event_id))
    state["history"].append(copy.deepcopy(item))
    state["history"] = state["history"][-MAX_HISTORY:]
    return state, True, None


def cancel(raw, day, account_id, *, event_id):
    """Cancel a live pledge, never the physical bundle held by a player.

    This competes with finish for the SAME terminal commission state.
    Rechecking inside the world's atomic event consequence prevents a stale
    caller from reopening a finished order or producing a second terminal
    outcome. The bundle is neither confiscated nor added to the hearth.
    """
    state = refresh(raw, day)
    item = state["commission"]
    if int(day) < state["day"]:
        return state, False, "The village clock cannot cancel an earlier commission."
    if not item or item["status"] != "pledged":
        return state, False, "Only an outstanding pledge can be cancelled."
    if (not isinstance(account_id, int) or isinstance(account_id, bool)
            or account_id < 1 or account_id != item["supplier_account"]):
        return state, False, "Only the original supplier may cancel this pledge."
    if not isinstance(event_id, int) or isinstance(event_id, bool) or event_id < 1:
        return state, False, "A signed cancellation event is required."
    item["status"] = "cancelled"
    item["event_ids"].append(event_id)
    state["history"].append(copy.deepcopy(item))
    state["history"] = state["history"][-MAX_HISTORY:]
    return state, True, None
