"""Real Smith work between the Market Workshop and Market Lane.

All public effects come from actual source objects, finite stock and the
canonical event ledger. Workshop implements an optional handoff: the Smith
can install a fitting alone, or physically give it to another character.
"""
from __future__ import annotations

from django.db import transaction
from evennia import create_object
from evennia.scripts.models import ScriptDB
from evennia.utils import search

from world import workshop_state
from world.callings import active_calling, record_participation
from world.events import publish_world_event

WORKSHOP = "The Market Workshop"
MARKET = "Market Lane"
FITTING = "a forged market hinge"


def _room(key):
    return next((
        room for room in search.search_object(key)
        if room.key == key and room.location is None
        and room.tags.has("ic", category="side")
    ), None)


def _clock():
    try:
        script = ScriptDB.objects.get(db_key="village_time")
        return int(script.db.day or 1), int(
            script.db.hour if script.db.hour is not None else 21
        )
    except ScriptDB.DoesNotExist:
        return 1, 21


def status(mask):
    workplace = _room(WORKSHOP)
    market = _room(MARKET)
    if not getattr(mask, "account", None):
        return "Only ordinary logged-in characters can work on the market."
    if workplace is None or market is None:
        return "The Market Workshop has not yet been furnished."
    if mask.location not in (workplace, market):
        return "Visit Market Lane or its eastward Workshop to inspect repair work."
    day, _hour = _clock()
    return workshop_state.public_lines(workplace.db.repair_docket, day)


def forge(mask):
    workplace = _room(WORKSHOP)
    if (not getattr(mask, "account", None) or workplace is None
            or mask.location != workplace):
        return None, "A Smith must work at the real Market Workshop bench."
    if active_calling(mask) != "smith":
        return None, "Only an active Smith can forge new public market fittings."
    if any(obj.key == FITTING and obj.db.forged_market_part
           for obj in mask.contents):
        return None, "You already carry a forged market hinge. Deliver or give it."
    day, hour = _clock()
    _preview, okay, reason = workshop_state.forge(
        workplace.db.repair_docket, day=day, hour=hour,
        account_id=mask.account.id, mask_id=mask.id, mask=mask.key,
        event_id=1, item_id=1,
    )
    if not okay:
        return None, reason

    def consequence(event):
        with transaction.atomic():
            if _clock() != (day, hour) or mask.location != workplace:
                raise RuntimeError("Smith or work shift moved before forging.")
            if active_calling(mask) != "smith":
                raise RuntimeError("The Smith is no longer on the active Calling.")
            if any(obj.key == FITTING and obj.db.forged_market_part
                   for obj in mask.contents):
                raise RuntimeError("The Smith already carries a forged hinge.")
            item = create_object(
                "typeclasses.objects.Object",
                key=FITTING, location=mask,
                aliases=["market hinge", "forged hinge", "forged market hinge", "iron hinge"],
            )
            item.db.forged_market_part = {
                "source_event_id": event["id"],
                "issued_day": day,
                "source_room_id": workplace.id,
                "smith_account_id": mask.account.id,
            }
            item.db.desc = (
                "A real replacement iron hinge shaped at the public Market "
                "Workshop. It can be given to another traveler, carried west "
                "to Market Lane and installed with workshop install. "
                "It has not magically repaired anything while in your pack."
            )
            changed, accepted, reason = workshop_state.forge(
                workplace.db.repair_docket,
                day=day, hour=hour, account_id=mask.account.id,
                mask_id=mask.id, mask=mask.key,
                event_id=event["id"], item_id=item.id,
            )
            if not accepted:
                raise RuntimeError(reason)
            workplace.db.repair_docket = changed
            return {
                "source_room_id": workplace.id,
                "item_id": item.id,
                "offcuts_remaining": changed["offcuts"],
            }

    event = publish_world_event(
        "village.market_hinge_forged", actor=mask,
        payload={
            "day": day, "hour": hour, "room_id": workplace.id,
            "harbinger": False, "chronicle_eligible": False,
        },
        consequence=consequence,
    )
    record_participation(mask, "market_hinges_forged", calling="smith")
    result = workshop_state.refresh(workplace.db.repair_docket, day)
    return {"event_id": event["id"], "remaining": result["offcuts"]}, None


def install(mask):
    market = _room(MARKET)
    workplace = _room(WORKSHOP)
    if (not getattr(mask, "account", None) or market is None
            or workplace is None or mask.location != market):
        return None, "Carry a real forged hinge to Market Lane to install it."
    items = [
        obj for obj in mask.contents
        if obj.key == FITTING and hasattr(obj.db.forged_market_part, "get")
    ]
    if not items:
        return None, "Carry an actual forged market hinge from the Workshop."
    item = items[0]
    source = dict(item.db.forged_market_part)
    event_id = source.get("source_event_id")
    if (type(event_id) is not int or event_id <= 0
            or source.get("source_room_id") != workplace.id):
        return None, "The fitting lacks authentic Workshop event provenance."
    day, hour = _clock()
    if int(source.get("issued_day") or 0) > day:
        return None, "That fitting is dated in a future village day."
    _preview, okay, reason = workshop_state.install(
        workplace.db.repair_docket,
        day=day, hour=hour, account_id=mask.account.id,
        mask_id=mask.id, mask=mask.key,
        event_id=1, item_id=item.id, source_event_id=event_id,
    )
    if not okay:
        return None, reason

    def consequence(event):
        with transaction.atomic():
            if _clock() != (day, hour) or item.location != mask:
                raise RuntimeError("Carrier or market shift changed before installation.")
            if mask.location != market:
                raise RuntimeError("The public market hinge is not here.")
            latest, accepted, error = workshop_state.install(
                workplace.db.repair_docket,
                day=day, hour=hour, account_id=mask.account.id,
                mask_id=mask.id, mask=mask.key,
                event_id=event["id"], item_id=item.id,
                source_event_id=event_id,
            )
            if not accepted:
                raise RuntimeError(error)
            workplace.db.repair_docket = latest
            used = item.id
            item.delete()
            return {
                "market_room_id": market.id,
                "workshop_room_id": workplace.id,
                "consumed_item_id": used,
                "source_event_id": event_id,
            }

    event = publish_world_event(
        "village.market_hinge_installed", actor=mask,
        payload={
            "day": day, "hour": hour, "market_room_id": market.id,
            "source_event_id": event_id,
            "harbinger": False, "chronicle_eligible": False,
        },
        consequence=consequence,
    )
    calling = active_calling(mask)
    if calling:
        record_participation(mask, "market_hinges_installed", calling=calling)
    return {"event_id": event["id"], "source_event_id": event_id}, None


def bench_description():
    workplace = _room(WORKSHOP)
    if not workplace:
        return "The market workshop is being repaired."
    day, _hour = _clock()
    return (
        "A communal smithing bench holds a finite rack of iron offcuts, "
        "a vise and a shallow forge. Nothing is repaired merely by "
        "reading the docket.\n"
        + workshop_state.public_lines(workplace.db.repair_docket, day)
    )


def market_board_description():
    workplace = _room(WORKSHOP)
    if not workplace:
        return "An unfilled market repair board stands beside the stalls."
    day, _hour = _clock()
    return (
        "A public board names the market hinges that still need repair. "
        "The eastward Workshop can shape a physical replacement.\n"
        + workshop_state.public_lines(workplace.db.repair_docket, day)
    )
