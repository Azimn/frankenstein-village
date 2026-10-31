"""Evennia adapter for the real, daily Tavern performance stage."""
from __future__ import annotations

from django.db import transaction
from evennia.scripts.models import ScriptDB
from evennia.utils import search

from world import stage_state
from world.callings import active_calling, record_participation
from world.events import publish_world_event, get_event_ledger

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
    from world import stage_fitting_work
    return (stage_state.public_lines(tavern.db.village_stage, day) + "\n" +
            stage_fitting_work.public_status(tavern))


def archive(mask):
    tavern, error = _guard(mask)
    if error:
        return error
    day, _ = _clock()
    return stage_state.archive_lines(tavern.db.village_stage, day)


def act(mask, action, tune=None):
    tavern, error = _guard(mask)
    if error:
        return None, error
    if action not in {"rehearse", "perform", "witness", "review", "contest"}:
        return None, "Use stage, stage rehearse ballad|reel, stage perform ballad|reel, or stage witness."
    if action in {"rehearse", "perform", "contest"} and active_calling(mask) != "performer":
        return None, "An active Performer must rehearse and perform."
    if action == "review" and active_calling(mask) != "chronicler":
        return None, "An active Chronicler must review a witnessed performance."
    if action == "review" and tune not in stage_state.VERDICTS:
        return None, "Choose praise or critique."
    if action == "witness" and tune is not None:
        return None, "Use stage witness without a tune."
    if action in {"rehearse", "perform"} and tune not in stage_state.TUNES:
        return None, "Choose ballad or reel."
    day, hour = _clock()
    contest_review_id = None
    if action == "contest":
        if tune is not None:
            contest_review_id = stage_state.parse_review_id(tune)
            if contest_review_id is None:
                return None, "Choose a positive numeric review event ID."
        else:
            current = stage_state.refresh(tavern.db.village_stage, day)
            show = current["performance"]
            latest = (show.get("reviews") or [])[-1] if show and show.get("reviews") else None
            contest_review_id = stage_state.parse_review_id(
                latest.get("event_id") if latest else None
            )
            if contest_review_id is None:
                return None, "No signed review exists for this performance."
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

        if action == "review":
            current = stage_state.refresh(tavern.db.village_stage, day)
            show = current["performance"]
            witness = next((
                w for w in current["witnesses"]
                if w["account_id"] == mask.account.id and w["mask_id"] == mask.id
            ), None)
            context = {
                "verdict": tune,
                "performance_event_id": show["event_id"] if show else None,
                "witness_event_id": witness["event_id"] if witness else None,
            }
        elif action == "contest":
            # Fixed at command admission: signed payload and consequence use
            # exactly the same positive integer, including the no-arg path.
            context = {"review_event_id": contest_review_id}
        return context

    def source_error(context):
        if action not in {"review", "contest"}:
            return None
        current = stage_state.refresh(tavern.db.village_stage, day)
        show = current["performance"]
        if not show:
            return None
        ledger = get_event_ledger()
        if action == "review":
            witness = next((
                w for w in current["witnesses"]
                if w["account_id"] == mask.account.id and w["mask_id"] == mask.id
                and w["event_id"] == context.get("witness_event_id")
            ), None)
            if witness is None:
                return None
        else:
            review_row = next((
                r for r in show.get("reviews") or []
                if r["event_id"] == stage_state._ident(context.get("review_event_id"))
            ), None)
            if review_row is None:
                return None
            witness = next((
                w for w in current["witnesses"]
                if w["event_id"] == review_row["witness_event_id"]
                and w["account_id"] == review_row["account_id"]
            ), None)
            if not witness or not stage_state.verify_review_event(
                review_row, ledger.get_event(review_row["event_id"]), show
            ):
                return "The original signed review cannot be verified."
        sources = {
            "performance": ledger.get_event(show["event_id"]),
            "rehearsal": ledger.get_event(show.get("rehearsal_event_id")),
            "witness": ledger.get_event(witness["event_id"]),
        }
        if not stage_state.verify_review_sources(show, witness, sources, day=day):
            return "The performance and firsthand witness ledger sources cannot be verified."
        return None

    context = contextual_kwargs()
    problem = source_error(context)
    if problem:
        return None, problem

    preview, ok, reason = transform(tavern.db.village_stage, event_id=1,
                                    **kwargs, **context)
    if not ok:
        return None, reason

    def consequence(event):
        with transaction.atomic():
            # Recheck after the ledger opens; never trust an earlier preview.
            now_day, now_hour = _clock()
            if (now_day, now_hour) != (day, hour):
                raise RuntimeError("Village clock changed before the stage event.")
            if action in {"review", "contest"} and (
                mask.location != tavern or active_calling(mask) != (
                    "chronicler" if action == "review" else "performer"
                )
            ):
                raise RuntimeError("The acting professional left or changed Calling.")
            live_context = contextual_kwargs()
            problem = source_error(live_context)
            if problem:
                raise RuntimeError(problem)
            current, accepted, reason = transform(
                tavern.db.village_stage, event_id=event["id"],
                **kwargs, **live_context,
            )
            if not accepted:
                raise RuntimeError(reason)
            tavern.db.village_stage = current
            return {
                "tavern_room_id": tavern.id, "day": day, "hour": hour,
                "tune": None if action == "contest" else tune,
                "witnesses": len(current["witnesses"]),
                "performance_event_id": (
                    current["performance"]["event_id"]
                    if current["performance"] else None
                ),
                "review_event_id": event["id"] if action == "review" else live_context.get("review_event_id"),
                "witness_event_id": live_context.get("witness_event_id"),
                "verdict": live_context.get("verdict"),
            }

    event = publish_world_event(
        "village.stage_" + action, actor=mask,
        payload={"day": day, "hour": hour,
                 "tune": None if action == "contest" else tune,
                 "source_performance_event_id": context.get("performance_event_id"),
                 "source_witness_event_id": context.get("witness_event_id"),
                 "review_event_id": context.get("review_event_id"),
                 "verdict": context.get("verdict"),
                 "harbinger": False, "chronicle_eligible": False},
        consequence=consequence,
    )
    if action != "witness":
        record_participation(mask, "stage_" + action,
                             calling="chronicler" if action == "review" else "performer")
    return {"event_id": event["id"], "action": action, "tune": tune}, None
