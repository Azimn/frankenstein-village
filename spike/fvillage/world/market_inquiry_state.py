"""Pure, durable Merchant/Detective inquiry rules for a real held market scale.

An inquiry is evidence of a signed investigation, not a finding of fraud.
The ordinary Merchant, Smith and Chronicler market workflow stays available.
"""
from __future__ import annotations

import copy
from collections.abc import Mapping

MAX_CASES = 24


def _whole_number(value):
    """Reject lossy numeric coercion of signed IDs and village hours."""
    if isinstance(value, bool):
        return None
    if isinstance(value, int):
        return value
    if isinstance(value, str):
        text = value.strip()
        if text and text.isascii() and text.isdecimal():
            try:
                return int(text, 10)
            except ValueError:
                return None
    return None


def _id(value):
    number = _whole_number(value)
    return number if number is not None and number > 0 else None


def _hour(value):
    number = _whole_number(value)
    return number if number is not None and 0 <= number <= 23 else None


def normalize(raw):
    try:
        candidates = list(raw or [])
    except (TypeError, ValueError):
        return []
    rows, sources = [], set()
    fields = (
        "day", "source_event_id", "source_account_id", "source_mask_id",
        "detective_account_id", "detective_mask_id", "scale_id", "case_event_id",
    )
    for item in candidates[-MAX_CASES * 2:]:
        if not hasattr(item, "get"):
            continue
        values = {key: _id(item.get(key)) for key in fields}
        hour, source_hour = _hour(item.get("hour")), _hour(item.get("source_hour"))
        if (any(value is None for value in values.values())
                or hour is None or source_hour is None or source_hour > hour
                or values["source_account_id"] == values["detective_account_id"]
                or values["source_event_id"] in sources):
            continue
        sources.add(values["source_event_id"])
        row = {
            **values, "hour": hour, "source_hour": source_hour,
            "detective_mask": str(item.get("detective_mask") or "")[:70],
            "rebuttal_event_id": None, "rebuttal_hour": None,
        }
        rebuttal = _id(item.get("rebuttal_event_id"))
        rebuttal_hour = _hour(item.get("rebuttal_hour"))
        if rebuttal and rebuttal_hour is not None and rebuttal_hour >= hour:
            row["rebuttal_event_id"] = rebuttal
            row["rebuttal_hour"] = rebuttal_hour
        rows.append(row)
    return copy.deepcopy(rows[-MAX_CASES:])


def open_case(raw, *, day, hour, source_day, source_hour, source_event_id,
              source_account_id, source_mask_id, detective_account_id,
              detective_mask_id, detective_mask, scale_id, case_event_id):
    rows = normalize(raw)
    values = [
        _id(v) for v in (
            day, source_day, source_event_id, source_account_id, source_mask_id,
            detective_account_id, detective_mask_id, scale_id, case_event_id,
        )
    ]
    h, sh = _hour(hour), _hour(source_hour)
    if any(v is None for v in values) or h is None or sh is None:
        return rows, False, "Signed identities, object, event and village time are required."
    (day, source_day, source_event_id, source_account_id, source_mask_id,
     detective_account_id, detective_mask_id, scale_id, case_event_id) = values
    if day != source_day or h < sh:
        return rows, False, "The held market decision must precede today's inquiry."
    if source_account_id == detective_account_id:
        return rows, False, "An independent account must investigate the Merchant's decision."
    if any((r["day"], r["hour"]) > (day, h) for r in rows):
        return rows, False, "A later inquiry is already recorded; the clock cannot be rewound."
    if any(r["source_event_id"] == source_event_id for r in rows):
        return rows, False, "That Merchant decision has already been investigated."
    rows.append({
        "day": day, "hour": h, "source_hour": sh,
        "source_event_id": source_event_id,
        "source_account_id": source_account_id,
        "source_mask_id": source_mask_id,
        "detective_account_id": detective_account_id,
        "detective_mask_id": detective_mask_id,
        "detective_mask": str(detective_mask or "")[:70],
        "scale_id": scale_id, "case_event_id": case_event_id,
        "rebuttal_event_id": None, "rebuttal_hour": None,
    })
    return rows[-MAX_CASES:], True, None


def rebut_case(raw, *, day, hour, source_event_id, merchant_account_id,
               merchant_mask_id, event_id):
    rows = normalize(raw)
    vals = [_id(v) for v in (
        day, source_event_id, merchant_account_id, merchant_mask_id, event_id
    )]
    h = _hour(hour)
    if any(v is None for v in vals) or h is None:
        return rows, False, "A signed Merchant response and village time are required."
    day, source_event_id, merchant_account_id, merchant_mask_id, event_id = vals
    found = next((r for r in rows if r["source_event_id"] == source_event_id), None)
    if found is None:
        return rows, False, "No independent Detective inquiry exists for this decision."
    if (found["day"] != day or h < found["hour"]
            or any((r["day"], r["hour"]) > (day, h) for r in rows)):
        return rows, False, "This response is outside the signed inquiry's village time."
    if (found["source_account_id"] != merchant_account_id
            or found["source_mask_id"] != merchant_mask_id):
        return rows, False, "Only the original Merchant may rebut this inquiry."
    if found["rebuttal_event_id"] is not None:
        return rows, False, "The Merchant's rebuttal is already recorded."
    found["rebuttal_event_id"] = event_id
    found["rebuttal_hour"] = h
    return rows, True, None


def _signed_event(event_lookup, event_id, kind, actor_account, actor_mask,
                  action, calling, day, hour, source_id=None, scale_id=None,
                  room_id=None, actor_name=None):
    """Require a completed canonical event matching its persisted identity."""
    try:
        event = event_lookup(event_id)
    except (LookupError, TypeError, ValueError, AttributeError):
        return None
    if not isinstance(event, Mapping):
        return None
    actor, payload, effect = (
        event.get("actor"), event.get("payload"), event.get("consequence")
    )
    if not all(isinstance(part, Mapping) for part in (actor, payload, effect)):
        return None
    if (type(event.get("id")) is not int or event.get("id") != event_id
            or event.get("kind") != kind or event.get("status") != "complete"
            or actor.get("account_id") != actor_account
            or actor.get("mask_id") != actor_mask
            or payload.get("action") != action
            or payload.get("professional_calling") != calling
            or payload.get("day") != day or payload.get("hour") != hour):
        return None
    if actor_name is not None and actor.get("mask") != actor_name:
        return None
    if source_id is not None and payload.get("source_event_id") != source_id:
        return None
    if scale_id is not None and payload.get("scale_id") != scale_id:
        return None
    if room_id is not None and payload.get("market_room_id") != room_id:
        return None
    return effect


def verified_case(row, *, event_lookup, room_id):
    """Read historic ledger events, never trust an unsigned saved case row."""
    if _id(room_id) is None or not callable(event_lookup):
        return False
    source = _signed_event(
        event_lookup, row["source_event_id"], "village.market_hold",
        row["source_account_id"], row["source_mask_id"], "hold", "merchant",
        row["day"], row["source_hour"],
    )
    if (source is None
            or source.get("action") != "hold"
            or source.get("review_event_id") != row["source_event_id"]
            or source.get("market_distribution_held") is not True):
        return False
    # The source is a historic market hold, not necessarily today's hold.
    try:
        held = event_lookup(row["source_event_id"])
    except (LookupError, TypeError, ValueError, AttributeError):
        return False
    if held["payload"].get("location") != "Market Lane":
        return False
    opened = _signed_event(
        event_lookup, row["case_event_id"], "village.market_inquiry_opened",
        row["detective_account_id"], row["detective_mask_id"],
        "investigate", "detective", row["day"], row["hour"],
        source_id=row["source_event_id"], scale_id=row["scale_id"],
        room_id=room_id, actor_name=row["detective_mask"],
    )
    if (opened is None
            or opened.get("source_event_id") != row["source_event_id"]
            or opened.get("scale_id") != row["scale_id"]
            or opened.get("market_room_id") != room_id
            or opened.get("case_event_id") != row["case_event_id"]
            or opened.get("rebuttal_event_id") is not None):
        return False
    if row["rebuttal_event_id"] is None:
        return True
    rebutted = _signed_event(
        event_lookup, row["rebuttal_event_id"], "village.market_inquiry_rebutted",
        row["source_account_id"], row["source_mask_id"],
        "rebut", "merchant", row["day"], row["rebuttal_hour"],
        source_id=row["source_event_id"], scale_id=row["scale_id"],
        room_id=room_id,
    )
    return bool(
        rebutted is not None
        and rebutted.get("source_event_id") == row["source_event_id"]
        and rebutted.get("scale_id") == row["scale_id"]
        and rebutted.get("market_room_id") == room_id
        and rebutted.get("case_event_id") == row["case_event_id"]
        and rebutted.get("rebuttal_event_id") == row["rebuttal_event_id"]
    )


def public_lines(raw, *, event_lookup=None, room_id=None):
    rows = normalize(raw)
    if not rows:
        return "No independent Detective market inquiry has been filed."
    latest = rows[-1]
    if not verified_case(latest, event_lookup=event_lookup, room_id=room_id):
        return "The market inquiry record is not verified against signed village events."
    reply = (
        f"Merchant decision event {latest['source_event_id']} was independently "
        f"examined by {latest['detective_mask']} (Detective event "
        f"{latest['case_event_id']}, village day {latest['day']}). "
        "This records an observed scale discrepancy, not a finding of fraud."
    )
    if latest["rebuttal_event_id"] is not None:
        reply += (
            f" The original Merchant filed rebuttal event "
            f"{latest['rebuttal_event_id']}; the claim remains contested."
        )
    return reply
