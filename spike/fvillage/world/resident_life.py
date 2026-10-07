"""Event-driven resident life state for Frankenstein Village.

This module is intentionally free of Evennia imports.  It contains the cheap
state transitions used by ordinary population residents.  Authored and
quest-specific residents can be marked authored_locked and are then strict
no-ops here.

Continuity is always active.  Cognition is activated only when required.
"""

from __future__ import annotations

import copy


SCHEMA_VERSION = 1
PROFILE_POPULATION = "population"
PROFILE_AUTHORED_LOCKED = "authored_locked"

# Generic-scheduler residents already serving authored narrative roles.
AUTHORED_LOCKED_IDS = frozenset({"ilona_szabo"})

BODY_KEYS = frozenset(
    {
        "cold",
        "wet",
        "pain",
        "injury",
        "illness",
        "intoxication",
        "discomfort",
    }
)

MAX_AFFECT_EPISODES = 8
MAX_PERCEPTIONS = 12
MAX_COMMITMENTS = 12
MAX_RESIDENT_RELATIONSHIPS = 24
MAX_ACTIVE_GOALS = 6


def clamp(value, low=0.0, high=100.0):
    return max(float(low), min(float(high), float(value)))


def profile_for(definition):
    """Return the explicit simulation profile for one resident definition."""
    explicit = definition.get("life_simulation_profile")
    if explicit in {PROFILE_POPULATION, PROFILE_AUTHORED_LOCKED}:
        return explicit

    # Existing runtime-canon and legacy-routine residents are deliberately
    # protected.  Resident Life v2 must not take control of authored quest NPCs.
    if (
        definition.get("stable_id") in AUTHORED_LOCKED_IDS
        or definition.get("provenance") == "runtime_canon"
        or definition.get("schedule_engine") == "legacy"
    ):
        return PROFILE_AUTHORED_LOCKED
    return PROFILE_POPULATION


def fresh_life_state(definition):
    profile = profile_for(definition)
    if profile == PROFILE_AUTHORED_LOCKED:
        return {
            "schema_version": SCHEMA_VERSION,
            "profile": PROFILE_AUTHORED_LOCKED,
            "enabled": False,
        }

    return {
        "schema_version": SCHEMA_VERSION,
        "profile": PROFILE_POPULATION,
        "enabled": True,
        "body": {key: 0.0 for key in BODY_KEYS},
        "affect": [],
        "commitments": [],
        "resident_relationships": {},
        "perceptions": [],
        "active_goals": [],
        "next_affect_id": 1,
        "next_commitment_id": 1,
        "last_decay_absolute_hour": None,
    }


def merge_life_state(definition, existing):
    """Upgrade persisted life state while preserving the authored lock."""
    fresh = fresh_life_state(definition)
    if not fresh["enabled"]:
        return fresh

    if not existing:
        return fresh

    old = copy.deepcopy(dict(existing))
    merged = copy.deepcopy(fresh)
    for key, value in old.items():
        if key in {
            "body",
            "resident_relationships",
        } and isinstance(value, dict):
            nested = dict(merged.get(key) or {})
            nested.update(value)
            merged[key] = nested
        elif key in {
            "affect",
            "commitments",
            "perceptions",
            "active_goals",
        }:
            merged[key] = list(value or [])
        else:
            merged[key] = value

    merged["schema_version"] = SCHEMA_VERSION
    merged["profile"] = PROFILE_POPULATION
    merged["enabled"] = True
    merged["body"] = {
        key: clamp((merged.get("body") or {}).get(key, 0.0))
        for key in BODY_KEYS
    }
    merged["affect"] = list(merged.get("affect") or [])[-MAX_AFFECT_EPISODES:]
    merged["commitments"] = list(merged.get("commitments") or [])[-MAX_COMMITMENTS:]
    merged["perceptions"] = list(merged.get("perceptions") or [])[-MAX_PERCEPTIONS:]
    relationships = dict(merged.get("resident_relationships") or {})
    if len(relationships) > MAX_RESIDENT_RELATIONSHIPS:
        relationships = dict(
            sorted(
                relationships.items(),
                key=lambda item: (
                    float((item[1] or {}).get("familiarity") or 0.0),
                    item[0],
                ),
                reverse=True,
            )[:MAX_RESIDENT_RELATIONSHIPS]
        )
    merged["resident_relationships"] = relationships
    merged["active_goals"] = list(merged.get("active_goals") or [])[
        :MAX_ACTIVE_GOALS
    ]
    return merged


def enabled(life):
    return bool(life and life.get("enabled"))


def absolute_hour(day, hour):
    return max(0, (int(day) - 1) * 24 + int(hour))


def apply_body_delta(life, **deltas):
    if not enabled(life):
        return life
    body = dict(life.get("body") or {})
    for key, delta in deltas.items():
        if key not in BODY_KEYS:
            continue
        body[key] = clamp(body.get(key, 0.0) + float(delta))
    life["body"] = body
    return life


def set_body_condition(life, condition, severity):
    if not enabled(life) or condition not in BODY_KEYS:
        return life
    body = dict(life.get("body") or {})
    body[condition] = clamp(severity)
    life["body"] = body
    return life


def add_affect_episode(
    life,
    kind,
    intensity,
    *,
    cause,
    target_id=None,
    day=1,
    hour=0,
    half_life_hours=8.0,
):
    if not enabled(life):
        return None
    episode_id = int(life.get("next_affect_id") or 1)
    life["next_affect_id"] = episode_id + 1
    record = {
        "id": episode_id,
        "kind": str(kind),
        "intensity": clamp(intensity),
        "cause": str(cause or "something happened"),
        "target_id": target_id,
        "created_day": int(day),
        "created_hour": int(hour),
        "created_absolute_hour": absolute_hour(day, hour),
        "half_life_hours": max(0.25, float(half_life_hours)),
    }
    episodes = list(life.get("affect") or [])
    episodes.append(record)
    life["affect"] = episodes[-MAX_AFFECT_EPISODES:]
    return record


def _decayed_intensity(episode, now_absolute_hour):
    age = max(
        0.0,
        float(now_absolute_hour)
        - float(episode.get("created_absolute_hour") or 0.0),
    )
    half_life = max(0.25, float(episode.get("half_life_hours") or 8.0))
    return clamp(
        float(episode.get("intensity") or 0.0) * (0.5 ** (age / half_life))
    )


def decay_life_state(life, day, hour):
    """Decay only bounded, consequential state.  No hidden ambient simulation."""
    if not enabled(life):
        return life
    now = absolute_hour(day, hour)
    previous = life.get("last_decay_absolute_hour")
    if previous is not None and int(previous) == now:
        return life

    kept = []
    for episode in list(life.get("affect") or []):
        current = dict(episode)
        current["current_intensity"] = _decayed_intensity(current, now)
        if current["current_intensity"] >= 1.0:
            kept.append(current)
    life["affect"] = kept[-MAX_AFFECT_EPISODES:]
    life["last_decay_absolute_hour"] = now

    # Wetness, cold, intoxication, discomfort, and pain can ease gradually.
    # Injury and illness do not heal here because recovery should be caused by
    # explicit rest, treatment, or authored world systems.
    body = dict(life.get("body") or {})
    body["wet"] = clamp(body.get("wet", 0.0) - 4.0)
    body["cold"] = clamp(body.get("cold", 0.0) - 2.0)
    body["intoxication"] = clamp(body.get("intoxication", 0.0) - 3.0)
    body["discomfort"] = clamp(body.get("discomfort", 0.0) - 1.0)
    body["pain"] = clamp(
        max(
            body.get("injury", 0.0) * 0.35,
            body.get("pain", 0.0) - 1.5,
        )
    )
    life["body"] = body
    return life


def record_perception(
    life,
    *,
    kind,
    summary,
    source_id=None,
    target_id=None,
    confidence=0.7,
    salience=0.5,
    day=1,
    hour=0,
):
    """Store a bounded first-person observation, not server omniscience."""
    if not enabled(life):
        return None
    text = str(summary or "").strip()
    if not text:
        return None
    if not (
        text.startswith("I ")
        or text.startswith("My ")
        or text.startswith("I'm ")
        or text.startswith("I've ")
    ):
        text = "I noticed " + text[0].lower() + text[1:]
    record = {
        "kind": str(kind),
        "summary": text,
        "source_id": source_id,
        "target_id": target_id,
        "confidence": max(0.0, min(1.0, float(confidence))),
        "salience": max(0.0, min(1.0, float(salience))),
        "day": int(day),
        "hour": int(hour),
    }
    perceptions = list(life.get("perceptions") or [])
    perceptions.append(record)
    life["perceptions"] = perceptions[-MAX_PERCEPTIONS:]
    return record


def add_commitment(
    life,
    key,
    summary,
    *,
    target_id=None,
    logical_location=None,
    due_day=None,
    due_hour=None,
    priority=0.5,
    day=1,
    hour=0,
):
    if not enabled(life):
        return None
    commitments = list(life.get("commitments") or [])
    for existing in commitments:
        if existing.get("key") == key and existing.get("status") == "open":
            return existing

    commitment_id = int(life.get("next_commitment_id") or 1)
    life["next_commitment_id"] = commitment_id + 1
    text = str(summary or "").strip()
    if text and not text.startswith("I "):
        text = "I need to " + text[0].lower() + text[1:]
    record = {
        "id": commitment_id,
        "key": str(key),
        "summary": text or "I need to keep a commitment.",
        "target_id": target_id,
        "logical_location": logical_location,
        "due_day": None if due_day is None else int(due_day),
        "due_hour": None if due_hour is None else int(due_hour),
        "priority": max(0.0, min(1.0, float(priority))),
        "status": "open",
        "created_day": int(day),
        "created_hour": int(hour),
        "resolved_day": None,
        "resolved_hour": None,
    }
    commitments.append(record)
    life["commitments"] = commitments[-MAX_COMMITMENTS:]
    return record


def resolve_commitment(life, key, status, *, day=1, hour=0):
    if not enabled(life) or status not in {"fulfilled", "broken", "cancelled"}:
        return None
    commitments = list(life.get("commitments") or [])
    resolved = None
    for record in commitments:
        if record.get("key") == key and record.get("status") == "open":
            record["status"] = status
            record["resolved_day"] = int(day)
            record["resolved_hour"] = int(hour)
            resolved = record
            break
    life["commitments"] = commitments[-MAX_COMMITMENTS:]
    return resolved


def open_commitments(life):
    if not enabled(life):
        return []
    return [
        record
        for record in list(life.get("commitments") or [])
        if record.get("status") == "open"
    ]


def relationship_for(life, other_id):
    if not enabled(life):
        return None
    current = dict(
        (life.get("resident_relationships") or {}).get(str(other_id)) or {}
    )
    return {
        "resident_id": str(other_id),
        "familiarity": clamp(current.get("familiarity", 0.0)),
        "affinity": max(-100.0, min(100.0, float(current.get("affinity", 0.0)))),
        "trust": max(-100.0, min(100.0, float(current.get("trust", 0.0)))),
        "respect": max(-100.0, min(100.0, float(current.get("respect", 0.0)))),
        "fear": clamp(current.get("fear", 0.0)),
        "grievance": clamp(current.get("grievance", 0.0)),
        "debt": max(-100.0, min(100.0, float(current.get("debt", 0.0)))),
        "interactions": int(current.get("interactions") or 0),
        "last_day": current.get("last_day"),
    }


def record_social_event(
    life,
    other_id,
    *,
    kind,
    day=1,
    valence=0.0,
    familiarity=0.5,
    trust=0.0,
    respect=0.0,
    fear=0.0,
    grievance=0.0,
    debt=0.0,
):
    if not enabled(life):
        return None
    relationships = dict(life.get("resident_relationships") or {})
    rel = relationship_for(life, other_id)
    rel["familiarity"] = clamp(rel["familiarity"] + float(familiarity))
    rel["affinity"] = max(
        -100.0,
        min(100.0, rel["affinity"] + float(valence)),
    )
    rel["trust"] = max(-100.0, min(100.0, rel["trust"] + float(trust)))
    rel["respect"] = max(
        -100.0,
        min(100.0, rel["respect"] + float(respect)),
    )
    rel["fear"] = clamp(rel["fear"] + float(fear))
    rel["grievance"] = clamp(rel["grievance"] + float(grievance))
    rel["debt"] = max(-100.0, min(100.0, rel["debt"] + float(debt)))
    rel["interactions"] += 1
    rel["last_day"] = int(day)
    rel["last_kind"] = str(kind)
    relationships[str(other_id)] = rel

    if len(relationships) > MAX_RESIDENT_RELATIONSHIPS:
        ranked = sorted(
            relationships.items(),
            key=lambda item: (
                float((item[1] or {}).get("familiarity") or 0.0),
                int((item[1] or {}).get("interactions") or 0),
                item[0],
            ),
            reverse=True,
        )[:MAX_RESIDENT_RELATIONSHIPS]
        relationships = dict(ranked)

    life["resident_relationships"] = relationships
    return rel


def social_weight(life, other_id):
    """Cheap weight for choosing whom this resident is likely to approach."""
    rel = relationship_for(life, other_id)
    if rel is None:
        return 1.0
    score = (
        1.0
        + rel["familiarity"] / 60.0
        + rel["trust"] / 120.0
        + rel["affinity"] / 160.0
        - rel["fear"] / 180.0
        - rel["grievance"] / 200.0
    )
    return max(0.25, min(3.0, score))


def _commitment_due(record, day, hour):
    due_day = record.get("due_day")
    due_hour = record.get("due_hour")
    if due_day is None:
        return False
    now = absolute_hour(day, hour)
    due = absolute_hour(due_day, 23 if due_hour is None else due_hour)
    return now >= due


def derive_goals(life, needs, *, day=1, hour=0):
    """Return a small consequential goal set for engaged residents only."""
    if not enabled(life):
        return []
    goals = []
    body = dict(life.get("body") or {})
    needs = dict(needs or {})

    def add(key, priority, summary, logical_location=None, target_id=None):
        goals.append(
            {
                "key": key,
                "priority": float(priority),
                "summary": summary,
                "logical_location": logical_location,
                "target_id": target_id,
            }
        )

    if body.get("injury", 0.0) >= 65 or body.get("illness", 0.0) >= 65:
        add(
            "recover",
            0.98,
            "I need to get somewhere safe and recover.",
            logical_location="home",
        )
    elif body.get("pain", 0.0) >= 70:
        add(
            "protect_body",
            0.90,
            "I need to stop making this hurt worse.",
            logical_location="home",
        )

    if float(needs.get("safety", 80.0)) <= 25:
        add("safety", 0.97, "I need to get somewhere safe.", logical_location="home")
    if float(needs.get("fatigue", 0.0)) >= 92:
        add("rest", 0.93, "I need to rest.", logical_location="home")
    if float(needs.get("hunger", 0.0)) >= 92:
        add("eat", 0.91, "I need to eat.")

    for record in open_commitments(life):
        priority = 0.55 + 0.4 * float(record.get("priority") or 0.0)
        if _commitment_due(record, day, hour):
            priority += 0.15
        add(
            "commitment:" + str(record.get("key")),
            min(1.0, priority),
            record.get("summary") or "I need to keep a commitment.",
            logical_location=record.get("logical_location"),
            target_id=record.get("target_id"),
        )

    for episode in list(life.get("affect") or []):
        intensity = float(
            episode.get("current_intensity", episode.get("intensity", 0.0))
        )
        if episode.get("kind") == "fear" and intensity >= 60:
            add(
                "avoid:" + str(episode.get("target_id") or "threat"),
                min(0.95, 0.55 + intensity / 200.0),
                "I want to stay away from what frightened me.",
                target_id=episode.get("target_id"),
            )

    goals = sorted(
        goals,
        key=lambda item: (-float(item["priority"]), item["key"]),
    )[:MAX_ACTIVE_GOALS]
    life["active_goals"] = goals
    return goals


def schedule_override(life, needs, definition, *, day=1, hour=0, availability=None):
    """Return a location override only for a concrete high-priority goal."""
    if not enabled(life):
        return None
    goals = derive_goals(life, needs, day=day, hour=hour)
    availability = availability or {}
    home = definition.get("home_id")

    for goal in goals:
        if goal["priority"] < 0.85:
            continue
        logical = goal.get("logical_location")
        if logical == "home":
            logical = home
        if not logical:
            continue
        state = availability.get(logical)
        if isinstance(state, dict) and not state.get("available", True):
            continue
        if state is False:
            continue
        return {
            "logical_location": logical,
            "reason": goal["summary"],
            "goal_key": goal["key"],
            "priority": goal["priority"],
        }
    return None


def first_person_thoughts(life, needs=None, *, day=1, hour=0, limit=4):
    """Render internal English only on demand, never as an always-on loop."""
    if not enabled(life):
        return []
    thoughts = []
    body = dict(life.get("body") or {})
    if body.get("pain", 0.0) >= 35:
        thoughts.append("I'm hurting.")
    if body.get("cold", 0.0) >= 45:
        thoughts.append("I'm getting cold.")
    if body.get("wet", 0.0) >= 45:
        thoughts.append("My clothes are still wet.")
    if body.get("illness", 0.0) >= 45:
        thoughts.append("I don't feel well.")

    for goal in derive_goals(life, needs or {}, day=day, hour=hour):
        summary = str(goal.get("summary") or "").strip()
        if summary and summary not in thoughts:
            thoughts.append(summary)
        if len(thoughts) >= int(limit):
            break

    if len(thoughts) < int(limit):
        for perception in reversed(list(life.get("perceptions") or [])):
            summary = str(perception.get("summary") or "").strip()
            if summary and summary not in thoughts:
                thoughts.append(summary)
            if len(thoughts) >= int(limit):
                break
    return thoughts[: max(0, int(limit))]
