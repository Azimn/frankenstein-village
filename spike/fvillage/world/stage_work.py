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


def cater(mask):
    """Innkeep places one actual cooked bowl at a genuinely witnessed show.

    The performance and witness are independent signed world events. The
    original consumable moves into the public Tavern, not a fictional crowd
    inventory. No food, attendance or extra stock is created by this action.
    """
    tavern, error = _guard(mask)
    if error:
        return None, error
    if active_calling(mask) != "innkeep":
        return None, "Only an active Innkeep can cater a performance."
    day, hour = _clock()
    bowls = sorted(
        (obj for obj in mask.contents
         if getattr(obj.db, "soup_serving", None)
         and int(getattr(obj.db, "servings", None) or 0) > 0
         and obj.tags.has("food")),
        key=lambda obj: obj.id,
    )
    if not bowls:
        return None, "Carry a real cooked soup bowl from soup simmer before catering."
    bowl = bowls[0]
    cooked = dict(bowl.db.soup_serving or {})
    try:
        cook_event_id = int(cooked["event_id"])
    except (TypeError, ValueError, KeyError, OverflowError):
        return None, "The bowl has no valid signed cooking source."

    def source_valid():
        ledger = get_event_ledger()
        cook = ledger.get_event(cook_event_id)
        if (not cook or cook.get("status") != "complete"
                or cook.get("kind") != "professional.innkeep_soup_cooked"
                or (cook.get("consequence") or {}).get("bowl_id") != bowl.id):
            return False
        state = stage_state.refresh(tavern.db.village_stage, day)
        show = state["performance"]
        if not show:
            return False
        performance = ledger.get_event(show["event_id"])
        if (not performance or performance.get("status") != "complete"
                or performance.get("kind") != "village.stage_perform"
                or (performance.get("actor") or {}).get("account_id")
                != show["account_id"]):
            return False
        return any(
            (witness := ledger.get_event(w["event_id"]))
            and witness.get("status") == "complete"
            and witness.get("kind") == "village.stage_witness"
            and (witness.get("actor") or {}).get("account_id") == w["account_id"]
            for w in state["witnesses"]
        )

    if not source_valid():
        return None, "The bowl, performance or firsthand audience source cannot be verified."
    stage = stage_state.refresh(tavern.db.village_stage, day)
    preview_id = max(stage["performance"]["event_id"], cook_event_id,
                     *(w["event_id"] for w in stage["witnesses"])) + 1
    _, allowed, reason = stage_state.cater(
        tavern.db.village_stage, day=day, hour=hour,
        account_id=mask.account.id, mask_id=mask.id, mask=mask.key,
        event_id=preview_id, bowl_id=bowl.id, cook_event_id=cook_event_id,
    )
    if not allowed:
        return None, reason

    def consequence(event):
        with transaction.atomic():
            if (_clock() != (day, hour) or mask.location != tavern
                    or active_calling(mask) != "innkeep"
                    or bowl.location != mask
                    or not getattr(bowl.db, "soup_serving", None)
                    or int(getattr(bowl.db, "servings", None) or 0) < 1):
                raise RuntimeError("The Innkeep, clock or real soup bowl changed.")
            if not source_valid():
                raise RuntimeError("The signed show, witness or cooking source changed.")
            state, accepted, why = stage_state.cater(
                tavern.db.village_stage, day=day, hour=hour,
                account_id=mask.account.id, mask_id=mask.id, mask=mask.key,
                event_id=event["id"], bowl_id=bowl.id,
                cook_event_id=cook_event_id,
            )
            if not accepted:
                raise RuntimeError(why)
            if not bowl.move_to(tavern, quiet=True):
                raise RuntimeError("The physical soup bowl could not be served.")
            bowl.db.stage_service = {
                "event_id": event["id"],
                "performance_event_id": state["service"]["performance_event_id"],
                "innkeep_account_id": mask.account.id,
            }
            tavern.db.village_stage = state
            record_participation(mask, "stage_catering", calling="innkeep")
            return {
                "day": day, "hour": hour, "tavern_room_id": tavern.id,
                "bowl_id": bowl.id, "cook_event_id": cook_event_id,
                "performance_event_id": state["service"]["performance_event_id"],
                "witness_event_id": state["service"]["witness_event_id"],
                "witness_count": state["service"]["witness_count"],
            }

    event = publish_world_event(
        "village.stage_cater", actor=mask,
        payload={"day": day, "hour": hour, "bowl_id": bowl.id,
                 "cook_event_id": cook_event_id,
                 "harbinger": False, "chronicle_eligible": False},
        consequence=consequence,
    )
    return {"event_id": event["id"], "bowl_id": bowl.id,
            "performance_event_id": event["consequence"]["performance_event_id"]}, None
