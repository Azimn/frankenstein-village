"""EDGE-08: original treeline cord, physical Hound dispatch, finite Tavern meal."""
from __future__ import annotations

from django.db import transaction
from evennia import create_object
from evennia.scripts.models import ScriptDB
from evennia.utils import search

from world import refuge_state, soup_state
from world.callings import active_calling, record_participation
from world.discoveries import LANDMARKS, normalize as known_landmarks, observed_caution
from world.events import get_event_ledger, publish_world_event

TAVERN = "The Blood of the Vine"
CORD = LANDMARKS["red_cord"]["key"]
TREELINE = LANDMARKS["red_cord"]["room"]
DISPATCH = "a signed treeline refuge dispatch"


def _room(key):
    return next((r for r in search.search_object(key)
                 if r.key == key and r.location is None), None)


def _clock():
    try:
        script = ScriptDB.objects.get(db_key="village_time")
        return int(script.db.day or 1), int(
            script.db.hour if script.db.hour is not None else 21)
    except ScriptDB.DoesNotExist:
        return 1, 21


def _cord(room):
    return next((obj for obj in room.contents
                 if obj.key == CORD and getattr(obj.db, "landmark_id", None) == "red_cord"),
                None)


def dispatch(mask):
    room = _room(TREELINE)
    if (not getattr(mask, "account", None) or room is None
            or mask.location != room or not room.tags.has("ic", category="side")):
        return None, "A logged-in Hound must stand at the Northern Treeline."
    if active_calling(mask) != "hound":
        return None, "Only an active Hound may issue a firsthand refuge dispatch."
    cord = _cord(room)
    if cord is None:
        return None, "The original frayed red cord is missing."
    day, hour = _clock()
    dispatch_account_id, dispatch_mask_id = mask.account.id, mask.id
    latest = dict(getattr(mask.db, "landmark_latest_view", None) or {})
    seen = latest.get("red_cord") or {}
    if (not any(row["id"] == "red_cord" for row in
                known_landmarks(mask.db.landmark_discoveries))
            or not hasattr(seen, "get") or seen.get("day") != day):
        return None, "Look at the physical red cord here today first."
    marker = cord.db.route_caution
    source_id = refuge_state.ident(
        marker.get("event_id") if hasattr(marker, "get") else None)
    source = get_event_ledger().get_event(source_id or -1)
    allowed, why = refuge_state.can_dispatch(
        cord.db.refuge_dispatch_last, source, marker,
        cord_id=cord.id, day=day, hour=hour,
        hound_account_id=mask.account.id, hound_mask_id=mask.id)
    if not allowed:
        return None, why
    if not observed_caution(
            latest, day=day, hour=hour, source_event_id=source["id"],
            cord_id=cord.id):
        return None, (
            "Look at the physical signed red cord after the current Hound "
            "warning before issuing a refuge dispatch.")
    if any(getattr(obj.db, "route_refuge_dispatch", None) for obj in mask.contents):
        return None, "Carry your existing refuge dispatch to the Tavern first."

    def consequence(event):
        with transaction.atomic():
            if mask.location != room or cord.location != room:
                raise RuntimeError("The Hound or original cord left the scene.")
            if not refuge_state.same_actor(
                    getattr(getattr(mask, "account", None), "id", None),
                    mask.id, dispatch_account_id, dispatch_mask_id):
                raise RuntimeError("The signed Hound account or mask changed.")
            if active_calling(mask) != "hound" or _clock() != (day, hour):
                raise RuntimeError("Hound authority or village time changed.")
            fresh_source = get_event_ledger().get_event(source["id"])
            ok, reason = refuge_state.can_dispatch(
                cord.db.refuge_dispatch_last, fresh_source, cord.db.route_caution,
                cord_id=cord.id, day=day, hour=hour,
                hound_account_id=mask.account.id, hound_mask_id=mask.id)
            if not ok:
                raise RuntimeError(reason)
            fresh_latest = dict(
                getattr(mask.db, "landmark_latest_view", None) or {})
            if not observed_caution(
                    fresh_latest.get("red_cord"),
                    day=day, hour=hour, source_event_id=source["id"],
                    cord_id=cord.id):
                raise RuntimeError(
                    "The Hound's firsthand signed cord inspection changed.")
            item = create_object(
                "typeclasses.objects.Object", key=DISPATCH, location=mask,
                aliases=["refuge dispatch", "treeline dispatch"])
            item.db.route_refuge_dispatch = {
                "dispatch_event_id": event["id"],
                "source_protect_event_id": source["id"],
                "hound_account_id": mask.account.id,
                "hound_mask_id": mask.id,
                "cord_id": cord.id, "day": day, "hour": hour,
            }
            item.db.desc = (
                "A physical report from a Hound who inspected the original "
                "treeline cord. It does not claim a rescued stranger. Carry "
                "it to the Blood of the Vine; a separate Innkeep can use "
                "soup refuge <hound mask> while you are present.")
            cord.db.refuge_dispatch_last = {
                "day": day, "event_id": event["id"],
                "account_id": mask.account.id, "item_id": item.id,
            }
            return {"item_id": item.id, "cord_id": cord.id,
                    "source_protect_event_id": source["id"]}

    event = publish_world_event(
        "professional.hound_refuge_dispatch", actor=mask,
        payload={"day": day, "hour": hour, "cord_id": cord.id,
                 "source_protect_event_id": source["id"],
                 "professional_calling": "hound", "location": TREELINE,
                 "harbinger": False, "chronicle_eligible": False},
        consequence=consequence)
    record_participation(mask, "refuge_dispatches", calling="hound")
    return {"event_id": event["id"], "source_id": source["id"]}, None


def serve(mask, hound_name):
    tavern = _room(TAVERN)
    if (not getattr(mask, "account", None) or tavern is None
            or mask.location != tavern or not tavern.tags.has("ic", category="side")):
        return None, "An Innkeep must be at the Blood of the Vine."
    if active_calling(mask) != "innkeep":
        return None, "Only an active Innkeep can allocate a refuge meal."
    name = (hound_name or "").strip().lower()
    if not name:
        return None, "Use soup refuge <hound mask> with the Hound present."
    matches = [obj for obj in tavern.contents
               if obj.key.lower() == name and getattr(obj, "account", None)]
    if len(matches) != 1:
        return None, "The named logged-in Hound is not here."
    hound = matches[0]
    if active_calling(hound) != "hound":
        return None, "The traveler must still be an active Hound."
    if hound.account.id == mask.account.id:
        return None, "A second player account must serve the Hound."
    innkeep_account_id, innkeep_mask_id = mask.account.id, mask.id
    hound_account_id, hound_mask_id = hound.account.id, hound.id
    tokens = [obj for obj in hound.contents
              if getattr(obj.db, "route_refuge_dispatch", None)]
    if len(tokens) != 1:
        return None, "The Hound must carry exactly one physical refuge dispatch."
    item = tokens[0]
    token = dict(item.db.route_refuge_dispatch)
    cord_room = _room(TREELINE)
    cord = _cord(cord_room) if cord_room else None
    if cord is None:
        return None, "The original treeline source cannot be verified."
    ledger = get_event_ledger()
    dispatch_event = ledger.get_event(token.get("dispatch_event_id"))
    source_event = ledger.get_event(token.get("source_protect_event_id"))
    day, hour = _clock()

    def preview(event_id):
        return refuge_state.accept(
            tavern.db.route_refuge, tavern.db.soup_pantry,
            day=day, hour=hour, innkeep_account_id=innkeep_account_id,
            innkeep_mask_id=innkeep_mask_id, hound_account_id=hound_account_id,
            hound_mask_id=hound_mask_id, token=token, token_id=item.id,
            dispatch_event=dispatch_event, protection=source_event,
            marker=cord.db.route_caution, cord_id=cord.id,
            tavern_id=tavern.id, event_id=event_id)

    _state, _food, allowed, why = preview(1)
    if not allowed:
        return None, why

    def consequence(event):
        with transaction.atomic():
            if (mask.location != tavern or hound.location != tavern
                    or item.location != hound or cord.location != cord_room
                    or active_calling(mask) != "innkeep"
                    or active_calling(hound) != "hound"
                    or _clock() != (day, hour)):
                raise RuntimeError("The participants, item or time changed.")
            if (not refuge_state.same_actor(
                    getattr(getattr(mask, "account", None), "id", None),
                    mask.id, innkeep_account_id, innkeep_mask_id)
                    or not refuge_state.same_actor(
                        getattr(getattr(hound, "account", None), "id", None),
                        hound.id, hound_account_id, hound_mask_id)):
                raise RuntimeError("A signed participant account or mask changed.")
            current = dict(item.db.route_refuge_dispatch or {})
            if current != token:
                raise RuntimeError("The physical dispatch was changed.")
            refuge, food, ok, reason = refuge_state.accept(
                tavern.db.route_refuge, tavern.db.soup_pantry,
                day=day, hour=hour, innkeep_account_id=innkeep_account_id,
                innkeep_mask_id=innkeep_mask_id, hound_account_id=hound_account_id,
                hound_mask_id=hound_mask_id, token=current, token_id=item.id,
                dispatch_event=ledger.get_event(token["dispatch_event_id"]),
                protection=ledger.get_event(token["source_protect_event_id"]),
                marker=cord.db.route_caution, cord_id=cord.id,
                tavern_id=tavern.id, event_id=event["id"])
            if not ok:
                raise RuntimeError(reason)
            recipe = soup_state.produce("turnip", "salt", warmed=False)
            bowl = create_object(
                "typeclasses.objects.Object",
                key="a bowl of Hound refuge soup", location=hound,
                aliases=["refuge soup", "soup bowl", "soup"])
            bowl.tags.add("consumable")
            bowl.tags.add("food")
            bowl.db.consume = {
                "nourish": recipe["nourish"], "servings_max": 1,
                "short": "refuge soup",
                "flavor": "Warm, plain turnip soup from the Tavern's real pantry.",
                "room": f"{hound.key} eats a bowl of refuge soup.",
            }
            bowl.db.servings = 1
            bowl.db.soup_serving = {
                **recipe, "event_id": event["id"],
                "dispatch_event_id": token["dispatch_event_id"],
                "maker_id": mask.id, "maker": mask.key,
            }
            bowl.db.desc = (
                "One real serving for the Hound who arrived from the "
                "Northern Treeline. It can be eaten or transferred.")
            refuge["history"][-1]["bowl_id"] = bowl.id
            tavern.db.soup_pantry = food
            tavern.db.route_refuge = refuge
            # Evennia clears the database ID on delete. Capture the physical
            # custody identifier before consuming the object.
            consumed_dispatch_id = item.id
            item.delete()
            return {
                "bowl_id": bowl.id, "consumed_dispatch_id": consumed_dispatch_id,
                "dispatch_event_id": token["dispatch_event_id"],
                "source_protect_event_id": token["source_protect_event_id"],
                "tavern_id": tavern.id,
                "stock_after": {"turnip": food["stock"]["turnip"],
                                "salt": food["stock"]["salt"]},
            }

    event = publish_world_event(
        "professional.innkeep_refuge_meal", actor=mask,
        payload={"day": day, "hour": hour, "tavern_id": tavern.id,
                 "hound_account_id": hound_account_id,
                 "hound_mask_id": hound_mask_id, "dispatch_item_id": item.id,
                 "dispatch_event_id": token["dispatch_event_id"],
                 "professional_calling": "innkeep",
                 "harbinger": False, "chronicle_eligible": False},
        consequence=consequence)
    record_participation(mask, "refuge_meals", calling="innkeep")
    return {"event_id": event["id"],
            "bowl_id": event["consequence"]["bowl_id"],
            "turnip": event["consequence"]["stock_after"]["turnip"]}, None
