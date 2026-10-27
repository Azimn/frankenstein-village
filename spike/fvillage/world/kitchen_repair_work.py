"""GDD-EDGE-02: actual Innkeep restriction and independent Smith pot repair.

Reuses the original Tavern pot, the Workshop's finite forged hinge, the
canonical event ledger and existing Calling participation. No second ledger.
"""
from __future__ import annotations

from django.db import transaction
from evennia.utils import search

from world import kitchen_repair_edge02 as rules
from world.callings import active_calling, record_participation
from world.events import get_event_ledger, publish_world_event
from world import soup_kitchen, workshop_work

POT_KEY = "a communal soup pot"


def _pot():
    tavern = soup_kitchen._room(soup_kitchen.TAVERN)
    if tavern is None:
        return None
    matches = [obj for obj in search.search_object(POT_KEY)
               if obj.key == POT_KEY and obj.location == tavern]
    return matches[0] if len(matches) == 1 else None


def _access(mask, calling):
    tavern, error = soup_kitchen._access(mask, soup_kitchen.TAVERN)
    if error:
        return None, None, error
    if active_calling(mask) != calling:
        return None, None, "An active " + calling.title() + " Calling is required."
    pot = _pot()
    if pot is None:
        return None, None, "The original communal soup pot is missing."
    return tavern, pot, None


def status():
    pot = _pot()
    return rules.public_lines(pot.db.kitchen_repair if pot else {"condition": "invalid"})


def restrict(mask):
    tavern, pot, error = _access(mask, "innkeep")
    if error:
        return None, error
    day, hour = soup_kitchen._clock()
    preview, okay, reason = rules.restrict(
        pot.db.kitchen_repair, day=day, hour=hour,
        account_id=mask.account.id, mask_id=mask.id, mask=mask.key,
        pot_id=pot.id, event_id=1)
    if not okay:
        return None, reason

    def consequence(event):
        with transaction.atomic():
            if (soup_kitchen._clock() != (day, hour)
                    or mask.location != tavern
                    or active_calling(mask) != "innkeep"):
                raise RuntimeError("The Innkeep or work shift changed.")
            changed, valid, reason = rules.restrict(
                pot.db.kitchen_repair, day=day, hour=hour,
                account_id=mask.account.id, mask_id=mask.id, mask=mask.key,
                pot_id=pot.id, event_id=event["id"])
            if not valid:
                raise RuntimeError(reason)
            pot.db.kitchen_repair = changed
            return {"pot_id": pot.id, "condition": "restricted",
                    "innkeep_account_id": mask.account.id}

    event = publish_world_event(
        "professional.innkeep_kitchen_restriction", actor=mask,
        payload={"day": day, "hour": hour, "pot_id": pot.id,
                 "professional_calling": "innkeep",
                 "harbinger": False, "chronicle_eligible": False},
        consequence=consequence)
    record_participation(mask, "kitchen_restrictions", calling="innkeep")
    return {"event_id": event["id"]}, None


def _sources(pot, item, smith):
    state = rules.normalize(pot.db.kitchen_repair)
    if state["condition"] != "restricted":
        return None, None, "No authentic outstanding kitchen restriction exists."
    restriction = state["restriction"]
    ledger = get_event_ledger()
    inn_event = ledger.get_event(restriction["event_id"])
    if (not inn_event or inn_event.get("status") != "complete"
            or inn_event.get("kind") != "professional.innkeep_kitchen_restriction"
            or not hasattr(inn_event.get("actor"), "get")
            or inn_event["actor"].get("account_id") != restriction["account_id"]
            or inn_event["actor"].get("mask_id") != restriction["mask_id"]
            or not hasattr(inn_event.get("payload"), "get")
            or inn_event["payload"].get("pot_id") != pot.id
            or inn_event["payload"].get("professional_calling") != "innkeep"
            or inn_event["payload"].get("day") != restriction["day"]
            or inn_event["payload"].get("hour") != restriction["hour"]
            or not hasattr(inn_event.get("consequence"), "get")
            or inn_event["consequence"].get("pot_id") != pot.id
            or inn_event["consequence"].get("condition") != "restricted"
            or inn_event["consequence"].get("innkeep_account_id")
            != restriction["account_id"]):
        return None, None, "The Innkeep restriction lacks a completed signed source."
    if restriction["account_id"] == smith.account.id:
        return None, None, "The Innkeep and Smith must use separate accounts."
    source = item.db.forged_market_part
    if not hasattr(source, "get"):
        return None, None, "The physical hinge lacks Workshop provenance."
    source = dict(source)
    workshop = workshop_work._room(workshop_work.WORKSHOP)
    if workshop is None:
        return None, None, "The original Workshop is unavailable."
    forge_id = source.get("source_event_id")
    if type(forge_id) is not int or forge_id <= 0:
        return None, None, "The hinge lacks a valid source event ID."
    forge = ledger.get_event(forge_id)
    if (not forge or forge.get("status") != "complete"
            or forge.get("kind") != "village.market_hinge_forged"
            or not hasattr(forge.get("actor"), "get")
            or forge["actor"].get("account_id") != source.get("smith_account_id")
            or not hasattr(forge.get("payload"), "get")
            or forge["payload"].get("room_id") != workshop.id
            or forge["payload"].get("day") != source.get("issued_day")
            or not hasattr(forge.get("consequence"), "get")
            or forge["consequence"].get("item_id") != item.id
            or forge["consequence"].get("source_room_id") != workshop.id
            or source.get("source_room_id") != workshop.id):
        return None, None, "The hinge has no completed matching forge event."
    day, hour = soup_kitchen._clock()
    if (source["issued_day"] > day
            or (day, hour) < (restriction["day"], restriction["hour"])):
        return None, None, "The source or repair lies in a future village shift."
    return restriction, forge_id, None


def repair(mask):
    tavern, pot, error = _access(mask, "smith")
    if error:
        return None, error
    items = [obj for obj in mask.contents
             if obj.key == workshop_work.FITTING
             and hasattr(obj.db.forged_market_part, "get")]
    if len(items) != 1:
        return None, "Carry one real forged iron hinge from the Market Workshop."
    item = items[0]
    restriction, forge_id, error = _sources(pot, item, mask)
    if error:
        return None, error
    day, hour = soup_kitchen._clock()
    preview, okay, reason = rules.repair(
        pot.db.kitchen_repair, day=day, hour=hour,
        account_id=mask.account.id, mask_id=mask.id, mask=mask.key,
        pot_id=pot.id, event_id=1, item_id=item.id,
        forge_event_id=forge_id, restriction_event_id=restriction["event_id"])
    if not okay:
        return None, reason

    def consequence(event):
        with transaction.atomic():
            if (soup_kitchen._clock() != (day, hour)
                    or mask.location != tavern
                    or active_calling(mask) != "smith"
                    or item.location != mask):
                raise RuntimeError("The Smith, fitting or work shift moved.")
            current, signed_forge, why = _sources(pot, item, mask)
            if why or signed_forge != forge_id or current != restriction:
                raise RuntimeError(why or "The signed sources changed.")
            changed, valid, why = rules.repair(
                pot.db.kitchen_repair, day=day, hour=hour,
                account_id=mask.account.id, mask_id=mask.id, mask=mask.key,
                pot_id=pot.id, event_id=event["id"], item_id=item.id,
                forge_event_id=forge_id,
                restriction_event_id=restriction["event_id"])
            if not valid:
                raise RuntimeError(why)
            used_item_id = item.id
            pot.db.kitchen_repair = changed
            item.delete()
            return {"pot_id": pot.id, "condition": "working",
                    "consumed_item_id": used_item_id,
                    "forge_event_id": forge_id,
                    "restriction_event_id": restriction["event_id"]}

    event = publish_world_event(
        "professional.smith_kitchen_repair", actor=mask,
        payload={"day": day, "hour": hour, "pot_id": pot.id,
                 "forge_event_id": forge_id,
                 "restriction_event_id": restriction["event_id"],
                 "professional_calling": "smith",
                 "harbinger": False, "chronicle_eligible": False},
        consequence=consequence)
    record_participation(mask, "kitchen_repairs", calling="smith")
    return {"event_id": event["id"], "forge_event_id": forge_id}, None
