"""Signed market discrepancy inquiry using the existing physical scale and ledger.

Merchant holds actual distribution; a different account's Detective inspects
the scale and opens a qualified case. The Merchant may file one attributable
rebuttal. No claim of counterfeit goods or guilt becomes objective truth.
"""
from __future__ import annotations

from collections.abc import Mapping

from django.db import transaction

from world import market_inquiry_state, market_standards
from world.callings import active_calling, record_participation
from world.events import get_event_ledger, publish_world_event

ROLE = {"investigate": "detective", "rebut": "merchant"}


def _market():
    from world.market_work import market_room
    return market_room()


def _clock():
    from world.market_work import clock
    return clock()


def _scale(room, mask, day):
    from world.market_work import SCALE, witnessed_scale_today
    objects = [
        obj for obj in room.contents
        if obj.key == SCALE and obj.db.landmark_id == "market_scale"
        and obj.access(mask, "view", default=True)
    ]
    if len(objects) != 1 or not witnessed_scale_today(mask, day):
        return None
    return objects[0]


def _signed_hold(room, day):
    state = market_standards.refresh(room.db.market_standards, day)
    review = state.get("review")
    if state["day"] != day or not review or review.get("choice") != "hold":
        return None, "A real Merchant market hold is required today."
    source_id = review.get("event_id")
    if type(source_id) is not int or source_id < 1:
        return None, "The Merchant hold lacks a signed source event."
    event = get_event_ledger().get_event(source_id)
    if not isinstance(event, Mapping):
        return None, "The Merchant hold lacks a completed canonical event."
    actor = event.get("actor") or {}
    payload = event.get("payload") or {}
    effect = event.get("consequence") or {}
    if (event.get("kind") != "village.market_hold"
            or event.get("status") != "complete"
            or not all(isinstance(part, Mapping)
                       for part in (actor, payload, effect))
            or actor.get("account_id") != review["account_id"]
            or actor.get("mask_id") != review["mask_id"]
            or payload.get("action") != "hold"
            or payload.get("professional_calling") != "merchant"
            or payload.get("location") != "Market Lane"
            or payload.get("day") != day
            or payload.get("hour") != review["hour"]
            or effect.get("action") != "hold"
            or effect.get("review_event_id") != source_id
            or effect.get("market_distribution_held") is not True):
        return None, "The held market record does not match its canonical source."
    return review, None


def status():
    room = _market()
    if room is None:
        return "The market inquiry desk is unavailable."
    return market_inquiry_state.public_lines(
        room.db.market_inquiries,
        event_lookup=get_event_ledger().get_event, room_id=room.id,
    )


def perform(mask, action):
    if action not in ROLE:
        return None, "Use trade investigate (Detective) or trade rebut (Merchant)."
    room = _market()
    account = getattr(mask, "account", None)
    if not account or room is None or mask.location != room:
        return None, "Inspect the real Market Lane scale before filing an inquiry."
    role = ROLE[action]
    if active_calling(mask) != role:
        return None, f"An active {role.title()} Calling must perform that action."
    day, hour = _clock()
    scale = _scale(room, mask, day)
    if scale is None:
        return None, "First inspect the actual crooked market scale here today."
    review, error = _signed_hold(room, day)
    if error:
        return None, error
    source_id = review["event_id"]
    if action == "investigate":
        def propose(event_id):
            return market_inquiry_state.open_case(
                room.db.market_inquiries,
                day=day, hour=hour, source_day=review["day"],
                source_hour=review["hour"], source_event_id=source_id,
                source_account_id=review["account_id"],
                source_mask_id=review["mask_id"],
                detective_account_id=account.id, detective_mask_id=mask.id,
                detective_mask=mask.key, scale_id=scale.id,
                case_event_id=event_id,
            )
    else:
        def propose(event_id):
            return market_inquiry_state.rebut_case(
                room.db.market_inquiries,
                day=day, hour=hour, source_event_id=source_id,
                merchant_account_id=account.id, merchant_mask_id=mask.id,
                event_id=event_id,
            )
    _preview, accepted, error = propose(1)
    if not accepted:
        return None, error

    def consequence(event):
        with transaction.atomic():
            if _clock() != (day, hour) or mask.location != room:
                raise RuntimeError("The market inquiry shifted before signing.")
            if active_calling(mask) != role or mask.account != account:
                raise RuntimeError("The acting professional changed identity.")
            if _scale(room, mask, day) is None:
                raise RuntimeError("The investigator lost firsthand scale access.")
            latest, source_error = _signed_hold(room, day)
            if source_error or latest["event_id"] != source_id:
                raise RuntimeError("The Merchant source changed before signing.")
            changed, valid, problem = propose(event["id"])
            if not valid:
                raise RuntimeError(problem)
            room.db.market_inquiries = changed
            return {
                "source_event_id": source_id,
                "scale_id": scale.id,
                "market_room_id": room.id,
                "case_event_id": (
                    event["id"] if action == "investigate"
                    else next(r["case_event_id"] for r in changed
                              if r["source_event_id"] == source_id)
                ),
                "rebuttal_event_id": event["id"] if action == "rebut" else None,
            }

    event = publish_world_event(
        "village.market_inquiry_" + ("opened" if action == "investigate" else "rebutted"),
        actor=mask,
        payload={
            "action": action, "day": day, "hour": hour,
            "source_event_id": source_id, "scale_id": scale.id,
            "market_room_id": room.id, "professional_calling": role,
            "harbinger": False, "chronicle_eligible": False,
        },
        consequence=consequence,
    )
    record_participation(mask, "market_inquiry_" + action, calling=role)
    return {"event_id": event["id"], "lines": status()}, None
