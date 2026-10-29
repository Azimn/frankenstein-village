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
from world.events import get_event_ledger, publish_world_event

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
    # Persisted advisory text is not proof that a Chronicler event completed.
    public_state = state
    item = state.get("advisory")
    ledger = get_event_ledger()
    if item and not route_surveys.verified_advisory_publication(
        state, ledger.get_event(item["event_id"]), square_id=square.id,
    ):
        public_state = dict(state, advisory=None)
        lines.append("The stored route map edition is unverified; no signed edition is displayed.")
    lines.extend(route_surveys.advisory_lines(public_state))
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
        archived = prior.get("advisory")
        if archived:
            historical = {
                "day": prior["day"], "reports": prior.get("reports") or {},
                "field_decisions": prior.get("field_decisions") or {},
                "advisory": archived, "history": [],
            }
            signed = route_surveys.verified_advisory_publication(
                historical, ledger.get_event(archived.get("event_id")),
                square_id=square.id,
            ) if hasattr(archived, "get") else False
            lines.append(
                "The prior day's signed route map is archived, not a live forecast."
                if signed else "The prior day's stored map is unverified, not a signed edition."
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


def publish_advisory(mask):
    """Chronicler publishes a dated map from an independent Wanderer source.

    Publication changes the same public Square route record, not physical
    road conditions. The source event must exist and be complete in the
    canonical ledger; role labels or unverified prose cannot forge a map.
    """
    if not getattr(mask, "account", None):
        return None, "An ordinary logged-in player mask is required."
    if active_calling(mask) != "chronicler":
        return None, "Only an active Chronicler may edit a route map."
    square = _square()
    if square is None:
        return None, "The Square's public route board is missing."
    if mask.location != square or not square.tags.has("ic", category="side"):
        return None, "Visit the Village Square to publish at the public route board."
    day, hour = _day_hour()
    state = route_surveys.refresh(square.db.daily_route_survey, day)
    if state["day"] > day:
        return None, "A later village day is already recorded."
    source = state["field_decisions"].get("wanderer")
    if not source:
        return None, "A Wanderer's signed firsthand route observation is required."

    def valid_source():
        event = get_event_ledger().get_event(source["event_id"])
        if not event or event.get("status") != "complete":
            return False
        if event.get("kind") != "village.route_passability_observed":
            return False
        payload, actor = event.get("payload") or {}, event.get("actor") or {}
        return (payload.get("site") == "red_cord"
                and payload.get("day") == day
                and actor.get("account_id") == source["account_id"])

    if not valid_source():
        return None, "The Wanderer's canonical signed source could not be verified."
    # This preflight does not allocate a ledger event. ID 1 is not a
    # safe placeholder: the first legitimate Wanderer event may itself
    # be event 1, and a publication must have a distinct event ID.
    preview_event_id = source["event_id"] + 1
    _candidate, allowed, reason = route_surveys.publish_advisory(
        state, day, mask.account.id, mask.key,
        preview_event_id, source["event_id"],
    )
    if not allowed:
        return None, reason

    def consequence(event):
        with transaction.atomic():
            now_day, now_hour = _day_hour()
            if ((now_day, now_hour) != (day, hour) or mask.location != square
                    or active_calling(mask) != "chronicler"):
                raise RuntimeError("The publisher moved, changed Calling, or the village clock advanced.")
            if not valid_source():
                raise RuntimeError("The original Wanderer source is no longer valid.")
            changed, accepted, error = route_surveys.publish_advisory(
                square.db.daily_route_survey, day, mask.account.id,
                mask.key, event["id"], source["event_id"],
            )
            if not accepted:
                raise RuntimeError(error)
            square.db.daily_route_survey = changed
            record_participation(mask, "route_advisories", calling="chronicler")
            return {
                "day": day, "version": 1, "square_room_id": square.id,
                "source_event_id": source["event_id"],
                "source_account_id": source["account_id"],
                "observation": source["observation"],
            }

    event = publish_world_event(
        "village.route_map_published",
        actor=mask,
        payload={
            "site": "red_cord", "day": day, "hour": hour,
            "version": 1, "source_event_id": source["event_id"],
            "source_account_id": source["account_id"],
            "harbinger": False, "chronicle_eligible": False,
        },
        consequence=consequence,
    )
    return {"event_id": event["id"], "source_event_id": source["event_id"],
            "version": 1, "day": day}, None
