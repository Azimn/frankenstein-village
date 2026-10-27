"""GDD-EDGE-27: consented music at the original St. Lazarus clinic cot.

One real Healer requests the treated visitor's consent; a different
authenticated Performer's actual presence and music complete the encounter.
The cot and canonical world-event ledger are the only public authorities.
"""
from __future__ import annotations

from django.db import transaction

from world import clinic_comfort_edge27 as rules, clinic_state, clinic_work
from world.callings import active_calling, record_participation
from world.events import get_event_ledger, publish_world_event


def _cot(room):
    found = [
        obj for obj in room.contents
        if obj.key == clinic_work.COT
        and obj.is_typeclass("typeclasses.objects.ClinicCot", exact=True)
    ]
    return found[0] if len(found) == 1 else None


def _seen(mask, cot, day):
    seen = getattr(mask.db, "clinic_cot_seen", None)
    return (hasattr(seen, "get") and seen.get("day") == day
            and seen.get("cot_id") == cot.id
            and seen.get("room_id") == cot.location.id)


def act(mask, action):
    room, error = clinic_work._guard(mask)
    if error:
        return None, error
    if action not in ("invite", "music"):
        return None, "Use clinic invite or clinic music."
    role = "healer" if action == "invite" else "performer"
    if active_calling(mask) != role:
        return None, "Only an active %s can use clinic %s." % (role.title(), action)
    cot = _cot(room)
    if cot is None:
        return None, "The original physical clinic cot is missing."
    day, hour = clinic_work._clock()
    if rules.stamp(day, hour) is None:
        return None, "The village clock is invalid."
    if not _seen(mask, cot, day):
        return None, "Look at the original clinic cot before acting."
    ledger = get_event_ledger()
    clinic = clinic_state.refresh(room.db.village_clinic, day)
    if clinic["day"] != day or not clinic["treatment"]:
        return None, "Today's visitor needs genuine Healer treatment first."
    treatment = dict(clinic["treatment"])
    source = ledger.get_event(treatment["event_id"])
    if not rules.treatment_valid(treatment, source, room.id):
        return None, "The original Healer treatment is not verified."
    if action == "invite":
        kwargs = {
            "treatment": treatment, "treatment_event": source,
        }
        transform = rules.invite
    else:
        current = rules.refresh(cot.db.clinic_comfort, day)
        invitation = current["invitation"]
        kwargs = {
            "invitation_event": (
                ledger.get_event(invitation["event_id"]) if invitation else None
            ),
        }
        transform = rules.offer
    common = {
        "day": day, "hour": hour, "account_id": mask.account.id,
        "mask_id": mask.id, "mask": mask.key,
        "room_id": room.id, "cot_id": cot.id,
    }
    _preview, good, reason = transform(
        cot.db.clinic_comfort, event_id=1, **common, **kwargs)
    if not good:
        return None, reason

    def consequence(event):
        with transaction.atomic():
            if (clinic_work._clock() != (day, hour)
                    or mask.location != room or cot.location != room
                    or not _seen(mask, cot, day)
                    or mask.account is None
                    or mask.account.id != common["account_id"]
                    or active_calling(mask) != role):
                raise RuntimeError("The actor, cot, Calling or village hour changed.")
            latest = clinic_state.refresh(room.db.village_clinic, day)
            if (latest["day"] != day or latest["treatment"] != treatment
                    or not rules.treatment_valid(
                        treatment, ledger.get_event(treatment["event_id"]),
                        room.id)):
                raise RuntimeError("The signed clinical source changed.")
            if action == "music":
                invitation = rules.refresh(
                    cot.db.clinic_comfort, day)["invitation"]
                fresh_kwargs = {
                    "invitation_event": ledger.get_event(
                        invitation["event_id"]) if invitation else None
                }
            else:
                fresh_kwargs = {
                    "treatment": treatment,
                    "treatment_event": ledger.get_event(treatment["event_id"]),
                }
            changed, valid, problem = transform(
                cot.db.clinic_comfort, event_id=event["id"],
                **common, **fresh_kwargs)
            if not valid:
                raise RuntimeError(problem)
            cot.db.clinic_comfort = changed
            record = changed["invitation"] if action == "invite" else changed["music"]
            return {
                "room_id": room.id, "cot_id": cot.id,
                "day": day, "hour": hour,
                "source_healer_event_id": treatment["event_id"],
                "source_event_id": record["source_event_id"],
                "consent": "accepted" if action == "invite" else "respected",
                "outcome": "invited" if action == "invite" else "music_offered",
            }

    event = publish_world_event(
        "village.clinic_music_" + ("invited" if action == "invite" else "offered"),
        actor=mask,
        payload={
            "day": day, "hour": hour, "room_id": room.id, "cot_id": cot.id,
            "professional_calling": role,
            "source_healer_event_id": treatment["event_id"],
            "harbinger": False, "chronicle_eligible": False,
        },
        consequence=consequence,
    )
    record_participation(
        mask, "clinic_music_" + action, calling=role)
    return {"event_id": event["id"], "action": action,
            "source_healer_event_id": treatment["event_id"]}, None
