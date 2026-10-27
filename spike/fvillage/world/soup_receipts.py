"""GDD-EDGE-01: a consented kitchen receipt and independent public account.

Pure transitions on the existing finite soup-pantry history. No guest names,
private lodging records, new ledger, or claim of objective patron behavior.
"""
from __future__ import annotations

from world import soup_state


def _positive(value):
    return type(value) is int and value > 0


def _signed(actor):
    return (
        isinstance(actor, dict)
        and _positive(actor.get("account_id"))
        and _positive(actor.get("mask_id"))
        and isinstance(actor.get("mask"), str)
        and bool(actor["mask"].strip())
    )


def _event(event, kind, event_id):
    return (
        isinstance(event, dict)
        and event.get("id") == event_id
        and event.get("kind") == kind
        and event.get("status") == "complete"
        and isinstance(event.get("actor"), dict)
        and isinstance(event.get("payload"), dict)
        and isinstance(event.get("consequence"), dict)
    )


def _batch(state, event_id):
    return next(
        (row for row in state["history"]
         if row.get("cook_event_id") == event_id), None
    )


def _clock_ok(day, hour):
    return _positive(day) and type(hour) is int and 0 <= hour <= 23


def _source_valid(row, cooked, prepared):
    if not _event(cooked, "professional.innkeep_soup_cooked", row["cook_event_id"]):
        return False
    if not _event(prepared, "professional.innkeep_soup_prepared", row["prep_event_id"]):
        return False
    cp, cc, ca = cooked["payload"], cooked["consequence"], cooked["actor"]
    pp, pc, pa = prepared["payload"], prepared["consequence"], prepared["actor"]
    return (
        _signed(ca)
        and _signed(pa)
        and ca["mask_id"] == row["maker_id"]
        and ca["mask"] == row["maker"]
        and cp.get("day") == row["day"]
        and cp.get("base") == row["base"]
        and cp.get("seasoning") == row["seasoning"]
        and cp.get("prep_event_id") == row["prep_event_id"]
        and cp.get("packet_id") == pc.get("packet_id")
        and cc.get("source_event_id") == row["prep_event_id"]
        and cc.get("quality") == row["quality"]
        and _positive(cc.get("bowl_id"))
        and _positive(cc.get("pantry_room_id"))
        and cc.get("pantry_room_id") == pp.get("room_id")
        and _positive(pp.get("room_id"))
        and pp.get("day") <= row["day"]
        and pp.get("base") == row["base"]
        and pp.get("seasoning") == row["seasoning"]
        and _positive(pc.get("packet_id"))
        and prepared["id"] < cooked["id"]
    )


def _valid_actor(actor, cooked):
    return (
        _signed(actor)
        and actor["account_id"] == cooked["actor"].get("account_id")
        and actor["mask_id"] == cooked["actor"].get("mask_id")
        and actor["mask"] == cooked["actor"].get("mask")
    )


def authorize(raw, *, batch_id, actor, day, hour, event_id, cooked, prepared):
    """Innkeep consents to disclosing only a real cooked batch's house facts."""
    state = soup_state.pantry(raw, day)
    row = _batch(state, batch_id)
    if not row:
        return state, None, "No such real cooked batch is in the tavern history."
    if not _clock_ok(day, hour) or not _positive(event_id):
        return state, None, "The receipt needs a valid village time and event."
    if day < row["day"] or day > row["day"] + 2:
        return state, None, "That batch is outside the house receipt window."
    if row.get("consent"):
        return state, None, "That batch already has a signed disclosure decision."
    if not _source_valid(row, cooked, prepared) or not _valid_actor(actor, cooked):
        return state, None, "The cooked batch has no matching signed Innkeep source."
    if event_id <= batch_id:
        return state, None, "A house receipt must follow the completed cooking event."
    row["consent"] = {
        "event_id": event_id, "cook_event_id": batch_id,
        "account_id": actor["account_id"], "mask_id": actor["mask_id"],
        "mask": actor["mask"], "day": day, "hour": hour,
        "scope": "public_kitchen_batch_only",
    }
    return state, dict(row["consent"]), None


def publish(raw, *, batch_id, actor, day, hour, event_id,
            cooked, prepared, consent_event):
    """Independent Chronicler publishes a qualified, consent-bounded receipt."""
    state = soup_state.pantry(raw, day)
    row = _batch(state, batch_id)
    if not row:
        return state, None, "No such real cooked batch is in the tavern history."
    consent = row.get("consent")
    if not consent:
        return state, None, "The Innkeep has not authorized a public house receipt."
    if row.get("publication"):
        return state, None, "This house receipt is already published."
    if not _clock_ok(day, hour) or not _positive(event_id):
        return state, None, "Publication needs a valid village time and event."
    if day < consent["day"] or day > row["day"] + 2:
        return state, None, "That house receipt is outside its publication window."
    if day == consent["day"] and hour < consent["hour"]:
        return state, None, "Publication cannot precede the Innkeep's consent."
    if not _signed(actor) or actor["account_id"] == consent["account_id"]:
        return state, None, "An independent Chronicler account must publish."
    if not _source_valid(row, cooked, prepared):
        return state, None, "The original cooking provenance cannot be verified."
    if not _event(
        consent_event, "professional.innkeep_house_receipt_disclosed",
        consent["event_id"]
    ):
        return state, None, "The Innkeep disclosure event is missing or incomplete."
    source_actor = consent_event["actor"]
    source_payload = consent_event["payload"]
    source_consequence = consent_event["consequence"]
    if (
        not _valid_actor(source_actor, cooked)
        or source_actor["account_id"] != consent["account_id"]
        or source_actor["mask_id"] != consent["mask_id"]
        or source_actor["mask"] != consent["mask"]
        or source_payload.get("cook_event_id") != batch_id
        or source_payload.get("day") != consent["day"]
        or source_payload.get("hour") != consent["hour"]
        or source_payload.get("scope") != consent["scope"]
        or source_consequence.get("cook_event_id") != batch_id
        or source_consequence.get("scope") != consent["scope"]
        or event_id <= consent["event_id"]
    ):
        return state, None, "The house disclosure source does not match its signed consent."
    row["publication"] = {
        "event_id": event_id, "cook_event_id": batch_id,
        "consent_event_id": consent["event_id"],
        "account_id": actor["account_id"], "mask_id": actor["mask_id"],
        "mask": actor["mask"], "day": day, "hour": hour,
        "scope": consent["scope"],
    }
    return state, dict(row["publication"]), None


def public_lines(raw, day):
    state = soup_state.pantry(raw, day)
    lines = ["|wConsented public house receipts|n"]
    published = [
        row for row in state["history"] if row.get("publication")
    ]
    if not published:
        return "\n".join(lines + [
            "No kitchen receipt has been independently published. "
            "A cooked batch alone is not a public guest account."
        ])
    for row in published[-10:]:
        consent = row["consent"]
        review = row["publication"]
        lines.append(
            f"* Day {row['day']}: {row['base']} and {row['seasoning']} "
            f"cooked by {row['maker']}, recorded kitchen quality {row['quality']}; "
            f"cook event {row['cook_event_id']}, consent event "
            f"{consent['event_id']}, Chronicler {review['mask']} "
            f"publication event {review['event_id']}."
        )
    lines.append(
        "These are consented kitchen production facts, not a guest list, "
        "customer satisfaction finding, or proof of private behavior."
    )
    return "\n".join(lines)
