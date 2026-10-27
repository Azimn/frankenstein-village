"""Physical player-authored daily route surveys, using the canonical clock.

Existing object inspections and player Calling records are reused. Nothing
teleports, grants a quest reward, or publishes a claim as objective truth.
"""
from __future__ import annotations

from collections.abc import Mapping

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


def _inspected_today(mask, site, day):
    """Require a valid same-day physical inspection, even for old/corrupt saves."""
    views = getattr(mask.db, "landmark_latest_view", None)
    if not isinstance(views, Mapping):
        return False
    recent = views.get(site)
    if not isinstance(recent, Mapping):
        return False
    recorded_day = recent.get("day")
    if isinstance(recorded_day, bool):
        return False
    try:
        return int(recorded_day or 0) == day
    except (ValueError, TypeError, OverflowError):
        return False


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
    lines.append("Use |wsurvey history|n for the latest signed days, or |wsurvey history <day>|n for an older retained record.")
    # Use the same validated public projection as survey history. Old or
    # malformed persisted archive rows must not crash the daily board or
    # let a stale "completed" flag misrepresent signed checkpoint counts.
    previous = route_surveys.history_records(state, day, limit=1)
    if previous:
        prior = previous[0]
        lines.append(
            f"Previous surveyed day {prior['day']}: "
            + ("complete" if prior["completed"] else "unfinished")
            + f" ({len(prior['reports'])} of {len(route_surveys.SITES)})."
        )
    return "\n".join(lines)


def history_lines(day_filter=None):
    """Show bounded, source-attributed public route history without writing it."""
    square = _square()
    if square is None:
        return "The route report is unavailable; the Square is missing."
    day, _hour = _day_hour()
    previous = route_surveys.history_records(
        square.db.daily_route_survey, day, limit=5, selected_day=day_filter
    )
    lines = ["|wSigned village route history|n"]
    if not previous:
        if day_filter is None:
            lines.append("No earlier village day has an archived route record yet.")
        else:
            lines.append(
                f"No signed route archive is retained for village day {day_filter}. "
                "The Square preserves at most 30 previous recorded days."
            )
        return "\n".join(lines)
    for row in previous:
        lines.append(
            f"Village day {row['day']}: "
            + ("complete" if row["completed"] else "unfinished")
            + f" ({len(row['reports'])} of {len(route_surveys.SITES)} checkpoints)."
        )
        for site in route_surveys.SITES:
            report = row["reports"].get(site)
            if report:
                lines.append(
                    f"  {LANDMARKS[site]['room']}: {report['mask']} "
                    f"(signed event {report['event_id']})."
                )
        lines.extend("  " + line for line in route_surveys.field_lines(row))
    lines.append(
        "These are dated observations and signed actions, not proof of "
        "what caused a hazard or whether the route is safe today."
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
    inspected_today = _inspected_today(mask, site, day)
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
            # A report must belong to the hour and day actually witnessed.
            # Field actions already enforce this boundary; civic reports must
            # not sign a stale day if the village clock advances mid-command.
            now_day, now_hour = _day_hour()
            if (now_day, now_hour) != (day, hour):
                raise RuntimeError("Village time advanced before this route report.")
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

    try:
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
    except RuntimeError as error:
        # The canonical ledger records the rejected consequence. Show a
        # recoverable command response instead of a player-facing traceback.
        return None, str(error)
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
    today = _inspected_today(mask, site, day)
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
            # The role, firsthand inspection, and access may change between
            # the initial command checks and the signed consequence.
            if active_calling(mask) != role:
                raise RuntimeError("Your active Calling changed before the route action.")
            if not _inspected_today(mask, site, day):
                raise RuntimeError("Examine the physical red cord again before acting.")
            if not cord.access(mask, "view", default=True):
                raise RuntimeError("The physical red cord is no longer available.")
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

    try:
        event = publish_world_event(
            "village.route_protected" if role == "hound"
            else "village.route_passability_observed",
            actor=mask,
            payload={"site": site, "day": day, "hour": hour,
                     "role": role, "action": action, "location": room.key,
                     "harbinger": False, "chronicle_eligible": False},
            consequence=consequence,
        )
    except RuntimeError as error:
        # A competing player or advancing village clock can invalidate the
        # physical action after preflight. The ledger records the rejection;
        # give the player a recoverable message, never a server traceback.
        return None, str(error)
    return {"event_id": event["id"], "role": role, "action": action}, None
