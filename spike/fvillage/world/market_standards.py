"""Pure, clock-driven civic trade-dispute rules.

Market work is authored by Merchant, Smith and Chronicler characters through
physical observation and signed events. A Merchant can hold distribution over
disputed weights, a Smith can restore the scale, and a Chronicler can attest
what actually happened. Old decisions persist. Days do not auto-generate jobs.
"""
from __future__ import annotations

import copy
from collections.abc import Mapping

MAX_HISTORY = 28
CHOICES = frozenset({"honor", "hold"})
ROLES = {"review": "merchant", "calibrate": "smith", "attest": "chronicler"}


def fresh(day=0):
    return {
        "day": day, "review": None, "calibration": None,
        "release": None, "attestation": None, "audit": None, "history": [],
    }


def _signed(account_id, mask_id, mask, event_id, day, hour):
    if any(isinstance(v, bool) for v in (account_id, mask_id, event_id, day, hour)):
        return None
    try:
        aid, mid, eid, d, h = map(
            int, (account_id, mask_id, event_id, day, hour)
        )
    except (TypeError, ValueError, OverflowError):
        return None
    if min(aid, mid, eid, d) < 1 or not 0 <= h < 24:
        return None
    return {
        "account_id": aid, "mask_id": mid, "mask": str(mask or "")[:70],
        "event_id": eid, "day": d, "hour": h,
    }


def normalize(raw):
    if not hasattr(raw, "get"):
        return fresh()
    try:
        d = max(0, int(raw.get("day") or 0))
    except (ValueError, TypeError, OverflowError):
        d = 0
    result = fresh(d)
    for name in ("review", "calibration", "release", "attestation", "audit"):
        row = raw.get(name)
        if not hasattr(row, "get"):
            continue
        signed = _signed(
            row.get("account_id"), row.get("mask_id"), row.get("mask"),
            row.get("event_id"), row.get("day"), row.get("hour"),
        )
        if not signed or signed["day"] != d:
            continue
        if name == "review":
            if row.get("choice") not in CHOICES:
                continue
            signed["choice"] = row["choice"]
        if name == "audit":
            source_id = row.get("review_event_id")
            if type(source_id) is not int or source_id < 1:
                continue
            if row.get("review_choice") not in CHOICES:
                continue
            review = result["review"]
            if (not review or source_id != review["event_id"]
                    or row["review_choice"] != review["choice"]
                    or signed["account_id"] == review["account_id"]
                    or signed["hour"] < review["hour"]):
                continue
            signed["review_event_id"] = source_id
            signed["review_choice"] = row["review_choice"]
        if name == "attestation":
            try:
                review_id = int(row.get("review_event_id"))
                calibration_id = int(row.get("calibration_event_id"))
            except (TypeError, ValueError, OverflowError):
                continue
            if (review_id < 1 or calibration_id < 1
                    or isinstance(row.get("review_event_id"), bool)
                    or isinstance(row.get("calibration_event_id"), bool)):
                continue
            signed["review_event_id"] = review_id
            signed["calibration_event_id"] = calibration_id
        result[name] = signed
    try:
        history = list(raw.get("history") or [])
    except (TypeError, ValueError):
        history = []
    # Bounded prior-day records. No stored character-authored prose.
    result["history"] = [
        copy.deepcopy(row) for row in history[-MAX_HISTORY * 2:]
        if hasattr(row, "get") and isinstance(row.get("day"), int)
        and 0 < row["day"] < d
    ][-MAX_HISTORY:]
    return result


def refresh(raw, day):
    state = normalize(raw)
    day = int(day)
    if day < 1:
        raise ValueError("Village day must be positive.")
    if day <= state["day"]:
        return state
    if state["day"] >= 1 and any(state[k] for k in
                                 ("review", "calibration", "release", "attestation", "audit")):
        old = {k: copy.deepcopy(state[k]) for k in
               ("review", "calibration", "release", "attestation", "audit")}
        old["day"] = state["day"]
        old["unresolved_hold"] = suspended(state, state["day"])
        state["history"].append(old)
    old_history = state["history"][-MAX_HISTORY:]
    state = fresh(day)
    state["history"] = old_history
    return state


def suspended(raw, day):
    state = normalize(raw)
    return bool(
        state["day"] == int(day)
        and state["review"] and state["review"]["choice"] == "hold"
        and not state["calibration"]
        and not state["release"]
    )


def verified_merchant_review(review, source):
    """Check the canonical completed Merchant decision, not a copied receipt."""
    if not isinstance(review, Mapping) or not isinstance(source, Mapping):
        return False
    actor, payload, result = (
        source.get("actor"), source.get("payload"), source.get("consequence")
    )
    if not all(isinstance(row, Mapping) for row in (actor, payload, result)):
        return False
    choice = review.get("choice")
    if choice not in CHOICES:
        return False
    if type(source.get("id")) is not int or source["id"] < 1:
        return False
    if source.get("status") != "complete" or source.get("kind") != "village.market_" + choice:
        return False
    if type(review.get("event_id")) is not int or source["id"] != review["event_id"]:
        return False
    if any(type(review.get(k)) is not int or review[k] < 1 for k in
           ("account_id", "mask_id", "day")):
        return False
    if type(review.get("hour")) is not int or not 0 <= review["hour"] < 24:
        return False
    if any(type(actor.get(k)) is not int or actor[k] != review[k] for k in
           ("account_id", "mask_id")):
        return False
    if actor.get("mask") != review.get("mask"):
        return False
    return (
        payload.get("action") == choice
        and payload.get("professional_calling") == "merchant"
        and payload.get("location") == "Market Lane"
        and type(payload.get("day")) is int
        and payload["day"] == review["day"]
        and type(payload.get("hour")) is int
        and payload["hour"] == review["hour"]
        and result.get("action") == choice
        and type(result.get("review_event_id")) is int
        and result["review_event_id"] == source["id"]
    )


def apply(raw, action, *, day, hour, account_id, mask_id, mask, event_id):
    state = refresh(raw, day)
    if int(day) < state["day"]:
        return state, False, "A later village day is already recorded."
    signed = _signed(account_id, mask_id, mask, event_id, day, hour)
    if signed is None:
        return state, False, "A signed account, event and village time are required."

    if action in CHOICES:
        if state["review"]:
            return state, False, "The Merchant's decision is recorded for today."
        if action == "hold" and state["calibration"]:
            return state, False, "The scale was already calibrated today."
        signed["choice"] = action
        state["review"] = signed
    elif action == "calibrate":
        if state["calibration"]:
            return state, False, "The scale has already been calibrated today."
        state["calibration"] = signed
    elif action == "release":
        if not suspended(state, day):
            return state, False, "There is no active market hold to release."
        state["release"] = signed
    elif action == "audit":
        review = state["review"]
        if not review:
            return state, False, "A completed Merchant decision is needed before an independent audit."
        if state["audit"]:
            return state, False, "The Merchant decision has already been audited today."
        if signed["account_id"] == review["account_id"]:
            return state, False, "A separate account must audit the Merchant decision."
        if signed["hour"] < review["hour"]:
            return state, False, "The audit cannot precede the Merchant decision."
        signed["review_event_id"] = review["event_id"]
        signed["review_choice"] = review["choice"]
        state["audit"] = signed
    elif action == "attest":
        if not state["review"] or not state["calibration"]:
            return state, False, (
                "A documented Merchant decision and Smith calibration "
                "are both needed for an attestation."
            )
        if state["attestation"]:
            return state, False, "The Chronicler has already attested today's record."
        signed["review_event_id"] = state["review"]["event_id"]
        signed["calibration_event_id"] = state["calibration"]["event_id"]
        state["attestation"] = signed
    else:
        return state, False, "Unknown market action."
    return state, True, None


def public_lines(raw, day):
    state = refresh(raw, day)
    lines = ["|wMarket Lane: standards and trades|n"]
    if state["day"] > int(day):
        lines.append("A later village record is already held; the clock cannot be rewound.")
        return lines
    if suspended(state, day):
        lines.append(
            "Distribution of civic construction kits is temporarily on hold. "
            "The Merchant challenged the crooked scale's disputed weights. "
            "A Smith can calibrate it, or a Merchant can release the hold."
        )
    elif state["calibration"]:
        lines.append(
            "The market scale has been physically recalibrated today. "
            "The civic material table can distribute its remaining stock."
        )
    elif state["review"] and state["review"]["choice"] == "honor":
        lines.append(
            "The Merchant agreed to honor the posted figures despite their "
            "discrepancy. Distribution continues; the scale is still crooked."
        )
    else:
        lines.append(
            "The market scale is crooked and two chalk prices disagree. "
            "The public civic material table remains accessible."
        )
    if state["review"]:
        row = state["review"]
        lines.append(
            f"Merchant {row['mask']} chose {row['choice']} on day "
            f"{row['day']} (event {row['event_id']})."
        )
    if state["calibration"]:
        row = state["calibration"]
        lines.append(
            f"Smith {row['mask']} calibrated the scale "
            f"(event {row['event_id']})."
        )
    if state["release"]:
        row = state["release"]
        lines.append(
            f"Merchant {row['mask']} released the hold "
            f"(event {row['event_id']})."
        )
    if state["audit"]:
        row = state["audit"]
        lines.append(
            f"Chronicler {row['mask']} independently audited Merchant "
            f"{row['review_choice']} (source event {row['review_event_id']}, "
            f"audit event {row['event_id']})."
        )
    if state["attestation"]:
        row = state["attestation"]
        lines.append(
            f"Chronicler {row['mask']} attested both source events "
            f"(event {row['event_id']})."
        )
    if state["history"]:
        recent = state["history"][-1]
        lines.append(
            f"Prior recorded day {recent['day']}: "
            + ("unresolved market hold at day's end"
               if recent.get("unresolved_hold") else "record preserved")
            + "."
        )
    lines.append(
        "At Market Lane, examine the physical market scale today. "
        "Merchants: |wtrade honor|n, |wtrade hold|n or |wtrade release|n. "
        "Smiths: |wtrade calibrate|n. Chroniclers: |wtrade audit|n "
        "after a Merchant decision, or |wtrade attest|n after both sources exist. Use |wtrade|n to review the evidence."
    )
    return lines

def personal_agenda(raw, day, mask_id):
    """Resume only this character's signed Market Lane standards decisions.

    Read the established public board and bounded history. This is a
    read-only view, not a new quest flag, stock store, or permission grant.
    """
    if type(day) is not int or day < 1 or type(mask_id) is not int or mask_id < 1:
        return []
    state = refresh(raw, day)
    if state["day"] != day:
        return []

    own = {
        name: bool(state[name] and state[name]["mask_id"] == mask_id)
        for name in ("review", "calibration", "release", "attestation", "audit")
    }
    lines = []
    if own["review"]:
        if state["review"]["choice"] == "hold":
            if suspended(state, day):
                lines.append(
                    "Market Lane: your Merchant market hold remains active. "
                    "Return to the physical scale and use |wtrade release|n "
                    "to reopen civic material distribution, or ask a Smith "
                    "to calibrate the scale."
                )
            elif state["calibration"]:
                lines.append(
                    "Market Lane: your Merchant market hold was resolved "
                    "when a Smith calibrated the scale. Distribution resumed."
                )
            else:
                lines.append(
                    "Market Lane: your Merchant market hold was released. "
                    "Distribution resumed; no second release is needed."
                )
        else:
            lines.append(
                "Market Lane: your Merchant decision to honor the disputed "
                "prices is recorded today; distribution remains available."
            )
    if own["calibration"]:
        lines.append(
            "Market Lane: your Smith calibration corrected the physical "
            "scale today. " + (
                "A Chronicler can attest both source events."
                if state["review"] and not state["attestation"]
                else "No repeat calibration is needed."
            )
        )
    if own["release"]:
        lines.append(
            "Market Lane: your Merchant release of the hold is recorded; "
            "the public material table is open again."
        )
    if own["audit"]:
        lines.append(
            "Market Lane: your independent Chronicler audit of the "
            "Merchant decision is on the public record today."
        )
    if own["attestation"]:
        lines.append(
            "Market Lane: your Chronicler attestation of both source events "
            "is recorded; no repeat attestation is needed."
        )
    if lines:
        return lines

    # Only yesterday's personal work belongs in a returning player's agenda.
    # Prior-day decisions are history, never an actionable current-day hold.
    for old in reversed(state["history"]):
        if old.get("day") != day - 1:
            continue
        if any(
            old.get(name) and old[name].get("mask_id") == mask_id
            for name in ("review", "calibration", "release", "attestation", "audit")
        ):
            return [
                "Market Lane: your previous day's standards work is archived. "
                "Today's scale decisions are separate; use |wtrade|n at "
                "Market Lane to inspect the current record."
            ]
    return []
