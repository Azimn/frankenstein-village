"""GDD-EDGE-27: consented music for a real, treated clinic visitor.

The original cot owns the bounded public consent/music record. Medical notes
stay in the existing clinic state; neither a song nor an invitation is care.
"""
from __future__ import annotations

import copy
from collections.abc import Mapping

MAX_HISTORY = 36


def positive(value):
    return value if type(value) is int and value > 0 else None


def stamp(day, hour):
    if positive(day) is None or type(hour) is not int or not 0 <= hour <= 23:
        return None
    return day * 24 + hour


def fresh(day=1):
    return {"day": day, "invitation": None, "music": None, "history": []}


def _row(raw, fields, day):
    if not isinstance(raw, Mapping) or raw.get("day") != day:
        return None
    if stamp(raw.get("day"), raw.get("hour")) is None:
        return None
    if any(positive(raw.get(key)) is None for key in fields):
        return None
    return {**{key: raw[key] for key in fields},
            "day": day, "hour": raw["hour"],
            "mask": str(raw.get("mask") or "")[:70]}


INVITE_FIELDS = ("account_id", "mask_id", "event_id", "source_event_id",
                 "room_id", "cot_id")
MUSIC_FIELDS = ("account_id", "mask_id", "event_id", "source_event_id",
                "healer_account_id", "room_id", "cot_id")


def normalize(raw):
    if not isinstance(raw, Mapping):
        return fresh()
    day = positive(raw.get("day")) or 1
    state = fresh(day)
    invitation = _row(raw.get("invitation"), INVITE_FIELDS, day)
    music = _row(raw.get("music"), MUSIC_FIELDS, day)
    if invitation and invitation["event_id"] != invitation["source_event_id"]:
        state["invitation"] = invitation
    if (state["invitation"] and music
            and music["source_event_id"] == invitation["event_id"]
            and music["healer_account_id"] == invitation["account_id"]
            and music["account_id"] != invitation["account_id"]
            and music["event_id"] not in
            (music["source_event_id"], invitation["source_event_id"])
            and music["cot_id"] == invitation["cot_id"]
            and music["room_id"] == invitation["room_id"]
            and stamp(day, music["hour"]) >= stamp(day, invitation["hour"])):
        state["music"] = music
    history = raw.get("history") or []
    if not isinstance(history, (str, bytes)):
        try:
            history = list(history)
        except TypeError:
            history = []
        state["history"] = [
            copy.deepcopy(dict(row)) for row in history[-MAX_HISTORY * 2:]
            if isinstance(row, Mapping)
            and positive(row.get("day")) is not None and row["day"] < day
        ][-MAX_HISTORY:]
    return state


def refresh(raw, day):
    if positive(day) is None:
        raise ValueError("A positive village day is required.")
    state = normalize(raw)
    if day <= state["day"]:
        return state
    if state["invitation"] or state["music"]:
        state["history"].append({
            "day": state["day"],
            "invitation": copy.deepcopy(state["invitation"]),
            "music": copy.deepcopy(state["music"]),
        })
    future = fresh(day)
    future["history"] = state["history"][-MAX_HISTORY:]
    return future


def treatment_valid(treatment, source_event, room_id):
    """A completed, attributable clinical treatment, not a claimed cure."""
    if not isinstance(treatment, Mapping) or not isinstance(source_event, Mapping):
        return False
    actor = source_event.get("actor")
    payload = source_event.get("payload")
    consequence = source_event.get("consequence")
    if not all(isinstance(x, Mapping) for x in (actor, payload, consequence)):
        return False
    return (
        positive(room_id) is not None
        and source_event.get("kind") == "village.clinic_treat"
        and source_event.get("status") == "complete"
        and positive(source_event.get("id")) == positive(treatment.get("event_id"))
        and positive(actor.get("account_id")) == positive(treatment.get("account_id"))
        and positive(actor.get("mask_id")) == positive(treatment.get("mask_id"))
        and actor.get("mask") == treatment.get("mask")
        and payload.get("professional_calling") == "healer"
        and payload.get("day") == treatment.get("day")
        and payload.get("hour") == treatment.get("hour")
        and payload.get("method") == treatment.get("method")
        and stamp(treatment.get("day"), treatment.get("hour")) is not None
        and positive(consequence.get("room_id")) == room_id
        and positive(consequence.get("assessment_event_id"))
        == positive(treatment.get("assessment_event_id"))
        and consequence.get("patient_condition") in ("cold", "sprain", "fever")
    )


def invitation_valid(invitation, event):
    """Validate the original Healer's completed, cot-bound consent event."""
    if not isinstance(invitation, Mapping) or not isinstance(event, Mapping):
        return False
    actor, payload, consequence = (
        event.get("actor"), event.get("payload"), event.get("consequence"))
    if not all(isinstance(x, Mapping) for x in (actor, payload, consequence)):
        return False
    return (
        event.get("kind") == "village.clinic_music_invited"
        and event.get("status") == "complete"
        and positive(event.get("id")) == positive(invitation.get("event_id"))
        and positive(actor.get("account_id")) == positive(invitation.get("account_id"))
        and positive(actor.get("mask_id")) == positive(invitation.get("mask_id"))
        and actor.get("mask") == invitation.get("mask")
        and payload.get("professional_calling") == "healer"
        and payload.get("day") == invitation.get("day")
        and payload.get("hour") == invitation.get("hour")
        and payload.get("cot_id") == invitation.get("cot_id")
        and payload.get("source_healer_event_id") == invitation.get("source_event_id")
        and positive(consequence.get("room_id")) == invitation.get("room_id")
        and positive(consequence.get("cot_id")) == invitation.get("cot_id")
        and positive(consequence.get("source_healer_event_id"))
        == invitation.get("source_event_id")
        and consequence.get("consent") == "accepted"
        and stamp(invitation.get("day"), invitation.get("hour")) is not None
    )


def invite(raw, *, day, hour, account_id, mask_id, mask, event_id,
           room_id, cot_id, treatment, treatment_event):
    state = refresh(raw, day) if positive(day) else normalize(raw)
    if stamp(day, hour) is None or day < state["day"]:
        return state, False, "The village clock is invalid or has moved backward."
    ids = (account_id, mask_id, event_id, room_id, cot_id)
    if any(positive(x) is None for x in ids):
        return state, False, "A real Healer, cot and signed event are required."
    if state["invitation"]:
        return state, False, "Today's patient has already answered an invitation."
    if not treatment_valid(treatment, treatment_event, room_id):
        return state, False, "The signed clinical treatment cannot be verified."
    if (treatment["day"] != day or treatment["account_id"] != account_id
            or treatment["mask_id"] != mask_id or treatment["mask"] != mask
            or stamp(day, hour) < stamp(day, treatment["hour"])
            or event_id == treatment["event_id"]):
        return state, False, "Only today's treating Healer can request this patient's consent."
    state["invitation"] = {
        "day": day, "hour": hour, "account_id": account_id,
        "mask_id": mask_id, "mask": str(mask or "")[:70],
        "event_id": event_id, "source_event_id": treatment["event_id"],
        "room_id": room_id, "cot_id": cot_id,
    }
    return state, True, None


def offer(raw, *, day, hour, account_id, mask_id, mask, event_id,
          room_id, cot_id, invitation_event):
    state = refresh(raw, day) if positive(day) else normalize(raw)
    if stamp(day, hour) is None or day < state["day"]:
        return state, False, "The village clock is invalid or has moved backward."
    if any(positive(x) is None for x in
           (account_id, mask_id, event_id, room_id, cot_id)):
        return state, False, "A real Performer, cot and signed event are required."
    invitation = state["invitation"]
    if not invitation or not invitation_valid(invitation, invitation_event):
        return state, False, "The visitor has no verifiable consented invitation."
    if state["music"]:
        return state, False, "The visitor has already received today's music."
    if (invitation["room_id"] != room_id or invitation["cot_id"] != cot_id
            or invitation["account_id"] == account_id
            or invitation["mask_id"] == mask_id
            or event_id in (invitation["event_id"], invitation["source_event_id"])
            or stamp(day, hour) < stamp(day, invitation["hour"])):
        return state, False, "An independent Performer must attend the original cot after consent."
    state["music"] = {
        "day": day, "hour": hour, "account_id": account_id,
        "mask_id": mask_id, "mask": str(mask or "")[:70],
        "event_id": event_id, "source_event_id": invitation["event_id"],
        "healer_account_id": invitation["account_id"],
        "room_id": room_id, "cot_id": cot_id,
    }
    return state, True, None


def _public_sources_verified(state, *, event_lookup, treatment,
                             treatment_event, room_id, cot_id):
    """Verify public signed claims against canonical completed events."""
    invitation = state["invitation"]
    music = state["music"]
    if (not invitation or not callable(event_lookup)
            or not isinstance(treatment, Mapping)
            or positive(room_id) is None or positive(cot_id) is None):
        return False
    if (invitation["room_id"] != room_id or invitation["cot_id"] != cot_id
            or invitation["source_event_id"] != treatment.get("event_id")
            or invitation["account_id"] != treatment.get("account_id")
            or invitation["mask_id"] != treatment.get("mask_id")
            or invitation["mask"] != treatment.get("mask")
            or invitation["day"] != treatment.get("day")
            or stamp(treatment.get("day"), treatment.get("hour")) is None
            or stamp(invitation["day"], invitation["hour"])
            < stamp(treatment["day"], treatment["hour"])
            or positive(treatment.get("event_id")) is None
            or not (positive(treatment.get("event_id"))
                    < positive(invitation["event_id"]))
            or not treatment_valid(treatment, treatment_event, room_id)):
        return False
    try:
        signed_invitation = event_lookup(invitation["event_id"])
    except Exception:
        return False
    if not invitation_valid(invitation, signed_invitation):
        return False
    payload = signed_invitation["payload"]
    consequence = signed_invitation["consequence"]
    if (positive(payload.get("room_id")) != room_id
            or positive(consequence.get("source_event_id"))
            != invitation["source_event_id"]
            or consequence.get("day") != invitation["day"]
            or consequence.get("hour") != invitation["hour"]
            or consequence.get("outcome") != "invited"):
        return False
    if music is None:
        return True
    if (music["room_id"] != room_id or music["cot_id"] != cot_id
            or music["day"] != invitation["day"]
            or music["source_event_id"] != invitation["event_id"]
            or music["healer_account_id"] != invitation["account_id"]
            or music["account_id"] == invitation["account_id"]
            or music["mask_id"] == invitation["mask_id"]
            or not (positive(invitation["event_id"])
                    < positive(music["event_id"]))
            or stamp(music["day"], music["hour"])
            < stamp(invitation["day"], invitation["hour"])):
        return False
    try:
        signed_music = event_lookup(music["event_id"])
    except Exception:
        return False
    if not isinstance(signed_music, Mapping):
        return False
    actor = signed_music.get("actor")
    payload = signed_music.get("payload")
    consequence = signed_music.get("consequence")
    if not all(isinstance(x, Mapping) for x in (actor, payload, consequence)):
        return False
    return (
        signed_music.get("kind") == "village.clinic_music_offered"
        and signed_music.get("status") == "complete"
        and positive(signed_music.get("id")) == music["event_id"]
        and positive(actor.get("account_id")) == music["account_id"]
        and positive(actor.get("mask_id")) == music["mask_id"]
        and actor.get("mask") == music["mask"]
        and payload.get("professional_calling") == "performer"
        and payload.get("day") == music["day"]
        and payload.get("hour") == music["hour"]
        and positive(payload.get("room_id")) == room_id
        and positive(payload.get("cot_id")) == cot_id
        and positive(payload.get("source_healer_event_id"))
        == invitation["source_event_id"]
        and consequence.get("day") == music["day"]
        and consequence.get("hour") == music["hour"]
        and positive(consequence.get("room_id")) == room_id
        and positive(consequence.get("cot_id")) == cot_id
        and positive(consequence.get("source_event_id"))
        == invitation["event_id"]
        and positive(consequence.get("source_healer_event_id"))
        == invitation["source_event_id"]
        and consequence.get("consent") == "respected"
        and consequence.get("outcome") == "music_offered"
    )


def public_lines(raw, day, *, event_lookup=None, treatment=None,
                 treatment_event=None, room_id=None, cot_id=None):
    state = refresh(raw, day)
    current_claim = (isinstance(raw, Mapping) and raw.get("day") == day
                     and (raw.get("invitation") is not None
                          or raw.get("music") is not None))
    invalid_shape = (current_claim and (
        (raw.get("invitation") is not None and state["invitation"] is None)
        or (raw.get("music") is not None and state["music"] is None)))
    if current_claim and (invalid_shape or not _public_sources_verified(
            state, event_lookup=event_lookup, treatment=treatment,
            treatment_event=treatment_event, room_id=room_id, cot_id=cot_id)):
        return ("The clinic comfort record cannot be verified against "
                "completed world events. No signed consent or music is claimed.")
    if state["music"]:
        return ("A visitor voluntarily heard a short piece at the cot "
                "(signed music event %s, consent event %s). "
                "The song is not a treatment or diagnosis."
                % (state["music"]["event_id"], state["invitation"]["event_id"]))
    if state["invitation"]:
        return ("Today's visitor has accepted a short, voluntary song. "
                "An independent Performer may look at the cot and use clinic music.")
    return ("After today's signed care, the treating Healer may look at the cot "
            "and use clinic invite to ask whether the visitor wants company. "
            "No music is presumed without a separate Performer.")
