"""Persistent emergent resident population for Frankenstein Village.

Continuity is always active. Cognition is activated only when required.

The module owns production behavior around resident identity, schedules,
relationships, progressive detail, event wakeups, and fact claiming. Mutable
character state lives on each Evennia object. The only shared mutable state is
coordination state on the persistent resident_population script.
"""

from __future__ import annotations

import copy
import hashlib
import time

from evennia import create_object, create_script
from evennia.scripts.models import ScriptDB
from evennia.utils import search

from world.resident_data import (
    FACT_BY_ID,
    FACT_POOL,
    INTEREST_POOL,
    RESIDENT_BY_ID,
    RESIDENTS,
    SCHEMA_VERSION,
    projection_for,
    resolve_schedule,
    schedule_block,
)


REGISTRY_KEY = "resident_population"
DEPTH_ORDER = {"D": 0, "C": 1, "B": 2, "A": 3}
UP = {"D": 8.0, "C": 16.0, "B": 40.0}
DOWN = {"C": 1.5, "B": 8.0, "A": 22.0}
RESOLUTION = {"D": "automaton", "C": "reactive", "B": "engaged", "A": "focused"}
MEMORY_CAP = {"D": 0, "C": 5, "B": 30, "A": 60}
ENGAGEMENT_DECAY = 0.93


def _clock():
    try:
        clock = ScriptDB.objects.get(db_key="village_time")
        return int(clock.db.day or 1), int(clock.db.hour if clock.db.hour is not None else 21)
    except ScriptDB.DoesNotExist:
        return 1, 21


def _room(key):
    found = [obj for obj in search.search_object(key) if obj.key == key]
    return found[0] if found else None


def _stable_index(stable_id, namespace, modulo):
    if modulo <= 0:
        return 0
    raw = f"{stable_id}|{namespace}".encode("utf-8")
    return int.from_bytes(hashlib.sha256(raw).digest()[:8], "big") % modulo


def _depth_max(a, b):
    return a if DEPTH_ORDER.get(a, 0) >= DEPTH_ORDER.get(b, 0) else b


def _initial_interests(stable_id):
    first = _stable_index(stable_id, "interest:0", len(INTEREST_POOL))
    second = _stable_index(stable_id, "interest:1", len(INTEREST_POOL) - 1)
    if second >= first:
        second += 1
    return [INTEREST_POOL[first], INTEREST_POOL[second]]


def get_population_registry():
    try:
        return ScriptDB.objects.get(db_key=REGISTRY_KEY)
    except ScriptDB.DoesNotExist:
        return create_script(
            "typeclasses.scripts.ResidentPopulationRegistry",
            key=REGISTRY_KEY,
            persistent=True,
        )


def _fresh_state(definition):
    authored = definition.get("provenance") == "runtime_canon"
    initial_depth = "B" if authored else "D"
    return {
        "schema_version": SCHEMA_VERSION,
        "stable_id": definition["stable_id"],
        "simulation_resolution": "automaton",
        "engagement_tier": "D",
        "character_depth": initial_depth,
        "narrative_importance": 1 if authored else 0,
        "engagement": 0.0,
        "engagement_floor": 0.0,
        "last_interaction_day": None,
        "last_decay_day": None,
        "relationships": {},
        "interests": _initial_interests(definition["stable_id"]),
        "facts": [],
        "important_memories": [],
        "event_flags": {},
        "wake_reasons": [],
        "routine_override": None,
        "routine": {
            "day": None,
            "hour": None,
            "desired_location": definition["home_id"],
            "logical_location": definition["home_id"],
            "activity": "keeps ordinary household hours",
            "source": "initial",
            "reason": None,
        },
        "lifecycle": {
            "status": "active",
            "reason": None,
            "changed_day": None,
        },
        "relationship_constraints": {
            "eligible_by_age": definition.get("age_band") not in {"child", "teen"},
            "constraints": [],
        },
        "needs": {
            "fatigue": 20.0,
            "hunger": 25.0,
            "safety": 80.0,
            "affiliation": 45.0,
            "duty": 30.0,
        },
        "metrics": {
            "routine_resolutions": 0,
            "decision_evaluations": 0,
            "player_interactions": 0,
        },
    }


def _merge_state(definition, existing):
    state = _fresh_state(definition)
    if existing:
        old = copy.deepcopy(dict(existing))
        for key, value in old.items():
            if key in {"routine", "lifecycle", "needs", "metrics"} and isinstance(value, dict):
                merged = dict(state[key])
                merged.update(value)
                state[key] = merged
            else:
                state[key] = value
    state["schema_version"] = SCHEMA_VERSION
    state["stable_id"] = definition["stable_id"]
    state["interests"] = list(state.get("interests") or _initial_interests(definition["stable_id"]))
    state["facts"] = list(state.get("facts") or [])
    state["important_memories"] = list(state.get("important_memories") or [])
    state["relationships"] = dict(state.get("relationships") or {})
    state["event_flags"] = dict(state.get("event_flags") or {})
    state["wake_reasons"] = list(state.get("wake_reasons") or [])
    state["simulation_resolution"] = RESOLUTION.get(
        state.get("engagement_tier", "D"), "automaton"
    )
    return state


def resident_definition(obj_or_id):
    stable_id = obj_or_id if isinstance(obj_or_id, str) else obj_or_id.db.resident_id
    return RESIDENT_BY_ID.get(stable_id)


def resident_state(npc):
    definition = resident_definition(npc)
    if not definition:
        return None
    return _merge_state(definition, npc.db.resident_state)


def save_state(npc, state):
    npc.db.resident_state = copy.deepcopy(state)
    return state


def is_resident(obj):
    try:
        return bool(obj.tags.has("resident", category="system"))
    except Exception:
        return False


def all_residents():
    try:
        return list(search.search_tag("resident", category="system"))
    except Exception:
        return []


def _find_existing(definition):
    tagged = list(search.search_tag(definition["stable_id"], category="resident_id"))
    if tagged:
        return tagged[0]
    existing_key = definition.get("existing_key")
    if existing_key:
        found = [obj for obj in search.search_object(existing_key) if obj.key == existing_key]
        if found:
            return found[0]
    return None


def _generic_desc(definition, state):
    routine = state.get("routine") or {}
    activity = routine.get("activity") or "goes about ordinary village business"
    return (
        f"{definition['display_name']} is a village resident who works as "
        f"{definition['occupation']}. At present: {activity}."
    )


def _sync_generic_desc(npc, definition, state):
    if npc.typeclass_path == "typeclasses.characters.ResidentNPC":
        npc.db.desc = _generic_desc(definition, state)


def ensure_population():
    """Create or register the canonical launch-scale resident population."""
    registry = get_population_registry()
    created = 0
    registered = 0
    for definition in RESIDENTS:
        npc = _find_existing(definition)
        if npc is None:
            offstage = _room("Offstage")
            npc = create_object(
                "typeclasses.characters.ResidentNPC",
                key=definition["display_name"],
                location=offstage,
            )
            created += 1
        else:
            registered += 1

        npc.db.resident_id = definition["stable_id"]
        npc.tags.add("resident", category="system")
        npc.tags.add(definition["stable_id"], category="resident_id")
        state = _merge_state(definition, npc.db.resident_state)
        npc.db.resident_state = state
        _sync_generic_desc(npc, definition, state)

    day, hour = _clock()
    advance_population(day=day, hour=hour, emit=False)

    seed_background_rumors()

    metrics = dict(registry.db.metrics or {})
    metrics["population_size"] = len(RESIDENTS)
    metrics["last_build_created"] = created
    metrics["last_build_registered"] = registered
    registry.db.metrics = metrics
    return {
        "population_size": len(RESIDENTS),
        "created": created,
        "registered": registered,
    }


def seed_background_rumors():
    """Give a sparse deterministic subset of residents each canon rumor.

    Residents all participate in the rumor network, but they do not begin with
    omniscient village gossip. The initial exposure is sparse and reproducible.
    """
    try:
        from world.rumors import get_rumor_registry
        registry = get_rumor_registry()
    except Exception:
        return 0

    roots = [
        dict(rumor)
        for rumor in (registry.db.rumors or [])
        if rumor.get("canonical_seed_id") is not None
    ]
    seeded = 0
    for npc in all_residents():
        npc.tags.add("participant", category="rumor")
        definition = resident_definition(npc)
        if not definition:
            continue
        for root in roots:
            gate = _stable_index(
                definition["stable_id"],
                f"rumor-seed:{root['canonical_seed_id']}",
                100,
            )
            if gate >= 30:
                continue
            if registry.belief_for(npc, root["id"]):
                continue
            registry.hear_direct(
                root["id"],
                npc,
                source_label=root.get("source_actor") or "village talk",
                source_type=root.get("source_type") or "canon_teller",
                location=(resident_state(npc).get("routine") or {}).get(
                    "logical_location"
                ),
            )
            seeded += 1
    return seeded


def _availability():
    registry = get_population_registry()
    return copy.deepcopy(dict(registry.db.location_states or {}))


def set_location_availability(location_id, available, reason=None, event_id=None):
    registry = get_population_registry()
    states = copy.deepcopy(dict(registry.db.location_states or {}))
    states[location_id] = {
        "available": bool(available),
        "reason": reason,
        "event_id": event_id,
        "changed_at": time.time(),
    }
    registry.db.location_states = states
    return dict(states[location_id])


def location_state(location_id):
    return _availability().get(
        location_id,
        {"available": True, "reason": None, "event_id": None},
    )


def set_resident_deviation(npc, logical_location, until_day, until_hour, reason):
    state = resident_state(npc)
    if not state:
        return False
    state["routine_override"] = {
        "logical_location": logical_location,
        "until_day": int(until_day),
        "until_hour": int(until_hour),
        "reason": reason,
    }
    save_state(npc, state)
    return True


def _override_active(override, day, hour):
    if not override:
        return False
    end = (int(override.get("until_day", day)), int(override.get("until_hour", hour)))
    return (int(day), int(hour)) < end


def _resolve_target(definition, state, day, hour, availability):
    override = state.get("routine_override")
    if _override_active(override, day, hour):
        logical = override["logical_location"]
        status = availability.get(logical, {"available": True})
        if status.get("available", True):
            return {
                "start": hour,
                "end": hour + 1,
                "desired_location": logical,
                "logical_location": logical,
                "activity": f"deviates from routine: {override['reason']}",
                "source": "deviation",
                "reason": override["reason"],
            }
    elif override:
        state["routine_override"] = None

    current = (state.get("routine") or {}).get("logical_location")
    return resolve_schedule(
        definition,
        hour,
        availability=availability,
        current_location=current,
    )


def apply_need_delta(npc, **deltas):
    """Change the five production needs without forcing continuous thought."""
    state = resident_state(npc)
    if not state:
        return None
    needs = dict(state.get("needs") or {})
    for key, delta in deltas.items():
        if key not in needs:
            continue
        needs[key] = max(0.0, min(100.0, float(needs[key]) + float(delta)))
    state["needs"] = needs
    save_state(npc, state)
    return needs


def _need_override(definition, state):
    """Cheap utility boundary used only for awake or engaged residents."""
    metrics = dict(state.get("metrics") or {})
    metrics["decision_evaluations"] = int(metrics.get("decision_evaluations") or 0) + 1
    state["metrics"] = metrics

    needs = state.get("needs") or {}
    home = definition["home_id"]
    if float(needs.get("safety", 80)) <= 25:
        return home, "safety need overrides routine"
    if float(needs.get("fatigue", 20)) >= 92:
        return home, "fatigue overrides routine"
    if float(needs.get("hunger", 25)) >= 92:
        return home, "hunger overrides routine"
    return None


def _has_observer(room):
    if not room:
        return False
    return any(getattr(obj, "has_account", False) for obj in room.contents)


def _announce_move(npc, old_room, new_room, activity):
    if old_room and old_room != new_room and _has_observer(old_room):
        old_room.msg_contents(f"{npc.key} finishes up and heads on.")
    if new_room and old_room != new_room and _has_observer(new_room):
        new_room.msg_contents(f"{npc.key} arrives and {activity}.")


def advance_population(*, day=None, hour=None, emit=True):
    """Resolve all population-scheduled residents directly to current time.

    Skipped hours are not replayed. Cost depends on resident count, not elapsed
    world time.
    """
    if day is None or hour is None:
        now_day, now_hour = _clock()
        day = now_day if day is None else day
        hour = now_hour if hour is None else hour

    availability = _availability()
    registry = get_population_registry()
    resolved = 0
    moved = 0
    fallbacks = 0
    decisions = 0

    for npc in all_residents():
        definition = resident_definition(npc)
        if not definition or definition.get("schedule_engine") != "population":
            continue
        state = resident_state(npc)
        lifecycle = (state.get("lifecycle") or {}).get("status", "active")
        if lifecycle in {"dead", "departed"}:
            continue

        target = _resolve_target(definition, state, day, hour, availability)
        awake = bool(state.get("wake_reasons"))
        if state.get("simulation_resolution") != "automaton" or awake:
            before = int((state.get("metrics") or {}).get("decision_evaluations") or 0)
            override = _need_override(definition, state)
            after = int((state.get("metrics") or {}).get("decision_evaluations") or 0)
            decisions += max(0, after - before)
            if override:
                logical, reason = override
                target = {
                    **target,
                    "desired_location": target.get("desired_location"),
                    "logical_location": logical,
                    "source": "need_override",
                    "reason": reason,
                    "activity": "returns home because something more immediate matters",
                }
            state["wake_reasons"] = []

        previous = dict(state.get("routine") or {})
        state["routine"] = {
            "day": int(day),
            "hour": int(hour),
            "desired_location": target["desired_location"],
            "logical_location": target["logical_location"],
            "activity": target["activity"],
            "source": target["source"],
            "reason": target.get("reason"),
        }
        metrics = dict(state.get("metrics") or {})
        metrics["routine_resolutions"] = int(metrics.get("routine_resolutions") or 0) + 1
        state["metrics"] = metrics
        save_state(npc, state)
        _sync_generic_desc(npc, definition, state)
        resolved += 1
        if target["source"] == "fallback":
            fallbacks += 1

        physical_key = projection_for(target["logical_location"])
        new_room = _room(physical_key)
        old_room = npc.location
        if new_room and old_room != new_room:
            npc.move_to(new_room, quiet=True)
            moved += 1
            if emit:
                _announce_move(npc, old_room, new_room, target["activity"])
        elif previous.get("logical_location") != target["logical_location"]:
            # A logical move can happen entirely Offstage. Persist it without
            # inventing a visible transition.
            moved += 1

    metrics = dict(registry.db.metrics or {})
    metrics["last_population_resolved"] = resolved
    metrics["last_population_moved"] = moved
    metrics["last_population_fallbacks"] = fallbacks
    metrics["last_decision_evaluations"] = decisions
    metrics["last_tick_day"] = int(day)
    metrics["last_tick_hour"] = int(hour)
    registry.db.metrics = metrics
    return {
        "resolved": resolved,
        "moved": moved,
        "fallbacks": fallbacks,
        "decision_evaluations": decisions,
    }


def relationship_for(npc, player):
    state = resident_state(npc)
    if not state:
        return None
    key = str(player.id)
    rel = dict((state.get("relationships") or {}).get(key) or {})
    return {
        "player_id": player.id,
        "player_name": player.key,
        "familiarity": float(rel.get("familiarity") or 0.0),
        "affinity": float(rel.get("affinity") or 0.0),
        "trust": float(rel.get("trust") or 0.0),
        "respect": float(rel.get("respect") or 0.0),
        "fear": float(rel.get("fear") or 0.0),
        "grievance": float(rel.get("grievance") or 0.0),
        "debt": float(rel.get("debt") or 0.0),
        "attraction": float(rel.get("attraction") or 0.0),
        "interactions": int(rel.get("interactions") or 0),
        "last_day": rel.get("last_day"),
        "revealed_fact_ids": list(rel.get("revealed_fact_ids") or []),
    }


def _tier_after_gain(current, score, floor):
    score = max(float(score), float(floor))
    tier = current
    while tier in UP and score >= UP[tier]:
        tier = {"D": "C", "C": "B", "B": "A"}[tier]
    return tier


def _tier_after_decay(current, score, floor):
    score = max(float(score), float(floor))
    tier = current
    while tier != "D":
        threshold = DOWN[tier]
        if score >= threshold:
            break
        tier = {"A": "B", "B": "C", "C": "D"}[tier]
    return tier


def _on_role_shift(definition, hour, npc=None):
    if not definition.get("role_bound"):
        return False
    if definition.get("schedule_engine") == "legacy":
        if npc is None or npc.location is None:
            return False
        work_room = {
            "bram_v": "The Blood of the Vine",
        }.get(definition["stable_id"])
        return bool(work_room and npc.location.key == work_room)
    block = schedule_block(definition, hour)
    return block["desired_location"] != definition["home_id"]


def remember_important(npc, kind, summary, *, salience=0.5, day=None):
    state = resident_state(npc)
    if not state:
        return None
    depth = state.get("character_depth", "D")
    cap = MEMORY_CAP.get(depth, 0)
    if cap <= 0 and kind not in {"major_event", "lifecycle"}:
        return None
    if day is None:
        day, _hour = _clock()
    memories = list(state.get("important_memories") or [])
    record = {
        "day": int(day),
        "kind": kind,
        "summary": summary,
        "salience": float(salience),
    }
    memories.append(record)
    hard_cap = max(cap, 8 if kind in {"major_event", "lifecycle"} else cap)
    if hard_cap and len(memories) > hard_cap:
        memories = sorted(
            memories,
            key=lambda entry: (float(entry.get("salience") or 0), int(entry.get("day") or 0)),
        )[-hard_cap:]
    state["important_memories"] = memories
    save_state(npc, state)
    return record


def record_player_interaction(npc, player, *, kind="talk", depth=1.0):
    if not is_resident(npc) or not getattr(player, "has_account", False):
        return None
    definition = resident_definition(npc)
    state = resident_state(npc)
    day, hour = _clock()

    weights = {
        "talk": 1.0,
        "ask": 1.2,
        "transaction": 0.5,
        "gift": 2.0,
        "help": 3.0,
    }
    amount = float(depth) * weights.get(kind, 1.0)
    if _on_role_shift(definition, hour, npc=npc):
        amount *= 0.25

    relationships = dict(state.get("relationships") or {})
    key = str(player.id)
    first = key not in relationships
    rel = relationship_for(npc, player)
    rel["familiarity"] = min(100.0, rel["familiarity"] + amount)
    rel["affinity"] = max(-100.0, min(100.0, rel["affinity"] + 0.12 * amount))
    rel["trust"] = max(-100.0, min(100.0, rel["trust"] + 0.08 * amount))
    rel["respect"] = max(-100.0, min(100.0, rel["respect"] + 0.04 * amount))
    rel["interactions"] += 1
    rel["last_day"] = day
    relationships[key] = rel
    state["relationships"] = relationships

    score = float(state.get("engagement") or 0.0) + amount + (1.0 if first else 0.0)
    state["engagement"] = score
    state["last_interaction_day"] = day
    old_tier = state.get("engagement_tier", "D")
    new_tier = _tier_after_gain(
        old_tier,
        score,
        state.get("engagement_floor") or 0.0,
    )
    state["engagement_tier"] = new_tier
    state["simulation_resolution"] = RESOLUTION[new_tier]
    state["character_depth"] = _depth_max(
        state.get("character_depth", "D"),
        new_tier,
    )
    metrics = dict(state.get("metrics") or {})
    metrics["player_interactions"] = int(metrics.get("player_interactions") or 0) + 1
    state["metrics"] = metrics
    save_state(npc, state)

    if first or (kind in {"gift", "help"} and DEPTH_ORDER[state["character_depth"]] >= 2):
        remember_important(
            npc,
            "player",
            f"{'met' if first else kind} {player.key}",
            salience=0.45 if first else 0.7,
            day=day,
        )
    return relationship_for(npc, player)


def decay_engagement(day=None):
    if day is None:
        day, _hour = _clock()
    changed = 0
    for npc in all_residents():
        state = resident_state(npc)
        last = state.get("last_decay_day")
        if last is None:
            state["last_decay_day"] = int(day)
            save_state(npc, state)
            continue
        elapsed = max(0, int(day) - int(last))
        if elapsed <= 0:
            continue
        state["engagement"] = float(state.get("engagement") or 0.0) * (
            ENGAGEMENT_DECAY ** elapsed
        )
        old = state.get("engagement_tier", "D")
        new = _tier_after_decay(
            old,
            state["engagement"],
            state.get("engagement_floor") or 0.0,
        )
        state["engagement_tier"] = new
        state["simulation_resolution"] = RESOLUTION[new]
        state["last_decay_day"] = int(day)
        # Character depth, facts, relationships, and memories intentionally
        # remain untouched here.
        save_state(npc, state)
        if new != old:
            changed += 1
    return changed


def ratchet_engagement(npc, *, minimum_tier="C", floor=6.0, reason="major event"):
    state = resident_state(npc)
    if not state:
        return None
    state["engagement_floor"] = max(float(state.get("engagement_floor") or 0.0), float(floor))
    current = state.get("engagement_tier", "D")
    if DEPTH_ORDER[current] < DEPTH_ORDER[minimum_tier]:
        current = minimum_tier
    state["engagement_tier"] = current
    state["simulation_resolution"] = RESOLUTION[current]
    state["character_depth"] = _depth_max(state.get("character_depth", "D"), current)
    state["wake_reasons"] = list(state.get("wake_reasons") or []) + [reason]
    save_state(npc, state)
    remember_important(npc, "major_event", reason, salience=0.9)
    return state


def _claims():
    return copy.deepcopy(dict(get_population_registry().db.fact_claims or {}))


def _fact_available(fact, claims):
    current = list(claims.get(fact["id"]) or [])
    if fact["claim"] == "reusable":
        return True
    limit = int(fact.get("limit") or 1)
    return len(current) < limit


def assign_fact(npc, *, class_hint=None):
    """Assign one persistent fact, honoring unique and limited claims."""
    definition = resident_definition(npc)
    state = resident_state(npc)
    if not definition or not state:
        return None
    existing_ids = {entry["fact_id"] for entry in state.get("facts") or []}
    claims = _claims()

    if class_hint is None:
        roll = _stable_index(
            definition["stable_id"],
            f"fact-class:{len(existing_ids)}",
            100,
        )
        class_hint = "ordinary" if roll < 90 else "serious" if roll < 98 else "gothic"

    minor = definition.get("age_band") in {"child", "teen"}
    candidates = []
    for fact in FACT_POOL:
        if fact["id"] in existing_ids or fact["class"] != class_hint:
            continue
        if minor and fact["class"] != "ordinary":
            continue
        if _fact_available(fact, claims):
            candidates.append(fact)

    if not candidates and class_hint != "ordinary":
        return assign_fact(npc, class_hint="ordinary")
    if not candidates:
        return None

    idx = _stable_index(
        definition["stable_id"],
        f"fact:{class_hint}:{len(existing_ids)}",
        len(candidates),
    )
    fact = dict(candidates[idx])
    day, _hour = _clock()
    record = {
        "fact_id": fact["id"],
        "class": fact["class"],
        "text": fact["text"],
        "assigned_day": day,
        "provenance": "resident_fact_repository",
    }
    facts = list(state.get("facts") or [])
    facts.append(record)
    state["facts"] = facts
    save_state(npc, state)

    claims.setdefault(fact["id"], [])
    if definition["stable_id"] not in claims[fact["id"]]:
        claims[fact["id"]].append(definition["stable_id"])
    registry = get_population_registry()
    registry.db.fact_claims = claims
    return record


def reveal_fact(npc, player, fact):
    state = resident_state(npc)
    relationships = dict(state.get("relationships") or {})
    key = str(player.id)
    rel = relationship_for(npc, player)
    known = list(rel.get("revealed_fact_ids") or [])
    if fact["fact_id"] not in known:
        known.append(fact["fact_id"])
    rel["revealed_fact_ids"] = known
    relationships[key] = rel
    state["relationships"] = relationships
    save_state(npc, state)
    return fact


def facts_known_by_player(npc, player):
    state = resident_state(npc)
    rel = relationship_for(npc, player)
    known = set(rel.get("revealed_fact_ids") or [])
    return [fact for fact in state.get("facts") or [] if fact["fact_id"] in known]


def expose_fact_as_rumor(npc, fact_id, *, source_actor=None):
    """Explicitly expose a fact into the rumor graph. Assignment alone is silent."""
    state = resident_state(npc)
    fact = next(
        (entry for entry in state.get("facts") or [] if entry["fact_id"] == fact_id),
        None,
    )
    if not fact:
        return None
    from world.rumors import publish_public_rumor

    return publish_public_rumor(
        f"{npc.key} {fact['text']}.",
        source_actor=source_actor or npc.key,
        source_type="resident_fact",
        subject=f"resident_fact:{fact_id}",
        family=f"resident_fact:{npc.db.resident_id}",
        confidence=0.48,
        emotional_charge=0.35,
    )


def _kin_names(definition):
    names = []
    for stable_id in definition.get("kin") or ():
        kin = RESIDENT_BY_ID.get(stable_id)
        if kin:
            names.append(kin["display_name"])
    return names


def _current_fact_for_revelation(npc, player, *, secret=False):
    state = resident_state(npc)
    rel = relationship_for(npc, player)
    facts = list(state.get("facts") or [])
    known = set(rel.get("revealed_fact_ids") or [])
    hidden = [fact for fact in facts if fact["fact_id"] not in known]
    if hidden:
        return hidden[0]

    depth = state.get("character_depth", "D")
    if secret:
        if DEPTH_ORDER[depth] < DEPTH_ORDER["B"]:
            return None
        # Even intimate revelation strongly favors ordinary/serious truths.
        fact = assign_fact(npc)
    else:
        if DEPTH_ORDER[depth] < DEPTH_ORDER["C"]:
            return None
        fact = assign_fact(npc, class_hint="ordinary")
    return fact


def share_held_rumor(npc, player):
    try:
        from world.rumors import get_rumor_registry
        registry = get_rumor_registry()
        beliefs = list(registry.beliefs_for(npc).values())
        if not beliefs:
            return None
        belief = sorted(
            beliefs,
            key=lambda entry: (
                float(entry.get("confidence") or 0.0),
                float(entry.get("heard_at") or 0.0),
            ),
            reverse=True,
        )[0]
        result = registry.transmit(
            belief["rumor_id"],
            npc,
            player,
            location=npc.location.key if npc.location else None,
            force_accept=True,
        )
        return result
    except Exception:
        return None


def generic_talk_line(npc, player):
    definition = resident_definition(npc)
    state = resident_state(npc)
    rel = relationship_for(npc, player)
    routine = state.get("routine") or {}

    if routine.get("reason"):
        reason = str(routine["reason"]).replace("_", " ")
        return f"Plans changed today. {reason}. I am making do."

    if rel["familiarity"] >= 8:
        return (
            f"Back again, {player.key}. You know how it is. "
            f"At present: {routine.get('activity') or 'keeping busy'}."
        )
    if _on_role_shift(definition, _clock()[1], npc=npc):
        return "Good day. I am working just now, but I can spare a word."
    return f"Good day. I am {definition['display_name']}. I work as {definition['occupation']}."


def generic_ask_line(npc, player, topic):
    definition = resident_definition(npc)
    state = resident_state(npc)
    rel = relationship_for(npc, player)
    t = topic.lower().strip()

    if any(word in t for word in ("rumor", "rumour", "gossip", "talk")):
        result = share_held_rumor(npc, player)
        if result:
            return f"{result['claim']} That is the version I heard."
        return "Nothing I would swear to today."

    if any(word in t for word in ("family", "kin", "relative", "household")):
        names = _kin_names(definition)
        if not names:
            return "No family here that I make other people's business."
        return "My people here are " + ", ".join(names) + "."

    if any(word in t for word in ("work", "job", "trade", "occupation")):
        return f"I work as {definition['occupation']}. Most days that is enough explanation."

    if any(word in t for word in ("interest", "hobby", "like", "enjoy")):
        interests = list(state.get("interests") or [])
        return "When there is time, I have a weakness for " + " and ".join(interests[:2]) + "."

    if any(word in t for word in ("where", "routine", "today", "school")):
        routine = state.get("routine") or {}
        if routine.get("reason"):
            return (
                f"I should have been {routine.get('activity')}, but "
                f"{str(routine['reason']).replace('_', ' ')} changed that."
            )
        return f"Today I am {routine.get('activity') or 'keeping my usual hours'}."

    if any(word in t for word in ("secret", "hide", "hiding")):
        if rel["familiarity"] < 16 or rel["trust"] < 1.0:
            return "That is a quick road to a closed door."
        fact = _current_fact_for_revelation(npc, player, secret=True)
        if not fact:
            return "There is nothing more I mean to give you today."
        reveal_fact(npc, player, fact)
        return f"All right. Keep this where I put it: I {fact['text']}."

    if any(word in t for word in ("past", "history", "before", "story")):
        if rel["familiarity"] < 8:
            return "We have not known each other long enough for old stories."
        fact = _current_fact_for_revelation(npc, player, secret=False)
        if not fact:
            return "Most of my past is exactly as ordinary as it sounds."
        reveal_fact(npc, player, fact)
        return f"Since you keep asking: I {fact['text']}."

    return None


def wake_resident(npc, reason, *, event_id=None, importance_delta=0.25):
    state = resident_state(npc)
    if not state:
        return None
    wakes = list(state.get("wake_reasons") or [])
    marker = reason if event_id is None else f"{reason}:{event_id}"
    if marker not in wakes:
        wakes.append(marker)
    state["wake_reasons"] = wakes[-12:]
    state["narrative_importance"] = max(
        0.0,
        min(3.0, float(state.get("narrative_importance") or 0.0) + float(importance_delta)),
    )
    save_state(npc, state)
    return state


def set_lifecycle(npc, status, *, reason=None, day=None):
    if status not in {"active", "retired", "dead", "departed"}:
        raise ValueError(f"invalid resident lifecycle: {status}")
    state = resident_state(npc)
    if not state:
        return None
    if day is None:
        day, _hour = _clock()
    state["lifecycle"] = {
        "status": status,
        "reason": reason,
        "changed_day": int(day),
    }
    save_state(npc, state)
    remember_important(
        npc,
        "lifecycle",
        f"{status}: {reason or 'no reason recorded'}",
        salience=1.0,
        day=day,
    )
    return state


def _resident_by_stable_id(stable_id):
    tagged = list(search.search_tag(stable_id, category="resident_id"))
    return tagged[0] if tagged else None


def consume_world_event(event):
    """Consume structured world events without converting prose back into state."""
    if not event:
        return []
    kind = event.get("kind")
    payload = dict(event.get("payload") or {})
    event_id = event.get("id")
    affected = set()

    location_id = payload.get("location_id") or payload.get("target_location")
    if kind in {"building_destroyed", "location_closed"} and location_id:
        set_location_availability(
            location_id,
            False,
            reason=payload.get("cause") or f"{location_id}_{kind}",
            event_id=event_id,
        )
    elif kind in {"building_restored", "location_opened"} and location_id:
        set_location_availability(
            location_id,
            True,
            reason=None,
            event_id=event_id,
        )

    explicit = list(payload.get("resident_ids") or payload.get("witnesses") or [])
    target_id = payload.get("resident_id") or payload.get("target_resident_id")
    if target_id:
        explicit.append(target_id)
    for stable_id in explicit:
        if stable_id in RESIDENT_BY_ID:
            affected.add(stable_id)

    if location_id:
        for npc in all_residents():
            state = resident_state(npc)
            definition = resident_definition(npc)
            routine = state.get("routine") or {}
            block = schedule_block(definition, _clock()[1])
            if (
                routine.get("logical_location") == location_id
                or block.get("desired_location") == location_id
            ):
                affected.add(definition["stable_id"])

    if target_id and target_id in RESIDENT_BY_ID:
        definition = RESIDENT_BY_ID[target_id]
        for kin_id in definition.get("kin") or ():
            if kin_id in RESIDENT_BY_ID:
                affected.add(kin_id)

    touched = []
    for stable_id in sorted(affected):
        npc = _resident_by_stable_id(stable_id)
        if not npc:
            continue
        state = resident_state(npc)
        flags = dict(state.get("event_flags") or {})
        flags[str(event_id)] = {
            "kind": kind,
            "payload": payload,
            "recorded_at": event.get("recorded_at"),
        }
        state["event_flags"] = flags
        save_state(npc, state)
        wake_resident(npc, kind or "world_event", event_id=event_id)
        if kind in {"death", "resident_death"} and stable_id == target_id:
            set_lifecycle(npc, "dead", reason=payload.get("cause") or "world event")
        elif kind in {"departure", "resident_departure"} and stable_id == target_id:
            set_lifecycle(npc, "departed", reason=payload.get("cause") or "world event")
        if kind in {"death", "resident_death", "marriage", "heroism"}:
            ratchet_engagement(
                npc,
                minimum_tier="C" if kind != "heroism" else "B",
                floor=10.0 if kind != "heroism" else 18.0,
                reason=f"{kind} event",
            )
        touched.append(stable_id)
    return touched


def note_rumor_exposure(actor, rumor_id):
    if not actor or not is_resident(actor):
        return None
    return wake_resident(
        actor,
        f"rumor:{rumor_id}",
        importance_delta=0.05,
    )


MASS_ALWAYS = {
    "mother_bell",
    "bess_bell",
    "young_tam_bell",
    "wren_vessey",
    "marta_kovacs",
}
MASS_NEVER = {
    "bram_v",
    "janos",
    "lucian_deville",
    "miklos_farkas",
    "elias_dorn",
    "sorin_dragomir",
}


def attends_sunday_mass(npc):
    """Deterministic household-aware attendance for background residents."""
    definition = resident_definition(npc)
    if not definition:
        return False
    stable_id = definition["stable_id"]
    if stable_id in MASS_ALWAYS:
        return True
    if stable_id in MASS_NEVER:
        return False
    if definition.get("schedule_engine") != "population":
        return False
    household = definition["household_id"]
    # Households tend to attend together. Work and authored exceptions above
    # can override this inexpensive default.
    return _stable_index(household, "sunday-mass", 100) < 58


def gather_population_for_mass(day):
    moved = []
    for npc in all_residents():
        if not attends_sunday_mass(npc):
            continue
        set_resident_deviation(
            npc,
            "church",
            until_day=day,
            until_hour=11,
            reason="Sunday mass",
        )
        moved.append(npc.db.resident_id)
    advance_population(day=day, hour=10, emit=True)
    return moved


def population_tick(*, day=None, hour=None):
    if day is None or hour is None:
        current_day, current_hour = _clock()
        day = current_day if day is None else day
        hour = current_hour if hour is None else hour
    decay_engagement(day)
    return advance_population(day=day, hour=hour)


def population_snapshot():
    result = []
    for npc in all_residents():
        definition = resident_definition(npc)
        state = resident_state(npc)
        result.append({
            "stable_id": definition["stable_id"],
            "name": npc.key,
            "occupation": definition["occupation"],
            "household": definition["household_id"],
            "logical_location": (state.get("routine") or {}).get("logical_location"),
            "activity": (state.get("routine") or {}).get("activity"),
            "lifecycle": (state.get("lifecycle") or {}).get("status"),
            "simulation_resolution": state.get("simulation_resolution"),
            "engagement_tier": state.get("engagement_tier"),
            "character_depth": state.get("character_depth"),
            "narrative_importance": state.get("narrative_importance"),
            "fact_count": len(state.get("facts") or []),
            "relationship_count": len(state.get("relationships") or {}),
        })
    return sorted(result, key=lambda entry: entry["stable_id"])
