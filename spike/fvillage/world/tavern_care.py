"""Purpose-built cross-calling care case at the Blood of the Vine.

The patient state lives in Resident Life, the meal is an existing finite
consumable, professional authority comes from the calling system, and the
SituationRegistry keeps only the authored case/provenance record.
"""

from __future__ import annotations

import copy

from evennia.scripts.models import ScriptDB
from evennia.utils import search

from world.callings import active_calling, record_participation
from world.object_properties import mechanical_value
from world.residents import (
    add_resident_commitment,
    apply_resident_condition,
    record_player_interaction,
    record_resident_perception,
    resident_state,
    resolve_resident_commitment,
)
from world.situations import (
    TAVERN_COLD_CARE_ID,
    ensure_situations,
    get_situation,
    get_situation_registry,
)


PATIENT_ID = "silas_crowe"
PATIENT_KEY = "Silas Crowe"
RESOURCE_KEY = "a bowl of stew"
COMMITMENT_KEY = "warm_after_hunt"


def _clock():
    try:
        clock = ScriptDB.objects.get(db_key="village_time")
        return (
            int(clock.db.day or 1),
            int(clock.db.hour if clock.db.hour is not None else 21),
        )
    except ScriptDB.DoesNotExist:
        return 1, 21


def _deadline_after(day, hour, hours=4):
    absolute = (int(day) - 1) * 24 + int(hour) + int(hours)
    return absolute // 24 + 1, absolute % 24


def _case():
    ensure_situations()
    return get_situation(TAVERN_COLD_CARE_ID)


def _save(case):
    registry = get_situation_registry()
    situations = copy.deepcopy(dict(registry.db.situations or {}))
    situations[TAVERN_COLD_CARE_ID] = copy.deepcopy(case)
    registry.db.situations = situations
    return copy.deepcopy(case)


def _patient():
    matches = list(search.search_tag(PATIENT_ID, category="resident_id"))
    return matches[0] if len(matches) == 1 else None


def _resource(room=None):
    candidates = search.search_object(RESOURCE_KEY)
    if room is not None:
        candidates = [obj for obj in candidates if obj.location is room]
    exact = [obj for obj in candidates if obj.key == RESOURCE_KEY]
    return exact[0] if len(exact) == 1 else None


def _body(patient):
    state = resident_state(patient) or {}
    return dict(((state.get("life") or {}).get("body") or {}))


def _same_tavern(mask, patient):
    room = getattr(mask, "location", None)
    return bool(
        room
        and room is getattr(patient, "location", None)
        and room.key == "The Blood of the Vine"
    )


def ensure_tavern_cold_care():
    """Surface the case once without resetting later mutable Resident Life."""
    case = _case()
    mutations = copy.deepcopy(dict(case.get("objective_mutations") or {}))
    existing = dict(mutations.get("patient_initialized") or {})
    if existing:
        return {"case": case, "created": False, "initialization": existing}

    patient = _patient()
    if patient is None:
        return {"case": case, "created": False, "error": "patient unavailable"}

    body = _body(patient)
    targets = {
        "cold": 58.0,
        "wet": 48.0,
        "discomfort": 35.0,
    }
    for condition, target in targets.items():
        current = float(body.get(condition) or 0.0)
        if current < target:
            apply_resident_condition(
                patient,
                condition,
                target - current,
                cause="a long wet evening in the woods",
            )

    day, hour = _clock()
    due_day, due_hour = _deadline_after(day, hour, 4)
    add_resident_commitment(
        patient,
        COMMITMENT_KEY,
        "I need to get warm and eat something before I head home.",
        logical_location="tavern",
        due_day=due_day,
        due_hour=due_hour,
        priority=0.8,
    )
    record_resident_perception(
        patient,
        "physical_condition",
        "I'm soaked through and I cannot stop shivering.",
        confidence=1.0,
        salience=0.9,
    )

    from world.events import publish_world_event

    event = publish_world_event(
        "civic.cold_hunter_surfaced",
        payload={
            "harbinger": False,
            "chronicle_eligible": False,
            "resident_ids": [PATIENT_ID],
            "situation_id": TAVERN_COLD_CARE_ID,
            "cause": "cold wet return from evening hunt",
        },
    )
    initialization = {
        "resident_id": PATIENT_ID,
        "resident_name": PATIENT_KEY,
        "event_id": event["id"],
        "baseline": {
            key: float(_body(patient).get(key) or 0.0)
            for key in targets
        },
        "day": int(day),
        "hour": int(hour),
    }
    mutations["patient_initialized"] = initialization
    case["objective_mutations"] = mutations
    case["state"] = "surfaced"
    case["surfaced_day"] = int(day)
    case["surfaced_hour"] = int(hour)
    case["deadline_day"] = int(due_day)
    case["deadline_hour"] = int(due_hour)
    case["surface_count"] = max(1, int(case.get("surface_count") or 0))
    event_ids = list(case.get("event_ids") or [])
    event_ids.append(event["id"])
    case["event_ids"] = event_ids
    return {
        "case": _save(case),
        "created": True,
        "initialization": copy.deepcopy(initialization),
    }


def care_status():
    ensure_tavern_cold_care()
    return reconcile_tavern_cold_care()


def _target_is_patient(target):
    return getattr(getattr(target, "db", None), "resident_id", None) == PATIENT_ID


def submit_healer_care_assessment(mask, target):
    """Record the professional assessment but do not spend tavern resources."""
    ensure_tavern_cold_care()
    case = reconcile_tavern_cold_care()
    if case.get("state") == "aftermath":
        return None, "This cold-exposure case is already closed."
    if active_calling(mask) != "healer":
        return None, "Assessing this care case requires an active Healer calling."
    if not _target_is_patient(target):
        return None, "This care case concerns Silas Crowe."
    if not _same_tavern(mask, target):
        return None, "Silas and the Healer must both be present in the Blood of the Vine."

    mutations = copy.deepcopy(dict(case.get("objective_mutations") or {}))
    existing = dict(mutations.get("healer_assessment") or {})
    if existing:
        return {"case": case, "assessment": existing, "created": False}, None

    body = _body(target)
    if float(body.get("cold") or 0.0) < 35.0:
        return None, "Silas is no longer cold enough to require this assessment."

    from world.events import publish_world_event

    event = publish_world_event(
        "professional.healer_cold_assessment",
        actor=mask,
        payload={
            "harbinger": False,
            "chronicle_eligible": False,
            "resident_ids": [PATIENT_ID],
            "situation_id": TAVERN_COLD_CARE_ID,
            "professional_calling": "healer",
            "finding": "cold exposure",
        },
    )
    day, hour = _clock()
    assessment = {
        "calling": "healer",
        "mask_id": getattr(mask, "id", None),
        "mask": getattr(mask, "key", None),
        "resident_id": PATIENT_ID,
        "event_id": event["id"],
        "day": int(day),
        "hour": int(hour),
        "recommendation": "warm meal, dry warmth, and rest",
    }
    mutations["healer_assessment"] = assessment
    case["objective_mutations"] = mutations
    case["state"] = "investigating"
    event_ids = list(case.get("event_ids") or [])
    event_ids.append(event["id"])
    case["event_ids"] = event_ids
    saved = _save(case)

    record_participation(mask, "resident_assessments", calling="healer")
    record_resident_perception(
        target,
        "professional_advice",
        f"{mask.key} says I need warm food, dry warmth, and rest.",
        source_id=str(getattr(mask, "id", "")),
        target_id=PATIENT_ID,
        confidence=0.95,
        salience=0.8,
    )
    record_player_interaction(target, mask, kind="talk", depth=0.5)
    return {"case": saved, "assessment": assessment, "created": True}, None


def provide_innkeep_care(mask, target):
    """Spend one finite stew serving after the Healer establishes the need."""
    ensure_tavern_cold_care()
    case = reconcile_tavern_cold_care()
    if case.get("state") == "aftermath":
        mutations = dict(case.get("objective_mutations") or {})
        existing = dict(mutations.get("innkeep_care") or {})
        if existing:
            return {"case": case, "care": existing, "created": False}, None
        return None, "This cold-exposure case closed before tavern care was provided."
    if active_calling(mask) != "innkeep":
        return None, "Providing the recovery meal requires an active Innkeep calling."
    if not _target_is_patient(target):
        return None, "This care case concerns Silas Crowe."
    if not _same_tavern(mask, target):
        return None, "Silas and the Innkeep must both be present in the Blood of the Vine."

    mutations = copy.deepcopy(dict(case.get("objective_mutations") or {}))
    assessment = dict(mutations.get("healer_assessment") or {})
    if not assessment:
        return None, "An Innkeep cannot close this care case until a Healer has assessed Silas."

    existing = dict(mutations.get("innkeep_care") or {})
    if existing:
        return {"case": case, "care": existing, "created": False}, None

    stew = _resource(mask.location)
    if stew is None:
        return None, "There is no bowl of stew available in the tavern."
    capacity = mechanical_value(stew, "uses", None)
    if stew.db.servings is None and capacity is not None:
        stew.db.servings = int(capacity)
    before = int(stew.db.servings or 0)
    if before <= 0:
        return None, "The tavern has no stew servings left to spend on the care case."
    stew.db.servings = before - 1

    body = _body(target)
    targets = {"cold": 12.0, "wet": 8.0, "discomfort": 8.0}
    for condition, target_value in targets.items():
        current = float(body.get(condition) or 0.0)
        if current > target_value:
            apply_resident_condition(
                target,
                condition,
                target_value - current,
                cause="warm food and a place by the hearth",
            )
            body = _body(target)

    resolve_resident_commitment(target, COMMITMENT_KEY, "fulfilled")
    record_resident_perception(
        target,
        "care",
        "The hot stew and a place by the hearth finally stop my shivering.",
        source_id=str(getattr(mask, "id", "")),
        target_id=PATIENT_ID,
        confidence=1.0,
        salience=0.9,
    )
    record_player_interaction(target, mask, kind="help", depth=1.0)

    from world.events import publish_world_event

    event = publish_world_event(
        "professional.innkeep_recovery_care",
        actor=mask,
        payload={
            "harbinger": False,
            "chronicle_eligible": False,
            "resident_ids": [PATIENT_ID],
            "situation_id": TAVERN_COLD_CARE_ID,
            "professional_calling": "innkeep",
            "source_healer_event_id": assessment.get("event_id"),
            "resource_object_id": stew.id,
            "resource_object_key": stew.key,
            "servings_before": before,
            "servings_after": int(stew.db.servings or 0),
        },
    )
    day, hour = _clock()
    care = {
        "calling": "innkeep",
        "mask_id": getattr(mask, "id", None),
        "mask": getattr(mask, "key", None),
        "resident_id": PATIENT_ID,
        "event_id": event["id"],
        "resource_object_id": stew.id,
        "resource_object_key": stew.key,
        "servings_before": before,
        "servings_after": int(stew.db.servings or 0),
        "source_healer_event_id": assessment.get("event_id"),
        "day": int(day),
        "hour": int(hour),
    }
    mutations["innkeep_care"] = care
    case["objective_mutations"] = mutations
    case["state"] = "aftermath"
    case["branch"] = "cared_for"
    case["resolved_day"] = int(day)
    case["resolved_hour"] = int(hour)
    case["aftermath"] = (
        "A Healer established the need, and an Innkeep spent a real tavern meal "
        "to help Silas warm up before going home."
    )
    event_ids = list(case.get("event_ids") or [])
    event_ids.append(event["id"])
    case["event_ids"] = event_ids
    saved = _save(case)

    record_participation(mask, "recovery_hospitality", calling="innkeep")
    return {"case": saved, "care": care, "created": True}, None


def reconcile_tavern_cold_care():
    """Let the resident recover naturally when the four-hour window expires."""
    case = _case()
    if case.get("state") == "aftermath":
        return case
    due_day = case.get("deadline_day")
    due_hour = case.get("deadline_hour")
    if due_day is None or due_hour is None:
        return case
    day, hour = _clock()
    if (int(day), int(hour)) < (int(due_day), int(due_hour)):
        return case

    patient = _patient()
    if patient is None:
        return case
    body = _body(patient)
    for condition in ("cold", "wet", "discomfort"):
        current = float(body.get(condition) or 0.0)
        if current > 0:
            apply_resident_condition(
                patient,
                condition,
                -current,
                cause="time by the tavern fire",
            )
            body = _body(patient)
    resolve_resident_commitment(patient, COMMITMENT_KEY, "fulfilled")

    from world.events import publish_world_event

    event = publish_world_event(
        "civic.cold_hunter_self_recovered",
        payload={
            "harbinger": False,
            "chronicle_eligible": False,
            "resident_ids": [PATIENT_ID],
            "situation_id": TAVERN_COLD_CARE_ID,
        },
    )
    case["state"] = "aftermath"
    case["branch"] = "self_recovered"
    case["resolved_day"] = int(day)
    case["resolved_hour"] = int(hour)
    case["aftermath"] = (
        "Silas warmed up on his own before coordinated professional care was completed."
    )
    event_ids = list(case.get("event_ids") or [])
    event_ids.append(event["id"])
    case["event_ids"] = event_ids
    return _save(case)
