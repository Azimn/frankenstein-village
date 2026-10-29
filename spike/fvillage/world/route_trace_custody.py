"""Pure signed Hound/Detective trace-custody rules for the original red cord.

A Hound's caution marker is an observed physical alteration, not a solved
crime. A Detective may preserve a qualified record once, even when arriving
on a later village day. No tracks, perpetrator or hazard truth is invented.
"""
from __future__ import annotations

from collections.abc import Mapping


def _positive(value):
    if isinstance(value, bool):
        return None
    try:
        number = int(value)
    except (TypeError, ValueError, OverflowError):
        return None
    return number if number > 0 else None


def _hour(value):
    if isinstance(value, bool):
        return None
    try:
        number = int(value)
    except (TypeError, ValueError, OverflowError):
        return None
    return number if 0 <= number <= 23 else None


def normalize(raw):
    """Return only a complete, internally consistent custody record."""
    if not isinstance(raw, Mapping):
        return None
    keys = (
        "day", "source_day", "source_event_id", "hound_account_id",
        "hound_mask_id", "detective_account_id", "detective_mask_id",
        "cord_id", "event_id",
    )
    values = {key: _positive(raw.get(key)) for key in keys}
    hour, source_hour = _hour(raw.get("hour")), _hour(raw.get("source_hour"))
    if (any(value is None for value in values.values())
            or hour is None or source_hour is None
            or values["source_day"] > values["day"]
            or (values["source_day"] == values["day"] and source_hour > hour)
            or values["hound_account_id"] == values["detective_account_id"]
            or values["hound_mask_id"] == values["detective_mask_id"]
            or values["source_event_id"] == values["event_id"]
            or raw.get("observed_condition") != "tied_caution"):
        return None
    return {
        **values,
        "hour": hour,
        "source_hour": source_hour,
        "detective_mask": str(raw.get("detective_mask") or "")[:70],
        "observed_condition": "tied_caution",
        "late_arrival": values["source_day"] < values["day"],
    }


def preserve(raw, *, day, hour, source_day, source_hour, source_event_id,
             hound_account_id, hound_mask_id, detective_account_id,
             detective_mask_id, detective_mask, cord_id, event_id,
             observed_condition):
    existing = normalize(raw)
    if raw is not None:
        if existing is None:
            return None, False, "The existing custody record is malformed; do not overwrite it."
        return existing, False, "This physical cord already has a signed Detective custody record."
    proposal = normalize({
        "day": day, "hour": hour, "source_day": source_day,
        "source_hour": source_hour, "source_event_id": source_event_id,
        "hound_account_id": hound_account_id,
        "hound_mask_id": hound_mask_id,
        "detective_account_id": detective_account_id,
        "detective_mask_id": detective_mask_id,
        "detective_mask": detective_mask,
        "cord_id": cord_id, "event_id": event_id,
        "observed_condition": observed_condition,
    })
    if proposal is None:
        return None, False, "A valid earlier Hound source, distinct Detective, physical cord and village time are required."
    return proposal, True, None


def public_lines(raw):
    record = normalize(raw)
    if record is None:
        return "No independent Detective custody record has been signed for the treeline cord."
    timing = (
        "This was a late-arrival examination; the original scene was already altered."
        if record["late_arrival"]
        else "The cord was examined on the Hound's recorded village day."
    )
    return (
        f"{record['detective_mask']} preserved a qualified physical trace record "
        f"(Detective event {record['event_id']}, Hound source "
        f"{record['source_event_id']}, day {record['day']}). "
        "The tied warning is real, but neither tracks nor a culprit were established; "
        "it is not proof of who damaged the cord. "
        + timing
    )
