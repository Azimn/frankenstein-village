"""Ordinary-player bridge investigation bound to visible physical evidence."""
from __future__ import annotations

from django.db import transaction
from evennia.utils import search
from evennia.scripts.models import ScriptDB

from world import bridge_choices
from world.discoveries import normalize as known_landmarks
from world.events import publish_world_event
from world.public_mysteries import BRIDGE_PLAQUE_ID, get_public_mystery

BRIDGE_NAME = "The Old Stone Bridge"


def _bridge():
    return next((
        room for room in search.search_object(BRIDGE_NAME)
        if room.key == BRIDGE_NAME
        and room.location is None
        and room.tags.has("ic", category="side")
    ), None)


def _clock():
    try:
        c = ScriptDB.objects.get(db_key="village_time")
        return int(c.db.day or 1), int(
            c.db.hour if c.db.hour is not None else 21
        )
    except ScriptDB.DoesNotExist:
        return 1, 21


def _plaque_witness(mask, *, day=None):
    """Check firsthand public-mystery evidence linked to this exact mask."""
    mystery = get_public_mystery(BRIDGE_PLAQUE_ID) or {}
    for observation in mystery.get("observations") or []:
        if day is not None and observation.get("day") != day:
            continue
        if any(
            witness.get("mask_id") == mask.id
            and witness.get("account_id") == mask.account.id
            for witness in observation.get("witnesses") or []
        ):
            return True
    return False


def _gauge_witness(mask):
    return any(
        finding["id"] == "river_gauge"
        for finding in known_landmarks(mask.db.landmark_discoveries)
    )


def status_lines(mask):
    bridge = _bridge()
    if bridge is None:
        return "The Old Stone Bridge is not accessible."
    state = bridge_choices.normalize(bridge.db.bridge_inquiry)
    lines = [
        "|wThe Missing Plaque: a civic investigation|n",
        bridge_choices.public_line(state),
        "The marks do not establish who took the plaque or why.",
    ]
    if state["resolution"] is not None:
        signed = state["resolution"]
        lines.append(
            f"The {signed['choice']} response was signed by "
            f"{signed['mask']} on village day {signed['day']} "
            f"(world event {signed['event_id']})."
        )
        lines.append(
            "Inspect the actual plaque at the bridge today, then use "
            "|wbridgework check|n to maintain this shared response. "
            "Each account may sign one inspection per village day."
        )
        return "\n".join(lines)
    if not _plaque_witness(mask):
        lines.append(
            "First go to the Old Stone Bridge and |wlook plaque|n. "
            "A rumor alone does not count as observing the missing inscription."
        )
    if not _gauge_witness(mask):
        lines.append(
            "Compare the waterside evidence: inspect the |wriver gauge|n "
            "on Riverside Path, one room west of the bridge."
        )
    if _plaque_witness(mask) and _gauge_witness(mask):
        lines.append(
            "You have firsthand evidence from both sites. At the bridge, "
            "choose |wbridgework preserve|n to fit a protective cover, or "
            "|wbridgework display|n to erect a public witness board. "
            "Both choices have lasting visible consequences, and neither "
            "names a culprit. Only one public response can be established."
        )
    else:
        lines.append(
            "Return to the bridge after inspecting both physical clues. "
            "No profession, private information, or second player is required."
        )
    return "\n".join(lines)


def act(mask, verb):
    """Authoritative mutation from a signed, located ordinary player mask."""
    account = getattr(mask, "account", None)
    room = getattr(mask, "location", None)
    bridge = _bridge()
    if not account or bridge is None or room != bridge:
        return None, "You must be at the Old Stone Bridge as your own mask."
    if not room.tags.has("ic", category="side"):
        return None, "Bridge work only exists inside the village."
    day, hour = _clock()
    state = bridge_choices.normalize(bridge.db.bridge_inquiry)
    if verb in bridge_choices.CHOICES:
        if state["resolution"]:
            return None, "The public bridge response is already settled."
        if not _plaque_witness(mask) or not _gauge_witness(mask):
            return None, (
                "Examine the actual plaque here and the river gauge "
                "on Riverside Path before choosing a response."
            )
        event_kind = "village.bridge_response"
    elif verb == "check":
        if not state["resolution"]:
            return None, "The bridge has no public response to maintain."
        if not _plaque_witness(mask, day=day):
            return None, (
                "Examine the plaque socket here again today before "
                "signing an upkeep check."
            )
        # Validate before publishing: failures do not create phantom events.
        _, accepted, error = bridge_choices.check(
            state, account_id=account.id, mask_id=mask.id,
            day=day, event_id=1,
        )
        if not accepted:
            return None, error
        event_kind = "village.bridge_upkeep"
    else:
        return None, "Use: bridgework | bridgework preserve | bridgework display | bridgework check"

    def consequence(event):
        with transaction.atomic():
            if mask.location != bridge or not mask.account:
                raise RuntimeError("The investigator left the bridge.")
            # The real shared room is the authority, not the player's diary.
            current = bridge.db.bridge_inquiry
            if verb == "check":
                changed, valid, problem = bridge_choices.check(
                    current, account_id=account.id, mask_id=mask.id,
                    day=day, event_id=event["id"],
                )
            else:
                changed, valid, problem = bridge_choices.settle(
                    current, verb, account_id=account.id,
                    mask_id=mask.id, mask=mask.key, day=day, hour=hour,
                    event_id=event["id"],
                )
            if not valid:
                raise RuntimeError(problem)
            bridge.db.bridge_inquiry = changed
            return {
                "choice": changed["resolution"]["choice"],
                "signed_upkeep": len(changed["checks"]),
            }

    event = publish_world_event(
        event_kind, actor=mask,
        payload={
            "choice": verb if verb in bridge_choices.CHOICES else None,
            "location": BRIDGE_NAME, "day": day, "hour": hour,
            "harbinger": False, "chronicle_eligible": False,
        },
        consequence=consequence,
    )
    state = bridge_choices.normalize(bridge.db.bridge_inquiry)
    return {
        "event_id": event["id"],
        "choice": state["resolution"]["choice"],
        "line": bridge_choices.public_line(state),
    }, None
