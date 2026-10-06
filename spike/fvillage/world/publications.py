"""Harbinger and Chronicle publication pipeline.

The canonical world-event ledger owns objective history. This module stores
public accounts of that history without collapsing reports into truth.

Harbinger:
    fast, public, corrigible, may report rumor as rumor.

Chronicle:
    slower in editorial threshold, provenance-first, objective claims only when
    backed by canonical events. Player depositions canonize that an account was
    given, never that the account is true.
"""

from __future__ import annotations

import hashlib
import time

from evennia import create_script
from evennia.scripts.models import ScriptDB
from evennia.utils import search


REGISTRY_KEY = "public_records"

PRIVATE_KINDS = {"confession"}
CHRONICLE_KINDS = {
    "building_destroyed",
    "building_restored",
    "location_closed",
    "location_opened",
    "resident_death",
    "resident_departure",
    "death",
    "departure",
    "room_six.note_to_tavern",
}
SPECIAL_EDITION_KINDS = {
    "building_destroyed",
    "resident_death",
    "death",
    "room_six.note_to_tavern",
}
HARBINGER_OBJECTIVE_KINDS = {
    "building_destroyed",
    "building_restored",
    "location_closed",
    "location_opened",
    "resident_death",
    "resident_departure",
    "death",
    "departure",
    "mass",
    "feast",
    "routine",
    "room_six.note_to_tavern",
}


def _clock():
    try:
        clock = ScriptDB.objects.get(db_key="village_time")
        return (
            int(clock.db.day or 1),
            int(clock.db.hour if clock.db.hour is not None else 21),
        )
    except ScriptDB.DoesNotExist:
        return 1, 21


def get_public_record_registry():
    try:
        return ScriptDB.objects.get(db_key=REGISTRY_KEY)
    except ScriptDB.DoesNotExist:
        return create_script(
            "typeclasses.scripts.PublicRecordRegistry",
            key=REGISTRY_KEY,
            persistent=True,
        )


def _humanize(token):
    return str(token or "").replace("_", " ").replace(".", " ").strip()


def _event_rumor(event):
    rumor = event.get("rumor") or {}
    if not isinstance(rumor, dict):
        try:
            rumor = dict(rumor)
        except Exception:
            rumor = {}
    if not rumor.get("published"):
        return None
    return rumor


def _policy(event):
    payload = dict(event.get("payload") or {})
    kind = event.get("kind")

    if kind in PRIVATE_KINDS or payload.get("sealed") or payload.get("publicity") == "private":
        return {
            "harbinger": False,
            "chronicle": False,
            "special": False,
        }

    explicit_harbinger = payload.get("harbinger")
    rumor = _event_rumor(event)
    harbinger = (
        bool(explicit_harbinger)
        if explicit_harbinger is not None
        else bool(
            rumor
            or payload.get("public_summary")
            or kind in HARBINGER_OBJECTIVE_KINDS
        )
    )

    explicit_chronicle = payload.get("chronicle_eligible")
    chronicle = (
        bool(explicit_chronicle)
        if explicit_chronicle is not None
        else kind in CHRONICLE_KINDS
    )

    special = (
        payload.get("publication_priority") == "special"
        or kind in SPECIAL_EDITION_KINDS
    )
    return {
        "harbinger": harbinger,
        "chronicle": chronicle,
        "special": special,
    }


def _headline_and_body(event):
    kind = event.get("kind")
    payload = dict(event.get("payload") or {})
    rumor = _event_rumor(event)

    if payload.get("headline") and payload.get("public_summary"):
        return str(payload["headline"]), str(payload["public_summary"]), "objective"

    if kind == "building_destroyed":
        place = _humanize(payload.get("location_id") or "village building")
        return (
            f"{place.title()} Closed After Destruction",
            f"The {place} is no longer usable. The cause recorded by the village is "
            f"{_humanize(payload.get('cause') or 'under investigation')}.",
            "objective",
        )
    if kind == "building_restored":
        place = _humanize(payload.get("location_id") or "village building")
        return (
            f"{place.title()} Reopens",
            f"The {place} has returned to use after repairs or restoration.",
            "objective",
        )
    if kind == "location_closed":
        place = _humanize(payload.get("location_id") or "village location")
        return (
            f"{place.title()} Closed",
            f"The {place} is presently closed.",
            "objective",
        )
    if kind == "location_opened":
        place = _humanize(payload.get("location_id") or "village location")
        return (
            f"{place.title()} Opens Again",
            f"The {place} is again available for ordinary use.",
            "objective",
        )
    if kind == "mass":
        attendees = list(payload.get("attendees") or [])
        return (
            "Sunday Mass Well Attended",
            f"St. Lazarus held Sunday Mass with {len(attendees)} recorded attendees.",
            "objective",
        )
    if kind == "feast":
        feast = payload.get("feast") or "the feast day"
        return (
            f"{feast} Observed",
            f"The village calendar marks {feast}; ordinary routines shifted around the observance.",
            "objective",
        )
    if kind == "routine":
        regular = _humanize(payload.get("regular") or "a resident")
        if rumor:
            return (
                "Village Hours Shift",
                rumor.get("body") or f"{regular.title()} is keeping different hours.",
                "reported",
            )
        return (
            "Village Hours Shift",
            f"{regular.title()} is keeping different hours than before.",
            "objective",
        )
    if kind == "room_six.note_to_tavern":
        return (
            "Folded Note Posted at the Blood of the Vine",
            "A folded note connected to the upstairs Room Six door was placed where Tavern patrons can inspect it.",
            "objective",
        )
    if kind in {"resident_death", "death"}:
        subject = _humanize(
            payload.get("resident_name")
            or payload.get("resident_id")
            or payload.get("target_resident_id")
            or "a village resident"
        )
        return (
            f"Death Recorded: {subject.title()}",
            f"The village records the death of {subject}. Public accounts may differ on circumstance and meaning.",
            "objective",
        )
    if kind in {"resident_departure", "departure"}:
        subject = _humanize(
            payload.get("resident_name")
            or payload.get("resident_id")
            or payload.get("target_resident_id")
            or "a village resident"
        )
        return (
            f"Departure Recorded: {subject.title()}",
            f"{subject.title()} has departed from ordinary village life.",
            "objective",
        )

    if rumor:
        claim = rumor.get("body") or "A report is circulating without a settled account."
        return (
            f"Report: {_humanize(kind).title()}",
            claim,
            "reported",
        )

    return (
        _humanize(kind).title() or "Village Notice",
        str(payload.get("public_summary") or "A village event has been recorded."),
        "objective",
    )


def _chronicle_text(event):
    kind = event.get("kind")
    payload = dict(event.get("payload") or {})

    if kind == "building_destroyed":
        place = _humanize(payload.get("location_id") or "a village building")
        cause = _humanize(payload.get("cause") or "cause not settled")
        return (
            f"The Chronicle records that the {place} became unusable. "
            f"The event ledger gives the immediate cause as {cause}."
        )
    if kind == "building_restored":
        place = _humanize(payload.get("location_id") or "a village building")
        return f"The Chronicle records that the {place} returned to ordinary use."
    if kind == "location_closed":
        place = _humanize(payload.get("location_id") or "a village location")
        return f"The Chronicle records the closure of the {place}."
    if kind == "location_opened":
        place = _humanize(payload.get("location_id") or "a village location")
        return f"The Chronicle records the reopening of the {place}."
    if kind == "room_six.note_to_tavern":
        return (
            "The Chronicle records that a folded note associated with the Room Six door "
            "was publicly posted at the Blood of the Vine. This entry records the posting, "
            "not the truth of any claim written on the note."
        )
    if kind in {"resident_death", "death"}:
        subject = _humanize(
            payload.get("resident_name")
            or payload.get("resident_id")
            or payload.get("target_resident_id")
            or "a village resident"
        )
        return f"The Chronicle records the death of {subject}."
    if kind in {"resident_departure", "departure"}:
        subject = _humanize(
            payload.get("resident_name")
            or payload.get("resident_id")
            or payload.get("target_resident_id")
            or "a village resident"
        )
        return f"The Chronicle records the departure of {subject}."

    summary = payload.get("chronicle_summary") or payload.get("public_summary")
    if summary:
        return str(summary)
    return f"The Chronicle records a verified {_humanize(kind)} event."


def _story_for_event(event):
    registry = get_public_record_registry()
    for existing in registry.db.harbinger_drafts or []:
        if existing.get("source_event_id") == event["id"]:
            return dict(existing)

    headline, body, basis = _headline_and_body(event)
    rumor = _event_rumor(event)
    day, hour = _clock()
    story = {
        "id": int(registry.db.next_story_id or 1),
        "source_event_id": event["id"],
        "source_rumor_id": rumor.get("rumor_id") if rumor else None,
        "headline": headline,
        "body": body,
        "basis": basis,
        "confidence": 0.55 if basis == "reported" else 0.90,
        "status": "pending",
        "created_day": day,
        "created_hour": hour,
        "published_edition_id": None,
        "corrections": [],
    }
    registry.db.next_story_id = story["id"] + 1
    drafts = list(registry.db.harbinger_drafts or [])
    drafts.append(story)
    registry.db.harbinger_drafts = drafts
    return dict(story)


def _chronicle_for_event(event):
    registry = get_public_record_registry()
    for existing in registry.db.chronicle_entries or []:
        if event["id"] in list(existing.get("source_event_ids") or []):
            return dict(existing)

    day, hour = _clock()
    title, _body, _basis = _headline_and_body(event)
    entry = {
        "id": int(registry.db.next_chronicle_id or 1),
        "entry_type": "objective_record",
        "title": title,
        "text": _chronicle_text(event),
        "claim_status": "verified_event",
        "source_event_ids": [event["id"]],
        "source_rumor_ids": [],
        "source_mask_id": None,
        "source_mask": None,
        "recorded_day": day,
        "recorded_hour": hour,
        "annotations": [],
    }
    registry.db.next_chronicle_id = entry["id"] + 1
    entries = list(registry.db.chronicle_entries or [])
    entries.append(entry)
    registry.db.chronicle_entries = entries

    # The Chronicler remembers the record as institutional work, but this does
    # not inflate every resident's active simulation.
    try:
        from world.residents import remember_important
        found = [
            obj for obj in search.search_object("Ilona Szabó")
            if obj.key == "Ilona Szabó"
        ]
        if found:
            remember_important(
                found[0],
                "chronicle",
                f"C{entry['id']}: {entry['title']}",
                salience=0.65,
                day=day,
            )
    except Exception:
        pass
    return dict(entry)


def ingest_event(event):
    """Project a completed canonical event into public-record systems."""
    if not event or event.get("status") != "complete":
        return {"harbinger_story_id": None, "chronicle_entry_id": None}

    policy = _policy(event)
    story = _story_for_event(event) if policy["harbinger"] else None
    chronicle = _chronicle_for_event(event) if policy["chronicle"] else None
    edition = None
    if story and policy["special"]:
        edition = publish_harbinger_edition(special=True)

    return {
        "harbinger_story_id": story["id"] if story else None,
        "chronicle_entry_id": chronicle["id"] if chronicle else None,
        "special_edition_id": edition["id"] if edition else None,
    }


def _resident_readers(story, edition_id):
    try:
        from world.residents import all_residents, resident_definition, resident_state
    except Exception:
        return []

    readers = []
    for npc in all_residents():
        definition = resident_definition(npc)
        state = resident_state(npc)
        if not definition or not state:
            continue
        if (state.get("lifecycle") or {}).get("status") in {"dead", "departed"}:
            continue

        always = (
            definition.get("faction") == "Chronicler"
            or definition.get("occupation") == "chronicler"
            or "foreign newspapers" in (state.get("interests") or [])
        )
        token = (
            f"{definition['stable_id']}|harbinger|{edition_id}|{story['id']}"
        ).encode("utf-8")
        roll = int.from_bytes(hashlib.sha256(token).digest()[:4], "big") % 100
        if always or roll < 35:
            readers.append(npc)
    return readers


def _distribute_story(story, edition_id):
    """Feed a printed story back into NPC belief state with clear provenance."""
    try:
        from world.rumors import get_rumor_registry
        registry = get_rumor_registry()
    except Exception:
        return 0

    rumor = registry.ensure_rumor(
        subject=f"harbinger:{story['id']}",
        claim=story["body"],
        source_actor="The Harbinger",
        source_type="harbinger",
        original_event_id=story.get("source_event_id"),
        origin_location="Harbinger",
        confidence=story.get("confidence", 0.6),
        emotional_charge=0.20,
        privacy="public",
        variants=[],
        family=f"harbinger:{story['id']}",
    )
    count = 0
    for npc in _resident_readers(story, edition_id):
        if registry.belief_for(npc, rumor["id"]):
            continue
        registry.hear_direct(
            rumor["id"],
            npc,
            source_label="The Harbinger",
            source_type="harbinger",
            location="Harbinger",
        )
        count += 1
    return count


def publish_harbinger_edition(*, special=False, day=None, hour=None):
    """Print all pending copy as one immutable edition."""
    registry = get_public_record_registry()
    if day is None or hour is None:
        current_day, current_hour = _clock()
        day = current_day if day is None else day
        hour = current_hour if hour is None else hour

    # Section 3.22 Stop the Press conflicts share the ordinary publication
    # deadline. An unresolved conflict prints attributed disagreement rather
    # than silently selecting a winner.
    from world.harbinger_content import resolve_due_harbinger_conflicts
    resolve_due_harbinger_conflicts(day, hour)

    drafts = [dict(story) for story in (registry.db.harbinger_drafts or [])]
    pending = [story for story in drafts if story.get("status") == "pending"]
    if not pending:
        return None

    edition = {
        "id": int(registry.db.next_edition_id or 1),
        "day": int(day),
        "hour": int(hour),
        "special": bool(special),
        "story_ids": [story["id"] for story in pending],
        "published_at": time.time(),
        "reader_exposures": 0,
    }
    registry.db.next_edition_id = edition["id"] + 1

    for story in drafts:
        if story["id"] in edition["story_ids"]:
            story["status"] = "published"
            story["published_edition_id"] = edition["id"]
            edition["reader_exposures"] += _distribute_story(
                story,
                edition["id"],
            )
    registry.db.harbinger_drafts = drafts

    editions = list(registry.db.harbinger_editions or [])
    editions.append(edition)
    registry.db.harbinger_editions = editions
    if not special:
        registry.db.last_harbinger_day = int(day)
    return dict(edition)


def publish_due_harbinger(day, hour):
    """Fixed morning publication cadence. Special editions do not consume it."""
    registry = get_public_record_registry()
    if int(hour) != 8:
        return None
    if registry.db.last_harbinger_day == int(day):
        return None
    return publish_harbinger_edition(
        special=False,
        day=int(day),
        hour=int(hour),
    )


def latest_edition():
    editions = list(get_public_record_registry().db.harbinger_editions or [])
    return dict(editions[-1]) if editions else None


def get_story(story_id):
    try:
        story_id = int(story_id)
    except (TypeError, ValueError):
        return None
    for story in get_public_record_registry().db.harbinger_drafts or []:
        if story.get("id") == story_id:
            return dict(story)
    return None


def get_chronicle_entry(entry_id):
    try:
        entry_id = int(entry_id)
    except (TypeError, ValueError):
        return None
    for entry in get_public_record_registry().db.chronicle_entries or []:
        if entry.get("id") == entry_id:
            return dict(entry)
    return None


def annotate_chronicle(entry_id, text, *, source_event_ids=(), author="Chronicler"):
    """Append evidence/correction without altering the original entry text."""
    registry = get_public_record_registry()
    entries = [dict(entry) for entry in (registry.db.chronicle_entries or [])]
    updated = None
    day, hour = _clock()
    for index, entry in enumerate(entries):
        if entry.get("id") != int(entry_id):
            continue
        annotations = list(entry.get("annotations") or [])
        annotation = {
            "id": len(annotations) + 1,
            "text": str(text),
            "source_event_ids": [int(eid) for eid in source_event_ids],
            "author": str(author),
            "day": day,
            "hour": hour,
        }
        annotations.append(annotation)
        replacement = dict(entry)
        replacement["annotations"] = annotations
        entries[index] = replacement
        updated = replacement
        break
    if updated:
        registry.db.chronicle_entries = entries
        return dict(updated)
    return None


def correct_harbinger_story(story_id, text, *, source_event_id=None):
    """Append a correction and queue the correction for the next issue."""
    registry = get_public_record_registry()
    drafts = [dict(story) for story in (registry.db.harbinger_drafts or [])]
    original = None
    day, hour = _clock()
    for index, story in enumerate(drafts):
        if story.get("id") != int(story_id):
            continue
        corrections = list(story.get("corrections") or [])
        correction = {
            "id": len(corrections) + 1,
            "text": str(text),
            "source_event_id": source_event_id,
            "day": day,
            "hour": hour,
        }
        corrections.append(correction)
        replacement = dict(story)
        replacement["corrections"] = corrections
        drafts[index] = replacement
        original = replacement
        break
    if not original:
        return None

    correction_story = {
        "id": int(registry.db.next_story_id or 1),
        "source_event_id": source_event_id,
        "source_rumor_id": None,
        "headline": f"Correction: {original['headline']}",
        "body": str(text),
        "basis": "correction",
        "confidence": 0.95,
        "status": "pending",
        "created_day": day,
        "created_hour": hour,
        "published_edition_id": None,
        "corrections": [],
        "corrects_story_id": original["id"],
    }
    registry.db.next_story_id = correction_story["id"] + 1
    drafts.append(correction_story)
    registry.db.harbinger_drafts = drafts
    return dict(correction_story)



def depositions_for_rumor(rumor_id):
    """Return public signed accounts for one rumor root in record order."""
    try:
        rumor_id = int(rumor_id)
    except (TypeError, ValueError):
        return []
    registry = get_public_record_registry()
    return [
        dict(deposition)
        for deposition in (registry.db.depositions or [])
        if deposition.get("rumor_id") == rumor_id
    ]


def chronicle_disagreement_for_rumor(rumor_id):
    """Return the Chronicle record that preserves incompatible accounts."""
    try:
        rumor_id = int(rumor_id)
    except (TypeError, ValueError):
        return None
    registry = get_public_record_registry()
    for entry in registry.db.chronicle_entries or []:
        if (
            entry.get("entry_type") == "disagreement_record"
            and rumor_id in list(entry.get("source_rumor_ids") or [])
        ):
            return dict(entry)
    return None


def _distinct_deposition_versions(depositions):
    """Keep one representative deposition for each distinct signed claim."""
    versions = []
    seen = set()
    for deposition in depositions:
        claim = str(deposition.get("claim") or "").strip()
        if not claim or claim in seen:
            continue
        seen.add(claim)
        versions.append(dict(deposition))
    return versions


def _version_ref(deposition):
    return {
        "deposition_id": deposition["id"],
        "source_mask_id": deposition.get("source_mask_id"),
        "source_mask": deposition.get("source_mask"),
        "claim": deposition.get("claim"),
    }


def _preserve_deposition_disagreement(rumor_id):
    """Preserve incompatible signed accounts without selecting a true version."""
    versions = _distinct_deposition_versions(depositions_for_rumor(rumor_id))
    if len(versions) < 2:
        return None

    registry = get_public_record_registry()
    existing = chronicle_disagreement_for_rumor(rumor_id)
    day, hour = _clock()

    if existing is None:
        from world.rumors import get_rumor_registry

        root = get_rumor_registry().get_rumor(rumor_id) or {}
        first, second = versions[:2]
        subject = _humanize(root.get("subject") or f"rumor R{rumor_id}")
        if str(root.get("subject") or "").startswith("canon:"):
            subject = "a village rumor"
        entry = {
            "id": int(registry.db.next_chronicle_id or 1),
            "entry_type": "disagreement_record",
            "title": f"Two Versions Survive: {subject.title()}",
            "text": (
                f"The Chronicle preserves incompatible signed accounts concerning "
                f"{subject}. {first.get('source_mask') or 'One witness'} recorded: "
                f"\"{first['claim']}\" "
                f"{second.get('source_mask') or 'Another witness'} recorded: "
                f"\"{second['claim']}\" "
                "The archive does not choose between them. Both remain attributed "
                "accounts rather than verified fact."
            ),
            "claim_status": "documented_disagreement",
            "source_event_ids": [],
            "source_rumor_ids": [int(rumor_id)],
            "source_deposition_ids": [first["id"], second["id"]],
            "version_claims": [_version_ref(first), _version_ref(second)],
            "recorded_day": day,
            "recorded_hour": hour,
            "annotations": [],
        }
        registry.db.next_chronicle_id = entry["id"] + 1
        entries = list(registry.db.chronicle_entries or [])
        entries.append(entry)
        registry.db.chronicle_entries = entries
        if len(versions) > 2:
            return _preserve_deposition_disagreement(rumor_id)
        return dict(entry)

    represented = {
        str(item.get("claim") or "").strip()
        for item in (existing.get("version_claims") or [])
    }
    additions = [
        version
        for version in versions
        if str(version.get("claim") or "").strip() not in represented
    ]
    if not additions:
        return existing

    entries = [dict(entry) for entry in (registry.db.chronicle_entries or [])]
    for index, entry in enumerate(entries):
        if entry.get("id") != existing["id"]:
            continue
        replacement = dict(entry)
        annotations = list(replacement.get("annotations") or [])
        version_claims = list(replacement.get("version_claims") or [])
        source_deposition_ids = list(
            replacement.get("source_deposition_ids") or []
        )
        for deposition in additions:
            annotations.append({
                "id": len(annotations) + 1,
                "text": (
                    f"A further incompatible signed account from "
                    f"{deposition.get('source_mask') or 'another witness'} is "
                    f"preserved: \"{deposition['claim']}\" "
                    "The annotation records disagreement, not truth."
                ),
                "source_event_ids": [],
                "source_deposition_ids": [deposition["id"]],
                "author": "Chronicler",
                "day": day,
                "hour": hour,
            })
            version_claims.append(_version_ref(deposition))
            source_deposition_ids.append(deposition["id"])
        replacement["annotations"] = annotations
        replacement["version_claims"] = version_claims
        replacement["source_deposition_ids"] = source_deposition_ids
        entries[index] = replacement
        registry.db.chronicle_entries = entries
        return dict(replacement)
    return existing


def reconcile_chronicle_disagreement(rumor_id):
    """Backfill or update one rumor root from persisted depositions."""
    try:
        rumor_id = int(rumor_id)
    except (TypeError, ValueError):
        return None
    return _preserve_deposition_disagreement(rumor_id)


def reconcile_chronicle_disagreements():
    """Backfill and update disagreement records from persisted depositions."""
    registry = get_public_record_registry()
    rumor_ids = []
    for deposition in registry.db.depositions or []:
        rumor_id = deposition.get("rumor_id")
        try:
            rumor_id = int(rumor_id)
        except (TypeError, ValueError):
            continue
        rumor_ids.append(rumor_id)

    disagreement_ids = []
    for rumor_id in sorted(set(rumor_ids)):
        entry = reconcile_chronicle_disagreement(rumor_id)
        if entry:
            disagreement_ids.append(entry["id"])

    return {
        "rumor_ids_checked": len(set(rumor_ids)),
        "disagreement_ids": disagreement_ids,
    }


def submit_deposition(player, rumor_id):
    """Record that a player publicly submitted a rumor account to Chronicle."""
    from world.rumors import get_rumor_registry

    rumor_registry = get_rumor_registry()
    belief = rumor_registry.belief_for(player, rumor_id)
    root = rumor_registry.get_rumor(rumor_id)
    if not belief or not root:
        return None, "You cannot submit an account you have not actually heard."

    registry = get_public_record_registry()
    day, hour = _clock()
    deposition = {
        "id": int(registry.db.next_deposition_id or 1),
        "source_mask_id": player.id,
        "source_mask": player.key,
        "rumor_id": int(rumor_id),
        "transmission_id": belief.get("transmission_id"),
        "claim": belief.get("claim"),
        "day": day,
        "hour": hour,
    }
    registry.db.next_deposition_id = deposition["id"] + 1
    depositions = list(registry.db.depositions or [])
    depositions.append(deposition)
    registry.db.depositions = depositions

    entry = {
        "id": int(registry.db.next_chronicle_id or 1),
        "entry_type": "deposition",
        "title": f"Deposition from {player.key}",
        "text": (
            f"{player.key} submitted this account: {belief['claim']} "
            "The Chronicle records the testimony, not its truth."
        ),
        "claim_status": "reported_account",
        "source_event_ids": [],
        "source_rumor_ids": [int(rumor_id)],
        "source_mask_id": player.id,
        "source_mask": player.key,
        "recorded_day": day,
        "recorded_hour": hour,
        "annotations": [],
        "deposition_id": deposition["id"],
    }
    registry.db.next_chronicle_id = entry["id"] + 1
    entries = list(registry.db.chronicle_entries or [])
    entries.append(entry)
    registry.db.chronicle_entries = entries
    _preserve_deposition_disagreement(rumor_id)
    return dict(entry), None


def edition_stories(edition):
    if not edition:
        return []
    wanted = set(edition.get("story_ids") or [])
    stories = []
    for story in get_public_record_registry().db.harbinger_drafts or []:
        if story.get("id") in wanted:
            stories.append(dict(story))
    by_id = {story["id"]: story for story in stories}
    return [by_id[sid] for sid in edition.get("story_ids") or [] if sid in by_id]


def chronicle_entries():
    return [dict(entry) for entry in (get_public_record_registry().db.chronicle_entries or [])]
