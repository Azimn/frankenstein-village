"""Finite village mail parcels and signed ferry-post receipts, Evennia-free."""
from __future__ import annotations
import copy

DAILY_STOCK = 2
MAX_RECEIPTS = 48


def _id(value):
    if isinstance(value, bool):
        return None
    try:
        x = int(value)
    except (ValueError, TypeError, OverflowError):
        return None
    return x if x > 0 else None


def stock(raw, day):
    current = dict(raw or {})
    d = _id(day)
    if d is None:
        raise ValueError("Valid village day required")
    old = _id(current.get("day")) or 0
    if not old or d > old:
        return {"day": d, "remaining": DAILY_STOCK}
    return {"day": old, "remaining": max(0, min(
        DAILY_STOCK, int(current.get("remaining") or 0)))}


def issue(raw, day):
    state = stock(raw, day)
    if day < state["day"] or state["remaining"] == 0:
        return state, False
    state["remaining"] -= 1
    return state, True



def freight_contract(raw, *, accepted=False):
    """Validate source-bound Merchant freight without trusting an item label."""
    if not hasattr(raw, "get"):
        return None
    merchant = _id(raw.get("merchant_account_id"))
    source = _id(raw.get("consignment_event_id"))
    if not (merchant and source):
        return None
    if not accepted and (raw.get("accept_event_id") is not None
                         or raw.get("wanderer_account_id") is not None):
        return None  # Already accepted freight cannot be re-consigned.
    contract = {"merchant_account_id": merchant, "consignment_event_id": source}
    if accepted:
        wanderer = _id(raw.get("wanderer_account_id"))
        handoff = _id(raw.get("accept_event_id"))
        if not (wanderer and handoff) or wanderer == merchant or handoff == source:
            return None
        contract.update(wanderer_account_id=wanderer, accept_event_id=handoff)
    return contract

def manifest(raw):
    state = raw if hasattr(raw, "get") else {}
    receipts = []
    seen = set()
    for r in list(state.get("receipts") or [])[-MAX_RECEIPTS * 3:]:
        if not hasattr(r, "get"):
            continue
        source = _id(r.get("source_event_id"))
        event = _id(r.get("delivery_event_id"))
        account = _id(r.get("account_id"))
        day = _id(r.get("day"))
        if not (source and event and account and day) or source in seen:
            continue
        seen.add(source)
        receipt = {
            "source_event_id": source, "delivery_event_id": event,
            "account_id": account, "mask": str(r.get("mask") or "")[:70],
            "day": day, "parcel_id": _id(r.get("parcel_id")) or 0,
        }
        if "freight" in r:
            contract = freight_contract(r.get("freight"), accepted=True)
            if (contract is None or contract["consignment_event_id"] != source
                    or contract["wanderer_account_id"] != account):
                continue  # A corrupt freight receipt cannot become ordinary mail.
            receipt["freight"] = contract
        receipts.append(receipt)
    return {"receipts": receipts[-MAX_RECEIPTS:]}


def receive(raw, *, day, account_id, mask, parcel_id,
            source_event_id, delivery_event_id, freight=None):
    state = manifest(raw)
    values = [_id(day), _id(account_id), _id(parcel_id),
              _id(source_event_id), _id(delivery_event_id)]
    if any(x is None for x in values):
        return state, False, "Valid physical parcel and signed accounts required."
    d, aid, pid, source, event = values
    contract = freight_contract(freight, accepted=True) if freight is not None else None
    if freight is not None and (contract is None
            or contract["consignment_event_id"] != source
            or contract["wanderer_account_id"] != aid
            or contract["merchant_account_id"] == aid):
        return state, False, "Freight requires distinct signed Merchant and Wanderer custody."
    if any(r["source_event_id"] == source or r["parcel_id"] == pid
           for r in state["receipts"]):
        return state, False, "That physical parcel was already delivered."
    if state["receipts"] and d < max(r["day"] for r in state["receipts"]):
        return state, False, "A delivery cannot travel backwards in village time."
    receipt = {
        "day": d, "account_id": aid, "mask": str(mask)[:70],
        "parcel_id": pid, "source_event_id": source,
        "delivery_event_id": event,
    }
    if contract is not None:
        receipt["freight"] = contract
    state["receipts"].append(receipt)
    state["receipts"] = state["receipts"][-MAX_RECEIPTS:]
    return state, True, None
