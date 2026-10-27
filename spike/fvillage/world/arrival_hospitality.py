"""Pure, source-bound hospitality transition for GDD-EDGE-05.

The existing Tavern soup batch is the durable receipt. A Wanderer first signs
a real treeline observation; an independent Innkeep then transfers a genuinely
cooked, finite bowl. Neither role invents a stranded traveler or route safety.
"""
from __future__ import annotations

from collections.abc import Mapping

from world import soup_state


def _id(value):
    return value if type(value) is int and value > 0 else None


def _hour(value):
    return value if type(value) is int and 0 <= value <= 23 else None


def _map(value):
    return value if isinstance(value, Mapping) else {}


def welcome(raw, *, day, hour, innkeep_account_id, innkeep_mask_id,
            wanderer_account_id, wanderer_mask_id, wanderer_mask,
            route_entry, route_event, bowl_event, bowl_id,
            square_room_id, tavern_room_id, event_id):
    """Validate independent completed events and append one persistent receipt.

    The caller is responsible for checking the actual held bowl and both
    characters' current room and Callings. No state is changed on failure.
    """
    state = soup_state.pantry(raw, day)
    if (_id(day) is None or _hour(hour) is None
            or state["day"] != day):
        return state, False, "The kitchen cannot backdate a welcome."
    values = (innkeep_account_id, innkeep_mask_id, wanderer_account_id,
              wanderer_mask_id, bowl_id, square_room_id, tavern_room_id, event_id)
    if any(_id(v) is None for v in values):
        return state, False, "Signed identities and physical objects are required."
    if innkeep_account_id == wanderer_account_id:
        return state, False, "The Wanderer and Innkeep must be different accounts."

    route = _map(route_event)
    ractor, rpay, rresult = (
        _map(route.get("actor")), _map(route.get("payload")),
        _map(route.get("consequence")),
    )
    entry = _map(route_entry)
    route_id = _id(route.get("id"))
    if (not route_id or route.get("status") != "complete"
            or route.get("kind") != "village.route_passability_observed"
            or ractor.get("account_id") != wanderer_account_id
            or ractor.get("mask_id") != wanderer_mask_id
            or ractor.get("mask") != wanderer_mask
            or entry.get("event_id") != route_id
            or entry.get("account_id") != wanderer_account_id
            or entry.get("mask") != wanderer_mask
            or entry.get("site") != "red_cord"
            or entry.get("action") != "passability"
            or entry.get("observation") not in ("marked_caution", "unmarked")
            or rpay.get("site") != "red_cord"
            or rpay.get("role") != "wanderer"
            or rpay.get("action") != "passability"
            or rpay.get("location") != "The Northern Treeline"
            or rpay.get("day") != day
            or _hour(rpay.get("hour")) is None
            or rpay["hour"] > hour
            or rresult.get("site") != "red_cord"
            or rresult.get("role") != "wanderer"
            or rresult.get("action") != "passability"
            or rresult.get("day") != day
            or rresult.get("square_room_id") != square_room_id
            or _id(rresult.get("cord_object_id")) is None):
        return state, False, "The arrival lacks a matching signed firsthand route observation."

    cooked = _map(bowl_event)
    cactor, cpay, cresult = (
        _map(cooked.get("actor")), _map(cooked.get("payload")),
        _map(cooked.get("consequence")),
    )
    cook_id = _id(cooked.get("id"))
    if (not cook_id or cooked.get("status") != "complete"
            or cooked.get("kind") != "professional.innkeep_soup_cooked"
            or cactor.get("account_id") != innkeep_account_id
            or cactor.get("mask_id") != innkeep_mask_id
            or cresult.get("bowl_id") != bowl_id
            or cresult.get("pantry_room_id") != tavern_room_id
            or _id(cpay.get("prep_event_id")) is None
            or _id(cpay.get("packet_id")) is None
            or _id(cresult.get("source_event_id")) != cpay.get("prep_event_id")
            or _hour(cpay.get("hour")) is None
            or cpay.get("day") != day
            or cpay["hour"] > hour):
        return state, False, "The bowl lacks a completed signed Innkeep cooking source."

    matching = [
        row for row in state["history"]
        if _map(row).get("cook_event_id") == cook_id
        and row.get("prep_event_id") == cpay["prep_event_id"]
        and row.get("maker_id") == innkeep_mask_id
        and row.get("base") == cpay.get("base")
        and row.get("seasoning") == cpay.get("seasoning")
    ]
    if len(matching) != 1:
        return state, False, "The actual cooked batch is missing from the Tavern pantry."
    if any(_map(_map(row).get("arrival_welcome")).get("route_event_id") == route_id
           or _map(_map(row).get("arrival_welcome")).get("bowl_id") == bowl_id
           for row in state["history"]):
        return state, False, "This arrival or physical bowl has already been welcomed."
    batch = matching[0]
    if batch.get("arrival_welcome"):
        return state, False, "This batch has already been committed to a guest."
    batch["arrival_welcome"] = {
        "event_id": event_id, "day": day, "hour": hour,
        "route_event_id": route_id,
        "wanderer_account_id": wanderer_account_id,
        "wanderer_mask_id": wanderer_mask_id,
        "wanderer_mask": wanderer_mask,
        "innkeep_account_id": innkeep_account_id,
        "innkeep_mask_id": innkeep_mask_id,
        "bowl_id": bowl_id, "cook_event_id": cook_id,
        "service": "physical_bowl_transferred",
        "route_observation": entry["observation"],
    }
    return state, True, None
