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
    return {"day": int(day), "reports": {}, "field_decisions": {}, "safety_notice": None, "history": []}


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
        if role not in {"hound", "wanderer", "hound_assessment"} or not hasattr(entry, "get"):
            continue
        try:
            account, event = int(entry["account_id"]), int(entry["event_id"])
        except (ValueError, TypeError, KeyError, OverflowError):
            continue
        if (isinstance(entry.get("account_id"), bool)
                or isinstance(entry.get("event_id"), bool)
                or account < 1 or event < 1):
            continue
        action = {"hound": "protect", "wanderer": "passability",
                  "hound_assessment": "assess"}[role]
        observation = entry.get("observation")
        if entry.get("action") != action:
            continue
        if role in {"wanderer", "hound_assessment"} and observation not in {"unmarked", "marked_caution"}:
            continue
        decisions[role] = {"account_id": account, "mask": str(entry.get("mask") or "")[:70],
                           "event_id": event, "action": action, "site": "red_cord"}
        if role in {"wanderer", "hound_assessment"}:
            decisions[role]["observation"] = observation
    notice = value.get("safety_notice")
    signed_notice = None
    if isinstance(notice, Mapping):
        fields = ("account_id", "mask_id", "event_id", "source_event_id",
                  "source_account_id", "day", "hour")
        if (all(type(notice.get(k)) is int for k in fields)
                and all(notice[k] > 0 for k in fields if k != "hour")
                and 0 <= notice["hour"] < 24
                and notice["day"] == day
                and notice.get("observation") in {"unmarked", "marked_caution"}):
            signed_notice = {k: notice[k] for k in fields}
            signed_notice["mask"] = str(notice.get("mask") or "")[:70]
            signed_notice["observation"] = notice["observation"]
    return {
        "day": day,
        "reports": reports,
        "field_decisions": decisions,
        "safety_notice": signed_notice,
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
            "safety_notice": copy.deepcopy(state["safety_notice"]),
        }
        state["history"].append(previous)
        state["history"] = state["history"][-MAX_HISTORY:]
    state["day"] = day
    state["reports"] = {}
    state["field_decisions"] = {}
    state["safety_notice"] = None
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
        ("hound", "protect"), ("hound", "assess"),
        ("wanderer", "passability")
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
    slot = "hound_assessment" if (role, action) == ("hound", "assess") else role
    if slot in state["field_decisions"]:
        return state, False, "That professional field action is already signed today."
    if role == "hound" and caution_marked:
        return state, False, "The frayed cord is already tied as a visible caution marker."
    entry = {
        "site": site, "action": action,
        "account_id": int(account_id), "mask": str(mask)[:70],
        "event_id": int(event_id),
    }
    if action in {"passability", "assess"}:
        entry["observation"] = "marked_caution" if caution_marked else "unmarked"
    state["field_decisions"][slot] = entry
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
    if "hound_assessment" in entries:
        row = entries["hound_assessment"]
        condition = ("a tied caution marker" if row["observation"] == "marked_caution"
                     else "an unmarked frayed cord")
        lines.append(
            f"{row['mask']} assessed {condition} at the Northern Treeline "
            f"(Hound event {row['event_id']}). This is a dated observation, "
            "not a claim about an unseen threat."
        )
    if state["safety_notice"]:
        row = state["safety_notice"]
        lines.append(
            f"Chronicler {row['mask']} published a qualified route safety notice "
            f"(source Hound event {row['source_event_id']}, "
            f"notice event {row['event_id']}). The report describes "
            f"{'a marked caution' if row['observation'] == 'marked_caution' else 'an unmarked cord'} "
            "when the Hound inspected it. No injury or monster is established."
        )
    return lines

def verified_hound_assessment(entry, source, day):
    """Reject copied, failed, mismatched or invented Hound source events."""
    if not isinstance(entry, Mapping) or not isinstance(source, Mapping):
        return False
    actor, payload, result = (source.get("actor"), source.get("payload"),
                              source.get("consequence"))
    if not all(isinstance(x, Mapping) for x in (actor, payload, result)):
        return False
    if (type(day) is not int or day < 1
            or type(entry.get("event_id")) is not int
            or type(entry.get("account_id")) is not int
            or entry["event_id"] < 1 or entry["account_id"] < 1):
        return False
    if source.get("status") != "complete" or source.get("kind") != "village.route_hazard_assessed":
        return False
    if type(source.get("id")) is not int or source["id"] != entry["event_id"]:
        return False
    if (type(actor.get("account_id")) is not int
            or actor["account_id"] != entry["account_id"]
            or type(actor.get("mask_id")) is not int
            or actor["mask_id"] < 1
            or actor.get("mask") != entry.get("mask")):
        return False
    if (payload.get("site") != "red_cord" or payload.get("role") != "hound"
            or payload.get("action") != "assess"
            or payload.get("location") != "The Northern Treeline"
            or type(payload.get("day")) is not int or payload["day"] != day
            or type(payload.get("hour")) is not int
            or not 0 <= payload["hour"] < 24):
        return False
    if (result.get("site") != "red_cord" or result.get("role") != "hound"
            or result.get("action") != "assess" or result.get("day") != day
            or type(result.get("cord_object_id")) is not int
            or result["cord_object_id"] < 1
            or type(result.get("square_room_id")) is not int
            or result["square_room_id"] < 1
            or type(result.get("caution_marked")) is not bool):
        return False
    expected = "marked_caution" if result["caution_marked"] else "unmarked"
    return (entry.get("observation") == expected
            and result.get("interpretation") == expected)


def publish_safety_notice(raw, *, day, hour, account_id, mask_id, mask,
                          event_id, source):
    """An independent Chronicler cites the signed Hound assessment, once per day."""
    state = refresh(raw, day)
    if day < state["day"]:
        return state, False, "A later village day is already recorded."
    vals = (day, account_id, mask_id, event_id)
    if (any(type(x) is not int or x < 1 for x in vals)
            or type(hour) is not int or not 0 <= hour < 24):
        return state, False, "A signed Chronicler and valid village time are required."
    if state["safety_notice"]:
        return state, False, "Today's safety notice has already been published."
    hound = state["field_decisions"].get("hound_assessment")
    if not verified_hound_assessment(hound, source, day):
        return state, False, "A completed signed Hound assessment is required."
    if account_id == hound["account_id"]:
        return state, False, "An independent account must publish the Hound's evidence."
    if hour < source["payload"]["hour"]:
        return state, False, "The notice cannot predate the Hound assessment."
    state["safety_notice"] = {
        "day": day, "hour": hour, "account_id": account_id,
        "mask_id": mask_id, "mask": str(mask)[:70],
        "event_id": event_id, "source_event_id": hound["event_id"],
        "source_account_id": hound["account_id"],
        "observation": hound["observation"],
    }
    return state, True, None
