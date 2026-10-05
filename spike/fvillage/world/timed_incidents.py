"""Short-lived world windows with persistent witness and aftermath state.

Timed incidents reward presence without making absence equal content loss.
A player who is physically present during a window can retain firsthand
evidence. A later arrival can still encounter residue, rumor, and publication
aftermath. Windows are shared world state, never private quest instances.
"""

from __future__ import annotations

import copy
import time

from evennia import create_script
from evennia.scripts.models import ScriptDB
from evennia.utils import search


REGISTRY_KEY = "timed_incident_registry"
WELL_BOILS_ID = "TIMED-WELL-BOILS"

TEMPLATES = {
    WELL_BOILS_ID: {
        "title": "The Well Boils",
        "location": "Village Square",
        "duration_seconds": 600,
        "schedule": {
            "hour": 22,
            "every_days": 7,
            "day_offset": 1,
        },
        "cooldown_days": 7,
        "live_text": (
            "The well's thin thread of steam suddenly thickens into a white column. "
            "Water knocks hard against the stone throat below, and the rope begins "
            "to tremble against the curb."
        ),
        "firsthand": {
            "id": "boiling_window",
            "quality": "firsthand",
            "label": "the live steam surge",
            "summary": (
                "You were present while the well surged. The steam rose in a dense "
                "white column, the rope trembled without anyone touching it, and the "
                "stone lip warmed quickly enough to bead with condensation."
            ),
        },
        "aftermath": {
            "id": "mineral_residue",
            "quality": "aftermath",
            "label": "the residue after the surge",
            "summary": (
                "After the steam subsides, the well lip remains wet and warm. A pale "
                "mineral ring has dried along the inner stones, preserving evidence "
                "that something more than the ordinary faint vapor occurred."
            ),
        },
        "rumor": (
            "The village well boiled hard enough to shake its rope. By the time most "
            "people arrived, only a pale ring and warm stone remained."
        ),
        "headline": "Steam Surge Reported at Village Well",
        "public_summary": (
            "A brief surge of steam and violent water movement was reported at the "
            "village well. The disturbance ended on its own, leaving warm stone and "
            "a pale mineral deposit. No cause has been established."
        ),
    },
}


def _registry():
    try:
        return ScriptDB.objects.get(db_key=REGISTRY_KEY)
    except ScriptDB.DoesNotExist:
        return create_script(
            "typeclasses.scripts.TimedIncidentRegistry",
            key=REGISTRY_KEY,
            persistent=True,
        )


def get_timed_incident_registry():
    return _registry()


def _clock():
    try:
        clock = ScriptDB.objects.get(db_key="village_time")
        return int(clock.db.day or 1), int(
            clock.db.hour if clock.db.hour is not None else 21
        )
    except ScriptDB.DoesNotExist:
        return 1, 21


def _metric(**deltas):
    registry = _registry()
    metrics = copy.deepcopy(dict(registry.db.metrics or {}))
    for key, value in deltas.items():
        metrics[key] = int(metrics.get(key) or 0) + int(value)
    registry.db.metrics = metrics


def _empty_incident(stable_id):
    return {
        "id": stable_id,
        "state": "dormant",
        "occurrence_count": 0,
        "current": None,
        "history": [],
        "last_started_day": None,
        "cooldown_until_day": None,
    }


def ensure_timed_incidents():
    registry = _registry()
    incidents = copy.deepcopy(dict(registry.db.incidents or {}))
    created = 0
    for stable_id in TEMPLATES:
        if stable_id not in incidents:
            incidents[stable_id] = _empty_incident(stable_id)
            created += 1
    registry.db.incidents = incidents
    advance_timed_incidents()
    return {"created": created, "count": len(incidents)}


def get_timed_incident(stable_id=WELL_BOILS_ID):
    raw = dict((_registry().db.incidents or {}).get(stable_id) or {})
    return copy.deepcopy(raw) if raw else None


def _save(incident):
    registry = _registry()
    incidents = copy.deepcopy(dict(registry.db.incidents or {}))
    incidents[incident["id"]] = copy.deepcopy(incident)
    registry.db.incidents = incidents
    return copy.deepcopy(incident)


def _exact_room(key):
    found = [obj for obj in search.search_object(key) if obj.key == key]
    return found[0] if found else None


def _observation_record(player, evidence, *, source, observed_at):
    return {
        "player_id": getattr(player, "id", None),
        "player_name": getattr(player, "key", None),
        "evidence_id": evidence["id"],
        "quality": evidence["quality"],
        "label": evidence["label"],
        "summary": evidence["summary"],
        "source": source,
        "observed_at": float(observed_at),
    }


def _record_player_observation(
    incident,
    player,
    evidence,
    *,
    source,
    observed_at,
):
    current = copy.deepcopy(dict(incident.get("current") or {}))
    observations = copy.deepcopy(dict(current.get("player_observations") or {}))
    key = str(getattr(player, "id", ""))
    existing = dict(observations.get(key) or {})

    # Firsthand evidence dominates aftermath evidence for the same occurrence.
    if existing.get("quality") == "firsthand":
        return incident, False
    if existing and evidence["quality"] != "firsthand":
        return incident, False

    observations[key] = _observation_record(
        player,
        evidence,
        source=source,
        observed_at=observed_at,
    )
    current["player_observations"] = observations
    incident["current"] = current
    return incident, True


def _schedule_matches(template, day, hour):
    schedule = dict(template.get("schedule") or {})
    if int(hour) != int(schedule.get("hour", -1)):
        return False
    every_days = max(1, int(schedule.get("every_days") or 1))
    offset = int(schedule.get("day_offset") or 1)
    return (int(day) - offset) % every_days == 0


def _can_start(incident, template, day, hour, *, force=False):
    if incident.get("state") == "active":
        return False
    if force:
        return True
    if not _schedule_matches(template, day, hour):
        return False
    if incident.get("last_started_day") == int(day):
        return False
    cooldown = incident.get("cooldown_until_day")
    if cooldown is not None and int(day) < int(cooldown):
        return False
    return True


def _resident_ids_in(room):
    resident_ids = []
    if not room:
        return resident_ids
    for obj in room.contents:
        stable_id = getattr(obj.db, "resident_id", None)
        if stable_id:
            resident_ids.append(str(stable_id))
    return sorted(set(resident_ids))


def start_timed_incident(
    stable_id=WELL_BOILS_ID,
    *,
    day=None,
    hour=None,
    now=None,
    force=False,
):
    """Start one short-lived shared world window."""
    template = TEMPLATES.get(stable_id)
    incident = get_timed_incident(stable_id)
    if not template or not incident:
        return None

    if day is None or hour is None:
        clock_day, clock_hour = _clock()
        day = clock_day if day is None else int(day)
        hour = clock_hour if hour is None else int(hour)
    now = time.time() if now is None else float(now)

    if not _can_start(incident, template, int(day), int(hour), force=force):
        return None

    previous = incident.get("current")
    history = copy.deepcopy(list(incident.get("history") or []))
    if previous:
        history.append(copy.deepcopy(previous))
        history = history[-12:]

    room = _exact_room(template["location"])
    occurrence = int(incident.get("occurrence_count") or 0) + 1
    current = {
        "occurrence": occurrence,
        "state": "active",
        "started_day": int(day),
        "started_hour": int(hour),
        "started_at": now,
        "expires_at": now + int(template["duration_seconds"]),
        "resolved_at": None,
        "player_observations": {},
        "resident_witness_ids": _resident_ids_in(room),
        "start_event_id": None,
        "aftermath_event_id": None,
        "rumor_id": None,
        "publications": {},
    }
    incident.update({
        "state": "active",
        "occurrence_count": occurrence,
        "current": current,
        "history": history,
        "last_started_day": int(day),
        "cooldown_until_day": None,
    })

    firsthand_count = 0
    if room:
        for obj in list(room.contents):
            if not obj.has_account:
                continue
            incident, added = _record_player_observation(
                incident,
                obj,
                template["firsthand"],
                source="present_when_window_opened",
                observed_at=now,
            )
            firsthand_count += 1 if added else 0

    from world.events import publish_world_event

    start_event = publish_world_event(
        "timed.well_boils.started",
        payload={
            "timed_incident_id": stable_id,
            "occurrence": occurrence,
            "location": template["location"],
            "publicity": "private",
            "resident_ids": list(current["resident_witness_ids"]),
        },
    )
    incident["current"]["start_event_id"] = start_event["id"]
    _save(incident)

    if room:
        room.msg_contents(template["live_text"])

    _metric(
        starts=1,
        firsthand_witnesses=firsthand_count,
    )
    return get_timed_incident(stable_id)


def maybe_start_timed_incidents(*, day=None, hour=None, now=None):
    """Start any scheduled windows matching the current village boundary."""
    if day is None or hour is None:
        clock_day, clock_hour = _clock()
        day = clock_day if day is None else int(day)
        hour = clock_hour if hour is None else int(hour)
    now = time.time() if now is None else float(now)

    advance_timed_incidents(now=now)
    started = []
    for stable_id in sorted(TEMPLATES):
        result = start_timed_incident(
            stable_id,
            day=int(day),
            hour=int(hour),
            now=now,
            force=False,
        )
        if result:
            started.append(stable_id)
    _metric(schedule_checks=1)
    return started


def _resolve_well(incident, *, now):
    template = TEMPLATES[WELL_BOILS_ID]
    current = copy.deepcopy(dict(incident.get("current") or {}))
    room = _exact_room(template["location"])

    from world.events import publish_world_event

    event = publish_world_event(
        "timed.well_boils.aftermath",
        payload={
            "timed_incident_id": WELL_BOILS_ID,
            "occurrence": current["occurrence"],
            "location": template["location"],
            "headline": template["headline"],
            "public_summary": template["public_summary"],
            "chronicle_eligible": False,
            "resident_ids": list(current.get("resident_witness_ids") or []),
        },
        rumor=template["rumor"],
    )

    current["state"] = "aftermath"
    current["resolved_at"] = float(now)
    current["aftermath_event_id"] = event["id"]
    rumor = event.get("rumor") or {}
    try:
        current["rumor_id"] = rumor.get("rumor_id")
    except Exception:
        current["rumor_id"] = None
    publications = event.get("publications") or {}
    try:
        current["publications"] = dict(publications)
    except Exception:
        current["publications"] = {}

    incident["state"] = "aftermath"
    incident["current"] = current
    incident["cooldown_until_day"] = (
        int(current["started_day"]) + int(template["cooldown_days"])
    )

    if room:
        room.msg_contents(
            "The well's violent steaming dwindles almost as quickly as it began. "
            "The rope settles. Warm water beads on the stone, leaving a pale ring "
            "as it dries."
        )
    return incident


def advance_timed_incidents(*, now=None):
    """Resolve expired windows without replaying intermediate time."""
    now = time.time() if now is None else float(now)
    registry = _registry()
    incidents = copy.deepcopy(dict(registry.db.incidents or {}))
    resolved = 0

    for stable_id, raw in list(incidents.items()):
        incident = dict(raw)
        if incident.get("state") != "active":
            continue
        current = dict(incident.get("current") or {})
        expires_at = current.get("expires_at")
        if expires_at is None or now < float(expires_at):
            continue

        if stable_id == WELL_BOILS_ID:
            incident = _resolve_well(incident, now=now)
        else:
            continue
        incidents[stable_id] = incident
        resolved += 1

    if resolved:
        registry.db.incidents = incidents
        _metric(resolutions=resolved)
    return resolved


def record_observation(player, stable_id=WELL_BOILS_ID, *, source="look"):
    incident = get_timed_incident(stable_id)
    template = TEMPLATES.get(stable_id)
    if not incident or not template or not incident.get("current"):
        return None

    state = incident.get("state")
    if state == "active":
        evidence = template["firsthand"]
    elif state == "aftermath":
        evidence = template["aftermath"]
    else:
        return None

    incident, added = _record_player_observation(
        incident,
        player,
        evidence,
        source=source,
        observed_at=time.time(),
    )
    if added:
        _save(incident)
        if evidence["quality"] == "firsthand":
            _metric(firsthand_witnesses=1)
        else:
            _metric(aftermath_discoveries=1)
    key = str(getattr(player, "id", ""))
    return copy.deepcopy(
        dict((incident["current"].get("player_observations") or {}).get(key) or {})
    )


def status_for_player(player, stable_id=WELL_BOILS_ID):
    incident = get_timed_incident(stable_id)
    if not incident or not incident.get("current"):
        return None
    current = dict(incident["current"])
    observation = dict(
        (current.get("player_observations") or {}).get(
            str(getattr(player, "id", "")),
            {},
        )
    )
    if not observation:
        return None
    return {
        "id": stable_id,
        "title": TEMPLATES[stable_id]["title"],
        "state": incident["state"],
        "occurrence": current["occurrence"],
        "observation": observation,
        "started_day": current["started_day"],
        "started_hour": current["started_hour"],
        "aftermath_event_id": current.get("aftermath_event_id"),
        "rumor_id": current.get("rumor_id"),
        "publications": copy.deepcopy(current.get("publications") or {}),
    }


def known_timed_incidents(player):
    known = []
    for stable_id in TEMPLATES:
        status = status_for_player(player, stable_id)
        if status:
            known.append(status)
    return sorted(
        known,
        key=lambda entry: (
            int(entry.get("started_day") or 0),
            int(entry.get("started_hour") or 0),
            entry["id"],
        ),
        reverse=True,
    )


def resolve_timed_subject(subject):
    raw = str(subject or "").strip().lower()
    aliases = {
        "well": WELL_BOILS_ID,
        "village well": WELL_BOILS_ID,
        "boiling well": WELL_BOILS_ID,
        "well boils": WELL_BOILS_ID,
        "well boiling": WELL_BOILS_ID,
        WELL_BOILS_ID.lower(): WELL_BOILS_ID,
    }
    return aliases.get(raw)


def well_description(looker=None):
    incident = get_timed_incident(WELL_BOILS_ID)
    if not incident or not incident.get("current"):
        return (
            "The village well stands at the square's heart. It steams faintly, "
            "though the night is cool. When the air falls still, the vapor rises "
            "in a strangely straight thread. The rope vanishes down into dark water "
            "you cannot quite see."
        )

    state = incident.get("state")
    if state == "active":
        if looker is not None and looker.has_account:
            record_observation(looker, WELL_BOILS_ID, source="look_during_window")
        return (
            "The well is not merely steaming now. White vapor climbs in a dense "
            "column from the stone throat, and unseen water knocks below hard enough "
            "to make the rope shiver. Condensation has made the lip slick and warm."
        )

    if state == "aftermath":
        if looker is not None and looker.has_account:
            record_observation(looker, WELL_BOILS_ID, source="look_after_window")
        return (
            "The well has returned to its ordinary faint steaming, but the stone lip "
            "is still warmer than the square air. A pale mineral ring dries along the "
            "inner stones, and the rope is damp where spray reached it."
        )

    return (
        "The village well stands at the square's heart. It steams faintly, though "
        "the night is cool."
    )
