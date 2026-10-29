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
    "calibrate": "smith", "attest": "chronicler", "audit": "chronicler",
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
    try:
        recent = dict(mask.db.landmark_latest_view or {}).get("market_scale") or {}
        return int(recent.get("day") or 0) == int(day)
    except (ValueError, TypeError, OverflowError):
        return False


def perform(mask, action):
    if action not in ACTION_ROLE:
        return None, "Use trade | trade honor | trade hold | trade release | trade calibrate | trade audit | trade attest."
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
    # Validate before creating a world event, so ordinary repeated attempts
    # do not add misleading failed-event records.
    _proposed, accepted, error = market_standards.apply(
        room.db.market_standards, action,
        account_id=account.id, mask_id=mask.id, mask=mask.key,
        day=day, hour=hour, event_id=1,
    )
    if not accepted:
        return None, error
    if action == "audit":
        review = market_standards.refresh(room.db.market_standards, day)["review"]
        source = get_event_ledger().get_event(review["event_id"])
        if not market_standards.verified_merchant_review(review, source):
            return None, "The Merchant source event is not a verified completed decision."

    def consequence(event):
        with transaction.atomic():
            if mask.location != room or not witnessed_scale_today(mask, day):
                raise RuntimeError("The witness left the market scale.")
            if active_calling(mask) != role:
                raise RuntimeError("The acting professional changed Calling.")
            if action == "audit":
                if clock()[0] != day:
                    raise RuntimeError("The village day changed before the audit.")
                current = market_standards.refresh(room.db.market_standards, day)
                review = current["review"]
                source = (get_event_ledger().get_event(review["event_id"])
                          if review else None)
                if not market_standards.verified_merchant_review(review, source):
                    raise RuntimeError("The Merchant source is no longer verified.")
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
                "audit_source_event_id": (
                    changed["audit"]["review_event_id"]
                    if action == "audit" else None
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
