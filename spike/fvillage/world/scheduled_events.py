"""Recurring village calendar events.

Scheduled events create predictable rhythm. They are not quests and they do not
require player acceptance. The village clock is the only scheduler; this module
provides persistent idempotence, active-state tracking, bounded history, and
event-specific start/end behavior.
"""

from __future__ import annotations

import copy

from evennia import create_script
from evennia.scripts.models import ScriptDB
from evennia.utils import search


REGISTRY_KEY = "scheduled_event_registry"

MARKET_MORNING_ID = "SCHEDULED-MARKET-MORNING"
HARBINGER_PUBLICATION_ID = "SCHEDULED-HARBINGER-PUBLICATION"
SUNDAY_SERVICE_ID = "SCHEDULED-SUNDAY-SERVICE"

DAY_NAMES = (
    "Sunday",
    "Monday",
    "Tuesday",
    "Wednesday",
    "Thursday",
    "Friday",
    "Saturday",
)

DEFINITIONS = {
    MARKET_MORNING_ID: {
        "title": "Market Morning",
        "kind": "window",
        "start_hour": 7,
        "end_hour": 12,
        "weekday": "Saturday",
        "location": "Village Square",
        "public_schedule": "Saturday, 07:00 to 12:00",
    },
    HARBINGER_PUBLICATION_ID: {
        "title": "Harbinger Publication",
        "kind": "pulse",
        "start_hour": 8,
        "weekday": None,
        "location": None,
        "public_schedule": "daily at 08:00",
    },
    SUNDAY_SERVICE_ID: {
        "title": "Sunday Service",
        "kind": "window",
        "start_hour": 10,
        "end_hour": 11,
        "weekday": "Sunday",
        "location": "St. Lazarus Church",
        "public_schedule": "Sunday, 10:00 to 11:00",
    },
}


def day_name(day):
    return DAY_NAMES[(int(day) - 1) % 7]


def _registry():
    try:
        return ScriptDB.objects.get(db_key=REGISTRY_KEY)
    except ScriptDB.DoesNotExist:
        return create_script(
            "typeclasses.scripts.ScheduledEventRegistry",
            key=REGISTRY_KEY,
            persistent=True,
        )


def get_scheduled_event_registry():
    return _registry()


def _empty_event(stable_id):
    return {
        "id": stable_id,
        "state": "idle",
        "run_count": 0,
        "last_start_key": None,
        "current": None,
        "history": [],
    }


def _save(event):
    registry = _registry()
    events = copy.deepcopy(dict(registry.db.events or {}))
    events[event["id"]] = copy.deepcopy(event)
    registry.db.events = events
    return copy.deepcopy(event)


def _metrics(**deltas):
    registry = _registry()
    metrics = copy.deepcopy(dict(registry.db.metrics or {}))
    for key, value in deltas.items():
        metrics[key] = int(metrics.get(key) or 0) + int(value)
    registry.db.metrics = metrics


def _room(key):
    if not key:
        return None
    found = [obj for obj in search.search_object(key) if obj.key == key]
    return found[0] if found else None


def set_room_overlay(room_key, stable_id, text):
    room = _room(room_key)
    if not room:
        return False
    overlays = copy.deepcopy(dict(room.db.scheduled_overlays or {}))
    overlays[stable_id] = str(text)
    room.db.scheduled_overlays = overlays
    return True


def clear_room_overlay(room_key, stable_id):
    room = _room(room_key)
    if not room:
        return False
    overlays = copy.deepcopy(dict(room.db.scheduled_overlays or {}))
    changed = stable_id in overlays
    overlays.pop(stable_id, None)
    room.db.scheduled_overlays = overlays
    return changed


def _schedule_matches(definition, day, hour):
    if int(hour) != int(definition["start_hour"]):
        return False
    weekday = definition.get("weekday")
    return weekday is None or day_name(day) == weekday


def _archive(event, record):
    history = copy.deepcopy(list(event.get("history") or []))
    history.append(copy.deepcopy(record))
    event["history"] = history[-16:]
    return event


def _market_participant_ids():
    from world.residents import all_residents, resident_definition

    exact_roles = {
        "flower seller",
        "bread seller",
        "butcher",
        "butcher assistant",
        "farmer",
        "herbwife",
        "seamstress",
        "carpenter",
        "well keeper",
    }
    participants = []
    for npc in all_residents():
        definition = resident_definition(npc)
        if not definition or definition.get("schedule_engine") != "population":
            continue
        if str(definition.get("occupation") or "").lower() in exact_roles:
            participants.append(npc.db.resident_id)
    return sorted(set(participants))


def _start_market(day, hour):
    from world.residents import (
        all_residents,
        advance_population,
        set_resident_deviation,
    )

    participant_ids = set(_market_participant_ids())
    for npc in all_residents():
        if npc.db.resident_id not in participant_ids:
            continue
        set_resident_deviation(
            npc,
            "square",
            until_day=int(day),
            until_hour=12,
            reason="Saturday market morning",
        )
    advance_population(day=int(day), hour=int(hour), emit=True)

    set_room_overlay(
        "Village Square",
        MARKET_MORNING_ID,
        (
            "Market morning fills the square. Cloth awnings and handcarts break "
            "the open cobbles into narrow aisles; bread, flowers, herbs, meat, "
            "mending, and farm goods trade hands beneath the gas standards."
        ),
    )
    square = _room("Village Square")
    if square:
        square.msg_contents(
            "Market morning opens across the square as carts, baskets, and folding "
            "stalls take their familiar places."
        )
    return {
        "participant_ids": sorted(participant_ids),
        "participant_count": len(participant_ids),
    }


def _end_market(day, hour, current):
    from world.residents import advance_population

    clear_room_overlay("Village Square", MARKET_MORNING_ID)
    advance_population(day=int(day), hour=int(hour), emit=True)
    square = _room("Village Square")
    if square:
        square.msg_contents(
            "The market folds itself away. Awnings come down, carts roll out, "
            "and the square returns to ordinary traffic."
        )
    return {
        "participant_count": len(current.get("result", {}).get("participant_ids") or []),
    }


def _start_sunday_service(day, hour):
    from world.routines import hold_mass

    set_room_overlay(
        "St. Lazarus Church",
        SUNDAY_SERVICE_ID,
        (
            "Sunday Mass is underway. The pews are fuller than on an ordinary "
            "morning; candle smoke hangs above bowed heads while Father Andrei "
            "keeps the service moving at the altar."
        ),
    )
    attendee_count = hold_mass(int(day))
    return {"attendee_count": int(attendee_count)}


def _end_sunday_service(day, hour, current):
    from world.residents import advance_population
    from world.routines import advance

    clear_room_overlay("St. Lazarus Church", SUNDAY_SERVICE_ID)
    advance(hour=int(hour), day=int(day))
    advance_population(day=int(day), hour=int(hour), emit=True)
    church = _room("St. Lazarus Church")
    if church:
        church.msg_contents(
            "The service releases into murmured greetings and the scrape of pews. "
            "People begin returning to the rest of their Sunday."
        )
    return {"attendee_count": current.get("result", {}).get("attendee_count", 0)}


def _pulse_harbinger(day, hour):
    from world.publications import publish_due_harbinger

    edition = publish_due_harbinger(int(day), int(hour))
    if edition:
        for room_key in ("Village Square", "The Blood of the Vine"):
            room = _room(room_key)
            if not room:
                continue
            if any(
                obj.has_account and obj.is_connected
                for obj in room.contents
            ):
                room.msg_contents(
                    "A newspaper runner calls out the new issue of The Harbinger."
                )
    return {
        "published": bool(edition),
        "edition_id": edition.get("id") if edition else None,
        "story_count": len(edition.get("story_ids") or []) if edition else 0,
    }


def _start_behavior(stable_id, day, hour):
    if stable_id == MARKET_MORNING_ID:
        return _start_market(day, hour)
    if stable_id == SUNDAY_SERVICE_ID:
        return _start_sunday_service(day, hour)
    if stable_id == HARBINGER_PUBLICATION_ID:
        return _pulse_harbinger(day, hour)
    return {}


def _end_behavior(stable_id, day, hour, current):
    if stable_id == MARKET_MORNING_ID:
        return _end_market(day, hour, current)
    if stable_id == SUNDAY_SERVICE_ID:
        return _end_sunday_service(day, hour, current)
    return {}


def _start_event(event, definition, day, hour):
    start_key = f"{int(day)}:{int(hour)}"
    if event.get("last_start_key") == start_key:
        return event, False, False

    run_count = int(event.get("run_count") or 0) + 1
    result = _start_behavior(event["id"], int(day), int(hour))
    record = {
        "run": run_count,
        "started_day": int(day),
        "started_hour": int(hour),
        "ended_day": None,
        "ended_hour": None,
        "result": copy.deepcopy(result or {}),
        "end_result": {},
    }
    event["run_count"] = run_count
    event["last_start_key"] = start_key

    if definition["kind"] == "pulse":
        record["ended_day"] = int(day)
        record["ended_hour"] = int(hour)
        event["state"] = "idle"
        event["current"] = None
        _archive(event, record)
        return event, True, True

    event["state"] = "active"
    event["current"] = record
    return event, True, False


def _end_due(event, definition, day, hour):
    if event.get("state") != "active" or not event.get("current"):
        return event, False
    current = copy.deepcopy(dict(event["current"]))
    due = (
        int(current["started_day"]),
        int(definition["end_hour"]),
    )
    if (int(day), int(hour)) < due:
        return event, False

    end_result = _end_behavior(event["id"], int(day), int(hour), current)
    current["ended_day"] = int(day)
    current["ended_hour"] = int(hour)
    current["end_result"] = copy.deepcopy(end_result or {})
    event["state"] = "idle"
    event["current"] = None
    _archive(event, current)
    return event, True


def ensure_scheduled_events():
    registry = _registry()
    events = copy.deepcopy(dict(registry.db.events or {}))
    created = 0
    for stable_id in DEFINITIONS:
        if stable_id not in events:
            events[stable_id] = _empty_event(stable_id)
            created += 1
    registry.db.events = events
    reconcile_scheduled_overlays()
    return {"created": created, "count": len(events)}


def reconcile_scheduled_overlays():
    events = copy.deepcopy(dict(_registry().db.events or {}))
    for stable_id, raw in events.items():
        event = dict(raw)
        if event.get("state") != "active":
            continue
        if stable_id == MARKET_MORNING_ID:
            set_room_overlay(
                "Village Square",
                stable_id,
                (
                    "Market morning fills the square. Cloth awnings and handcarts "
                    "turn the cobbles into narrow aisles of ordinary trade."
                ),
            )
        elif stable_id == SUNDAY_SERVICE_ID:
            set_room_overlay(
                "St. Lazarus Church",
                stable_id,
                "Sunday Mass is underway; the pews are full and the altar candles burn.",
            )


def advance_scheduled_events(*, day, hour):
    """Advance recurring events at one authoritative village-clock boundary."""
    registry = _registry()
    events = copy.deepcopy(dict(registry.db.events or {}))
    started = []
    ended = []
    pulsed = []

    for stable_id, definition in DEFINITIONS.items():
        event = dict(events.get(stable_id) or _empty_event(stable_id))
        event, did_end = _end_due(event, definition, int(day), int(hour))
        if did_end:
            ended.append(stable_id)

        if _schedule_matches(definition, int(day), int(hour)):
            event, did_start, was_pulse = _start_event(
                event,
                definition,
                int(day),
                int(hour),
            )
            if did_start:
                if was_pulse:
                    pulsed.append(stable_id)
                else:
                    started.append(stable_id)

        events[stable_id] = event

    registry.db.events = events
    _metrics(
        checks=1,
        starts=len(started),
        ends=len(ended),
        pulses=len(pulsed),
    )
    return {
        "started": started,
        "ended": ended,
        "pulsed": pulsed,
    }


def get_scheduled_event(stable_id):
    raw = dict((_registry().db.events or {}).get(stable_id) or {})
    return copy.deepcopy(raw) if raw else None


def _next_day_for_weekday(day, weekday):
    for offset in range(0, 8):
        candidate = int(day) + offset
        if day_name(candidate) == weekday:
            return candidate
    return int(day)


def calendar_lines(day, hour):
    """Player-facing stable calendar facts and the next occurrence."""
    day = int(day)
    hour = int(hour)
    try:
        from world.seasonal_frameworks import calendar_line
        seasonal = calendar_line(day)
    except Exception:
        seasonal = None

    lines = [
        f"Today is game day {day}, {day_name(day)}.",
    ]
    if seasonal:
        lines.append(seasonal)
    lines.extend([
        "The Harbinger normally appears daily at 08:00.",
        "Market morning is Saturday from 07:00 to 12:00 in the Village Square.",
        "Sunday Mass is held at St. Lazarus from 10:00 to 11:00.",
    ])

    events = dict(_registry().db.events or {})
    active = [
        DEFINITIONS[stable_id]["title"]
        for stable_id, raw in events.items()
        if stable_id in DEFINITIONS and dict(raw).get("state") == "active"
    ]
    if active:
        lines.append("Underway now: " + ", ".join(sorted(active)) + ".")

    next_market_day = _next_day_for_weekday(day, "Saturday")
    if next_market_day == day and hour >= 12:
        next_market_day += 7

    next_sunday_day = _next_day_for_weekday(day, "Sunday")
    if next_sunday_day == day and hour >= 11:
        next_sunday_day += 7

    next_paper_day = day if hour < 8 else day + 1
    lines.extend([
        f"Next Harbinger publication: day {next_paper_day} at 08:00.",
        f"Next market morning: day {next_market_day} at 07:00.",
        f"Next Sunday Mass: day {next_sunday_day} at 10:00.",
    ])
    return lines
