"""Cross-calling public-health warning for the well mushrooms.

This is deliberately one authored vertical slice, not a generic job board.
It reuses the existing SituationRegistry for persistent shared state, the
calling system for professional authority, the hidden object mechanic for
world truth, and the event/publication pipeline for the final public record.
"""

from __future__ import annotations

import copy

from evennia.scripts.models import ScriptDB

from world.callings import (
    active_calling,
    assess_hidden_object,
    record_participation,
)
from world.object_properties import (
    is_hidden_mechanical_property,
    mechanical_value,
)
from world.situations import (
    WELL_MUSHROOM_WARNING_ID,
    ensure_situations,
    get_situation,
    get_situation_registry,
)


TARGET_OBJECT_KEY = "a cluster of mushrooms"
TARGET_PROPERTY = "toxin"


def _clock():
    try:
        clock = ScriptDB.objects.get(db_key="village_time")
        return (
            int(clock.db.day or 1),
            int(clock.db.hour if clock.db.hour is not None else 21),
        )
    except ScriptDB.DoesNotExist:
        return 1, 21


def _case():
    ensure_situations()
    return get_situation(WELL_MUSHROOM_WARNING_ID)


def _save(case):
    registry = get_situation_registry()
    situations = copy.deepcopy(dict(registry.db.situations or {}))
    situations[WELL_MUSHROOM_WARNING_ID] = copy.deepcopy(case)
    registry.db.situations = situations
    return copy.deepcopy(case)


def warning_status():
    """Return the current persistent interdependence case."""
    return _case()


def _is_target(obj):
    return (
        getattr(obj, "key", None) == TARGET_OBJECT_KEY
        and is_hidden_mechanical_property(obj, TARGET_PROPERTY)
    )


def submit_healer_finding(mask, obj):
    """File the Healer half of the warning without making it public yet."""
    if not _is_target(obj):
        return (
            None,
            "This public-health case concerns the pale mushrooms beside the "
            "village well, not that object.",
        )

    assessment, error = assess_hidden_object(mask, obj)
    if error:
        return None, error

    toxin = next(
        (
            item
            for item in assessment.get("discoveries") or []
            if item.get("property") == TARGET_PROPERTY
        ),
        None,
    )
    if not toxin:
        return (
            None,
            "The Healer assessment did not establish a supported hidden toxin "
            "for this public-health case.",
        )

    case = _case()
    mutations = copy.deepcopy(dict(case.get("objective_mutations") or {}))
    existing = dict(mutations.get("healer_finding") or {})
    if existing:
        return {
            "case": case,
            "finding": existing,
            "created": False,
        }, None

    from world.events import publish_world_event

    day, hour = _clock()
    event = publish_world_event(
        "professional.healer_finding_submitted",
        actor=mask,
        payload={
            "publicity": "private",
            "harbinger": False,
            "chronicle_eligible": False,
            "situation_id": WELL_MUSHROOM_WARNING_ID,
            "source_object_id": getattr(obj, "id", None),
            "source_object_key": getattr(obj, "key", None),
            "mechanical_property": TARGET_PROPERTY,
            "mechanical_value": mechanical_value(obj, TARGET_PROPERTY),
            "professional_calling": "healer",
        },
    )

    finding = {
        "calling": "healer",
        "mask_id": getattr(mask, "id", None),
        "mask": getattr(mask, "key", None),
        "object_id": getattr(obj, "id", None),
        "object_key": getattr(obj, "key", None),
        "property": TARGET_PROPERTY,
        "value": toxin.get("value"),
        "assessment_source": toxin.get("source"),
        "event_id": event["id"],
        "day": int(day),
        "hour": int(hour),
    }
    mutations["healer_finding"] = finding
    case["objective_mutations"] = mutations
    case["state"] = "investigating"
    case["surfaced_day"] = case.get("surfaced_day") or int(day)
    case["surfaced_hour"] = (
        case.get("surfaced_hour")
        if case.get("surfaced_hour") is not None
        else int(hour)
    )
    case["surface_count"] = max(1, int(case.get("surface_count") or 0))
    event_ids = list(case.get("event_ids") or [])
    event_ids.append(event["id"])
    case["event_ids"] = event_ids
    saved = _save(case)

    record_participation(
        mask,
        "public_health_findings",
        calling="healer",
    )
    return {
        "case": saved,
        "finding": copy.deepcopy(finding),
        "created": True,
    }, None


def publish_public_warning(mask):
    """Complete the Chronicler half and project one canonical warning event."""
    if active_calling(mask) != "chronicler":
        return (
            None,
            "Publishing the institutional warning requires an active Chronicler "
            "calling.",
        )

    case = _case()
    mutations = copy.deepcopy(dict(case.get("objective_mutations") or {}))
    finding = dict(mutations.get("healer_finding") or {})
    if not finding:
        return (
            None,
            "The Chronicle cannot publish this health warning until a Healer "
            "has filed a professional assessment.",
        )

    existing = dict(mutations.get("chronicler_record") or {})
    if existing and case.get("state") == "aftermath":
        return {
            "case": case,
            "record": existing,
            "created": False,
        }, None

    from world.events import publish_world_event

    healer_name = finding.get("mask") or "a village Healer"
    summary = (
        f"After a professional assessment by {healer_name}, the Chronicle "
        "records that the pale mushrooms beside the village well can be toxic. "
        "The warning concerns this identified growth; it does not certify other "
        "mushrooms as safe."
    )
    event = publish_world_event(
        "professional.public_health_warning",
        actor=mask,
        payload={
            "harbinger": True,
            "chronicle_eligible": True,
            "headline": "Health Warning Issued for Well Mushrooms",
            "public_summary": summary,
            "chronicle_summary": summary,
            "situation_id": WELL_MUSHROOM_WARNING_ID,
            "source_healer_mask_id": finding.get("mask_id"),
            "source_healer_mask": finding.get("mask"),
            "source_healer_event_id": finding.get("event_id"),
            "source_object_id": finding.get("object_id"),
            "source_object_key": finding.get("object_key"),
            "mechanical_property": TARGET_PROPERTY,
            "professional_calling": "chronicler",
        },
    )
    refs = dict(event.get("publications") or {})
    if not refs.get("chronicle_entry_id") or not refs.get("harbinger_story_id"):
        return (
            None,
            "The warning event was recorded but did not project into both "
            "required public-record systems.",
        )

    day, hour = _clock()
    record = {
        "calling": "chronicler",
        "mask_id": getattr(mask, "id", None),
        "mask": getattr(mask, "key", None),
        "event_id": event["id"],
        "chronicle_entry_id": refs["chronicle_entry_id"],
        "harbinger_story_id": refs["harbinger_story_id"],
        "day": int(day),
        "hour": int(hour),
    }
    mutations["chronicler_record"] = record
    case["objective_mutations"] = mutations
    case["state"] = "aftermath"
    case["branch"] = "public_warning"
    case["resolved_day"] = int(day)
    case["resolved_hour"] = int(hour)
    case["aftermath"] = (
        "A Healer established the risk and a Chronicler made the warning part "
        "of the public record. The mushroom mechanic itself is unchanged."
    )
    event_ids = list(case.get("event_ids") or [])
    event_ids.append(event["id"])
    case["event_ids"] = event_ids
    publications = list(case.get("publications") or [])
    publications.append(
        {
            "event_id": event["id"],
            "chronicle_entry_id": refs["chronicle_entry_id"],
            "harbinger_story_id": refs["harbinger_story_id"],
        }
    )
    case["publications"] = publications
    saved = _save(case)

    record_participation(
        mask,
        "public_health_records",
        calling="chronicler",
    )
    return {
        "case": saved,
        "record": copy.deepcopy(record),
        "created": True,
    }, None
