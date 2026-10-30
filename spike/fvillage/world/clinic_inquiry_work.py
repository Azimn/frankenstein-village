"""EDGE-28 Evennia adapter: original St. Lazarus cot and signed Healer source."""
from __future__ import annotations

from django.db import transaction
from evennia.utils import search

from world import clinic_inquiry_state, clinic_state, clinic_work
from world.callings import active_calling, record_participation
from world.events import get_event_ledger, publish_world_event
from world.object_properties import is_hidden_mechanical_property, mechanical_value


def _cot(room):
    found = [o for o in room.contents
             if o.key == clinic_work.COT
             and o.is_typeclass("typeclasses.objects.ClinicCot", exact=True)]
    return found[0] if len(found) == 1 else None


def _seen(mask, cot, day):
    observation = getattr(mask.db, "clinic_cot_seen", None)
    return (hasattr(observation, "get")
            and observation.get("cot_id") == cot.id
            and observation.get("room_id") == cot.location.id
            and observation.get("day") == day)


def _canonical_well():
    """Resolve the original physical Village Square well, not a name match."""
    wells = [o for o in search.search_object("village well")
             if o.key == "well"
             and o.is_typeclass("typeclasses.objects.VillageWell", exact=True)
             and getattr(o.location, "key", None) == "Village Square"]
    return wells[0] if len(wells) == 1 else None


def _case_item(mask, room):
    """Require the actual well-grown object and its real hidden toxin value.

    The persistent well ID is stamped only by ensure_well_mushrooms.
    Carrying the specimen preserves its origin across rooms and restarts.
    """
    well = _canonical_well()
    if well is None:
        return None
    candidates = [o for o in list(room.contents) + list(mask.contents)
                  if o.key == clinic_inquiry_state.CASE_ITEM_KEY
                  and o.location in (room, mask)
                  and o.is_typeclass("typeclasses.objects.Object", exact=True)
                  and is_hidden_mechanical_property(o, "toxin")
                  and clinic_inquiry_state.well_case_source_valid(
                      getattr(o.db, "well_mushroom_source_id", None),
                      well.id, mechanical_value(o, "toxin", None))]
    specimen = clinic_inquiry_state.choose_case_item(candidates, mask)
    return (specimen, well) if specimen is not None else None


def investigate(mask, interpretation="unrelated_illness"):
    room, error = clinic_work._guard(mask)
    if error:
        return None, error
    if active_calling(mask) != "detective":
        return None, "Only an active Detective can investigate the clinic timeline."
    cot = _cot(room)
    if cot is None:
        return None, "The original physical clinic cot is missing."
    day, hour = clinic_work._clock()
    if clinic_inquiry_state.stamp(day, hour) is None:
        return None, "The village clock is invalid."
    if not _seen(mask, cot, day):
        return None, "Look at the original clinic cot before investigating."
    if interpretation not in clinic_inquiry_state.INTERPRETATIONS:
        return None, "Choose clinic investigate illness or clinic investigate exposure."
    case_item = _case_item(mask, room)
    if case_item is None:
        return None, ("Bring a real cluster of mushrooms from the village well "
                      "to the original clinic cot as a physical case item.")
    specimen, well = case_item
    toxin_value = mechanical_value(specimen, "toxin", None)
    clinic = clinic_state.refresh(room.db.village_clinic, day)
    if clinic["day"] != day or not clinic["assessment"]:
        return None, "A Healer must sign today's actual patient assessment first."
    source = clinic["assessment"]
    ledger = get_event_ledger()
    event_source = ledger.get_event(source["event_id"])
    if not clinic_inquiry_state.source_valid(event_source, source, room.id):
        return None, "The original Healer assessment cannot be verified in the ledger."
    common = dict(
        day=day, hour=hour, account_id=mask.account.id, mask_id=mask.id,
        mask=mask.key, source_event_id=source["event_id"],
        source_account_id=source["account_id"],
        source_mask_id=source["mask_id"],
        source_day=source["day"], source_hour=source["hour"],
        cot_id=cot.id, room_id=room.id, case_item_id=specimen.id,
        case_well_id=well.id, interpretation=interpretation,
    )
    # No event exists at preflight time. The real ledger ID is checked
    # separately inside the atomic consequence before signing the cot.
    _preview, valid, reason = clinic_inquiry_state.investigate(
        cot.db.clinic_inquiry, event_id=None, preview=True, **common)
    if not valid:
        return None, reason

    def consequence(event):
        with transaction.atomic():
            if (clinic_work._clock() != (day, hour)
                    or mask.location != room or cot.location != room
                    or active_calling(mask) != "detective"
                    or not _seen(mask, cot, day)
                    or mask.account.id != common["account_id"]
                    or _case_item(mask, room) != (specimen, well)
                    or mechanical_value(specimen, "toxin", None) != toxin_value):
                raise RuntimeError("The Detective, physical cot or village hour changed.")
            current = clinic_state.refresh(room.db.village_clinic, day)
            if (current["day"] != day or current["assessment"] != source
                    or not clinic_inquiry_state.source_valid(
                        ledger.get_event(source["event_id"]), source, room.id)):
                raise RuntimeError("The original clinical source no longer verifies.")
            changed, okay, problem = clinic_inquiry_state.investigate(
                cot.db.clinic_inquiry, event_id=event["id"], **common)
            if not okay:
                raise RuntimeError(problem)
            cot.db.clinic_inquiry = changed
            return {
                "cot_id": cot.id, "room_id": room.id,
                "source_healer_event_id": source["event_id"],
                "case_item_id": specimen.id,
                "case_well_id": well.id, "case_item_toxin": toxin_value,
                "interpretation": interpretation,
                "alternative": clinic_inquiry_state.alternative(interpretation),
                "causal_status": "unproven",
                "finding": "contested_clinic_cause",
                "day": day, "hour": hour,
            }

    event = publish_world_event(
        "village.clinic_inquiry", actor=mask,
        payload={
            "day": day, "hour": hour, "professional_calling": "detective",
            "cot_id": cot.id, "room_id": room.id,
            "case_item_id": specimen.id,
            "case_item_key": clinic_inquiry_state.CASE_ITEM_KEY,
            "case_well_id": well.id, "case_item_toxin": toxin_value,
            "interpretation": interpretation,
            "alternative": clinic_inquiry_state.alternative(interpretation),
            "source_healer_event_id": source["event_id"],
            "source_healer_account_id": source["account_id"],
            "harbinger": False, "chronicle_eligible": False,
        },
        consequence=consequence,
    )
    record_participation(mask, "clinic_inquiry", calling="detective")
    return {"event_id": event["id"], "case_item_id": specimen.id,
            "interpretation": interpretation,
            "alternative": clinic_inquiry_state.alternative(interpretation),
            "source_event_id": source["event_id"]}, None
