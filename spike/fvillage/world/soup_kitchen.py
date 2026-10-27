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

from world import soup_state, hearth_state
from world.callings import active_calling, record_participation
from world.events import publish_world_event

TAVERN = "The Blood of the Vine"
MARKET = "Market Lane"
PACKET = "a packet of soup ingredients"
CRATE = "a crate of kitchen roots"
RATION = "a bowl of plain kitchen broth"
# A visitor can prepare a modest, finite meal without taking the Innkeep's
# professional cooking, quality choices, notebook or participation credit.
RATION_PAIRS = (
    ("barley", "salt"), ("turnip", "salt"),
    ("barley", "thyme"), ("turnip", "thyme"),
    ("barley", "pepper"), ("turnip", "pepper"),
)


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


def _ration_pair(raw, day):
    """Pick from real available pantry ingredients without modifying stock."""
    for base, seasoning in RATION_PAIRS:
        _preview, available, _reason = soup_state.reserve(
            raw, day, base, seasoning)
        if available:
            return base, seasoning
    return None


def can_make_ration():
    """Read-only, public kitchen availability for co-located body guidance."""
    tavern = _room(TAVERN)
    if tavern is None:
        return False
    day, _hour = _clock()
    return _ration_pair(tavern.db.soup_pantry, day) is not None


def _full_bowls(mask):
    """Spent bowls do not count against the small physical carry limit."""
    return sum(
        1 for obj in mask.contents
        if (getattr(obj.db, "kitchen_ration", None)
            or getattr(obj.db, "soup_serving", None))
        and int(getattr(obj.db, "servings", 0) or 0) > 0
    )


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
        " Any visitor may cook soup ration from genuinely remaining pantry "
        "ingredients; Innkeeps can use soup prep and soup simmer for "
        "professional recipes. Also try soup notebook or coordinate "
        "a Merchant delivery."
    )


def status(mask):
    if mask is None or not getattr(mask, "location", None):
        return "Visit the Blood of the Vine to work in its shared kitchen."
    if mask.location.key != TAVERN:
        return "The shared soup kitchen is at the Blood of the Vine."
    return pot_description()


def ration(mask):
    """Any player can make ONE plain physical meal from finite pantry stock.

    It is a modest unskilled alternative, not an Innkeep recipe, free meal
    from nowhere, or an additional world stock ledger.
    """
    tavern, err = _access(mask, TAVERN)
    if err:
        return None, err
    if _full_bowls(mask) >= 3:
        return None, "Serve or eat a carried soup bowl before taking more."
    day, hour = _clock()
    if _ration_pair(tavern.db.soup_pantry, day) is None:
        return None, (
            "The shared pantry has no complete broth ingredients right now. "
            "The finite pantry renews next village day; carry or eat other "
            "real food if you have it."
        )

    def consequence(event):
        with transaction.atomic():
            live_room, reason = _access(mask, TAVERN)
            if reason:
                raise RuntimeError(reason)
            if live_room != tavern:
                raise RuntimeError("The kitchen changed during preparation.")
            if _clock()[0] != day:
                raise RuntimeError("The village day changed before the broth was made.")
            if _full_bowls(mask) >= 3:
                raise RuntimeError("Serve or eat a carried soup bowl before taking more.")
            pair = _ration_pair(tavern.db.soup_pantry, day)
            if pair is None:
                raise RuntimeError(
                    "The shared pantry is out of broth ingredients. "
                    "No bowl was made and no stock was spent."
                )
            base, seasoning = pair
            updated, accepted, reason = soup_state.reserve(
                tavern.db.soup_pantry, day, base, seasoning)
            if not accepted:
                raise RuntimeError(reason)
            recipe = soup_state.produce(base, seasoning, warmed=False)
            bowl = create_object(
                "typeclasses.objects.Object",
                key=RATION, location=mask,
                aliases=["plain broth", "kitchen broth", "broth"],
            )
            bowl.tags.add("consumable")
            bowl.tags.add("food")
            bowl.db.consume = {
                "nourish": recipe["nourish"], "servings_max": 1,
                "short": "plain kitchen broth",
                "flavor": (
                    "You eat the plain broth you made from the communal "
                    "pantry. It settles a little of your hunger."
                ),
                "room": f"{mask.key} eats plain broth from the village pot.",
            }
            bowl.db.servings = 1
            bowl.db.kitchen_ration = {
                "day": day, "hour": hour, "cook_event_id": event["id"],
                "maker_id": mask.id, "source_room_id": tavern.id,
                "base": base, "seasoning": seasoning,
            }
            bowl.db.desc = (
                f"A single transferable bowl of plain {base} and {seasoning} "
                "broth. It came from real shared kitchen ingredients, "
                f"signed as event {event['id']}. Eat plain broth to use it."
            )
            tavern.db.soup_pantry = updated
            return {
                "bowl_id": bowl.id, "base": base, "seasoning": seasoning,
                "nourish": recipe["nourish"],
                "stock_after": copy.deepcopy(updated["stock"]),
                "tavern_room_id": tavern.id,
            }

    try:
        event = publish_world_event(
            "village.kitchen_plain_ration", actor=mask,
            payload={
                "day": day, "hour": hour, "tavern_room_id": tavern.id,
                "chronicle_eligible": False, "harbinger": False,
            },
            consequence=consequence,
        )
    except RuntimeError as error:
        return None, str(error)
    return {"event_id": event["id"], **event["consequence"]}, None


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
    _preview, ok, why = soup_state.reserve(
        tavern.db.soup_pantry, day, base, seasoning)
    if not ok:
        return None, why

    def consequence(event):
        # A preflight is not a stock reservation. Recheck live inventory,
        # village time and the shared pantry inside the signed consequence.
        with transaction.atomic():
            _room_now, reason = _access(mask, TAVERN)
            if reason:
                raise RuntimeError(reason)
            if _room_now != tavern:
                raise RuntimeError("The kitchen changed during preparation.")
            if active_calling(mask) != "innkeep":
                raise RuntimeError("An active Innkeep is needed to prepare a recipe.")
            if _clock()[0] != day:
                raise RuntimeError("The village day changed during preparation.")
            if _held(mask, "soup_preparation"):
                raise RuntimeError("You already carry a prepared packet.")
            updated, accepted, reason = soup_state.reserve(
                tavern.db.soup_pantry, day, base, seasoning)
            if not accepted:
                raise RuntimeError(reason)
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
            tavern.db.soup_pantry = updated
            return {"packet_id": item.id, "room_id": tavern.id,
                    "stock_after": copy.deepcopy(updated["stock"])}

    try:
        event = publish_world_event(
            "professional.innkeep_soup_prepared", actor=mask,
            payload={"day": day, "hour": hour, "base": base,
                     "seasoning": seasoning, "room_id": tavern.id,
                     "chronicle_eligible": False, "harbinger": False},
            consequence=consequence)
    except RuntimeError as error:
        # Another player may have taken the last ingredient; never mint
        # a packet, overwrite a pantry update or expose a server traceback.
        return None, str(error)
    record_participation(mask, "soup_preparations", calling="innkeep")
    return {"event_id": event["id"], "base": base,
            "seasoning": seasoning,
            "stock": event["consequence"]["stock_after"]}, None


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
    if not soup_state.produce(record["base"], record["seasoning"], warmed=False):
        return None, "The packet has an invalid recipe."
    if _full_bowls(mask) >= 3:
        return None, "You already carry three soup bowls; serve or eat them first."

    def consequence(event):
        # Recheck the real packet, room, clock, Calling and carry limit at
        # commit time. A stale preview must not mint a second bowl.
        with transaction.atomic():
            room_now, reason = _access(mask, TAVERN)
            if reason:
                raise RuntimeError(reason)
            if room_now != tavern:
                raise RuntimeError("The kitchen changed before simmering.")
            if active_calling(mask) != "innkeep":
                raise RuntimeError("An active Innkeep is needed to simmer a batch.")
            if _clock() != (day, hour):
                raise RuntimeError("The village clock changed before simmering.")
            held = _held(mask, "soup_preparation")
            if (len(held) != 1 or held[0] != packet
                    or dict(packet.db.soup_preparation or {}) != record):
                raise RuntimeError(
                    "The reserved ingredients were moved, changed or consumed."
                )
            if _full_bowls(mask) >= 3:
                raise RuntimeError(
                    "You already carry three soup bowls; serve or eat them first."
                )
            if day < int(record["day"]) or day > int(record["day"]) + 2:
                raise RuntimeError("The prepared ingredients are not fresh today.")
            warm_now = hearth_state.active(tavern.db.civic_hearth, day, hour)
            cooked = soup_state.produce(
                record["base"], record["seasoning"], warmed=warm_now)
            if not cooked:
                raise RuntimeError("The packet has an invalid recipe.")
            bowl = create_object(
                "typeclasses.objects.Object",
                key=f"a bowl of {record['base']} and {record['seasoning']} soup",
                location=mask,
                aliases=["homemade soup", "soup bowl", "soup"],
            )
            bowl.tags.add("consumable")
            bowl.tags.add("food")
            bowl.db.consume = {
                "nourish": cooked["nourish"], "servings_max": 1,
                "short": "homemade soup",
                "flavor": (
                    f"You taste {cooked['flavor']}. "
                    "It is a recipe someone here really cooked."
                ),
                "room": f"{mask.key} tastes freshly cooked soup.",
            }
            bowl.db.servings = 1
            bowl.db.soup_serving = {
                **cooked, "event_id": event["id"],
                "prep_event_id": record["prep_event_id"],
                "maker_id": mask.id, "maker": mask.key,
            }
            bowl.db.desc = (
                f"Fresh {record['base']} soup with {record['seasoning']}. "
                f"Cooking quality {cooked['quality']}; "
                f"prepared on village day {record['day']}. "
                "A single real serving, transferable to another player."
            )
            tavern.db.soup_pantry = soup_state.archive(
                tavern.db.soup_pantry, day, maker_id=mask.id,
                maker=mask.key, source_event_id=record["prep_event_id"],
                cook_event_id=event["id"], recipe=cooked)
            packet.delete()
            return {"bowl_id": bowl.id, "pantry_room_id": tavern.id,
                    "quality": cooked["quality"],
                    "source_event_id": record["prep_event_id"],
                    "recipe": cooked}

    try:
        event = publish_world_event(
            "professional.innkeep_soup_cooked", actor=mask,
            payload={"day": day, "hour": hour,
                     "base": record["base"], "seasoning": record["seasoning"],
                     "packet_id": packet.id, "prep_event_id": record["prep_event_id"],
                     "chronicle_eligible": False, "harbinger": False},
            consequence=consequence)
    except RuntimeError as error:
        return None, str(error)
    committed = event["consequence"]["recipe"]
    row = {
        "day": day, "base": committed["base"],
        "seasoning": committed["seasoning"],
        "quality": committed["quality"], "warmed": committed["warmed"],
        "cook_event_id": event["id"],
    }
    mask.db.soup_notebook = soup_state.notebook(mask.db.soup_notebook, row)
    record_participation(mask, "soup_batches_cooked", calling="innkeep")
    return {"event_id": event["id"], **committed}, None


def procure(mask):
    market, err = _access(mask, MARKET)
    if err:
        return None, err
    if active_calling(mask) != "merchant":
        return None, "An active Merchant must procure the kitchen root crate."
    if _held(mask, "soup_delivery"):
        return None, "You already carry a kitchen delivery; take it to the Tavern."
    day, hour = _clock()
    _preview, okay = soup_state.issue_crate(market.db.soup_market, day)
    if not okay:
        return None, "The market has no more kitchen root crates available today."

    def consequence(event):
        with transaction.atomic():
            _room_now, reason = _access(mask, MARKET)
            if reason:
                raise RuntimeError(reason)
            if _room_now != market:
                raise RuntimeError("The market changed during procurement.")
            if active_calling(mask) != "merchant":
                raise RuntimeError("An active Merchant must procure this crate.")
            if _clock()[0] != day:
                raise RuntimeError("The village day changed before procurement.")
            if _held(mask, "soup_delivery"):
                raise RuntimeError("You already carry a kitchen delivery.")
            updated, accepted = soup_state.issue_crate(
                market.db.soup_market, day)
            if not accepted:
                raise RuntimeError(
                    "The market has no more kitchen root crates available today."
                )
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
            market.db.soup_market = updated
            return {"crate_id": crate.id,
                    "remaining_crates": updated["remaining"]}

    try:
        event = publish_world_event(
            "professional.merchant_kitchen_procurement", actor=mask,
            payload={"day": day, "hour": hour, "market_room_id": market.id,
                     "chronicle_eligible": False, "harbinger": False},
            consequence=consequence)
    except RuntimeError as error:
        return None, str(error)
    record_participation(mask, "kitchen_procurements", calling="merchant")
    return {"event_id": event["id"],
            "remaining": event["consequence"]["remaining_crates"]}, None


def deliver(mask):
    tavern, err = _access(mask, TAVERN)
    if err:
        return None, err
    crates = _held(mask, "soup_delivery")
    if not crates:
        return None, "Bring a physical kitchen root crate from Market Lane."
    crate = crates[0]
    day, hour = _clock()
    _preview, okay = soup_state.deliver(tavern.db.soup_pantry, day)
    if not okay:
        return None, "The pantry already has enough turnips for now."
    source = dict(crate.db.soup_delivery or {})
    if day < int(source.get("day") or 0):
        return None, "The crate's procurement lies in the future."

    def consequence(event):
        # Another player can fill the pantry between the preview and event.
        # The crate is consumed only after revalidating the real shared stock.
        with transaction.atomic():
            _room_now, reason = _access(mask, TAVERN)
            if reason:
                raise RuntimeError(reason)
            if _room_now != tavern:
                raise RuntimeError("The kitchen changed before delivery.")
            if _clock()[0] != day:
                raise RuntimeError("The village day changed before delivery.")
            if crate.location != mask or dict(crate.db.soup_delivery or {}) != source:
                raise RuntimeError("The physical kitchen crate changed hands or contents.")
            updated, accepted = soup_state.deliver(
                tavern.db.soup_pantry, day)
            if not accepted:
                raise RuntimeError(
                    "The pantry already has enough turnips. Keep the crate for later."
                )
            crate.delete()
            tavern.db.soup_pantry = updated
            return {"turnip_stock": updated["stock"]["turnip"],
                    "procurement_event_id": source.get("procurement_event_id")}

    try:
        event = publish_world_event(
            "village.kitchen_delivery", actor=mask,
            payload={"day": day, "hour": hour,
                     "crate_id": crate.id,
                     "procurement_event_id": source.get("procurement_event_id"),
                     "chronicle_eligible": False, "harbinger": False},
            consequence=consequence)
    except RuntimeError as error:
        return None, str(error)
    return {"event_id": event["id"],
            "turnips": event["consequence"]["turnip_stock"]}, None
