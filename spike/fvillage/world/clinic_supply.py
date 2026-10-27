"""Pure finite linen procurement and source-bound clinical acceptance.

Market Lane owns daily supply, the parcel owns custody, the ledger owns
attribution, and the existing Church clinic state owns accepted linen.
"""
from __future__ import annotations
from collections.abc import Mapping
from world import clinic_state

MARKET_DAILY = 1
UNITS = 2


def positive(value):
    return type(value) is int and value > 0


def stock(raw, day):
    if not positive(day):
        raise ValueError("Village day must be positive.")
    source = dict(raw) if isinstance(raw, Mapping) else {}
    old_day = source.get("day")
    if not positive(old_day) or day > old_day:
        return {"day": day, "remaining": MARKET_DAILY}
    remaining = source.get("remaining")
    if type(remaining) is not int:
        remaining = 0
    return {"day": old_day, "remaining": max(0, min(MARKET_DAILY, remaining))}


def issue(raw, day):
    current = stock(raw, day)
    if day < current["day"]:
        return current, False, "The market supply is recorded for a later day."
    if not current["remaining"]:
        return current, False, "Today's sealed clinic linen supply is exhausted."
    current["remaining"] -= 1
    return current, True, None


def verify_source(event, parcel, *, item_id, market_id, healer_account_id, day):
    """A portable parcel is not proof by itself: verify its signed ledger source."""
    error = "The clinic parcel has no valid completed Merchant source event."
    if not all(positive(v) for v in (item_id, market_id, healer_account_id, day)):
        return False, error
    if not isinstance(event, Mapping) or not isinstance(parcel, Mapping):
        return False, error
    actor = event.get("actor")
    payload = event.get("payload")
    consequence = event.get("consequence")
    if not all(isinstance(x, Mapping) for x in (actor, payload, consequence)):
        return False, error
    source_day = parcel.get("day")
    source_hour = parcel.get("hour")
    merchant = parcel.get("merchant_account_id")
    mask = parcel.get("merchant_mask_id")
    source_id = parcel.get("source_event_id")
    if not all(positive(v) for v in (source_day, merchant, mask, source_id)):
        return False, error
    if (type(source_hour) is not int or not 0 <= source_hour <= 23
            or source_day > day or day > source_day + 1
            or merchant == healer_account_id):
        return False, error
    if (event.get("id") != source_id
            or event.get("kind") != "professional.merchant_clinic_supply"
            or event.get("status") != "complete"
            or actor.get("account_id") != merchant
            or actor.get("mask_id") != mask
            or payload.get("professional_calling") != "merchant"
            or payload.get("day") != source_day
            or payload.get("hour") != source_hour
            or payload.get("market_room_id") != market_id
            or consequence.get("parcel_id") != item_id
            or consequence.get("market_room_id") != market_id
            or consequence.get("units") != UNITS
            or parcel.get("market_room_id") != market_id
            or parcel.get("units") != UNITS
            or parcel.get("material") != "clean_linen"):
        return False, error
    return True, None


def accept(raw, *, day, event_id, source_event_id, source_day,
           parcel_id, merchant_account_id, healer_account_id):
    state = clinic_state.refresh(raw, day)
    if day < state["day"]:
        return state, False, "The clinic has a later day's cabinet record."
    if not all(positive(v) for v in (
            day, event_id, source_event_id, source_day, parcel_id,
            merchant_account_id, healer_account_id)):
        return state, False, "The delivery requires valid signed accounts and source IDs."
    if merchant_account_id == healer_account_id:
        return state, False, "A different Merchant account must supply the Healer."
    if source_day > day or day > source_day + 1:
        return state, False, "The linen shipment is stale or dated in the future."
    if state["supply"]:
        return state, False, "The clinic has already accepted today's Merchant parcel."
    if state["linen"] + UNITS > clinic_state.MAX_LINEN:
        return state, False, "The cabinet has no space for another linen shipment."
    state["linen"] += UNITS
    state["supply"] = {
        "day": day, "event_id": event_id, "source_event_id": source_event_id,
        "source_day": source_day, "parcel_id": parcel_id,
        "merchant_account_id": merchant_account_id,
        "healer_account_id": healer_account_id,
    }
    return state, True, None
