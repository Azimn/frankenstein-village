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
    return _verified_public_status(tavern.db.village_stage, day, hour)


def act(mask, action, tune=None):
    tavern, error = _guard(mask)
    if error:
        return None, error
    if action not in {"rehearse", "perform", "witness"}:
        return None, "Use stage, stage rehearse ballad or stage rehearse reel, stage perform ballad or stage perform reel, or stage witness."
    if action in {"rehearse", "perform"} and active_calling(mask) != "performer":
        return None, "An active Performer must rehearse and perform."
    if action == "witness" and tune is not None:
        return None, "Use stage witness without a tune."
    if action != "witness" and tune not in stage_state.TUNES:
        return None, "Choose ballad or reel."
    day, hour = _clock()
    if (action == "perform"
            and stage_state.refresh(tavern.db.village_stage, day).get("safety_decision")
            and not _verified_decision(tavern.db.village_stage, day, hour)):
        return None, "The signed Performer safety decision cannot be verified."
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

    # The ledger may execute the consequence after the preview. Preserve the
    # actual actor's identity and authorization across that boundary.
    expected_account_id = mask.account.id

    def consequence(event):
        with transaction.atomic():
            # A preview cannot authorize a later action by a different account,
            # a player who has left the stage, or a former Performer.
            account = getattr(mask, "account", None)
            if (mask.location != tavern or account is None
                    or account.id != expected_account_id):
                raise RuntimeError("The stage actor left or changed account.")
            if (action in {"rehearse", "perform"}
                    and active_calling(mask) != "performer"):
                raise RuntimeError("The Performer Calling changed before the event.")
            if action == "witness":
                try:
                    connected = bool(account.sessions.all())
                except (AttributeError, TypeError):
                    connected = False
                if not connected:
                    raise RuntimeError("The witness is no longer connected.")
            # Recheck after the ledger opens; never trust an earlier preview.
            now_day, now_hour = _clock()
            if (now_day, now_hour) != (day, hour):
                raise RuntimeError("Village clock changed before the stage event.")
            if (action == "perform"
                    and stage_state.refresh(tavern.db.village_stage, day).get("safety_decision")
                    and not _verified_decision(tavern.db.village_stage, day, hour)):
                raise RuntimeError("The signed Performer safety decision changed.")
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
