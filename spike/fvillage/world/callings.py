"""Persistent social-profession state for player masks.

Callings are social roles, not combat classes. The active calling controls the
professional identity a mask is currently exercising. Old calling records are
retained so respecialization changes the present without deleting biography.

This module intentionally does not invent automatic promotion thresholds.
Participation is recorded as structured evidence for later authored promotion
gates. Master is the current authority ceiling, and only the active calling can
exercise Master authority at a given time.
"""

from __future__ import annotations

import copy

from evennia.scripts.models import ScriptDB


SCHEMA_VERSION = 1
RANK_APPRENTICE = "apprentice"
RANK_MASTER = "master"
RANKS = (RANK_APPRENTICE, RANK_MASTER)

CALLINGS = {
    "innkeep": {
        "display": "Innkeep",
        "summary": "Hospitality, rooms, tabs, messages, and house responsibility.",
    },
    "chronicler": {
        "display": "Chronicler",
        "summary": "Records, testimony, provenance, indexing, and public memory.",
    },
    "smith": {
        "display": "Smith",
        "summary": "Repair, tools, materials, commissions, and maker provenance.",
    },
    "healer": {
        "display": "Healer",
        "summary": "Care, medicines, case notes, scarcity, and diagnosis.",
    },
    "merchant": {
        "display": "Merchant",
        "summary": "Supply, prices, credit, contracts, and procurement.",
    },
    "wanderer": {
        "display": "Wanderer",
        "summary": "Routes, travel conditions, guiding, and courier work.",
    },
    "performer": {
        "display": "Performer",
        "summary": "Music, stories, public gatherings, requests, and satire.",
    },
    "detective": {
        "display": "Detective",
        "summary": "Cases, evidence, interviews, theory, and contradiction.",
    },
    "hound": {
        "display": "Hound",
        "summary": "Patrols, field investigation, protection, and anomaly reports.",
    },
}

CALLING_ALIASES = {
    "hunter": "hound",
    "hunter (hound)": "hound",
    "barkeep": "innkeep",
    "innkeeper": "innkeep",
    "record keeper": "chronicler",
}


def _clock():
    try:
        clock = ScriptDB.objects.get(db_key="village_time")
        return (
            int(clock.db.day or 1),
            int(clock.db.hour if clock.db.hour is not None else 21),
        )
    except ScriptDB.DoesNotExist:
        return 1, 21


def resolve_calling(value):
    """Resolve player-facing calling text to one canonical slug."""
    token = str(value or "").strip().lower()
    if token in {"", "none", "no calling", "unaffiliated"}:
        return None
    token = CALLING_ALIASES.get(token, token)
    return token if token in CALLINGS else False


def calling_label(slug):
    definition = CALLINGS.get(slug) or {}
    return definition.get("display") or str(slug or "No calling")


def _fresh_state():
    return {
        "schema_version": SCHEMA_VERSION,
        "active": None,
        "records": {},
        "history": [],
        "relations": [],
    }


def calling_state(mask):
    """Return a normalized plain calling state for one mask."""
    raw = getattr(mask.db, "calling_state", None)
    state = _fresh_state()
    if raw:
        old = copy.deepcopy(dict(raw))
        state["active"] = old.get("active")
        state["records"] = {
            str(key): copy.deepcopy(dict(value))
            for key, value in dict(old.get("records") or {}).items()
            if key in CALLINGS
        }
        state["history"] = [
            copy.deepcopy(dict(item))
            for item in list(old.get("history") or [])
        ]
        state["relations"] = [
            copy.deepcopy(dict(item))
            for item in list(old.get("relations") or [])
        ]
    if state["active"] not in CALLINGS:
        state["active"] = None
    state["schema_version"] = SCHEMA_VERSION
    return state


def _save(mask, state):
    mask.db.calling_state = copy.deepcopy(state)
    return calling_state(mask)


def _history_entry(action, **details):
    day, hour = _clock()
    return {
        "action": str(action),
        "day": int(day),
        "hour": int(hour),
        **details,
    }


def _new_record(slug):
    day, hour = _clock()
    return {
        "calling": slug,
        "rank": RANK_APPRENTICE,
        "first_joined_day": int(day),
        "first_joined_hour": int(hour),
        "mastered_day": None,
        "mastered_hour": None,
        "mastery_reason": None,
        "mastery_source_event_id": None,
        "participation": {},
    }


def active_calling(mask):
    return calling_state(mask).get("active")


def calling_record(mask, calling=None):
    state = calling_state(mask)
    slug = state.get("active") if calling is None else resolve_calling(calling)
    if not slug or slug is False:
        return None
    record = (state.get("records") or {}).get(slug)
    return copy.deepcopy(dict(record)) if record else None


def active_rank(mask):
    record = calling_record(mask)
    return record.get("rank") if record else None


def choose_calling(mask, calling):
    """Choose or respecialize a mask without erasing earlier profession history."""
    slug = resolve_calling(calling)
    if slug is False:
        return None, "No such calling is recognized by the village."

    state = calling_state(mask)
    previous = state.get("active")
    if previous != slug and active_relations(mask):
        return (
            None,
            "End the active apprenticeship before changing callings. "
            "Professional obligations do not disappear through respecialization.",
        )
    if previous == slug:
        return {
            "state": state,
            "record": calling_record(mask, slug) if slug else None,
            "changed": False,
        }, None

    if slug is None:
        state["active"] = None
        if previous:
            state["history"].append(
                _history_entry("left_active_calling", calling=previous)
            )
        return {
            "state": _save(mask, state),
            "record": None,
            "changed": bool(previous),
        }, None

    records = dict(state.get("records") or {})
    first_time = slug not in records
    if first_time:
        records[slug] = _new_record(slug)
    state["records"] = records
    state["active"] = slug
    action = "joined_calling" if previous is None else "respecialized"
    state["history"].append(
        _history_entry(
            action,
            calling=slug,
            previous_calling=previous,
            returning=not first_time,
        )
    )
    state = _save(mask, state)
    return {
        "state": state,
        "record": copy.deepcopy(state["records"][slug]),
        "changed": True,
    }, None


def record_participation(mask, metric, amount=1, *, calling=None):
    """Record real work for the active profession without auto-promoting it."""
    state = calling_state(mask)
    active = state.get("active")
    expected = resolve_calling(calling) if calling is not None else active
    if not active or expected is False or expected != active:
        return None
    record = copy.deepcopy(dict(state["records"].get(active) or _new_record(active)))
    counters = dict(record.get("participation") or {})
    key = str(metric or "").strip().lower().replace(" ", "_")
    if not key:
        return None
    counters[key] = int(counters.get(key) or 0) + int(amount)
    record["participation"] = counters
    state["records"][active] = record
    _save(mask, state)
    return int(counters[key])


def promote_to_master(mask, *, reason, source_event_id=None):
    """Authored promotion gate. There is deliberately no player command for this."""
    state = calling_state(mask)
    active = state.get("active")
    if not active:
        return None, "A mask must have an active calling before it can be promoted."
    record = copy.deepcopy(dict(state["records"].get(active) or _new_record(active)))
    if record.get("rank") == RANK_MASTER:
        return copy.deepcopy(record), None
    day, hour = _clock()
    record["rank"] = RANK_MASTER
    record["mastered_day"] = int(day)
    record["mastered_hour"] = int(hour)
    record["mastery_reason"] = str(reason or "authored promotion")
    record["mastery_source_event_id"] = source_event_id
    state["records"][active] = record
    state["history"].append(
        _history_entry(
            "promoted_master",
            calling=active,
            reason=record["mastery_reason"],
            source_event_id=source_event_id,
        )
    )
    _save(mask, state)
    return copy.deepcopy(record), None


def _relation_id(calling, mentor, apprentice):
    return f"{calling}:{getattr(mentor, 'id', None)}:{getattr(apprentice, 'id', None)}"


def active_relations(mask, role=None):
    state = calling_state(mask)
    rows = [
        copy.deepcopy(dict(item))
        for item in state.get("relations") or []
        if item.get("status") == "active"
    ]
    if role:
        rows = [item for item in rows if item.get("role") == role]
    return rows


def create_apprenticeship(mentor, apprentice):
    """Create one same-calling Master-to-Apprentice social relation."""
    if mentor is apprentice or getattr(mentor, "id", None) == getattr(apprentice, "id", None):
        return None, "A mask cannot apprentice itself."
    mentor_calling = active_calling(mentor)
    apprentice_calling = active_calling(apprentice)
    if not mentor_calling or mentor_calling != apprentice_calling:
        return None, "Mentor and apprentice must currently practice the same calling."
    if active_rank(mentor) != RANK_MASTER:
        return None, "Only a Master in the active calling can take an apprentice."
    if active_rank(apprentice) != RANK_APPRENTICE:
        return None, "The invited mask must currently be an Apprentice in that calling."

    relation_id = _relation_id(mentor_calling, mentor, apprentice)
    for relation in active_relations(apprentice, role="apprentice"):
        if relation.get("calling") == mentor_calling:
            if relation.get("relation_id") == relation_id:
                return copy.deepcopy(relation), None
            return None, "That Apprentice already has an active mentor in this calling."

    day, hour = _clock()
    base = {
        "relation_id": relation_id,
        "calling": mentor_calling,
        "mentor_mask_id": getattr(mentor, "id", None),
        "mentor_mask": getattr(mentor, "key", None),
        "apprentice_mask_id": getattr(apprentice, "id", None),
        "apprentice_mask": getattr(apprentice, "key", None),
        "started_day": int(day),
        "started_hour": int(hour),
        "status": "active",
    }

    mentor_state = calling_state(mentor)
    apprentice_state = calling_state(apprentice)
    mentor_relation = {**base, "role": "mentor"}
    apprentice_relation = {**base, "role": "apprentice"}
    mentor_state["relations"].append(mentor_relation)
    apprentice_state["relations"].append(apprentice_relation)
    mentor_state["history"].append(
        _history_entry(
            "apprentice_taken",
            calling=mentor_calling,
            counterpart_mask_id=getattr(apprentice, "id", None),
            counterpart_mask=getattr(apprentice, "key", None),
        )
    )
    apprentice_state["history"].append(
        _history_entry(
            "mentor_joined",
            calling=mentor_calling,
            counterpart_mask_id=getattr(mentor, "id", None),
            counterpart_mask=getattr(mentor, "key", None),
        )
    )
    _save(mentor, mentor_state)
    _save(apprentice, apprentice_state)
    return copy.deepcopy(apprentice_relation), None


def end_apprenticeship(mentor, apprentice, *, reason="ended"):
    """Close a shared apprenticeship record on both masks."""
    calling = active_calling(mentor)
    if not calling:
        return None, "The mentor has no active calling."
    relation_id = _relation_id(calling, mentor, apprentice)
    changed = False
    for owner in (mentor, apprentice):
        state = calling_state(owner)
        relations = []
        owner_changed = False
        for item in state.get("relations") or []:
            row = copy.deepcopy(dict(item))
            if row.get("relation_id") == relation_id and row.get("status") == "active":
                row["status"] = "ended"
                day, hour = _clock()
                row["ended_day"] = int(day)
                row["ended_hour"] = int(hour)
                row["ended_reason"] = str(reason)
                owner_changed = True
            relations.append(row)
        if owner_changed:
            state["relations"] = relations
            state["history"].append(
                _history_entry(
                    "apprenticeship_ended",
                    calling=calling,
                    relation_id=relation_id,
                    reason=str(reason),
                )
            )
            _save(owner, state)
            changed = True
    if not changed:
        return None, "No active apprenticeship connects those masks."
    return {"relation_id": relation_id, "status": "ended"}, None

def withdraw_apprenticeship(apprentice, *, reason="withdrawn_by_apprentice"):
    """Let an Apprentice end their own active relation without needing the mentor online."""
    relations = active_relations(apprentice, role="apprentice")
    if not relations:
        return None, "This mask has no active apprenticeship to withdraw from."
    relation = relations[0]
    mentor_id = relation.get("mentor_mask_id")
    mentor = None
    if mentor_id is not None:
        try:
            from evennia.utils import search
            found = search.search_object(f"#{int(mentor_id)}")
            mentor = next(
                (obj for obj in found if getattr(obj, "id", None) == int(mentor_id)),
                None,
            )
        except Exception:
            mentor = None

    if mentor is not None:
        return end_apprenticeship(
            mentor,
            apprentice,
            reason=reason,
        )

    state = calling_state(apprentice)
    relation_id = relation.get("relation_id")
    day, hour = _clock()
    rows = []
    for item in state.get("relations") or []:
        row = copy.deepcopy(dict(item))
        if row.get("relation_id") == relation_id and row.get("status") == "active":
            row["status"] = "ended"
            row["ended_day"] = int(day)
            row["ended_hour"] = int(hour)
            row["ended_reason"] = str(reason)
            row["counterpart_missing"] = True
        rows.append(row)
    state["relations"] = rows
    state["history"].append(
        _history_entry(
            "apprenticeship_ended",
            calling=relation.get("calling"),
            relation_id=relation_id,
            reason=str(reason),
            counterpart_missing=True,
        )
    )
    _save(apprentice, state)
    return {
        "relation_id": relation_id,
        "status": "ended",
        "counterpart_missing": True,
    }, None

