"""Weighted random world incidents driven by the authoritative village clock.

Random incidents are low-cost texture and occasional signal. They are not
private quests, do not own their own scheduler, and do not replay elapsed time.
The village clock evaluates this module once per game hour.

Selection is deterministic for a given world-state boundary. This preserves
restart stability while still producing changing results across day/hour,
weather, occupancy, and resident presence.
"""

from __future__ import annotations

import copy
import hashlib

from evennia import create_script
from evennia.scripts.models import ScriptDB
from evennia.utils import search


REGISTRY_KEY = "random_incident_registry"
PUBLIC_SNEEZE_ID = "RANDOM-PUBLIC-SNEEZE"
EXTINGUISHED_LAMP_ID = "RANDOM-EXTINGUISHED-LAMP"

TRIGGER_PERCENT = 34
MAX_HISTORY = 24

DEFINITIONS = {
    PUBLIC_SNEEZE_ID: {
        "title": "Public Sneeze",
        "tone": "mundane",
        "base_weight": 80,
        "locations": ["Village Square", "The Blood of the Vine"],
        "hours": list(range(7, 23)),
        "requires_resident": True,
        "cooldown_hours": 6,
        "overlay": (
            "{resident} keeps interrupting the room with a spectacular series "
            "of sneezes. It looks miserable rather than mysterious."
        ),
    },
    EXTINGUISHED_LAMP_ID: {
        "title": "Extinguished Lamp",
        "tone": "odd",
        "base_weight": 18,
        "locations": ["Village Square"],
        "hours": [18, 19, 20, 21, 22, 23, 0, 1, 2, 3, 4, 5],
        "requires_resident": False,
        "cooldown_hours": 18,
        "weather_bonus": {
            "rain": 25,
            "fog": 12,
            "clear": 0,
        },
        "overlay": (
            "One gas lamp at the edge of the square has gone out again while "
            "the neighboring lamps burn steadily. Its glass is intact."
        ),
    },
}


def _registry():
    try:
        return ScriptDB.objects.get(db_key=REGISTRY_KEY)
    except ScriptDB.DoesNotExist:
        return create_script(
            "typeclasses.scripts.RandomIncidentRegistry",
            key=REGISTRY_KEY,
            persistent=True,
        )


def get_random_incident_registry():
    return _registry()


def ensure_random_incidents():
    registry = _registry()
    if registry.db.current is None:
        registry.db.current = None
    if registry.db.history is None:
        registry.db.history = []
    if registry.db.last_check_key is None:
        registry.db.last_check_key = None
    if registry.db.last_runs is None:
        registry.db.last_runs = {}
    return {
        "definition_count": len(DEFINITIONS),
        "history_count": len(registry.db.history or []),
    }


def _room(key):
    found = [obj for obj in search.search_object(key) if obj.key == key]
    return found[0] if found else None


def _weather():
    try:
        return str(
            ScriptDB.objects.get(db_key="village_weather").db.state or "clear"
        ).lower()
    except ScriptDB.DoesNotExist:
        return "clear"


def _connected_players(room):
    if not room:
        return []
    return [
        obj for obj in room.contents
        if obj.has_account and obj.is_connected
    ]


def _residents(room):
    if not room:
        return []
    return [
        obj for obj in room.contents
        if getattr(obj.db, "resident_id", None)
    ]


def _metric(**deltas):
    registry = _registry()
    metrics = copy.deepcopy(dict(registry.db.metrics or {}))
    for key, value in deltas.items():
        metrics[key] = int(metrics.get(key) or 0) + int(value)
    registry.db.metrics = metrics


def _stable_number(*parts, modulo=10000):
    raw = "|".join(str(part) for part in parts)
    digest = hashlib.sha256(raw.encode("utf-8")).hexdigest()
    return int(digest[:16], 16) % int(modulo)


def _absolute_hour(day, hour):
    return (int(day) - 1) * 24 + int(hour)


def _within_cooldown(stable_id, definition, day, hour):
    last_runs = dict(_registry().db.last_runs or {})
    previous = last_runs.get(stable_id)
    if not previous:
        return False
    elapsed = _absolute_hour(day, hour) - _absolute_hour(
        previous["day"],
        previous["hour"],
    )
    return elapsed < int(definition.get("cooldown_hours") or 0)


def _eligible_locations(definition):
    eligible = []
    for location_key in definition.get("locations") or []:
        room = _room(location_key)
        if not room:
            continue
        residents = _residents(room)
        if definition.get("requires_resident") and not residents:
            continue
        eligible.append({
            "key": location_key,
            "room": room,
            "resident_count": len(residents),
            "player_count": len(_connected_players(room)),
        })
    return eligible


def _candidate_weight(stable_id, definition, day, hour, weather):
    if int(hour) not in set(definition.get("hours") or []):
        return 0, []
    if _within_cooldown(stable_id, definition, day, hour):
        return 0, []

    locations = _eligible_locations(definition)
    if not locations:
        return 0, []

    weight = int(definition.get("base_weight") or 0)
    weight += int(
        (definition.get("weather_bonus") or {}).get(weather, 0)
    )

    # Occupied spaces are a little more likely to receive social texture,
    # but empty rooms remain eligible. This preserves a world that happens
    # without players while still making witnessed life common.
    weight += min(20, sum(item["player_count"] for item in locations) * 5)

    # Public Sneeze gets a small social-density bonus because it requires a
    # resident body to sneeze. Odd environmental incidents do not.
    if stable_id == PUBLIC_SNEEZE_ID:
        weight += min(20, sum(item["resident_count"] for item in locations) * 2)

    return max(0, weight), locations


def candidate_table(*, day, hour):
    weather = _weather()
    table = []
    for stable_id, definition in DEFINITIONS.items():
        weight, locations = _candidate_weight(
            stable_id,
            definition,
            int(day),
            int(hour),
            weather,
        )
        if not weight:
            continue
        table.append({
            "id": stable_id,
            "title": definition["title"],
            "tone": definition["tone"],
            "weight": weight,
            "locations": [
                {
                    "key": item["key"],
                    "resident_count": item["resident_count"],
                    "player_count": item["player_count"],
                }
                for item in locations
            ],
        })
    return sorted(table, key=lambda row: (-row["weight"], row["id"]))


def _choose_location(stable_id, day, hour, locations):
    ranked = sorted(
        locations,
        key=lambda item: (
            -item["player_count"],
            -item["resident_count"],
            item["key"],
        ),
    )
    if len(ranked) <= 1:
        return ranked[0]
    index = _stable_number(
        "location",
        stable_id,
        day,
        hour,
        _weather(),
        modulo=len(ranked),
    )
    return ranked[index]


def _select_candidate(day, hour, table):
    total = sum(row["weight"] for row in table)
    if total <= 0:
        return None
    roll = _stable_number(
        "random-incident-choice",
        day,
        hour,
        _weather(),
        ";".join(f"{row['id']}:{row['weight']}" for row in table),
        modulo=total,
    )
    cursor = 0
    for row in table:
        cursor += row["weight"]
        if roll < cursor:
            return row
    return table[-1]


def _actor_ref(obj):
    if not obj:
        return None
    return {
        "object_id": getattr(obj, "id", None),
        "key": getattr(obj, "key", None),
        "resident_id": getattr(obj.db, "resident_id", None),
    }


def _start_public_sneeze(record, room):
    residents = sorted(
        _residents(room),
        key=lambda obj: (
            str(getattr(obj.db, "resident_id", "")),
            obj.id,
        ),
    )
    if not residents:
        return None
    index = _stable_number(
        PUBLIC_SNEEZE_ID,
        record["started_day"],
        record["started_hour"],
        room.key,
        modulo=len(residents),
    )
    resident = residents[index]
    record["subject"] = _actor_ref(resident)
    record["overlay_text"] = DEFINITIONS[PUBLIC_SNEEZE_ID]["overlay"].format(
        resident=resident.key
    )
    record["resident_ids"] = [resident.db.resident_id]
    return record


def _start_extinguished_lamp(record, room):
    record["subject"] = {
        "key": "gas lamp",
        "location": room.key,
    }
    record["overlay_text"] = DEFINITIONS[EXTINGUISHED_LAMP_ID]["overlay"]
    record["resident_ids"] = [
        obj.db.resident_id for obj in _residents(room)
    ]
    return record


def _start_record(stable_id, day, hour, location):
    return {
        "id": stable_id,
        "title": DEFINITIONS[stable_id]["title"],
        "tone": DEFINITIONS[stable_id]["tone"],
        "state": "active",
        "started_day": int(day),
        "started_hour": int(hour),
        "end_day": int(day),
        "end_hour": int(hour) + 1,
        "location": location["key"],
        "subject": None,
        "overlay_text": None,
        "resident_ids": [],
        "player_witnesses": [],
        "event_id": None,
        "end_event_id": None,
        "result": {},
    }


def _normalize_end(record):
    if int(record["end_hour"]) >= 24:
        record["end_day"] = int(record["end_day"]) + 1
        record["end_hour"] = int(record["end_hour"]) % 24
    return record


def _record_connected_witnesses(record, room):
    record["player_witnesses"] = [
        {
            "player_id": obj.id,
            "player_name": obj.key,
        }
        for obj in _connected_players(room)
    ]
    return record


def _publish_start(record):
    from world.events import publish_world_event

    event = publish_world_event(
        f"random.{record['id'].lower()}",
        payload={
            "random_incident_id": record["id"],
            "title": record["title"],
            "tone": record["tone"],
            "location": record["location"],
            "subject": copy.deepcopy(record["subject"]),
            "resident_ids": list(record.get("resident_ids") or []),
            # The occurrence is canonical but is not automatically public news.
            "publicity": "private",
        },
    )
    record["event_id"] = event["id"]
    return record


def _set_overlay(record):
    from world.scheduled_events import set_room_overlay

    return set_room_overlay(
        record["location"],
        record["id"],
        record["overlay_text"],
    )


def _clear_overlay(record):
    from world.scheduled_events import clear_room_overlay

    return clear_room_overlay(record["location"], record["id"])


def _start_incident(stable_id, day, hour, candidate):
    definition = DEFINITIONS[stable_id]
    weight, locations = _candidate_weight(
        stable_id,
        definition,
        day,
        hour,
        _weather(),
    )
    if not weight or not locations:
        return None

    location = _choose_location(stable_id, day, hour, locations)
    room = location["room"]
    record = _normalize_end(
        _start_record(stable_id, day, hour, location)
    )

    if stable_id == PUBLIC_SNEEZE_ID:
        record = _start_public_sneeze(record, room)
    elif stable_id == EXTINGUISHED_LAMP_ID:
        record = _start_extinguished_lamp(record, room)
    if not record:
        return None

    record = _record_connected_witnesses(record, room)
    record = _publish_start(record)
    _set_overlay(record)
    if room:
        room.msg_contents(record["overlay_text"])

    registry = _registry()
    registry.db.current = copy.deepcopy(record)
    last_runs = copy.deepcopy(dict(registry.db.last_runs or {}))
    last_runs[stable_id] = {
        "day": int(day),
        "hour": int(hour),
    }
    registry.db.last_runs = last_runs

    _metric(
        triggered=1,
        mundane=1 if definition["tone"] == "mundane" else 0,
        odd=1 if definition["tone"] == "odd" else 0,
    )
    return copy.deepcopy(record)


def _end_current(day, hour):
    registry = _registry()
    current = copy.deepcopy(dict(registry.db.current or {}))
    if not current:
        return None
    due = (int(current["end_day"]), int(current["end_hour"]))
    if (int(day), int(hour)) < due:
        return None

    _clear_overlay(current)

    from world.events import publish_world_event

    end_event = publish_world_event(
        f"random.{current['id'].lower()}.ended",
        payload={
            "random_incident_id": current["id"],
            "title": current["title"],
            "tone": current["tone"],
            "location": current["location"],
            "subject": copy.deepcopy(current["subject"]),
            "resident_ids": list(current.get("resident_ids") or []),
            "publicity": "private",
        },
    )
    current["end_event_id"] = end_event["id"]
    current["state"] = "ended"
    current["ended_day"] = int(day)
    current["ended_hour"] = int(hour)

    history = copy.deepcopy(list(registry.db.history or []))
    history.append(current)
    registry.db.history = history[-MAX_HISTORY:]
    registry.db.current = None
    _metric(ended=1)
    return copy.deepcopy(current)


def advance_random_incidents(*, day, hour, force_id=None):
    """End due texture, then evaluate at most one incident for this boundary."""
    day = int(day)
    hour = int(hour)
    registry = _registry()
    check_key = f"{day}:{hour}"

    ended = _end_current(day, hour)

    # One active random incident at a time. Its lifetime is one game hour.
    if registry.db.current:
        return {
            "ended": ended["id"] if ended else None,
            "started": None,
            "roll": None,
            "candidates": [],
        }

    if registry.db.last_check_key == check_key and force_id is None:
        return {
            "ended": ended["id"] if ended else None,
            "started": None,
            "roll": None,
            "candidates": [],
        }

    registry.db.last_check_key = check_key
    table = candidate_table(day=day, hour=hour)
    _metric(checks=1)

    if force_id is not None:
        selected = next(
            (row for row in table if row["id"] == force_id),
            None,
        )
        if selected is None:
            return {
                "ended": ended["id"] if ended else None,
                "started": None,
                "roll": None,
                "candidates": table,
            }
        started = _start_incident(force_id, day, hour, selected)
        return {
            "ended": ended["id"] if ended else None,
            "started": started["id"] if started else None,
            "roll": "forced",
            "candidates": table,
        }

    if not table:
        return {
            "ended": ended["id"] if ended else None,
            "started": None,
            "roll": None,
            "candidates": [],
        }

    gate = _stable_number(
        "random-incident-gate",
        day,
        hour,
        _weather(),
        ";".join(row["id"] for row in table),
        modulo=100,
    )
    if gate >= TRIGGER_PERCENT:
        return {
            "ended": ended["id"] if ended else None,
            "started": None,
            "roll": gate,
            "candidates": table,
        }

    selected = _select_candidate(day, hour, table)
    started = _start_incident(selected["id"], day, hour, selected)
    return {
        "ended": ended["id"] if ended else None,
        "started": started["id"] if started else None,
        "roll": gate,
        "candidates": table,
    }


def current_random_incident():
    current = dict(_registry().db.current or {})
    return copy.deepcopy(current) if current else None


def recent_random_incidents(limit=10):
    return copy.deepcopy(list(_registry().db.history or [])[-int(limit):])
