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
            or _id(ractor.get("account_id")) != wanderer_account_id
            or _id(ractor.get("mask_id")) != wanderer_mask_id
            or ractor.get("mask") != wanderer_mask
            or _id(entry.get("event_id")) != route_id
            or _id(entry.get("account_id")) != wanderer_account_id
            or entry.get("mask") != wanderer_mask
            or entry.get("site") != "red_cord"
            or entry.get("action") != "passability"
            or entry.get("observation") not in ("marked_caution", "unmarked")
            or rpay.get("site") != "red_cord"
            or rpay.get("role") != "wanderer"
            or rpay.get("action") != "passability"
            or rpay.get("location") != "The Northern Treeline"
            or type(rpay.get("day")) is not int or rpay["day"] != day
            or _hour(rpay.get("hour")) is None
            or rpay["hour"] > hour
            or rresult.get("site") != "red_cord"
            or rresult.get("role") != "wanderer"
            or rresult.get("action") != "passability"
            or type(rresult.get("day")) is not int or rresult["day"] != day
            or _id(rresult.get("square_room_id")) != square_room_id
            or _id(rresult.get("cord_object_id")) is None
            or rresult.get("interpretation") != entry.get("observation")
            or type(rresult.get("caution_marked")) is not bool
            or rresult["caution_marked"] != (entry["observation"] == "marked_caution")):
        return state, False, "The arrival lacks a matching signed firsthand route observation."

    cooked = _map(bowl_event)
    cactor, cpay, cresult = (
        _map(cooked.get("actor")), _map(cooked.get("payload")),
        _map(cooked.get("consequence")),
    )
    cook_id = _id(cooked.get("id"))
    if (not cook_id or cooked.get("status") != "complete"
            or cooked.get("kind") != "professional.innkeep_soup_cooked"
            or _id(cactor.get("account_id")) != innkeep_account_id
            or _id(cactor.get("mask_id")) != innkeep_mask_id
            or _id(cresult.get("bowl_id")) != bowl_id
            or _id(cresult.get("pantry_room_id")) != tavern_room_id
            or _id(cpay.get("prep_event_id")) is None
            or _id(cpay.get("packet_id")) is None
            or _id(cresult.get("source_event_id")) != cpay.get("prep_event_id")
            or _hour(cpay.get("hour")) is None
            or type(cpay.get("day")) is not int or cpay["day"] != day
            or cpay["hour"] > hour):
        return state, False, "The bowl lacks a completed signed Innkeep cooking source."

    matching = [
        row for row in state["history"]
        if _id(_map(row).get("cook_event_id")) == cook_id
        and _id(row.get("prep_event_id")) == cpay["prep_event_id"]
        and _id(row.get("maker_id")) == innkeep_mask_id
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


def verified_public_welcome(history, get_event):
    """Return public, source-backed history, never an assertion from mutable soup data.

    This is a read-only projection of completed canonical events. A stale or
    forged batch Attribute cannot manufacture a public hospitality claim.
    The actual bowl may later be eaten; signed transfer remains historical.
    """
    if not isinstance(history, (list, tuple)) or not callable(get_event):
        return ""
    for batch in reversed(history):
        row = _map(batch)
        receipt = _map(row.get("arrival_welcome"))
        if not receipt:
            continue
        keys = ("event_id", "route_event_id", "cook_event_id", "bowl_id",
                "innkeep_account_id", "innkeep_mask_id",
                "wanderer_account_id", "wanderer_mask_id", "day")
        if any(_id(receipt.get(key)) is None for key in keys):
            continue
        if (_hour(receipt.get("hour")) is None
                or receipt.get("service") != "physical_bowl_transferred"
                or not isinstance(receipt.get("wanderer_mask"), str)
                or not receipt["wanderer_mask"]
                or _id(row.get("cook_event_id")) != receipt["cook_event_id"]
                or _id(row.get("maker_id")) != receipt["innkeep_mask_id"]
                or _id(row.get("prep_event_id")) is None
                or receipt["innkeep_account_id"] == receipt["wanderer_account_id"]
                or receipt["event_id"] <= max(receipt["route_event_id"],
                                               receipt["cook_event_id"])):
            continue
        try:
            event = _map(get_event(receipt["event_id"]))
            route = _map(get_event(receipt["route_event_id"]))
            cook = _map(get_event(receipt["cook_event_id"]))
        except (LookupError, TypeError, ValueError, AttributeError):
            continue
        actor, payload, result = (
            _map(event.get("actor")), _map(event.get("payload")),
            _map(event.get("consequence")),
        )
        ractor, rpay, rresult = (
            _map(route.get("actor")), _map(route.get("payload")),
            _map(route.get("consequence")),
        )
        cactor, cpay, cresult = (
            _map(cook.get("actor")), _map(cook.get("payload")),
            _map(cook.get("consequence")),
        )
        if (event.get("status") != "complete"
                or event.get("kind") != "professional.innkeep_wanderer_arrival_welcome"
                or _id(event.get("id")) != receipt["event_id"]
                or _id(actor.get("account_id")) != receipt["innkeep_account_id"]
                or _id(actor.get("mask_id")) != receipt["innkeep_mask_id"]
                or _id(payload.get("guest_account_id")) != receipt["wanderer_account_id"]
                or _id(payload.get("guest_mask_id")) != receipt["wanderer_mask_id"]
                or _id(payload.get("route_event_id")) != receipt["route_event_id"]
                or _id(payload.get("cook_event_id")) != receipt["cook_event_id"]
                or _id(payload.get("bowl_id")) != receipt["bowl_id"]
                or _id(payload.get("tavern_room_id")) is None
                or type(payload.get("day")) is not int
                or payload["day"] != receipt["day"]
                or _hour(payload.get("hour")) != receipt["hour"]
                or _id(result.get("route_event_id")) != receipt["route_event_id"]
                or _id(result.get("cook_event_id")) != receipt["cook_event_id"]
                or _id(result.get("bowl_id")) != receipt["bowl_id"]
                or _id(result.get("innkeep_account_id")) != receipt["innkeep_account_id"]
                or _id(result.get("wanderer_account_id")) != receipt["wanderer_account_id"]
                or result.get("service") != "physical_bowl_transferred"):
            continue
        if (route.get("status") != "complete"
                or route.get("kind") != "village.route_passability_observed"
                or _id(route.get("id")) != receipt["route_event_id"]
                or _id(ractor.get("account_id")) != receipt["wanderer_account_id"]
                or _id(ractor.get("mask_id")) != receipt["wanderer_mask_id"]
                or ractor.get("mask") != receipt["wanderer_mask"]
                or rpay.get("location") != "The Northern Treeline"
                or rpay.get("site") != "red_cord"
                or rpay.get("role") != "wanderer"
                or rpay.get("action") != "passability"
                or type(rpay.get("day")) is not int
                or rpay["day"] != receipt["day"]
                or _hour(rpay.get("hour")) is None
                or rpay["hour"] > receipt["hour"]
                or rresult.get("site") != "red_cord"
                or rresult.get("role") != "wanderer"
                or rresult.get("action") != "passability"
                or rresult.get("interpretation") != receipt.get("route_observation")
                or type(rresult.get("caution_marked")) is not bool
                or rresult["caution_marked"] != (
                    receipt.get("route_observation") == "marked_caution")):
            continue
        if (cook.get("status") != "complete"
                or cook.get("kind") != "professional.innkeep_soup_cooked"
                or _id(cook.get("id")) != receipt["cook_event_id"]
                or _id(cactor.get("account_id")) != receipt["innkeep_account_id"]
                or _id(cactor.get("mask_id")) != receipt["innkeep_mask_id"]
                or _id(cpay.get("prep_event_id")) != row["prep_event_id"]
                or type(cpay.get("day")) is not int
                or cpay["day"] != receipt["day"]
                or _hour(cpay.get("hour")) is None
                or cpay["hour"] > receipt["hour"]
                or _id(cresult.get("bowl_id")) != receipt["bowl_id"]
                or _id(cresult.get("pantry_room_id")) != payload["tavern_room_id"]
                or _id(cresult.get("source_event_id")) != row["prep_event_id"]):
            continue
        return (
            " Signed returning-traveler hospitality: "
            + receipt["wanderer_mask"][:70]
            + " received a real cooked bowl (route event "
            + str(receipt["route_event_id"])
            + "; welcome event " + str(receipt["event_id"])
            + "). This historical receipt does not certify route safety."
        )
    return ""
