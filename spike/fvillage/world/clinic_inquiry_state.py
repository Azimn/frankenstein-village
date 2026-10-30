"""EDGE-28: independent procedural inquiry into a signed clinic assessment.

The cot and the existing clinic state remain authoritative. The inquiry
records a verified timeline, never a diagnosis, patient identity or culprit.
"""
from __future__ import annotations

from collections.abc import Mapping
import copy

MAX_RECORDS = 36
# Two bounded, competing procedural interpretations. Neither is a diagnosis.
INTERPRETATIONS = ("possible_exposure", "unrelated_illness")
CASE_ITEM_KEY = "a cluster of mushrooms"


def alternative(interpretation):
    return next((name for name in INTERPRETATIONS if name != interpretation), None)


def positive(value):
    return value if type(value) is int and value > 0 else None


def well_case_source_valid(origin_well_id, actual_well_id, toxin_value):
    """Validate the well-grown object's persisted origin and hidden magnitude.

    The origin marker is set by ensure_well_mushrooms, never by the Detective.
    """
    return (positive(origin_well_id) is not None
            and positive(actual_well_id) is not None
            and origin_well_id == actual_well_id
            and type(toxin_value) is int and toxin_value > 0)


def choose_case_item(candidates, carrier):
    """Choose a real, already-validated specimen without arbitrary list order.

    Prefer a physically carried cluster over one left in the clinic room.
    Within either location use the stable Evennia object ID, not room.contents
    order. The adapter validates origin, toxin and location before this step;
    it rechecks the exact chosen object inside the signed consequence.
    """
    eligible = [obj for obj in candidates
                if positive(getattr(obj, "id", None)) is not None]
    return min(eligible,
               key=lambda obj: (obj.location is not carrier, obj.id),
               default=None)


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
                  "source_account_id", "source_mask_id", "cot_id", "room_id",
                  "case_item_id", "case_well_id")
        values = {name: positive(candidate.get(name)) for name in fields}
        day, hour = candidate.get("day"), candidate.get("hour")
        if (stamp(day, hour) is None or not all(values.values())
                or day in seen_days or values["event_id"] in seen_events
                or values["event_id"] == values["source_event_id"]
                or values["account_id"] == values["source_account_id"]
                or candidate.get("interpretation") not in INTERPRETATIONS
                or candidate.get("alternative") != alternative(candidate.get("interpretation"))):
            continue
        row = {**values, "day": day, "hour": hour,
               "mask": str(candidate.get("mask") or "")[:70],
               "finding": "contested_clinic_cause",
               "interpretation": candidate["interpretation"],
               "alternative": candidate["alternative"]}
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
                source_day, source_hour, cot_id, room_id, case_item_id=None,
                case_well_id=None, interpretation=None, preview=False):
    """Validate a player attempt; only a real ledger ID can sign a record.

    Preview checks the same physical, account, clock and duplicate gates,
    but does not invent an event ID or mutate even the returned state.
    """
    state = normalize(raw)
    now, earlier = stamp(day, hour), stamp(source_day, source_hour)
    ids = (account_id, mask_id, source_event_id,
           source_account_id, source_mask_id, cot_id, room_id, case_item_id,
           case_well_id)
    if (type(preview) is not bool or now is None or earlier is None
            or any(positive(i) is None for i in ids)
            or interpretation not in INTERPRETATIONS
            or (preview and event_id is not None)
            or (not preview and positive(event_id) is None)):
        return state, False, "A real account, original cot and valid village clock are required."
    if day != source_day or now < earlier:
        return state, False, "The source is not from the present patient or lies in the future."
    if account_id == source_account_id:
        return state, False, "One account cannot sign both professional roles."
    if not preview and event_id == source_event_id:
        return state, False, "The inquiry requires its own independent signed event."
    if state["records"] and now < max(stamp(r["day"], r["hour"]) for r in state["records"]):
        return state, False, "The clock cannot rewind behind recorded clinic inquiries."
    if any(r["day"] == day or r["source_event_id"] == source_event_id
           or (not preview and r["event_id"] == event_id)
           for r in state["records"]):
        return state, False, "This patient-day already has an independent inquiry."
    if preview:
        return copy.deepcopy(state), True, None
    state["records"].append({
        "day": day, "hour": hour, "account_id": account_id,
        "mask_id": mask_id, "mask": str(mask or "")[:70],
        "event_id": event_id, "source_event_id": source_event_id,
        "source_account_id": source_account_id,
        "source_mask_id": source_mask_id,
        "cot_id": cot_id, "room_id": room_id,
        "case_item_id": case_item_id, "case_well_id": case_well_id,
        "interpretation": interpretation,
        "alternative": alternative(interpretation),
        "finding": "contested_clinic_cause",
    })
    state["records"] = state["records"][-MAX_RECORDS:]
    return copy.deepcopy(state), True, None


def signed_inquiry(row, event_lookup):
    """A persisted cot row is signed only when both canonical events agree."""
    if not isinstance(row, Mapping) or not callable(event_lookup):
        return False
    fields = ("event_id", "source_event_id", "account_id", "mask_id",
              "source_account_id", "source_mask_id", "cot_id", "room_id",
              "case_item_id", "case_well_id")
    if any(positive(row.get(key)) is None for key in fields):
        return False
    if (row["account_id"] == row["source_account_id"]
            or stamp(row.get("day"), row.get("hour")) is None
            or row.get("interpretation") not in INTERPRETATIONS
            or row.get("alternative") != alternative(row.get("interpretation"))):
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
        and positive(payload.get("case_item_id")) == row["case_item_id"]
        and positive(payload.get("case_well_id")) == row["case_well_id"]
        and well_case_source_valid(
            payload.get("case_well_id"), row["case_well_id"],
            payload.get("case_item_toxin"))
        and payload.get("case_item_key") == CASE_ITEM_KEY
        and payload.get("interpretation") == row["interpretation"]
        and payload.get("alternative") == row["alternative"]
        and positive(payload.get("room_id")) == row["room_id"]
        and positive(payload.get("source_healer_event_id")) == row["source_event_id"]
        and positive(payload.get("source_healer_account_id")) == row["source_account_id"]
        and positive(consequence.get("cot_id")) == row["cot_id"]
        and positive(consequence.get("case_item_id")) == row["case_item_id"]
        and positive(consequence.get("case_well_id")) == row["case_well_id"]
        and consequence.get("case_item_toxin") == payload.get("case_item_toxin")
        and consequence.get("interpretation") == row["interpretation"]
        and consequence.get("alternative") == row["alternative"]
        and consequence.get("causal_status") == "unproven"
        and positive(consequence.get("room_id")) == row["room_id"]
        and positive(consequence.get("source_healer_event_id")) == row["source_event_id"]
        and consequence.get("finding") == "contested_clinic_cause"
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
                "clinic cot. A Detective can look at the cot, bring a real well-mushroom "
                "cluster to St. Lazarus, and use clinic investigate illness or "
                "clinic investigate exposure after a Healer's signed assessment. "
                "Neither hypothesis is a proven cause.")
    if event_lookup is None:
        try:
            from world.events import get_event_ledger
            event_lookup = get_event_ledger().get_event
        except Exception:
            return "The clinic inquiry register requires signed source inspection."
    if not signed_inquiry(current, event_lookup):
        return "The clinic inquiry register requires signed source inspection."
    labels = {"possible_exposure": "possible environmental exposure",
              "unrelated_illness": "an unrelated illness"}
    return ("Independent procedural clinic inquiry signed as event %s, "
            "linked to Healer assessment event %s and physical specimen %s. "
            "Competing interpretations: %s versus %s. The source and timing "
            "are documented, but neither causal explanation is proven. "
            "No private medical notes or diagnosis are disclosed."
            % (current["event_id"], current["source_event_id"],
               current["case_item_id"], labels[current["interpretation"]],
               labels[current["alternative"]]))
