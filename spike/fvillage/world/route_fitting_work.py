"""Ordinary-player physical bridge and cord fitting work for EDGE-20/23.

Existing Market Lane table, original gauge/cord, WorldEventLedger, clock,
Calling state and physical Evennia objects are the sole authorities.
"""
from __future__ import annotations

from django.db import transaction
from evennia import create_object
from evennia.scripts.models import ScriptDB
from evennia.utils import search

from world import bridge_work, route_work, route_fittings, river_evidence
from world.callings import active_calling, record_participation
from world.events import get_event_ledger, publish_world_event
from world.discoveries import LANDMARKS


def _clock():
    try:
        c = ScriptDB.objects.get(db_key="village_time")
        return int(c.db.day or 1), int(
            c.db.hour if c.db.hour is not None else 21)
    except ScriptDB.DoesNotExist:
        return 1, 21


def _ledger(event_id):
    return get_event_ledger().get_event(event_id)


def _table():
    return bridge_work._market_supply()


def _room(key):
    rooms = [r for r in search.search_object(key)
             if r.key == key and r.location is None
             and r.tags.has("ic", category="side")]
    return rooms[0] if len(rooms) == 1 else None


def _target(kind):
    if kind == "span":
        room = bridge_work._bridge()
        return (room, room) if room else (None, None)
    if kind != "cord":
        return None, None
    room = _room("The Northern Treeline")
    if not room:
        return None, None
    spec = LANDMARKS["red_cord"]
    cords = [obj for obj in room.contents
             if obj.key == spec["key"]
             and getattr(obj.db, "landmark_id", None) == "red_cord"]
    return (room, cords[0]) if len(cords) == 1 else (None, None)


def _source(kind, day, hour):
    """Recheck the existing completed firsthand event and original object."""
    if kind == "span":
        room = _room("Riverside Path")
        if not room:
            return None
        spec = LANDMARKS["river_gauge"]
        gauges = [obj for obj in room.contents
                  if obj.key == spec["key"]
                  and getattr(obj.db, "landmark_id", None) == "river_gauge"]
        if len(gauges) != 1:
            return None
        gauge = gauges[0]
        witness = river_evidence.normalize(gauge.db.river_evidence)["witness"]
        if (not witness or witness["day"] != day
                or witness["hour"] > hour
                or not route_work._verified_river_source(gauge, room, witness)):
            return None
        return {"event_id": witness["event_id"],
                "account_id": witness["account_id"],
                "mask_id": witness["mask_id"],
                "object_id": gauge.id, "room_id": room.id}
    if kind == "cord":
        square = route_work._square()
        if not square:
            return None
        proof = route_work._signed_hound_source(square, day, hour)
        if not proof:
            return None
        return {"event_id": proof["source_event_id"],
                "account_id": proof["source_account_id"],
                "mask_id": proof["source_mask_id"],
                "object_id": proof["source_cord_id"],
                "room_id": square.id}
    return None


def _carried(mask, kind, table_id, day, hour):
    return [obj for obj in mask.contents
            if obj.key == route_fittings.NAMES[kind]
            and obj.db.route_fitting_kind == kind
            and route_fittings.verified_forge(
                {"item_id": obj.id,
                 "forge_event_id": obj.db.route_fitting_forge_event,
                 "forge_day": obj.db.route_fitting_forge_day},
                _ledger, kind=kind, table_id=table_id, day=day,
                hour=hour)]


def _verified_target(kind, room, target, table, day, hour):
    return route_fittings.verified_install(
        target.db.route_fitting_install, _ledger, kind=kind,
        target_id=target.id, room_id=room.id,
        table_id=table.id, day=day, hour=hour)


def status():
    table = _table()
    day, hour = _clock()
    lines = ["|wPhysical route fittings|n",
             "A signed survey is evidence, not a repair or a guarantee of safety."]
    for kind in route_fittings.KINDS:
        room, target = _target(kind)
        if not table or not room or not target:
            lines.append(f"{kind}: original site or civic material table unavailable.")
            continue
        raw = target.db.route_fitting_install
        valid = _verified_target(kind, room, target, table, day, hour)
        if valid:
            lines.append(f"{kind}: physically fitted, completed-ledger verified. "
                         f"Signed installation {raw['install_event_id']}.")
            if kind == "span":
                lines.append("The repaired bridge inspection span can be crossed "
                             "with |wbridgefit cross|n from the bridge.")
            else:
                tested = route_fittings.verified_test(
                    raw, target.db.route_fitting_test, _ledger,
                    cord_id=target.id, room_id=room.id,
                    table_id=table.id, day=day, hour=hour)
                lines.append("The local red-cord anchor was "
                             + ("independently Hound-tested." if tested
                                else "not yet independently tested."))
        elif raw is not None:
            lines.append(f"{kind}: unsupported saved fitting, no public repair claim.")
        else:
            lines.append(f"{kind}: no installed physical fitting.")
    lines.append(
        "Smith: |wbridgefit forge span|n or |wbridgefit forge cord|n "
        "at Market Lane's civic table, then carry the real fitting to its site. "
        "Wanderer: inspect the Riverside gauge and |wsurvey gauge|n today. "
        "Hound: inspect the Northern Treeline cord and |wsurvey protect|n today. "
        "An independent Smith uses |wbridgefit install span|n at the bridge "
        "or |wbridgefit install cord|n at the treeline. "
        "A Hound may then |wbridgefit test cord|n at the original cord."
    )
    return "\n".join(lines)


def forge(mask, kind):
    if kind not in route_fittings.KINDS:
        return None, "Choose span or cord."
    if active_calling(mask) != "smith" or not getattr(mask, "account", None):
        return None, "An active Smith on a logged-in account must forge this fitting."
    room = getattr(mask, "location", None)
    table = _table()
    if (not room or room.key != "Market Lane" or not table
            or table.location != room
            or not room.tags.has("ic", category="side")):
        return None, "Visit the physical civic material table in Market Lane."
    from world.market_work import supply_held
    if supply_held():
        return None, "Disputed market weights have stopped civic material supply."
    day, hour = _clock()
    _candidate, error = route_fittings.withdraw(
        table.db.route_fitting_stock, day, kind)
    if error:
        return None, error
    if any(obj.db.route_fitting_kind in route_fittings.KINDS
           for obj in mask.contents):
        return None, "Carry only one unfinished physical route fitting."
    account_id, mask_id = mask.account.id, mask.id

    def consequence(event):
        with transaction.atomic():
            if (mask.location != room or table.location != room
                    or not mask.account or mask.account.id != account_id
                    or mask.id != mask_id or active_calling(mask) != "smith"
                    or _clock() != (day, hour) or supply_held()):
                raise RuntimeError("The Smith, table, supply or village clock changed.")
            if any(obj.db.route_fitting_kind in route_fittings.KINDS
                   for obj in mask.contents):
                raise RuntimeError("The Smith already carries a fitting.")
            updated, issue = route_fittings.withdraw(
                table.db.route_fitting_stock, day, kind)
            if issue:
                raise RuntimeError(issue)
            item = create_object(
                "typeclasses.objects.Object",
                key=route_fittings.NAMES[kind], location=mask,
                aliases=["route fitting", kind + " fitting"])
            item.db.route_fitting_kind = kind
            item.db.route_fitting_forge_event = event["id"]
            item.db.route_fitting_forge_day = day
            item.db.desc = (
                "A finite, portable Smith-forged physical component. "
                "Its original completed Market Lane receipt is required "
                "before any installation; it may be carried or given.")
            table.db.route_fitting_stock = updated
            record_participation(mask, "route_fittings_forged", calling="smith")
            return {"item_id": item.id, "table_id": table.id,
                    "kind": kind, "remaining": updated["remaining"][kind]}

    event = publish_world_event(
        "village.route_fitting_forged", actor=mask,
        payload={"kind": kind, "calling": "smith",
                 "location": room.key, "table_id": table.id,
                 "day": day, "hour": hour,
                 "harbinger": False, "chronicle_eligible": False},
        consequence=consequence)
    return {"event_id": event["id"], "kind": kind}, None


def install(mask, kind):
    if kind not in route_fittings.KINDS:
        return None, "Choose span or cord."
    if active_calling(mask) != "smith" or not getattr(mask, "account", None):
        return None, "An active Smith must install the physical fitting."
    room, target = _target(kind)
    table = _table()
    if not room or not target or not table or mask.location != room:
        return None, "Stand at the original bridge or treeline fitting site."
    day, hour = _clock()
    if target.db.route_fitting_install is not None:
        return None, "The fitting is installed already or its saved record needs review."
    source = _source(kind, day, hour)
    if not source:
        return None, "A firsthand completed Wanderer gauge or Hound cord source is required today."
    if source["account_id"] == mask.account.id or source["mask_id"] == mask.id:
        return None, "The Smith and original field observer must be independent accounts."
    items = _carried(mask, kind, table.id, day, hour)
    if not items:
        return None, "Carry a genuine Smith-forged fitting from the Market Lane table."
    item = items[0]
    account_id, mask_id = mask.account.id, mask.id
    forge_id = item.db.route_fitting_forge_event

    def consequence(event):
        with transaction.atomic():
            if (mask.location != room or target.location not in (room, None)
                    or not mask.account or mask.account.id != account_id
                    or mask.id != mask_id or active_calling(mask) != "smith"
                    or _clock() != (day, hour)
                    or target.db.route_fitting_install is not None):
                raise RuntimeError("The original site, Calling, clock or fitting changed.")
            current_source = _source(kind, day, hour)
            if current_source != source:
                raise RuntimeError("The completed field source changed during installation.")
            if item.location != mask or item not in _carried(
                    mask, kind, table.id, day, hour):
                raise RuntimeError("The physical fitting or its forge receipt changed.")
            saved = {"kind": kind, "install_event_id": event["id"],
                     "source_event_id": source["event_id"],
                     "forge_event_id": forge_id, "item_id": item.id,
                     "source_object_id": source["object_id"],
                     "source_room_id": source["room_id"],
                     "target_id": target.id, "target_room_id": room.id,
                     "day": day, "hour": hour,
                     "smith_account_id": account_id,
                     "source_account_id": source["account_id"]}
            target.db.route_fitting_install = saved
            item.delete()
            record_participation(mask, "route_fittings_installed", calling="smith")
            return {"installed": True, "target_id": target.id,
                    "target_room_id": room.id,
                    "source_event_id": source["event_id"],
                    "forge_event_id": forge_id, "consumed_item_id": saved["item_id"]}

    event = publish_world_event(
        "village.route_fitting_installed", actor=mask,
        payload={"kind": kind, "calling": "smith",
                 "location": room.key, "day": day, "hour": hour,
                 "target_id": target.id, "target_room_id": room.id,
                 "source_event_id": source["event_id"],
                 "forge_event_id": forge_id, "item_id": item.id,
                 "harbinger": False, "chronicle_eligible": False},
        consequence=consequence)
    return {"event_id": event["id"], "source_event_id": source["event_id"]}, None


def test_cord(mask):
    if active_calling(mask) != "hound" or not getattr(mask, "account", None):
        return None, "An active Hound must test the repaired physical cord."
    room, cord = _target("cord")
    table = _table()
    if not room or not cord or not table or mask.location != room:
        return None, "Inspect the original red cord at the Northern Treeline."
    day, hour = _clock()
    saved = cord.db.route_fitting_install
    if not _verified_target("cord", room, cord, table, day, hour):
        return None, "There is no completed signed Smith cord installation to test."
    if saved["smith_account_id"] == mask.account.id:
        return None, "The independent Hound must use a different account."
    if cord.db.route_fitting_test is not None:
        return None, "The repair was tested already or needs source review."
    try:
        latest = dict(mask.db.landmark_latest_view or {}).get("red_cord") or {}
    except (TypeError, ValueError):
        latest = {}
    if not route_fittings.verified_post_install_view(
            latest, day=day, hour=hour, install_day=saved["day"],
            install_hour=saved["hour"],
            install_event_id=saved["install_event_id"], cord_id=cord.id):
        return None, "Examine the original repaired red cord after installation."
    account_id = mask.account.id
    install_id = saved["install_event_id"]

    def consequence(event):
        with transaction.atomic():
            if (mask.location != room or cord.location != room
                    or not mask.account or mask.account.id != account_id
                    or active_calling(mask) != "hound" or _clock() != (day, hour)
                    or cord.db.route_fitting_test is not None
                    or not _verified_target("cord", room, cord, table, day, hour)
                    or cord.db.route_fitting_install["install_event_id"] != install_id):
                raise RuntimeError("The original repaired cord or Hound changed.")
            try:
                recent = dict(mask.db.landmark_latest_view or {}).get("red_cord") or {}
            except (TypeError, ValueError):
                recent = {}
            if not route_fittings.verified_post_install_view(
                    recent, day=day, hour=hour, install_day=saved["day"],
                    install_hour=saved["hour"],
                    install_event_id=install_id, cord_id=cord.id):
                raise RuntimeError("The Hound's postrepair physical inspection changed.")
            cord.db.route_fitting_test = {
                "event_id": event["id"], "install_event_id": install_id}
            record_participation(mask, "route_fittings_tested", calling="hound")
            return {"tested": True, "target_id": cord.id,
                    "install_event_id": install_id}

    event = publish_world_event(
        "village.route_fitting_tested", actor=mask,
        payload={"kind": "cord", "calling": "hound", "location": room.key,
                 "day": day, "hour": hour, "target_id": cord.id,
                 "target_room_id": room.id, "install_event_id": install_id,
                 "harbinger": False, "chronicle_eligible": False},
        consequence=consequence)
    return {"event_id": event["id"]}, None


def cross(mask):
    """An optional real movement across the repaired inspection span.

    Normal public west exits remain available. This additional crossing
    action only becomes possible after physical signed installation.
    """
    room, target = _target("span")
    table = _table()
    destination = _room("Riverside Path")
    day, hour = _clock()
    if (not getattr(mask, "account", None) or not room or not target
            or not table or not destination or mask.location != room):
        return None, "Stand at the Old Stone Bridge to cross its inspection span."
    if not _verified_target("span", room, target, table, day, hour):
        return None, "The inspection span has not been physically fitted and verified."
    if not mask.move_to(destination):
        return None, "The repaired inspection crossing could not be traversed."
    return {"location": destination.key}, None
