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
    ledger = get_event_ledger()
    # A normalized board claim alone is not a completed route recheck. The
    # current physical cord and all three original ledger events must agree.
    public_field_state = state
    entries = state["field_decisions"]
    joint = (entries.get("wanderer") or {}).get("corroboration")
    if joint:
        cord = next((
            obj for obj in search.search_object(LANDMARKS["red_cord"]["key"])
            if getattr(getattr(obj, "location", None), "key", None)
            == LANDMARKS["red_cord"]["room"]
            and getattr(obj.db, "landmark_id", None) == "red_cord"
        ), None)
        hound = entries.get("hound") or {}
        wanderer = entries.get("wanderer") or {}
        signed = bool(cord) and route_surveys.verify_signed_corroboration(
            state, ledger.get_event(joint["event_id"]),
            ledger.get_event(hound.get("event_id")),
            ledger.get_event(wanderer.get("event_id")),
            day=day, hour=_hour, cord_id=cord.id, square_id=square.id,
            marker=_caution_marker(getattr(cord.db, "route_caution", None)),
        )
        if not signed:
            public_entries = dict(entries)
            public_wanderer = dict(wanderer)
            public_wanderer.pop("corroboration", None)
            public_entries["wanderer"] = public_wanderer
            public_field_state = dict(state, field_decisions=public_entries)
            lines.append("The stored route corroboration is unverified; no signed recheck is displayed.")
    # A mutable Square projection cannot authenticate a caution notice.
    if state.get("caution_notice") and not _verified_notice(square, state, day):
        public_field_state = dict(public_field_state, caution_notice=None)
        lines.append("The stored Chronicler caution is unverified; no signed notice is displayed.")
    # A forged Square attribution cannot be displayed as signed Hound work.
    if entries.get("hound") and not _signed_hound_source(square, day, _hour):
        public_entries = dict(public_field_state["field_decisions"])
        public_entries.pop("hound", None)
        if "wanderer" in public_entries:
            independent = dict(public_entries["wanderer"])
            independent.pop("corroboration", None)
            public_entries["wanderer"] = independent
        public_field_state = dict(public_field_state, field_decisions=public_entries,
                                  caution_notice=None)
        lines.append("The stored Hound attribution is unverified; no signed Hound warning is displayed.")
    lines.extend(route_surveys.field_lines(public_field_state))
    # Persisted advisory text is not proof that a Chronicler event completed.
    public_state = state
    item = state.get("advisory")
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
        "After both signed actions, the original Wanderer may examine the "
        "cord again and use |wsurvey corroborate|n for an independent check. "
        "Neither action proves why the cord was damaged."
    )
    lines.append("Chroniclers: examine the physical cord after a signed Hound protection, return to the Square, and use |wsurvey caution|n to publish a qualified, source-linked notice.")
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
    original_account_id = mask.account.id

    def consequence(event):
        with transaction.atomic():
            account = getattr(mask, "account", None)
            if (mask.location != room or clue.location != room
                    or account is None or account.id != original_account_id):
                raise RuntimeError("The observer changed account or left the actual landmark.")
            if (getattr(clue.db, "landmark_id", None) != site
                    or not clue.access(mask, "view", default=True)):
                raise RuntimeError("The physical inspected landmark changed.")
            if _day_hour() != (day, hour):
                raise RuntimeError("Village time advanced before the report.")
            current_known = any(row["id"] == site for row in
                                known_landmarks(mask.db.landmark_discoveries))
            try:
                current_latest = dict(mask.db.landmark_latest_view or {}).get(site) or {}
                current_inspected = int(current_latest.get("day") or 0) == day
            except (TypeError, ValueError, OverflowError):
                current_inspected = False
            if not current_known or not current_inspected:
                raise RuntimeError("The firsthand physical inspection changed.")
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
        ("hound", "protect"), ("wanderer", "passability"),
        ("wanderer", "corroborate")
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
    if action == "corroborate":
        return _corroborate(mask, room, cord, square, day, hour)
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
            if (account is None or account.id != original_account_id
                    or active_calling(mask) != role):
                raise RuntimeError("The professional changed account or Calling.")
            if mask.location != room or cord.location != room:
                raise RuntimeError("The real observer or cord moved away.")
            if (getattr(cord.db, "landmark_id", None) != site
                    or not cord.access(mask, "view", default=True)):
                raise RuntimeError("The inspected physical cord changed.")
            current_known = any(row["id"] == site for row in
                                known_landmarks(mask.db.landmark_discoveries))
            try:
                current_latest = dict(mask.db.landmark_latest_view or {}).get(site) or {}
                current_inspected = int(current_latest.get("day") or 0) == day
            except (TypeError, ValueError, OverflowError):
                current_inspected = False
            if not current_known or not current_inspected:
                raise RuntimeError("The professional's physical inspection changed.")
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


def _corroboration_sources(square, cord, day, hour):
    """Validate both completed events and the same actual marked object."""
    state = route_surveys.refresh(square.db.daily_route_survey, day)
    entries = state["field_decisions"]
    hound, wanderer = entries.get("hound"), entries.get("wanderer")
    if not hound or not wanderer:
        return None, "Both independent professional field records are required."
    marker = _caution_marker(getattr(cord.db, "route_caution", None))
    if marker is None:
        return None, "The physical cord warning record is malformed."
    if not route_surveys.verify_caution_marker(marker, hound, day):
        return None, "The current physical warning has no matching Hound source today."
    if hound["account_id"] == wanderer["account_id"]:
        return None, "Two separate ordinary accounts must contribute."
    ledger = get_event_ledger()
    for role, entry in (("hound", hound), ("wanderer", wanderer)):
        signed = ledger.get_event(entry["event_id"])
        if not route_surveys.verify_signed_field_source(
            signed, entry, role, day, hour, cord.id, square.id
        ):
            return None, "A completed independent field source could not be verified."
    return state, None


def _corroborate(mask, room, cord, square, day, hour):
    """A later firsthand Wanderer check, bound to signed Hound protection."""
    state, problem = _corroboration_sources(square, cord, day, hour)
    if problem:
        return None, problem
    hound = state["field_decisions"]["hound"]
    proposed, ok, reason = route_surveys.corroborate(
        state, day, "red_cord", hound["event_id"],
        mask.account.id, mask.key,
        max(hound["event_id"], state["field_decisions"]["wanderer"]["event_id"]) + 1,
    )
    if not ok:
        return None, reason

    def consequence(event):
        with transaction.atomic():
            if mask.location != room or cord.location != room:
                raise RuntimeError("The firsthand observer left the physical cord.")
            if active_calling(mask) != "wanderer":
                raise RuntimeError("The observer is no longer a Wanderer.")
            if _day_hour() != (day, hour):
                raise RuntimeError("Village time changed during corroboration.")
            recent = dict(mask.db.landmark_latest_view or {}).get("red_cord") or {}
            if int(recent.get("day") or 0) != day:
                raise RuntimeError("The Wanderer did not inspect the cord today.")
            latest, source_error = _corroboration_sources(square, cord, day, hour)
            if source_error:
                raise RuntimeError(source_error)
            hound_entry = latest["field_decisions"]["hound"]
            updated, valid, failure = route_surveys.corroborate(
                latest, day, "red_cord", hound_entry["event_id"],
                mask.account.id, mask.key, event["id"],
            )
            if not valid:
                raise RuntimeError(failure)
            square.db.daily_route_survey = updated
            record_participation(mask, "field_corroborations", calling="wanderer")
            return {
                "site": "red_cord", "day": day,
                "role": "wanderer", "action": "corroborate",
                "cord_object_id": cord.id, "square_room_id": square.id,
                "hound_source_event_id": hound_entry["event_id"],
                "wanderer_source_event_id": latest["field_decisions"]["wanderer"]["event_id"],
                "physical_caution_present": True,
            }

    event = publish_world_event(
        "village.route_caution_corroborated", actor=mask,
        payload={
            "site": "red_cord", "day": day, "hour": hour,
            "role": "wanderer", "action": "corroborate",
            "location": room.key, "cord_object_id": cord.id,
            "hound_source_event_id": hound["event_id"],
            "wanderer_source_event_id": state["field_decisions"]["wanderer"]["event_id"],
            "harbinger": False, "chronicle_eligible": False,
        },
        consequence=consequence,
    )
    return {"event_id": event["id"], "hound_source_event_id": hound["event_id"]}, None


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


def _chronicler_inspected_source(mask, day, source):
    """Require a physical look at this particular signed Hound marker.

    Whole-hour timestamps cannot order two actions within an hour.
    The private inspection stamp must identify the source event actually
    present on the original cord when the Chronicler looked.
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
            and source["source_hour"] <= observed_hour <= 23
            and type(latest.get("route_caution_event_id")) is int
            and latest["route_caution_event_id"] == source["source_event_id"]
            and type(latest.get("route_caution_cord_id")) is int
            and latest["route_caution_cord_id"] == source["source_cord_id"])


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
    if not _chronicler_inspected_source(mask, day, source):
        return None, ("Examine the real red cord at Northern Treeline today "
                      "and return to the Square before publishing.")
    original_account = account.id
    base = {"day": day, "hour": hour, "account_id": original_account,
            "mask_id": mask.id, "mask": mask.key, **source}
    _state, accepted, reason = route_surveys.publish_caution(
        square.db.daily_route_survey, event_id=source["source_event_id"] + 1, **base)
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
            if not _chronicler_inspected_source(mask, day, source):
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
