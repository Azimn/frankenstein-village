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
from world.events import publish_world_event, get_event_ledger

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

def _signed_prior_caution(cord, square, marker, day):
    """Verify a completed earlier Hound event before re-tying this same cord."""
    if not hasattr(marker, "get"):
        return False
    prior_day = marker.get("day")
    event_id = marker.get("event_id")
    account_id = marker.get("account_id")
    if (any(type(v) is not int or v < 1 for v in
            (prior_day, event_id, account_id)) or prior_day >= day):
        return False
    signed = get_event_ledger().get_event(event_id)
    if not signed or signed.get("kind") != "village.route_protected" or signed.get("status") != "complete":
        return False
    actor = signed.get("actor") or {}
    payload = signed.get("payload") or {}
    effect = signed.get("consequence") or {}
    return (
        actor.get("account_id") == account_id
        and type(actor.get("mask_id")) is int and actor["mask_id"] > 0
        and payload.get("day") == prior_day
        and payload.get("site") == "red_cord"
        and payload.get("role") == "hound"
        and payload.get("action") == "protect"
        and payload.get("location") == LANDMARKS["red_cord"]["room"]
        and effect.get("cord_object_id") == cord.id
        and effect.get("square_room_id") == square.id
        and effect.get("day") == prior_day
        and effect.get("role") == "hound"
        and effect.get("action") == "protect"
        and effect.get("caution_marked") is True
    )


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
    marker = dict(getattr(cord.db, "route_caution", None) or {})
    marked = bool(marker)
    if role == "hound" and marked and not _signed_prior_caution(cord, square, marker, day):
        return None, "The older cord warning has no valid signed source or is already current."
    prior_event_id = marker.get("event_id") if role == "hound" and marked else None
    current, allowed, why = route_surveys.field_decision(
        square.db.daily_route_survey, day, site, role, action,
        marked, mask.account.id, mask.key, 1,
        caution_day=marker.get("day") if role == "hound" else None,
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
            now_marker = dict(getattr(cord.db, "route_caution", None) or {})
            now_marked = bool(now_marker)
            if action == "protect":
                if (now_marker.get("event_id") if now_marker else None) != prior_event_id:
                    raise RuntimeError("The original cord marker changed during this action.")
                if now_marked and not _signed_prior_caution(cord, square, now_marker, day):
                    raise RuntimeError("The previous cord marker is not a completed signed event.")
            updated, valid, reason = route_surveys.field_decision(
                square.db.daily_route_survey, day, site, role, action,
                now_marked, mask.account.id, mask.key, event["id"],
                caution_day=now_marker.get("day") if role == "hound" else None,
            )
            if not valid:
                raise RuntimeError(reason)
            if action == "protect":
                # Re-tighten the same cord; preserve bounded historical markers.
                if now_marker:
                    history = list(cord.db.route_caution_history or [])
                    history.append(now_marker)
                    cord.db.route_caution_history = history[-30:]
                cord.db.route_caution = {
                    "event_id": event["id"], "account_id": mask.account.id,
                    "mask": mask.key, "day": day,
                    "prior_caution_event_id": prior_event_id,
                }
            square.db.daily_route_survey = updated
            record_participation(mask, "field_surveys", calling=role)
            return {
                "cord_object_id": cord.id, "square_room_id": square.id,
                "site": site, "day": day, "role": role, "action": action,
                "caution_marked": bool(cord.db.route_caution),
                "prior_caution_event_id": prior_event_id if action == "protect" else None,
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
                 "prior_caution_event_id": prior_event_id,
                 "harbinger": False, "chronicle_eligible": False},
        consequence=consequence,
    )
    return {"event_id": event["id"], "role": role, "action": action}, None
