"""One truthful, renewable daily civic survey across four real districts.

Each accepted report must come from a mask physically at a supported landmark.
The pure state machine never invents an observation, moves a character, or
rewards XP. Four unique, signed reports change the public daily report from
incomplete to complete. Incomplete days become explicit historical outcomes.
"""
from __future__ import annotations

import copy
from collections.abc import Mapping, Sequence

SITES = ("grave_marker", "red_cord", "market_scale", "river_gauge")
MAX_HISTORY = 30


def fresh(day=0):
    return {"day": int(day), "reports": {}, "field_decisions": {}, "history": []}


def normalize(raw):
    # Persisted Evennia attributes can be malformed after interrupted or old
    # writes. Reject invalid shapes instead of crashing every survey reader.
    value = copy.deepcopy(dict(raw)) if isinstance(raw, Mapping) else {}
    try:
        day = max(0, int(value.get("day") or 0))
    except (TypeError, ValueError, OverflowError):
        day = 0
    reports = {}
    saved_reports = value.get("reports")
    for ident, entry in (saved_reports.items() if isinstance(saved_reports, Mapping) else ()):
        if ident not in SITES or not hasattr(entry, "get"):
            continue
        try:
            account = int(entry["account_id"])
            event = int(entry["event_id"])
        except (ValueError, TypeError, KeyError, OverflowError):
            continue
        if (isinstance(entry.get("account_id"), bool)
                or isinstance(entry.get("event_id"), bool)
                or account < 1 or event < 1):
            continue
        reports[ident] = {
            "account_id": account, "mask": str(entry.get("mask") or "")[:70],
            "event_id": event,
        }
    decisions = {}
    saved_decisions = value.get("field_decisions")
    for role, entry in (saved_decisions.items() if isinstance(saved_decisions, Mapping) else ()):
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
        if role == "wanderer" and observation not in ("unmarked", "marked_caution"):
            continue
        decisions[role] = {"account_id": account, "mask": str(entry.get("mask") or "")[:70],
                           "event_id": event, "action": action, "site": "red_cord"}
        if role == "wanderer":
            decisions[role]["observation"] = observation
        else:
            # Older Hound records predate the daily maintenance distinction.
            decisions[role]["renewed"] = entry.get("renewed") is True
    saved_history = value.get("history")
    # Evennia persists Attribute lists as _SaverList (MutableSequence), not
    # built-in list. Reject strings and mappings, but preserve wrapped rows.
    if not isinstance(saved_history, Sequence) or isinstance(
        saved_history, (str, bytes, bytearray)
    ):
        saved_history = []
    return {
        "day": day,
        "reports": reports,
        "field_decisions": decisions,
        "history": list(saved_history)[-MAX_HISTORY:],
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
        }
        state["history"].append(previous)
        state["history"] = state["history"][-MAX_HISTORY:]
    state["day"] = day
    state["reports"] = {}
    state["field_decisions"] = {}
    return state


def report(raw, day, ident, account_id, mask, event_id):
    state = refresh(raw, day)
    if day < state["day"]:
        return state, False, "A later village day is already recorded."
    if ident not in SITES:
        return state, False, "That location is not on today's inspection route."
    if ident in state["reports"]:
        return state, False, "Today's report for this landmark is already signed."
    if isinstance(account_id, bool) or isinstance(event_id, bool):
        return state, False, "A signed account and canonical event are required."
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
    entry = {
        "site": site, "action": action,
        "account_id": int(account_id), "mask": str(mask)[:70],
        "event_id": int(event_id),
    }
    if role == "wanderer":
        entry["observation"] = "marked_caution" if caution_marked else "unmarked"
    else:
        # A later day can tend an existing warning without pretending the
        # cord was newly repaired or spending imaginary supplies.
        entry["renewed"] = caution_marked
    state["field_decisions"][role] = entry
    return state, True, None


def history_records(raw, day, *, limit=5, selected_day=None):
    """Public, read-only snapshots of previous village days, newest first.

    A day transition can be viewed before the next report is signed. Archive
    rows are normalized through the same public report and field-decision
    validators, so unrelated private keys and malformed receipts never leak.
    The stored record is not mutated and no new canonical state is created.
    """
    state = refresh(raw, day)
    # Exact-day lookups may inspect the whole retained archive, but never
    # private keys, dates at/after the current day, or malformed day values.
    if selected_day is not None and (
        type(selected_day) is not int or selected_day < 1
    ):
        return []
    try:
        count = max(0, min(10, int(limit)))
    except (TypeError, ValueError, OverflowError):
        count = 0
    if count == 0:
        return []
    rows = []
    for raw_row in state["history"][-MAX_HISTORY:]:
        if not isinstance(raw_row, Mapping):
            continue
        try:
            old_day = int(raw_row.get("day"))
        except (TypeError, ValueError, OverflowError):
            continue
        if (isinstance(raw_row.get("day"), bool)
                or old_day < 1 or old_day >= state["day"]):
            continue
        reports = raw_row.get("reports")
        decisions = raw_row.get("field_decisions")
        clean = normalize({
            "day": old_day,
            "reports": reports if isinstance(reports, Mapping) else {},
            "field_decisions": decisions if isinstance(decisions, Mapping) else {},
        })
        rows.append({
            "day": old_day,
            "completed": len(clean["reports"]) == len(SITES),
            "reports": clean["reports"],
            "field_decisions": clean["field_decisions"],
        })
    if selected_day is not None:
        matches = [row for row in rows if row["day"] == selected_day]
        return matches[-1:]  # one authoritative dated snapshot
    return rows[-count:][::-1]


def field_lines(raw):
    """Source-limited public record; a professional report is not a hazard oracle."""
    state = normalize(raw)
    entries = state["field_decisions"]
    lines = []
    if "hound" in entries:
        hound = entries["hound"]
        action = "tended" if hound.get("renewed") else "tied"
        lines.append(
            f"The Northern Treeline's frayed cord was {action} as a caution marker "
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
