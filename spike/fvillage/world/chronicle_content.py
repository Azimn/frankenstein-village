"""Playable Chronicler content for Section 3.23.

Revision by Evidence lets a player bring evidence their current mask actually
discovered back to an existing Chronicle entry. The result is an append-only
annotation with explicit provenance. The original entry text and claim status
remain unchanged.
"""

from __future__ import annotations

from collections.abc import Mapping

from world.publications import (
    annotate_chronicle,
    chronicle_entries,
    get_chronicle_entry,
    get_public_record_registry,
)
from world.situations import (
    TITHE_ID,
    TORN_CHRONICLE_ID,
    TEMPLATES,
    known_situations,
    resolve_situation_subject,
    situation_status_for_player,
)


def _evidence_ref(stable_id, evidence):
    return {
        "situation_id": stable_id,
        "evidence_id": evidence["id"],
        "label": evidence["label"],
        "provenance": evidence["provenance"],
        "summary": evidence["summary"],
    }


def evidence_reference_token(evidence_ref):
    """Return a stable player-facing token for one evidence reference."""
    aliases = {
        TITHE_ID: "strongbox",
        TORN_CHRONICLE_ID: "chronicle",
    }
    subject = aliases.get(
        evidence_ref.get("situation_id"),
        evidence_ref.get("situation_id"),
    )
    return f"{subject}/{evidence_ref.get('evidence_id')}"


def _entry_situation_ids(entry):
    """Return situation IDs established by the entry's canonical event sources."""
    from world.events import get_event_ledger

    ledger = get_event_ledger()
    situation_ids = set()
    for event_id in entry.get("source_event_ids") or []:
        event = ledger.get_event(int(event_id))
        if not event:
            continue
        payload = event.get("payload") or {}
        if not isinstance(payload, Mapping):
            try:
                payload = dict(payload)
            except Exception:
                payload = {}
        stable_id = payload.get("situation_id")
        if stable_id:
            situation_ids.add(str(stable_id))
    return situation_ids


def revision_evidence_for_player(player, entry_id=None):
    """Return discovered evidence relevant to the selected Chronicle entry."""
    relevant = None
    if entry_id is not None:
        entry = get_chronicle_entry(entry_id)
        if not entry:
            return []
        relevant = _entry_situation_ids(entry)

    refs = []
    for situation, knowledge in known_situations(player):
        stable_id = situation["id"]
        if relevant is not None and stable_id not in relevant:
            continue
        template = TEMPLATES.get(stable_id) or {}
        for evidence_id in knowledge.get("evidence") or []:
            evidence = (template.get("evidence") or {}).get(evidence_id)
            if not evidence:
                continue
            refs.append(
                _evidence_ref(
                    stable_id,
                    {"id": evidence_id, **evidence},
                )
            )
    return refs


def resolve_evidence_reference(player, subject, evidence_id):
    stable_id = resolve_situation_subject(subject)
    if not stable_id:
        return None, "No known situation matches that evidence source."

    status = situation_status_for_player(player, stable_id)
    if not status:
        return None, "Your current mask has not discovered that situation."

    wanted = str(evidence_id or "").strip().lower().replace(" ", "_")
    for evidence in status.get("evidence") or []:
        aliases = {
            str(evidence["id"]).lower(),
            str(evidence["label"]).lower().replace(" ", "_"),
        }
        if wanted in aliases:
            return _evidence_ref(stable_id, evidence), None

    return (
        None,
        "Your current mask has not discovered that evidence. The Chronicle "
        "cannot cite information you do not possess.",
    )


def _already_cited(entry, evidence_ref):
    wanted = (
        evidence_ref["situation_id"],
        evidence_ref["evidence_id"],
    )
    for annotation in entry.get("annotations") or []:
        for existing in annotation.get("source_evidence_refs") or []:
            current = (
                existing.get("situation_id"),
                existing.get("evidence_id"),
            )
            if current == wanted:
                return True
    return False


def submit_evidence_revision(player, entry_id, subject, evidence_id):
    """Append one provenance-bearing evidence annotation to a Chronicle entry."""
    entry = get_chronicle_entry(entry_id)
    if not entry:
        return None, "No such Chronicle entry is in the public index."

    evidence_ref, error = resolve_evidence_reference(
        player,
        subject,
        evidence_id,
    )
    if error:
        return None, error

    linked_situations = _entry_situation_ids(entry)
    if not linked_situations:
        return (
            None,
            "That Chronicle entry has no situation-linked event provenance, so "
            "Revision by Evidence cannot attach unrelated material to it.",
        )
    if evidence_ref["situation_id"] not in linked_situations:
        return (
            None,
            "That evidence belongs to a different situation than this Chronicle "
            "entry. The archive will not imply a connection the source record "
            "does not establish.",
        )

    if _already_cited(entry, evidence_ref):
        return (
            None,
            "That evidence is already cited on this Chronicle entry. The archive "
            "does not duplicate the same provenance merely to make it look stronger.",
        )

    text = (
        f"Evidence submitted by {player.key}: {evidence_ref['label']}. "
        f"{evidence_ref['summary']} The Chronicle appends this evidence with its "
        "provenance; the original entry and its prior claim status remain unchanged."
    )
    updated = annotate_chronicle(
        entry["id"],
        text,
        author="Chronicler",
        source_evidence_refs=[evidence_ref],
        source_mask_id=getattr(player, "id", None),
        source_mask=getattr(player, "key", None),
        annotation_type="evidence_revision",
    )
    if not updated:
        return None, "The Chronicle could not append that evidence."
    return updated, None


MIN_REFUSAL_SUPPORTERS = 3
REFUSAL_CONFIDENCE_FLOOR = 0.50


def _refusal_state():
    registry = get_public_record_registry()
    if registry.db.chronicle_refusals is None:
        registry.db.chronicle_refusals = []
    if registry.db.next_chronicle_refusal_id is None:
        registry.db.next_chronicle_refusal_id = 1
    return registry


def chronicle_refusal_for_rumor(rumor_id):
    """Return an existing institutional refusal for one rumor root."""
    try:
        rumor_id = int(rumor_id)
    except (TypeError, ValueError):
        return None
    registry = _refusal_state()
    for refusal in registry.db.chronicle_refusals or []:
        if refusal.get("rumor_id") == rumor_id:
            return dict(refusal)
    return None


def _verified_chronicle_for_rumor(root):
    """Return an event-backed Chronicle entry that already establishes the fact."""
    event_id = root.get("original_event_id")
    if event_id is None:
        return None
    for entry in chronicle_entries():
        if (
            entry.get("claim_status") == "verified_event"
            and int(event_id) in [
                int(source_id)
                for source_id in (entry.get("source_event_ids") or [])
            ]
        ):
            return entry
    return None


def _resident_supporters(rumor_id):
    """Residents currently carrying the rumor with committed acceptance."""
    from world.residents import all_residents
    from world.rumors import get_rumor_registry

    rumor_registry = get_rumor_registry()
    supporters = []
    for npc in all_residents():
        belief = rumor_registry.belief_for(npc, rumor_id)
        if not belief:
            continue
        if float(belief.get("confidence") or 0.0) < REFUSAL_CONFIDENCE_FLOOR:
            continue
        supporters.append(
            {
                "resident_id": npc.db.resident_id,
                "object_id": npc.id,
                "name": npc.key,
                "confidence": float(belief.get("confidence") or 0.0),
            }
        )
    return supporters


def petition_refused_entry(player, rumor_id):
    """Ask the Chronicle to canonize a popular rumor and preserve its refusal.

    The Chronicle may canonize that a claim was popular and refused without
    canonizing the claim itself. The refusal becomes a canonical institutional
    event, while the rumor remains a rumor.
    """
    from world.events import publish_world_event
    from world.publications import _clock
    from world.rumors import get_rumor_registry

    try:
        rumor_id = int(rumor_id)
    except (TypeError, ValueError):
        return None, "That is not a valid rumor reference."

    rumor_registry = get_rumor_registry()
    root = rumor_registry.get_rumor(rumor_id)
    belief = rumor_registry.belief_for(player, rumor_id)
    if not root or not belief:
        return None, "You cannot petition over a rumor your current mask has not heard."
    if root.get("privacy") != "public":
        return None, "Private information cannot be turned into a public Chronicle petition."

    existing = chronicle_refusal_for_rumor(rumor_id)
    if existing:
        entry = get_chronicle_entry(existing.get("chronicle_entry_id"))
        return {
            "refusal": existing,
            "entry": entry,
            "created": False,
        }, None

    verified = _verified_chronicle_for_rumor(root)
    if verified:
        return (
            None,
            f"Chronicle C{verified['id']} already has event-backed authority for "
            "that underlying occurrence; it is not eligible for a refused-entry case.",
        )

    supporters = _resident_supporters(rumor_id)
    if len(supporters) < MIN_REFUSAL_SUPPORTERS:
        return (
            None,
            f"That rumor has only {len(supporters)} committed resident carriers. "
            f"The Refused Entry case requires at least {MIN_REFUSAL_SUPPORTERS} "
            "people already treating the claim as credible public knowledge.",
        )

    registry = _refusal_state()
    refusal_id = int(registry.db.next_chronicle_refusal_id or 1)
    day, hour = _clock()
    supporter_ids = [item["resident_id"] for item in supporters]
    public_summary = (
        f"The Chronicler declined a petition to enter rumor R{rumor_id} as settled "
        f"history. {len(supporters)} residents currently carry the claim with "
        "committed confidence, but repetition is not evidence. The refusal records "
        "an archival boundary, not a verdict on whether the rumor is true."
    )
    event = publish_world_event(
        "chronicle.refused_entry",
        actor=player,
        payload={
            "headline": f"Chronicle Refuses Popular Rumor R{rumor_id}",
            "public_summary": public_summary,
            "harbinger": True,
            "chronicle_eligible": False,
            "source_rumor_id": rumor_id,
            "resident_ids": supporter_ids,
            "supporter_count": len(supporters),
            "reaction": "angered_by_refusal",
            "refusal_id": refusal_id,
        },
    )

    entry = {
        "id": int(registry.db.next_chronicle_id or 1),
        "entry_type": "refusal_record",
        "title": f"Refused Entry: Rumor R{rumor_id}",
        "text": (
            f"A petition asked the Chronicle to canonize the claim: "
            f"\"{root.get('claim') or ''}\" The Chronicler refused. "
            f"At the time of refusal, {len(supporters)} residents carried the "
            "claim strongly enough to count as committed supporters. This entry "
            "canonizes the petition, the refusal, and the public dispute only. "
            "It does not certify the rumor as true or false."
        ),
        "claim_status": "refused_canonization",
        "source_event_ids": [event["id"]],
        "source_rumor_ids": [rumor_id],
        "source_deposition_ids": [],
        "recorded_day": int(day),
        "recorded_hour": int(hour),
        "annotations": [],
        "refusal_id": refusal_id,
    }
    registry.db.next_chronicle_id = entry["id"] + 1
    entries = list(registry.db.chronicle_entries or [])
    entries.append(entry)
    registry.db.chronicle_entries = entries

    refusal = {
        "id": refusal_id,
        "rumor_id": rumor_id,
        "claim": root.get("claim"),
        "petitioned_by_mask_id": getattr(player, "id", None),
        "petitioned_by_mask": getattr(player, "key", None),
        "day": int(day),
        "hour": int(hour),
        "supporter_count": len(supporters),
        "supporter_resident_ids": supporter_ids,
        "supporter_confidence_floor": REFUSAL_CONFIDENCE_FLOOR,
        "reason": "popularity_without_archival_evidence",
        "status": "refused",
        "event_id": event["id"],
        "chronicle_entry_id": entry["id"],
        "harbinger_story_id": (
            (event.get("publications") or {}).get("harbinger_story_id")
        ),
    }
    registry.db.next_chronicle_refusal_id = refusal_id + 1
    refusals = list(registry.db.chronicle_refusals or [])
    refusals.append(refusal)
    registry.db.chronicle_refusals = refusals
    return {
        "refusal": dict(refusal),
        "entry": dict(entry),
        "created": True,
    }, None
