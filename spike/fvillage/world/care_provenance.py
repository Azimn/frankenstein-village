"""GDD-EDGE-03: validate a Healer's actual completed care assessment.

The situation row is a pointer, not proof. The canonical event ledger must
independently confirm the professional, account, mask, patient, time and case.
This module deliberately has no Evennia imports so forged-record cases can
be exercised without a running server.
"""

from collections.abc import Mapping, Sequence


def _positive_id(value):
    if isinstance(value, bool):
        return None
    try:
        number = int(value)
    except (TypeError, ValueError, OverflowError):
        return None
    return number if number > 0 and str(value) == str(number) else None


def _clock_part(value, lower, upper):
    number = _positive_id(value) if lower > 0 else None
    if lower == 0:
        if isinstance(value, bool):
            return None
        try:
            number = int(value)
        except (TypeError, ValueError, OverflowError):
            return None
        if str(value) != str(number):
            return None
    return number if number is not None and lower <= number <= upper else None


def validate_healer_source(assessment, event, *, innkeep_account_id,
                           case_event_ids, situation_id, resident_id):
    """Return (verified source, error); never infer an event from a row."""
    error = "The Healer assessment has no valid signed source; no meal was spent."
    if not isinstance(assessment, Mapping) or not isinstance(event, Mapping):
        return None, error
    source_id = _positive_id(assessment.get("event_id"))
    healer_account = _positive_id(assessment.get("account_id"))
    healer_mask = _positive_id(assessment.get("mask_id"))
    innkeep_account = _positive_id(innkeep_account_id)
    day = _clock_part(assessment.get("day"), 1, 1000000)
    hour = _clock_part(assessment.get("hour"), 0, 23)
    if not all((source_id, healer_account, healer_mask, innkeep_account, day is not None,
                hour is not None)):
        return None, error
    if healer_account == innkeep_account:
        return None, "Healer and Innkeep contributions require different player accounts."
    try:
        known_ids = {_positive_id(value) for value in case_event_ids}
    except (TypeError, ValueError):
        return None, error
    if source_id not in known_ids:
        return None, error
    actor = event.get("actor")
    payload = event.get("payload")
    if not isinstance(actor, Mapping) or not isinstance(payload, Mapping):
        return None, error
    # Signed resident IDs must be an actual ordered patient collection.
    # Do not iterate scalar, string or mapping values from malformed persisted
    # events. The validation runs before the Innkeep spends finite stew.
    resident_ids = payload.get("resident_ids")
    if not isinstance(resident_ids, Sequence) or isinstance(
        resident_ids, (str, bytes, bytearray)
    ):
        return None, error + " Source mismatch: event patient."
    checks = (
        ("event completion", event.get("status") == "complete"),
        ("event kind", event.get("kind") == "professional.healer_cold_assessment"),
        ("source event ID", _positive_id(event.get("id")) == source_id),
        ("source account", _positive_id(actor.get("account_id")) == healer_account),
        ("source mask ID", _positive_id(actor.get("mask_id")) == healer_mask),
        ("source mask name", actor.get("mask") == assessment.get("mask")),
        ("assessment role", assessment.get("calling") == "healer"),
        ("assessment patient", assessment.get("resident_id") == resident_id),
        ("event role", payload.get("professional_calling") == "healer"),
        ("event case", payload.get("situation_id") == situation_id),
        ("event patient", list(resident_ids) == [resident_id]),
        ("event finding", payload.get("finding") == "cold exposure"),
        ("event day", _clock_part(payload.get("day"), 1, 1000000) == day),
        ("event hour", _clock_part(payload.get("hour"), 0, 23) == hour),
    )
    for label, valid in checks:
        if not valid:
            return None, error + " Source mismatch: " + label + "."
    return {
        "event_id": source_id,
        "account_id": healer_account,
        "mask_id": healer_mask,
        "day": day,
        "hour": hour,
    }, None
