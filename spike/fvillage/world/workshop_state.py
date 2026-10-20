"""Finite, physically settled repair work for the public Market Workshop.

Pure rules only. A real Smith uses a unit of stock to forge a transferable
hinge. A carrier later installs the actual item on Market Lane. No remote
crafting, simulated labor, quest XP, or parallel economy is permitted.
"""
from __future__ import annotations

import copy

DAILY_OFFCUTS = 2
MAX_HISTORY = 28


def _positive(value):
    if isinstance(value, bool):
        return None
    try:
        number = int(value)
    except (ValueError, TypeError, OverflowError):
        return None
    return number if number > 0 else None


def _hour(value):
    if isinstance(value, bool):
        return None
    try:
        number = int(value)
    except (ValueError, TypeError, OverflowError):
        return None
    return number if 0 <= number <= 23 else None


def fresh(day=0):
    return {
        "day": int(day), "offcuts": DAILY_OFFCUTS, "crafts": [],
        "installation": None, "history": [],
    }


def normalize(raw):
    if not hasattr(raw, "get"):
        return fresh()
    day = _positive(raw.get("day")) or 0
    state = fresh(day)
    try:
        state["offcuts"] = max(
            0, min(DAILY_OFFCUTS, int(raw.get("offcuts")))
        )
    except (ValueError, TypeError, OverflowError):
        pass
    for row in list(raw.get("crafts") or [])[:DAILY_OFFCUTS * 3]:
        if not hasattr(row, "get"):
            continue
        aid = _positive(row.get("account_id"))
        mid = _positive(row.get("mask_id"))
        eid = _positive(row.get("event_id"))
        item = _positive(row.get("item_id"))
        hour = _hour(row.get("hour"))
        if aid and mid and eid and item and hour is not None:
            if not any(r["event_id"] == eid for r in state["crafts"]):
                state["crafts"].append({
                    "account_id": aid, "mask_id": mid,
                    "event_id": eid, "item_id": item, "hour": hour,
                    "mask": str(row.get("mask") or "")[:70],
                })
    state["crafts"] = state["crafts"][:DAILY_OFFCUTS]
    receipt = raw.get("installation")
    if hasattr(receipt, "get"):
        vals = [_positive(receipt.get(k)) for k in (
            "account_id", "mask_id", "event_id", "item_id",
            "source_event_id",
        )]
        h = _hour(receipt.get("hour"))
        if all(vals) and h is not None:
            state["installation"] = {
                "account_id": vals[0], "mask_id": vals[1],
                "event_id": vals[2], "item_id": vals[3],
                "source_event_id": vals[4], "hour": h,
                "mask": str(receipt.get("mask") or "")[:70],
            }
    history = raw.get("history") or []
    if isinstance(history, (list, tuple)):
        state["history"] = [
            copy.deepcopy(row) for row in history[-MAX_HISTORY * 2:]
            if hasattr(row, "get") and _positive(row.get("day"))
            and _positive(row.get("day")) < day
        ][-MAX_HISTORY:]
    return state


def refresh(raw, day):
    target = _positive(day)
    if not target:
        raise ValueError("A positive village day is required")
    state = normalize(raw)
    if target <= state["day"]:
        return state
    if state["day"] and (state["crafts"] or state["installation"]):
        state["history"].append({
            "day": state["day"],
            "crafts": copy.deepcopy(state["crafts"]),
            "installation": copy.deepcopy(state["installation"]),
        })
    next_day = fresh(target)
    next_day["history"] = state["history"][-MAX_HISTORY:]
    return next_day


def forge(raw, *, day, hour, account_id, mask_id, mask,
          event_id, item_id):
    state = refresh(raw, day)
    if day < state["day"] or _hour(hour) is None:
        return state, False, "The village clock moved behind the repair book."
    account, maskid = _positive(account_id), _positive(mask_id)
    event, item = _positive(event_id), _positive(item_id)
    if not all((account, maskid, event, item)):
        return state, False, "A real worker, object and signed event are required."
    if state["offcuts"] == 0:
        return state, False, "Today's iron offcuts have already been used."
    if any(row["account_id"] == account for row in state["crafts"]):
        return state, False, "You have already forged a market fitting today."
    if any(row["event_id"] == event or row["item_id"] == item
           for row in state["crafts"]):
        return state, False, "This physical repair was already recorded."
    state["offcuts"] -= 1
    state["crafts"].append({
        "account_id": account, "mask_id": maskid,
        "mask": str(mask)[:70], "hour": hour,
        "event_id": event, "item_id": item,
    })
    return state, True, None


def install(raw, *, day, hour, account_id, mask_id, mask,
            event_id, item_id, source_event_id):
    state = refresh(raw, day)
    if day < state["day"] or _hour(hour) is None:
        return state, False, "The market cannot accept a backdated repair."
    vals = [
        _positive(value) for value in (
            account_id, mask_id, event_id, item_id, source_event_id
        )
    ]
    if any(value is None for value in vals):
        return state, False, "A physical fitting and signed carrier are required."
    if state["installation"]:
        return state, False, "Today's market fitting has already been installed."
    used_sources = {
        row["installation"]["source_event_id"]
        for row in state["history"] if row.get("installation")
    }
    if vals[4] in used_sources:
        return state, False, "This fitting was already installed in another day."
    state["installation"] = {
        "account_id": vals[0], "mask_id": vals[1],
        "event_id": vals[2], "item_id": vals[3],
        "source_event_id": vals[4],
        "mask": str(mask)[:70], "hour": hour,
    }
    return state, True, None


def public_lines(raw, day):
    state = refresh(raw, day)
    lines = [
        "|wMarket Workshop repair docket|n",
        f"Village day {state['day']}: {state['offcuts']} of "
        f"{DAILY_OFFCUTS} iron offcuts remain.",
        f"Signed fittings forged today: {len(state['crafts'])}.",
    ]
    receipt = state["installation"]
    if receipt:
        lines.append(
            f"{receipt['mask']} installed a real replacement market hinge "
            f"(world event {receipt['event_id']}, forged source "
            f"{receipt['source_event_id']})."
        )
    else:
        lines.append(
            "The day's market fitting is still uninstalled. "
            "A Smith may use |wworkshop forge|n in the Workshop; "
            "any actual carrier can use |wworkshop install|n on Market Lane."
        )
    if state["history"]:
        old = state["history"][-1]
        lines.append(
            f"Previous recorded day {old['day']}: "
            + (
                f"repaired by {old['installation']['mask']}."
                if old.get("installation") else "left unfinished."
            )
        )
    return "\n".join(lines)
