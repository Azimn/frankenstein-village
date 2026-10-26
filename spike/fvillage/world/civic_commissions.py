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
    # Never truncate fractional days or treat bool as an integer clock tick.
    # A coerced day could attach a signed event to the wrong daily order.
    if isinstance(day, bool) or not isinstance(day, int) or day < 1:
        raise ValueError("Village day must be a positive integer")
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
    if event_id in item["event_ids"]:
        return state, False, "The delivery needs a distinct signed event."
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
    if event_id in item["event_ids"]:
        return state, False, "The cancellation needs a distinct signed event."
    item["status"] = "cancelled"
    item["event_ids"].append(event_id)
    state["history"].append(copy.deepcopy(item))
    state["history"] = state["history"][-MAX_HISTORY:]
    return state, True, None



def personal_agenda(raw, day, account_id, carried_bundle_ids=()):
    """Read-only, actor-scoped continuity for the existing firewood order.

    Never infer custody from a pledge. The caller supplies IDs of actual
    objects currently carried by this mask. No new store or game action.
    """
    if type(account_id) is not int or account_id < 1:
        return []
    state = refresh(raw, day)
    item = state.get("commission") or {}
    status = item.get("status")
    order = item.get("id")
    held = {value for value in carried_bundle_ids
            if type(value) is int and value > 0}
    supplier = item.get("supplier_account") == account_id
    finisher = item.get("finisher_account") == account_id

    if status == "pledged":
        if supplier:
            return [
                f"Commission {order}: your firewood pledge is pending. "
                "A different account must deliver the actual bundle to the "
                "Blood of the Vine. Coordinate the handoff or use "
                "|wcommission cancel|n while the pledge remains open."
            ]
        if item.get("bundle_id") in held:
            return [
                f"Commission {order}: you carry the exact pledged bundle. "
                "Take it to the Blood of the Vine and use "
                "|wcommission deliver|n, unless the supplier cancels first."
            ]
    if status == "complete" and (supplier or finisher):
        if supplier:
            return [
                f"Commission {order}: completed by another account. "
                "Your pledge is fulfilled; the real wood reached the Tavern."
            ]
        return [
            f"Commission {order}: your delivery is complete. "
            "The pledged bundle is now in the shared Tavern rack."
        ]
    if status == "cancelled":
        if supplier:
            return [
                f"Commission {order}: your pledge was cancelled. "
                "The physical bundle was not confiscated; use "
                "|whearth deliver|n if you still carry it."
            ]
        if item.get("bundle_id") in held:
            return [
                f"Commission {order}: the supplier cancelled the pledge "
                "while you carried its physical bundle. "
                "The commission is closed; use |whearth deliver|n "
                "at the Blood of the Vine instead."
            ]

    # A new day's public order must not make yesterday's personal pledge
    # appear pending. Only the immediately previous day's expiry is relevant.
    previous = f"civic-{int(day) - 1}"
    for old in reversed(state.get("history") or []):
        if old.get("id") != previous or old.get("status") != "expired":
            continue
        if old.get("supplier_account") == account_id:
            return [
                f"Commission {previous}: yesterday's pledge expired. "
                "No wood was confiscated by expiry. Today's commission "
                "is a separate order; use |wcommission|n for its status."
            ]
        if old.get("bundle_id") in held:
            return [
                f"Commission {previous}: yesterday's pledge expired "
                "while you carried its physical bundle. "
                "Today's commission is a separate order; use "
                "|whearth deliver|n at the Blood of the Vine instead."
            ]
    return []
