"""Physical St. Lazarus clinic and signed treatment of a present patient.

A cot fixture represents an actual visitor in the current village day.
Daily recurring clinical requests use the canonical clock, real linen
objects, the world event ledger, and existing player Calling membership.
"""
from __future__ import annotations

from django.db import transaction
from evennia import create_object
from evennia.scripts.models import ScriptDB
from evennia.utils import search

from world import clinic_state, clinic_supply
from world.callings import active_calling, record_participation
from world.events import get_event_ledger, publish_world_event

CHURCH = "St. Lazarus Church"
COT = "a clinic treatment cot"
COMPRESS = "a fresh linen compress"
MARKET = "Market Lane"
PARCEL = "a sealed clinic linen parcel"


def _room():
    return next((o for o in search.search_object(CHURCH)
                 if o.key == CHURCH and o.location is None
                 and o.tags.has("ic", category="side")), None)


def _clock():
    try:
        c = ScriptDB.objects.get(db_key="village_time")
        return int(c.db.day or 1), int(c.db.hour if c.db.hour is not None else 21)
    except ScriptDB.DoesNotExist:
        return 1, 21


def _guard(mask):
    room = _room()
    if not getattr(mask, "account", None):
        return room, "An ordinary logged-in character must be present."
    if room is None or mask.location != room:
        return room, "Clinical work takes place at St. Lazarus Church."
    if not any(o.key == COT and o.location == room for o in room.contents):
        return room, "The treatment cot has not been furnished."
    return room, None


def status(mask=None):
    room = _room()
    if room is None:
        return "St. Lazarus village clinic is not constructed."
    if mask is not None:
        _, error = _guard(mask)
        if error:
            return error
    day, _ = _clock()
    lines = clinic_state.public_lines(room.db.village_clinic, day)
    cot = next((o for o in room.contents if o.key == COT), None)
    if cot:
        from world.clinic_comfort_edge27 import public_lines
        ledger = None
        treatment = None
        source = None
        try:
            ledger = get_event_ledger()
            treatment = clinic_state.refresh(room.db.village_clinic, day).get("treatment")
            if treatment:
                source = ledger.get_event(treatment["event_id"])
        except Exception:
            # A missing ledger is not permission to advertise signed consent.
            ledger = None
        lines += "\n" + public_lines(
            cot.db.clinic_comfort, day,
            event_lookup=ledger.get_event if ledger is not None else None,
            treatment=treatment, treatment_event=source,
            room_id=room.id, cot_id=cot.id,
        )
    return lines


def confidential_records(mask):
    """Restrict personal case data to this patient's consenting examiner."""
    room, error = _guard(mask)
    if error:
        return error
    if active_calling(mask) != "healer":
        return "Private clinical notes require an attending Healer and patient permission."
    day, _hour = _clock()
    return clinic_state.private_lines(
        room.db.village_clinic, day,
        account_id=mask.account.id, mask_id=mask.id,
    )


def _compresses(mask, day):
    return [
        o for o in mask.contents
        if o.key == COMPRESS and hasattr(o.db.clinic_compress, "get")
        and int(o.db.clinic_compress.get("day") or 0) <= day
        and day - int(o.db.clinic_compress.get("day") or 0) <= 2
    ]


def act(mask, action, method=None):
    room, error = _guard(mask)
    if error:
        return None, error
    if active_calling(mask) != "healer":
        return None, "An active Healer must undertake clinical work."
    if action not in {"assess", "prepare", "treat", "request_records"}:
        return None, "Use clinic | clinic assess | clinic prepare | clinic treat rest|compress | clinic request records."
    if action == "treat" and method not in clinic_state.METHODS:
        return None, "Choose clinic treat rest or clinic treat compress."
    if action != "treat" and method is not None:
        return None, "Only the treatment command takes a method."
    day, hour = _clock()
    props = {
        "day": day, "hour": hour, "account_id": mask.account.id,
        "mask_id": mask.id, "mask": mask.key,
    }
    linen = _compresses(mask, day) if action == "treat" and method == "compress" else []
    if action == "treat" and method == "compress" and not linen:
        return None, "Carry a real fresh linen compress, prepared at this clinic."
    transform = (clinic_state.grant_records_permission if action == "request_records"
                 else getattr(clinic_state, action))
    if action == "prepare":
        preview, valid, reason = transform(room.db.village_clinic, day=day)
    else:
        extra = {"method": method} if action == "treat" else {}
        preview, valid, reason = transform(
            room.db.village_clinic, event_id=1, **props, **extra)
    if not valid:
        return None, reason

    def consequence(event):
        with transaction.atomic():
            now = _clock()
            if now != (day, hour) or mask.location != room:
                raise RuntimeError("The patient, hour or treatment room changed.")
            if active_calling(mask) != "healer":
                raise RuntimeError("The acting Healer changed Calling.")
            if action == "prepare":
                changed, good, problem = clinic_state.prepare(
                    room.db.village_clinic, day=day)
                if not good:
                    raise RuntimeError(problem)
                compress = create_object(
                    "typeclasses.objects.Object", key=COMPRESS,
                    location=mask, aliases=["linen compress", "compress"],
                )
                compress.db.clinic_compress = {
                    "day": day, "source_event_id": event["id"],
                    "source_room_id": room.id,
                }
                compress.db.desc = (
                    "A physically prepared clean linen dressing from "
                    "the St. Lazarus shared clinic cabinet. Usable within "
                    "two village days by a Healer at that clinic."
                )
                room.db.village_clinic = changed
                return {"compress_item_id": compress.id, "remaining_linen": changed["linen"]}
            extra = {"method": method} if action == "treat" else {}
            if action == "treat" and method == "compress":
                if not linen or linen[0].location != mask:
                    raise RuntimeError("The real linen dressing is no longer carried.")
            changed, good, problem = transform(
                room.db.village_clinic, event_id=event["id"], **props, **extra)
            if not good:
                raise RuntimeError(problem)
            room.db.village_clinic = changed
            if action == "request_records":
                return {
                    "room_id": room.id,
                    "examiner_mask_id": mask.id,
                    "records_permission_event_id": event["id"],
                }
            used_id = None
            source_id = None
            if action == "treat" and method == "compress":
                dressing = linen[0]
                used_id = dressing.id
                source_id = dressing.db.clinic_compress.get("source_event_id")
                dressing.delete()
            return {"patient_condition": changed["condition"],
                    "method": method, "used_item_id": used_id,
                    "source_event_id": source_id,
                    "improvement": changed["treatment"]["improvement"]
                    if changed["treatment"] else None,
                    "assessment_event_id": changed["assessment"]["event_id"]
                    if changed["assessment"] else None,
                    "room_id": room.id}

    event = publish_world_event(
        "village.clinic_" + (
            "records_permission" if action == "request_records" else action
        ), actor=mask,
        payload={"day": day, "hour": hour, "method": method,
                 "professional_calling": "healer",
                 "harbinger": False, "chronicle_eligible": False},
        consequence=consequence,
    )
    if action != "request_records":
        record_participation(mask, "clinic_" + action, calling="healer")
    return {
        "event_id": event["id"], "action": action, "method": method,
        "condition": None if action == "request_records" else preview["condition"],
    }, None


def procure(mask):
    """Merchant withdraws one real sealed linen parcel from Market Lane."""
    market = next((o for o in search.search_object(MARKET)
                   if o.key == MARKET and o.location is None
                   and o.tags.has("ic", category="side")), None)
    if (not getattr(mask, "account", None) or market is None
            or mask.location != market):
        return None, "A Merchant must be present at Market Lane to procure clinic linen."
    if active_calling(mask) != "merchant":
        return None, "Only an active Merchant may procure clinic linen."
    if any(o.key == PARCEL and o.db.clinic_supply_parcel for o in mask.contents):
        return None, "You already carry a sealed clinic linen parcel."
    day, hour = _clock()
    _preview, okay, reason = clinic_supply.issue(market.db.clinic_linen_stock, day)
    if not okay:
        return None, reason

    def consequence(event):
        with transaction.atomic():
            if (_clock() != (day, hour) or mask.location != market
                    or active_calling(mask) != "merchant"):
                raise RuntimeError("The Merchant left or the market shift changed.")
            if any(o.key == PARCEL and o.db.clinic_supply_parcel for o in mask.contents):
                raise RuntimeError("A clinic parcel is already carried.")
            changed, good, problem = clinic_supply.issue(
                market.db.clinic_linen_stock, day)
            if not good:
                raise RuntimeError(problem)
            parcel = create_object(
                "typeclasses.objects.Object", key=PARCEL, location=mask,
                aliases=["clinic linen parcel", "linen parcel", "sealed linen"],
            )
            parcel.db.clinic_supply_parcel = {
                "day": day, "hour": hour, "source_event_id": event["id"],
                "market_room_id": market.id,
                "merchant_account_id": mask.account.id,
                "merchant_mask_id": mask.id,
                "units": clinic_supply.UNITS, "material": "clean_linen",
            }
            parcel.db.desc = (
                "Two clean linen dressings, sealed at Market Lane. Carry or "
                "give this physical parcel to St. Lazarus Church, then have "
                "a separate Healer inspect and accept it with clinic receive."
            )
            market.db.clinic_linen_stock = changed
            return {
                "parcel_id": parcel.id, "market_room_id": market.id,
                "units": clinic_supply.UNITS,
                "remaining": changed["remaining"],
            }

    event = publish_world_event(
        "professional.merchant_clinic_supply", actor=mask,
        payload={
            "day": day, "hour": hour, "market_room_id": market.id,
            "professional_calling": "merchant",
            "harbinger": False, "chronicle_eligible": False,
        },
        consequence=consequence,
    )
    record_participation(mask, "clinic_supplies_procured", calling="merchant")
    return {"event_id": event["id"]}, None


def receive(mask):
    """Healer accepts real signed linen without accessing private case notes."""
    church, error = _guard(mask)
    if error:
        return None, error
    if active_calling(mask) != "healer":
        return None, "Only an active Healer can accept clinic supplies."
    market = next((o for o in search.search_object(MARKET)
                   if o.key == MARKET and o.location is None
                   and o.tags.has("ic", category="side")), None)
    if market is None:
        return None, "Market Lane is not available."
    parcels = [
        o for o in list(church.contents) + list(mask.contents)
        if o.key == PARCEL and hasattr(o.db.clinic_supply_parcel, "get")
    ]
    if not parcels:
        return None, "Bring a physical sealed clinic linen parcel from Market Lane."
    if len(parcels) != 1:
        return None, "Choose a single clinic linen parcel before accepting supplies."
    item = parcels[0]
    source = dict(item.db.clinic_supply_parcel)
    day, hour = _clock()
    receipt = get_event_ledger().get_event(source.get("source_event_id"))
    valid, problem = clinic_supply.verify_source(
        receipt, source, item_id=item.id, market_id=market.id,
        healer_account_id=mask.account.id, day=day,
    )
    if not valid:
        return None, problem
    props = {
        "day": day, "event_id": 1,
        "source_event_id": source["source_event_id"],
        "source_day": source["day"], "parcel_id": item.id,
        "merchant_account_id": source["merchant_account_id"],
        "healer_account_id": mask.account.id,
    }
    _preview, okay, reason = clinic_supply.accept(church.db.village_clinic, **props)
    if not okay:
        return None, reason

    def consequence(event):
        with transaction.atomic():
            if (_clock() != (day, hour) or mask.location != church
                    or active_calling(mask) != "healer"
                    or item.location not in (church, mask)):
                raise RuntimeError("The clinical handoff or shift changed.")
            current = dict(item.db.clinic_supply_parcel or {})
            signed = get_event_ledger().get_event(current.get("source_event_id"))
            valid, problem = clinic_supply.verify_source(
                signed, current, item_id=item.id, market_id=market.id,
                healer_account_id=mask.account.id, day=day,
            )
            if not valid or current != source:
                raise RuntimeError(problem or "The parcel provenance changed.")
            changed, good, reason = clinic_supply.accept(
                church.db.village_clinic, **{**props, "event_id": event["id"]})
            if not good:
                raise RuntimeError(reason)
            church.db.village_clinic = changed
            consumed_id = item.id
            item.delete()
            return {
                "consumed_parcel_id": consumed_id,
                "source_merchant_event_id": source["source_event_id"],
                "merchant_account_id": source["merchant_account_id"],
                "clinic_room_id": church.id,
                "linen_after": changed["linen"],
            }

    event = publish_world_event(
        "village.clinic_supply_received", actor=mask,
        payload={
            "day": day, "hour": hour,
            "source_merchant_event_id": source["source_event_id"],
            "parcel_id": item.id, "professional_calling": "healer",
            "harbinger": False, "chronicle_eligible": False,
        },
        consequence=consequence,
    )
    record_participation(mask, "clinic_supplies_received", calling="healer")
    return {"event_id": event["id"], "source_event_id": source["source_event_id"]}, None
