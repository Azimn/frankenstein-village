"""Physical rain exposure for the existing first-person resident life system.

Weather is observed only by residents physically present in the open Village
Square after their normal schedule resolves. One exposure per village hour;
no catch-up ticks, no telepathy, and no additional resident scheduler.
"""

from __future__ import annotations

from world.resident_life import (
    absolute_hour, apply_body_delta, enabled, record_perception,
)

COLD_PER_RAIN_HOUR = 10.0
WET_PER_RAIN_HOUR = 14.0
RAIN_TARGET_ID = "village_square_rain"


def observe(life, *, physical_room, weather, day, hour):
    """Apply one co-located rain exposure, or return None without mutation.

    The cursor is the canonical village hour. Repeated ticks, backwards clock
    adjustments, and overlapping server operations cannot create extra cold.
    Any missing/disabled resident life is a strict no-op.
    """
    if not enabled(life) or physical_room != "Village Square" or weather != "rain":
        return None
    now = absolute_hour(day, hour)
    previous = life.get("last_rain_exposure_absolute_hour")
    if previous is not None and now <= int(previous):
        return None
    record = record_perception(
        life,
        kind="weather",
        summary="I stood in the rain by the village well; the chill soaked into my clothes.",
        source_id="village_weather:rain",
        target_id=RAIN_TARGET_ID,
        confidence=1.0,
        salience=0.35,
        day=day,
        hour=hour,
    )
    if record is None:
        return None
    apply_body_delta(
        life, wet=WET_PER_RAIN_HOUR, cold=COLD_PER_RAIN_HOUR,
    )
    life["last_rain_exposure_absolute_hour"] = now
    return record


def first_person_account(life):
    """Ground a rain response in personal observation, not global weather."""
    if not enabled(life):
        return None
    witnessed = any(
        p.get("target_id") == RAIN_TARGET_ID
        for p in life.get("perceptions") or []
    )
    return (
        "I was caught in the rain by the well. My clothes took the worst of it."
        if witnessed else
        "I haven't been out by the well in the rain."
    )
