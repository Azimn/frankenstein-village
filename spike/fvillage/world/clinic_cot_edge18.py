"""GDD-EDGE-18: physical clinic cot repair and independent clinical approval.

The original cot owns this durable equipment record. Smith installation is
not clinical approval; Healer approval cannot fabricate a repair or cure.
The existing Workshop supplies finite iron and the canonical ledger verifies
source events in the Evennia adapter. This module contains pure state rules.
"""
from __future__ import annotations

from collections.abc import Mapping

def _id(value):
    return value if type(value) is int and value > 0 else None

def _time(day, hour):
    return _id(day) is not None and type(hour) is int and 0 <= hour <= 23

def _actor(row):
    if not isinstance(row, Mapping):
        return False
    if not _time(row.get("day"), row.get("hour")):
        return False
    return all(_id(row.get(k)) for k in ("event_id", "account_id", "mask_id", "cot_id"))

def fresh():
    return {"condition": "worn", "brace": None, "certification": None}

def normalize(raw):
    if raw is None:
        return fresh()
    if not isinstance(raw, Mapping):
        return {"condition": "invalid", "brace": None, "certification": None}
    condition = raw.get("condition")
    if condition == "worn" and raw.get("brace") is None and raw.get("certification") is None:
        return fresh()
    brace = raw.get("brace")
    if condition not in ("braced", "certified") or not _actor(brace):
        return {"condition": "invalid", "brace": None, "certification": None}
    if not all(_id(brace.get(k)) for k in ("item_id", "forge_event_id", "workshop_id")):
        return {"condition": "invalid", "brace": None, "certification": None}
    b = {k: brace[k] for k in (
        "day", "hour", "event_id", "account_id", "mask_id", "cot_id",
        "item_id", "forge_event_id", "workshop_id"
    )}
    b["mask"] = str(brace.get("mask") or "")[:70]
    if condition == "braced" and raw.get("certification") is None:
        return {"condition": "braced", "brace": b, "certification": None}
    cert = raw.get("certification")
    if condition != "certified" or not _actor(cert):
        return {"condition": "invalid", "brace": None, "certification": None}
    if (not _id(cert.get("assessment_event_id"))
            or cert["cot_id"] != b["cot_id"]
            or cert["account_id"] == b["account_id"]
            or cert["mask_id"] == b["mask_id"]
            or (cert["day"], cert["hour"]) < (b["day"], b["hour"])):
        return {"condition": "invalid", "brace": None, "certification": None}
    c = {k: cert[k] for k in (
        "day", "hour", "event_id", "account_id", "mask_id",
        "cot_id", "assessment_event_id"
    )}
    c["mask"] = str(cert.get("mask") or "")[:70]
    return {"condition": "certified", "brace": b, "certification": c}

def brace(raw, *, day, hour, event_id, account_id, mask_id, mask,
          cot_id, item_id, forge_event_id, workshop_id):
    state = normalize(raw)
    if state["condition"] != "worn":
        return state, False, "The cot has already been braced or its record is invalid."
    if (not _time(day, hour) or not all(_id(v) for v in (
            event_id, account_id, mask_id, cot_id, item_id,
            forge_event_id, workshop_id))):
        return state, False, "A real cot, fitting, worker and signed shift are required."
    state["condition"] = "braced"
    state["brace"] = {
        "day": day, "hour": hour, "event_id": event_id,
        "account_id": account_id, "mask_id": mask_id,
        "mask": str(mask or "")[:70], "cot_id": cot_id,
        "item_id": item_id, "forge_event_id": forge_event_id,
        "workshop_id": workshop_id,
    }
    return state, True, None

def certify(raw, *, day, hour, event_id, account_id, mask_id, mask,
            cot_id, assessment_event_id):
    state = normalize(raw)
    if state["condition"] != "braced":
        return state, False, "A real Smith fitting must be installed before approval."
    b = state["brace"]
    if (not _time(day, hour) or not all(_id(v) for v in (
            event_id, account_id, mask_id, cot_id, assessment_event_id))):
        return state, False, "The cot needs a signed clinical inspection and assessment."
    if cot_id != b["cot_id"]:
        return state, False, "The signed fitting belongs to another physical cot."
    if account_id == b["account_id"] or mask_id == b["mask_id"]:
        return state, False, "Clinical approval requires an independent Healer account."
    if (day, hour) < (b["day"], b["hour"]):
        return state, False, "The village clock precedes the physical installation."
    state["condition"] = "certified"
    state["certification"] = {
        "day": day, "hour": hour, "event_id": event_id,
        "account_id": account_id, "mask_id": mask_id,
        "mask": str(mask or "")[:70], "cot_id": cot_id,
        "assessment_event_id": assessment_event_id,
    }
    return state, True, None

def public_lines(raw):
    state = normalize(raw)
    condition = state["condition"]
    if condition == "worn":
        return ("The clinic cot's folding rail has a worn hinge. A Smith may "
                "bring a real Workshop-forged hinge and use clinic brace. "
                "Ordinary care remains possible; reinforced rest is unavailable.")
    if condition == "braced":
        return ("A Smith has fitted a real hinge to the cot rail. An independent "
                "Healer must assess today's patient and use clinic certify "
                "before reinforced rest can be offered.")
    if condition == "certified":
        return ("The cot rail is reinforced and clinically approved. "
                "A Healer may offer clinic treat supported after a current "
                "patient assessment. The fitting and approval are signed.")
    return "The cot repair record is inconsistent; reinforced rest is unavailable."
