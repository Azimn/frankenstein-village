"""Finite bridge fittings and completed-ledger source proof for EDGE-20/23.

This is a pure rule layer. Evennia owns the physical table, carried objects,
original route observations, clock and event ledger. Saved Attributes are
read-only indexes and never independent evidence of a repaired route.
"""
from __future__ import annotations

from collections.abc import Mapping

KINDS = ("span", "cord")
DAILY = 2
NAMES = {
    "span": "a forged bridge-span fitting",
    "cord": "a forged red-cord anchor",
}
ROOMS = {"span": "The Old Stone Bridge", "cord": "The Northern Treeline"}
SOURCES = {"span": "village.river_gauge_witnessed",
           "cord": "village.route_protected"}


def positive(value):
    return type(value) is int and value > 0


def hour_valid(value):
    return type(value) is int and 0 <= value <= 23


def record(value):
    return value if isinstance(value, Mapping) else {}


def stock(raw, day):
    """Return (stock, error), never replenish corrupt or backdated records."""
    if not positive(day):
        return None, "A valid village day is required."
    if raw is None:
        return {"day": day, "remaining": {key: DAILY for key in KINDS}}, None
    if not isinstance(raw, Mapping) or not positive(raw.get("day")):
        return None, "The finite fitting stock needs source review."
    old_day = raw["day"]
    if day < old_day:
        return None, "The fitting table cannot reopen an earlier day."
    if day > old_day:
        return {"day": day, "remaining": {key: DAILY for key in KINDS}}, None
    remaining = raw.get("remaining")
    if (not isinstance(remaining, Mapping)
            or any(type(remaining.get(k)) is not int
                   or not 0 <= remaining[k] <= DAILY for k in KINDS)):
        return None, "The finite fitting stock needs source review."
    return {"day": day, "remaining": {k: remaining[k] for k in KINDS}}, None


def withdraw(raw, day, kind):
    if kind not in KINDS:
        return None, "Choose span or cord."
    state, error = stock(raw, day)
    if error:
        return None, error
    if state["remaining"][kind] < 1:
        return None, "No matching physical fittings remain today."
    state["remaining"][kind] -= 1
    return state, None


def _event(get_event, ident, kind):
    if not positive(ident):
        return {}
    try:
        event = record(get_event(ident))
    except Exception:
        return {}
    if (event.get("id") != ident or type(event.get("id")) is not int
            or event.get("status") != "complete" or event.get("kind") != kind):
        return {}
    return event


def verified_forge(item, get_event, *, kind, table_id, day):
    """Verify a carried fitting against its original finite workshop receipt."""
    item = record(item)
    if (kind not in KINDS or not positive(table_id) or not positive(day)
            or not positive(item.get("item_id"))
            or not positive(item.get("forge_event_id"))
            or not positive(item.get("forge_day"))
            or item["forge_day"] > day):
        return False
    event = _event(get_event, item["forge_event_id"],
                   "village.route_fitting_forged")
    actor, payload, result = (record(event.get(k))
                              for k in ("actor", "payload", "consequence"))
    return bool(
        event and positive(actor.get("account_id"))
        and positive(actor.get("mask_id"))
        and isinstance(actor.get("mask"), str) and actor["mask"]
        and payload.get("calling") == "smith"
        and payload.get("kind") == kind
        and payload.get("location") == "Market Lane"
        and payload.get("day") == item["forge_day"]
        and hour_valid(payload.get("hour"))
        and payload.get("table_id") == table_id
        and result.get("item_id") == item["item_id"]
        and result.get("table_id") == table_id
        and result.get("kind") == kind
        and type(result.get("remaining")) is int
        and 0 <= result["remaining"] < DAILY
    )


def verified_install(saved, get_event, *, kind, target_id, room_id,
                     table_id, day):
    """Validate all three completed original events, not a saved 'safe' flag."""
    saved = record(saved)
    if (kind not in KINDS or saved.get("kind") != kind
            or not all(positive(saved.get(k)) for k in (
                "install_event_id", "source_event_id", "forge_event_id",
                "item_id", "source_object_id", "source_room_id",
                "target_id", "target_room_id", "day", "smith_account_id",
                "source_account_id"))
            or not hour_valid(saved.get("hour"))
            or saved["target_id"] != target_id
            or saved["target_room_id"] != room_id
            or not positive(day) or saved["day"] > day
            or saved["smith_account_id"] == saved["source_account_id"]):
        return False
    install = _event(get_event, saved["install_event_id"],
                     "village.route_fitting_installed")
    source = _event(get_event, saved["source_event_id"], SOURCES[kind])
    forge = _event(get_event, saved["forge_event_id"],
                   "village.route_fitting_forged")
    if not install or not source or not forge:
        return False
    ia, ip, ic = (record(install.get(k)) for k in
                  ("actor", "payload", "consequence"))
    sa, sp, sc = (record(source.get(k)) for k in
                  ("actor", "payload", "consequence"))
    fa, fp, fc = (record(forge.get(k)) for k in
                  ("actor", "payload", "consequence"))
    d, h = saved["day"], saved["hour"]
    if not (
        ia.get("account_id") == saved["smith_account_id"]
        and positive(ia.get("mask_id"))
        and isinstance(ia.get("mask"), str) and ia["mask"]
        and sa.get("account_id") == saved["source_account_id"]
        and positive(sa.get("mask_id"))
        and sa.get("account_id") != ia.get("account_id")
        and sa.get("mask_id") != ia.get("mask_id")
        and isinstance(sa.get("mask"), str) and bool(sa["mask"])
        and positive(fa.get("account_id"))
        and positive(fa.get("mask_id"))
        and isinstance(fa.get("mask"), str) and bool(fa["mask"])
        and fp.get("calling") == "smith"
        and fp.get("kind") == kind
        and fp.get("location") == "Market Lane"
        and positive(fp.get("day")) and hour_valid(fp.get("hour"))
        and fp.get("table_id") == table_id
        and fc.get("item_id") == saved["item_id"]
        and fc.get("table_id") == table_id
        and fc.get("kind") == kind
        and type(fc.get("remaining")) is int
        and 0 <= fc["remaining"] < DAILY
        and ip.get("calling") == "smith"
        and ip.get("kind") == kind
        and ip.get("location") == ROOMS[kind]
        and ip.get("day") == d and ip.get("hour") == h
        and ip.get("target_id") == target_id
        and ip.get("target_room_id") == room_id
        and ip.get("source_event_id") == saved["source_event_id"]
        and ip.get("forge_event_id") == saved["forge_event_id"]
        and ip.get("item_id") == saved["item_id"]
        and ic.get("installed") is True
        and ic.get("target_id") == target_id
        and ic.get("target_room_id") == room_id
        and ic.get("source_event_id") == saved["source_event_id"]
        and ic.get("forge_event_id") == saved["forge_event_id"]
        and ic.get("consumed_item_id") == saved["item_id"]
        and sp.get("day") == d and hour_valid(sp.get("hour"))
        and sp["hour"] <= h
        and (fp["day"], fp["hour"]) <= (d, h)
        and positive(sp.get("object_id") if kind == "span" else
                     sc.get("cord_object_id"))
    ):
        return False
    if kind == "span":
        return bool(
            sp.get("calling") == "wanderer"
            and sp.get("location") == "Riverside Path"
            and sp.get("object_id") == saved["source_object_id"]
            and sp.get("room_id") == saved["source_room_id"]
            and sc.get("gauge_object_id") == saved["source_object_id"]
            and sc.get("room_id") == saved["source_room_id"]
            and sc.get("account_id") == sa["account_id"]
            and sc.get("witness_event_id") == saved["source_event_id"]
        )
    return bool(
        sp.get("role") == "hound" and sp.get("action") == "protect"
        and sp.get("site") == "red_cord"
        and sp.get("location") == "The Northern Treeline"
        and sc.get("cord_object_id") == saved["source_object_id"]
        and sc.get("square_room_id") == saved["source_room_id"]
        and sc.get("site") == "red_cord"
        and sc.get("role") == "hound"
        and sc.get("action") == "protect"
        and sc.get("caution_marked") is True
    )


def verified_post_install_view(latest, *, day, hour, install_day,
                               install_hour, install_event_id, cord_id):
    """Require a firsthand view of this exact installed physical cord.

    A look at the original hazard before Smith installation cannot count
    as an inspection of the repaired object, even within the same hour.
    """
    latest = record(latest)
    return bool(
        positive(day) and positive(install_day)
        and hour_valid(hour) and hour_valid(install_hour)
        and positive(install_event_id) and positive(cord_id)
        and type(latest.get("day")) is int and latest["day"] == day
        and hour_valid(latest.get("hour"))
        and (latest["day"], latest["hour"]) >= (install_day, install_hour)
        and latest["hour"] <= hour
        and type(latest.get("route_fitting_install_event_id")) is int
        and latest["route_fitting_install_event_id"] == install_event_id
        and type(latest.get("route_fitting_cord_id")) is int
        and latest["route_fitting_cord_id"] == cord_id
    )

def verified_test(saved, test, get_event, *, cord_id, room_id, table_id, day):
    if not verified_install(saved, get_event, kind="cord", target_id=cord_id,
                            room_id=room_id, table_id=table_id, day=day):
        return False
    test = record(test)
    if (not positive(test.get("event_id"))
            or test.get("install_event_id") != saved["install_event_id"]):
        return False
    event = _event(get_event, test["event_id"], "village.route_fitting_tested")
    actor, payload, effect = (record(event.get(k))
                              for k in ("actor", "payload", "consequence"))
    return bool(event and positive(actor.get("account_id"))
                and actor.get("account_id") != saved["smith_account_id"]
                and positive(actor.get("mask_id"))
                and payload.get("calling") == "hound"
                and payload.get("kind") == "cord"
                and payload.get("location") == "The Northern Treeline"
                and payload.get("target_id") == cord_id
                and payload.get("target_room_id") == room_id
                and payload.get("install_event_id") == saved["install_event_id"]
                and positive(payload.get("day"))
                and payload["day"] >= saved["day"] and payload["day"] <= day
                and hour_valid(payload.get("hour"))
                and (payload["day"], payload["hour"]) >=
                    (saved["day"], saved["hour"])
                and effect.get("tested") is True
                and effect.get("target_id") == cord_id
                and effect.get("install_event_id") == saved["install_event_id"])
