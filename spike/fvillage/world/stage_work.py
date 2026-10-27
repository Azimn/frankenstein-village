"""Evennia adapter for the real, daily Tavern performance stage."""
from __future__ import annotations

from django.db import transaction
from evennia.scripts.models import ScriptDB
from evennia.utils import search

from world import stage_state
from world.callings import active_calling, record_participation
from world.events import publish_world_event

TAVERN = "The Blood of the Vine"


def _tavern():
    return next((o for o in search.search_object(TAVERN)
                 if o.key == TAVERN and o.location is None
                 and o.tags.has("ic", category="side")), None)


def _clock():
    try:
        c = ScriptDB.objects.get(db_key="village_time")
        return int(c.db.day or 1), int(c.db.hour if c.db.hour is not None else 21)
    except ScriptDB.DoesNotExist:
        return 1, 21


def _guard(mask):
    tavern = _tavern()
    if not getattr(mask, "account", None):
        return tavern, "Log in with an ordinary player character first."
    if tavern is None or mask.location != tavern:
        return tavern, "Visit the real stage at the Blood of the Vine."
    return tavern, None


def status(mask):
    tavern, error = _guard(mask)
    if error:
        return error
    day, _ = _clock()
    return stage_state.public_lines(tavern.db.village_stage, day)


def act(mask, action, tune=None):
    tavern, error = _guard(mask)
    if error:
        return None, error
    if action not in {"rehearse", "perform", "witness"}:
        return None, "Use stage, stage rehearse ballad|reel, stage perform ballad|reel, or stage witness."
    if action in {"rehearse", "perform"} and active_calling(mask) != "performer":
        return None, "An active Performer must rehearse and perform."
    if action == "witness" and tune is not None:
        return None, "Use stage witness without a tune."
    if action != "witness" and tune not in stage_state.TUNES:
        return None, "Choose ballad or reel."
    day, hour = _clock()
    kwargs = {
        "day": day, "hour": hour,
        "account_id": mask.account.id, "mask_id": mask.id,
        "mask": mask.key,
    }
    transform = getattr(stage_state, action)

    def contextual_kwargs():
        context = {"tune": tune} if tune else {}
        if action == "perform":
            # Only independently connected, co-located player masks were in
            # the real audience at the moment the music was actually played.
            audience = []
            for person in tavern.contents:
                account = getattr(person, "account", None)
                if person == mask or account is None:
                    continue
                try:
                    if not account.sessions.all():
                        continue
                except (AttributeError, TypeError):
                    continue
                audience.append(account.id)
            context["audience_account_ids"] = audience
        return context

    preview, ok, reason = transform(tavern.db.village_stage, event_id=1,
                                    **kwargs, **contextual_kwargs())
    if not ok:
        return None, reason

    def consequence(event):
        with transaction.atomic():
            # Recheck after the ledger opens; never trust an earlier preview.
            now_day, now_hour = _clock()
            if (now_day, now_hour) != (day, hour):
                raise RuntimeError("Village clock changed before the stage event.")
            current, accepted, reason = transform(
                tavern.db.village_stage, event_id=event["id"],
                **kwargs, **contextual_kwargs(),
            )
            if not accepted:
                raise RuntimeError(reason)
            tavern.db.village_stage = current
            return {
                "tavern_room_id": tavern.id, "day": day, "hour": hour,
                "tune": tune, "witnesses": len(current["witnesses"]),
                "performance_event_id": (
                    current["performance"]["event_id"]
                    if current["performance"] else None
                ),
            }

    event = publish_world_event(
        "village.stage_" + action, actor=mask,
        payload={"day": day, "hour": hour, "tune": tune,
                 "harbinger": False, "chronicle_eligible": False},
        consequence=consequence,
    )
    if action != "witness":
        record_participation(mask, "stage_" + action, calling="performer")
    return {"event_id": event["id"], "action": action, "tune": tune}, None

def serve(mask, target_name):
    """Transfer an existing edible bowl, never a fictitious catering credit."""
    tavern, error = _guard(mask)
    if error:
        return None, error
    if active_calling(mask) != "innkeep":
        return None, "An active Innkeep must provide performance hospitality."
    matches = [
        person for person in tavern.contents
        if getattr(person, "key", "").casefold() == target_name.casefold()
        and getattr(person, "account", None) is not None
    ]
    if len(matches) != 1:
        return None, "The recipient must be a distinct player present at the Tavern."
    guest = matches[0]
    if guest == mask:
        return None, "You cannot serve yourself."
    try:
        connected = bool(guest.account.sessions.all())
    except (AttributeError, TypeError):
        connected = False
    if not connected:
        return None, "The recipient must be connected and present for service."
    day, hour = _clock()
    bowls = [
        obj for obj in mask.contents
        if obj.location == mask and getattr(obj.db, "soup_serving", None)
        and int(getattr(obj.db, "servings", 0) or 0) > 0
    ]
    if not bowls:
        return None, "Carry a real uneaten homemade soup bowl; use soup prep and soup simmer."
    bowl = bowls[0]
    source = dict(bowl.db.soup_serving)
    details = dict(
        day=day, hour=hour, account_id=mask.account.id,
        mask_id=mask.id, mask=mask.key,
        recipient_account_id=guest.account.id, recipient_mask_id=guest.id,
        bowl_id=bowl.id, cook_event_id=source.get("event_id"),
    )
    _preview, ok, reason = stage_state.serve(
        tavern.db.village_stage, event_id=1, **details,
    )
    if not ok:
        return None, reason

    def consequence(event):
        with transaction.atomic():
            current_tavern, access_error = _guard(mask)
            if access_error or current_tavern != tavern:
                raise RuntimeError(access_error or "The Innkeep left the Tavern.")
            if active_calling(mask) != "innkeep":
                raise RuntimeError("The Innkeep Calling changed before service.")
            if _clock() != (day, hour):
                raise RuntimeError("The performance hour changed before service.")
            if guest.location != tavern or guest.account.id != details["recipient_account_id"]:
                raise RuntimeError("The guest left the Tavern before service.")
            try:
                if not guest.account.sessions.all():
                    raise RuntimeError("The guest disconnected before service.")
            except (AttributeError, TypeError):
                raise RuntimeError("The guest is no longer connected.")
            if (bowl.location != mask or
                    dict(bowl.db.soup_serving or {}) != source or
                    int(bowl.db.servings or 0) < 1):
                raise RuntimeError("The physical soup bowl was moved or consumed.")
            updated, accepted, reason = stage_state.serve(
                tavern.db.village_stage, event_id=event["id"], **details,
            )
            if not accepted:
                raise RuntimeError(reason)
            if not bowl.move_to(guest, quiet=True):
                raise RuntimeError("The soup bowl could not be transferred.")
            tavern.db.village_stage = updated
            return {
                "tavern_room_id": tavern.id, "bowl_id": bowl.id,
                "recipient_mask_id": guest.id,
                "cook_event_id": source["event_id"],
                "performance_event_id": updated["performance"]["event_id"],
            }

    try:
        event = publish_world_event(
            "village.stage_hospitality", actor=mask,
            payload={
                "day": day, "hour": hour, "bowl_id": bowl.id,
                "cook_event_id": source["event_id"],
                "recipient_mask_id": guest.id,
                "chronicle_eligible": False, "harbinger": False,
            },
            consequence=consequence,
        )
    except RuntimeError as error:
        return None, str(error)
    record_participation(mask, "stage_hospitality", calling="innkeep")
    return {
        "action": "serve", "event_id": event["id"],
        "recipient": guest.key, "bowl_id": bowl.id,
    }, None
