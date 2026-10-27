"""GDD-EDGE-03: validate a Healer's actual completed care assessment.

The situation row is a pointer, not proof. The canonical event ledger must
independently confirm the professional, account, mask, patient, time and case.
This module deliberately has no Evennia imports so forged-record cases can
be exercised without a running server.
"""


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
    if not isinstance(assessment, dict) or not isinstance(event, dict):
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
    if not isinstance(actor, dict) or not isinstance(payload, dict):
        return None, error
    if (event.get("status") != "complete"
            or event.get("kind") != "professional.healer_cold_assessment"
            or _positive_id(event.get("id")) != source_id
            or _positive_id(actor.get("account_id")) != healer_account
            or _positive_id(actor.get("mask_id")) != healer_mask
            or actor.get("mask") != assessment.get("mask")
            or assessment.get("calling") != "healer"
            or assessment.get("resident_id") != resident_id
            or payload.get("professional_calling") != "healer"
            or payload.get("situation_id") != situation_id
            or payload.get("resident_ids") != [resident_id]
            or payload.get("finding") != "cold exposure"
            or _clock_part(payload.get("day"), 1, 1000000) != day
            or _clock_part(payload.get("hour"), 0, 23) != hour):
        return None, error
    return {
        "event_id": source_id,
        "account_id": healer_account,
        "mask_id": healer_mask,
        "day": day,
        "hour": hour,
    }, None
