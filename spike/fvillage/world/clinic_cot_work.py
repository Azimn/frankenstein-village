"""GDD-EDGE-18: actual Workshop fitting, clinic cot and signed Healer approval.

Uses the original Church cot, finite Market Workshop hinge, clinic assessment,
Calling identity and canonical WorldEventLedger. No new quest/economy ledger.
"""
from __future__ import annotations

from django.db import transaction
from evennia.utils import search

from world import clinic_cot_edge18 as rules, clinic_state, clinic_work, workshop_work
from world.callings import active_calling, record_participation
from world.events import get_event_ledger, publish_world_event

def _cot():
    church = clinic_work._room()
    if church is None:
        return None
    found = [o for o in search.search_object(clinic_work.COT)
             if o.key == clinic_work.COT and o.location == church]
    return found[0] if len(found) == 1 else None

def _guard(mask, calling):
    church, error = clinic_work._guard(mask)
    if error:
        return None, error
    if active_calling(mask) != calling:
        return None, "An active " + calling.title() + " Calling is required."
    cot = _cot()
    if cot is None:
        return None, "The original clinic treatment cot is missing."
    return cot, None

def status():
    cot = _cot()
    return rules.public_lines(cot.db.clinic_equipment if cot else {"condition": "invalid"})

def _forge(item):
    source = item.db.forged_market_part
    if not hasattr(source, "get"):
        return None, "The carried hinge lacks physical Workshop provenance."
    workshop = workshop_work._room(workshop_work.WORKSHOP)
    if workshop is None:
        return None, "The original Market Workshop is missing."
    forge_id = source.get("source_event_id")
    if type(forge_id) is not int or forge_id <= 0:
        return None, "The fitting has no signed forging event."
    event = get_event_ledger().get_event(forge_id)
    if (not event or event.get("kind") != "village.market_hinge_forged"
            or event.get("status") != "complete"
            or not hasattr(event.get("actor"), "get")
            or not hasattr(event.get("payload"), "get")
            or not hasattr(event.get("consequence"), "get")
            or event["actor"].get("account_id") != source.get("smith_account_id")
            or event["payload"].get("room_id") != workshop.id
            or event["payload"].get("day") != source.get("issued_day")
            or event["consequence"].get("item_id") != item.id
            or event["consequence"].get("source_room_id") != workshop.id
            or source.get("source_room_id") != workshop.id):
        return None, "The hinge has no matching completed Workshop forge receipt."
    day, _hour = clinic_work._clock()
    if (type(source.get("issued_day")) is not int
            or source["issued_day"] > day):
        return None, "The hinge has an invalid or future workshop date."
    return {"forge_event_id": forge_id, "workshop_id": workshop.id}, None

def brace(mask):
    cot, error = _guard(mask, "smith")
    if error:
        return None, error
    items = [o for o in mask.contents
             if o.key == workshop_work.FITTING
             and hasattr(o.db.forged_market_part, "get")]
    if len(items) != 1:
        return None, "Carry one real Workshop-forged iron hinge to the Church cot."
    item = items[0]
    source, error = _forge(item)
    if error:
        return None, error
    day, hour = clinic_work._clock()
    props = dict(day=day, hour=hour, account_id=mask.account.id,
                 mask_id=mask.id, mask=mask.key, cot_id=cot.id,
                 item_id=item.id, **source)
    _preview, okay, reason = rules.brace(
        cot.db.clinic_equipment, event_id=1, **props)
    if not okay:
        return None, reason

    def consequence(event):
        with transaction.atomic():
            if (clinic_work._clock() != (day, hour)
                    or mask.location != cot.location
                    or active_calling(mask) != "smith"
                    or item.location != mask):
                raise RuntimeError("Smith, hinge or clinic shift changed.")
            fresh_source, why = _forge(item)
            if why or fresh_source != source:
                raise RuntimeError(why or "Forging provenance changed.")
            changed, valid, why = rules.brace(
                cot.db.clinic_equipment, event_id=event["id"], **props)
            if not valid:
                raise RuntimeError(why)
            cot.db.clinic_equipment = changed
            consumed_id = item.id
            item.delete()
            return {"cot_id": cot.id, "consumed_item_id": consumed_id,
                    "forge_event_id": source["forge_event_id"],
                    "workshop_id": source["workshop_id"],
                    "condition": "braced"}

    event = publish_world_event(
        "professional.clinic_cot_braced", actor=mask,
        payload={"day": day, "hour": hour, "cot_id": cot.id,
                 "forge_event_id": source["forge_event_id"],
                 "professional_calling": "smith",
                 "harbinger": False, "chronicle_eligible": False},
        consequence=consequence,
    )
    record_participation(mask, "clinic_cot_braces", calling="smith")
    return {"event_id": event["id"], "forge_event_id": source["forge_event_id"]}, None

def _verified_brace(cot):
    state = rules.normalize(cot.db.clinic_equipment)
    if state["condition"] not in ("braced", "certified"):
        return None, "The physical cot has no valid completed fitting."
    b = state["brace"]
    event = get_event_ledger().get_event(b["event_id"])
    if (not event or event.get("status") != "complete"
            or event.get("kind") != "professional.clinic_cot_braced"
            or not hasattr(event.get("actor"), "get")
            or not hasattr(event.get("payload"), "get")
            or not hasattr(event.get("consequence"), "get")
            or event["actor"].get("account_id") != b["account_id"]
            or event["actor"].get("mask_id") != b["mask_id"]
            or event["payload"].get("cot_id") != cot.id
            or event["payload"].get("professional_calling") != "smith"
            or event["payload"].get("forge_event_id") != b["forge_event_id"]
            or event["payload"].get("day") != b["day"]
            or event["payload"].get("hour") != b["hour"]
            or event["consequence"].get("cot_id") != cot.id
            or event["consequence"].get("consumed_item_id") != b["item_id"]
            or event["consequence"].get("forge_event_id") != b["forge_event_id"]
            or event["consequence"].get("workshop_id") != b["workshop_id"]
            or event["consequence"].get("condition") != "braced"):
        return None, "The cot fitting lacks an authentic completed Smith event."
    forge = get_event_ledger().get_event(b["forge_event_id"])
    if (not forge or forge.get("status") != "complete"
            or forge.get("kind") != "village.market_hinge_forged"
            or not hasattr(forge.get("consequence"), "get")
            or forge["consequence"].get("item_id") != b["item_id"]
            or forge["consequence"].get("source_room_id") != b["workshop_id"]):
        return None, "The consumed hinge has no authentic forging source."
    return b, None

def _assessment(cot, mask, day, hour):
    clinic = clinic_state.refresh(cot.location.db.village_clinic, day)
    row = clinic["assessment"]
    if (clinic["day"] != day or not row
            or row["account_id"] != mask.account.id
            or row["mask_id"] != mask.id
            or (row["day"], row["hour"]) > (day, hour)):
        return None, "This Healer must assess today's actual patient first."
    event = get_event_ledger().get_event(row["event_id"])
    if (not event or event.get("status") != "complete"
            or event.get("kind") != "village.clinic_assess"
            or not hasattr(event.get("actor"), "get")
            or not hasattr(event.get("payload"), "get")
            or not hasattr(event.get("consequence"), "get")
            or event["actor"].get("account_id") != mask.account.id
            or event["actor"].get("mask_id") != mask.id
            or event["payload"].get("day") != day
            or event["payload"].get("professional_calling") != "healer"
            or event["consequence"].get("room_id") != cot.location.id
            or event["consequence"].get("patient_condition") != clinic["condition"]):
        return None, "The patient's assessment lacks an authentic Healer event."
    return row, None

def certify(mask):
    cot, error = _guard(mask, "healer")
    if error:
        return None, error
    day, hour = clinic_work._clock()
    brace_row, error = _verified_brace(cot)
    if error:
        return None, error
    assessment, error = _assessment(cot, mask, day, hour)
    if error:
        return None, error
    props = dict(day=day, hour=hour, account_id=mask.account.id,
                 mask_id=mask.id, mask=mask.key, cot_id=cot.id,
                 assessment_event_id=assessment["event_id"])
    _preview, okay, reason = rules.certify(
        cot.db.clinic_equipment, event_id=1, **props)
    if not okay:
        return None, reason

    def consequence(event):
        with transaction.atomic():
            if (clinic_work._clock() != (day, hour)
                    or mask.location != cot.location
                    or active_calling(mask) != "healer"):
                raise RuntimeError("Healer, cot or village shift changed.")
            latest, why = _verified_brace(cot)
            current, assessment_error = _assessment(cot, mask, day, hour)
            if why or assessment_error or latest != brace_row or current != assessment:
                raise RuntimeError(why or assessment_error or "Signed source changed.")
            changed, valid, why = rules.certify(
                cot.db.clinic_equipment, event_id=event["id"], **props)
            if not valid:
                raise RuntimeError(why)
            cot.db.clinic_equipment = changed
            return {"cot_id": cot.id, "brace_event_id": brace_row["event_id"],
                    "assessment_event_id": assessment["event_id"],
                    "condition": "certified"}

    event = publish_world_event(
        "professional.clinic_cot_certified", actor=mask,
        payload={"day": day, "hour": hour, "cot_id": cot.id,
                 "brace_event_id": brace_row["event_id"],
                 "assessment_event_id": assessment["event_id"],
                 "professional_calling": "healer",
                 "harbinger": False, "chronicle_eligible": False},
        consequence=consequence,
    )
    record_participation(mask, "clinic_cot_certifications", calling="healer")
    return {"event_id": event["id"], "brace_event_id": brace_row["event_id"]}, None

def _verified_current_patient(cot, day, hour):
    """Authenticate the current visitor's assessment against the world ledger.

    The treating Healer may differ from the examiner, but an Attribute alone
    cannot invent an assessment. A prior day's patient cannot be reused.
    """
    clinic = clinic_state.refresh(cot.location.db.village_clinic, day)
    row = clinic["assessment"]
    if (clinic["day"] != day or not row or row["day"] != day
            or (row["day"], row["hour"]) > (day, hour)):
        return None, "A Healer must examine the actual patient first."
    event = get_event_ledger().get_event(row["event_id"])
    if (not event or event.get("status") != "complete"
            or event.get("kind") != "village.clinic_assess"
            or not hasattr(event.get("actor"), "get")
            or not hasattr(event.get("payload"), "get")
            or not hasattr(event.get("consequence"), "get")
            or event["actor"].get("account_id") != row["account_id"]
            or event["actor"].get("mask_id") != row["mask_id"]
            or event["payload"].get("day") != row["day"]
            or event["payload"].get("hour") != row["hour"]
            or event["payload"].get("professional_calling") != "healer"
            or event["consequence"].get("room_id") != cot.location.id
            or event["consequence"].get("patient_condition") != clinic["condition"]):
        return None, "The current patient's assessment lacks a signed Healer event."
    return row, None


def supported_rest_ready(mask):
    cot, error = _guard(mask, "healer")
    if error:
        return False, error
    state = rules.normalize(cot.db.clinic_equipment)
    if state["condition"] != "certified":
        return False, "Reinforced rest requires an independently certified cot."
    brace_row, error = _verified_brace(cot)
    if error:
        return False, error
    c = state["certification"]
    day, hour = clinic_work._clock()
    if (day, hour) < (brace_row["day"], brace_row["hour"]) or (
            day, hour) < (c["day"], c["hour"]):
        return False, "The cot's signed installation and approval are still in the future."
    assessment, error = _verified_current_patient(cot, day, hour)
    if error:
        return False, error
    event = get_event_ledger().get_event(c["event_id"])
    if (not event or event.get("kind") != "professional.clinic_cot_certified"
            or event.get("status") != "complete"
            or not hasattr(event.get("actor"), "get")
            or not hasattr(event.get("payload"), "get")
            or not hasattr(event.get("consequence"), "get")
            or event["actor"].get("account_id") != c["account_id"]
            or event["actor"].get("mask_id") != c["mask_id"]
            or event["payload"].get("cot_id") != cot.id
            or event["payload"].get("day") != c["day"]
            or event["payload"].get("hour") != c["hour"]
            or event["payload"].get("professional_calling") != "healer"
            or event["payload"].get("brace_event_id") != brace_row["event_id"]
            or event["payload"].get("assessment_event_id") != c["assessment_event_id"]
            or event["consequence"].get("cot_id") != cot.id
            or event["consequence"].get("brace_event_id") != brace_row["event_id"]
            or event["consequence"].get("assessment_event_id") != c["assessment_event_id"]
            or event["consequence"].get("condition") != "certified"):
        return False, "The clinical approval lacks a completed signed event."
    return True, None
