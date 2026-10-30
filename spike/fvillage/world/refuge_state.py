"""Pure EDGE-08 rules: witnessed Hound arrival and finite Innkeep refuge."""
from __future__ import annotations

from world import soup_state

TREELINE = "The Northern Treeline"
MAX_RECEIPTS = 24


def ident(value):
    """Accept only lossless positive IDs, never truncating fractional evidence."""
    if type(value) is int:
        return value if value > 0 else None
    if not (isinstance(value, str) and value.isascii()
            and value.isdecimal() and len(value) <= 32):
        return None
    number = int(value)
    return number if number > 0 else None


def stamp(day, hour):
    d = ident(day)
    if type(hour) is int:
        h = hour
    elif (isinstance(hour, str) and hour.isascii()
          and hour.isdecimal() and len(hour) <= 4):
        h = int(hour)
    else:
        return None
    return (d - 1) * 24 + h if d and 0 <= h <= 23 else None


def mapping(value):
    return value if hasattr(value, "get") else {}


def same_actor(current_account_id, current_mask_id, expected_account_id, expected_mask_id):
    """Fail closed if a logged-in mask changes its controlling account mid-action."""
    values = (current_account_id, current_mask_id,
              expected_account_id, expected_mask_id)
    return (all(type(value) is int and value > 0 for value in values)
            and current_account_id == expected_account_id
            and current_mask_id == expected_mask_id)


def protection_valid(event, marker, cord_id):
    """Only a completed ledger event matching the ORIGINAL marked cord."""
    event, marker = mapping(event), mapping(marker)
    actor, payload, consequence = (
        mapping(event.get("actor")), mapping(event.get("payload")),
        mapping(event.get("consequence")))
    marker_day = marker.get("day")
    source_day = payload.get("day")
    effect_day = consequence.get("day")
    prior_marker = marker.get("prior_caution_event_id")
    prior_source = payload.get("prior_caution_event_id")
    prior_effect = consequence.get("prior_caution_event_id")
    return bool(
        # A persisted marker is physical evidence only for its own signed
        # protection day. Never coerce booleans, strings or missing dates.
        type(marker_day) is int and marker_day > 0
        and type(source_day) is int and type(effect_day) is int
        and marker_day == source_day == effect_day
        and (
            (prior_marker is None and prior_source is None and prior_effect is None)
            or (type(prior_marker) is int and prior_marker > 0
                and prior_marker == prior_source == prior_effect)
        )
        and ident(cord_id)
        and event.get("kind") == "village.route_protected"
        and event.get("status") == "complete"
        # Two absent or malformed values must not authenticate each other.
        # A completed source must identify its own event and actor first.
        and ident(event.get("id")) is not None
        and ident(actor.get("account_id")) is not None
        and ident(actor.get("mask_id")) is not None
        and isinstance(actor.get("mask"), str)
        and bool(actor["mask"].strip())
        and ident(event.get("id")) == ident(marker.get("event_id"))
        and ident(actor.get("account_id")) == ident(marker.get("account_id"))
        and actor.get("mask") == marker.get("mask")
        and payload.get("site") == "red_cord"
        and payload.get("role") == "hound"
        and payload.get("action") == "protect"
        and payload.get("location") == TREELINE
        and stamp(payload.get("day"), payload.get("hour")) is not None
        and ident(consequence.get("cord_object_id")) == ident(cord_id)
        and consequence.get("caution_marked") is True)


def can_dispatch(last, protection, marker, *, cord_id, day, hour,
                 hound_account_id, hound_mask_id):
    now = stamp(day, hour)
    if now is None or not ident(hound_account_id) or not ident(hound_mask_id):
        return False, "A valid village time and Hound identity are required."
    if not protection_valid(protection, marker, cord_id):
        return False, "The original cord has no completed signed Hound warning."
    source = mapping(protection.get("payload"))
    if source.get("day") != day:
        return False, "A fresh signed Hound warning is required today."
    if stamp(source.get("day"), source.get("hour")) > now:
        return False, "The source warning lies in the future."
    if last is not None:
        # A stored last-dispatch consequence is not authenticated by its
        # day alone. Corrupted or partial event, actor and item IDs must
        # block a new dispatch instead of silently clearing the prior work.
        if (not hasattr(last, "get")
                or type(last.get("day")) is not int
                or last["day"] < 1
                or any(ident(last.get(key)) is None for key in (
                    "event_id", "account_id", "item_id"))):
            return False, "The cord's dispatch record is malformed."
        if last["day"] >= int(day):
            return False, "A refuge dispatch already left this cord today."
    return True, None



def dispatch_source_marker(current, history, protection, current_protection, cord_id):
    """Resolve a carried dispatch's signed marker without requiring it to stay current.

    A legitimate next-day re-tying archives the previous physical marker.
    The signed historical event, immediate replacement chain and original
    cord must all agree. Unverifiable archives fail closed.
    """
    source_id = ident(mapping(protection).get("id"))
    current = mapping(current)
    if source_id is None:
        return None
    if ident(current.get("event_id")) == source_id:
        return current if protection_valid(protection, current, cord_id) else None
    if not protection_valid(current_protection, current, cord_id):
        return None
    if (not isinstance(history, (list, tuple))
            and not (hasattr(history, "__iter__") and hasattr(history, "__len__")
                     and not isinstance(history, (str, bytes, dict)))):
        return None
    try:
        previous = history[-1]
    except (IndexError, KeyError, TypeError, ValueError):
        return None
    previous = mapping(previous)
    if (ident(previous.get("event_id")) != source_id
            or type(previous.get("day")) is not int
            or type(current.get("day")) is not int
            or current["day"] <= previous["day"]
            or ident(current.get("prior_caution_event_id")) != source_id):
        return None
    return previous if protection_valid(protection, previous, cord_id) else None


def dispatch_valid(event, token, protection, marker, cord_id, item_id):
    event, token = mapping(event), mapping(token)
    actor, payload, consequence = (
        mapping(event.get("actor")), mapping(event.get("payload")),
        mapping(event.get("consequence")))
    if not protection_valid(protection, marker, cord_id):
        return False
    if not all(ident(x) for x in (
        item_id, token.get("dispatch_event_id"), token.get("hound_account_id"),
        token.get("hound_mask_id"), token.get("cord_id"))):
        return False
    if not (
        event.get("kind") == "professional.hound_refuge_dispatch"
        and event.get("status") == "complete"
        and ident(event.get("id")) == ident(token.get("dispatch_event_id"))
        and ident(actor.get("account_id")) == ident(token.get("hound_account_id"))
        and ident(actor.get("mask_id")) == ident(token.get("hound_mask_id"))
        and payload.get("professional_calling") == "hound"
        and payload.get("location") == TREELINE
        and ident(payload.get("cord_id")) == ident(cord_id)
        and ident(token.get("cord_id")) == ident(cord_id)
        and ident(payload.get("source_protect_event_id"))
            == ident(token.get("source_protect_event_id"))
            == ident(mapping(protection).get("id"))
        and ident(consequence.get("item_id")) == ident(item_id)
        # A completed dispatch must sign the same physical cord in its
        # outcome, not only in its requested payload and carried token.
        and ident(consequence.get("cord_id")) == ident(cord_id)
        and ident(consequence.get("source_protect_event_id"))
            == ident(mapping(protection).get("id"))
        # The dispatch itself must be issued on the signed marker day.
        # A later Tavern meal may still be served within its 24-hour window.
        and payload.get("day") == mapping(protection.get("payload")).get("day")
        and stamp(payload.get("day"), payload.get("hour"))
            == stamp(token.get("day"), token.get("hour"))):
        return False
    first = mapping(protection.get("payload"))
    source_time = stamp(first.get("day"), first.get("hour"))
    dispatch_time = stamp(token.get("day"), token.get("hour"))
    return source_time is not None and dispatch_time is not None and source_time <= dispatch_time


def history(raw):
    if raw is None:
        return []
    if not hasattr(raw, "get"):
        return None
    rows = raw.get("history")
    if rows is None:
        return []
    # Evennia persists nested lists as saver-backed mutable sequences, not
    # necessarily built-in list/tuple instances. Materialize read-only first.
    if isinstance(rows, (str, bytes)) or not hasattr(rows, "__iter__"):
        return None
    try:
        entries = list(rows)[-MAX_RECEIPTS:]
    except (TypeError, ValueError):
        return None
    result = []
    for row in entries:
        if not hasattr(row, "get") or not all(ident(row.get(key)) for key in (
            "event_id", "dispatch_event_id", "hound_account_id",
            "innkeep_account_id", "item_id")):
            return None
        result.append(dict(row))
    return result


def accept(raw, pantry_raw, *, day, hour, innkeep_account_id,
           innkeep_mask_id, hound_account_id, hound_mask_id,
           token, token_id, dispatch_event, protection, marker,
           cord_id, tavern_id, event_id):
    """Return (new Tavern receipt, new pantry, allowed, error) without mutation."""
    receipts = history(raw)
    original = soup_state.pantry(pantry_raw, max(1, ident(day) or 1))
    if receipts is None:
        return None, original, False, "The Tavern refuge register is malformed."
    if not all(ident(value) for value in (
        innkeep_account_id, innkeep_mask_id, hound_account_id,
        hound_mask_id, token_id, tavern_id, event_id)):
        return None, original, False, "Independent signed player identities are required."
    if int(innkeep_account_id) == int(hound_account_id):
        return None, original, False, "One account cannot serve as both Hound and Innkeep."
    if not dispatch_valid(dispatch_event, token, protection, marker, cord_id, token_id):
        return None, original, False, "The physical dispatch has no valid completed source."
    if (ident(token.get("hound_account_id")) != ident(hound_account_id)
            or ident(token.get("hound_mask_id")) != ident(hound_mask_id)):
        return None, original, False, "The source Hound must arrive with the dispatch."
    now, sent = stamp(day, hour), stamp(token.get("day"), token.get("hour"))
    if now is None or sent is None or not 0 <= now - sent <= 24:
        return None, original, False, "The arrival is late or the village clock rewound."
    if any(ident(row["dispatch_event_id"]) == ident(token["dispatch_event_id"])
           or ident(row["item_id"]) == ident(token_id) for row in receipts):
        return None, original, False, "This dispatch has already been served."
    food, allowed, why = soup_state.reserve(pantry_raw, day, "turnip", "salt")
    if not allowed:
        return None, original, False, why
    receipts.append({
        "event_id": int(event_id),
        "dispatch_event_id": int(token["dispatch_event_id"]),
        "source_protect_event_id": int(token["source_protect_event_id"]),
        "hound_account_id": int(hound_account_id),
        "hound_mask_id": int(hound_mask_id),
        "innkeep_account_id": int(innkeep_account_id),
        "innkeep_mask_id": int(innkeep_mask_id),
        "item_id": int(token_id), "tavern_id": int(tavern_id),
        "day": int(day), "hour": int(hour), "bowl_id": None,
    })
    return {"history": receipts[-MAX_RECEIPTS:]}, food, True, None


def signed_receipt(row, event_lookup):
    """Verify persisted refuge readback against three completed canonical events.

    A shape-valid Tavern attribute is not a signed world event. The original
    physical dispatch may already have been consumed and its cord re-tied, so
    verify the immutable event chain rather than requiring today's cord marker.
    """
    if not hasattr(row, "get") or not callable(event_lookup):
        return False
    try:
        meal = mapping(event_lookup(row.get("event_id")))
        dispatch = mapping(event_lookup(row.get("dispatch_event_id")))
        source = mapping(event_lookup(row.get("source_protect_event_id")))
    except (KeyError, TypeError, ValueError, AttributeError):
        return False
    meal_actor, meal_payload, meal_result = (
        mapping(meal.get("actor")), mapping(meal.get("payload")),
        mapping(meal.get("consequence")))
    dispatch_actor, dispatch_payload, dispatch_result = (
        mapping(dispatch.get("actor")), mapping(dispatch.get("payload")),
        mapping(dispatch.get("consequence")))
    source_actor, source_payload, source_result = (
        mapping(source.get("actor")), mapping(source.get("payload")),
        mapping(source.get("consequence")))
    cord_id = ident(source_result.get("cord_object_id"))
    source_time = stamp(source_payload.get("day"), source_payload.get("hour"))
    sent_time = stamp(dispatch_payload.get("day"), dispatch_payload.get("hour"))
    served_time = stamp(meal_payload.get("day"), meal_payload.get("hour"))
    if (not cord_id or source_time is None or sent_time is None
            or served_time is None or not source_time <= sent_time <= served_time
            or served_time - sent_time > 24):
        return False
    # Every persisted identity and physical object must be present, positive,
    # and tied to its corresponding event. Paired absent IDs are not evidence.
    ids = (
        ("event_id", meal.get("id")),
        ("dispatch_event_id", dispatch.get("id")),
        ("source_protect_event_id", source.get("id")),
        ("hound_account_id", dispatch_actor.get("account_id")),
        ("hound_mask_id", dispatch_actor.get("mask_id")),
        ("innkeep_account_id", meal_actor.get("account_id")),
        ("innkeep_mask_id", meal_actor.get("mask_id")),
        ("item_id", dispatch_result.get("item_id")),
        ("tavern_id", meal_payload.get("tavern_id")),
        ("bowl_id", meal_result.get("bowl_id")),
    )
    if any(ident(row.get(key)) is None or ident(row.get(key)) != ident(value)
           for key, value in ids):
        return False
    if ident(row.get("hound_account_id")) == ident(row.get("innkeep_account_id")):
        return False
    return bool(
        meal.get("kind") == "professional.innkeep_refuge_meal"
        and meal.get("status") == "complete"
        and dispatch.get("kind") == "professional.hound_refuge_dispatch"
        and dispatch.get("status") == "complete"
        and source.get("kind") == "village.route_protected"
        and source.get("status") == "complete"
        and ident(source_actor.get("account_id"))
        and ident(source_actor.get("mask_id"))
        and source_payload.get("site") == "red_cord"
        and source_payload.get("role") == "hound"
        and source_payload.get("action") == "protect"
        and source_payload.get("location") == TREELINE
        and source_result.get("caution_marked") is True
        and dispatch_payload.get("professional_calling") == "hound"
        and dispatch_payload.get("location") == TREELINE
        and ident(dispatch_payload.get("cord_id")) == cord_id
        and ident(dispatch_result.get("cord_id")) == cord_id
        and ident(dispatch_payload.get("source_protect_event_id"))
            == ident(source.get("id"))
        and ident(dispatch_result.get("source_protect_event_id"))
            == ident(source.get("id"))
        and dispatch_payload.get("day") == source_payload.get("day")
        and meal_payload.get("professional_calling") == "innkeep"
        and ident(meal_payload.get("hound_account_id"))
            == ident(row.get("hound_account_id"))
        and ident(meal_payload.get("hound_mask_id"))
            == ident(row.get("hound_mask_id"))
        and ident(meal_payload.get("dispatch_item_id"))
            == ident(row.get("item_id"))
        and ident(meal_payload.get("dispatch_event_id"))
            == ident(dispatch.get("id"))
        and ident(meal_result.get("consumed_dispatch_id"))
            == ident(row.get("item_id"))
        and ident(meal_result.get("dispatch_event_id"))
            == ident(dispatch.get("id"))
        and ident(meal_result.get("source_protect_event_id"))
            == ident(source.get("id"))
        and ident(meal_result.get("tavern_id"))
            == ident(row.get("tavern_id"))
        and type(row.get("day")) is int
        and type(row.get("hour")) is int
        and row["day"] == meal_payload.get("day")
        and row["hour"] == meal_payload.get("hour")
        and served_time == stamp(row["day"], row["hour"])
    )


def public_lines(raw, event_lookup=None):
    """Only call an arrival signed after canonical ledger verification."""
    receipts = history(raw)
    if receipts is None:
        return "The refuge register requires inspection."
    if not receipts:
        return "No witnessed Hound refuge meals have been served."
    if event_lookup is None:
        try:
            from world.events import get_event_ledger
            event_lookup = get_event_ledger().get_event
        except Exception:
            return "The refuge register requires signed source inspection."
    if not all(signed_receipt(row, event_lookup) for row in receipts):
        return "The refuge register requires signed source inspection."
    return (
        f"{len(receipts)} signed Hound arrival meal(s) in the Tavern refuge "
        f"register; latest event {receipts[-1]['event_id']}. "
        "This proves a real traveler arrived, not an unseen rescue.")
