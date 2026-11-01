"""Shared soup kitchen at the Blood of the Vine with genuine ingredient custody.

Tavern/Market own stock, player inventories own prepared packets and finished
edible bowls. Ordinary Evennia verbs handle transfer and eating. No timers,
special AI capabilities, home ownership or free-score cooking shortcuts.
"""
from __future__ import annotations

import copy

from evennia import create_object
from evennia.scripts.models import ScriptDB
from evennia.utils import search

from world import soup_state, hearth_state
from world.callings import active_calling, record_participation
from world.events import publish_world_event

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
    from world import kitchen_repair_work
    return (
        "A large, shared iron soup pot sits beside the Blood of the Vine's "
        "working kitchen fire. Bram's ordinary pantry renews each village day "
        "whether or not players are present; it is not anyone's private business. "
        f"Pantry day {state['day']}: {listed}. "
        f"The main hearth is {'warm' if fire else 'low'}."
        + last + " " + kitchen_repair_work.status() +
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
    from world import kitchen_repair_edge02, kitchen_repair_work
    pot = kitchen_repair_work._pot()
    if not kitchen_repair_work.player_simmer_allowed(pot):
        return None, "Player simmering is restricted until the real kitchen pot is repaired."
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
        # Recheck signed pot service when the world event is actually applied.
        # A rollback between command preflight and consequence cannot cook.
        if (mask.location != tavern
                or active_calling(mask) != "innkeep"
                or kitchen_repair_work._pot() != pot
                or not kitchen_repair_work.player_simmer_allowed(pot)):
            raise RuntimeError("The physical kitchen pot is not cleared for player simmering.")
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
