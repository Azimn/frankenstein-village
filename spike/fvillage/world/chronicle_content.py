"""Playable Chronicler content for Section 3.23.

Revision by Evidence lets a player bring evidence their current mask actually
discovered back to an existing Chronicle entry. The result is an append-only
annotation with explicit provenance. The original entry text and claim status
remain unchanged.
"""

from __future__ import annotations

from collections.abc import Mapping

from world.publications import annotate_chronicle, get_chronicle_entry
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
