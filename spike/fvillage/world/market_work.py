"""Authenticated, physical three-Calling market standards work.

The crooked scale is authoritative scenery. A personal firsthand view must
occur today before signing a public decision. Event provenance is written to
the existing world event ledger, not an independent simulation scheduler.
"""
from __future__ import annotations

from django.db import transaction
from evennia.scripts.models import ScriptDB
from evennia.utils import search

from world import market_standards, forensic_scale
from world.callings import active_calling, record_participation
from world.events import publish_world_event, get_event_ledger

MARKET = "Market Lane"
SCALE = "a crooked market scale"
ACTION_ROLE = {
    "honor": "merchant", "hold": "merchant", "release": "merchant",
    "calibrate": "smith", "attest": "chronicler", "inspect": "detective",
}


def market_room():
    return next(
        (room for room in search.search_object(MARKET)
         if room.key == MARKET and room.location is None
         and room.tags.has("ic", category="side")),
        None,
    )


def clock():
    try:
        script = ScriptDB.objects.get(db_key="village_time")
        return int(script.db.day or 1), int(
            script.db.hour if script.db.hour is not None else 21
        )
    except ScriptDB.DoesNotExist:
        return 1, 21


def state_lines():
    room = market_room()
    if not room:
        return "The Market Lane standards board is missing."
    day, _hour = clock()
    lines = market_standards.public_lines(room.db.market_standards, day)
    scale = next((o for o in room.contents if o.key == SCALE
                  and o.db.landmark_id == "market_scale"), None)
    if scale:
        # Public readback must never create a missing ledger or trust a stored
        # row without the original completed Smith and Detective events.
        try:
            ledger = ScriptDB.objects.get(db_key="world_event_ledger")
        except ScriptDB.DoesNotExist:
            ledger = None
        lines.append(forensic_scale.public_lines(
            scale.db.forensic_inspections, day,
            event_lookup=ledger.get_event if ledger else None,
            scale_id=scale.id, market_id=room.id,
        ))
    return "\n".join(lines)


def supply_held():
    room = market_room()
    if room is None:
        return False
    day, _hour = clock()
    return market_standards.suspended(room.db.market_standards, day)


def witnessed_scale_today(mask, day):
    room = market_room()
    if room is None or mask.location != room:
        return False
    scale = next((
        obj for obj in room.contents
        if obj.key == SCALE
        and obj.db.landmark_id == "market_scale"
        and obj.access(mask, "view", default=True)
    ), None)
    if not scale:
        return False
    try:
        recent = dict(mask.db.landmark_latest_view or {}).get("market_scale") or {}
        return int(recent.get("day") or 0) == int(day)
    except (ValueError, TypeError, OverflowError):
        return False


def perform(mask, action):
    if action not in ACTION_ROLE:
        return None, "Use trade | trade honor | trade hold | trade release | trade calibrate | trade attest | trade inspect."
    account = getattr(mask, "account", None)
    room = market_room()
    if not account or not room or getattr(mask, "location", None) != room:
        return None, "This professional work must be done in Market Lane."
    role = ACTION_ROLE[action]
    if active_calling(mask) != role:
        return None, f"An active {role.title()} Calling must perform that action."
    day, hour = clock()
    if not witnessed_scale_today(mask, day):
        return None, (
            "First inspect the actual crooked market scale here today. "
            "A remembered rumor or an old observation is not sufficient."
        )
    if action == "inspect":
        return inspect_scale(mask, room, day, hour)
    # Validate before creating a world event, so ordinary repeated attempts
    # do not add misleading failed-event records.
    _proposed, accepted, error = market_standards.apply(
        room.db.market_standards, action,
        account_id=account.id, mask_id=mask.id, mask=mask.key,
        day=day, hour=hour, event_id=1,
    )
    if not accepted:
        return None, error

    def consequence(event):
        with transaction.atomic():
            if mask.location != room or not witnessed_scale_today(mask, day):
                raise RuntimeError("The witness left the market scale.")
            if active_calling(mask) != role:
                raise RuntimeError("The acting professional changed Calling.")
            changed, valid, problem = market_standards.apply(
                room.db.market_standards, action,
                account_id=account.id, mask_id=mask.id, mask=mask.key,
                day=day, hour=hour, event_id=event["id"],
            )
            if not valid:
                raise RuntimeError(problem)
            room.db.market_standards = changed
            return {
                "action": action,
                "market_distribution_held": market_standards.suspended(
                    changed, day
                ),
                "review_event_id": (
                    changed["review"]["event_id"] if changed["review"] else None
                ),
                "calibration_event_id": (
                    changed["calibration"]["event_id"]
                    if changed["calibration"] else None
                ),
            }

    event = publish_world_event(
        "village.market_" + action, actor=mask,
        payload={
            "action": action, "day": day, "hour": hour,
            "location": MARKET, "professional_calling": role,
            "harbinger": False, "chronicle_eligible": False,
        },
        consequence=consequence,
    )
    record_participation(mask, "market_" + action, calling=role)
    return {
        "event_id": event["id"], "action": action,
        "lines": state_lines(),
    }, None


def inspect_scale(mask, room, day, hour):
    """Detective observes an actual calibrated scale, not an invented culprit."""
    scale = next((obj for obj in room.contents
                  if obj.key == SCALE
                  and obj.db.landmark_id == "market_scale"
                  and obj.access(mask, "view", default=True)), None)
    if scale is None:
        return None, "The physical market scale is unavailable."
    state = market_standards.refresh(room.db.market_standards, day)
    calibration = state.get("calibration") if state["day"] == day else None
    source_id = calibration.get("event_id") if calibration else None
    ledger = get_event_ledger()
    source = ledger.get_event(source_id) if source_id else None

    def evaluate(event_id):
        return forensic_scale.inspect(
            scale.db.forensic_inspections,
            calibration=calibration, source_event=source,
            account_id=mask.account.id, mask_id=mask.id, mask=mask.key,
            day=day, hour=hour, event_id=event_id,
            scale_id=scale.id, market_id=room.id,
        )

    _preview, valid, reason = evaluate(1)
    if not valid:
        return None, reason

    def consequence(event):
        with transaction.atomic():
            now_day, now_hour = clock()
            if (now_day, now_hour) != (day, hour):
                raise RuntimeError("Village time changed before the forensic inquiry.")
            if (mask.location != room or scale.location != room
                    or not witnessed_scale_today(mask, day)
                    or active_calling(mask) != "detective"):
                raise RuntimeError("The investigator lost physical access or authority.")
            now_state = market_standards.refresh(room.db.market_standards, day)
            now_calibration = (
                now_state.get("calibration") if now_state["day"] == day else None
            )
            now_source_id = (
                now_calibration.get("event_id") if now_calibration else None
            )
            now_source = ledger.get_event(now_source_id) if now_source_id else None
            changed, accepted, problem = forensic_scale.inspect(
                scale.db.forensic_inspections,
                calibration=now_calibration, source_event=now_source,
                account_id=mask.account.id, mask_id=mask.id, mask=mask.key,
                day=day, hour=hour, event_id=event["id"],
                scale_id=scale.id, market_id=room.id,
            )
            if not accepted:
                raise RuntimeError(problem)
            scale.db.forensic_inspections = changed
            return {
                "scale_object_id": scale.id,
                "market_room_id": room.id,
                "smith_source_event_id": now_source_id,
                "finding": forensic_scale.FINDING,
                "day": day,
            }

    event = publish_world_event(
        forensic_scale.INQUIRY_KIND, actor=mask,
        payload={
            "action": "inspect", "day": day, "hour": hour,
            "location": MARKET, "scale_object_id": scale.id,
            "smith_source_event_id": source_id,
            "professional_calling": "detective",
            "harbinger": False, "chronicle_eligible": False,
        },
        consequence=consequence,
    )
    record_participation(mask, "market_forensic_inspections", calling="detective")
    return {"event_id": event["id"], "action": "inspect",
            "lines": state_lines()}, None
