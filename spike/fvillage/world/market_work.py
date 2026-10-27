"""Authenticated, physical three-Calling market standards work.

The crooked scale is authoritative scenery. A personal firsthand view must
occur today before signing a public decision. Event provenance is written to
the existing world event ledger, not an independent simulation scheduler.
"""
from __future__ import annotations

from django.db import transaction
from evennia.scripts.models import ScriptDB
from evennia.utils import search

from world import market_standards
from world.callings import active_calling, record_participation
from world.events import get_event_ledger, publish_world_event

MARKET = "Market Lane"
SCALE = "a crooked market scale"
ACTION_ROLE = {
    "honor": "merchant", "hold": "merchant", "release": "merchant",
    "calibrate": "smith", "attest": "chronicler",
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
    return "\n".join(market_standards.public_lines(
        room.db.market_standards, day
    ))


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
    # Evennia persistence can contain malformed legacy inspection values.
    # Reject those as missing evidence, not as a command-crashing exception.
    try:
        views = mask.db.landmark_latest_view
        if not hasattr(views, "get"):
            return False
        recent = views.get("market_scale")
        if not hasattr(recent, "get"):
            return False
        inspected_day = recent.get("day")
        if isinstance(inspected_day, bool):
            return False
        return int(inspected_day) == int(day)
    except (ValueError, TypeError, OverflowError):
        return False


def perform(mask, action):
    if action not in ACTION_ROLE:
        return None, "Use trade | trade honor | trade hold | trade release | trade calibrate | trade attest."
    account = getattr(mask, "account", None)
    room = market_room()
    if not account or not room or getattr(mask, "location", None) != room:
        return None, "This professional work must be done in Market Lane."
    account_id, mask_id = account.id, mask.id
    role = ACTION_ROLE[action]
    if active_calling(mask) != role:
        return None, f"An active {role.title()} Calling must perform that action."
    day, hour = clock()
    if not witnessed_scale_today(mask, day):
        return None, (
            "First inspect the actual crooked market scale here today. "
            "A remembered rumor or an old observation is not sufficient."
        )
    # Validate before creating a world event, so ordinary repeated attempts
    # do not add misleading failed-event records.
    _proposed, accepted, error = market_standards.apply(
        room.db.market_standards, action,
        account_id=account_id, mask_id=mask_id, mask=mask.key,
        day=day, hour=hour, event_id=1,
    )
    if not accepted:
        return None, error
    if action == "attest" and not market_standards.verified_sources(
            room.db.market_standards, day, get_event_ledger().get_event):
        return None, (
            "The Merchant and Smith source events cannot be verified "
            "against the signed world ledger. No attestation was issued."
        )

    def consequence(event):
        with transaction.atomic():
            # Delayed event consequences cannot sign a stale hour or borrow
            # another authenticated account's authority.
            if (not getattr(mask, "account", None)
                    or mask.account.id != account_id or mask.id != mask_id):
                raise RuntimeError("The market account changed before signing.")
            if clock() != (day, hour):
                raise RuntimeError("Village time advanced before the market decision.")
            if mask.location != room or not witnessed_scale_today(mask, day):
                raise RuntimeError("The witness left the market scale.")
            if active_calling(mask) != role:
                raise RuntimeError("The acting professional changed Calling.")
            if action == "attest" and not market_standards.verified_sources(
                    room.db.market_standards, day, get_event_ledger().get_event):
                raise RuntimeError("The signed market source events changed.")
            changed, valid, problem = market_standards.apply(
                room.db.market_standards, action,
                account_id=account_id, mask_id=mask_id, mask=mask.key,
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

    try:
        event = publish_world_event(
            "village.market_" + action, actor=mask,
            payload={
                "action": action, "day": day, "hour": hour,
                "location": MARKET, "professional_calling": role,
                "harbinger": False, "chronicle_eligible": False,
            },
            consequence=consequence,
        )
    except RuntimeError as error:
        # The signed event was rejected; present a recoverable player error.
        return None, str(error)
    record_participation(mask, "market_" + action, calling=role)
    return {
        "event_id": event["id"], "action": action,
        "lines": state_lines(),
    }, None
