"""Physical player-authored daily route surveys, using the canonical clock.

Existing object inspections and player Calling records are reused. Nothing
teleports, grants a quest reward, or publishes a claim as objective truth.
"""
from __future__ import annotations

from collections.abc import Mapping, Sequence

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
    # The public Hound attribution must also be tied to the signed physical
    # source. A damaged Square label is not independent eyewitness evidence.
    if (state["field_decisions"].get("hound")
            and not _signed_hound_source(square, day, 23)):
        state["field_decisions"].pop("hound", None)
        state["caution_notice"] = None
    # Never expose an unsupported publication as a verified public notice.
    if state.get('caution_notice') and not _verified_notice(square, state, day):
        state['caution_notice'] = None
    lines.extend(route_surveys.field_lines(state))
    lines.append(
        "At the Northern Treeline, an active Hound can examine the actual "
        "frayed red cord and use |wsurvey protect|n to tie a visible warning. "
        "An active Wanderer can independently use |wsurvey passability|n "
        "there to record whether the warning was present when inspected. "
        "Neither action proves why the cord was damaged."
    )
    lines.append("Chroniclers: after a Hound protects the real treeline cord, "
                 "examine that physical cord at Northern Treeline today, "
                 "then return to this Square board and use survey caution "
                 "to publish one source-linked warning. This does not prove a threat.")
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
    original_account_id = mask.account.id

    def consequence(event):
        with transaction.atomic():
            account = getattr(mask, "account", None)
            if (mask.location != room or clue.location != room
                    or account is None or account.id != original_account_id):
                raise RuntimeError("The observer changed account or left the actual landmark.")
            if (getattr(clue.db, "landmark_id", None) != site
                    or not clue.access(mask, "view", default=True)):
                raise RuntimeError("The inspected physical landmark changed.")
            if _day_hour() != (day, hour):
                raise RuntimeError("Village time advanced before the route report.")
            still_known = any(
                row["id"] == site
                for row in known_landmarks(mask.db.landmark_discoveries)
            )
            try:
                latest = dict(mask.db.landmark_latest_view or {}).get(site) or {}
                still_inspected = int(latest.get("day") or 0) == day
            except (ValueError, TypeError, OverflowError):
                still_inspected = False
            if not still_known or not still_inspected:
                raise RuntimeError("The observer's current physical inspection is no longer valid.")
            changed, accepted, error = route_surveys.report(
                square.db.daily_route_survey, day, site,
                original_account_id, mask.key, event["id"],
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

def _caution_marker(raw):
    """Read a persisted physical marker without coercing corrupt values.

    None is an unmarked cord. Other non-mappings are not empty evidence and
    must never be silently replaced with an unmarked state.
    """
    if raw is None:
        return {}
    return dict(raw) if isinstance(raw, Mapping) else None


def _signed_prior_caution(cord, square, marker, day):
    """Verify a completed earlier Hound event before re-tying this same cord."""
    if not isinstance(marker, Mapping):
        return False
    prior_day = marker.get("day")
    event_id = marker.get("event_id")
    account_id = marker.get("account_id")
    if (any(type(v) is not int or v < 1 for v in
            (prior_day, event_id, account_id)) or prior_day >= day):
        return False
    signed = get_event_ledger().get_event(event_id)
    if (not isinstance(signed, Mapping) or signed.get("kind") != "village.route_protected"
            or signed.get("status") != "complete"):
        return False
    actor = signed.get("actor")
    payload = signed.get("payload")
    effect = signed.get("consequence")
    if not all(isinstance(value, Mapping) for value in (actor, payload, effect)):
        return False
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
    marker = _caution_marker(getattr(cord.db, "route_caution", None))
    if marker is None:
        return None, "The physical cord warning record is malformed; ask a keeper to inspect it."
    marked = bool(marker)
    if (role == "hound" and marked and marker.get("day") != day
            and not _signed_prior_caution(cord, square, marker, day)):
        return None, "The older cord warning has no valid signed source or is already current."
    prior_event_id = marker.get("event_id") if role == "hound" and marked else None
    original_account_id = mask.account.id
    current, allowed, why = route_surveys.field_decision(
        square.db.daily_route_survey, day, site, role, action,
        marked, mask.account.id, mask.key, 1,
        caution_day=marker.get("day") if role == "hound" else None,
    )
    if not allowed:
        return None, why

    def consequence(event):
        with transaction.atomic():
            account = getattr(mask, "account", None)
            if (mask.location != room or cord.location != room
                    or account is None or account.id != original_account_id
                    or active_calling(mask) != role):
                raise RuntimeError("The route observer changed account, Calling or location.")
            now_day, now_hour = _day_hour()
            if (now_day, now_hour) != (day, hour):
                raise RuntimeError("Village time advanced before this route action.")
            now_marker = _caution_marker(getattr(cord.db, "route_caution", None))
            if now_marker is None:
                raise RuntimeError("The physical cord warning record became malformed.")
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
                    raw_history = cord.db.route_caution_history
                    if raw_history is None:
                        history = []
                    elif (isinstance(raw_history, Sequence)
                          and not isinstance(raw_history, (str, bytes, bytearray))
                          and all(isinstance(item, Mapping) for item in raw_history)):
                        history = list(raw_history)
                    else:
                        raise RuntimeError("The physical cord caution history is malformed.")
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

def _signed_hound_source(square, day, hour):
    """Return only a current, physical, completed Hound source."""
    state = route_surveys.refresh(square.db.daily_route_survey, day)
    if state["day"] != day:
        return None
    source = state["field_decisions"].get("hound")
    if not isinstance(source, Mapping):
        return None
    spec = LANDMARKS["red_cord"]
    rooms = [room for room in search.search_object(spec["room"])
             if room.key == spec["room"] and room.location is None]
    if len(rooms) != 1:
        return None
    cord = next((obj for obj in rooms[0].contents
                 if obj.key == spec["key"]
                 and getattr(obj.db, "landmark_id", None) == "red_cord"), None)
    if cord is None:
        return None
    marker = getattr(cord.db, "route_caution", None)
    if not isinstance(marker, Mapping):
        return None
    source_id = source.get("event_id")
    account_id = source.get("account_id")
    if (marker.get("event_id") != source_id
            or marker.get("account_id") != account_id
            or marker.get("day") != day):
        return None
    signed = get_event_ledger().get_event(source_id)
    if (not isinstance(signed, Mapping)
            or signed.get("id") != source_id
            or signed.get("status") != "complete"
            or signed.get("kind") != "village.route_protected"):
        return None
    actor, payload, effect = (
        signed.get("actor"), signed.get("payload"), signed.get("consequence"))
    if not all(isinstance(item, Mapping) for item in (actor, payload, effect)):
        return None
    source_hour = payload.get("hour")
    # Public attribution is a signed fact, not an editable Square label.
    # Compare the historical name captured by the event, not the mask's
    # potentially renamed current key.
    if (not isinstance(actor.get("mask"), str)
            or source.get("mask") != actor["mask"][:70]):
        return None
    if (not isinstance(source_hour, int) or isinstance(source_hour, bool)
            or not 0 <= source_hour <= hour <= 23
            or actor.get("account_id") != account_id
            or not route_surveys._positive(actor.get("mask_id"))
            or payload.get("day") != day
            or payload.get("site") != "red_cord"
            or payload.get("role") != "hound"
            or payload.get("action") != "protect"
            or payload.get("location") != spec["room"]
            or effect.get("cord_object_id") != cord.id
            or effect.get("square_room_id") != square.id
            or effect.get("site") != "red_cord"
            or effect.get("day") != day
            or effect.get("role") != "hound"
            or effect.get("action") != "protect"
            or effect.get("caution_marked") is not True):
        return None
    return {
        "source_event_id": source_id,
        "source_account_id": account_id,
        "source_mask_id": actor["mask_id"],
        "source_cord_id": cord.id,
        "source_hour": source_hour,
    }


def _verified_notice(square, state, day):
    notice = state.get("caution_notice")
    if not notice:
        return False
    source = _signed_hound_source(square, day, 23)
    if not source or any(notice.get(k) != v for k, v in source.items()):
        return False
    signed = get_event_ledger().get_event(notice["event_id"])
    if (not isinstance(signed, Mapping)
            or signed.get("id") != notice["event_id"]
            or signed.get("status") != "complete"
            or signed.get("kind") != "village.route_caution_published"):
        return False
    actor, payload, effect = (
        signed.get("actor"), signed.get("payload"), signed.get("consequence"))
    if not all(isinstance(v, Mapping) for v in (actor, payload, effect)):
        return False
    return (
        actor.get("account_id") == notice["account_id"]
        and actor.get("mask_id") == notice["mask_id"]
        and isinstance(actor.get("mask"), str)
        and actor["mask"][:70] == notice["mask"]
        and payload.get("day") == day
        and payload.get("hour") == notice["hour"]
        and payload.get("source_event_id") == notice["source_event_id"]
        and effect.get("square_room_id") == square.id
        and effect.get("source_event_id") == notice["source_event_id"]
        and effect.get("publication_event_id") == notice["event_id"]
    )


def _chronicler_inspected_source(mask, day, source_hour):
    """Require an independent, same-day physical cord inspection.

    The landmark clock records whole hours, so same-hour inspections cannot
    establish an ordering within that hour. This proves firsthand access,
    not that the Chronicler independently verified an unseen threat.
    """
    db = getattr(mask, "db", None)
    if db is None:
        return False
    if not any(row["id"] == "red_cord" for row in
               known_landmarks(getattr(db, "landmark_discoveries", None))):
        return False
    try:
        latest = dict(getattr(db, "landmark_latest_view", None) or {}).get("red_cord")
    except (TypeError, ValueError, AttributeError):
        return False
    if not isinstance(latest, Mapping):
        return False
    observed_day, observed_hour = latest.get("day"), latest.get("hour")
    return (type(observed_day) is int and observed_day == day
            and type(observed_hour) is int
            and source_hour <= observed_hour <= 23)


def publish_caution(mask):
    """Chronicler publishes a bounded public warning after a Hound's act."""
    account = getattr(mask, "account", None)
    if account is None or active_calling(mask) != "chronicler":
        return None, "An authenticated Chronicler is required."
    square = _square()
    if square is None or mask.location != square:
        return None, "Visit the Village Square route board."
    day, hour = _day_hour()
    source = _signed_hound_source(square, day, hour)
    if not source:
        return None, "A completed Hound protection of the real cord is required today."
    if not _chronicler_inspected_source(mask, day, source["source_hour"]):
        return None, ("Examine the real red cord at Northern Treeline today "
                      "and return to the Square before publishing.")
    original_account = account.id
    base = {"day": day, "hour": hour, "account_id": original_account,
            "mask_id": mask.id, "mask": mask.key, **source}
    _state, accepted, reason = route_surveys.publish_caution(
        square.db.daily_route_survey, event_id=1, **base)
    if not accepted:
        return None, reason

    def consequence(event):
        with transaction.atomic():
            current_account = getattr(mask, "account", None)
            if (mask.location != square or current_account is None
                    or current_account.id != original_account
                    or active_calling(mask) != "chronicler"):
                raise RuntimeError("The Chronicler changed account, Calling or location.")
            try:
                connected = bool(current_account.sessions.all())
            except (AttributeError, TypeError):
                connected = False
            if not connected:
                raise RuntimeError("The Chronicler disconnected before publication.")
            if _day_hour() != (day, hour):
                raise RuntimeError("Village time changed before publication.")
            if not _chronicler_inspected_source(mask, day, source["source_hour"]):
                raise RuntimeError("The Chronicler's firsthand cord inspection changed.")
            if _signed_hound_source(square, day, hour) != source:
                raise RuntimeError("The physical Hound source changed.")
            updated, ok, why = route_surveys.publish_caution(
                square.db.daily_route_survey, event_id=event["id"], **base)
            if not ok:
                raise RuntimeError(why)
            square.db.daily_route_survey = updated
            return {"square_room_id": square.id, "day": day, "hour": hour,
                    "source_event_id": source["source_event_id"],
                    "publication_event_id": event["id"]}
    event = publish_world_event(
        "village.route_caution_published", actor=mask,
        payload={"day": day, "hour": hour,
                 "source_event_id": source["source_event_id"],
                 "harbinger": False, "chronicle_eligible": False},
        consequence=consequence,
    )
    record_participation(mask, "route_caution_publication", calling="chronicler")
    return {"event_id": event["id"], "source_event_id": source["source_event_id"]}, None
