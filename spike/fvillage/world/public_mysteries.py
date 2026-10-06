"""Community-scale public mysteries with evidence/theory separation.

A public mystery is an open question whose local facts can accumulate without
certifying the world bible's intentionally unresolved metaphysics.
"""

from __future__ import annotations

import copy
import hashlib

from evennia import create_script
from evennia.scripts.models import ScriptDB


REGISTRY_KEY = "public_mystery_registry"
MANOR_LIGHTS_ID = "PUBLIC-MANOR-LIGHTS"
MAX_OBSERVATIONS = 120
MAX_THEORIES = 80

DEFINITIONS = {
    MANOR_LIGHTS_ID: {
        "title": "Why Are the Manor Lights Returning?",
        "question": "Why are lights appearing again in the hilltop Manor?",
        "location": "Village Square",
        "unresolved_note": (
            "The village may establish when and where the lights appear. "
            "No metaphysical explanation is certified."
        ),
    },
}


def _registry():
    try:
        return ScriptDB.objects.get(db_key=REGISTRY_KEY)
    except ScriptDB.DoesNotExist:
        return create_script(
            "typeclasses.scripts.PublicMysteryRegistry",
            key=REGISTRY_KEY,
            persistent=True,
        )


def get_public_mystery_registry():
    return _registry()


def _fresh(stable_id):
    definition = DEFINITIONS[stable_id]
    return {
        "id": stable_id,
        "title": definition["title"],
        "question": definition["question"],
        "status": "open",
        "observations": [],
        "theories": [],
        "next_theory_id": 1,
        "first_signal_event_id": None,
        "first_signal_rumor_id": None,
        "first_signal_publications": {},
    }


def ensure_public_mysteries():
    registry = _registry()
    mysteries = copy.deepcopy(dict(registry.db.mysteries or {}))
    created = 0
    for stable_id in DEFINITIONS:
        if stable_id not in mysteries:
            mysteries[stable_id] = _fresh(stable_id)
            created += 1
    registry.db.mysteries = mysteries
    return {"created": created, "count": len(mysteries)}


def get_public_mystery(stable_id=MANOR_LIGHTS_ID):
    raw = dict((_registry().db.mysteries or {}).get(stable_id) or {})
    return copy.deepcopy(raw) if raw else None


def _save(mystery):
    registry = _registry()
    mysteries = copy.deepcopy(dict(registry.db.mysteries or {}))
    mysteries[mystery["id"]] = copy.deepcopy(mystery)
    registry.db.mysteries = mysteries
    return copy.deepcopy(mystery)


def _metric(**deltas):
    registry = _registry()
    metrics = copy.deepcopy(dict(registry.db.metrics or {}))
    for key, value in deltas.items():
        metrics[key] = int(metrics.get(key) or 0) + int(value)
    registry.db.metrics = metrics


def _clock():
    try:
        clock = ScriptDB.objects.get(db_key="village_time")
        return int(clock.db.day or 1), int(
            clock.db.hour if clock.db.hour is not None else 21
        )
    except ScriptDB.DoesNotExist:
        return 1, 21


def _weather():
    try:
        return str(
            ScriptDB.objects.get(db_key="village_weather").db.state or "clear"
        ).lower()
    except ScriptDB.DoesNotExist:
        return "clear"


def manor_light_state(day, hour, weather):
    """Return a deterministic observable state without encoding a cause."""
    day = int(day)
    hour = int(hour)
    weather = str(weather or "clear").lower()
    night = hour >= 18 or hour <= 5

    if not night:
        return {
            "lit": False,
            "pattern": "daylight",
            "detail": (
                "In daylight the Manor is a dark mass of roofline and blind "
                "windows. No artificial light is visible from the square."
            ),
        }

    token = f"manor-lights|{day}|{hour}|{weather}".encode("utf-8")
    roll = int.from_bytes(hashlib.sha256(token).digest()[:4], "big") % 100

    # Fog makes distant light easier to notice as a glow, not more supernatural.
    threshold = 45 if weather == "fog" else 34
    if roll >= threshold:
        return {
            "lit": False,
            "pattern": "dark",
            "detail": (
                "The Manor windows remain dark. The hill gives back only a "
                "broken silhouette."
            ),
        }

    patterns = (
        (
            "one_upper_window",
            "One upper window shows a steady amber rectangle.",
        ),
        (
            "three_windows",
            "Three separated windows glow at once, too far apart to be one room.",
        ),
        (
            "east_gallery",
            "A pale light moves behind the east gallery windows, then holds still.",
        ),
    )
    pattern, detail = patterns[roll % len(patterns)]
    return {
        "lit": True,
        "pattern": pattern,
        "detail": detail,
    }


def _player_ref(player):
    account = getattr(player, "account", None)
    return {
        "mask_id": getattr(player, "id", None),
        "mask": getattr(player, "key", None),
        "account_id": getattr(account, "id", None),
    }


def _signal_publication(mystery, observation, actor):
    if mystery.get("first_signal_event_id") or not observation["lit"]:
        return mystery

    from world.events import publish_world_event

    event = publish_world_event(
        "public_mystery.manor_lights.observed",
        actor=actor,
        payload={
            "public_mystery_id": MANOR_LIGHTS_ID,
            "day": observation["day"],
            "hour": observation["hour"],
            "weather": observation["weather"],
            "pattern": observation["pattern"],
            "harbinger": True,
            "chronicle_eligible": False,
        },
        rumor=(
            "Someone watching from the square saw lights burning again in "
            "the hilltop Manor. Nobody agrees on who could be inside."
        ),
    )
    rumor = event.get("rumor") or {}
    try:
        rumor = dict(rumor)
    except Exception:
        rumor = {}
    mystery["first_signal_event_id"] = event["id"]
    mystery["first_signal_rumor_id"] = rumor.get("rumor_id")
    mystery["first_signal_publications"] = copy.deepcopy(
        event.get("publications") or {}
    )
    _metric(public_signals=1)
    return mystery


def observe_manor(player, *, day=None, hour=None, weather=None):
    mystery = get_public_mystery(MANOR_LIGHTS_ID)
    if not mystery:
        ensure_public_mysteries()
        mystery = get_public_mystery(MANOR_LIGHTS_ID)

    if day is None or hour is None:
        clock_day, clock_hour = _clock()
        day = clock_day if day is None else int(day)
        hour = clock_hour if hour is None else int(hour)
    weather = _weather() if weather is None else str(weather).lower()

    state = manor_light_state(day, hour, weather)
    observation_key = f"{int(day)}:{int(hour)}:{weather}:{state['pattern']}"
    observations = copy.deepcopy(list(mystery.get("observations") or []))
    witness = _player_ref(player)
    witness_id = witness.get("mask_id")

    existing_index = next(
        (
            index
            for index, record in enumerate(observations)
            if record.get("key") == observation_key
        ),
        None,
    )

    if existing_index is None:
        record = {
            "key": observation_key,
            "day": int(day),
            "hour": int(hour),
            "weather": weather,
            "lit": bool(state["lit"]),
            "pattern": state["pattern"],
            "detail": state["detail"],
            "witnesses": [witness] if witness_id is not None else [],
        }
        observations.append(record)
        observations = observations[-MAX_OBSERVATIONS:]
        mystery["observations"] = observations
        mystery = _signal_publication(mystery, record, player)
        _metric(observations=1, witness_links=1 if witness_id is not None else 0)
        _save(mystery)
        return copy.deepcopy(record)

    record = copy.deepcopy(dict(observations[existing_index]))
    witnesses = list(record.get("witnesses") or [])
    if witness_id is not None and not any(
        item.get("mask_id") == witness_id for item in witnesses
    ):
        witnesses.append(witness)
        record["witnesses"] = witnesses
        observations[existing_index] = record
        mystery["observations"] = observations
        _metric(witness_links=1)
        _save(mystery)
    return copy.deepcopy(record)


def manor_description(looker=None):
    day, hour = _clock()
    weather = _weather()
    state = manor_light_state(day, hour, weather)

    if looker is not None and getattr(looker, "has_account", False):
        observe_manor(looker, day=day, hour=hour, weather=weather)

    return (
        "The Manor stands above the village on the hill, too distant for "
        "architectural detail from here. "
        + state["detail"]
        + " Whatever the lights mean, distance does not supply the answer."
    )


def submit_theory(player, text, stable_id=MANOR_LIGHTS_ID):
    mystery = get_public_mystery(stable_id)
    if not mystery or mystery.get("status") != "open":
        return None, "That public question is not open."

    body = str(text or "").strip()
    if not body:
        return None, "A theory needs actual words."
    if len(body) > 600:
        return None, "Keep a public theory under 600 characters."

    theory = {
        "id": int(mystery.get("next_theory_id") or 1),
        "author": _player_ref(player),
        "text": body,
        "status": "proposed",
        "truth_status": None,
        "created_day": _clock()[0],
        "created_hour": _clock()[1],
    }
    theories = copy.deepcopy(list(mystery.get("theories") or []))
    theories.append(theory)
    mystery["theories"] = theories[-MAX_THEORIES:]
    mystery["next_theory_id"] = theory["id"] + 1
    _save(mystery)
    _metric(theories=1)
    return copy.deepcopy(theory), None


def resolve_subject(token):
    token = str(token or "").strip().lower()
    if token in {
        "manor",
        "lights",
        "manor lights",
        "manor-lights",
        "hilltop manor",
        "why are the manor lights returning",
    }:
        return MANOR_LIGHTS_ID
    return None


def mystery_lines(player=None, stable_id=MANOR_LIGHTS_ID):
    mystery = get_public_mystery(stable_id)
    if not mystery:
        return ["No public mystery record is available."]

    definition = DEFINITIONS[stable_id]
    observations = list(mystery.get("observations") or [])
    theories = list(mystery.get("theories") or [])
    lit_count = sum(1 for record in observations if record.get("lit"))

    lines = [
        mystery["title"],
        "Question: " + mystery["question"],
        (
            f"Shared observations: {len(observations)} "
            f"({lit_count} with visible artificial light)."
        ),
    ]

    if observations:
        lines.append("Latest public observations:")
        for record in observations[-5:]:
            witnesses = len(record.get("witnesses") or [])
            lines.append(
                f"  day {record['day']} {record['hour']:02d}:00, "
                f"{record['weather']}: {record['detail']} "
                f"({witnesses} named witness(es))"
            )
    else:
        lines.append(
            "No shared observation has been logged yet. The Manor is visible "
            "from the Village Square."
        )

    if theories:
        lines.append("Provisional theories:")
        for theory in theories[-5:]:
            author = (theory.get("author") or {}).get("mask") or "unknown"
            lines.append(
                f"  T{theory['id']} {author}: {theory['text']}"
            )
    else:
        lines.append("No public theory has been submitted yet.")

    lines.append(definition["unresolved_note"])
    return lines
