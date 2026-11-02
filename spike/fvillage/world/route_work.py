"""Physical player-authored daily route surveys, using the canonical clock.

Existing object inspections and player Calling records are reused. Nothing
teleports, grants a quest reward, or publishes a claim as objective truth.
"""
from __future__ import annotations

from django.db import transaction
from evennia.scripts.models import ScriptDB
from evennia.utils import search

from world import route_surveys
from world.callings import active_calling, record_participation
from world.discoveries import LANDMARKS, normalize as known_landmarks
from world.events import publish_world_event

SQUARE = "Village Square"
SCOUT_ROLES = frozenset({"wanderer", "hound", "detective"})


def _square():
    return next(
        (obj for obj in search.search_object(SQUARE)
         if obj.key == SQUARE and obj.location is None),
        None,
    )


def _day_hour():
    try:
        clock = ScriptDB.objects.get(db_key="village_time")
        return int(clock.db.day or 1), int(
            clock.db.hour if clock.db.hour is not None else 21
        )
    except ScriptDB.DoesNotExist:
        return 1, 21


def status_lines():
    square = _square()
    if not square:
        return "The route report is unavailable; the Square is missing."
    day, _hour = _day_hour()
    state = route_surveys.refresh(square.db.daily_route_survey, day)
    lines = [
        "|wVillage daily route survey|n",
        f"Day {day}. Confirmed checkpoints: {len(state['reports'])} of "
        f"{len(route_surveys.SITES)}.",
    ]
    for ident in route_surveys.SITES:
        spec = LANDMARKS[ident]
        report = state["reports"].get(ident)
        if report:
            lines.append(
                f"* {spec['room']}: inspected by {report['mask']} "
                f"(world event {report['event_id']})."
            )
        else:
            lines.append(
                f"* {spec['room']}: not yet inspected. Find "
                f"{spec['key']} and examine it."
            )
    lines.extend(route_surveys.field_lines(state))
    lines.append(
        "At the Northern Treeline, an active Hound can examine the actual "
        "frayed red cord and use |wsurvey protect|n to tie a visible warning. "
        "An active Wanderer can independently use |wsurvey passability|n "
        "there to record whether the warning was present when inspected. "
        "Neither action proves why the cord was damaged."
    )
    lines.append(
        "At Riverside Path, a Wanderer can examine the actual river gauge "
        "and use |wsurvey gauge|n to sign firsthand flood-mark evidence. "
        "A different Detective can examine that same gauge and use "
        "|wsurvey compare|n for a qualified source-linked case note. "
        "|wsurvey evidence|n reads the gauge record; it does not solve "
        "the bridge mystery or predict a flood."
    )
    if route_surveys.complete(state):
        lines.append(
            "The public route is complete for today. Tomorrow's observations "
            "will begin a new record without erasing these signed reports."
        )
    else:
        lines.append(
            "After examining a landmark in person, use |wsurvey report|n "
            "while still there. Other travelers can finish different stops."
        )
    lines.append(
        "The board is public. You can ask a resident you actually meet "
        "about the survey (|wask <resident> about survey|n); they may "
        "recognize the person who signed a real inspection."
    )
    if state["history"]:
        prior = state["history"][-1]
        lines.append(
            f"Previous surveyed day {prior['day']}: "
            + ("complete" if prior["completed"] else "unfinished")
            + f" ({len(prior['reports'])} of {len(route_surveys.SITES)})."
        )
    return "\n".join(lines)


def report(mask):
    if not getattr(mask, "account", None):
        return None, "A logged-in player mask is required."
    room = getattr(mask, "location", None)
    if not room or not room.tags.has("ic", category="side"):
        return None, "The route can only be inspected from inside the village."
    site = next(
        (ident for ident in route_surveys.SITES
         if LANDMARKS[ident]["room"] == room.key),
        None,
    )
    if site is None:
        return None, "Travel to a listed district landmark before reporting."
    clue = next(
        (obj for obj in room.contents
         if getattr(obj.db, "landmark_id", None) == site
         and obj.key == LANDMARKS[site]["key"]
         and obj.access(mask, "view", default=True)),
        None,
    )
    if clue is None:
        return None, "The landmark is not available for a physical inspection."
    day, hour = _day_hour()
    witnessed = any(
        row["id"] == site
        for row in known_landmarks(mask.db.landmark_discoveries)
    )
    try:
        recent = dict(mask.db.landmark_latest_view or {}).get(site) or {}
        inspected_today = int(recent.get("day") or 0) == day
    except (ValueError, TypeError, OverflowError):
        inspected_today = False
    if not witnessed or not inspected_today:
        return None, (
            f"First examine {LANDMARKS[site]['key']} here today. "
            "Reading an old report or merely entering does not qualify."
        )
    square = _square()
    if square is None:
        return None, "The village Square report cannot be found."
    existing = route_surveys.refresh(square.db.daily_route_survey, day)
    if existing["day"] > day:
        return None, "A later village day is already recorded."
    if site in existing["reports"]:
        return None, "Today's report for this landmark is already signed."

    def consequence(event):
        with transaction.atomic():
            if mask.location != room or clue.location != room:
                raise RuntimeError("The observer left the actual landmark.")
            changed, accepted, error = route_surveys.report(
                square.db.daily_route_survey, day, site,
                mask.account.id, mask.key, event["id"],
            )
            if not accepted:
                raise RuntimeError(error)
            square.db.daily_route_survey = changed
            role = active_calling(mask)
            if role:
                metric = (
                    "field_surveys" if role in SCOUT_ROLES
                    else "community_route_contributions"
                )
                record_participation(mask, metric, calling=role)
            return {
                "site": site,
                "day": day,
                "completed": route_surveys.complete(changed),
                "count": len(changed["reports"]),
            }

    event = publish_world_event(
        "village.route_inspected",
        actor=mask,
        payload={
            "site": site, "day": day, "hour": hour,
            "location": room.key,
            "harbinger": False, "chronicle_eligible": False,
        },
        consequence=consequence,
    )
    current = route_surveys.refresh(square.db.daily_route_survey, day)
    return {
        "event_id": event["id"], "site": site,
        "count": len(current["reports"]),
        "completed": route_surveys.complete(current),
    }, None

def field_action(mask, action):
    """Professionally distinct decisions using the existing physical cord.

    Route state remains the Square's daily record. The inspected, real cord is
    the owner of its durable physical warning marker. There is no new quest,
    separate hazard truth, cloned stock, or automatic success for a class tag.
    """
    if not getattr(mask, "account", None):
        return None, "Use an ordinary logged-in player mask."
    role = active_calling(mask)
    if (role, action) not in {
        ("hound", "protect"), ("wanderer", "passability")
    }:
        return None, "Only a Hound can protect a route and a Wanderer can assess passability."
    site = "red_cord"
    room = getattr(mask, "location", None)
    if (not room or room.key != LANDMARKS[site]["room"]
            or not room.tags.has("ic", category="side")):
        return None, "Visit the Northern Treeline before assessing its physical route."
    cord = next(
        (obj for obj in room.contents
         if obj.key == LANDMARKS[site]["key"]
         and getattr(obj.db, "landmark_id", None) == site
         and obj.access(mask, "view", default=True)),
        None,
    )
    if cord is None:
        return None, "The physical red cord is unavailable."
    day, hour = _day_hour()
    observed = any(e["id"] == site for e in known_landmarks(mask.db.landmark_discoveries))
    try:
        recent = dict(mask.db.landmark_latest_view or {}).get(site) or {}
        today = int(recent.get("day") or 0) == day
    except (ValueError, TypeError, OverflowError):
        today = False
    if not observed or not today:
        return None, "Examine the physical red cord here today first."
    square = _square()
    if square is None:
        return None, "The Square's existing public route board is missing."
    marked = bool(getattr(cord.db, "route_caution", None))
    current, allowed, why = route_surveys.field_decision(
        square.db.daily_route_survey, day, site, role, action,
        marked, mask.account.id, mask.key, 1,
    )
    if not allowed:
        return None, why

    def consequence(event):
        with transaction.atomic():
            if mask.location != room or cord.location != room:
                raise RuntimeError("The real observer or cord moved away.")
            now_day, now_hour = _day_hour()
            if (now_day, now_hour) != (day, hour):
                raise RuntimeError("Village time advanced before this route action.")
            now_marked = bool(getattr(cord.db, "route_caution", None))
            updated, valid, reason = route_surveys.field_decision(
                square.db.daily_route_survey, day, site, role, action,
                now_marked, mask.account.id, mask.key, event["id"],
            )
            if not valid:
                raise RuntimeError(reason)
            if action == "protect":
                # Reposition the ORIGINAL cord as a truthful visual caution,
                # no repair, consumed object, invented hazard or new material.
                cord.db.route_caution = {
                    "event_id": event["id"], "account_id": mask.account.id,
                    "mask": mask.key, "day": day,
                }
            square.db.daily_route_survey = updated
            record_participation(mask, "field_surveys", calling=role)
            return {
                "cord_object_id": cord.id, "square_room_id": square.id,
                "site": site, "day": day, "role": role, "action": action,
                "caution_marked": bool(cord.db.route_caution),
                "interpretation": (
                    updated["field_decisions"].get("wanderer") or {}
                ).get("observation"),
            }

    event = publish_world_event(
        "village.route_protected" if role == "hound"
        else "village.route_passability_observed",
        actor=mask,
        payload={"site": site, "day": day, "hour": hour,
                 "role": role, "action": action, "location": room.key,
                 "harbinger": False, "chronicle_eligible": False},
        consequence=consequence,
    )
    return {"event_id": event["id"], "role": role, "action": action}, None


def _river_context(mask):
    """Return the original river gauge after a current firsthand examination."""
    from world.discoveries import LANDMARKS, normalize as discoveries
    if not getattr(mask, "account", None):
        return None, None, None, "A logged-in player mask is required."
    site = "river_gauge"
    room = getattr(mask, "location", None)
    if (room is None or room.key != LANDMARKS[site]["room"]
            or not room.tags.has("ic", category="side")):
        return None, None, None, "Travel to Riverside Path and inspect the gauge."
    gauge = next((
        obj for obj in room.contents
        if obj.key == LANDMARKS[site]["key"]
        and getattr(obj.db, "landmark_id", None) == site
        and obj.access(mask, "view", default=True)
    ), None)
    if gauge is None:
        return None, None, None, "The original river gauge is missing."
    day, hour = _day_hour()
    try:
        recent = dict(mask.db.landmark_latest_view or {}).get(site) or {}
        seen = int(recent.get("day") or 0) == day
    except (TypeError, ValueError, OverflowError):
        seen = False
    if not seen or not any(row["id"] == site for row in discoveries(mask.db.landmark_discoveries)):
        return None, None, None, "Examine the actual river gauge here today first."
    return room, gauge, (day, hour), None


def river_status(mask):
    """Read only public source-limited evidence at the existing gauge."""
    from world import river_evidence
    room = getattr(mask, "location", None)
    if room is None or room.key != "Riverside Path":
        return "Visit the original river gauge on Riverside Path."
    gauges = [
        obj for obj in room.contents
        if obj.key == "a river gauge"
        and getattr(obj.db, "landmark_id", None) == "river_gauge"
    ]
    if len(gauges) != 1:
        return "The original river gauge cannot be uniquely verified."
    gauge = gauges[0]
    day, _hour = _day_hour()
    state = river_evidence.normalize(gauge.db.river_evidence)
    witness, review = state["witness"], state["review"]
    from world.events import get_event_ledger
    ledger = get_event_ledger()
    witness_event = (ledger.get_event(witness["event_id"]) if witness else None)
    review_event = (ledger.get_event(review["event_id"]) if review else None)
    return "\n".join(river_evidence.verified_public_lines(
        state, day, gauge_id=gauge.id, room_id=room.id,
        witness_event=witness_event, review_event=review_event,
    ))


def _verified_river_source(gauge, room, witness):
    """Check completed canonical source, not just mutable object attributes."""
    from world.events import get_event_ledger
    if not witness:
        return False
    event = get_event_ledger().get_event(witness["event_id"])
    if not event or event.get("kind") != "village.river_gauge_witnessed":
        return False
    if event.get("status") != "complete":
        return False
    actor = dict(event.get("actor") or {})
    payload = dict(event.get("payload") or {})
    consequence = dict(event.get("consequence") or {})
    return (
        type(actor.get("account_id")) is int
        and actor["account_id"] == witness["account_id"]
        and type(actor.get("mask_id")) is int
        and actor["mask_id"] == witness["mask_id"]
        and actor.get("mask") == witness["mask"]
        and payload.get("calling") == "wanderer"
        and type(payload.get("day")) is int
        and payload["day"] == witness["day"]
        and type(payload.get("hour")) is int
        and payload["hour"] == witness["hour"]
        and type(payload.get("object_id")) is int
        and payload["object_id"] == gauge.id == witness["object_id"]
        and type(payload.get("room_id")) is int
        and payload["room_id"] == room.id
        and payload.get("location") == "Riverside Path"
        and type(consequence.get("gauge_object_id")) is int
        and consequence["gauge_object_id"] == gauge.id
        and type(consequence.get("witness_event_id")) is int
        and consequence["witness_event_id"] == witness["event_id"]
        and type(consequence.get("account_id")) is int
        and consequence["account_id"] == witness["account_id"]
    )


def river_action(mask, action):
    """EDGE-37: Wanderer observes; independent Detective preserves comparison."""
    from world import river_evidence
    if action not in {"gauge", "compare"}:
        return None, "Use survey gauge (Wanderer) or survey compare (Detective)."
    role = "wanderer" if action == "gauge" else "detective"
    if active_calling(mask) != role:
        return None, f"An active {role.title()} must sign this action."
    room, gauge, stamp, error = _river_context(mask)
    if error:
        return None, error
    day, hour = stamp
    raw = gauge.db.river_evidence
    source = river_evidence.normalize(raw)["witness"]
    if action == "compare" and not _verified_river_source(gauge, room, source):
        return None, "The signed, completed Wanderer source cannot be verified."
    # Preview checks feasibility only; it does not reserve a ledger ID.
    # If the first genuine Wanderer event is ID 1, the Detective preview
    # must not reuse that signed source and reject otherwise valid gameplay.
    preview_id = source["event_id"] + 1 if action == "compare" else 1
    kwargs = dict(day=day, hour=hour, account_id=mask.account.id,
                  mask_id=mask.id, mask=mask.key, event_id=preview_id,
                  object_id=gauge.id)
    if action == "gauge":
        _candidate, ok, why = river_evidence.witness(raw, **kwargs)
    else:
        _candidate, ok, why = river_evidence.compare(
            raw, source_event_id=source["event_id"], **kwargs
        )
    if not ok:
        return None, why

    def consequence(event):
        with transaction.atomic():
            current_room, current_gauge, current_stamp, issue = _river_context(mask)
            if (issue or current_room != room or current_gauge != gauge
                    or current_stamp != stamp or active_calling(mask) != role):
                raise RuntimeError("The physical witness, Calling or village time changed.")
            actual = gauge.db.river_evidence
            fields = dict(kwargs, event_id=event["id"])
            if action == "gauge":
                changed, accepted, reason = river_evidence.witness(actual, **fields)
            else:
                actual_source = river_evidence.normalize(actual)["witness"]
                if not _verified_river_source(gauge, room, actual_source):
                    raise RuntimeError("The completed Wanderer source changed.")
                changed, accepted, reason = river_evidence.compare(
                    actual, source_event_id=actual_source["event_id"], **fields
                )
            if not accepted:
                raise RuntimeError(reason)
            gauge.db.river_evidence = changed
            record_participation(mask, "river_gauge_witnesses" if action == "gauge"
                                 else "river_evidence_comparisons", calling=role)
            return {
                "gauge_object_id": gauge.id, "room_id": room.id,
                "witness_event_id": (event["id"] if action == "gauge"
                                     else changed["witness"]["event_id"]),
                "account_id": mask.account.id,
                "review_event_id": (event["id"] if action == "compare" else None),
                "source_event_id": (changed["review"]["source_event_id"]
                                    if changed["review"] else None),
            }

    event = publish_world_event(
        "village.river_gauge_witnessed" if action == "gauge"
        else "village.river_evidence_compared",
        actor=mask,
        payload={
            "day": day, "hour": hour, "calling": role,
            "object_id": gauge.id, "room_id": room.id, "location": room.key,
            "source_event_id": source["event_id"] if action == "compare" else None,
            "harbinger": False, "chronicle_eligible": False,
        },
        consequence=consequence,
    )
    return {"event_id": event["id"], "action": action,
            "lines": river_status(mask)}, None
