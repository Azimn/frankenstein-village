"""Playable Harbinger editorial conflicts for Section 3.22.

"Stop the Press" turns incompatible signed Chronicle depositions into a
Harbinger copy-desk decision without converting any account into objective
truth. A player may select one attributed version for publication. If nobody
acts before the next morning issue, the paper prints the disagreement itself.

The canonical event ledger remains objective history. These records own only
editorial state and published interpretation.
"""

from __future__ import annotations

import hashlib

from world.publications import (
    depositions_for_rumor,
    get_public_record_registry,
    get_story,
)


def _clock():
    from world.publications import _clock as publication_clock

    return publication_clock()


def _humanize(value):
    return str(value or "").replace("_", " ").replace(".", " ").strip()


def _ensure_state():
    registry = get_public_record_registry()
    if registry.db.harbinger_conflicts is None:
        registry.db.harbinger_conflicts = []
    if registry.db.next_harbinger_conflict_id is None:
        registry.db.next_harbinger_conflict_id = 1
    return registry


def _deadline_after(day, hour):
    day = int(day)
    hour = int(hour)
    if hour < 8:
        return day, 8
    return day + 1, 8


def _distinct_accounts(rumor_id):
    accounts = []
    seen = set()
    for deposition in depositions_for_rumor(rumor_id):
        claim = str(deposition.get("claim") or "").strip()
        if not claim or claim in seen:
            continue
        seen.add(claim)
        accounts.append(
            {
                "deposition_id": deposition["id"],
                "source_mask_id": deposition.get("source_mask_id"),
                "source_mask": deposition.get("source_mask"),
                "claim": claim,
            }
        )
    return accounts


def harbinger_conflicts():
    registry = _ensure_state()
    return [dict(item) for item in (registry.db.harbinger_conflicts or [])]


def get_harbinger_conflict(conflict_id):
    try:
        conflict_id = int(conflict_id)
    except (TypeError, ValueError):
        return None
    for conflict in harbinger_conflicts():
        if conflict.get("id") == conflict_id:
            return conflict
    return None


def open_harbinger_conflicts():
    return [
        conflict
        for conflict in harbinger_conflicts()
        if conflict.get("status") == "open"
    ]


def ensure_harbinger_conflict(rumor_id):
    """Open one copy-desk conflict from incompatible signed accounts."""
    try:
        rumor_id = int(rumor_id)
    except (TypeError, ValueError):
        return None, "That is not a valid rumor reference."

    from world.rumors import get_rumor_registry

    root = get_rumor_registry().get_rumor(rumor_id)
    if not root:
        return None, f"No public rumor R{rumor_id} exists."

    accounts = _distinct_accounts(rumor_id)
    if len(accounts) < 2:
        return (
            None,
            "The copy desk needs at least two incompatible signed Chronicle "
            "accounts before this can become a Stop the Press decision.",
        )

    registry = _ensure_state()
    for existing in registry.db.harbinger_conflicts or []:
        if existing.get("rumor_id") == rumor_id:
            return dict(existing), None

    day, hour = _clock()
    deadline_day, deadline_hour = _deadline_after(day, hour)
    subject = _humanize(root.get("subject") or f"rumor R{rumor_id}")
    if str(root.get("subject") or "").startswith("canon:"):
        subject = f"rumor R{rumor_id}"

    conflict = {
        "id": int(registry.db.next_harbinger_conflict_id or 1),
        "rumor_id": rumor_id,
        "subject": subject,
        "accounts": accounts,
        "status": "open",
        "opened_day": int(day),
        "opened_hour": int(hour),
        "deadline_day": int(deadline_day),
        "deadline_hour": int(deadline_hour),
        "decision_deposition_id": None,
        "decided_by_mask_id": None,
        "decided_by_mask": None,
        "decided_day": None,
        "decided_hour": None,
        "story_id": None,
        "resolution": None,
    }
    registry.db.next_harbinger_conflict_id = conflict["id"] + 1
    conflicts = list(registry.db.harbinger_conflicts or [])
    conflicts.append(conflict)
    registry.db.harbinger_conflicts = conflicts
    return dict(conflict), None


def _replace_conflict(replacement):
    registry = _ensure_state()
    conflicts = [dict(item) for item in (registry.db.harbinger_conflicts or [])]
    for index, conflict in enumerate(conflicts):
        if conflict.get("id") == replacement.get("id"):
            conflicts[index] = dict(replacement)
            registry.db.harbinger_conflicts = conflicts
            return dict(replacement)
    return None


def _queue_conflict_story(conflict, *, chosen_account=None):
    registry = _ensure_state()
    if conflict.get("story_id"):
        from world.publications import get_story

        existing = get_story(conflict["story_id"])
        if existing:
            return existing

    day, hour = _clock()
    accounts = list(conflict.get("accounts") or [])
    subject = conflict.get("subject") or f"rumor R{conflict['rumor_id']}"

    if chosen_account is not None:
        source = chosen_account.get("source_mask") or "A signed witness"
        claim = chosen_account.get("claim") or "No claim was preserved."
        body = (
            f"{source} submitted one of several incompatible signed accounts: "
            f"\"{claim}\" The Harbinger prints this version as the copy-desk "
            "selection for the issue. Other signed accounts conflict with it, "
            "and publication does not certify the claim as fact."
        )
        basis = "contested_report"
        headline = f"Disputed Report: {subject.title()}"
        source_deposition_id = chosen_account.get("deposition_id")
        confidence = 0.50
    else:
        excerpts = []
        for account in accounts[:3]:
            source = account.get("source_mask") or "A signed witness"
            excerpts.append(f'{source}: "{account.get("claim") or ""}"')
        body = (
            "Incompatible signed accounts reached the copy desk before press "
            f"time. {'; '.join(excerpts)}. The Harbinger prints the "
            "disagreement without selecting any version as settled fact."
        )
        basis = "disputed_report"
        headline = f"Accounts Conflict: {subject.title()}"
        source_deposition_id = None
        confidence = 0.45

    story = {
        "id": int(registry.db.next_story_id or 1),
        "source_event_id": None,
        "source_rumor_id": int(conflict["rumor_id"]),
        "source_deposition_id": source_deposition_id,
        "headline": headline,
        "body": body,
        "basis": basis,
        "confidence": confidence,
        "status": "pending",
        "created_day": int(day),
        "created_hour": int(hour),
        "published_edition_id": None,
        "corrections": [],
        "editorial_conflict_id": int(conflict["id"]),
    }
    registry.db.next_story_id = story["id"] + 1
    drafts = list(registry.db.harbinger_drafts or [])
    drafts.append(story)
    registry.db.harbinger_drafts = drafts
    return dict(story)


def choose_harbinger_conflict(player, conflict_id, deposition_id):
    """Select one attributed account for publication before the deadline."""
    conflict = get_harbinger_conflict(conflict_id)
    if not conflict:
        return None, None, "No such Stop the Press item is on the copy desk."
    if conflict.get("status") != "open":
        return (
            conflict,
            None,
            "That copy-desk decision is already closed. Its original editorial "
            "record remains preserved.",
        )

    try:
        deposition_id = int(deposition_id)
    except (TypeError, ValueError):
        return conflict, None, "Choose one of the listed D<number> accounts."

    chosen = next(
        (
            account
            for account in (conflict.get("accounts") or [])
            if account.get("deposition_id") == deposition_id
        ),
        None,
    )
    if not chosen:
        return conflict, None, "That deposition is not one of the listed accounts."

    story = _queue_conflict_story(conflict, chosen_account=chosen)
    day, hour = _clock()
    replacement = dict(conflict)
    replacement["status"] = "selected"
    replacement["decision_deposition_id"] = deposition_id
    replacement["decided_by_mask_id"] = getattr(player, "id", None)
    replacement["decided_by_mask"] = getattr(player, "key", None)
    replacement["decided_day"] = int(day)
    replacement["decided_hour"] = int(hour)
    replacement["story_id"] = story["id"]
    replacement["resolution"] = "selected_account"
    conflict = _replace_conflict(replacement)
    return conflict, story, None


def resolve_due_harbinger_conflicts(day, hour):
    """Close overdue conflicts without inventing a winning account."""
    day = int(day)
    hour = int(hour)
    resolved = []
    for conflict in open_harbinger_conflicts():
        deadline = (
            int(conflict.get("deadline_day") or 0),
            int(conflict.get("deadline_hour") or 0),
        )
        if (day, hour) < deadline:
            continue

        story = _queue_conflict_story(conflict, chosen_account=None)
        replacement = dict(conflict)
        replacement["status"] = "deadline_neutral"
        replacement["story_id"] = story["id"]
        replacement["resolution"] = "printed_disagreement"
        replacement["decided_day"] = day
        replacement["decided_hour"] = hour
        _replace_conflict(replacement)
        resolved.append(
            {
                "conflict_id": conflict["id"],
                "story_id": story["id"],
            }
        )
    return resolved


def _ensure_correction_state():
    registry = get_public_record_registry()
    if registry.db.harbinger_correction_disputes is None:
        registry.db.harbinger_correction_disputes = []
    if registry.db.next_harbinger_correction_dispute_id is None:
        registry.db.next_harbinger_correction_dispute_id = 1
    return registry


def harbinger_correction_disputes():
    registry = _ensure_correction_state()
    return [
        dict(item)
        for item in (registry.db.harbinger_correction_disputes or [])
    ]


def correction_disputes_for_story(story_id):
    try:
        story_id = int(story_id)
    except (TypeError, ValueError):
        return []
    return [
        item
        for item in harbinger_correction_disputes()
        if item.get("story_id") == story_id
    ]


def _body_hash(body):
    return hashlib.sha256(str(body or "").encode("utf-8")).hexdigest()


def _replace_story(replacement):
    registry = get_public_record_registry()
    drafts = [dict(story) for story in (registry.db.harbinger_drafts or [])]
    for index, story in enumerate(drafts):
        if story.get("id") == replacement.get("id"):
            drafts[index] = dict(replacement)
            registry.db.harbinger_drafts = drafts
            return dict(replacement)
    return None


def submit_correction_dispute(player, story_id, claimed_text):
    """Preserve a correction claim contradicted by the surviving archive copy.

    This implements Section 3.22 THE CORRECTION. The surviving story body is
    immutable. The correction claim is preserved as a separate editorial
    discrepancy and queued for public reporting without being treated as an
    accepted correction.
    """
    try:
        story_id = int(story_id)
    except (TypeError, ValueError):
        return None, "That is not a valid Harbinger story reference."

    claimed_text = str(claimed_text or "").strip()
    if not claimed_text:
        return None, "A correction claim must name the wording you say appeared."

    story = get_story(story_id)
    if not story or story.get("status") != "published":
        return None, "The Correction requires a story from a surviving printed issue."

    surviving_body = str(story.get("body") or "")
    if claimed_text.casefold() in surviving_body.casefold():
        return (
            None,
            "The surviving copy already contains that wording. This case is for "
            "a claimed correction whose alleged original text is absent from the archive.",
        )

    registry = _ensure_correction_state()
    for existing in registry.db.harbinger_correction_disputes or []:
        if (
            existing.get("story_id") == story_id
            and str(existing.get("claimed_text") or "").casefold()
            == claimed_text.casefold()
        ):
            response_story = get_story(existing.get("response_story_id"))
            return {
                "dispute": dict(existing),
                "response_story": response_story,
                "created": False,
            }, None

    day, hour = _clock()
    dispute_id = int(registry.db.next_harbinger_correction_dispute_id or 1)
    archive_hash = _body_hash(surviving_body)
    dispute = {
        "id": dispute_id,
        "story_id": story_id,
        "published_edition_id": story.get("published_edition_id"),
        "claimed_text": claimed_text,
        "surviving_body_hash": archive_hash,
        "claimed_by_mask_id": getattr(player, "id", None),
        "claimed_by_mask": getattr(player, "key", None),
        "day": int(day),
        "hour": int(hour),
        "status": "archive_discrepancy",
        "response_story_id": None,
    }

    response_story = {
        "id": int(registry.db.next_story_id or 1),
        "source_event_id": None,
        "source_rumor_id": None,
        "headline": f"Correction Disputed: {story['headline']}",
        "body": (
            f"A correction claim says Harbinger H{story_id} originally contained "
            f"the wording: \"{claimed_text}\". The surviving archive copy does "
            "not contain that text. The paper records the discrepancy without "
            "rewriting the surviving issue or treating either recollection as "
            "automatically authoritative."
        ),
        "basis": "correction_dispute",
        "confidence": 0.55,
        "status": "pending",
        "created_day": int(day),
        "created_hour": int(hour),
        "published_edition_id": None,
        "corrections": [],
        "correction_dispute_id": dispute_id,
        "disputes_story_id": story_id,
        "surviving_body_hash": archive_hash,
    }
    registry.db.next_story_id = response_story["id"] + 1
    drafts = list(registry.db.harbinger_drafts or [])
    drafts.append(response_story)
    registry.db.harbinger_drafts = drafts

    dispute["response_story_id"] = response_story["id"]
    registry.db.next_harbinger_correction_dispute_id = dispute_id + 1
    disputes = list(registry.db.harbinger_correction_disputes or [])
    disputes.append(dispute)
    registry.db.harbinger_correction_disputes = disputes

    replacement = dict(story)
    claims = list(replacement.get("correction_disputes") or [])
    claims.append({
        "id": dispute_id,
        "claimed_text": claimed_text,
        "claimed_by_mask_id": dispute["claimed_by_mask_id"],
        "claimed_by_mask": dispute["claimed_by_mask"],
        "surviving_body_hash": archive_hash,
        "response_story_id": response_story["id"],
    })
    replacement["correction_disputes"] = claims
    _replace_story(replacement)

    return {
        "dispute": dict(dispute),
        "response_story": dict(response_story),
        "created": True,
    }, None
