"""Evennia adapter for the real, daily Tavern performance stage."""
from __future__ import annotations

from django.db import transaction
from evennia.scripts.models import ScriptDB
from evennia.utils import search

from world import stage_state
from world.callings import active_calling, record_participation
from world.events import get_event_ledger, publish_world_event

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



def _verified_performance(tavern, state, ledger, day):
    return stage_state.verify_sources(
        state, day=day, tavern_room_id=tavern.id,
        get_event=ledger.get_event,
    )


def investigate(mask):
    """An independent Detective inspects the stage and signs a limited timeline.

    The performance remains playable without a Detective. This does not grant
    access to private notes or certify the performer's innocence or location
    outside the recorded performance.
    """
    tavern, error = _guard(mask)
    if error:
        return None, error
    if active_calling(mask) != "detective":
        return None, "Only an active Detective may file a stage investigation."
    platform = next((obj for obj in tavern.contents
                     if obj.key == "a modest performance platform"
                     and obj.location == tavern), None)
    if platform is None:
        return None, "The physical performance platform is missing."
    day, hour = _clock()
    state = stage_state.refresh(tavern.db.village_stage, day)
    verified, error = _verified_performance(tavern, state, get_event_ledger(), day)
    if error:
        return None, error
    show = state["performance"]
    kwargs = {
        "day": day, "hour": hour,
        "account_id": mask.account.id, "mask_id": mask.id, "mask": mask.key,
        "source_event_id": show["event_id"],
        "source_account_id": show["account_id"],
        "source_mask_id": show["mask_id"],
        "source_hour": show["hour"], "source_tune": show["tune"],
        "witness_event_ids": verified, "stage_object_id": platform.id,
    }
    _preview, ok, reason = stage_state.investigate(
        tavern.db.village_stage, event_id=1, **kwargs
    )
    if not ok:
        return None, reason

    def consequence(event):
        with transaction.atomic():
            if (_clock() != (day, hour) or mask.location != tavern
                    or platform.location != tavern
                    or active_calling(mask) != "detective"):
                raise RuntimeError("The Detective, stage or village time changed.")
            current = stage_state.refresh(tavern.db.village_stage, day)
            current_verified, why = _verified_performance(
                tavern, current, get_event_ledger(), day
            )
            if why or current_verified != verified:
                raise RuntimeError(why or "The signed audience evidence changed.")
            changed, accepted, reason = stage_state.investigate(
                tavern.db.village_stage, event_id=event["id"], **kwargs
            )
            if not accepted:
                raise RuntimeError(reason)
            tavern.db.village_stage = changed
            return {
                "tavern_room_id": tavern.id,
                "stage_object_id": platform.id,
                "performance_event_id": show["event_id"],
                "witness_event_ids": list(verified),
                "independent_detective_account_id": mask.account.id,
                "inquiry_event_id": event["id"],
                "conclusion": "signed_show_not_alibi",
            }

    event = publish_world_event(
        "village.stage_investigated", actor=mask,
        payload={
            "day": day, "hour": hour, "tavern_room_id": tavern.id,
            "stage_object_id": platform.id,
            "source_performance_event_id": show["event_id"],
            "verified_witness_event_ids": list(verified),
            "harbinger": False, "chronicle_eligible": False,
        },
        consequence=consequence,
    )
    record_participation(mask, "stage_investigations", calling="detective")
    return {
        "event_id": event["id"],
        "source_event_id": show["event_id"],
        "witness_count": len(verified),
    }, None
