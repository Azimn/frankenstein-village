"""Smith and Merchant interdependence for one persistent public-lamp repair."""

from __future__ import annotations

import copy

from evennia.scripts.models import ScriptDB
from evennia.utils import search

from world.callings import active_calling, record_participation
from world.object_properties import mechanical_value
from world.situations import (
    LAMP_REPAIR_ID,
    ensure_situations,
    get_situation,
    get_situation_registry,
)

LAMP_KEY = "north-square gas lamp"
STOCK_KEY = "a tray of brass mantle collars"
LAMP_LOCATION = "Village Square"
STOCK_LOCATION = "The Lamp Shop"
REQUIRED_PART = "brass mantle collar"


def _clock():
    try:
        clock = ScriptDB.objects.get(db_key="village_time")
        return int(clock.db.day or 1), int(
            clock.db.hour if clock.db.hour is not None else 21
        )
    except ScriptDB.DoesNotExist:
        return 1, 21


def _deadline_after(day, hour, hours=12):
    absolute = (int(day) - 1) * 24 + int(hour) + int(hours)
    return absolute // 24 + 1, absolute % 24


def _case():
    ensure_situations()
    return get_situation(LAMP_REPAIR_ID)


def _save(case):
    registry = get_situation_registry()
    situations = copy.deepcopy(dict(registry.db.situations or {}))
    situations[LAMP_REPAIR_ID] = copy.deepcopy(case)
    registry.db.situations = situations
    return copy.deepcopy(case)


def _exact_object(key, room_key):
    matches = [
        obj for obj in search.search_object(key)
        if obj.key == key
        and getattr(getattr(obj, "location", None), "key", None) == room_key
    ]
    return matches[0] if len(matches) == 1 else None


def repair_lamp():
    return _exact_object(LAMP_KEY, LAMP_LOCATION)


def repair_stock():
    return _exact_object(STOCK_KEY, STOCK_LOCATION)


def sync_lamp_description(lamp=None):
    lamp = lamp or repair_lamp()
    if lamp is None:
        return False
    if str(lamp.db.repair_state or "broken") == "working":
        lamp.db.desc = (
            "The north-square gas lamp burns with a steady yellow flame. A "
            "fresh brass collar seats the mantle cleanly beneath the glass."
        )
    else:
        lamp.db.desc = (
            "The north-square gas lamp is dark although its glass is intact and "
            "the feed pipe appears seated. The mantle will not hold a flame. "
            "The fault is inside the fitting rather than obvious damage."
        )
    return True


def sync_stock_description(stock=None):
    stock = stock or repair_stock()
    if stock is None:
        return False
    capacity = mechanical_value(stock, "uses", None)
    if stock.db.units is None and capacity is not None:
        stock.db.units = int(capacity)
    units = int(stock.db.units or 0)
    suffix = "s" if units != 1 else ""
    stock.db.desc = (
        "A shallow trade tray of fitted brass collars used to seat gas-lamp "
        f"mantles. {units} replacement unit{suffix} remain."
    )
    return True


def ensure_lamp_repair_case():
    case = _case()
    mutations = copy.deepcopy(dict(case.get("objective_mutations") or {}))
    existing = dict(mutations.get("lamp_initialized") or {})
    lamp = repair_lamp()
    stock = repair_stock()
    if lamp is None or stock is None:
        return {"case": case, "created": False, "error": "repair objects unavailable"}

    if lamp.db.repair_state is None:
        lamp.db.repair_state = "broken"
    if lamp.db.repair_fault is None and lamp.db.repair_state != "working":
        lamp.db.repair_fault = "cracked mantle collar"
    capacity = mechanical_value(stock, "uses", None)
    if stock.db.units is None and capacity is not None:
        stock.db.units = int(capacity)
    sync_lamp_description(lamp)
    sync_stock_description(stock)
    if existing:
        return {"case": case, "created": False, "initialization": existing}

    day, hour = _clock()
    due_day, due_hour = _deadline_after(day, hour)
    from world.events import publish_world_event
    event = publish_world_event(
        "civic.public_lamp_broken",
        payload={
            "harbinger": False,
            "chronicle_eligible": False,
            "situation_id": LAMP_REPAIR_ID,
            "lamp_object_id": lamp.id,
            "lamp_object_key": lamp.key,
            "location": LAMP_LOCATION,
        },
    )
    initialization = {
        "lamp_object_id": lamp.id,
        "lamp_object_key": lamp.key,
        "stock_object_id": stock.id,
        "stock_object_key": stock.key,
        "stock_units_at_surface": int(stock.db.units or 0),
        "event_id": event["id"],
        "day": int(day),
        "hour": int(hour),
    }
    mutations["lamp_initialized"] = initialization
    case["objective_mutations"] = mutations
    case["state"] = "surfaced"
    case["surfaced_day"] = int(day)
    case["surfaced_hour"] = int(hour)
    case["deadline_day"] = int(due_day)
    case["deadline_hour"] = int(due_hour)
    case["surface_count"] = max(1, int(case.get("surface_count") or 0))
    case["event_ids"] = list(case.get("event_ids") or []) + [event["id"]]
    return {"case": _save(case), "created": True, "initialization": initialization}


def repair_status():
    ensure_lamp_repair_case()
    return reconcile_lamp_repair_case()


def _same_location(mask, obj, room_key):
    room = getattr(mask, "location", None)
    return bool(room and room is getattr(obj, "location", None) and room.key == room_key)


def submit_smith_repair_diagnosis(mask, target):
    case = repair_status()
    mutations = copy.deepcopy(dict(case.get("objective_mutations") or {}))
    existing = dict(mutations.get("smith_diagnosis") or {})
    if case.get("state") == "aftermath":
        if existing:
            return {"case": case, "diagnosis": existing, "created": False}, None
        return None, "The Broken Mantle case is already closed."
    if active_calling(mask) != "smith":
        return None, "Diagnosing this repair requires an active Smith calling."
    if getattr(target, "key", None) != LAMP_KEY:
        return None, "This repair case concerns the north-square gas lamp."
    if not _same_location(mask, target, LAMP_LOCATION):
        return None, "The Smith must inspect the lamp in the Village Square."
    if existing:
        return {"case": case, "diagnosis": existing, "created": False}, None

    from world.events import publish_world_event
    event = publish_world_event(
        "professional.smith_lamp_diagnosis",
        actor=mask,
        payload={
            "harbinger": False,
            "chronicle_eligible": False,
            "situation_id": LAMP_REPAIR_ID,
            "professional_calling": "smith",
            "lamp_object_id": target.id,
            "lamp_object_key": target.key,
            "finding": "cracked mantle collar",
            "required_part": REQUIRED_PART,
        },
    )
    day, hour = _clock()
    diagnosis = {
        "calling": "smith",
        "mask_id": getattr(mask, "id", None),
        "mask": getattr(mask, "key", None),
        "event_id": event["id"],
        "lamp_object_id": target.id,
        "lamp_object_key": target.key,
        "finding": "cracked mantle collar",
        "required_part": REQUIRED_PART,
        "day": int(day),
        "hour": int(hour),
    }
    mutations["smith_diagnosis"] = diagnosis
    case["objective_mutations"] = mutations
    case["state"] = "investigating"
    case["event_ids"] = list(case.get("event_ids") or []) + [event["id"]]
    saved = _save(case)
    record_participation(mask, "repair_diagnoses", calling="smith")
    return {"case": saved, "diagnosis": diagnosis, "created": True}, None


def procure_merchant_repair_part(mask):
    case = repair_status()
    mutations = copy.deepcopy(dict(case.get("objective_mutations") or {}))
    existing = dict(mutations.get("merchant_procurement") or {})
    if case.get("state") == "aftermath":
        if existing:
            return {"case": case, "procurement": existing, "created": False}, None
        return None, "The Broken Mantle case is already closed."
    if active_calling(mask) != "merchant":
        return None, "Procuring the repair part requires an active Merchant calling."
    diagnosis = dict(mutations.get("smith_diagnosis") or {})
    if not diagnosis:
        return None, "A Smith must diagnose the lamp before a Merchant can procure the right part."
    if existing:
        return {"case": case, "procurement": existing, "created": False}, None

    stock = repair_stock()
    if stock is None:
        return None, "The Lamp Shop replacement stock is unavailable."
    room = getattr(mask, "location", None)
    if not room or room is not getattr(stock, "location", None) or room.key != STOCK_LOCATION:
        return None, "The Merchant must procure the replacement from the Lamp Shop."

    capacity = mechanical_value(stock, "uses", None)
    if stock.db.units is None and capacity is not None:
        stock.db.units = int(capacity)
    before = int(stock.db.units or 0)
    if before <= 0:
        return None, "The Lamp Shop has no brass mantle collars left to procure."
    unit_worth = int(mechanical_value(stock, "worth", 0) or 0)
    stock.db.units = before - 1
    sync_stock_description(stock)

    from world.events import publish_world_event
    event = publish_world_event(
        "professional.merchant_repair_procurement",
        actor=mask,
        payload={
            "harbinger": False,
            "chronicle_eligible": False,
            "situation_id": LAMP_REPAIR_ID,
            "professional_calling": "merchant",
            "source_smith_event_id": diagnosis.get("event_id"),
            "resource_object_id": stock.id,
            "resource_object_key": stock.key,
            "required_part": REQUIRED_PART,
            "unit_worth": unit_worth,
            "units_before": before,
            "units_after": int(stock.db.units or 0),
        },
    )
    day, hour = _clock()
    procurement = {
        "calling": "merchant",
        "mask_id": getattr(mask, "id", None),
        "mask": getattr(mask, "key", None),
        "event_id": event["id"],
        "source_smith_event_id": diagnosis.get("event_id"),
        "resource_object_id": stock.id,
        "resource_object_key": stock.key,
        "required_part": REQUIRED_PART,
        "unit_worth": unit_worth,
        "units_before": before,
        "units_after": int(stock.db.units or 0),
        "day": int(day),
        "hour": int(hour),
    }
    mutations["merchant_procurement"] = procurement
    case["objective_mutations"] = mutations
    case["state"] = "changing"
    case["event_ids"] = list(case.get("event_ids") or []) + [event["id"]]
    saved = _save(case)
    record_participation(mask, "repair_procurements", calling="merchant")
    return {"case": saved, "procurement": procurement, "created": True}, None


def complete_smith_lamp_repair(mask, target):
    case = repair_status()
    mutations = copy.deepcopy(dict(case.get("objective_mutations") or {}))
    existing = dict(mutations.get("smith_repair") or {})
    if case.get("state") == "aftermath":
        if existing:
            return {"case": case, "repair": existing, "created": False}, None
        return None, "The Broken Mantle case closed with the lamp still dark."
    if active_calling(mask) != "smith":
        return None, "Completing this repair requires an active Smith calling."
    if getattr(target, "key", None) != LAMP_KEY:
        return None, "This repair case concerns the north-square gas lamp."
    if not _same_location(mask, target, LAMP_LOCATION):
        return None, "The Smith must repair the lamp in the Village Square."
    diagnosis = dict(mutations.get("smith_diagnosis") or {})
    if not diagnosis:
        return None, "A Smith diagnosis must establish the fault before repair."
    procurement = dict(mutations.get("merchant_procurement") or {})
    if not procurement:
        return None, "A Merchant must procure the replacement collar before the Smith can finish."
    if existing:
        return {"case": case, "repair": existing, "created": False}, None

    from world.events import publish_world_event
    def consequence(event):
        target.db.repair_state = "working"
        target.db.repair_fault = None
        target.db.repaired_by_event_id = event["id"]
        sync_lamp_description(target)
        return {
            "lamp_object_id": target.id,
            "lamp_object_key": target.key,
            "repair_state": "working",
            "installed_part": REQUIRED_PART,
        }

    event = publish_world_event(
        "professional.smith_lamp_repair_completed",
        actor=mask,
        payload={
            "harbinger": False,
            "chronicle_eligible": False,
            "situation_id": LAMP_REPAIR_ID,
            "professional_calling": "smith",
            "source_smith_diagnosis_event_id": diagnosis.get("event_id"),
            "source_merchant_event_id": procurement.get("event_id"),
            "resource_object_id": procurement.get("resource_object_id"),
            "resource_object_key": procurement.get("resource_object_key"),
            "installed_part": REQUIRED_PART,
        },
        consequence=consequence,
    )
    day, hour = _clock()
    repair = {
        "calling": "smith",
        "mask_id": getattr(mask, "id", None),
        "mask": getattr(mask, "key", None),
        "event_id": event["id"],
        "lamp_object_id": target.id,
        "lamp_object_key": target.key,
        "source_smith_diagnosis_event_id": diagnosis.get("event_id"),
        "source_merchant_event_id": procurement.get("event_id"),
        "resource_object_id": procurement.get("resource_object_id"),
        "resource_object_key": procurement.get("resource_object_key"),
        "installed_part": REQUIRED_PART,
        "day": int(day),
        "hour": int(hour),
    }
    mutations["smith_repair"] = repair
    case["objective_mutations"] = mutations
    case["state"] = "aftermath"
    case["branch"] = "repaired"
    case["resolved_day"] = int(day)
    case["resolved_hour"] = int(hour)
    case["aftermath"] = (
        "A Smith diagnosed the failed fitting, a Merchant spent real Lamp Shop "
        "stock, and the Smith returned the public lamp to service."
    )
    case["event_ids"] = list(case.get("event_ids") or []) + [event["id"]]
    saved = _save(case)
    record_participation(mask, "repair_completions", calling="smith")
    return {"case": saved, "repair": repair, "created": True}, None


def reconcile_lamp_repair_case():
    case = _case()
    if case.get("state") == "aftermath":
        return case
    due_day = case.get("deadline_day")
    due_hour = case.get("deadline_hour")
    if due_day is None or due_hour is None:
        return case
    day, hour = _clock()
    if (int(day), int(hour)) < (int(due_day), int(due_hour)):
        return case

    lamp = repair_lamp()
    if lamp is None:
        return case
    from world.events import publish_world_event
    event = publish_world_event(
        "civic.public_lamp_left_dark",
        payload={
            "harbinger": False,
            "chronicle_eligible": False,
            "situation_id": LAMP_REPAIR_ID,
            "lamp_object_id": lamp.id,
            "lamp_object_key": lamp.key,
            "location": LAMP_LOCATION,
        },
    )
    lamp.db.repair_state = "broken"
    lamp.db.repair_failure = "deadline"
    sync_lamp_description(lamp)
    mutations = copy.deepcopy(dict(case.get("objective_mutations") or {}))
    mutations["deadline_failure"] = {
        "event_id": event["id"],
        "lamp_object_id": lamp.id,
        "lamp_object_key": lamp.key,
        "day": int(day),
        "hour": int(hour),
        "repair_state": "broken",
    }
    case["objective_mutations"] = mutations
    case["state"] = "aftermath"
    case["branch"] = "left_dark"
    case["resolved_day"] = int(day)
    case["resolved_hour"] = int(hour)
    case["aftermath"] = (
        "The repair window closed before the professional chain was completed. "
        "The north-square gas lamp remains dark."
    )
    case["event_ids"] = list(case.get("event_ids") or []) + [event["id"]]
    return _save(case)
