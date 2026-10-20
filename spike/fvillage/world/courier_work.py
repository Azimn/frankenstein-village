"""Real Market Lane to Riverside Path courier deliveries for village Wanderers."""
from __future__ import annotations
from django.db import transaction
from evennia import create_object
from evennia.scripts.models import ScriptDB
from evennia.utils import search
from world import courier_state
from world.callings import active_calling, record_participation
from world.events import publish_world_event

MARKET = "Market Lane"
RIVERSIDE = "Riverside Path"
PARCEL = "a sealed village mail parcel"


def _room(name):
    return next((obj for obj in search.search_object(name)
                 if obj.key == name and obj.location is None
                 and obj.tags.has("ic", category="side")), None)


def _clock():
    try:
        script = ScriptDB.objects.get(db_key="village_time")
        return int(script.db.day or 1), int(
            script.db.hour if script.db.hour is not None else 21)
    except ScriptDB.DoesNotExist:
        return 1, 21


def _access(mask, room):
    return (bool(getattr(mask, "account", None)) and room is not None
            and getattr(mask, "location", None) == room)


def status(mask):
    day, _ = _clock()
    market, path = _room(MARKET), _room(RIVERSIDE)
    if not getattr(mask, "account", None):
        return "Only ordinary in-character players can read village post work."
    if market is None or path is None:
        return "The ferry-post route has not been constructed."
    supply = courier_state.stock(market.db.ferry_post_stock, day)
    receipts = courier_state.manifest(path.db.ferry_manifest)["receipts"]
    last = receipts[-1] if receipts else None
    lines = [
        "|wThe village ferry post|n",
        f"Market Lane postbag, day {day}: {supply['remaining']} real parcels left.",
        f"{len(receipts)} signed recent deliveries retained by the Riverside post chest.",
        "An active Wanderer can collect a physical parcel in Market Lane: |wcourier collect|n.",
        "Carry it east through the Tavern to Riverside Path, or give it to a neighbor.",
        "Any real carrier at Riverside Path may use |wcourier deliver|n.",
    ]
    if last:
        lines.append(
            f"Latest delivery by {last['mask']} on day {last['day']} "
            f"(world event {last['delivery_event_id']}).")
    return "\n".join(lines)


def collect(mask):
    market = _room(MARKET)
    if not _access(mask, market):
        return None, "Collect ferry post in Market Lane with an ordinary player mask."
    if active_calling(mask) != "wanderer":
        return None, "An active Wanderer collects scheduled ferry post."
    if any(obj.db.ferry_parcel for obj in mask.contents):
        return None, "You already carry a post parcel. Deliver or hand it over."
    day, hour = _clock()
    candidate, ok = courier_state.issue(market.db.ferry_post_stock, day)
    if not ok:
        return None, "The postal bag has no more parcels for this village day."

    def consequence(event):
        with transaction.atomic():
            latest, allowed = courier_state.issue(
                market.db.ferry_post_stock, day)
            if not allowed or mask.location != market:
                raise RuntimeError("The market parcel is no longer available.")
            parcel = create_object(
                "typeclasses.objects.Object", key=PARCEL,
                location=mask, aliases=["mail parcel", "ferry parcel"],
            )
            parcel.db.ferry_parcel = {
                "day": day, "origin_room_id": market.id,
                "source_event_id": event["id"],
                "collector_account_id": mask.account.id,
            }
            parcel.db.desc = (
                "A physically sealed, unsigned private letter sack for "
                "the ferry post, without any player-private contents. "
                "Carry it to Riverside Path and use courier deliver, "
                "or hand it to a trusted neighbor."
            )
            market.db.ferry_post_stock = latest
            return {"parcel_id": parcel.id, "remaining": latest["remaining"]}
    event = publish_world_event(
        "village.ferry_post_collected", actor=mask,
        payload={"day": day, "hour": hour, "market_room_id": market.id,
                 "harbinger": False, "chronicle_eligible": False},
        consequence=consequence,
    )
    record_participation(mask, "courier_collections", calling="wanderer")
    return {"event_id": event["id"], "remaining": candidate["remaining"]}, None


def deliver(mask):
    riverside = _room(RIVERSIDE)
    if not _access(mask, riverside):
        return None, "Deliver an actual post parcel from Riverside Path."
    parcels = [o for o in mask.contents if o.key == PARCEL
               and hasattr(o.db.ferry_parcel, "get")]
    if not parcels:
        return None, "You must carry an actual sealed parcel from Market Lane."
    parcel = parcels[0]
    source = dict(parcel.db.ferry_parcel)
    day, hour = _clock()
    if day < int(source.get("day") or 0):
        return None, "This parcel is dated in a future village day."
    _, allowed, reason = courier_state.receive(
        riverside.db.ferry_manifest, day=day,
        account_id=mask.account.id, mask=mask.key,
        parcel_id=parcel.id, source_event_id=source.get("source_event_id"),
        delivery_event_id=1,
    )
    if not allowed:
        return None, reason

    def consequence(event):
        with transaction.atomic():
            if parcel.location != mask or parcel.key != PARCEL:
                raise RuntimeError("The actual parcel has left the courier.")
            latest, accepted, reason = courier_state.receive(
                riverside.db.ferry_manifest, day=day,
                account_id=mask.account.id, mask=mask.key,
                parcel_id=parcel.id,
                source_event_id=source.get("source_event_id"),
                delivery_event_id=event["id"],
            )
            if not accepted:
                raise RuntimeError(reason)
            riverside.db.ferry_manifest = latest
            received_parcel_id = int(parcel.id)
            parcel.delete()  # The physical parcel passes into ferry-post custody.
            return {"riverside_room_id": riverside.id,
                    "parcel_id": received_parcel_id,
                    "source_event_id": source["source_event_id"]}
    event = publish_world_event(
        "village.ferry_post_delivered", actor=mask,
        payload={"day": day, "hour": hour, "parcel_id": int(parcel.id),
                 "source_event_id": source["source_event_id"],
                 "harbinger": False, "chronicle_eligible": False},
        consequence=consequence,
    )
    role = active_calling(mask)
    if role:
        record_participation(mask, "courier_deliveries", calling=role)
    return {"event_id": event["id"], "source_event_id": source["source_event_id"]}, None
