"""Read-only completed-event verification for the existing Old Stone Bridge.

The room Attribute is a projection, not a second authority for signed claims.
This module has no Evennia imports and never changes the canonical ledger,
finite stock, physical inventory, or the solo bridgework transitions.
"""
from __future__ import annotations

from world import bridge_choices

BRIDGE = "The Old Stone Bridge"
MARKET = "Market Lane"


def _id(value):
    return value if type(value) is int and value > 0 else None


def _hour(value):
    return value if type(value) is int and 0 <= value <= 23 else None


def _get(value):
    return value if hasattr(value, "get") else {}


def _event(get_event, event_id, kind):
    if _id(event_id) is None or not callable(get_event):
        return None
    try:
        event = _get(get_event(event_id))
    except Exception:
        return None
    if (event.get("status") != "complete"
            or event.get("kind") != kind
            or _id(event.get("id")) != event_id):
        return None
    return event


def _collection(event, *, choice, item_id, source_day=None,
                market_table_id=None, current_day=None):
    event = _get(event)
    actor = _get(event.get("actor"))
    payload = _get(event.get("payload"))
    result = _get(event.get("consequence"))
    day = payload.get("day")
    hour = payload.get("hour")
    if (event.get("status") != "complete"
            or event.get("kind") != "village.bridge_material_collected"
            or _id(event.get("id")) is None
            or _id(actor.get("account_id")) is None
            or _id(actor.get("mask_id")) is None
            or not isinstance(actor.get("mask"), str)
            or not actor["mask"]
            or payload.get("choice") != choice
            or payload.get("location") != MARKET
            or _id(day) is None
            or _hour(hour) is None
            or _id(result.get("item_id")) != item_id
            or result.get("choice") != choice
            or _id(result.get("market_table_id")) is None
            or type(result.get("remaining")) is not int
            or not 0 <= result["remaining"] <= 2):
        return False
    if source_day is not None and day != source_day:
        return False
    if market_table_id is not None and result["market_table_id"] != market_table_id:
        return False
    if current_day is not None and (_id(current_day) is None or day > current_day):
        return False
    return True


def verified_kit(kit, get_event, *, choice, market_table_id, current_day):
    """Verify an actual carried object against its completed collection event.

    The collecting account may differ from the present carrier: ordinary
    players can give physical kits to one another.
    """
    kit = _get(kit)
    item_id = _id(kit.get("item_id"))
    event_id = _id(kit.get("source_event_id"))
    source_day = _id(kit.get("source_day"))
    if (choice not in bridge_choices.CHOICES
            or None in (item_id, event_id, source_day,
                        _id(market_table_id), _id(current_day))):
        return False
    event = _event(get_event, event_id, "village.bridge_material_collected")
    return bool(event and _collection(
        event, choice=choice, item_id=item_id,
        source_day=source_day, market_table_id=market_table_id,
        current_day=current_day,
    ))


def _resolution(row, get_event, bridge_room_id):
    row = _get(row)
    if (row.get("choice") not in bridge_choices.CHOICES
            or any(_id(row.get(key)) is None for key in
                   ("account_id", "mask_id", "day", "event_id"))
            or _hour(row.get("hour")) is None
            or not isinstance(row.get("mask"), str)
            or not row["mask"]):
        return False
    event = _event(get_event, row["event_id"], "village.bridge_response")
    if event is None:
        return False
    actor = _get(event.get("actor"))
    payload = _get(event.get("payload"))
    result = _get(event.get("consequence"))
    source_id = _id(result.get("source_event_id"))
    item_id = _id(result.get("consumed_item_id"))
    if (actor.get("account_id") != row["account_id"]
            or actor.get("mask_id") != row["mask_id"]
            or actor.get("mask") != row["mask"]
            or payload.get("choice") != row["choice"]
            or payload.get("location") != BRIDGE
            or payload.get("day") != row["day"]
            or payload.get("hour") != row["hour"]
            or result.get("choice") != row["choice"]
            or type(result.get("signed_upkeep")) is not int
            or result["signed_upkeep"] != 0
            or source_id is None or item_id is None
            or source_id >= row["event_id"]):
        return False
    # Newly signed receipts carry an exact room ID. Earlier legitimate
    # receipts predate that field, but still require the canonical location
    # and complete physical source event. Never rewrite historical events.
    recorded_bridge_id = result.get("bridge_room_id")
    if recorded_bridge_id is not None and (
            _id(bridge_room_id) is None
            or _id(recorded_bridge_id) != bridge_room_id):
        return False
    collection = _event(
        get_event, source_id, "village.bridge_material_collected"
    )
    if not collection or not _collection(
            collection, choice=row["choice"], item_id=item_id,
            current_day=row["day"]):
        return False
    collection_payload = _get(collection.get("payload"))
    if (collection_payload["day"] == row["day"]
            and collection_payload["hour"] > row["hour"]):
        return False
    return True


def _upkeep(row, resolution, get_event):
    row = _get(row)
    if any(_id(row.get(key)) is None for key in
           ("account_id", "mask_id", "day", "event_id")):
        return False
    if (row["event_id"] <= resolution["event_id"]
            or row["day"] < resolution["day"]):
        return False
    event = _event(get_event, row["event_id"], "village.bridge_upkeep")
    if event is None:
        return False
    actor = _get(event.get("actor"))
    payload = _get(event.get("payload"))
    result = _get(event.get("consequence"))
    return bool(
        actor.get("account_id") == row["account_id"]
        and actor.get("mask_id") == row["mask_id"]
        and payload.get("choice") is None
        and payload.get("location") == BRIDGE
        and payload.get("day") == row["day"]
        and _hour(payload.get("hour")) is not None
        and result.get("choice") == resolution["choice"]
        and type(result.get("signed_upkeep")) is int
        and 1 <= result["signed_upkeep"] <= bridge_choices.MAX_CHECKS
    )


def verified_state(raw, get_event, *, bridge_room_id=None):
    """Return (safe public state, entirely_valid).

    A forged response never becomes a physical public outcome. Invalid
    upkeep entries are omitted, while an authentic original response remains
    visible. A caller must not authorize further upkeep from invalid history.
    """
    original = _get(raw)
    state = bridge_choices.normalize(raw)
    empty = {"resolution": None, "checks": []}
    row = _get(original.get("resolution"))
    if not row:
        return empty, not bool(original.get("checks"))
    if not _resolution(row, get_event, bridge_room_id):
        return empty, False
    resolution = state["resolution"]
    if resolution is None:
        return empty, False
    safe = {"resolution": resolution, "checks": []}
    seen_ids = set()
    seen_account_days = set()
    valid = True
    for raw_check in list(original.get("checks") or [])[-bridge_choices.MAX_CHECKS:]:
        check = _get(raw_check)
        signature = (check.get("account_id"), check.get("day"))
        event_id = check.get("event_id")
        if (event_id in seen_ids or signature in seen_account_days
                or not _upkeep(check, resolution, get_event)):
            valid = False
            continue
        seen_ids.add(event_id)
        seen_account_days.add(signature)
        safe["checks"].append({
            key: check[key] for key in
            ("account_id", "mask_id", "day", "event_id")
        })
    return safe, valid


def public_line(raw, get_event, *, bridge_room_id=None):
    """Production public projection, including explicit unverified warning."""
    safe, valid = verified_state(
        raw, get_event, bridge_room_id=bridge_room_id
    )
    line = bridge_choices.public_line(safe)
    if not valid:
        line += (
            " Some saved bridge signatures cannot be verified against "
            "completed world events; unsupported claims are withheld."
        )
    return line
