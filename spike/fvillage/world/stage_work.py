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


def _public_service_verified(tavern, state, ledger, bowl):
    """A public catering claim needs its original events AND the real bowl.

    Tavern stage attributes are mutable projections. They cannot themselves
    prove that food was cooked, carried or served by an independent player.
    """
    service = state.get("service")
    show = state.get("performance")
    witnesses = state.get("witnesses") or []
    if not (service and show and witnesses and bowl):
        return False
    try:
        witness = next((w for w in witnesses
                        if w["event_id"] == service["witness_event_id"]), None)
        if witness is None:
            return False
        event = ledger.get_event(service["event_id"])
        cook = ledger.get_event(service["cook_event_id"])
        performance = ledger.get_event(show["event_id"])
        witness_event = ledger.get_event(witness["event_id"])
        if not _catering_sources_match(
            state, cook, performance, witness_event,
            tavern_id=tavern.id, bowl_id=service["bowl_id"],
            cook_event_id=service["cook_event_id"],
        ):
            return False
        if not (hasattr(event, "get")
                and event.get("status") == "complete"
                and event.get("kind") == "village.stage_cater"):
            return False
        actor = event.get("actor") or {}
        payload = event.get("payload") or {}
        result = event.get("consequence") or {}
        if not all((
            event.get("id") == service["event_id"],
            actor.get("account_id") == service["account_id"],
            actor.get("mask_id") == service["mask_id"],
            actor.get("mask") == service["mask"],
            payload.get("day") == state["day"],
            payload.get("hour") == service["hour"],
            payload.get("bowl_id") == service["bowl_id"],
            payload.get("cook_event_id") == service["cook_event_id"],
            result.get("day") == state["day"],
            result.get("hour") == service["hour"],
            result.get("tavern_room_id") == tavern.id,
            result.get("bowl_id") == service["bowl_id"],
            result.get("cook_event_id") == service["cook_event_id"],
            result.get("performance_event_id") == show["event_id"],
            result.get("witness_event_id") == witness["event_id"],
            result.get("witness_count") == service["witness_count"],
            bowl.id == service["bowl_id"],
            bowl.location == tavern,
            bowl.tags.has("food"),
            int(bowl.db.servings or 0) > 0,
        )):
            return False
        cooked = bowl.db.soup_serving or {}
        placed = bowl.db.stage_service or {}
        return (cooked.get("event_id") == service["cook_event_id"]
                and placed.get("event_id") == service["event_id"]
                and placed.get("performance_event_id") == show["event_id"]
                and placed.get("innkeep_account_id") == service["account_id"])
    except (AttributeError, KeyError, TypeError, ValueError, OverflowError,
            RuntimeError, StopIteration):
        return False

def status(mask):
    tavern, error = _guard(mask)
    if error:
        return error
    day, _ = _clock()
    state = stage_state.refresh(tavern.db.village_stage, day)
    if state["service"]:
        try:
            candidates = search.search_object("#%d" % state["service"]["bowl_id"])
            bowl = next((obj for obj in candidates if obj.id == state["service"]["bowl_id"]), None)
            valid = _public_service_verified(tavern, state, get_event_ledger(), bowl)
        except (AttributeError, KeyError, TypeError, ValueError, RuntimeError):
            valid = False
        if not valid:
            state["service"] = None
    from world import stage_fitting_work
    return (stage_state.public_lines(state, day) + "\n" +
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


def _catering_sources_match(state, cook, performance, witness, *,
                            tavern_id, bowl_id, cook_event_id):
    """Verify the original signed show, its *own* witness and cooked bowl.

    Persisted stage rows are projections, never substitutes for the completed
    canonical world events. In particular a real witness of another show must
    not authorize catering this performance.
    """
    show = state.get("performance")
    sources = state.get("witnesses") or []
    if not show or not sources:
        return False
    source = sources[0]

    def completed(event, kind, event_id):
        return (hasattr(event, "get")
                and event.get("status") == "complete"
                and event.get("kind") == kind
                and event.get("id") == event_id)

    if not (completed(cook, "professional.innkeep_soup_cooked",
                      cook_event_id)
            and completed(performance, "village.stage_perform",
                          show.get("event_id"))
            and completed(witness, "village.stage_witness",
                          source.get("event_id"))):
        return False

    day, hour = state.get("day"), show.get("hour")
    show_actor = performance.get("actor") or {}
    show_payload = performance.get("payload") or {}
    show_result = performance.get("consequence") or {}
    witness_actor = witness.get("actor") or {}
    witness_payload = witness.get("payload") or {}
    witness_result = witness.get("consequence") or {}
    cook_payload = cook.get("payload") or {}
    cook_result = cook.get("consequence") or {}

    if not all((
        show_actor.get("account_id") == show.get("account_id"),
        show_actor.get("mask_id") == show.get("mask_id"),
        show_actor.get("mask") == show.get("mask"),
        show_payload.get("day") == day,
        show_payload.get("hour") == hour,
        show_payload.get("tune") == show.get("tune"),
        show_result.get("day") == day,
        show_result.get("hour") == hour,
        show_result.get("tune") == show.get("tune"),
        show_result.get("tavern_room_id") == tavern_id,
        show_result.get("performance_event_id") == show.get("event_id"),
        witness_actor.get("account_id") == source.get("account_id"),
        witness_actor.get("mask_id") == source.get("mask_id"),
        witness_actor.get("mask") == source.get("mask"),
        source.get("account_id") != show.get("account_id"),
        source.get("account_id") in show.get("eligible_audience_ids", []),
        witness_payload.get("day") == day,
        witness_payload.get("hour") == hour,
        witness_result.get("day") == day,
        witness_result.get("hour") == hour,
        witness_result.get("tavern_room_id") == tavern_id,
        witness_result.get("performance_event_id") == show.get("event_id"),
        show.get("event_id") < source.get("event_id"),
        cook_result.get("bowl_id") == bowl_id,
        cook_result.get("pantry_room_id") == tavern_id,
    )):
        return False

    # An actual cooked bowl may have been prepared earlier and transferred,
    # but a future signed cook event cannot supply a past public show.
    cooked_day, cooked_hour = cook_payload.get("day"), cook_payload.get("hour")
    return (type(cooked_day) is int and type(cooked_hour) is int
            and 1 <= cooked_day <= day and 0 <= cooked_hour <= 23
            and (cooked_day < day or cooked_hour <= hour))

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
        try:
            ledger = get_event_ledger()
            state = stage_state.refresh(tavern.db.village_stage, day)
            show = state["performance"]
            if not show or not state["witnesses"]:
                return False
            return _catering_sources_match(
                state,
                ledger.get_event(cook_event_id),
                ledger.get_event(show["event_id"]),
                ledger.get_event(state["witnesses"][0]["event_id"]),
                tavern_id=tavern.id, bowl_id=bowl.id,
                cook_event_id=cook_event_id,
            )
        except (AttributeError, KeyError, TypeError, ValueError, RuntimeError):
            # Unavailable or damaged canonical source never authorizes service.
            return False

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

