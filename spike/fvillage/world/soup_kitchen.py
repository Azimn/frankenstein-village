"""Shared soup kitchen at the Blood of the Vine with genuine ingredient custody.

Tavern/Market own stock, player inventories own prepared packets and finished
edible bowls. Ordinary Evennia verbs handle transfer and eating. No timers,
special AI capabilities, home ownership or free-score cooking shortcuts.
"""
from __future__ import annotations

import copy

from django.db import transaction

from evennia import create_object
from evennia.scripts.models import ScriptDB
from evennia.utils import search

from world import soup_state, hearth_state, arrival_hospitality, route_surveys
from world.callings import active_calling, record_participation
from world.events import get_event_ledger, publish_world_event

TAVERN = "The Blood of the Vine"
MARKET = "Market Lane"
PACKET = "a packet of soup ingredients"
CRATE = "a crate of kitchen roots"


def _room(name):
    return next((o for o in search.search_object(name)
                 if o.key == name and o.location is None), None)


def _clock():
    try:
        script = ScriptDB.objects.get(db_key="village_time")
        return int(script.db.day or 1), int(
            script.db.hour if script.db.hour is not None else 21)
    except ScriptDB.DoesNotExist:
        return 1, 21


def _access(mask, name):
    room = _room(name)
    if (not getattr(mask, "account", None) or room is None
            or mask.location != room
            or not room.tags.has("ic", category="side")):
        return None, (
            f"An in-character player must be physically at {name} to do that."
        )
    return room, None


def _held(mask, attr):
    return [obj for obj in mask.contents if getattr(obj.db, attr, None)]


def pot_description():
    tavern = _room(TAVERN)
    if not tavern:
        return "The kitchen is not yet available."
    day, hour = _clock()
    state = soup_state.pantry(tavern.db.soup_pantry, day)
    fire = hearth_state.active(tavern.db.civic_hearth, day, hour)
    listed = ", ".join(f"{k} {v}" for k, v in state["stock"].items())
    done = state["history"][-1] if state["history"] else None
    last = (
        f" Last completed batch: {done['maker']}'s "
        f"{done['base']}-{done['seasoning']} soup, "
        f"quality {done['quality']} (world event {done['cook_event_id']})."
        if done else " No player-made batch has been recorded."
    )
    return (
        "A large, shared iron soup pot sits beside the Blood of the Vine's "
        "working kitchen fire. Bram's ordinary pantry renews each village day "
        "whether or not players are present; it is not anyone's private business. "
        f"Pantry day {state['day']}: {listed}. "
        f"The main hearth is {'warm' if fire else 'low'}."
        + last +
        (" Signed returning-traveler hospitality: world event %s, route event %s." % (done["arrival_welcome"]["event_id"], done["arrival_welcome"]["route_event_id"]) if done and done.get("arrival_welcome") else "") +
        " Use soup prep <turnip|barley> <thyme|salt|pepper>, soup simmer, "
        "soup notebook, or coordinate a Merchant delivery."
    )


def status(mask):
    if mask is None or not getattr(mask, "location", None):
        return "Visit the Blood of the Vine to work in its shared kitchen."
    if mask.location.key != TAVERN:
        return "The shared soup kitchen is at the Blood of the Vine."
    return pot_description()


def recipe_notes(mask):
    entries = list(getattr(mask.db, "soup_notebook", None) or [])
    if not entries:
        return (
            "Your soup notebook is blank. Try soup prep turnip thyme, "
            "followed by soup simmer at the Tavern."
        )
    lines = ["|wYour signed soup notebook|n"]
    for row in entries[-10:]:
        lines.append(
            f"* Day {row['day']}: {row['base']} with {row['seasoning']}, "
            f"quality {row['quality']}; event {row['cook_event_id']}."
        )
    return "\n".join(lines)


def prep(mask, base, seasoning):
    tavern, err = _access(mask, TAVERN)
    if err:
        return None, err
    if active_calling(mask) != "innkeep":
        return None, "An active Innkeep is needed to prepare a recipe."
    if _held(mask, "soup_preparation"):
        return None, "You already carry a prepared packet; cook or hand it off first."
    day, hour = _clock()
    prepared, ok, why = soup_state.reserve(
        tavern.db.soup_pantry, day, base, seasoning)
    if not ok:
        return None, why

    def consequence(event):
        # Both reservation and exact physical custody live in this event.
        if _held(mask, "soup_preparation"):
            raise RuntimeError("A prepared packet was added during work.")
        item = create_object(
            "typeclasses.objects.Object", key=PACKET,
            location=mask, aliases=["soup packet", "ingredients"],
        )
        item.db.soup_preparation = {
            "base": base, "seasoning": seasoning,
            "day": day, "hour": hour,
            "prep_event_id": event["id"], "preparer_id": mask.id,
            "preparer": mask.key, "source_room_id": tavern.id,
        }
        item.db.desc = (
            f"A packet of real measured {base} and {seasoning} from the "
            "shared tavern cupboard. Give it to another Innkeep, or "
            "bring it back to the communal pot and use soup simmer."
        )
        tavern.db.soup_pantry = prepared
        return {"packet_id": item.id, "room_id": tavern.id,
                "stock_after": copy.deepcopy(prepared["stock"])}

    event = publish_world_event(
        "professional.innkeep_soup_prepared", actor=mask,
        payload={"day": day, "hour": hour, "base": base,
                 "seasoning": seasoning, "room_id": tavern.id,
                 "chronicle_eligible": False, "harbinger": False},
        consequence=consequence)
    record_participation(mask, "soup_preparations", calling="innkeep")
    return {"event_id": event["id"], "base": base,
            "seasoning": seasoning,
            "stock": prepared["stock"]}, None


def simmer(mask):
    tavern, err = _access(mask, TAVERN)
    if err:
        return None, err
    if active_calling(mask) != "innkeep":
        return None, "An active Innkeep is needed to simmer a batch."
    packets = _held(mask, "soup_preparation")
    if not packets:
        return None, "Carry one real prepared packet; use soup prep first."
    if len(packets) > 1:
        return None, "Carry only one prepared packet when simmering."
    packet = packets[0]
    record = dict(packet.db.soup_preparation)
    day, hour = _clock()
    if day < int(record["day"]):
        return None, "The kitchen clock has moved behind this preparation."
    if day > int(record["day"]) + 2:
        return None, "These old ingredients have spoiled. Discard the packet."
    warm = hearth_state.active(tavern.db.civic_hearth, day, hour)
    recipe = soup_state.produce(
        record["base"], record["seasoning"], warmed=warm)
    if not recipe:
        return None, "The packet has an invalid recipe."
    if len([o for o in mask.contents if getattr(o.db, "soup_serving", None)]) >= 3:
        return None, "You already carry three soup bowls; serve or eat them first."

    def consequence(event):
        if packet.location != mask or not packet.db.soup_preparation:
            raise RuntimeError("The reserved ingredients were moved or consumed.")
        bowl = create_object(
            "typeclasses.objects.Object",
            key=f"a bowl of {record['base']} and {record['seasoning']} soup",
            location=mask,
            aliases=["homemade soup", "soup bowl", "soup"],
        )
        bowl.tags.add("consumable")
        bowl.tags.add("food")
        bowl.db.consume = {
            "nourish": recipe["nourish"], "servings_max": 1,
            "short": "homemade soup",
            "flavor": (
                f"You taste {recipe['flavor']}. "
                "It is a recipe someone here really cooked."
            ),
            "room": f"{mask.key} tastes freshly cooked soup.",
        }
        bowl.db.servings = 1
        bowl.db.soup_serving = {
            **recipe, "event_id": event["id"],
            "prep_event_id": record["prep_event_id"],
            "maker_id": mask.id, "maker": mask.key,
        }
        bowl.db.desc = (
            f"Fresh {record['base']} soup with {record['seasoning']}. "
            f"Cooking quality {recipe['quality']}; "
            f"prepared on village day {record['day']}. "
            "A single real serving, transferable to another player."
        )
        tavern.db.soup_pantry = soup_state.archive(
            tavern.db.soup_pantry, day, maker_id=mask.id,
            maker=mask.key, source_event_id=record["prep_event_id"],
            cook_event_id=event["id"], recipe=recipe)
        packet.delete()
        return {"bowl_id": bowl.id, "pantry_room_id": tavern.id,
                "quality": recipe["quality"],
                "source_event_id": record["prep_event_id"]}

    event = publish_world_event(
        "professional.innkeep_soup_cooked", actor=mask,
        payload={"day": day, "hour": hour,
                 "base": record["base"], "seasoning": record["seasoning"],
                 "packet_id": packet.id, "prep_event_id": record["prep_event_id"],
                 "chronicle_eligible": False, "harbinger": False},
        consequence=consequence)
    row = {
        "day": day, "base": record["base"], "seasoning": record["seasoning"],
        "quality": recipe["quality"], "warmed": warm,
        "cook_event_id": event["id"],
    }
    mask.db.soup_notebook = soup_state.notebook(mask.db.soup_notebook, row)
    record_participation(mask, "soup_batches_cooked", calling="innkeep")
    return {"event_id": event["id"], **recipe}, None



def welcome(mask, guest_name):
    """Give one genuinely cooked bowl to a separately signed returning Wanderer.

    The source is the original daily Square route record and completed world
    event, not a story about a traveler. The Tavern's existing cooked-batch
    history is the only hospitality receipt store.
    """
    tavern, error = _access(mask, TAVERN)
    if error:
        return None, error
    if active_calling(mask) != "innkeep":
        return None, "An active Innkeep must offer a real cooked serving."
    guests = [
        obj for obj in tavern.contents
        if obj is not mask and obj.key.casefold() == guest_name.casefold()
        and getattr(obj, "account", None) is not None
    ]
    if len(guests) != 1:
        return None, "The named guest must be physically present in the Tavern."
    guest = guests[0]
    if guest.account.id == mask.account.id:
        return None, "Hospitality requires a different player's account."
    if active_calling(guest) != "wanderer":
        return None, "This arrival service requires an active Wanderer."
    bowls = [
        obj for obj in _held(mask, "soup_serving")
        if int(getattr(obj.db, "servings", 0) or 0) == 1
    ]
    if not bowls:
        return None, "Cook and carry a real uneaten soup bowl before welcoming a traveler."
    bowl = bowls[0]
    serving = dict(bowl.db.soup_serving or {})
    if serving.get("maker_id") != mask.id:
        return None, "The Innkeep must offer a bowl they actually cooked."
    if not bowl.tags.has("food") or not bowl.tags.has("consumable"):
        return None, "The offered object is not an edible soup serving."
    square = _room("Village Square")
    if square is None:
        return None, "The original public route record is missing."
    day, hour = _clock()
    route_state = route_surveys.refresh(square.db.daily_route_survey, day)
    if route_state["day"] != day:
        return None, "The route record is dated later than the arrival."
    entry = dict(route_state["field_decisions"].get("wanderer") or {})
    route_id = entry.get("event_id")
    ledger = get_event_ledger()
    route_event = ledger.get_event(route_id) if type(route_id) is int else None
    cook_id = serving.get("event_id")
    bowl_event = ledger.get_event(cook_id) if type(cook_id) is int else None
    if (not bowl_event or not hasattr(bowl_event.get("consequence"), "get")
            or not hasattr(bowl_event.get("payload"), "get")
            or bowl_event["consequence"].get("bowl_id") != bowl.id
            or serving.get("prep_event_id")
            != bowl_event["payload"].get("prep_event_id")):
        return None, "The physical bowl has no matching signed cooking source."
    kwargs = {
        "day": day, "hour": hour,
        "innkeep_account_id": mask.account.id, "innkeep_mask_id": mask.id,
        "wanderer_account_id": guest.account.id, "wanderer_mask_id": guest.id,
        "wanderer_mask": guest.key, "route_entry": entry,
        "route_event": route_event, "bowl_event": bowl_event,
        "bowl_id": bowl.id, "square_room_id": square.id,
        "tavern_room_id": tavern.id,
    }
    _preview, okay, reason = arrival_hospitality.welcome(
        tavern.db.soup_pantry, event_id=1, **kwargs,
    )
    if not okay:
        return None, reason

    def consequence(event):
        with transaction.atomic():
            if (_clock() != (day, hour) or mask.location != tavern
                    or guest.location != tavern or bowl.location != mask
                    or not mask.account or not guest.account
                    or mask.account.id == guest.account.id
                    or active_calling(mask) != "innkeep"
                    or active_calling(guest) != "wanderer"
                    or int(bowl.db.servings or 0) != 1
                    or dict(bowl.db.soup_serving or {}) != serving
                    or not bowl.tags.has("food")
                    or not bowl.tags.has("consumable")):
                raise RuntimeError("The physical guest, serving or village time changed.")
            try:
                if not guest.account.sessions.all():
                    raise RuntimeError("The returning Wanderer disconnected.")
            except (AttributeError, TypeError):
                raise RuntimeError("The returning Wanderer disconnected.")
            fresh_route = route_surveys.refresh(square.db.daily_route_survey, day)
            if fresh_route["day"] != day:
                raise RuntimeError("The route record changed before the welcome.")
            current_entry = dict(fresh_route["field_decisions"].get("wanderer") or {})
            current_route = ledger.get_event(current_entry.get("event_id"))
            current_bowl = ledger.get_event(serving.get("event_id"))
            changed, accepted, why = arrival_hospitality.welcome(
                tavern.db.soup_pantry, event_id=event["id"],
                **{**kwargs, "route_entry": current_entry,
                   "route_event": current_route, "bowl_event": current_bowl},
            )
            if not accepted:
                raise RuntimeError(why)
            if not bowl.move_to(guest, quiet=True):
                raise RuntimeError("The real soup bowl could not be handed over.")
            tavern.db.soup_pantry = changed
            return {
                "tavern_room_id": tavern.id, "bowl_id": bowl.id,
                "route_event_id": current_entry["event_id"],
                "cook_event_id": serving["event_id"],
                "wanderer_account_id": guest.account.id,
                "innkeep_account_id": mask.account.id,
                "service": "physical_bowl_transferred",
            }

    event = publish_world_event(
        "professional.innkeep_wanderer_arrival_welcome", actor=mask,
        payload={
            "day": day, "hour": hour, "tavern_room_id": tavern.id,
            "guest_mask_id": guest.id, "guest_account_id": guest.account.id,
            "route_event_id": route_id, "cook_event_id": cook_id,
            "bowl_id": bowl.id, "harbinger": False,
            "chronicle_eligible": False,
        },
        consequence=consequence,
    )
    record_participation(mask, "arrival_hospitality", calling="innkeep")
    return {
        "event_id": event["id"], "guest": guest.key,
        "route_event_id": route_id, "bowl_id": bowl.id,
    }, None


def procure(mask):
    market, err = _access(mask, MARKET)
    if err:
        return None, err
    if active_calling(mask) != "merchant":
        return None, "An active Merchant must procure the kitchen root crate."
    if _held(mask, "soup_delivery"):
        return None, "You already carry a kitchen delivery; take it to the Tavern."
    day, hour = _clock()
    next_stock, okay = soup_state.issue_crate(market.db.soup_market, day)
    if not okay:
        return None, "The market has no more kitchen root crates available today."

    def consequence(event):
        crate = create_object(
            "typeclasses.objects.Object", key=CRATE,
            location=mask, aliases=["kitchen roots", "root crate"],
        )
        crate.db.soup_delivery = {
            "day": day, "market_id": market.id,
            "procurement_event_id": event["id"],
            "merchant_id": mask.id,
        }
        crate.db.desc = (
            "A real crate with two turnip portions for the Blood of the Vine. "
            "Carry it there and use soup deliver, or hand it to a courier."
        )
        market.db.soup_market = next_stock
        return {"crate_id": crate.id,
                "remaining_crates": next_stock["remaining"]}

    event = publish_world_event(
        "professional.merchant_kitchen_procurement", actor=mask,
        payload={"day": day, "hour": hour, "market_room_id": market.id,
                 "chronicle_eligible": False, "harbinger": False},
        consequence=consequence)
    record_participation(mask, "kitchen_procurements", calling="merchant")
    return {"event_id": event["id"],
            "remaining": next_stock["remaining"]}, None


def deliver(mask):
    tavern, err = _access(mask, TAVERN)
    if err:
        return None, err
    crates = _held(mask, "soup_delivery")
    if not crates:
        return None, "Bring a physical kitchen root crate from Market Lane."
    crate = crates[0]
    day, hour = _clock()
    result, okay = soup_state.deliver(tavern.db.soup_pantry, day)
    if not okay:
        return None, "The pantry already has enough turnips for now."
    source = dict(crate.db.soup_delivery or {})
    if day < int(source.get("day") or 0):
        return None, "The crate's procurement lies in the future."

    def consequence(event):
        if crate.location != mask or not crate.db.soup_delivery:
            raise RuntimeError("The delivery crate was moved or consumed.")
        tavern.db.soup_pantry = result
        crate.delete()
        return {"turnip_stock": result["stock"]["turnip"],
                "procurement_event_id": source.get("procurement_event_id")}

    event = publish_world_event(
        "village.kitchen_delivery", actor=mask,
        payload={"day": day, "hour": hour,
                 "crate_id": crate.id,
                 "procurement_event_id": source.get("procurement_event_id"),
                 "chronicle_eligible": False, "harbinger": False},
        consequence=consequence)
    return {"event_id": event["id"],
            "turnips": result["stock"]["turnip"]}, None
