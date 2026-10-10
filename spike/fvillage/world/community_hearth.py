"""Player-built warmth at the Blood of the Vine, not an authored quest.

Finite bundles become physical carryable objects, the Tavern keeps an actual
reserve, and an active Innkeep spends one bundle for eight game-hours of
additional warmth. The hearth never extinguishes entirely in existing canon.
No free points, mastery, impossible offscreen jobs or paid model service.
"""

from __future__ import annotations

from evennia import create_object
from evennia.scripts.models import ScriptDB
from evennia.utils import search

from world import hearth_state
from world.callings import active_calling, record_participation
from world.events import publish_world_event


WOODPILE_KEY = "a village woodpile"
SQUARE_KEY = "Village Square"
TAVERN_KEY = "The Blood of the Vine"
FIREWOOD_KEY = "a bundle of firewood"


def _room(name):
    return next(
        (obj for obj in search.search_object(name)
         if obj.key == name and obj.location is None), None
    )


def _woodpile():
    square = _room(SQUARE_KEY)
    return next(
        (obj for obj in (square.contents if square else [])
         if obj.key == WOODPILE_KEY), None
    )


def _clock():
    try:
        script = ScriptDB.objects.get(db_key="village_time")
        return (
            int(script.db.day or 1),
            int(script.db.hour if script.db.hour is not None else 21),
        )
    except ScriptDB.DoesNotExist:
        return 1, 21


def _status():
    day, hour = _clock()
    source = _woodpile()
    tavern = _room(TAVERN_KEY)
    return {
        "day": day, "hour": hour,
        "woodpile": hearth_state.source(
            source.db.civic_wood if source else None, day
        ) if source else None,
        "hearth": hearth_state.hearth(
            tavern.db.civic_hearth if tavern else None
        ) if tavern else None,
    }


def public_woodpile_line():
    status = _status()
    source = status["woodpile"]
    if source is None:
        return "The communal pile has not been built."
    return (
        "Neatly split timber left beside the square for anyone carrying wood "
        "to the Blood of the Vine. "
        f"{source['remaining']} of today's {hearth_state.DAILY_WOOD} "
        "bundles remain. Try |whearth gather|n if you wish to carry one."
    )


def public_hearth_line():
    status = _status()
    data = status["hearth"]
    if data is None:
        return "There is no hearth to tend."
    if hearth_state.active(data, status["day"], status["hour"]):
        remaining = data["warm_until"] - hearth_state.absolute_hour(
            status["day"], status["hour"]
        )
        return (
            "Fresh logs blaze in the Blood of the Vine's hearth; the heat "
            f"will settle in {remaining} village hour"
            + ("s." if remaining != 1 else ".")
        )
    return (
        "Only a bed of faithful embers remains in the Blood of the Vine's "
        "hearth. The Innkeep can build the fire up from delivered fuel."
    )


def status_lines():
    status = _status()
    source, data = status["woodpile"], status["hearth"]
    if source is None or data is None:
        return "The civic hearth materials have not been prepared."
    last = data["history"][-1] if data["history"] else None
    lines = [
        "|wThe Village Hearth|n",
        public_hearth_line(),
        f"Tavern firewood reserve: {data['reserve']} of "
        f"{hearth_state.MAX_RESERVE} bundles.",
        f"Village Square woodpile: {source['remaining']} of "
        f"{hearth_state.DAILY_WOOD} bundles available today.",
    ]
    if last:
        lines.append(
            f"Last tended by {last['mask']} on village day "
            f"{last['day']}, hour {last['hour']:02d}."
        )
    lines.append(
        "From the Square: |whearth gather|n (take a real bundle); "
        "in the Tavern: |whearth deliver|n; an active Innkeep can "
        "|whearth tend|n when the fire has settled. "
        "Bring a friend, or leave delivered stock for the next Innkeep."
    )
    return "\n".join(lines)


def _actor_ok(mask, room_key):
    room = getattr(mask, "location", None)
    if not getattr(mask, "account", None):
        return False, "Only a logged-in player mask may take part."
    if not room or room.key != room_key or not room.tags.has("ic", category="side"):
        return False, (
            "For this action you must be in "
            + ("the Village Square." if room_key == SQUARE_KEY
               else "the Blood of the Vine.")
        )
    return True, None


def _carried(mask):
    return [
        obj for obj in mask.contents
        if obj.key == FIREWOOD_KEY and obj.db.civic_firewood is True
    ]


def gather(mask):
    allowed, error = _actor_ok(mask, SQUARE_KEY)
    if not allowed:
        return None, error
    wood = _woodpile()
    if wood is None:
        return None, "The square woodpile is missing."
    if _carried(mask):
        return None, (
            "You already carry a firewood bundle; deliver or give it "
            "to another traveler before gathering more."
        )
    day, hour = _clock()
    current = hearth_state.source(wood.db.civic_wood, day)
    updated, permitted = hearth_state.take(current, day)
    if not permitted:
        return None, "The woodpile has no more bundles ready today."
    def consequence(event):
        bundle = create_object(
            "typeclasses.objects.Object", key=FIREWOOD_KEY,
            location=mask, aliases=["firewood", "wood bundle"],
        )
        bundle.db.civic_firewood = True
        bundle.db.source_day = day
        bundle.db.gather_event_id = event["id"]
        bundle.db.desc = (
            "One tangible bundle of dry split wood, carried from the "
            "Village Square pile. Deliver it to the Blood of the Vine "
            "or give it to someone who will."
        )
        wood.db.civic_wood = updated
        return {
            "bundle_id": bundle.id, "woodpile_object_id": wood.id,
            "remaining": updated["remaining"],
        }
    event = publish_world_event(
        "civic.hearth_firewood_gathered", actor=mask,
        payload={"day": day, "hour": hour, "resource": FIREWOOD_KEY,
                 "chronicle_eligible": False, "harbinger": False},
        consequence=consequence,
    )
    return {
        "event_id": event["id"], "remaining": updated["remaining"],
    }, None


def deliver(mask):
    allowed, error = _actor_ok(mask, TAVERN_KEY)
    if not allowed:
        return None, error
    bundles = _carried(mask)
    if not bundles:
        return None, (
            "Bring a real bundle of firewood from the Village Square. "
            "Nothing has been placed in the Tavern stock."
        )
    tavern = _room(TAVERN_KEY)
    current = hearth_state.hearth(tavern.db.civic_hearth)
    updated, allowed = hearth_state.deliver(current)
    if not allowed:
        return None, "The Tavern's firewood rack is full. Leave this bundle for later."
    bundle = bundles[0]
    source_id = bundle.db.gather_event_id
    def consequence(event):
        tavern.db.civic_hearth = updated
        bundle.delete()
        return {
            "resource": FIREWOOD_KEY, "reserve": updated["reserve"],
            "gather_event_id": source_id,
        }
    event = publish_world_event(
        "civic.hearth_firewood_delivered", actor=mask,
        payload={"resource": FIREWOOD_KEY, "gather_event_id": source_id,
                 "chronicle_eligible": False, "harbinger": False},
        consequence=consequence,
    )
    return {
        "event_id": event["id"], "reserve": updated["reserve"],
    }, None


def tend(mask):
    allowed, error = _actor_ok(mask, TAVERN_KEY)
    if not allowed:
        return None, error
    if active_calling(mask) != "innkeep":
        return None, "An active Innkeep is needed to tend the Tavern hearth."
    tavern = _room(TAVERN_KEY)
    day, hour = _clock()
    current = hearth_state.hearth(tavern.db.civic_hearth)
    if current["reserve"] <= 0:
        return None, "The hearth has no stored firewood. A traveler must deliver a bundle."
    if hearth_state.active(current, day, hour):
        return None, "The hearth is already blazing. Let these logs burn first."
    def consequence(event):
        changed, success = hearth_state.stoke(
            current, day, hour,
            actor={"mask_id": mask.id, "mask": mask.key},
            source_event_id=event["id"],
        )
        if not success:
            raise RuntimeError("Civic hearth state changed before tending.")
        tavern.db.civic_hearth = changed
        return {
            "reserve": changed["reserve"],
            "warm_until": changed["warm_until"],
            "tavern_room_id": tavern.id,
        }
    event = publish_world_event(
        "civic.hearth_tended", actor=mask,
        payload={"professional_calling": "innkeep", "resource": FIREWOOD_KEY,
                 "chronicle_eligible": False, "harbinger": False},
        consequence=consequence,
    )
    record_participation(mask, "hearth_tendings", calling="innkeep")
    return {
        "event_id": event["id"],
        "reserve": current["reserve"] - 1,
        "warm_until": hearth_state.absolute_hour(day, hour) + hearth_state.WARM_HOURS,
    }, None
