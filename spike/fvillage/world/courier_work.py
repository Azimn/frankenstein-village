"""Real Market Lane to Riverside Path courier deliveries for village Wanderers."""
from __future__ import annotations
from django.db import transaction
from evennia import create_object
from evennia.scripts.models import ScriptDB
from evennia.utils import search
from world import courier_state
from world.callings import active_calling, record_participation
from world.events import get_event_ledger, publish_world_event

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
        "A Merchant can consign one of the same finite parcels with |wcourier consign|n",
        "in Market Lane. A different Wanderer uses |wcourier accept|n there.",
        "Unaccepted freight remains physically available to another Wanderer.",
    ]
    if last:
        lines.append(
            f"Latest delivery by {last['mask']} on day {last['day']} "
            f"(world event {last['delivery_event_id']}).")
        freight = last.get("freight")
        if freight:
            lines.append(
                f"Freight consignment {freight['consignment_event_id']} "
                f"(Merchant account {freight['merchant_account_id']}), "
                f"Wanderer acceptance {freight['accept_event_id']} "
                f"(account {freight['wanderer_account_id']}). "
                "These are signed custody claims, not proof of parcel contents."
            )
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
            parcel.locks.add("get:false()")  # Custody requires courier accept, not get.
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



def _freight_sources(parcel, contract, *, accepted=False):
    """Check signed physical custody against the one canonical event ledger."""
    if contract is None:
        return False
    ledger = get_event_ledger()
    source = ledger.get_event(contract["consignment_event_id"])
    actor = (source or {}).get("actor") or {}
    payload = (source or {}).get("payload") or {}
    result = (source or {}).get("consequence") or {}
    if (not source or source.get("status") != "complete"
            or source.get("kind") != "village.freight_consigned"
            or actor.get("account_id") != contract["merchant_account_id"]
            or payload.get("professional_calling") != "merchant"
            or payload.get("market_room_id") != parcel.db.ferry_parcel.get("origin_room_id")
            or result.get("parcel_id") != parcel.id):
        return False
    if not accepted:
        return True
    handoff = ledger.get_event(contract["accept_event_id"])
    actor = (handoff or {}).get("actor") or {}
    payload = (handoff or {}).get("payload") or {}
    result = (handoff or {}).get("consequence") or {}
    return bool(
        handoff and handoff.get("status") == "complete"
        and handoff.get("kind") == "village.freight_accepted"
        and actor.get("account_id") == contract["wanderer_account_id"]
        and payload.get("professional_calling") == "wanderer"
        and payload.get("source_event_id") == contract["consignment_event_id"]
        and payload.get("parcel_id") == parcel.id
        and result.get("parcel_id") == parcel.id
    )



def _ordinary_source(parcel, source):
    """Prevent an altered Merchant consignment from masquerading as solo mail."""
    event_id = source.get("source_event_id")
    if isinstance(event_id, bool) or not isinstance(event_id, int) or event_id < 1:
        return False
    event = get_event_ledger().get_event(event_id)
    return bool(
        event and event.get("status") == "complete"
        and event.get("kind") == "village.ferry_post_collected"
        and (event.get("actor") or {}).get("account_id") == source.get("collector_account_id")
        and (event.get("payload") or {}).get("market_room_id") == source.get("origin_room_id")
        and (event.get("payload") or {}).get("day") == source.get("day")
        and (event.get("consequence") or {}).get("parcel_id") == parcel.id
    )


def consign(mask):
    """Merchant reserves one existing postbag slot as real physical freight."""
    market = _room(MARKET)
    if not _access(mask, market) or active_calling(mask) != "merchant":
        return None, "An active Merchant must consign freight in Market Lane."
    day, hour = _clock()
    candidate, allowed = courier_state.issue(market.db.ferry_post_stock, day)
    if not allowed:
        return None, "The shared Market postbag is depleted for today."

    def consequence(event):
        with transaction.atomic():
            if mask.location != market or active_calling(mask) != "merchant":
                raise RuntimeError("The Merchant left the Market or changed Calling.")
            if _clock() != (day, hour):
                raise RuntimeError("Village time advanced before the consignment.")
            latest, ok = courier_state.issue(market.db.ferry_post_stock, day)
            if not ok:
                raise RuntimeError("The finite Market postbag was already depleted.")
            parcel = create_object(
                "typeclasses.objects.Object", key=PARCEL,
                location=market, aliases=["mail parcel", "ferry parcel", "freight parcel"],
            )
            parcel.db.ferry_parcel = {
                "day": day, "origin_room_id": market.id,
                "source_event_id": event["id"],
                "collector_account_id": None,
                "freight": {
                    "merchant_account_id": mask.account.id,
                    "consignment_event_id": event["id"],
                },
            }
            parcel.db.desc = (
                "A sealed freight parcel consigned by a Merchant. "
                "An active Wanderer can use courier accept in Market Lane "
                "to take signed custody for Riverside Path."
            )
            market.db.ferry_post_stock = latest
            return {"parcel_id": parcel.id, "remaining": latest["remaining"]}

    event = publish_world_event(
        "village.freight_consigned", actor=mask,
        payload={"day": day, "hour": hour, "market_room_id": market.id,
                 "professional_calling": "merchant",
                 "harbinger": False, "chronicle_eligible": False},
        consequence=consequence,
    )
    record_participation(mask, "freight_consignments", calling="merchant")
    return {"event_id": event["id"], "remaining": candidate["remaining"]}, None


def accept_freight(mask):
    """A different Wanderer physically takes custody of Merchant freight."""
    market = _room(MARKET)
    if not _access(mask, market) or active_calling(mask) != "wanderer":
        return None, "An active Wanderer must accept freight in Market Lane."
    if any(obj.db.ferry_parcel for obj in mask.contents):
        return None, "You already carry a post parcel. Deliver or hand it over."
    parcels = [
        obj for obj in market.contents
        if obj.key == PARCEL and hasattr(obj.db.ferry_parcel, "get")
        and obj.db.ferry_parcel.get("freight") is not None
    ]
    if not parcels:
        return None, "No physical Merchant freight parcel awaits acceptance here."
    parcel = parcels[0]
    source = dict(parcel.db.ferry_parcel)
    contract = courier_state.freight_contract(source.get("freight"))
    if (contract is None or contract["merchant_account_id"] == mask.account.id
            or source.get("source_event_id") != contract["consignment_event_id"]
            or not _freight_sources(parcel, contract)):
        return None, "The Merchant's signed freight source cannot be verified."
    day, hour = _clock()
    if day < int(source.get("day") or 0):
        return None, "This freight is dated in a future village day."

    def consequence(event):
        with transaction.atomic():
            if (parcel.location != market or mask.location != market
                    or active_calling(mask) != "wanderer"):
                raise RuntimeError("The freight or Wanderer left the Market.")
            if _clock() != (day, hour):
                raise RuntimeError("Village time advanced before custody acceptance.")
            if not _freight_sources(parcel, contract):
                raise RuntimeError("The Merchant consignment lost its signed source.")
            if not parcel.move_to(mask, quiet=True):
                raise RuntimeError("The physical freight could not change hands.")
            updated = dict(source)
            updated["freight"] = {
                **contract, "wanderer_account_id": mask.account.id,
                "accept_event_id": event["id"],
            }
            updated["collector_account_id"] = mask.account.id
            parcel.db.ferry_parcel = updated
            return {"parcel_id": parcel.id,
                    "consignment_event_id": contract["consignment_event_id"]}

    event = publish_world_event(
        "village.freight_accepted", actor=mask,
        payload={"day": day, "hour": hour, "parcel_id": parcel.id,
                 "source_event_id": contract["consignment_event_id"],
                 "professional_calling": "wanderer",
                 "harbinger": False, "chronicle_eligible": False},
        consequence=consequence,
    )
    record_participation(mask, "freight_acceptances", calling="wanderer")
    return {"event_id": event["id"],
            "consignment_event_id": contract["consignment_event_id"]}, None


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
    freight = None
    if "freight" in source:
        freight = courier_state.freight_contract(source["freight"], accepted=True)
        if (freight is None or active_calling(mask) != "wanderer"
                or freight["wanderer_account_id"] != mask.account.id
                or freight["consignment_event_id"] != source.get("source_event_id")
                or not _freight_sources(parcel, freight, accepted=True)):
            return None, "Freight needs its original distinct Merchant and Wanderer receipts."
    elif not _ordinary_source(parcel, source):
        return None, "The ordinary parcel's signed collection source cannot be verified."
    _, allowed, reason = courier_state.receive(
        riverside.db.ferry_manifest, day=day,
        account_id=mask.account.id, mask=mask.key,
        parcel_id=parcel.id, source_event_id=source.get("source_event_id"),
        delivery_event_id=1, freight=freight,
    )
    if not allowed:
        return None, reason

    def consequence(event):
        with transaction.atomic():
            if parcel.location != mask or parcel.key != PARCEL:
                raise RuntimeError("The actual parcel has left the courier.")
            if freight is not None and (
                    active_calling(mask) != "wanderer"
                    or not _freight_sources(parcel, freight, accepted=True)):
                raise RuntimeError("The signed freight custody chain is invalid.")
            if freight is None and not _ordinary_source(parcel, source):
                raise RuntimeError("The ordinary collection source is invalid.")
            latest, accepted, reason = courier_state.receive(
                riverside.db.ferry_manifest, day=day,
                account_id=mask.account.id, mask=mask.key,
                parcel_id=parcel.id,
                source_event_id=source.get("source_event_id"),
                delivery_event_id=event["id"], freight=freight,
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
                 "freight_accept_event_id": (
                     freight["accept_event_id"] if freight else None),
                 "harbinger": False, "chronicle_eligible": False},
        consequence=consequence,
    )
    role = active_calling(mask)
    if role:
        record_participation(mask, "courier_deliveries", calling=role)
    return {"event_id": event["id"], "source_event_id": source["source_event_id"]}, None
