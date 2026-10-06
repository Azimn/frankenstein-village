"""Mask-specific private mystery delivery and voluntary disclosure.

Private mysteries enrich social play through information asymmetry. They are
never prerequisites for server-wide progress and never become public merely
because they exist.
"""

from __future__ import annotations

import copy

from evennia import create_script
from evennia.scripts.models import ScriptDB


REGISTRY_KEY = "private_mystery_registry"
HOUNDS_INVITATION_ID = "PRIVATE-HOUNDS-INVITATION"

DEFINITIONS = {
    HOUNDS_INVITATION_ID: {
        "title": "A Private Invitation",
        "source_key": "János",
        "source_regular_key": "janos",
        "trigger_terms": (
            "hound", "hounds", "hunt", "hunting", "contract", "contracts",
        ),
        "followup_terms": (
            "east patrol", "patrol", "invitation", "invite",
        ),
        "invitation_claim": (
            "János invited you to ask him privately about the east patrol. "
            "He said not to turn the invitation into tavern entertainment."
        ),
        "invitation_line": (
            "János studies you a moment before lowering his voice. "
            ""The Hounds keep some things off the bar. If you want to hear "
            "one of them, come back to me and ask about the east patrol. "
            "Do not make a performance of the invitation.""
        ),
        "followup_claim": (
            "The east patrol has found the same chalk ring on three different "
            "shutters before dawn. Each mark was wiped away before the next "
            "patrol, and the Hounds do not agree whether the pattern is a "
            "warning, a route sign, or a prank."
        ),
        "followup_line": (
            "János waits until your question is finished. "Three mornings. "
            "Three different shutters on the east patrol. Same chalk ring, "
            "gone before the next round. Warning, route sign, prank. We do "
            "not know. That last sentence matters.""
        ),
    },
}


def _registry():
    try:
        return ScriptDB.objects.get(db_key=REGISTRY_KEY)
    except ScriptDB.DoesNotExist:
        return create_script(
            "typeclasses.scripts.PrivateMysteryRegistry",
            key=REGISTRY_KEY,
            persistent=True,
        )


def get_private_mystery_registry():
    return _registry()


def ensure_private_mysteries():
    registry = _registry()
    if registry.db.records is None:
        registry.db.records = {}
    return {
        "definition_count": len(DEFINITIONS),
        "mask_count": len(registry.db.records or {}),
    }


def _clock():
    try:
        clock = ScriptDB.objects.get(db_key="village_time")
        return int(clock.db.day or 1), int(
            clock.db.hour if clock.db.hour is not None else 21
        )
    except ScriptDB.DoesNotExist:
        return 1, 21


def _actor_ref(actor):
    if actor is None:
        return None
    account = getattr(actor, "account", None)
    return {
        "mask_id": getattr(actor, "id", None),
        "mask": getattr(actor, "key", None),
        "account_id": getattr(account, "id", None),
    }


def _metric(**deltas):
    registry = _registry()
    metrics = copy.deepcopy(dict(registry.db.metrics or {}))
    for key, value in deltas.items():
        metrics[key] = int(metrics.get(key) or 0) + int(value)
    registry.db.metrics = metrics


def _mask_records(player):
    records = copy.deepcopy(dict(_registry().db.records or {}))
    return records, copy.deepcopy(dict(records.get(str(player.id)) or {}))


def _save_mask_records(player, mask_records):
    registry = _registry()
    records = copy.deepcopy(dict(registry.db.records or {}))
    records[str(player.id)] = copy.deepcopy(mask_records)
    registry.db.records = records
    return copy.deepcopy(mask_records)


def _private_rumor(player, source, *, stage, claim):
    from world.rumors import get_rumor_registry

    registry = get_rumor_registry()
    family = f"private:{HOUNDS_INVITATION_ID}:{player.id}:{stage}"
    rumor = registry.ensure_rumor(
        subject=f"{HOUNDS_INVITATION_ID}:{stage}",
        claim=claim,
        source_actor=getattr(source, "key", "János"),
        source_type="private_invitation",
        original_event_id=None,
        origin_location=getattr(getattr(source, "location", None), "key", None),
        confidence=0.82,
        emotional_charge=0.25,
        privacy="private",
        variants=[],
        family=family,
    )
    registry.hear_direct(
        rumor["id"],
        player,
        source_label=getattr(source, "key", "János"),
        source_type="private_invitation",
        location=getattr(getattr(source, "location", None), "key", None),
    )
    return rumor


def _eligible_source(source):
    definition = DEFINITIONS[HOUNDS_INVITATION_ID]
    return bool(
        getattr(source, "key", None) == definition["source_key"]
        or getattr(source.db, "regular_key", None)
        == definition["source_regular_key"]
    )


def _matches(topic, terms):
    normalized = str(topic or "").strip().lower()
    return any(term in normalized for term in terms)


def deliver_hounds_invitation(source, player):
    """Deliver the private invitation once to this exact mask."""
    if not _eligible_source(source) or player is None:
        return None

    definition = DEFINITIONS[HOUNDS_INVITATION_ID]
    records, mask_records = _mask_records(player)
    existing = copy.deepcopy(
        dict(mask_records.get(HOUNDS_INVITATION_ID) or {})
    )
    if existing:
        _metric(repeat_checks=1)
        return existing

    day, hour = _clock()
    rumor = _private_rumor(
        player,
        source,
        stage="invitation",
        claim=definition["invitation_claim"],
    )
    record = {
        "id": HOUNDS_INVITATION_ID,
        "title": definition["title"],
        "status": "invited",
        "source": _actor_ref(source),
        "delivered_day": day,
        "delivered_hour": hour,
        "invitation_rumor_id": rumor["id"],
        "followup_rumor_id": None,
        "followup_day": None,
        "followup_hour": None,
        "disclosures": [],
    }
    mask_records[HOUNDS_INVITATION_ID] = record
    _save_mask_records(player, mask_records)
    _metric(deliveries=1)
    return copy.deepcopy(record)


def open_hounds_followup(source, player):
    """Reveal the private substance only after this mask received the invite."""
    if not _eligible_source(source) or player is None:
        return None

    definition = DEFINITIONS[HOUNDS_INVITATION_ID]
    _records, mask_records = _mask_records(player)
    record = copy.deepcopy(
        dict(mask_records.get(HOUNDS_INVITATION_ID) or {})
    )
    if not record:
        return None
    if record.get("followup_rumor_id"):
        _metric(repeat_checks=1)
        return record

    day, hour = _clock()
    rumor = _private_rumor(
        player,
        source,
        stage="east_patrol",
        claim=definition["followup_claim"],
    )
    record["status"] = "opened"
    record["followup_rumor_id"] = rumor["id"]
    record["followup_day"] = day
    record["followup_hour"] = hour
    mask_records[HOUNDS_INVITATION_ID] = record
    _save_mask_records(player, mask_records)
    return copy.deepcopy(record)


def private_mystery_answer(source, player, topic):
    """Return private IC prose when this interaction matches the template."""
    if not _eligible_source(source):
        return None

    definition = DEFINITIONS[HOUNDS_INVITATION_ID]
    if _matches(topic, definition["followup_terms"]):
        _records, mask_records = _mask_records(player)
        existing = dict(mask_records.get(HOUNDS_INVITATION_ID) or {})
        if not existing:
            return (
                "János gives you a flat look. "That is not a conversation "
                "I offered you.""
            )
        record = open_hounds_followup(source, player)
        rumor_id = record["followup_rumor_id"]
        return (
            definition["followup_line"]
            + f" [Private P1, rumor R{rumor_id}. You decide whether to retell it.]"
        )

    if _matches(topic, definition["trigger_terms"]):
        record = deliver_hounds_invitation(source, player)
        return (
            definition["invitation_line"]
            + f" [Private P1, rumor R{record['invitation_rumor_id']}.]"
        )
    return None


def records_for(player):
    _all_records, mask_records = _mask_records(player)
    return [
        copy.deepcopy(record)
        for _key, record in sorted(mask_records.items())
    ]


def private_lines(player):
    records = records_for(player)
    if not records:
        return [
            "You are not carrying any private mystery thread on this mask."
        ]

    lines = []
    for index, record in enumerate(records, start=1):
        lines.append(
            f"P{index} {record['title']} [{record['status']}]"
        )
        lines.append(
            f"  Invitation rumor: R{record['invitation_rumor_id']}."
        )
        if record.get("followup_rumor_id"):
            lines.append(
                f"  Follow-up rumor: R{record['followup_rumor_id']}."
            )
        disclosures = list(record.get("disclosures") or [])
        if disclosures:
            names = [
                item.get("target", {}).get("mask") or "someone"
                for item in disclosures[-5:]
            ]
            lines.append(
                "  You chose to disclose private material to: "
                + ", ".join(names)
                + "."
            )
        else:
            lines.append(
                "  You have not deliberately disclosed this private thread."
            )
    lines.append(
        "Private information is not a server-wide requirement. "
        "Use retell <person> R<number> if you choose to disclose a rumor."
    )
    return lines


def note_disclosure(speaker, target, rumor_id):
    """Record voluntary disclosure if the rumor belongs to a private thread."""
    if speaker is None or target is None:
        return None
    try:
        rumor_id = int(rumor_id)
    except (TypeError, ValueError):
        return None

    _records, mask_records = _mask_records(speaker)
    changed = None
    for stable_id, raw in list(mask_records.items()):
        record = copy.deepcopy(dict(raw))
        private_ids = {
            rid
            for rid in (
                record.get("invitation_rumor_id"),
                record.get("followup_rumor_id"),
            )
            if rid is not None
        }
        if rumor_id not in private_ids:
            continue
        disclosures = copy.deepcopy(list(record.get("disclosures") or []))
        target_ref = _actor_ref(target)
        if not any(
            entry.get("rumor_id") == rumor_id
            and (entry.get("target") or {}).get("mask_id")
            == target_ref.get("mask_id")
            for entry in disclosures
        ):
            day, hour = _clock()
            disclosures.append({
                "rumor_id": rumor_id,
                "target": target_ref,
                "day": day,
                "hour": hour,
            })
            record["disclosures"] = disclosures[-20:]
            mask_records[stable_id] = record
            changed = record
            _metric(disclosures=1)
        break

    if changed:
        _save_mask_records(speaker, mask_records)
        return copy.deepcopy(changed)
    return None
