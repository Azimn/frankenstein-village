"""Evennia adapter for the real, daily Tavern performance stage."""
from __future__ import annotations

from collections.abc import Mapping

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

def _verified_public_status(raw, day, hour):
    """Show safety decisions only when original world sources still verify.

    Tavern Attribute projections are not signatures. In particular, a
    restored or edited projection must never advertise an invented Hound
    caution or an independent Performer decision as completed.
    """
    state = stage_state.refresh(raw, day)
    claimed_warning = bool(state.get("safety_warning"))
    claimed_decision = bool(state.get("safety_decision"))
    verified_warning = False
    verified_decision = False
    if claimed_warning:
        try:
            verified_warning = bool(_verified_warning(raw, day, hour))
        except (AttributeError, KeyError, TypeError, ValueError):
            verified_warning = False
    if claimed_decision and verified_warning:
        try:
            verified_decision = bool(_verified_decision(raw, day, hour))
        except (AttributeError, KeyError, TypeError, ValueError):
            verified_decision = False

    if not verified_warning:
        state["safety_warning"] = None
    if not verified_decision:
        state["safety_decision"] = None

    # Earlier-day projections are not independently verified by the current
    # daily route record. Never call a mutable archived choice signed.
    historical_claim = False
    for record in state["history"]:
        if isinstance(record, Mapping) and record.get("safety_decision"):
            record["safety_decision"] = None
            historical_claim = True

    lines = stage_state.public_lines(state, day)
    if (claimed_warning and not verified_warning
            or claimed_decision and not verified_decision):
        lines += "\nA stage safety claim could not be verified against the original signed events."
    if historical_claim:
        lines += "\nEarlier stage safety choices require separate source verification."
    return lines

def status(mask):
    tavern, error = _guard(mask)
    if error:
        return error
    day, hour = _clock()
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
    return (_verified_public_status(state, day, hour) + "\n" +
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
    if (action == "perform"
            and stage_state.refresh(tavern.db.village_stage, day).get("safety_decision")
            and not _verified_decision(tavern.db.village_stage, day, hour)):
        return None, "The signed Performer safety decision cannot be verified."
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
            account = getattr(mask, "account", None)
            if (mask.location != tavern or account is None
                    or account.id != kwargs["account_id"]):
                raise RuntimeError("The stage actor left or changed account.")
            if action in {"rehearse", "perform"} and active_calling(mask) != "performer":
                raise RuntimeError("The Performer Calling changed before the event.")
            if action == "witness":
                try:
                    connected = bool(account.sessions.all())
                except (AttributeError, TypeError):
                    connected = False
                if not connected:
                    raise RuntimeError("The witness is no longer connected.")
            if (action == "perform"
                    and stage_state.refresh(tavern.db.village_stage, day).get("safety_decision")
                    and not _verified_decision(tavern.db.village_stage, day, hour)):
                raise RuntimeError("The signed Performer safety decision changed.")
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


def _verified_route_source(*, account_id, mask_id, source_event_id,
                           cord_id, day, hour):
    """Check ledger, actual cord and Square record, not a claimed danger."""
    from world import route_work, route_surveys
    from world.discoveries import LANDMARKS

    square = route_work._square()
    if square is None:
        return False
    state = route_surveys.normalize(square.db.daily_route_survey)
    if state["day"] != day:
        return False
    signed = state["field_decisions"].get("hound") or {}
    if signed.get("event_id") != source_event_id or signed.get("account_id") != account_id:
        return False
    spec = LANDMARKS["red_cord"]
    rooms = [o for o in search.search_object(spec["room"])
             if o.key == spec["room"] and o.location is None]
    if len(rooms) != 1:
        return False
    cord = next((o for o in rooms[0].contents
                 if o.id == cord_id and o.key == spec["key"]
                 and getattr(o.db, "landmark_id", None) == "red_cord"), None)
    if cord is None:
        return False
    raw_marker = getattr(cord.db, "route_caution", None)
    if not isinstance(raw_marker, Mapping):
        return False
    marker = dict(raw_marker)
    if (marker.get("event_id") != source_event_id
            or marker.get("account_id") != account_id
            or marker.get("day") != day):
        return False
    event = get_event_ledger().get_event(source_event_id)
    return stage_state.verified_hound_source(
        state, event, marker, account_id=account_id, mask_id=mask_id,
        source_event_id=source_event_id, cord_id=cord_id,
        square_id=square.id, day=day, hour=hour, room_name=spec["room"],
    )


def _verified_warning(stage, day, hour):
    warning = stage_state.refresh(stage, day).get("safety_warning")
    if not warning:
        return False
    signed = get_event_ledger().get_event(warning["event_id"])
    if (not isinstance(signed, Mapping)
            or signed.get("kind") != "village.stage_warned"
            or signed.get("status") != "complete"):
        return False
    actor, payload, effect = (signed.get("actor"), signed.get("payload"),
                              signed.get("consequence"))
    if not all(isinstance(value, Mapping) for value in (actor, payload, effect)):
        return False
    tavern = _tavern()
    if tavern is None:
        return False
    if not (
        actor.get("account_id") == warning["account_id"]
        and actor.get("mask_id") == warning["mask_id"]
        and payload.get("day") == day
        and payload.get("hour") == warning["hour"]
        and payload.get("source_event_id") == warning["source_event_id"]
        and effect.get("source_event_id") == warning["source_event_id"]
        and effect.get("hour") == warning["hour"]
        and effect.get("cord_id") == warning["cord_id"]
        and effect.get("tavern_room_id") == tavern.id
        and isinstance(warning["hour"], int)
        and warning["hour"] <= hour
    ):
        return False
    return _verified_route_source(
        account_id=warning["account_id"], mask_id=warning["mask_id"],
        source_event_id=warning["source_event_id"],
        cord_id=warning["cord_id"], day=day, hour=warning["hour"],
    )


def _verified_decision(stage, day, hour):
    state = stage_state.refresh(stage, day)
    warning, decision = state.get("safety_warning"), state.get("safety_decision")
    if not warning or not decision or not _verified_warning(stage, day, hour):
        return False
    signed = get_event_ledger().get_event(decision["event_id"])
    if (not isinstance(signed, Mapping)
            or signed.get("status") != "complete"
            or signed.get("kind") != "village.stage_adapted"):
        return False
    actor, payload, effect = (
        signed.get("actor"), signed.get("payload"),
        signed.get("consequence"))
    if not all(isinstance(value, Mapping) for value in (actor, payload, effect)):
        return False
    tavern = _tavern()
    if tavern is None:
        return False
    return (
        decision["account_id"] != warning["account_id"]
        and actor.get("account_id") == decision["account_id"]
        and actor.get("mask_id") == decision["mask_id"]
        and payload.get("day") == day
        and payload.get("hour") == decision["hour"]
        and payload.get("choice") == decision["choice"]
        and effect.get("tavern_room_id") == tavern.id
        and effect.get("hour") == decision["hour"]
        and effect.get("warning_event_id") == warning["event_id"]
        and effect.get("choice") == decision["choice"]
        and isinstance(decision["hour"], int)
        and not isinstance(decision["hour"], bool)
        and decision["hour"] >= warning["hour"]
        and decision["hour"] <= hour
    )


def safety_action(mask, action, choice=None):
    """Hound brings actual route evidence; independent Performer chooses fate."""
    tavern, error = _guard(mask)
    if error:
        return None, error
    role = active_calling(mask)
    if (action, role) not in {("warn", "hound"), ("adapt", "performer")}:
        return None, "Only an active Hound may warn; only a Performer may adapt."
    if action == "adapt" and choice not in {"indoor", "cancel"}:
        return None, "Use stage adapt indoor or stage adapt cancel."
    day, hour = _clock()
    # A completed performance is authoritative even when a later warning
    # lacks valid provenance. Reject retroactive edits before consulting
    # mutable route evidence; no world event is created on this path.
    if (action == "warn"
            and stage_state.refresh(tavern.db.village_stage, day).get("performance")):
        return None, "A warning cannot retroactively change an actual show."
    base = {"day": day, "hour": hour, "account_id": mask.account.id,
            "mask_id": mask.id, "mask": mask.key}
    if action == "warn":
        from world import route_work, route_surveys
        square = route_work._square()
        if square is None:
            return None, "The public route record is missing."
        record = route_surveys.normalize(square.db.daily_route_survey)
        source = record["field_decisions"].get("hound") or {}
        source_id = source.get("event_id")
        from world.discoveries import LANDMARKS
        spec = LANDMARKS["red_cord"]
        rooms = [o for o in search.search_object(spec["room"])
                 if o.key == spec["room"] and o.location is None]
        cord = next((o for o in rooms[0].contents
                     if o.key == spec["key"]
                     and getattr(o.db, "landmark_id", None) == "red_cord"), None) if len(rooms) == 1 else None
        if not cord or not _verified_route_source(
                account_id=mask.account.id, mask_id=mask.id,
                source_event_id=source_id, cord_id=cord.id, day=day, hour=hour):
            return None, "First protect the actual treeline cord today, then bring its signed warning here."
        extra = {"source_event_id": source_id, "cord_id": cord.id}
        transform = stage_state.warn
    else:
        if not _verified_warning(tavern.db.village_stage, day, hour):
            return None, "The stage warning has no verified current physical source."
        extra = {"choice": choice}
        transform = stage_state.adapt

    _preview, accepted, reason = transform(
        tavern.db.village_stage, event_id=1, **base, **extra)
    if not accepted:
        return None, reason

    def consequence(event):
        with transaction.atomic():
            # A signed Hound/Performer decision must belong to the same
            # authenticated account that passed the original role check.
            account = getattr(mask, "account", None)
            if (mask.location != tavern or account is None
                    or account.id != base["account_id"]
                    or active_calling(mask) != role):
                raise RuntimeError(
                    "The player left the stage or changed account or Calling."
                )
            if _clock() != (day, hour):
                raise RuntimeError("Village time changed before the stage decision.")
            if action == "warn":
                if not _verified_route_source(
                        account_id=mask.account.id, mask_id=mask.id,
                        source_event_id=extra["source_event_id"],
                        cord_id=extra["cord_id"], day=day, hour=hour):
                    raise RuntimeError("The physical route warning source changed.")
            elif not _verified_warning(tavern.db.village_stage, day, hour):
                raise RuntimeError("The signed warning cannot be verified.")
            current, ok, why = transform(
                tavern.db.village_stage, event_id=event["id"], **base, **extra)
            if not ok:
                raise RuntimeError(why)
            tavern.db.village_stage = current
            return {"tavern_room_id": tavern.id, "day": day, "hour": hour,
                    "source_event_id": extra.get("source_event_id"),
                    "cord_id": extra.get("cord_id"),
                    "warning_event_id": (
                        current["safety_warning"]["event_id"]
                        if current["safety_warning"] else None),
                    "choice": choice}

    event = publish_world_event(
        "village.stage_warned" if action == "warn" else "village.stage_adapted",
        actor=mask,
        payload={"day": day, "hour": hour, "choice": choice,
                 "source_event_id": extra.get("source_event_id"),
                 "harbinger": False, "chronicle_eligible": False},
        consequence=consequence,
    )
    record_participation(mask, "stage_" + action, calling=role)
    return {"event_id": event["id"], "action": action, "choice": choice}, None

