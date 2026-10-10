"""Bounded, physically grounded resident responses to a stoked hearth.

No Evennia imports, no claimed emotions, no social bond inferred from fuel.
The same observation must not replay at each tick, and a resident cannot
witness warmth from somewhere else or outside the actual burning interval.
The single-hour linger is optional and yields to needs and authored routines.
"""

from __future__ import annotations

from world.resident_life import (
    apply_body_delta,
    enabled,
    record_perception,
)

HEARTH_TARGET_ID = "tavern_hearth"
COLD_RELIEF = 12.0
LINGER_COLD = 55.0


def observe(life, *, present, warm, source_event_id, day, hour):
    """Once per burn, note personally experienced heat; reduce measured cold.

    Returns a fresh observation or None. Mutates life only on a valid first
    physical exposure to a *currently active* specific tending event.
    """
    if not enabled(life) or not present or not warm or not source_event_id:
        return None
    marker = int(source_event_id)
    if marker <= 0 or int(life.get("last_witnessed_hearth_event_id") or 0) >= marker:
        return None
    record = record_perception(
        life,
        kind="environment",
        summary="I felt the stronger fire at the Blood of the Vine ease the cold.",
        source_id=marker,
        target_id=HEARTH_TARGET_ID,
        confidence=1.0,
        salience=0.55,
        day=day,
        hour=hour,
    )
    if record is None:
        return None
    # This is relief from physical cold, not treatment for illness or an
    # automatic opinion about whoever brought or tended the fuel.
    apply_body_delta(life, cold=-COLD_RELIEF)
    life["last_witnessed_hearth_event_id"] = marker
    return record


def maybe_linger(
    life, definition, current_target, *, physical_location,
    previous_hour_location, active_heat, hour, needs,
):
    """One-hour discretionary postponement when leaving a warm Tavern.

    Only a resident already physically there, scheduled there in the prior
    hour, otherwise on a normal homebound route, and still cold may choose
    to remain for the last hour. Critical needs, unsafe conditions, other
    goal overrides and authored characters win over this preference.
    """
    if not enabled(life) or not active_heat:
        return None
    if physical_location != "The Blood of the Vine":
        return None
    if int(hour) < 1 or previous_hour_location != "tavern":
        return None
    if current_target.get("source") != "schedule":
        return None
    if current_target.get("logical_location") != definition.get("home_id"):
        return None
    cold = float((life.get("body") or {}).get("cold") or 0)
    needs = dict(needs or {})
    if cold < LINGER_COLD:
        return None
    if float(needs.get("fatigue", 0)) >= 80:
        return None
    if float(needs.get("safety", 80)) <= 30:
        return None
    if float((life.get("body") or {}).get("injury") or 0) >= 65:
        return None
    if float((life.get("body") or {}).get("illness") or 0) >= 65:
        return None
    return {
        **current_target,
        "logical_location": "tavern",
        "source": "hearth_preference",
        "reason": "I chose one more hour beside the stronger fire before going home.",
        "activity": "lingers by the hearth before heading home",
    }


def first_person_account(life):
    """Speak from recorded experience, not from omniscient room state."""
    if not enabled(life):
        return None
    record = next(
        (
            r for r in reversed(life.get("perceptions") or [])
            if r.get("target_id") == HEARTH_TARGET_ID
            and r.get("source_id")
        ),
        None,
    )
    if not record:
        return "I haven't been near that fire since anyone built it up."
    return (
        "I was there when the Tavern hearth burned higher. "
        "The heat got into my hands. That much I remember."
    )
