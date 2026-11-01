"""GDD-EDGE-02: actual Innkeep restriction and independent Smith pot repair.

Reuses the original Tavern pot, the Workshop's finite forged hinge, the
canonical event ledger and existing Calling participation. No second ledger.
"""
from __future__ import annotations

from collections.abc import Mapping, Sequence

from django.db import transaction
from evennia.scripts.models import ScriptDB
from evennia.utils import search

from world import kitchen_repair_edge02 as rules
from world.callings import active_calling, record_participation
from world.events import LEDGER_KEY, get_event_ledger, publish_world_event
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


def _prior_completed_pot_event(pot, kinds):
    """A mutable pot Attribute cannot erase signed physical work.

    Read existing canonical history without creating a new ledger. Corrupt
    history fails closed rather than permitting a second finite installation.
    """
    try:
        ledger = ScriptDB.objects.get(db_key=LEDGER_KEY)
    except ScriptDB.DoesNotExist:
        return False, None
    records = ledger.db.events
    if not isinstance(records, Sequence) or isinstance(records, (str, bytes)):
        return True, "The signed kitchen history is unavailable."
    for event in records:
        if not isinstance(event, Mapping):
            return True, "The signed kitchen history is malformed."
        if event.get("status") != "complete" or event.get("kind") not in kinds:
            continue
        payload = event.get("payload")
        if not isinstance(payload, Mapping):
            return True, "A completed kitchen event has no readable source."
        if payload.get("pot_id") == pot.id:
            return True, "This pot already has completed signed kitchen work."
    return False, None


def _rollback_blocker(pot):
    state = rules.normalize(pot.db.kitchen_repair)
    if state["condition"] == "loose":
        return _prior_completed_pot_event(
            pot, ("professional.innkeep_kitchen_restriction",
                  "professional.smith_kitchen_repair"))
    if state["condition"] == "restricted":
        return _prior_completed_pot_event(
            pot, ("professional.smith_kitchen_repair",))
    return False, None



def player_simmer_allowed(pot):
    """Use original signed physical history, not just the mutable pot Attribute.

    A legitimate never-restricted loose pot is usable. Once an Innkeep has
    signed a restriction, only a matching completed Smith repair can reopen
    player cooking. A rolled-back or forged 'working' Attribute cannot do so.
    This is read-only: never create a new ledger merely to inspect service.
    """
    if pot is None:
        return False
    state = rules.normalize(pot.db.kitchen_repair)
    condition = state["condition"]
    if condition == "loose":
        prior, _ = _prior_completed_pot_event(
            pot, ("professional.innkeep_kitchen_restriction",
                  "professional.smith_kitchen_repair"))
        return not prior
    if condition != "working":
        return False

    restriction, repair = state["restriction"], state["repair"]
    try:
        ledger = ScriptDB.objects.get(db_key=LEDGER_KEY)
        inn = ledger.get_event(restriction["event_id"])
        smith = ledger.get_event(repair["event_id"])
        forge = ledger.get_event(repair["forge_event_id"])
    except Exception:
        return False
    if not all(isinstance(event, Mapping) for event in (inn, smith, forge)):
        return False
    if any(event.get("status") != "complete" for event in (inn, smith, forge)):
        return False
    if (inn.get("kind") != "professional.innkeep_kitchen_restriction"
            or smith.get("kind") != "professional.smith_kitchen_repair"
            or forge.get("kind") != "village.market_hinge_forged"):
        return False
    for event, worker in ((inn, restriction), (smith, repair)):
        actor, payload, consequence = (
            event.get("actor"), event.get("payload"), event.get("consequence"))
        if not all(isinstance(part, Mapping)
                   for part in (actor, payload, consequence)):
            return False
        if (actor.get("account_id") != worker["account_id"]
                or actor.get("mask_id") != worker["mask_id"]
                or payload.get("pot_id") != pot.id
                or payload.get("day") != worker["day"]
                or payload.get("hour") != worker["hour"]
                or consequence.get("pot_id") != pot.id):
            return False
    if (inn["payload"].get("professional_calling") != "innkeep"
            or inn["consequence"].get("condition") != "restricted"
            or inn["consequence"].get("innkeep_account_id")
            != restriction["account_id"]
            or smith["payload"].get("professional_calling") != "smith"
            or smith["payload"].get("restriction_event_id")
            != restriction["event_id"]
            or smith["payload"].get("forge_event_id") != repair["forge_event_id"]
            or smith["consequence"].get("condition") != "working"
            or smith["consequence"].get("restriction_event_id")
            != restriction["event_id"]
            or smith["consequence"].get("forge_event_id")
            != repair["forge_event_id"]
            or smith["consequence"].get("consumed_item_id") != repair["item_id"]
            or not isinstance(forge.get("consequence"), Mapping)
            or forge["consequence"].get("item_id") != repair["item_id"]
            or inn["id"] >= smith["id"]
            or forge["id"] >= smith["id"]):
        return False
    return True


def status():
    pot = _pot()
    if pot is None:
        return rules.public_lines({"condition": "invalid"})
    prior, _reason = _rollback_blocker(pot)
    if prior:
        return "The pot's repair record conflicts with signed physical history; service is unavailable."
    return rules.public_lines(pot.db.kitchen_repair)


def restrict(mask):
    tavern, pot, error = _access(mask, "innkeep")
    if error:
        return None, error
    prior, reason = _prior_completed_pot_event(
        pot, ("professional.innkeep_kitchen_restriction",
              "professional.smith_kitchen_repair"))
    if prior:
        return None, reason
    day, hour = soup_kitchen._clock()
    preview, okay, reason = rules.restrict(
        pot.db.kitchen_repair, day=day, hour=hour,
        account_id=mask.account.id, mask_id=mask.id, mask=mask.key,
        pot_id=pot.id, event_id=1)
    if not okay:
        return None, reason

    def consequence(event):
        with transaction.atomic():
            prior, reason = _prior_completed_pot_event(
                pot, ("professional.innkeep_kitchen_restriction",
                      "professional.smith_kitchen_repair"))
            if prior:
                raise RuntimeError(reason)
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
    prior, reason = _prior_completed_pot_event(
        pot, ("professional.smith_kitchen_repair",))
    if prior:
        return None, reason
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
            prior, reason = _prior_completed_pot_event(
                pot, ("professional.smith_kitchen_repair",))
            if prior:
                raise RuntimeError(reason)
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
