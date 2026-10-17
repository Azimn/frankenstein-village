"""World-owned cross-location daily commissions using tangible firewood.

Square pledge -> ordinary player-to-player object handoff -> Tavern delivery.
No teleportation, free resource creation, XP reward or NPC completion.
"""
from __future__ import annotations

from django.db import transaction
from evennia.scripts.models import ScriptDB
from evennia.utils import search

from world import civic_commissions, hearth_state
from world.community_hearth import FIREWOOD_KEY, SQUARE_KEY, TAVERN_KEY
from world.events import publish_world_event


def _tavern():
    return next(
        (room for room in search.search_object(TAVERN_KEY)
         if room.key == TAVERN_KEY and room.location is None),
        None,
    )


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
        if obj.key == FIREWOOD_KEY and obj.db.civic_firewood is True
    ]


def _guard(mask, room_name):
    if not getattr(mask, "account", None):
        return "A logged-in player mask is required."
    room = getattr(mask, "location", None)
    if not room or room.key != room_name or not room.tags.has("ic", category="side"):
        return f"Travel to {room_name} to perform this work."
    return None


def _state(tavern, day):
    return civic_commissions.refresh(tavern.db.civic_commission, day)


def status_lines():
    tavern = _tavern()
    if not tavern:
        return "The village commissions are unavailable; the Tavern is missing."
    day, hour = _clock()
    state = _state(tavern, day)
    item = state["commission"]
    if item is None:
        return "The commission board has no current day."
    lines = [
        "|wVillage Commission: The Shared Firewood|n",
        f"Day {day}, hour {hour:02d}. Commission {item['id']}: {item['status']}.",
    ]
    if item["status"] == "open":
        lines += [
            "The Blood of the Vine needs one physical bundle of firewood.",
            "In the Village Square: |whearth gather|n, then |wcommission pledge|n.",
            "Give that exact bundle to another player with the ordinary |wgive|n command.",
            "That player carries it east to the Tavern and uses |wcommission deliver|n.",
        ]
    elif item["status"] == "pledged":
        lines += [
            f"{item['supplier_mask']} pledged a real bundle in the Square.",
            "Another account must carry that exact bundle to the Blood of the Vine.",
            "Use |wcommission deliver|n there to add it to the public hearth rack.",
            "A pledged bundle can still be exchanged or dropped normally.",
        ]
    else:
        lines += [
            f"Completed by {item['supplier_mask']} and {item['finisher_mask']}.",
            "One finite wood bundle was added to the shared Tavern rack.",
            "An active Innkeep may tend the fire from this actual reserve.",
        ]
    lines += [
        "There is one commission per village day. Unfinished pledges expire at the",
        "next day without confiscating their physical bundles. No experience is awarded.",
    ]
    return "\n".join(lines)


def pledge(mask):
    error = _guard(mask, SQUARE_KEY)
    if error:
        return None, error
    tavern = _tavern()
    if not tavern:
        return None, "The Tavern has not been constructed."
    day, hour = _clock()
    state = _state(tavern, day)
    if not state["commission"] or state["commission"]["status"] != "open":
        return None, "Today's commission is no longer open."
    bundles = _carried(mask)
    if not bundles:
        return None, "First gather a physical firewood bundle with |whearth gather|n."
    bundle = bundles[0]
    def consequence(event):
        with transaction.atomic():
            if bundle.location != mask or bundle.db.civic_firewood is not True:
                raise RuntimeError("The pledged bundle is no longer in the mask's hands.")
            changed, success, reason = civic_commissions.pledge(
                tavern.db.civic_commission, day, mask.account.id, mask.key,
                bundle_id=int(bundle.id), event_id=event["id"],
            )
            if not success:
                raise RuntimeError(reason)
            tavern.db.civic_commission = changed
            return {
                "commission_id": changed["commission"]["id"],
                "bundle_id": int(bundle.id), "source_event_id": bundle.db.gather_event_id,
                "day": day,
            }
    event = publish_world_event(
        "civic.commission_pledged", actor=mask,
        payload={"day": day, "hour": hour, "bundle_id": bundle.id,
                 "harbinger": False, "chronicle_eligible": False},
        consequence=consequence,
    )
    return {"event_id": event["id"], "bundle_id": bundle.id}, None


def deliver(mask):
    error = _guard(mask, TAVERN_KEY)
    if error:
        return None, error
    tavern = _tavern()
    if not tavern:
        return None, "The Tavern has not been constructed."
    day, hour = _clock()
    state = _state(tavern, day)
    item = state["commission"]
    if not item or item["status"] != "pledged":
        return None, "A neighbor must first pledge a real bundle in the Village Square."
    if mask.account.id == item["supplier_account"]:
        return None, "Another player's account must carry out the delivery."
    bundle = next(
        (obj for obj in _carried(mask) if int(obj.id) == item["bundle_id"]),
        None,
    )
    if bundle is None:
        return None, "Carry the exact pledged bundle to the Tavern."
    current = hearth_state.hearth(tavern.db.civic_hearth)
    if current["reserve"] >= hearth_state.MAX_RESERVE:
        return None, "The Tavern rack is full. Wait until an Innkeep tends the fire."
    def consequence(event):
        with transaction.atomic():
            if bundle.location != mask or bundle.db.civic_firewood is not True:
                raise RuntimeError("The pledged firewood was moved before delivery.")
            changed, success, reason = civic_commissions.finish(
                tavern.db.civic_commission, day, mask.account.id, mask.key,
                carried_bundle_id=int(bundle.id), reserve_has_space=True,
                event_id=event["id"],
            )
            if not success:
                raise RuntimeError(reason)
            rack, accepted = hearth_state.deliver(tavern.db.civic_hearth)
            if not accepted:
                raise RuntimeError("The Tavern wood rack filled before completion.")
            # Transaction protects the resource transfer from partial DB writes.
            bundle.delete()
            tavern.db.civic_hearth = rack
            tavern.db.civic_commission = changed
            return {
                "commission_id": changed["commission"]["id"],
                "bundle_id": int(item["bundle_id"]),
                "reserve": rack["reserve"], "day": day,
            }
    event = publish_world_event(
        "civic.commission_completed", actor=mask,
        payload={"day": day, "hour": hour, "bundle_id": int(bundle.id),
                 "supplier_account_id": item["supplier_account"],
                 "harbinger": False, "chronicle_eligible": False},
        consequence=consequence,
    )
    return {"event_id": event["id"], "reserve": current["reserve"] + 1,
            "supplier_mask": item["supplier_mask"]}, None
