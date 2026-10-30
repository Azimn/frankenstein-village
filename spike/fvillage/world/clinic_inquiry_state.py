"""EDGE-28: independent procedural inquiry into a signed clinic assessment.

The cot and the existing clinic state remain authoritative. The inquiry
records a verified timeline, never a diagnosis, patient identity or culprit.
"""
from __future__ import annotations

from collections.abc import Mapping
import copy

MAX_RECORDS = 36


def positive(value):
    return value if type(value) is int and value > 0 else None


def stamp(day, hour):
    if positive(day) is None or type(hour) is not int or not 0 <= hour <= 23:
        return None
    return day * 24 + hour


def normalize(raw):
    result = {"records": []}
    if not isinstance(raw, Mapping):
        return result
    seen_events, seen_days = set(), set()
    entries = raw.get("records")
    if entries is None:
        return result
    if isinstance(entries, (str, bytes, Mapping)) or not hasattr(entries, "__iter__"):
        return result
    try:
        candidates = list(entries)[-MAX_RECORDS * 2:]
    except (TypeError, ValueError):
        return result
    for candidate in candidates:
        if not isinstance(candidate, Mapping):
            continue
        fields = ("account_id", "mask_id", "event_id", "source_event_id",
                  "source_account_id", "source_mask_id", "cot_id", "room_id")
        values = {name: positive(candidate.get(name)) for name in fields}
        day, hour = candidate.get("day"), candidate.get("hour")
        if (stamp(day, hour) is None or not all(values.values())
                or day in seen_days or values["event_id"] in seen_events
                or values["event_id"] == values["source_event_id"]
                or values["account_id"] == values["source_account_id"]):
            continue
        row = {**values, "day": day, "hour": hour,
               "mask": str(candidate.get("mask") or "")[:70],
               "finding": "qualified_clinic_timeline"}
        result["records"].append(row)
        seen_days.add(day)
        seen_events.add(values["event_id"])
    result["records"] = result["records"][-MAX_RECORDS:]
    return result


def source_valid(event, assessment, room_id):
    """Only a completed ledger event matching the original clinical state counts."""
    if not all(isinstance(x, Mapping) for x in (event, assessment)):
        return False
    actor, payload, consequence = (
        event.get("actor"), event.get("payload"), event.get("consequence"))
    if not all(isinstance(x, Mapping) for x in (actor, payload, consequence)):
        return False
    return (
        event.get("kind") == "village.clinic_assess"
        and event.get("status") == "complete"
        and positive(room_id) is not None
        # Two missing or malformed IDs must not authenticate one another.
        and positive(event.get("id")) is not None
        and positive(actor.get("account_id")) is not None
        and positive(actor.get("mask_id")) is not None
        and isinstance(actor.get("mask"), str)
        and bool(actor["mask"].strip())
        and positive(event.get("id")) == positive(assessment.get("event_id"))
        and positive(actor.get("account_id")) == positive(assessment.get("account_id"))
        and positive(actor.get("mask_id")) == positive(assessment.get("mask_id"))
        and actor.get("mask") == assessment.get("mask")
        and payload.get("professional_calling") == "healer"
        and stamp(payload.get("day"), payload.get("hour")) is not None
        and payload.get("day") == assessment.get("day")
        and payload.get("hour") == assessment.get("hour")
        and positive(consequence.get("room_id")) == room_id
        and positive(consequence.get("assessment_event_id")) == event.get("id")
        and consequence.get("patient_condition") in ("cold", "sprain", "fever")
    )


def investigate(raw, *, day, hour, account_id, mask_id, mask, event_id,
                source_event_id, source_account_id, source_mask_id,
                source_day, source_hour, cot_id, room_id):
    """One independent, same-patient-day procedural record per village day."""
    state = normalize(raw)
    now, earlier = stamp(day, hour), stamp(source_day, source_hour)
    ids = (account_id, mask_id, event_id, source_event_id,
           source_account_id, source_mask_id, cot_id, room_id)
    if now is None or earlier is None or any(positive(i) is None for i in ids):
        return state, False, "A real account, original cot and valid village clock are required."
    if day != source_day or now < earlier:
        return state, False, "The source is not from the present patient or lies in the future."
    if account_id == source_account_id:
        return state, False, "One account cannot sign both professional roles."
    if event_id == source_event_id:
        return state, False, "The inquiry requires its own independent signed event."
    if state["records"] and now < max(stamp(r["day"], r["hour"]) for r in state["records"]):
        return state, False, "The clock cannot rewind behind recorded clinic inquiries."
    if any(r["day"] == day or r["source_event_id"] == source_event_id
           or r["event_id"] == event_id for r in state["records"]):
        return state, False, "This patient-day already has an independent inquiry."
    state["records"].append({
        "day": day, "hour": hour, "account_id": account_id,
        "mask_id": mask_id, "mask": str(mask or "")[:70],
        "event_id": event_id, "source_event_id": source_event_id,
        "source_account_id": source_account_id,
        "source_mask_id": source_mask_id,
        "cot_id": cot_id, "room_id": room_id,
        "finding": "qualified_clinic_timeline",
    })
    state["records"] = state["records"][-MAX_RECORDS:]
    return copy.deepcopy(state), True, None


def signed_inquiry(row, event_lookup):
    """A persisted cot row is signed only when both canonical events agree."""
    if not isinstance(row, Mapping) or not callable(event_lookup):
        return False
    fields = ("event_id", "source_event_id", "account_id", "mask_id",
              "source_account_id", "source_mask_id", "cot_id", "room_id")
    if any(positive(row.get(key)) is None for key in fields):
        return False
    if (row["account_id"] == row["source_account_id"]
            or stamp(row.get("day"), row.get("hour")) is None):
        return False
    try:
        inquiry = event_lookup(row["event_id"])
        source = event_lookup(row["source_event_id"])
    except Exception:
        return False
    if not isinstance(inquiry, Mapping) or not isinstance(source, Mapping):
        return False
    actor, payload, consequence = (inquiry.get("actor"), inquiry.get("payload"),
                                   inquiry.get("consequence"))
    healer, source_payload, source_result = (source.get("actor"),
                                              source.get("payload"),
                                              source.get("consequence"))
    if not all(isinstance(part, Mapping) for part in
               (actor, payload, consequence, healer, source_payload, source_result)):
        return False
    first = stamp(source_payload.get("day"), source_payload.get("hour"))
    last = stamp(payload.get("day"), payload.get("hour"))
    if first is None or last is None or first > last:
        return False
    return bool(
        positive(inquiry.get("id")) == row["event_id"]
        and positive(source.get("id")) == row["source_event_id"]
        and inquiry.get("kind") == "village.clinic_inquiry"
        and inquiry.get("status") == "complete"
        and source.get("kind") == "village.clinic_assess"
        and source.get("status") == "complete"
        and positive(actor.get("account_id")) == row["account_id"]
        and positive(actor.get("mask_id")) == row["mask_id"]
        and actor.get("mask") == row.get("mask")
        and isinstance(actor.get("mask"), str) and bool(actor["mask"].strip())
        and positive(healer.get("account_id")) == row["source_account_id"]
        and positive(healer.get("mask_id")) == row["source_mask_id"]
        and isinstance(healer.get("mask"), str) and bool(healer["mask"].strip())
        and payload.get("professional_calling") == "detective"
        and source_payload.get("professional_calling") == "healer"
        and payload.get("day") == row["day"]
        and payload.get("hour") == row["hour"]
        and source_payload.get("day") == row["day"]
        and positive(payload.get("cot_id")) == row["cot_id"]
        and positive(payload.get("room_id")) == row["room_id"]
        and positive(payload.get("source_healer_event_id")) == row["source_event_id"]
        and positive(payload.get("source_healer_account_id")) == row["source_account_id"]
        and positive(consequence.get("cot_id")) == row["cot_id"]
        and positive(consequence.get("room_id")) == row["room_id"]
        and positive(consequence.get("source_healer_event_id")) == row["source_event_id"]
        and consequence.get("finding") == "qualified_clinic_timeline"
        and consequence.get("day") == row["day"]
        and consequence.get("hour") == row["hour"]
        and positive(source_result.get("room_id")) == row["room_id"]
        and positive(source_result.get("assessment_event_id")) == row["source_event_id"]
        and source_result.get("patient_condition") in ("cold", "sprain", "fever")
    )


def public_lines(raw, day, event_lookup=None):
    """Never advertise a stored inquiry as signed without its ledger chain."""
    if isinstance(raw, Mapping):
        entries = raw.get("records")
        if entries is not None and (isinstance(entries, (str, bytes, Mapping))
                                    or not hasattr(entries, "__iter__")):
            return "The clinic inquiry register requires signed source inspection."
    records = normalize(raw)["records"]
    current = next((r for r in reversed(records) if r["day"] == day), None)
    if not current:
        return ("No independent Detective inquiry has been signed for today's "
                "clinic cot. A Detective can look at the cot and use clinic investigate "
                "after a Healer's signed assessment.")
    if event_lookup is None:
        try:
            from world.events import get_event_ledger
            event_lookup = get_event_ledger().get_event
        except Exception:
            return "The clinic inquiry register requires signed source inspection."
    if not signed_inquiry(current, event_lookup):
        return "The clinic inquiry register requires signed source inspection."
    return ("Independent procedural clinic inquiry signed as event %s, "
            "linked to Healer assessment event %s. It records only the "
            "witnessed timeline, not private medical notes or a diagnosis."
            % (current["event_id"], current["source_event_id"]))
