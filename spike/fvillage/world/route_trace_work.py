"""Detective custody of a real Hound-altered treeline cord.

Uses the original landmark, Hound route event and canonical event ledger.
The record documents the alteration and its limits, never a solved crime.
"""
from __future__ import annotations

from collections.abc import Mapping
from django.db import transaction

from world import route_trace_custody
from world.callings import active_calling, record_participation
from world.discoveries import LANDMARKS, normalize as known_landmarks
from world.events import get_event_ledger, publish_world_event


def _site(mask):
    room = getattr(mask, "location", None)
    site = "red_cord"
    if (room is None or room.key != LANDMARKS[site]["room"]
            or not room.tags.has("ic", category="side")):
        return None, None
    matches = [
        obj for obj in room.contents
        if obj.key == LANDMARKS[site]["key"]
        and getattr(obj.db, "landmark_id", None) == site
        and obj.access(mask, "view", default=True)
    ]
    return room, matches[0] if len(matches) == 1 else None


def _clock():
    from world.route_work import _day_hour
    return _day_hour()


def _observed(mask, day):
    if not any(row["id"] == "red_cord"
               for row in known_landmarks(mask.db.landmark_discoveries)):
        return False
    try:
        latest = dict(mask.db.landmark_latest_view or {}).get("red_cord") or {}
        return type(latest.get("day")) is int and latest["day"] == day
    except (TypeError, ValueError, KeyError):
        return False


def _hound_source(cord, room, day, hour):
    caution = cord.db.route_caution
    if not isinstance(caution, Mapping):
        return None, "The cord has no signed Hound caution marker."
    source_id = caution.get("event_id")
    if type(source_id) is not int or source_id <= 0:
        return None, "The physical warning has no valid source event."
    source = get_event_ledger().get_event(source_id)
    if not isinstance(source, Mapping):
        return None, "The Hound's canonical source event is missing."
    actor = source.get("actor")
    payload = source.get("payload")
    effect = source.get("consequence")
    if not all(isinstance(x, Mapping) for x in (actor, payload, effect)):
        return None, "The Hound event has incomplete signed evidence."
    source_day, source_hour = payload.get("day"), payload.get("hour")
    if (source.get("kind") != "village.route_protected"
            or source.get("status") != "complete"
            or payload.get("site") != "red_cord"
            or payload.get("role") != "hound"
            or payload.get("action") != "protect"
            or payload.get("location") != room.key
            or type(source_day) is not int or source_day < 1
            or type(source_hour) is not int or not 0 <= source_hour <= 23
            or (source_day, source_hour) > (day, hour)
            or actor.get("account_id") != caution.get("account_id")
            or actor.get("mask") != caution.get("mask")
            or caution.get("day") != source_day
            or effect.get("cord_object_id") != cord.id
            or effect.get("site") != "red_cord"
            or effect.get("role") != "hound"
            or effect.get("action") != "protect"
            or effect.get("caution_marked") is not True):
        return None, "The physical caution marker disagrees with the signed Hound event."
    return source, None


def status(mask):
    room, cord = _site(mask)
    if cord is None:
        return "Visit the Northern Treeline to inspect its physical cord."
    return route_trace_custody.public_lines(cord.db.route_trace_custody)


def preserve(mask):
    account = getattr(mask, "account", None)
    if account is None:
        return None, "An ordinary logged-in character must preserve physical evidence."
    if active_calling(mask) != "detective":
        return None, "Only an active Detective can sign a trace-custody record."
    room, cord = _site(mask)
    if cord is None:
        return None, "The Detective must stand beside the original treeline cord."
    day, hour = _clock()
    if not _observed(mask, day):
        return None, "Examine the physical red cord here today before preserving traces."
    source, error = _hound_source(cord, room, day, hour)
    if error:
        return None, error
    source_id = source["id"]
    source_actor = source["actor"]
    source_payload = source["payload"]

    def propose(event_id):
        return route_trace_custody.preserve(
            cord.db.route_trace_custody,
            day=day, hour=hour,
            source_day=source_payload["day"],
            source_hour=source_payload["hour"],
            source_event_id=source_id,
            hound_account_id=source_actor["account_id"],
            hound_mask_id=source_actor["mask_id"],
            detective_account_id=account.id,
            detective_mask_id=mask.id,
            detective_mask=mask.key,
            cord_id=cord.id,
            event_id=event_id,
            observed_condition="tied_caution",
        )

    _preview, accepted, error = propose(1)
    if not accepted:
        return None, error

    def consequence(event):
        with transaction.atomic():
            if (_clock() != (day, hour) or mask.location != room
                    or cord.location != room or mask.account != account
                    or active_calling(mask) != "detective"
                    or not _observed(mask, day)):
                raise RuntimeError("The Detective's physical examination changed before signing.")
            current, problem = _hound_source(cord, room, day, hour)
            if problem or current["id"] != source_id:
                raise RuntimeError("The original Hound evidence changed before signing.")
            changed, okay, why = propose(event["id"])
            if not okay:
                raise RuntimeError(why)
            cord.db.route_trace_custody = changed
            return {
                "cord_object_id": cord.id,
                "hound_source_event_id": source_id,
                "hound_account_id": source_actor["account_id"],
                "detective_account_id": account.id,
                "late_arrival": changed["late_arrival"],
                "observed_condition": changed["observed_condition"],
            }

    event = publish_world_event(
        "village.route_trace_preserved", actor=mask,
        payload={
            "site": "red_cord", "day": day, "hour": hour,
            "location": room.key, "cord_object_id": cord.id,
            "hound_source_event_id": source_id,
            "professional_calling": "detective",
            "harbinger": False, "chronicle_eligible": False,
        },
        consequence=consequence,
    )
    record_participation(mask, "route_trace_preserved", calling="detective")
    return {"event_id": event["id"], "source_event_id": source_id,
            "lines": route_trace_custody.public_lines(cord.db.route_trace_custody)}, None
