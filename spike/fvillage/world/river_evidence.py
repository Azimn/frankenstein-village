"""Source-bound, two-Calling river evidence on the ORIGINAL Riverside gauge.

A Wanderer signs a physical flood-mark reading. A separate Detective may
compare that observation with the gauge, preserving a qualified case note.
This is not a bridge solution, a flood prediction, or a second case ledger.
"""
from __future__ import annotations

import copy
from collections.abc import Mapping, Sequence

MAX_HISTORY = 28


def _positive(value):
    return type(value) is int and value > 0


def _time(day, hour):
    return _positive(day) and type(hour) is int and 0 <= hour < 24


def _signature(row):
    if not isinstance(row, Mapping):
        return None
    keys = ("account_id", "mask_id", "event_id", "day", "hour", "object_id")
    if not all(_positive(row.get(k)) for k in keys if k != "hour"):
        return None
    if not _time(row["day"], row.get("hour")):
        return None
    mask = row.get("mask")
    if not isinstance(mask, str) or not mask.strip():
        return None
    return {k: row[k] for k in keys} | {"mask": mask[:70]}


def fresh(day=0):
    return {"day": day, "witness": None, "review": None, "history": []}


def normalize(raw):
    if not isinstance(raw, Mapping):
        return fresh()
    day = raw.get("day")
    state = fresh(day if type(day) is int and day >= 0 else 0)
    witness = _signature(raw.get("witness"))
    if witness and witness["day"] == state["day"]:
        state["witness"] = witness
    review = _signature(raw.get("review"))
    # The source linkage is checked separately to reject corrupted state.
    if review and witness and review["day"] == state["day"]:
        source = raw["review"].get("source_event_id")
        if (_positive(source) and source == witness["event_id"]
                and review["object_id"] == witness["object_id"]
                and review["account_id"] != witness["account_id"]
                and review["mask_id"] != witness["mask_id"]
                and review["event_id"] != witness["event_id"]
                and review["hour"] >= witness["hour"]):
            state["review"] = review | {"source_event_id": source}
    history = raw.get("history")
    if isinstance(history, Sequence) and not isinstance(history, (str, bytes)):
        for row in list(history)[-MAX_HISTORY * 2:]:
            if isinstance(row, Mapping) and _positive(row.get("day")) and row["day"] < state["day"]:
                state["history"].append(copy.deepcopy(dict(row)))
    state["history"] = state["history"][-MAX_HISTORY:]
    return state


def refresh(raw, day):
    state = normalize(raw)
    if not _positive(day):
        return state, False, "A valid village day is required."
    if day < state["day"]:
        return state, False, "A later village day is already recorded."
    if day > state["day"]:
        if state["day"] and state["witness"]:
            state["history"].append({
                "day": state["day"],
                "witness": copy.deepcopy(state["witness"]),
                "review": copy.deepcopy(state["review"]),
            })
        state["history"] = state["history"][-MAX_HISTORY:]
        state["day"] = day
        state["witness"] = None
        state["review"] = None
    return state, True, None


def witness(raw, *, day, hour, account_id, mask_id, mask, event_id, object_id):
    state, ok, error = refresh(raw, day)
    if not ok:
        return state, False, error
    signed = _signature(dict(day=day, hour=hour, account_id=account_id,
                             mask_id=mask_id, mask=mask, event_id=event_id,
                             object_id=object_id))
    if signed is None:
        return state, False, "A real account, mask, gauge, event and village time are required."
    if state["witness"]:
        return state, False, "A Wanderer's gauge observation is already signed today."
    state["witness"] = signed
    return state, True, None


def compare(raw, *, day, hour, account_id, mask_id, mask, event_id,
            object_id, source_event_id):
    state, ok, error = refresh(raw, day)
    if not ok:
        return state, False, error
    signed = _signature(dict(day=day, hour=hour, account_id=account_id,
                             mask_id=mask_id, mask=mask, event_id=event_id,
                             object_id=object_id))
    if signed is None or not _positive(source_event_id):
        return state, False, "A signed Detective and source event are required."
    source = state["witness"]
    if not source:
        return state, False, "A firsthand Wanderer gauge observation is needed."
    if state["review"]:
        return state, False, "This gauge observation already has a Detective comparison."
    if source["event_id"] != source_event_id or source["object_id"] != object_id:
        return state, False, "The source does not belong to this physical gauge."
    if source["account_id"] == account_id or source["mask_id"] == mask_id:
        return state, False, "A separate account and character must review the source."
    if hour < source["hour"]:
        return state, False, "The village clock predates the witnessed reading."
    if source_event_id == event_id:
        return state, False, "The Detective must sign a new canonical event."
    state["review"] = signed | {"source_event_id": source_event_id}
    return state, True, None


def public_lines(raw, day):
    state, ok, error = refresh(raw, day)
    if not ok:
        return ["The river gauge has a later dated record; do not backdate evidence."]
    lines = ["Riverside gauge: physical flood marks are evidence, not a forecast."]
    if state["witness"]:
        w = state["witness"]
        lines.append(
            f"Wanderer {w['mask']} recorded firsthand gauge marks on day "
            f"{w['day']} (event {w['event_id']})."
        )
    if state["review"]:
        d = state["review"]
        lines.append(
            f"Detective {d['mask']} preserved a separate comparison "
            f"(event {d['event_id']}, source {d['source_event_id']}). "
            "The record does not establish who removed the bridge plaque."
        )
    if not state["witness"]:
        lines.append("No signed Wanderer gauge reading exists today.")
    return lines


def _verified_signed_event(row, event, *, kind, calling, gauge_id, room_id,
                           witness_event_id=None):
    """Check a completed canonical event against the original physical gauge."""
    if (row is None or not isinstance(event, Mapping)
            or type(gauge_id) is not int or gauge_id <= 0
            or type(room_id) is not int or room_id <= 0):
        return False
    actor, payload, consequence = (
        event.get("actor"), event.get("payload"), event.get("consequence"))
    if not all(isinstance(part, Mapping)
               for part in (actor, payload, consequence)):
        return False
    is_witness = calling == "wanderer"
    return (
        type(event.get("id")) is int
        and event["id"] == row["event_id"]
        and event.get("kind") == kind
        and event.get("status") == "complete"
        and actor.get("account_id") == row["account_id"]
        and actor.get("mask_id") == row["mask_id"]
        and actor.get("mask") == row["mask"]
        and payload.get("calling") == calling
        and type(payload.get("day")) is int
        and payload["day"] == row["day"]
        and type(payload.get("hour")) is int
        and payload["hour"] == row["hour"]
        and type(payload.get("object_id")) is int
        and payload["object_id"] == gauge_id == row["object_id"]
        and type(payload.get("room_id")) is int
        and payload["room_id"] == room_id
        and payload.get("location") == "Riverside Path"
        and payload.get("source_event_id") ==
            (None if is_witness else witness_event_id)
        and type(consequence.get("gauge_object_id")) is int
        and consequence["gauge_object_id"] == gauge_id
        and type(consequence.get("room_id")) is int
        and consequence["room_id"] == room_id
        and type(consequence.get("account_id")) is int
        and consequence["account_id"] == row["account_id"]
        and consequence.get("witness_event_id") ==
            (row["event_id"] if is_witness else witness_event_id)
        and consequence.get("review_event_id") ==
            (None if is_witness else row["event_id"])
        and consequence.get("source_event_id") ==
            (None if is_witness else witness_event_id)
    )


def verified_public_lines(raw, day, *, gauge_id, room_id,
                          witness_event=None, review_event=None):
    """Fail-closed ordinary-player readback from the canonical event ledger.

    The gauge's persisted attributes are a projection, not a source of
    authority. Never attribute a professional action solely from that data.
    """
    state, ok, _error = refresh(raw, day)
    if not ok:
        return ["The river gauge has a later dated record; do not backdate evidence."]
    witness_row = state["witness"]
    witness_valid = _verified_signed_event(
        witness_row, witness_event,
        kind="village.river_gauge_witnessed", calling="wanderer",
        gauge_id=gauge_id, room_id=room_id,
    )
    review_row = state["review"]
    review_valid = (
        witness_valid and review_row is not None
        and review_row["source_event_id"] == witness_row["event_id"]
        and witness_row["event_id"] < review_row["event_id"]
        and review_row["day"] == witness_row["day"]
        and review_row["hour"] >= witness_row["hour"]
        and review_row["account_id"] != witness_row["account_id"]
        and review_row["mask_id"] != witness_row["mask_id"]
        and _verified_signed_event(
            review_row, review_event,
            kind="village.river_evidence_compared", calling="detective",
            gauge_id=gauge_id, room_id=room_id,
            witness_event_id=witness_row["event_id"],
        )
    )
    state["witness"] = witness_row if witness_valid else None
    state["review"] = review_row if review_valid else None
    return public_lines(state, day)
