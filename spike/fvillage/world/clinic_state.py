"""Day-scoped, evidence-based village care with bounded signed history.

A new visiting patient occupies the church clinic cot each village day.
The patient is a limited recurring service role, not a scheduled resident.
No medical diagnosis follows from a player's narrative assertion.
"""
from __future__ import annotations
import copy

CONDITIONS = ("cold", "sprain", "fever")
METHODS = ("rest", "compress")
MAX_HISTORY = 36
DAILY_LINEN = 2
MAX_LINEN = 4
# Each anonymous daily visitor has an authored preference independent of the
# Healer. This is a bounded game-state choice, not a new named-person canon fact.
MUSIC_CHOICES = ("accepts", "declines", "unavailable")


def music_preference(day):
    """Independent day-scoped visitor response, never selected by a player."""
    if type(day) is not int or day < 1:
        return None
    return MUSIC_CHOICES[(day - 1) % len(MUSIC_CHOICES)]



def ident(value):
    if isinstance(value, bool):
        return None
    try:
        n = int(value)
    except (ValueError, TypeError, OverflowError):
        return None
    return n if n > 0 else None


def hour_value(value):
    if isinstance(value, bool):
        return None
    try:
        n = int(value)
    except (ValueError, TypeError, OverflowError):
        return None
    return n if 0 <= n <= 23 else None


def _day_state(day):
    return {"day": day, "condition": CONDITIONS[(day - 1) % len(CONDITIONS)],
            "linen": DAILY_LINEN, "assessment": None, "treatment": None,
            "records_permission": None, "supply": None, "history": [],
            "music_preference": music_preference(day)}


def normalize(raw):
    if not hasattr(raw, "get"):
        return _day_state(1)
    day = ident(raw.get("day")) or 1
    state = _day_state(day)
    condition = raw.get("condition")
    if condition == state["condition"]:
        try:
            state["linen"] = max(0, min(MAX_LINEN, int(raw.get("linen"))))
        except (TypeError, ValueError, OverflowError):
            state["linen"] = DAILY_LINEN
    supply = raw.get("supply")
    if (hasattr(supply, "get") and ident(supply.get("event_id"))
            and ident(supply.get("source_event_id"))
            and ident(supply.get("parcel_id"))
            and ident(supply.get("merchant_account_id"))
            and ident(supply.get("healer_account_id"))
            and supply.get("day") == day):
        state["supply"] = copy.deepcopy(dict(supply))
    if not state["supply"]:
        state["linen"] = min(state["linen"], DAILY_LINEN)
    for key in ("assessment", "treatment"):
        row = raw.get(key)
        if (hasattr(row, "get") and ident(row.get("event_id"))
                and ident(row.get("account_id"))
                and ident(row.get("mask_id"))
                and row.get("day") == day and
                hour_value(row.get("hour")) is not None):
            if key == "assessment" or row.get("method") in METHODS:
                state[key] = copy.deepcopy(dict(row))
    if state["treatment"] and not state["assessment"]:
        state["treatment"] = None
    permission = raw.get("records_permission")
    examined = state["assessment"]
    if (examined and hasattr(permission, "get")
            and ident(permission.get("account_id")) == examined["account_id"]
            and ident(permission.get("mask_id")) == examined["mask_id"]
            and ident(permission.get("event_id"))
            and permission.get("day") == day
            and hour_value(permission.get("hour")) is not None):
        state["records_permission"] = copy.deepcopy(dict(permission))
    state["history"] = [
        copy.deepcopy(dict(row)) for row in list(raw.get("history") or [])[-MAX_HISTORY * 2:]
        if hasattr(row, "get") and ident(row.get("day"))
    ][-MAX_HISTORY:]
    return state


def refresh(raw, day):
    day = ident(day)
    if day is None:
        raise ValueError("Village day must be positive.")
    state = normalize(raw)
    if day <= state["day"]:
        return state
    if state["assessment"] or state["treatment"] or state["supply"]:
        state["history"].append({
            "day": state["day"], "condition": state["condition"],
            "assessment": copy.deepcopy(state["assessment"]),
            "treatment": copy.deepcopy(state["treatment"]),
            "supply": copy.deepcopy(state["supply"]),
        })
    future = _day_state(day)
    future["history"] = state["history"][-MAX_HISTORY:]
    return future


def _actor(day, hour, account_id, mask_id, mask, event_id):
    if not (ident(day) and ident(account_id) and ident(mask_id)
            and ident(event_id) and hour_value(hour) is not None):
        return None
    return {"day": day, "hour": hour, "account_id": int(account_id),
            "mask_id": int(mask_id), "mask": str(mask or "")[:70],
            "event_id": int(event_id)}


def assess(raw, *, day, hour, account_id, mask_id, mask, event_id):
    state = refresh(raw, day)
    if day < state["day"]:
        return state, False, "A newer day is already on the clinic register."
    actor = _actor(day, hour, account_id, mask_id, mask, event_id)
    if not actor:
        return state, False, "A signed, present player is required."
    if state["assessment"]:
        return state, False, "Today's visiting patient was already assessed."
    actor["finding"] = state["condition"]
    state["assessment"] = actor
    return state, True, None


def prepare(raw, *, day):
    state = refresh(raw, day)
    if day < state["day"] or not state["linen"]:
        return state, False, "The shared clinic cabinet has no fresh linen today."
    state["linen"] -= 1
    return state, True, None


def treat(raw, *, day, hour, account_id, mask_id, mask, event_id, method):
    state = refresh(raw, day)
    if day < state["day"]:
        return state, False, "The patient already belongs to a later day."
    actor = _actor(day, hour, account_id, mask_id, mask, event_id)
    if not actor:
        return state, False, "A signed, present player is required."
    if method not in METHODS:
        return state, False, "Choose rest or compress."
    if not state["assessment"]:
        return state, False, "A Healer must examine the actual patient first."
    if state["treatment"]:
        return state, False, "Today's patient has already received treatment."
    best = {"cold": "rest", "sprain": "compress", "fever": "rest"}
    actor["method"] = method
    actor["assessment_event_id"] = state["assessment"]["event_id"]
    actor["improvement"] = 25 if method == best[state["condition"]] else 10
    actor["outcome"] = (
        "The patient is more comfortable after appropriate care."
        if actor["improvement"] == 25
        else "The visitor rests more easily, although the care was less suited to the complaint."
    )
    state["treatment"] = actor
    return state, True, None


def grant_records_permission(raw, *, day, hour, account_id, mask_id,
                             mask, event_id):
    """The day's visiting patient agrees to share notes with their examiner.

    The consent is explicitly requested, stored in the *existing clinic state*
    as a signed, day-scoped grant, and never transfers across masks/accounts.
    In particular, another Healer does not inherit confidential records.
    """
    state = refresh(raw, day)
    if day < state["day"]:
        return state, False, "The current patient belongs to a later day."
    actor = _actor(day, hour, account_id, mask_id, mask, event_id)
    if not actor:
        return state, False, "A signed, present account is required."
    examiner = state["assessment"]
    if examiner is None:
        return state, False, "First complete an assessment of the present patient."
    if (examiner["account_id"], examiner["mask_id"]) != (
            actor["account_id"], actor["mask_id"]):
        return state, False, "Only this patient's examining Healer may request these records."
    if state["records_permission"]:
        return state, False, "The patient's permission is already signed for today."
    state["records_permission"] = actor
    return state, True, None


def private_lines(raw, day, *, account_id, mask_id):
    """Never return confidential details until the specific patient granted access.

    This pure function is a projection, not an access authority by itself:
    the runtime wrapper additionally checks current Calling and actual room.
    """
    state = refresh(raw, day)
    permission = state["records_permission"]
    if (permission is None or not ident(account_id) or not ident(mask_id)
            or permission["account_id"] != ident(account_id)
            or permission["mask_id"] != ident(mask_id)
            or state["assessment"] is None):
        return "Private clinical notes require this patient's signed permission for the examining Healer."
    assessment = state["assessment"]
    lines = [
        "|wConfidential St. Lazarus case record|n",
        f"Current patient, village day {state['day']}: {state['condition']}.",
        f"Assessment by {assessment['mask']} (event {assessment['event_id']}).",
        f"Patient permission recorded as event {permission['event_id']}.",
    ]
    if state["treatment"]:
        t = state["treatment"]
        lines.append(
            f"Treatment: {t['method']} by {t['mask']} "
            f"(event {t['event_id']}). {t['outcome']}"
        )
    else:
        lines.append("Treatment not yet completed.")
    # Today's unnamed visiting patient is not the previous day's patient.
    # The bounded prior archive is NOT part of their current case record.
    return "\n".join(lines)


def public_lines(raw, day):
    """Shared workplace status, never personal case detail or prior patients."""
    state = refresh(raw, day)
    lines = [
        "|wSt. Lazarus village clinic|n",
        f"Village day {state['day']}: a visiting patient is at the treatment cot.",
        f"Fresh linen in the shared cabinet: {state['linen']} of "
        f"{MAX_LINEN if state['supply'] else DAILY_LINEN}.",
        ("A Merchant parcel was clinically accepted (source event "
         f"{state['supply']['source_event_id']}, receipt {state['supply']['event_id']})."
         if state["supply"] else
         "No additional Merchant linen delivery has been accepted today."),
        ("A professional assessment has been recorded."
         if state["assessment"] else
         "No examination has been completed yet."),
        ("Care has been provided."
         if state["treatment"] else
         "Treatment remains available after assessment."),
        "Healers: clinic assess | clinic prepare | clinic treat rest or clinic treat compress | clinic receive.",
        "Merchants: clinic procure at Market Lane; carry a real parcel here for Healer acceptance.",
        "The examining Healer may request this patient's permission using "
        "clinic request records, then use clinic records for confidential notes.",
        "The public clinic board does not reveal individual findings or earlier patients.",
    ]
    return "\n".join(lines)
