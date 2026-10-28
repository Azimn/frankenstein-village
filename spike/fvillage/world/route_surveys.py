"""One truthful, renewable daily civic survey across four real districts.

Each accepted report must come from a mask physically at a supported landmark.
The pure state machine never invents an observation, moves a character, or
rewards XP. Four unique, signed reports change the public daily report from
incomplete to complete. Incomplete days become explicit historical outcomes.
"""
from __future__ import annotations

import copy
from collections.abc import Mapping

SITES = ("grave_marker", "red_cord", "market_scale", "river_gauge")
MAX_HISTORY = 30


def fresh(day=0):
    return {"day": int(day), "reports": {}, "field_decisions": {},
            "caution_notice": None, "history": []}



def _positive(value):
    if isinstance(value, bool):
        return None
    try:
        value = int(value)
    except (TypeError, ValueError, OverflowError):
        return None
    return value if value > 0 else None


def _notice(raw, decisions, day):
    """Reject malformed persisted editorial claims, including stale source links."""
    if not isinstance(raw, Mapping) or "hound" not in decisions:
        return None
    keys = ("account_id", "mask_id", "event_id", "source_event_id",
            "source_account_id", "source_mask_id", "source_cord_id")
    ids = {key: _positive(raw.get(key)) for key in keys}
    if not all(ids.values()):
        return None
    try:
        hour = int(raw.get("hour"))
        source_hour = int(raw.get("source_hour"))
    except (TypeError, ValueError, OverflowError):
        return None
    if (isinstance(raw.get("hour"), bool)
            or isinstance(raw.get("source_hour"), bool)
            or not (0 <= source_hour <= hour <= 23)
            or ids["account_id"] == ids["source_account_id"]
            or ids["source_event_id"] != decisions["hound"]["event_id"]
            or ids["source_account_id"] != decisions["hound"]["account_id"]
            or _positive(raw.get("day")) != day):
        return None
    return {**ids, "day": day, "hour": hour, "source_hour": source_hour,
            "mask": str(raw.get("mask") or "")[:70]}


def normalize(raw):
    value = copy.deepcopy(dict(raw or {}))
    try:
        day = max(0, int(value.get("day") or 0))
    except (TypeError, ValueError, OverflowError):
        day = 0
    reports = {}
    for ident, entry in dict(value.get("reports") or {}).items():
        if ident not in SITES or not hasattr(entry, "get"):
            continue
        try:
            account = int(entry["account_id"])
            event = int(entry["event_id"])
        except (ValueError, TypeError, KeyError, OverflowError):
            continue
        if account < 1 or event < 1:
            continue
        reports[ident] = {
            "account_id": account, "mask": str(entry.get("mask") or "")[:70],
            "event_id": event,
        }
    decisions = {}
    for role, entry in dict(value.get("field_decisions") or {}).items():
        if role not in {"hound", "wanderer"} or not hasattr(entry, "get"):
            continue
        try:
            account, event = int(entry["account_id"]), int(entry["event_id"])
        except (ValueError, TypeError, KeyError, OverflowError):
            continue
        if (isinstance(entry.get("account_id"), bool)
                or isinstance(entry.get("event_id"), bool)
                or account < 1 or event < 1):
            continue
        action = "protect" if role == "hound" else "passability"
        observation = entry.get("observation")
        if entry.get("action") != action:
            continue
        if role == "wanderer" and observation not in {"unmarked", "marked_caution"}:
            continue
        decisions[role] = {"account_id": account, "mask": str(entry.get("mask") or "")[:70],
                           "event_id": event, "action": action, "site": "red_cord"}
        if role == "wanderer":
            decisions[role]["observation"] = observation
    return {
        "day": day,
        "reports": reports,
        "field_decisions": decisions,
        "caution_notice": _notice(value.get("caution_notice"), decisions, day),
        "history": list(value.get("history") or [])[-MAX_HISTORY:],
    }


def refresh(raw, day):
    state = normalize(raw)
    day = int(day)
    if day < 1:
        raise ValueError("Village day must be positive")
    if day <= state["day"]:
        return state
    if state["day"] > 0:
        previous = {
            "day": state["day"],
            "completed": len(state["reports"]) == len(SITES),
            "reports": copy.deepcopy(state["reports"]),
            "field_decisions": copy.deepcopy(state["field_decisions"]),
            "caution_notice": copy.deepcopy(state["caution_notice"]),
        }
        state["history"].append(previous)
        state["history"] = state["history"][-MAX_HISTORY:]
    state["day"] = day
    state["reports"] = {}
    state["field_decisions"] = {}
    state["caution_notice"] = None
    return state


def report(raw, day, ident, account_id, mask, event_id):
    state = refresh(raw, day)
    if day < state["day"]:
        return state, False, "A later village day is already recorded."
    if ident not in SITES:
        return state, False, "That location is not on today's inspection route."
    if ident in state["reports"]:
        return state, False, "Today's report for this landmark is already signed."
    try:
        account_id, event_id = int(account_id), int(event_id)
    except (ValueError, TypeError, OverflowError):
        return state, False, "A signed account and canonical event are required."
    if account_id < 1 or event_id < 1:
        return state, False, "A signed account and canonical event are required."
    state["reports"][ident] = {
        "account_id": account_id, "mask": str(mask)[:70], "event_id": event_id,
    }
    return state, True, None


def complete(state):
    return len(normalize(state)["reports"]) == len(SITES)

def field_decision(raw, day, site, role, action, caution_marked,
                   account_id, mask, event_id):
    """One signed profession-specific action at the same physical treeline.

    The cord is the physical safety authority. A Hound may tie its existing
    loose end into a visible caution marker, without magically repairing the
    cord, removing a hazard or inventing materials. A Wanderer signs a dated
    passability interpretation from the condition actually observed. Neither
    rewrites an earlier report or creates a separate version of the route.
    """
    state = refresh(raw, day)
    if day < state["day"]:
        return state, False, "A later village day is already recorded."
    if site != "red_cord" or (role, action) not in {
        ("hound", "protect"), ("wanderer", "passability")
    }:
        return state, False, "That professional field action is not available here."
    if not isinstance(caution_marked, bool):
        return state, False, "The physical cord condition could not be verified."
    for val in (account_id, event_id):
        if isinstance(val, bool):
            return state, False, "A signed ordinary account and event are required."
        try:
            if int(val) < 1:
                return state, False, "A signed ordinary account and event are required."
        except (TypeError, ValueError, OverflowError):
            return state, False, "A signed ordinary account and event are required."
    if role in state["field_decisions"]:
        return state, False, "That professional field action is already signed today."
    if role == "hound" and caution_marked:
        return state, False, "The frayed cord is already tied as a visible caution marker."
    entry = {
        "site": site, "action": action,
        "account_id": int(account_id), "mask": str(mask)[:70],
        "event_id": int(event_id),
    }
    if role == "wanderer":
        entry["observation"] = "marked_caution" if caution_marked else "unmarked"
    state["field_decisions"][role] = entry
    return state, True, None



def publish_caution(raw, *, day, hour, account_id, mask_id, mask,
                    event_id, source_event_id, source_account_id,
                    source_mask_id, source_cord_id, source_hour):
    """One independent, qualified Chronicler notice per village day.

    The Hound's physical marker and completed ledger are verified separately
    by the adapter. This pure transition never asserts a monster or safe road.
    """
    state = refresh(raw, day)
    if day < state["day"]:
        return state, False, "A later village day is already recorded."
    if state["caution_notice"]:
        return state, False, "Today's sourced caution notice is already published."
    hound = state["field_decisions"].get("hound")
    if not hound:
        return state, False, "A firsthand signed Hound protection is required."
    raw_notice = {
        "day": day, "hour": hour, "account_id": account_id,
        "mask_id": mask_id, "mask": mask, "event_id": event_id,
        "source_event_id": source_event_id,
        "source_account_id": source_account_id,
        "source_mask_id": source_mask_id,
        "source_cord_id": source_cord_id,
        "source_hour": source_hour,
    }
    notice = _notice(raw_notice, state["field_decisions"], day)
    if not notice:
        return state, False, "Independent, chronological signed source evidence is required."
    state["caution_notice"] = notice
    return state, True, None


def field_lines(raw):
    """Source-limited public record; a professional report is not a hazard oracle."""
    state = normalize(raw)
    entries = state["field_decisions"]
    lines = []
    if "hound" in entries:
        hound = entries["hound"]
        lines.append(
            f"The Northern Treeline's frayed cord was tied as a caution marker "
            f"by {hound['mask']} (signed event {hound['event_id']}). "
            "This does not repair the cord or establish what damaged it."
        )
    if state["caution_notice"]:
        notice = state["caution_notice"]
        lines.append(
            f"{notice['mask']} published a Chronicler caution notice "
            f"(event {notice['event_id']}) based on the Hound's physical "
            f"cord marker (event {notice['source_event_id']}). "
            "This reports an observed warning, not a verified threat or safe route."
        )
    if "wanderer" in entries:
        traveler = entries["wanderer"]
        label = "marked caution" if traveler["observation"] == "marked_caution" else "unmarked cord"
        lines.append(
            f"{traveler['mask']} recorded a Wanderer's passage observation: "
            f"{label} (signed event {traveler['event_id']}). "
            "It describes the observed route at that time, not guaranteed safety."
        )
    return lines
