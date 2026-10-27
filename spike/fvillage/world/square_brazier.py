"""Ordinary players maintain the public Village Square warming brazier.

One world-object record owns the fire, one existing woodpile supplies physical
bundles, and the existing warmth watch applies the real bodily consequence.
A signed world event ties each consumed bundle to a visible contribution.
"""
from __future__ import annotations

from django.db import transaction
from evennia.scripts.models import ScriptDB
from evennia.utils import search

from world import square_brazier_state
from world import civic_commissions
from world.community_hearth import FIREWOOD_KEY, SQUARE_KEY, TAVERN_KEY
from world.events import publish_world_event

BRAZIER_KEY = "a public warming brazier"


def _room(name):
    return next(
        (room for room in search.search_object(name)
         if room.key == name and room.location is None),
        None,
    )


def _brazier():
    square = _room(SQUARE_KEY)
    return next(
        (obj for obj in square.contents if obj.key == BRAZIER_KEY),
        None,
    ) if square else None


def _clock():
    try:
        script = ScriptDB.objects.get(db_key="village_time")
        return int(script.db.day or 1), int(
            script.db.hour if script.db.hour is not None else 21
        )
    except ScriptDB.DoesNotExist:
        return 1, 21


def _carried(mask):
    return [
        obj for obj in mask.contents
        if obj.key == FIREWOOD_KEY
        and obj.db.civic_firewood is True
        and isinstance(obj.db.gather_event_id, int)
        and obj.db.gather_event_id > 0
    ]


def _pledged_bundle_id(day):
    tavern = _room(TAVERN_KEY)
    if tavern is None:
        return None
    order = civic_commissions.refresh(
        tavern.db.civic_commission, day
    )["commission"]
    return (
        int(order["bundle_id"])
        if order and order["status"] == "pledged"
        else None
    )


def _usable_bundle(mask, day):
    pledged_id = _pledged_bundle_id(day)
    return next(
        (item for item in _carried(mask)
         if int(item.id) != pledged_id),
        None,
    )


def _guard(mask):
    square = _room(SQUARE_KEY)
    if not getattr(mask, "account", None):
        return None, "A logged-in village player must tend the brazier."
    if (square is None or mask.location != square
            or not square.tags.has("ic", category="side")):
        return None, "Travel to Village Square to tend its public brazier."
    return square, None


def is_active():
    """Read the ONE persistent brazier object, without granting resources."""
    obj = _brazier()
    if obj is None:
        return False
    day, hour = _clock()
    return square_brazier_state.active(obj.db.square_brazier, day, hour)


def public_line():
    obj = _brazier()
    if obj is None:
        return "The Square has no public brazier prepared."
    day, hour = _clock()
    state = square_brazier_state.normalize(obj.db.square_brazier)
    left = square_brazier_state.remaining(state, day, hour)
    if left:
        return (
            "Split logs glow in the Square's shared iron brazier. "
            f"The warmth will last {left} more village hour(s). "
            "This is real shelter from the cold for anyone present."
        )
    return (
        "The public iron brazier by the Square woodpile is cold. "
        "A traveler can light it with a physical bundle of firewood."
    )


def status_lines(mask=None):
    brazier = _brazier()
    if brazier is None:
        return "The Square's shared warming brazier has not been built."
    day, hour = _clock()
    state = square_brazier_state.normalize(brazier.db.square_brazier)
    lines = [
        "|wThe Square's public warming brazier|n",
        public_line(),
        f"Village day {day}, hour {hour:02d}.",
        "Anyone, with or without a Calling, can carry one real bundle from "
        "the existing Square woodpile using |whearth gather|n.",
        "Use |wbrazier light|n while cold, or |wbrazier feed|n while burning "
        "to add limited warmth. It consumes the actual bundle; no fuel is "
        "minted and no XP is awarded.",
    ]
    if state["history"]:
        last = state["history"][-1]
        lines.append(
            f"Last supplied by {last['mask']} on village day "
            f"{last['day']}, hour {last['hour']:02d} "
            f"(signed event {last['event_id']})."
        )
    if mask is not None and getattr(mask, "account", None):
        room, reason = _guard(mask)
        if room is not None:
            usable = _usable_bundle(mask, day)
            if usable is not None:
                lines.append(
                    "You carry a free physical firewood bundle that can "
                    "be used here now, if the fire needs it."
                )
            elif _carried(mask):
                lines.append(
                    "Your carried bundle is pledged to another current "
                    "commission; it cannot be taken for this brazier."
                )
    return "\n".join(lines)


def act(mask, mode):
    """Signed ordinary-client public project with actual wood custody."""
    if mode not in {"light", "feed"}:
        return None, "Use brazier | brazier light | brazier feed."
    room, error = _guard(mask)
    if error:
        return None, error
    brazier = _brazier()
    if brazier is None or brazier.location != room:
        return None, "The public iron brazier is not available."
    day, hour = _clock()
    bundle = _usable_bundle(mask, day)
    if bundle is None:
        if _carried(mask):
            return None, (
                "That firewood is pledged to an open commission. "
                "Keep it for its intended carrier or cancel the pledge first."
            )
        return None, (
            "Carry a real bundle from the Village Square woodpile. "
            "Use hearth gather before brazier light or brazier feed."
        )
    preview, allowed, reason = square_brazier_state.contribute(
        brazier.db.square_brazier, day, hour, mode=mode,
        actor={"mask_id": mask.id, "mask": mask.key},
        bundle_id=bundle.id, gather_event_id=bundle.db.gather_event_id,
        event_id=-1,
    )
    if not allowed:
        return None, reason
    source_event_id = int(bundle.db.gather_event_id)
    bundle_id = int(bundle.id)  # Django may clear pk after object.delete()

    def consequence(event):
        with transaction.atomic():
            now_room, why = _guard(mask)
            if why:
                raise RuntimeError(why)
            if now_room != room or _brazier() != brazier:
                raise RuntimeError("The Square brazier changed during tending.")
            if _clock() != (day, hour):
                raise RuntimeError(
                    "The village clock changed before you tended the brazier."
                )
            if (bundle.location != mask
                    or bundle.db.civic_firewood is not True
                    or bundle.db.gather_event_id != source_event_id):
                raise RuntimeError(
                    "The physical firewood is no longer in your hands."
                )
            if int(bundle.id) == _pledged_bundle_id(day):
                raise RuntimeError(
                    "This bundle has since been pledged to a civic commission."
                )
            changed, accepted, why = square_brazier_state.contribute(
                brazier.db.square_brazier, day, hour, mode=mode,
                actor={"mask_id": mask.id, "mask": mask.key},
                bundle_id=bundle_id, gather_event_id=source_event_id,
                event_id=event["id"],
            )
            if not accepted:
                raise RuntimeError(why)
            bundle.delete()
            brazier.db.square_brazier = changed
            return {
                "brazier_id": brazier.id,
                "bundle_id": bundle_id,
                "gather_event_id": source_event_id,
                "warm_until": changed["warm_until"],
                "remaining": square_brazier_state.remaining(
                    changed, day, hour
                ),
            }

    try:
        event = publish_world_event(
            "civic.square_brazier_" + mode, actor=mask,
            payload={
                "day": day, "hour": hour,
                "brazier_id": brazier.id,
                "bundle_id": bundle_id,
                "gather_event_id": source_event_id,
                "chronicle_eligible": False,
                "harbinger": False,
            },
            consequence=consequence,
        )
    except RuntimeError as err:
        return None, str(err)
    return {
        "mode": mode,
        "event_id": event["id"],
        "remaining": event["consequence"]["remaining"],
        "bundle_id": bundle_id,
    }, None
