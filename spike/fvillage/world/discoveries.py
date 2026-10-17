"""Mask-private, first-hand discovery of persistent physical village landmarks.

The player must inspect the actual object in their current IC room. Looking at
unseen rooms, reading public mysteries or receiving a rumour cannot confer a
firsthand discovery. This is a personal field notebook, not a quest or proof of
a supernatural explanation.
"""
from __future__ import annotations

import copy

MAX_DISCOVERIES = 16

LANDMARKS = {
    "grave_marker": {
        "key": "a weathered grave marker",
        "room": "St. Lazarus Churchyard",
        "summary": "An older date and a second set of initials were recut by different hands.",
    },
    "red_cord": {
        "key": "a frayed red cord",
        "room": "The Northern Treeline",
        "summary": "A red cord was cut at one end and torn at the other.",
    },
    "market_scale": {
        "key": "a crooked market scale",
        "room": "Market Lane",
        "summary": "The empty scale was unbalanced and the slate gave conflicting prices.",
    },
    "river_gauge": {
        "key": "a river gauge",
        "room": "Riverside Path",
        "summary": "A nearly illegible flood date sat above the earlier winter high-water mark.",
    },
}


def normalize(raw):
    result = []
    seen = set()
    try:
        entries = list(raw or [])[:128]
    except (ValueError, TypeError):
        return []
    for value in entries:
        if not hasattr(value, "get"):
            continue
        ident = value.get("id")
        if not isinstance(ident, str) or ident not in LANDMARKS or ident in seen:
            continue
        try:
            day, hour = int(value.get("day")), int(value.get("hour"))
        except (TypeError, ValueError, OverflowError):
            continue
        if day < 1 or not 0 <= hour <= 23:
            continue
        seen.add(ident)
        result.append({"id": ident, "day": day, "hour": hour})
        if len(result) == MAX_DISCOVERIES:
            break
    return result


def record(raw, ident, day, hour):
    if ident not in LANDMARKS:
        return normalize(raw), False
    entries = normalize(raw)
    if any(entry["id"] == ident for entry in entries):
        return entries, False
    try:
        day, hour = int(day), int(hour)
    except (ValueError, TypeError, OverflowError):
        return entries, False
    if day < 1 or not 0 <= hour <= 23 or len(entries) >= MAX_DISCOVERIES:
        return entries, False
    entries.append({"id": ident, "day": day, "hour": hour})
    return entries, True


def inspected_today(raw, ident, day):
    """An old field note is not evidence of inspecting today's conditions."""
    if ident not in LANDMARKS:
        return False
    if not isinstance(raw, dict):
        return False
    observed = raw.get(ident)
    if not isinstance(observed, dict):
        return False
    try:
        checked_day = int(observed.get("day"))
        checked_hour = int(observed.get("hour"))
    except (ValueError, TypeError, OverflowError):
        return False
    return checked_day == day and 0 <= checked_hour <= 23


def capture(looker, physical, ident):
    """Persist only an authenticated in-person inspection by this mask."""
    spec = LANDMARKS.get(ident)
    room = getattr(physical, "location", None)
    if (not spec or not looker or not getattr(looker, "account", None)
            or getattr(looker, "location", None) != room
            or getattr(room, "key", None) != spec["room"]
            or getattr(physical, "key", None) != spec["key"]
            or not room.tags.has("ic", category="side")):
        return False
    from evennia.scripts.models import ScriptDB
    try:
        clock = ScriptDB.objects.get(db_key="village_time")
        day = int(clock.db.day or 1)
        hour = int(clock.db.hour if clock.db.hour is not None else 21)
    except ScriptDB.DoesNotExist:
        day, hour = 1, 21
    # The lifelong first-discovery ledger stays immutable, while repeat
    # physical inspections are also stamped for today's renewable civic work.
    # An old first visit is never sufficient evidence of a NEW day's patrol.
    latest = dict(getattr(looker.db, "landmark_latest_view", None) or {})
    latest[ident] = {"day": day, "hour": hour}
    looker.db.landmark_latest_view = {
        key: value for key, value in latest.items() if key in LANDMARKS
    }
    rows, changed = record(
        getattr(looker.db, "landmark_discoveries", None), ident, day, hour
    )
    if changed:
        looker.db.landmark_discoveries = copy.deepcopy(rows)
    # The permanent journal remembers the first visit. A separate tiny
    # observation timestamp is updated on *every genuine inspection* so a
    # report for tomorrow requires revisiting the actual object.
    latest = dict(getattr(looker.db, "landmark_last_inspected", None) or {})
    latest = {
        key: dict(value) for key, value in latest.items()
        if key in LANDMARKS and isinstance(value, dict)
    }
    latest[ident] = {"day": day, "hour": hour}
    looker.db.landmark_last_inspected = latest
    return changed


def journal_lines(raw):
    rows = normalize(raw)
    if not rows:
        return [
            "You have not personally inspected any district landmarks.",
            "Explore beyond the Square. Look at a named physical clue there",
            "to keep a firsthand record; reports from others are not yours.",
        ]
    lines = ["|wYour firsthand field discoveries|n"]
    for item in rows:
        spec = LANDMARKS[item["id"]]
        lines.append(
            f"* {spec['key']} ({spec['room']}, day {item['day']} "
            f"at {item['hour']:02d}:00): {spec['summary']}"
        )
    lines.append(
        "These are observations, not verified explanations. "
        "Use |wdiary|n to write your own interpretation."
    )
    return lines
