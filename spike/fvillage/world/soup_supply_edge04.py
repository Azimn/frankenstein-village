"""Pure source verification for Merchant-to-Innkeep kitchen supply (GDD-EDGE-04).

The canonical world ledger, not a crate attribute, proves procurement.
This module owns no persistent state and can be tested without Evennia.
"""
from collections.abc import Mapping


def _id(value):
    return type(value) is int and value > 0


def verify_procurement(event, crate, *, crate_id, market_id, day,
                       receiving_account_id=None, require_distinct=False):
    """Return (valid, reason) for a real, completed, physical root crate.

    Distinct-account acceptance is mandatory for an Innkeep's professional
    receipt. Ordinary courier delivery may be performed by the procurer.
    """
    if not isinstance(event, Mapping) or not isinstance(crate, Mapping):
        return False, "The crate has no verifiable procurement source."
    actor = event.get("actor")
    payload = event.get("payload")
    result = event.get("consequence")
    if not all(isinstance(x, Mapping) for x in (actor, payload, result)):
        return False, "The procurement source is incomplete."
    event_id = event.get("id")
    merchant_id = actor.get("mask_id")
    merchant_account = actor.get("account_id")
    if not all(_id(x) for x in (
        event_id, merchant_id, merchant_account, crate_id, market_id, day
    )):
        return False, "The procurement identities are invalid."
    if event.get("status") != "complete" or event.get("kind") != (
        "professional.merchant_kitchen_procurement"
    ):
        return False, "The procurement is not a completed Merchant event."
    if payload.get("professional_calling") != "merchant":
        return False, "The procurement Calling is not authenticated."
    if (
        crate.get("procurement_event_id") != event_id
        or crate.get("merchant_id") != merchant_id
        or crate.get("merchant_account_id") != merchant_account
        or crate.get("merchant") != actor.get("mask")
        or crate.get("market_id") != market_id
        or payload.get("market_room_id") != market_id
        or result.get("crate_id") != crate_id
    ):
        return False, "The physical crate does not match the signed procurement."
    source_day = payload.get("day")
    source_hour = payload.get("hour")
    if (
        not _id(source_day)
        or type(source_hour) is not int
        or not 0 <= source_hour <= 23
        or crate.get("day") != source_day
        or day < source_day
    ):
        return False, "The crate has invalid or future village time."
    if day > source_day + 2:
        return False, "The kitchen roots are too old to accept."
    if require_distinct:
        if not _id(receiving_account_id):
            return False, "An authenticated Innkeep must receive the crate."
        if receiving_account_id == merchant_account:
            return False, "A separate account must accept Merchant stock."
    return True, None
