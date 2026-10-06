"""Seasonal and chapter frameworks for slow world modulation.

The exact civil year remains intentionally unresolved. This layer therefore
tracks named story chapters against the internal village day counter rather
than claiming a Gregorian date. Chapters modify probabilities and routines;
they do not replace the village or create private quest copies.
"""

from __future__ import annotations

import copy

from evennia import create_script
from evennia.scripts.models import ScriptDB


REGISTRY_KEY = "seasonal_framework_registry"
OVERLAY_KEY = "SEASONAL-CHAPTER"

LONG_SHADOWS_ID = "SEASON-LONG-SHADOWS"
RECKONING_ID = "SEASON-RECKONING-OF-ACCOUNTS"
EMPTY_PLACES_ID = "SEASON-EMPTY-PLACES"
FROZEN_ROADS_ID = "SEASON-FROZEN-ROADS"
THAW_BELOW_ID = "SEASON-THAW-BELOW"
VISITORS_ID = "SEASON-VISITORS"

SEQUENCE = (
    LONG_SHADOWS_ID,
    RECKONING_ID,
    EMPTY_PLACES_ID,
    FROZEN_ROADS_ID,
    THAW_BELOW_ID,
    VISITORS_ID,
)

DEFINITIONS = {
    LONG_SHADOWS_ID: {
        "title": "The Weeks of Long Shadows",
        "nominal_season": "October pattern",
        "duration_days": 30,
        "description": (
            "Fog comes earlier, evening public life thins sooner, and small odd "
            "occurrences become a little more likely without becoming the norm."
        ),
        "overlay": (
            "The season of long shadows has settled over the village. Evening "
            "fog gathers early, and ordinary business tends to end sooner."
        ),
        "content_tags": ["fog", "cemetery", "evening", "small_investigations"],
        "weather_weights": {"clear": 1.0, "fog": 4.0, "rain": 1.5},
        "random_tone_bonus": {"mundane": 0, "odd": 6},
        "random_id_bonus": {"RANDOM-EXTINGUISHED-LAMP": 8},
        "evening_public_cutoff": 21,
        "economy": {},
    },
    RECKONING_ID: {
        "title": "The Reckoning of Accounts",
        "nominal_season": "November pattern",
        "duration_days": 30,
        "description": (
            "Winter preparation pushes debts, favors, tribute obligations, and "
            "household shortages toward the surface."
        ),
        "overlay": (
            "Ledgers, winter stores, and old obligations have become ordinary "
            "conversation. Even casual purchases seem to carry a second meaning."
        ),
        "content_tags": ["debts", "winter_stores", "tribute", "households"],
        "weather_weights": {"clear": 1.5, "fog": 2.0, "rain": 1.5},
        "random_tone_bonus": {"mundane": 5, "odd": 0},
        "random_id_bonus": {},
        "evening_public_cutoff": None,
        "economy": {"scarcity_pressure": 1.10, "debt_pressure": 1.35},
    },
    EMPTY_PLACES_ID: {
        "title": "The Empty Places at Table",
        "nominal_season": "December pattern",
        "duration_days": 31,
        "description": (
            "Gatherings emphasize hospitality, absence, newcomers, family ties, "
            "and old feuds without requiring a single holiday storyline."
        ),
        "overlay": (
            "Tables stay set a little longer than usual. Names of absent people "
            "surface in conversation beside invitations offered to newcomers."
        ),
        "content_tags": ["hospitality", "absence", "family", "newcomers", "feuds"],
        "weather_weights": {"clear": 2.0, "fog": 1.5, "rain": 1.0},
        "random_tone_bonus": {"mundane": 7, "odd": 0},
        "random_id_bonus": {},
        "evening_public_cutoff": None,
        "economy": {"hospitality_pressure": 1.20},
    },
    FROZEN_ROADS_ID: {
        "title": "The Frozen Roads",
        "nominal_season": "winter pattern",
        "duration_days": 90,
        "description": (
            "Travel grows expensive, village institutions matter more, and remote "
            "places become harder to reach without declaring them permanently closed."
        ),
        "overlay": (
            "Travel beyond the village has become difficult enough that local "
            "institutions carry more weight than they did in easier weather."
        ),
        "content_tags": ["travel_cost", "isolation", "local_institutions"],
        "weather_weights": {"clear": 2.5, "fog": 2.0, "rain": 0.5},
        "random_tone_bonus": {"mundane": 4, "odd": 1},
        "random_id_bonus": {},
        "evening_public_cutoff": 20,
        "economy": {"travel_cost": 1.50, "local_goods_pressure": 1.20},
    },
    THAW_BELOW_ID: {
        "title": "The Thaw Below",
        "nominal_season": "spring pattern",
        "duration_days": 90,
        "description": (
            "Water, mud, and thawing ground expose infrastructure, graves, objects, "
            "and routes that winter concealed."
        ),
        "overlay": (
            "Runoff threads through old stonework. Mud and thaw have begun exposing "
            "things the winter kept hidden."
        ),
        "content_tags": ["flooding", "catacombs", "graves", "infrastructure"],
        "weather_weights": {"clear": 1.0, "fog": 1.0, "rain": 4.0},
        "random_tone_bonus": {"mundane": 2, "odd": 4},
        "random_id_bonus": {},
        "evening_public_cutoff": None,
        "economy": {"repair_pressure": 1.25},
    },
    VISITORS_ID: {
        "title": "The Visitors",
        "nominal_season": "summer pattern",
        "duration_days": 94,
        "description": (
            "Better roads bring scholars, performers, merchants, investigators, and "
            "opportunists, increasing social pressure rather than military pressure."
        ),
        "overlay": (
            "More unfamiliar faces pass through the square than the village is used "
            "to seeing. Trade is easier; privacy is not."
        ),
        "content_tags": ["visitors", "trade", "scholars", "performers", "investigators"],
        "weather_weights": {"clear": 4.0, "fog": 0.5, "rain": 1.0},
        "random_tone_bonus": {"mundane": 8, "odd": 0},
        "random_id_bonus": {},
        "evening_public_cutoff": None,
        "economy": {"trade_access": 1.25, "social_pressure": 1.20},
    },
}


def _registry():
    try:
        return ScriptDB.objects.get(db_key=REGISTRY_KEY)
    except ScriptDB.DoesNotExist:
        return create_script(
            "typeclasses.scripts.SeasonalFrameworkRegistry",
            key=REGISTRY_KEY,
            persistent=True,
        )


def get_seasonal_framework_registry():
    return _registry()


def _clock():
    try:
        clock = ScriptDB.objects.get(db_key="village_time")
        return int(clock.db.day or 1), int(
            clock.db.hour if clock.db.hour is not None else 21
        )
    except ScriptDB.DoesNotExist:
        return 1, 21


def _metric(**deltas):
    registry = _registry()
    metrics = copy.deepcopy(dict(registry.db.metrics or {}))
    for key, value in deltas.items():
        metrics[key] = int(metrics.get(key) or 0) + int(value)
    registry.db.metrics = metrics


def _next_id(stable_id):
    index = SEQUENCE.index(stable_id)
    return SEQUENCE[(index + 1) % len(SEQUENCE)]


def _chapter_record(stable_id, started_day):
    definition = DEFINITIONS[stable_id]
    return {
        "id": stable_id,
        "title": definition["title"],
        "nominal_season": definition["nominal_season"],
        "started_day": int(started_day),
        "duration_days": int(definition["duration_days"]),
        "ended_day": None,
    }


def ensure_seasonal_frameworks():
    registry = _registry()
    day, _hour = _clock()
    created = False
    if not registry.db.active_id:
        registry.db.active_id = LONG_SHADOWS_ID
        registry.db.started_day = int(day)
        registry.db.cycle_started_day = int(day)
        registry.db.history = []
        created = True
    reconcile_seasonal_projection()
    return {
        "created": created,
        "active_id": registry.db.active_id,
        "started_day": int(registry.db.started_day or day),
    }


def current_chapter():
    registry = _registry()
    stable_id = registry.db.active_id
    if not stable_id:
        ensure_seasonal_frameworks()
        stable_id = registry.db.active_id
    definition = DEFINITIONS[stable_id]
    day, _hour = _clock()
    chapter_day = max(1, int(day) - int(registry.db.started_day or day) + 1)
    return {
        "id": stable_id,
        "title": definition["title"],
        "nominal_season": definition["nominal_season"],
        "description": definition["description"],
        "started_day": int(registry.db.started_day or day),
        "chapter_day": chapter_day,
        "duration_days": int(definition["duration_days"]),
        "content_tags": list(definition.get("content_tags") or []),
        "economy": copy.deepcopy(definition.get("economy") or {}),
    }


def content_tags():
    return set(current_chapter()["content_tags"])


def economy_modifiers():
    return copy.deepcopy(current_chapter()["economy"])


def weather_weights():
    stable_id = current_chapter()["id"]
    return copy.deepcopy(DEFINITIONS[stable_id]["weather_weights"])


def random_incident_bonus(stable_id, incident_definition, *, day, hour, weather):
    chapter_id = current_chapter()["id"]
    chapter = DEFINITIONS[chapter_id]
    tone = str(incident_definition.get("tone") or "mundane")
    bonus = int((chapter.get("random_tone_bonus") or {}).get(tone, 0))
    bonus += int((chapter.get("random_id_bonus") or {}).get(stable_id, 0))

    # Long Shadows specifically shifts strange texture toward the evening.
    if (
        chapter_id == LONG_SHADOWS_ID
        and tone == "odd"
        and (int(hour) >= 17 or int(hour) <= 5)
    ):
        bonus += 4
    return bonus


def apply_resident_target(definition, target, *, day, hour):
    """Apply cheap chapter schedule pressure after ordinary resolution.

    This is deliberately narrow. Essential night roles continue working;
    optional public evening activity may end earlier.
    """
    chapter_id = current_chapter()["id"]
    chapter = DEFINITIONS[chapter_id]
    cutoff = chapter.get("evening_public_cutoff")
    if cutoff is None or int(hour) < int(cutoff):
        return target

    logical = target.get("logical_location")
    if logical not in {"tavern", "village_square"}:
        return target

    occupation = str(definition.get("occupation") or "").lower()
    essential_night_roles = {
        "lamplighter",
        "night watch",
        "priest",
        "tavern keeper",
        "midwife",
    }
    if occupation in essential_night_roles:
        return target

    home = definition.get("home_id")
    if not home or logical == home:
        return target

    return {
        **target,
        "logical_location": home,
        "activity": (
            f"heads home early during {chapter['title'].lower()}"
        ),
        "source": "seasonal",
        "reason": chapter_id,
    }


def _publish_transition(old_id, new_id, started_day):
    try:
        from world.events import publish_world_event

        old_title = DEFINITIONS[old_id]["title"]
        new_title = DEFINITIONS[new_id]["title"]
        return publish_world_event(
            "seasonal.chapter_changed",
            payload={
                "old_chapter_id": old_id,
                "new_chapter_id": new_id,
                "started_day": int(started_day),
                "headline": f"{new_title} Begins",
                "public_summary": (
                    f"The village has moved from {old_title} into {new_title}. "
                    "The shift changes conditions and probabilities rather than "
                    "replacing ordinary village life."
                ),
                "chronicle_summary": (
                    f"The Chronicle records the beginning of {new_title} on village "
                    f"day {int(started_day)} after the close of {old_title}."
                ),
                "chronicle_eligible": True,
            },
        )
    except Exception:
        return None


def _set_projection(stable_id):
    from world.scheduled_events import set_room_overlay

    definition = DEFINITIONS[stable_id]
    return set_room_overlay(
        "Village Square",
        OVERLAY_KEY,
        definition["overlay"],
    )


def reconcile_seasonal_projection():
    registry = _registry()
    if not registry.db.active_id:
        return False
    return _set_projection(registry.db.active_id)


def advance_seasonal_framework(*, day, hour, emit=True):
    """Advance chapter state directly to the current village day."""
    registry = _registry()
    if not registry.db.active_id:
        ensure_seasonal_frameworks()

    transitions = []
    stable_id = registry.db.active_id
    started_day = int(registry.db.started_day or day)

    # At most one 365-day cycle is needed for normal catch-up, but this loop
    # also handles a long offline jump without replaying individual days.
    guard = 0
    while int(day) >= started_day + int(DEFINITIONS[stable_id]["duration_days"]):
        guard += 1
        if guard > len(SEQUENCE) * 4:
            break

        duration = int(DEFINITIONS[stable_id]["duration_days"])
        next_started_day = started_day + duration
        next_id = _next_id(stable_id)

        history = copy.deepcopy(list(registry.db.history or []))
        record = _chapter_record(stable_id, started_day)
        record["ended_day"] = next_started_day - 1
        history.append(record)
        registry.db.history = history[-12:]

        if emit:
            _publish_transition(stable_id, next_id, next_started_day)

        transitions.append({
            "from": stable_id,
            "to": next_id,
            "started_day": next_started_day,
        })
        stable_id = next_id
        started_day = next_started_day

    registry.db.active_id = stable_id
    registry.db.started_day = started_day
    _set_projection(stable_id)
    _metric(checks=1, transitions=len(transitions))
    return transitions


def calendar_line(day=None):
    if day is None:
        day, _hour = _clock()
    chapter = current_chapter()
    remaining = max(
        0,
        chapter["duration_days"] - chapter["chapter_day"],
    )
    return (
        f"Seasonal chapter: {chapter['title']} "
        f"(chapter day {chapter['chapter_day']}; "
        f"{remaining} day(s) before the next chapter boundary)."
    )


def chapter_history():
    return copy.deepcopy(list(_registry().db.history or []))
