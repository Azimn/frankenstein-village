"""Evennia adapter for GDD-EDGE-07 on the original Tavern guest register.

The Innkeep controls a limited disclosure, while a different Detective
makes a qualified physical inquiry. Neither action resolves Room Six canon.
"""
from __future__ import annotations

from django.db import transaction
from evennia.scripts.models import ScriptDB
from evennia.utils import search

from world import lodging_state
from world.callings import active_calling, record_participation
from world.events import get_event_ledger, publish_world_event

TAVERN = "The Blood of the Vine"
REGISTER = "register"


def _objects():
    taverns = [obj for obj in search.search_object(TAVERN)
               if obj.key == TAVERN and obj.location is None
               and obj.tags.has("ic", category="side")]
    if len(taverns) != 1:
        return None, None
    tavern = taverns[0]
    registers = [obj for obj in search.search_object(REGISTER)
                 if obj.key == REGISTER and obj.location == tavern
                 and obj.typeclass_path == "typeclasses.objects.Register"]
    return tavern, registers[0] if len(registers) == 1 else None


def _clock():
    try:
        clock = ScriptDB.objects.get(db_key="village_time")
        return int(clock.db.day or 1), int(
            clock.db.hour if clock.db.hour is not None else 21
        )
    except ScriptDB.DoesNotExist:
        return 1, 21


def _guard(mask):
    tavern, register = _objects()
    if not getattr(mask, "account", None):
        return tavern, register, "Log in with an ordinary player character."
    if tavern is None or register is None:
        return tavern, register, "The original Tavern guest register is unavailable."
    if mask.location != tavern:
        return tavern, register, "Visit the original guest register at the Blood of the Vine."
    return tavern, register, None


def _observed(mask):
    stage = getattr(mask.db, "room_six", None)
    return bool(hasattr(stage, "get") and stage.get("seen_register"))


def status(mask):
    _tavern, register, error = _guard(mask)
    if error:
        return error
    return lodging_state.public_lines(register.db.lodging_inquiry)


def act(mask, action):
    tavern, register, error = _guard(mask)
    if error:
        return None, error
    calling = {"disclose": "innkeep", "inquire": "detective"}.get(action)
    if calling is None:
        return None, "Use lodging, lodging disclose, or lodging inquire."
    if active_calling(mask) != calling:
        return None, "An active %s Calling is required for lodging %s." % (
            calling.title(), action
        )
    if not _observed(mask):
        return None, "Look at the original guest register first."
    day, hour = _clock()
    if lodging_state.valid_time(day, hour) is None:
        return None, "The village clock is invalid."
    common = {
        "day": day, "hour": hour, "account_id": mask.account.id,
        "mask_id": mask.id, "mask": mask.key,
        "register_id": register.id, "room_id": tavern.id,
    }
    source_id = None
    if action == "inquire":
        state = lodging_state.normalize(register.db.lodging_inquiry)
        row = next((r for r in reversed(state["records"])
                    if not r["inquiry"]), None)
        if row is None:
            return None, "No unused signed Innkeep disclosure is available."
        source_id = row["event_id"]
        source = get_event_ledger().get_event(source_id)
        if not lodging_state.source_is_valid(source, row):
            return None, "The original signed Innkeep disclosure cannot be verified."
        preview, okay, reason = lodging_state.inquire(
            register.db.lodging_inquiry, event_id=1,
            source_event_id=source_id, **common
        )
    else:
        preview, okay, reason = lodging_state.disclose(
            register.db.lodging_inquiry, event_id=1, **common
        )
    if not okay:
        return None, reason

    def consequence(event):
        with transaction.atomic():
            if (_clock() != (day, hour) or mask.location != tavern
                    or register.location != tavern
                    or active_calling(mask) != calling or not _observed(mask)):
                raise RuntimeError("The professional, register or village shift changed.")
            current = register.db.lodging_inquiry
            if action == "inquire":
                current_state = lodging_state.normalize(current)
                row = next((r for r in current_state["records"]
                            if r["event_id"] == source_id), None)
                source = get_event_ledger().get_event(source_id)
                if not lodging_state.source_is_valid(source, row):
                    raise RuntimeError("Original Innkeep provenance failed verification.")
                changed, accepted, why = lodging_state.inquire(
                    current, event_id=event["id"],
                    source_event_id=source_id, **common
                )
            else:
                changed, accepted, why = lodging_state.disclose(
                    current, event_id=event["id"], **common
                )
            if not accepted:
                raise RuntimeError(why)
            register.db.lodging_inquiry = changed
            return {
                "register_id": register.id, "room_id": tavern.id,
                "scope": lodging_state.SCOPE,
                "source_event_id": source_id if source_id else event["id"],
                "day": day, "hour": hour,
                "finding": "qualified_register_observation" if source_id else None,
            }

    event = publish_world_event(
        "village.lodging_" + ("disclosure" if action == "disclose" else "inquiry"),
        actor=mask,
        payload={
            "day": day, "hour": hour, "calling": calling,
            "register_id": register.id, "room_id": tavern.id,
            "scope": lodging_state.SCOPE, "source_event_id": source_id,
            "harbinger": False, "chronicle_eligible": False,
        },
        consequence=consequence,
    )
    record_participation(mask, "lodging_" + action, calling=calling)
    return {"event_id": event["id"], "source_event_id": source_id}, None
