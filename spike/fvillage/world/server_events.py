"""Village-scale server event frameworks.

Server-wide events are temporary systemic conditions, not single quests. They
create several local response opportunities, alter multiple public spaces,
wake relevant residents, and resolve into a persistent aftermath even if no
player intervenes.

The authoritative village clock is the only scheduler.
"""

from __future__ import annotations

import copy

from evennia import create_script
from evennia.scripts.models import ScriptDB
from evennia.utils import search


REGISTRY_KEY = "server_event_registry"
LONG_BLACKOUT_ID = "SERVER-LONG-BLACKOUT"
MAX_HISTORY = 12

DEFINITIONS = {
    LONG_BLACKOUT_ID: {
        "title": "The Long Blackout",
        "duration_hours": 12,
        "aftermath_hours": 6,
        "trigger": {
            "hour": 19,
            "every_days": 28,
            "day_offset": 10,
        },
        "resident_ids": [
            "miklos_farkas",
            "lucian_deville",
            "bram_v",
            "father_andrei",
            "sorin_dragomir",
        ],
        "start_rumor": (
            "The village lamps have gone dark together. The square is nearly "
            "black, and every institution is improvising its own answer."
        ),
        "start_headline": "Village Lighting Fails Across Several Districts",
        "start_summary": (
            "Gas lighting failed across several public districts during the "
            "evening. The square, church, tavern, and lamp trade are operating "
            "under temporary measures while the cause remains unsettled."
        ),
        "end_headline": "Village Lighting Restored After Long Blackout",
        "active_overlays": {
            "Village Square": (
                "The blackout has swallowed most of the square. Dark gas "
                "standards cut black lines against the sky while Miklós moves "
                "from lamp to lamp with a shielded flame."
            ),
            "The Blood of the Vine": (
                "The blackout has driven extra bodies indoors. Bram has set "
                "candles in saucers along the bar, and strangers are making "
                "room for one another near the hearth."
            ),
            "St. Lazarus Church": (
                "The church is lit almost entirely by altar and votive candles. "
                "Father Andrei has begun rationing tapers so the nave can remain "
                "open through the outage."
            ),
            "The Lamp Shop": (
                "The shop is doing emergency business by candlelight. Oil tins, "
                "spare mantles, and lamp glass have been pulled onto the counter "
                "for households that arrived unprepared."
            ),
        },
        "aftermath_overlays": {
            "Village Square": (
                "The gas lamps are burning again, though one mantle still "
                "flickers. Soot marks on the standards show where the "
                "lamplighter worked through the outage."
            ),
            "The Blood of the Vine": (
                "Spent candle ends and crowded chairs remain from the blackout. "
                "Bram has not yet decided whether to complain about the extra "
                "trade or the extra washing."
            ),
            "St. Lazarus Church": (
                "Shortened candle rows show how long the church stayed open "
                "during the blackout."
            ),
            "The Lamp Shop": (
                "The emergency queue is gone, but several shelves remain thin "
                "after the blackout rush."
            ),
        },
        "responses": {
            "lamps": {
                "location": "Village Square",
                "aliases": ["lamp", "relight", "lighting"],
                "label": "help relight and shield the street lamps",
                "result": "street lamps stabilized",
                "resident_ids": ["miklos_farkas", "sorin_dragomir"],
            },
            "shelter": {
                "location": "The Blood of the Vine",
                "aliases": ["tavern", "crowd", "beds"],
                "label": "help Bram shelter and sort stranded residents",
                "result": "tavern shelter organized",
                "resident_ids": ["bram_v"],
            },
            "candles": {
                "location": "St. Lazarus Church",
                "aliases": ["church", "tapers", "light"],
                "label": "help ration and place church candles",
                "result": "church candle supply stretched",
                "resident_ids": ["father_andrei"],
            },
            "supplies": {
                "location": "The Lamp Shop",
                "aliases": ["oil", "shop", "mantles"],
                "label": "help sort oil, mantles, and spare lamp glass",
                "result": "lamp supplies distributed",
                "resident_ids": ["lucian_deville"],
            },
        },
    },
}


def _registry():
    try:
        return ScriptDB.objects.get(db_key=REGISTRY_KEY)
    except ScriptDB.DoesNotExist:
        return create_script(
            "typeclasses.scripts.ServerEventRegistry",
            key=REGISTRY_KEY,
            persistent=True,
        )


def get_server_event_registry():
    return _registry()


def _clock():
    try:
        clock = ScriptDB.objects.get(db_key="village_time")
        return int(clock.db.day or 1), int(
            clock.db.hour if clock.db.hour is not None else 21
        )
    except ScriptDB.DoesNotExist:
        return 1, 21


def _empty_event(stable_id):
    return {
        "id": stable_id,
        "state": "dormant",
        "occurrence_count": 0,
        "current": None,
        "history": [],
        "last_started_day": None,
    }


def ensure_server_events():
    registry = _registry()
    events = copy.deepcopy(dict(registry.db.events or {}))
    created = 0
    for stable_id in DEFINITIONS:
        if stable_id not in events:
            events[stable_id] = _empty_event(stable_id)
            created += 1
    registry.db.events = events
    reconcile_server_event_overlays()
    return {"created": created, "count": len(events)}


def get_server_event(stable_id=LONG_BLACKOUT_ID):
    raw = dict((_registry().db.events or {}).get(stable_id) or {})
    return copy.deepcopy(raw) if raw else None


def _save(event):
    registry = _registry()
    events = copy.deepcopy(dict(registry.db.events or {}))
    events[event["id"]] = copy.deepcopy(event)
    registry.db.events = events
    return copy.deepcopy(event)


def _metric(**deltas):
    registry = _registry()
    metrics = copy.deepcopy(dict(registry.db.metrics or {}))
    for key, value in deltas.items():
        metrics[key] = int(metrics.get(key) or 0) + int(value)
    registry.db.metrics = metrics


def _absolute_hour(day, hour):
    return (int(day) - 1) * 24 + int(hour)


def _add_hours(day, hour, amount):
    absolute = _absolute_hour(day, hour) + int(amount)
    return absolute // 24 + 1, absolute % 24


def _room(key):
    found = [obj for obj in search.search_object(key) if obj.key == key]
    return found[0] if found else None


def _set_overlay(room_key, overlay_id, text):
    from world.scheduled_events import set_room_overlay

    return set_room_overlay(room_key, overlay_id, text)


def _clear_overlay(room_key, overlay_id):
    from world.scheduled_events import clear_room_overlay

    return clear_room_overlay(room_key, overlay_id)


def _active_overlay_id(stable_id):
    return f"{stable_id}:active"


def _aftermath_overlay_id(stable_id):
    return f"{stable_id}:aftermath"


def reconcile_server_event_overlays():
    events = copy.deepcopy(dict(_registry().db.events or {}))
    changed = 0

    for stable_id, definition in DEFINITIONS.items():
        active_id = _active_overlay_id(stable_id)
        aftermath_id = _aftermath_overlay_id(stable_id)
        event = dict(events.get(stable_id) or {})
        state = event.get("state")

        for room_key in definition.get("active_overlays") or {}:
            if state != "active":
                changed += int(bool(_clear_overlay(room_key, active_id)))
        for room_key in definition.get("aftermath_overlays") or {}:
            if state != "aftermath":
                changed += int(bool(_clear_overlay(room_key, aftermath_id)))

        if state == "active":
            for room_key, text in definition["active_overlays"].items():
                changed += int(bool(_set_overlay(room_key, active_id, text)))
        elif state == "aftermath":
            for room_key, text in definition["aftermath_overlays"].items():
                changed += int(bool(_set_overlay(room_key, aftermath_id, text)))

    return changed


def _trigger_matches(definition, day, hour):
    trigger = dict(definition.get("trigger") or {})
    if int(hour) != int(trigger.get("hour", -1)):
        return False
    every_days = max(1, int(trigger.get("every_days") or 1))
    offset = int(trigger.get("day_offset") or 1)
    return (int(day) - offset) % every_days == 0


def _response_alias_map(definition):
    aliases = {}
    for key, response in (definition.get("responses") or {}).items():
        aliases[key.lower()] = key
        for alias in response.get("aliases") or []:
            aliases[str(alias).lower()] = key
    return aliases


def _local_response(definition, room_key):
    for key, response in (definition.get("responses") or {}).items():
        if response.get("location") == room_key:
            return key, response
    return None, None


def _publish_start(stable_id, definition, current):
    from world.events import publish_world_event

    event = publish_world_event(
        "server.long_blackout.started",
        payload={
            "server_event_id": stable_id,
            "headline": definition["start_headline"],
            "public_summary": definition["start_summary"],
            "harbinger": True,
            "chronicle_eligible": False,
            "resident_ids": list(definition.get("resident_ids") or []),
            "started_day": current["started_day"],
            "started_hour": current["started_hour"],
        },
        rumor=definition["start_rumor"],
    )
    current["start_event_id"] = event["id"]
    current["start_publications"] = copy.deepcopy(event.get("publications") or {})
    current["start_rumor_id"] = (
        (event.get("rumor") or {}).get("rumor_id")
        if isinstance(event.get("rumor"), dict)
        else None
    )
    return current


def start_server_event(
    stable_id=LONG_BLACKOUT_ID,
    *,
    day=None,
    hour=None,
    force=False,
):
    definition = DEFINITIONS.get(stable_id)
    event = get_server_event(stable_id)
    if not definition or not event:
        return None

    if day is None or hour is None:
        clock_day, clock_hour = _clock()
        day = clock_day if day is None else int(day)
        hour = clock_hour if hour is None else int(hour)
    day = int(day)
    hour = int(hour)

    if event.get("state") in {"active", "aftermath"}:
        return None
    if not force and not _trigger_matches(definition, day, hour):
        return None
    if event.get("last_started_day") == day:
        return None

    end_day, end_hour = _add_hours(
        day,
        hour,
        definition.get("duration_hours") or 1,
    )
    occurrence = int(event.get("occurrence_count") or 0) + 1
    current = {
        "occurrence": occurrence,
        "state": "active",
        "started_day": day,
        "started_hour": hour,
        "end_day": end_day,
        "end_hour": end_hour,
        "responses": {},
        "contributors": {},
        "start_event_id": None,
        "start_rumor_id": None,
        "start_publications": {},
        "end_event_id": None,
        "end_rumor_id": None,
        "end_publications": {},
        "outcome": None,
        "aftermath_until_day": None,
        "aftermath_until_hour": None,
    }
    current = _publish_start(stable_id, definition, current)

    event["state"] = "active"
    event["occurrence_count"] = occurrence
    event["last_started_day"] = day
    event["current"] = current
    _save(event)
    reconcile_server_event_overlays()

    for room_key in definition.get("active_overlays") or {}:
        room = _room(room_key)
        if room:
            room.msg_contents(
                "The village lighting fails almost at once. Darkness spreads "
                "from street to street as people begin improvising."
            )

    _metric(starts=1)
    return get_server_event(stable_id)


def _player_ref(player):
    account = getattr(player, "account", None)
    return {
        "mask_id": getattr(player, "id", None),
        "mask": getattr(player, "key", None),
        "account_id": getattr(account, "id", None),
    }


def contribute(player, action, stable_id=LONG_BLACKOUT_ID):
    definition = DEFINITIONS.get(stable_id)
    event = get_server_event(stable_id)
    if not definition or not event or event.get("state") != "active":
        return None, "There is no active village-wide event to answer here."

    canonical = _response_alias_map(definition).get(str(action or "").strip().lower())
    if not canonical:
        return None, (
            "That is not a useful response here. Use event to see what this "
            "location currently needs."
        )
    response = definition["responses"][canonical]
    location = getattr(player, "location", None)
    location_key = getattr(location, "key", None)
    if location_key != response["location"]:
        return None, (
            f"That response belongs at {response['location']}, not here."
        )

    current = copy.deepcopy(dict(event.get("current") or {}))
    responses = copy.deepcopy(dict(current.get("responses") or {}))
    existing = dict(responses.get(canonical) or {})
    player_key = str(getattr(player, "id", ""))

    contributors = copy.deepcopy(dict(current.get("contributors") or {}))
    already = set(contributors.get(player_key) or [])
    if canonical in already:
        return None, "You have already done what you can on that local problem."

    first_completion = not bool(existing)
    helpers = list(existing.get("helpers") or [])
    helpers.append(_player_ref(player))
    responses[canonical] = {
        "action": canonical,
        "location": response["location"],
        "label": response["label"],
        "result": response["result"],
        "completed": True,
        "first_completed_by": (
            existing.get("first_completed_by") or _player_ref(player)
        ),
        "helpers": helpers,
    }
    already.add(canonical)
    contributors[player_key] = sorted(already)
    current["responses"] = responses
    current["contributors"] = contributors
    event["current"] = current
    _save(event)

    from world.events import publish_world_event

    published = publish_world_event(
        "server.long_blackout.local_response",
        actor=player,
        payload={
            "server_event_id": stable_id,
            "response": canonical,
            "location": response["location"],
            "resident_ids": list(response.get("resident_ids") or []),
            "publicity": "private",
            "first_completion": first_completion,
        },
    )

    _metric(contributions=1)
    return {
        "response": canonical,
        "label": response["label"],
        "result": response["result"],
        "first_completion": first_completion,
        "event_id": published["id"],
    }, None


def _outcome(definition, current):
    completed = set((current.get("responses") or {}).keys())
    total = len(definition.get("responses") or {})
    count = len(completed)

    if count >= total:
        quality = "coordinated"
        summary = (
            "Every major public node found help. Street lamps were stabilized, "
            "the tavern sheltered stranded residents, St. Lazarus stretched its "
            "candles, and the Lamp Shop distributed emergency supplies."
        )
    elif count >= 2:
        quality = "partial"
        summary = (
            "The village restored light with uneven local strain. Some public "
            "nodes received organized help while others improvised without it."
        )
    else:
        quality = "rough"
        summary = (
            "The lights returned, but most institutions endured the outage "
            "without organized player help. Shortages, soot, and strained "
            "households remain part of the aftermath."
        )

    return {
        "quality": quality,
        "completed_response_count": count,
        "total_response_count": total,
        "completed_responses": sorted(completed),
        "summary": summary,
    }


def _resolve(stable_id, definition, event, day, hour):
    current = copy.deepcopy(dict(event.get("current") or {}))
    outcome = _outcome(definition, current)

    from world.events import publish_world_event

    end = publish_world_event(
        "server.long_blackout.ended",
        payload={
            "server_event_id": stable_id,
            "headline": definition["end_headline"],
            "public_summary": outcome["summary"],
            "harbinger": True,
            "chronicle_eligible": True,
            "resident_ids": list(definition.get("resident_ids") or []),
            "outcome_quality": outcome["quality"],
            "completed_responses": outcome["completed_responses"],
        },
        rumor=(
            "The village lights are back. People disagree about whether the "
            "blackout proved the village resilient or merely lucky."
        ),
    )
    aftermath_day, aftermath_hour = _add_hours(
        day,
        hour,
        definition.get("aftermath_hours") or 1,
    )

    current["state"] = "aftermath"
    current["outcome"] = outcome
    current["ended_day"] = int(day)
    current["ended_hour"] = int(hour)
    current["end_event_id"] = end["id"]
    current["end_publications"] = copy.deepcopy(end.get("publications") or {})
    current["end_rumor_id"] = (
        (end.get("rumor") or {}).get("rumor_id")
        if isinstance(end.get("rumor"), dict)
        else None
    )
    current["aftermath_until_day"] = aftermath_day
    current["aftermath_until_hour"] = aftermath_hour

    event["state"] = "aftermath"
    event["current"] = current
    _save(event)
    reconcile_server_event_overlays()
    _metric(resolutions=1)
    return get_server_event(stable_id)


def _clear_aftermath(stable_id, event):
    current = copy.deepcopy(dict(event.get("current") or {}))
    history = copy.deepcopy(list(event.get("history") or []))
    if current:
        history.append(current)
    event["history"] = history[-MAX_HISTORY:]
    event["state"] = "dormant"
    event["current"] = None
    _save(event)
    reconcile_server_event_overlays()
    _metric(aftermath_clears=1)
    return get_server_event(stable_id)


def advance_server_events(*, day, hour):
    day = int(day)
    hour = int(hour)
    registry = _registry()
    events = copy.deepcopy(dict(registry.db.events or {}))
    started = []
    resolved = []
    cleared = []

    for stable_id, definition in DEFINITIONS.items():
        event = dict(events.get(stable_id) or _empty_event(stable_id))
        state = event.get("state")
        current = dict(event.get("current") or {})

        if state == "active" and current:
            due = (int(current["end_day"]), int(current["end_hour"]))
            if (day, hour) >= due:
                _resolve(stable_id, definition, event, day, hour)
                resolved.append(stable_id)
                event = get_server_event(stable_id)
                state = event.get("state")
                current = dict(event.get("current") or {})

        if state == "aftermath" and current:
            due = (
                int(current["aftermath_until_day"]),
                int(current["aftermath_until_hour"]),
            )
            if (day, hour) >= due:
                _clear_aftermath(stable_id, event)
                cleared.append(stable_id)
                event = get_server_event(stable_id)
                state = event.get("state")

        if state == "dormant" and _trigger_matches(definition, day, hour):
            if start_server_event(stable_id, day=day, hour=hour):
                started.append(stable_id)

    _metric(checks=1)
    return {
        "started": started,
        "resolved": resolved,
        "cleared": cleared,
    }


def current_server_events():
    results = []
    for stable_id in DEFINITIONS:
        event = get_server_event(stable_id)
        if event and event.get("state") in {"active", "aftermath"}:
            results.append(event)
    return results


def status_lines(player=None):
    events = current_server_events()
    if not events:
        return ["No village-wide emergency is active."]

    lines = []
    for event in events:
        definition = DEFINITIONS[event["id"]]
        current = dict(event.get("current") or {})
        lines.append(f"{definition['title']}: {event['state']}.")
        if event["state"] == "active":
            done = len(current.get("responses") or {})
            total = len(definition.get("responses") or {})
            lines.append(
                f"Local responses completed: {done} of {total}."
            )
            if player is not None:
                room_key = getattr(getattr(player, "location", None), "key", None)
                action, response = _local_response(definition, room_key)
                if response:
                    if action in (current.get("responses") or {}):
                        lines.append(
                            f"Here: {response['result']}. Additional hands can still help."
                        )
                    else:
                        lines.append(
                            f"Here: {response['label']}. Use event {action}."
                        )
        else:
            outcome = dict(current.get("outcome") or {})
            if outcome.get("summary"):
                lines.append("Aftermath: " + outcome["summary"])
    return lines
