"""Pure persistence rules for the missing bridge plaque civic investigation.

Two mutually exclusive physical responses can follow genuine local evidence.
No branch asserts why the plaque disappeared. A finished response persists,
while signed upkeep visits give the location a small renewable social loop.
"""
from __future__ import annotations

import copy

CHOICES = frozenset({"preserve", "display"})
MAX_CHECKS = 60

PUBLIC_LINES = {
    "preserve": (
        "A fitted canvas cover now protects the empty plaque socket from "
        "weather. Its lower edge can be lifted for close inspection; the "
        "missing inscription and its maker remain unknown."
    ),
    "display": (
        "A public inquiry board stands beside the empty plaque socket. "
        "A charcoal rubbing shows only surviving screw marks, and invites "
        "witnesses to compare accounts. No suspect is named."
    ),
}


def _positive_int(value):
    if isinstance(value, bool):
        return None
    try:
        number = int(value)
    except (TypeError, ValueError, OverflowError):
        return None
    return number if number > 0 else None


def normalize(raw):
    """Return bounded, detached world state, including historical receipts."""
    source = dict(raw or {}) if hasattr(raw, "get") else {}
    choice = source.get("resolution")
    if not hasattr(choice, "get") or choice.get("choice") not in CHOICES:
        resolution = None
    else:
        account = _positive_int(choice.get("account_id"))
        mask_id = _positive_int(choice.get("mask_id"))
        day = _positive_int(choice.get("day"))
        event = _positive_int(choice.get("event_id"))
        hour = choice.get("hour")
        if (
            None in (account, mask_id, day, event)
            or isinstance(hour, bool)
            or not isinstance(hour, int) or not 0 <= hour <= 23
        ):
            resolution = None
        else:
            resolution = {
                "choice": choice["choice"], "account_id": account,
                "mask_id": mask_id, "mask": str(choice.get("mask") or "")[:70],
                "day": day, "hour": hour, "event_id": event,
            }
    checks = []
    for item in list(source.get("checks") or [])[-MAX_CHECKS * 2:]:
        if not hasattr(item, "get"):
            continue
        aid = _positive_int(item.get("account_id"))
        mid = _positive_int(item.get("mask_id"))
        day = _positive_int(item.get("day"))
        event = _positive_int(item.get("event_id"))
        if None in (aid, mid, day, event):
            continue
        checks.append({
            "account_id": aid, "mask_id": mid, "day": day,
            "event_id": event,
        })
    return {"resolution": resolution, "checks": checks[-MAX_CHECKS:]}


def settle(raw, choice, *, account_id, mask_id, mask, day, hour, event_id):
    """A public, one-time decision, not a claim that the culprit was found."""
    state = normalize(raw)
    if state["resolution"]:
        return state, False, "The public bridge response is already settled."
    if choice not in CHOICES:
        return state, False, "Choose bridgework preserve or bridgework display."
    aid, mid = _positive_int(account_id), _positive_int(mask_id)
    d, event = _positive_int(day), _positive_int(event_id)
    if (
        None in (aid, mid, d, event)
        or isinstance(hour, bool) or not isinstance(hour, int)
        or not 0 <= hour <= 23
    ):
        return state, False, "A signed account and real village time are required."
    state["resolution"] = {
        "choice": choice, "account_id": aid, "mask_id": mid,
        "mask": str(mask or "")[:70], "day": d, "hour": hour,
        "event_id": event,
    }
    return state, True, None


def check(raw, *, account_id, mask_id, day, event_id):
    """One signed upkeep inspection per account per village day."""
    state = normalize(raw)
    if not state["resolution"]:
        return state, False, "The bridge has no agreed public response to tend."
    aid, mid = _positive_int(account_id), _positive_int(mask_id)
    d, event = _positive_int(day), _positive_int(event_id)
    if None in (aid, mid, d, event):
        return state, False, "A signed inspection is required."
    if d < state["resolution"]["day"]:
        return state, False, "The village clock cannot move backwards."
    if any(item["day"] > d for item in state["checks"]):
        return state, False, "A later inspection day is already recorded."
    if any(item["day"] == d and item["account_id"] == aid
           for item in state["checks"]):
        return state, False, "This account already inspected the bridge today."
    state["checks"].append({
        "account_id": aid, "mask_id": mid, "day": d, "event_id": event,
    })
    state["checks"] = state["checks"][-MAX_CHECKS:]
    return state, True, None


def public_line(raw):
    """Every visitor reads only the real shared physical aftermath."""
    state = normalize(raw)
    resolution = state["resolution"]
    if not resolution:
        return (
            "The missing plaque has prompted no public preservation or "
            "inquiry response. A firsthand investigator can use bridgework."
        )
    line = PUBLIC_LINES[resolution["choice"]]
    if state["checks"]:
        latest_day = max(item["day"] for item in state["checks"])
        checks = sum(1 for item in state["checks"]
                     if item["day"] == latest_day)
        line += (
            f" On village day {latest_day}, {checks} signed "
            f"upkeep inspection{'s' if checks != 1 else ''} were recorded."
        )
    return line
