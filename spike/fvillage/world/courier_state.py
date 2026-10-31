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
        seen.add(source)
        receipts.append(receipt)
    return {"receipts": receipts[-MAX_RECEIPTS:]}




def _positive_int(value):
    """Ledger/public receipt IDs must be actual positive integers, not booleans."""
    return type(value) is int and value > 0


def _signed_event(lookup, event_id, kind):
    if not _positive_int(event_id):
        return None
    try:
        event = lookup(event_id)
    except (KeyError, LookupError, ValueError, TypeError, AttributeError):
        return None
    if not isinstance(event, dict) or event.get("status") != "complete" or event.get("kind") != kind:
        return None
    if event.get("id") != event_id:
        return None
    if not all(isinstance(event.get(k), dict) for k in ("actor", "payload", "consequence")):
        return None
    return event


def public_manifest(raw, event_lookup, *, riverside_room_id):
    """Verify *every* retained receipt against canonical completed events.

    Returns (receipts, verified). A damaged newer row cannot be dropped to
    display an older signed row as the latest. The ordinary write normalizer
    remains unchanged; this strict path is exclusively for public claims.
    """
    if not _positive_int(riverside_room_id) or not callable(event_lookup):
        return [], False
    if raw is None:
        return [], True
    if not hasattr(raw, "get"):
        return [], False
    original = raw.get("receipts", [])
    if not isinstance(original, (list, tuple)) or len(original) > MAX_RECEIPTS:
        return [], False
    if any(not isinstance(row, dict) for row in original):
        return [], False
    try:
        normalized = manifest(raw)["receipts"]
    except (TypeError, ValueError, AttributeError, OverflowError):
        return [], False
    if len(normalized) != len(original):
        return [], False

    seen_sources, seen_deliveries, seen_parcels = set(), set(), set()
    previous_day = 0
    for row, signed in zip(original, normalized):
        # Reject silently normalized/corrupt values, not just missing events.
        if row != signed or not all(
            _positive_int(signed.get(k)) for k in (
                "source_event_id", "delivery_event_id", "account_id",
                "day", "parcel_id"
            )
        ):
            return [], False
        source_id, delivery_id = signed["source_event_id"], signed["delivery_event_id"]
        parcel_id, day = signed["parcel_id"], signed["day"]
        if (source_id >= delivery_id or day < previous_day
                or source_id in seen_sources or delivery_id in seen_deliveries
                or parcel_id in seen_parcels):
            return [], False
        seen_sources.add(source_id)
        seen_deliveries.add(delivery_id)
        seen_parcels.add(parcel_id)
        previous_day = day
        delivery = _signed_event(event_lookup, delivery_id, "village.ferry_post_delivered")
        if delivery is None:
            return [], False
        actor, payload, result = (
            delivery["actor"], delivery["payload"], delivery["consequence"]
        )
        if (actor.get("account_id") != signed["account_id"]
                or actor.get("mask") != signed["mask"]
                or payload.get("day") != day
                or payload.get("source_event_id") != source_id
                or payload.get("parcel_id") != parcel_id
                or result.get("riverside_room_id") != riverside_room_id
                or result.get("parcel_id") != parcel_id
                or result.get("source_event_id") != source_id):
            return [], False

        freight = signed.get("freight")
        if freight is None:
            if payload.get("freight_accept_event_id") is not None:
                return [], False
            source = _signed_event(event_lookup, source_id, "village.ferry_post_collected")
            if source is None:
                return [], False
            if (not _positive_int(source["actor"].get("account_id"))
                    or not _positive_int(source["payload"].get("market_room_id"))
                    or not _positive_int(source["payload"].get("day"))
                    or source["payload"]["day"] > day
                    or source["consequence"].get("parcel_id") != parcel_id):
                return [], False
        else:
            contract = freight_contract(freight, accepted=True)
            if contract != freight:
                return [], False
            accept_id = contract["accept_event_id"]
            if (not source_id < accept_id < delivery_id
                    or payload.get("freight_accept_event_id") != accept_id):
                return [], False
            source = _signed_event(event_lookup, source_id, "village.freight_consigned")
            handoff = _signed_event(event_lookup, accept_id, "village.freight_accepted")
            if source is None or handoff is None:
                return [], False
            sm, sp, sr = source["actor"], source["payload"], source["consequence"]
            ha, hp, hr = handoff["actor"], handoff["payload"], handoff["consequence"]
            if (sm.get("account_id") != contract["merchant_account_id"]
                    or sp.get("professional_calling") != "merchant"
                    or not _positive_int(sp.get("market_room_id"))
                    or not _positive_int(sp.get("day"))
                    or sr.get("parcel_id") != parcel_id
                    or ha.get("account_id") != contract["wanderer_account_id"]
                    or ha.get("account_id") != signed["account_id"]
                    or hp.get("professional_calling") != "wanderer"
                    or hp.get("source_event_id") != source_id
                    or hp.get("parcel_id") != parcel_id
                    or not _positive_int(hp.get("day"))
                    or not sp["day"] <= hp["day"] <= day
                    or hr.get("parcel_id") != parcel_id
                    or hr.get("consignment_event_id") != source_id):
                return [], False
    return normalized, True

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
