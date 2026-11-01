"""EDGE-22: qualified Detective custody of a real Smith market calibration.

Pure, fail-closed validation. The crooked scale owns the durable inquiry,
the market standards board owns calibration, and WorldEventLedger owns proof.
No inference of fraud, culprit, or retroactive mechanical change is permitted.
"""
from __future__ import annotations

import copy
from collections.abc import Mapping

MAX_RECORDS = 28
SOURCE_KIND = "village.market_calibrate"
INQUIRY_KIND = "village.market_forensic_inspection"
FINDING = (
    "The scale was calibrated by a Smith; this observation alone "
    "does not establish who caused the earlier discrepancy."
)


def _id(value):
    return value if type(value) is int and value > 0 else None


def _time(day, hour):
    return (
        type(day) is int and day > 0
        and type(hour) is int and 0 <= hour <= 23
    )


def _record(raw):
    if not isinstance(raw, Mapping):
        return None
    fields = ("event_id", "source_event_id", "account_id", "mask_id",
              "smith_account_id", "scale_id", "market_id", "day")
    if any(_id(raw.get(k)) is None for k in fields):
        return None
    if not _time(raw["day"], raw.get("hour")):
        return None
    if not isinstance(raw.get("mask"), str) or not raw["mask"].strip():
        return None
    if raw["account_id"] == raw["smith_account_id"]:
        return None
    if raw.get("finding") != FINDING:
        return None
    return copy.deepcopy(dict(raw))


def normalize(raw):
    """Read existing durable records without inventing or repairing evidence."""
    if raw is None:
        return []
    if isinstance(raw, (str, bytes, bytearray, Mapping)):
        return []
    try:
        rows = list(raw)
    except (TypeError, ValueError):
        return []
    return [r for row in rows if (r := _record(row)) is not None][-MAX_RECORDS:]


def inspect(raw, *, calibration, source_event, account_id, mask_id,
            mask, day, hour, event_id, scale_id, market_id):
    """Return (new_history, accepted, reason), never mutating an input."""
    if isinstance(raw, (str, bytes, bytearray, Mapping)):
        return [], False, "The scale's stored custody history is malformed."
    try:
        original = list(raw) if raw is not None else []
    except (TypeError, ValueError):
        return [], False, "The scale's stored custody history is malformed."
    history = normalize(original)
    if len(history) != len(original) or len(original) > MAX_RECORDS:
        return history, False, "The scale's stored custody history is malformed."
    if not _time(day, hour):
        return history, False, "A valid village day and hour are required."
    ids = (account_id, mask_id, event_id, scale_id, market_id)
    if any(_id(i) is None for i in ids):
        return history, False, "An authenticated mask, physical scale and signed event are required."
    if not isinstance(mask, str) or not mask.strip():
        return history, False, "A named investigative mask is required."
    if any(row["day"] > day for row in history):
        return history, False, "The village clock cannot be rewound."
    if any(row["day"] == day for row in history):
        return history, False, "Today's scale already has an independent custody inquiry."
    if not isinstance(calibration, Mapping):
        return history, False, "A real Smith calibration must precede the inquiry."
    smith_id = _id(calibration.get("account_id"))
    smith_mask = _id(calibration.get("mask_id"))
    source_id = _id(calibration.get("event_id"))
    if not smith_id or not smith_mask or not source_id:
        return history, False, "The calibration's signed identity is incomplete."
    if smith_id == account_id:
        return history, False, "A Smith cannot investigate their own work through another mask."
    if not _time(calibration.get("day"), calibration.get("hour")):
        return history, False, "The calibration time is invalid."
    if calibration["day"] != day or calibration["hour"] > hour:
        return history, False, "Only a completed calibration already performed today can be inspected."
    if not isinstance(source_event, Mapping):
        return history, False, "The canonical Smith source event is missing."
    actor = source_event.get("actor")
    payload = source_event.get("payload")
    consequence = source_event.get("consequence")
    if not all(isinstance(x, Mapping) for x in (actor, payload, consequence)):
        return history, False, "The source event lacks authoritative provenance."
    if (source_event.get("id") != source_id
            or source_event.get("kind") != SOURCE_KIND
            or source_event.get("status") != "complete"
            or actor.get("account_id") != smith_id
            or actor.get("mask_id") != smith_mask
            or actor.get("mask") != calibration.get("mask")
            or payload.get("professional_calling") != "smith"
            or payload.get("action") != "calibrate"
            or payload.get("location") != "Market Lane"
            or payload.get("day") != day
            or payload.get("hour") != calibration["hour"]
            or consequence.get("calibration_event_id") != source_id):
        return history, False, "The Smith calibration does not match a completed signed source event."
    row = {
        "event_id": event_id, "source_event_id": source_id,
        "account_id": account_id, "mask_id": mask_id,
        "mask": mask[:70], "smith_account_id": smith_id,
        "scale_id": scale_id, "market_id": market_id,
        "day": day, "hour": hour, "finding": FINDING,
    }
    return (history + [row])[-MAX_RECORDS:], True, None


def verified_record(row, *, event_lookup, scale_id, market_id):
    """Verify a persisted custody claim against both completed world events.

    Shape-valid database rows are not themselves signed evidence. The caller
    supplies a read-only canonical event lookup and the physical room/object.
    """
    if not isinstance(row, Mapping):
        return False
    if any(_id(value) is None for value in (scale_id, market_id)):
        return False
    if row.get("scale_id") != scale_id or row.get("market_id") != market_id:
        return False
    if row["source_event_id"] >= row["event_id"]:
        return False
    if not callable(event_lookup):
        return False
    try:
        smith = event_lookup(row["source_event_id"])
        inquiry = event_lookup(row["event_id"])
    except (Exception,):
        return False
    if not isinstance(smith, Mapping) or not isinstance(inquiry, Mapping):
        return False
    for event, event_id, kind in (
        (smith, row["source_event_id"], SOURCE_KIND),
        (inquiry, row["event_id"], INQUIRY_KIND),
    ):
        if (event.get("id") != event_id or type(event.get("id")) is not int
                or event.get("kind") != kind
                or event.get("status") != "complete"
                or not all(isinstance(event.get(k), Mapping)
                           for k in ("actor", "payload", "consequence"))):
            return False
    smith_actor, smith_payload, smith_result = (
        smith["actor"], smith["payload"], smith["consequence"]
    )
    detective_actor, detective_payload, detective_result = (
        inquiry["actor"], inquiry["payload"], inquiry["consequence"]
    )
    if (_id(smith_actor.get("mask_id")) is None
            or smith_actor.get("account_id") != row["smith_account_id"]
            or type(smith_actor.get("account_id")) is not int
            or not isinstance(smith_actor.get("mask"), str)
            or not smith_actor["mask"].strip()
            or smith_payload.get("professional_calling") != "smith"
            or smith_payload.get("action") != "calibrate"
            or smith_payload.get("location") != "Market Lane"
            or smith_payload.get("day") != row["day"]
            or not _time(smith_payload.get("day"), smith_payload.get("hour"))
            or smith_payload["hour"] > row["hour"]
            or smith_result.get("calibration_event_id") != row["source_event_id"]):
        return False
    if (detective_actor.get("account_id") != row["account_id"]
            or detective_actor.get("mask_id") != row["mask_id"]
            or detective_actor.get("mask") != row["mask"]
            or detective_payload.get("professional_calling") != "detective"
            or detective_payload.get("action") != "inspect"
            or detective_payload.get("location") != "Market Lane"
            or detective_payload.get("day") != row["day"]
            or detective_payload.get("hour") != row["hour"]
            or detective_payload.get("scale_object_id") != scale_id
            or detective_payload.get("smith_source_event_id")
            != row["source_event_id"]
            or detective_result.get("scale_object_id") != scale_id
            or detective_result.get("market_room_id") != market_id
            or detective_result.get("smith_source_event_id")
            != row["source_event_id"]
            or detective_result.get("finding") != FINDING
            or detective_result.get("day") != row["day"]):
        return False
    return True


def public_lines(raw, day, *, event_lookup=None, scale_id=None, market_id=None):
    rows = normalize(raw)
    today = [row for row in rows if row["day"] == day]
    if today:
        row = today[-1]
        if not verified_record(
            row, event_lookup=event_lookup,
            scale_id=scale_id, market_id=market_id,
        ):
            return (
                "A stored scale custody entry cannot be verified against "
                "completed world events; no signed Detective inquiry is shown."
            )
        return (
            f"Detective {row['mask']} inspected the physical scale "
            f"(event {row['event_id']}, Smith source {row['source_event_id']}). "
            + FINDING
        )
    return (
        "Detectives may use trade inspect after a different account's "
        "signed Smith calibration. This records limited physical evidence, "
        "not a finding of dishonesty."
    )
