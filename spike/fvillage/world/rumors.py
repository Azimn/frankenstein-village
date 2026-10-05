"""Persistent rumor data, provenance, and no-model propagation.

The server owns rumor records and transmission history. Dialogue only renders
what a character currently believes. Original rumor records are immutable.
Every retelling is a new transmission that points to its parent.
"""

from __future__ import annotations

import random
import re
from collections import defaultdict
from pathlib import Path

from evennia import create_script
from evennia.scripts.models import ScriptDB
from evennia.utils import search


REPO_ROOT = Path(__file__).resolve().parents[3]
RUMOR_FILE = REPO_ROOT / "files" / "rumor-seeds-v0.1.md"
REGISTRY_KEY = "rumor_registry"
PLAYABLE_RUMOR_IDS = frozenset({151, 201, 236})

_SEED_RE = re.compile(r"^\*\*(\d+)\.\*\*\s*(.+)$", re.M)
_VARIANT_RE = re.compile(r"\([a-z]\)\s*(.*?)(?=;\s*\([a-z]\)|$)")


def _strip_markup(text):
    return re.sub(r"\*([^*]+?)\*", r"\1", (text or "")).strip()


def _parse_seed_line(number, line):
    heard_marker = f" {chr(0x2014)} *Heard from:* "
    if heard_marker not in line:
        heard_marker = " - *Heard from:* "
    if heard_marker not in line:
        return {
            "canonical_seed_id": int(number),
            "claim": line.strip(),
            "source_actor": "village talk",
            "variants": [],
        }

    claim, tail = line.split(heard_marker, 1)
    source = tail
    if " *Benefits:* " in source:
        source = source.split(" *Benefits:* ", 1)[0]
    source = source.strip().rstrip(".")

    variants = []
    if "*Variants:* " in tail:
        blob = tail.split("*Variants:* ", 1)[1].strip()
        variants = [_strip_markup(v).rstrip(".") for v in _VARIANT_RE.findall(blob)]

    return {
        "canonical_seed_id": int(number),
        "claim": _strip_markup(claim.strip()),
        "source_actor": _strip_markup(source),
        "variants": variants,
    }


def load_canon_rumors(*, playable_only=True):
    """Return parsed canon rumor objects from the accepted seed corpus."""
    text = RUMOR_FILE.read_text(encoding="utf-8")
    results = []
    for match in _SEED_RE.finditer(text):
        number = int(match.group(1))
        if playable_only and number not in PLAYABLE_RUMOR_IDS:
            continue
        results.append(_parse_seed_line(number, match.group(2).strip()))
    return results


def get_rumor_registry():
    try:
        return ScriptDB.objects.get(db_key=REGISTRY_KEY)
    except ScriptDB.DoesNotExist:
        return create_script(
            "typeclasses.scripts.RumorRegistry",
            key=REGISTRY_KEY,
            persistent=True,
        )


def _find_tavern():
    found = [
        obj for obj in search.search_object("The Blood of the Vine")
        if obj.key == "The Blood of the Vine"
    ]
    return found[0] if found else None


def seed_playable_rumors(*, participants=()):
    """Materialize the currently reachable canon rumors idempotently."""
    registry = get_rumor_registry()
    created = []
    for seed in load_canon_rumors(playable_only=True):
        rumor = registry.ensure_rumor(
            subject=f"canon:{seed['canonical_seed_id']}",
            claim=seed["claim"],
            source_actor=seed["source_actor"],
            source_type="canon_teller",
            original_event_id=None,
            origin_location=None,
            confidence=0.52,
            emotional_charge=0.25,
            privacy="public",
            variants=seed["variants"],
            canonical_seed_id=seed["canonical_seed_id"],
            family=f"canon:{seed['canonical_seed_id']}",
        )
        created.append(rumor)
        for npc in participants:
            registry.hear_direct(
                rumor["id"],
                npc,
                source_label=seed["source_actor"],
                source_type="canon_teller",
                location=getattr(npc.location, "key", None),
            )
    return created


def _dynamic_claim(body):
    """Strip legacy inline attribution now that provenance is structured."""
    body = body or ""
    return re.sub(r"\s*\*Heard from:.*?\*\s*$", "", body, flags=re.I).strip()


def publish_public_rumor(
    body,
    *,
    source_actor=None,
    source_type="world_event",
    original_event_id=None,
    subject="world_event",
    location=None,
    variants=(),
    family=None,
    confidence=0.58,
    emotional_charge=0.35,
):
    """Create an immutable rumor root and expose it through the Tavern."""
    registry = get_rumor_registry()
    tavern = _find_tavern()
    rumor = registry.ensure_rumor(
        subject=subject,
        claim=_strip_markup(_dynamic_claim(body)),
        source_actor=source_actor or "village event",
        source_type=source_type,
        original_event_id=original_event_id,
        origin_location=location,
        confidence=confidence,
        emotional_charge=emotional_charge,
        privacy="public",
        variants=list(variants or ()),
        family=family or subject,
    )

    if not tavern:
        return {
            "published": False,
            "reason": "tavern_missing",
            "body": rumor["claim"],
            "rumor_id": rumor["id"],
        }

    public_ids = list(tavern.db.public_rumor_ids or [])
    if rumor.get("family") == "schedule_shift":
        keep = []
        for rid in public_ids:
            old = registry.get_rumor(rid)
            if not old or old.get("family") != "schedule_shift":
                keep.append(rid)
        public_ids = keep
    if rumor["id"] not in public_ids:
        public_ids.append(rumor["id"])
    tavern.db.public_rumor_ids = public_ids[-50:]

    legacy = list(tavern.db.player_rumors or [])
    if rumor.get("family") == "schedule_shift":
        schedule_re = re.compile(r"keeping (different|their old) hours")
        legacy = [r for r in legacy if not schedule_re.search(r)]
    if rumor["claim"] not in legacy:
        legacy.append(rumor["claim"])
    tavern.db.player_rumors = legacy[-50:]

    for obj in list(tavern.contents):
        if obj.tags.has("participant", category="rumor"):
            registry.hear_direct(
                rumor["id"],
                obj,
                source_label=source_actor or "the room",
                source_type=source_type,
                location=tavern.key,
            )

    return {
        "published": True,
        "location": tavern.key,
        "body": rumor["claim"],
        "rumor_id": rumor["id"],
    }


def migrate_legacy_public_rumors(tavern):
    """Upgrade pre-registry Tavern strings without losing player-created talk."""
    registry = get_rumor_registry()
    public_ids = list(tavern.db.public_rumor_ids or [])
    for body in list(tavern.db.player_rumors or []):
        claim = _strip_markup(_dynamic_claim(body))
        if not claim:
            continue
        existing = next(
            (
                dict(rumor)
                for rumor in (registry.db.rumors or [])
                if rumor.get("claim") == claim and rumor.get("privacy") == "public"
            ),
            None,
        )
        if existing:
            if existing["id"] not in public_ids:
                public_ids.append(existing["id"])
            continue
        rumor = registry.ensure_rumor(
            subject="legacy_tavern",
            claim=claim,
            source_actor="older tavern talk",
            source_type="legacy",
            original_event_id=None,
            origin_location=tavern.key,
            confidence=0.50,
            emotional_charge=0.25,
            privacy="public",
            variants=[],
            family="legacy_tavern",
        )
        if rumor["id"] not in public_ids:
            public_ids.append(rumor["id"])
    tavern.db.public_rumor_ids = public_ids[-50:]
    return public_ids


def public_dynamic_rumors(tavern):
    registry = get_rumor_registry()
    migrate_legacy_public_rumors(tavern)
    roots = []
    for rid in list(tavern.db.public_rumor_ids or []):
        rumor = registry.get_rumor(rid)
        if rumor:
            roots.append(rumor)
    return roots


def hear_public(actor, rumor_id, tavern=None):
    tavern = tavern or _find_tavern()
    registry = get_rumor_registry()
    root = registry.get_rumor(rumor_id)
    existing = registry.belief_for(actor, rumor_id)
    refresh = bool(
        root and existing and existing.get("claim") != root.get("claim")
    )
    return registry.hear_direct(
        rumor_id,
        actor,
        source_label=(tavern.key if tavern else "village talk"),
        source_type="public_tavern",
        location=(tavern.key if tavern else None),
        force_new=refresh,
    )


def _participants():
    try:
        return list(search.search_tag("participant", category="rumor"))
    except Exception:
        return []


def propagate_colocated_npcs(*, announce=False, max_per_room=1):
    """Run bounded rumor traffic among co-located participating NPCs."""
    registry = get_rumor_registry()
    by_room = defaultdict(list)
    for npc in _participants():
        if npc.location:
            by_room[npc.location.id].append(npc)

    results = []
    for group in by_room.values():
        if len(group) < 2:
            continue
        candidates = [npc for npc in group if registry.beliefs_for(npc)]
        if not candidates:
            continue
        attempts = 0
        while attempts < max_per_room:
            speaker = random.choice(candidates)
            listeners = [npc for npc in group if npc.id != speaker.id]
            if not listeners:
                break
            listener = random.choice(listeners)
            beliefs = list(registry.beliefs_for(speaker).values())
            if not beliefs:
                break
            belief = random.choice(beliefs)
            result = registry.transmit(
                belief["rumor_id"],
                speaker,
                listener,
                location=getattr(speaker.location, "key", None),
            )
            if result:
                results.append(result)
                if announce and speaker.location:
                    speaker.location.msg_contents(
                        f"{speaker.key} lowers their voice to {listener.key}. "
                        f'\"{result["claim"]}\"'
                    )
            attempts += 1
    return results
