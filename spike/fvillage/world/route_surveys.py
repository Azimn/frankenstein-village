"""One truthful, renewable daily civic survey across four real districts.

Each accepted report must come from a mask physically at a supported landmark.
The pure state machine never invents an observation, moves a character, or
rewards XP. Four unique, signed reports change the public daily report from
incomplete to complete. Incomplete days become explicit historical outcomes.
"""
from __future__ import annotations

import copy

SITES = ("grave_marker", "red_cord", "market_scale", "river_gauge")
MAX_HISTORY = 30


def fresh(day=0):
    return {"day": int(day), "reports": {}, "field_decisions": {}, "advisory": None, "history": []}


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
    # A map is an attributed editorial snapshot, never a live hazard oracle.
    advisory = None
    item = value.get("advisory")
    if hasattr(item, "get"):
        try:
            publisher = int(item["account_id"])
            event_id = int(item["event_id"])
            source_account = int(item["source_account_id"])
            source_event = int(item["source_event_id"])
            source_day = int(item["source_day"])
            version = int(item["version"])
        except (TypeError, ValueError, KeyError, OverflowError):
            pass
        else:
            if (all(not isinstance(item.get(k), bool) for k in (
                    "account_id", "event_id", "source_account_id",
                    "source_event_id", "source_day", "version"))
                    and min(publisher, event_id, source_account, source_event) > 0
                    and publisher != source_account and source_day == day
                    and event_id != source_event and version == 1
                    and item.get("observation") in {"unmarked", "marked_caution"}
                    and decisions.get("wanderer") is not None
                    and decisions["wanderer"]["account_id"] == source_account
                    and decisions["wanderer"]["event_id"] == source_event
                    and decisions["wanderer"]["observation"] == item["observation"]):
                advisory = {
                    "account_id": publisher, "mask": str(item.get("mask") or "")[:70],
                    "event_id": event_id, "version": version, "site": "red_cord",
                    "source_account_id": source_account,
                    "source_event_id": source_event, "source_day": source_day,
                    "source_mask": str(item.get("source_mask") or "")[:70],
                    "observation": item["observation"],
                }
    return {
        "day": day,
        "reports": reports,
        "field_decisions": decisions,
        "advisory": advisory,
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
            "advisory": copy.deepcopy(state["advisory"]),
        }
        state["history"].append(previous)
        state["history"] = state["history"][-MAX_HISTORY:]
    state["day"] = day
    state["reports"] = {}
    state["field_decisions"] = {}
    state["advisory"] = None
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
    if "wanderer" in entries:
        traveler = entries["wanderer"]
        label = "marked caution" if traveler["observation"] == "marked_caution" else "unmarked cord"
        lines.append(
            f"{traveler['mask']} recorded a Wanderer's passage observation: "
            f"{label} (signed event {traveler['event_id']}). "
            "It describes the observed route at that time, not guaranteed safety."
        )
    return lines


def publish_advisory(raw, day, account_id, mask, event_id, source_event_id):
    """One Chronicler edition from another account's signed Wanderer fieldwork.

    The source is the existing firsthand, daily passability record. A later
    Hound warning cannot retroactively alter what the Wanderer saw. The
    edition is finite to one per village day and archived at rollover.
    """
    state = refresh(raw, day)
    if day < state["day"]:
        return state, False, "A later village day is already recorded."
    source = state["field_decisions"].get("wanderer")
    if source is None:
        return state, False, "A Wanderer's signed firsthand route observation is required."
    if state["advisory"] is not None:
        return state, False, "Today's sourced map advisory is already published."
    try:
        values = (account_id, event_id, source_event_id)
        if any(isinstance(value, bool) for value in values):
            raise ValueError("Boolean identifiers are not accounts or events")
        account_id, event_id, source_event_id = (int(value) for value in values)
    except (TypeError, ValueError, OverflowError):
        return state, False, "Signed account and event identifiers are required."
    if min(account_id, event_id, source_event_id) < 1 or event_id == source_event_id:
        return state, False, "Signed account and event identifiers are required."
    if source["account_id"] == account_id:
        return state, False, "An independent Chronicler account must edit this field report."
    if source_event_id != source["event_id"]:
        return state, False, "The cited Wanderer source event does not match the actual survey."
    state["advisory"] = {
        "version": 1, "site": "red_cord", "account_id": account_id,
        "mask": str(mask)[:70], "event_id": event_id,
        "source_account_id": source["account_id"],
        "source_mask": source["mask"], "source_event_id": source_event_id,
        "source_day": state["day"], "observation": source["observation"],
    }
    return state, True, None


def advisory_lines(raw):
    state = normalize(raw)
    item = state["advisory"]
    if item is None:
        return ["No Chronicler route map edition has been published today. "
                "A Chronicler can use survey publish in the Village Square "
                "after an independent Wanderer signs survey passability."]
    label = "marked caution" if item["observation"] == "marked_caution" else "unmarked cord"
    return [
        f"Public route map v{item['version']} for day {item['source_day']}: "
        f"Chronicler {item['mask']} (signed event {item['event_id']}) edited "
        f"{item['source_mask']}'s firsthand {label} report "
        f"(source event {item['source_event_id']}). "
        "This dated account is not a current safety guarantee or proof of a hazard."
    ]
