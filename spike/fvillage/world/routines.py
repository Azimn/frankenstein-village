"""Daily routines for the Blood of the Vine's regulars.

The clockwork base: each regular has a 24-hour schedule of (start, end,
room, doing). A ticker advances them — they walk out, do their business,
and come back. Offstage blocks mean "home": the churchyard, the cottage,
the woods edge — places the spike hasn't built yet.

The schedule is the default, not destiny. Two override paths:

1. Weather: Vasile's knees call rain before the sky does. When the
   square's weather is rain and he'd be heading for the tavern, he stays
   home — announced once, with a reason, so it's attributable.
2. set_deviation(): any event or player verb can park a regular somewhere
   else until a given hour, with a reason. The reason is the point: a
   deviation nobody can attribute is just a bug with good PR.

Every 30 game-days, monthly_shift() nudges one regular's hours and logs
it to the event ledger. The village is never quite the same place twice.
"""

OFFSTAGE = "Offstage"

# regular_key -> [(start_hour, end_hour, room_key, doing)]
# Hours are half-open [start, end); wrap handled by splitting at midnight.
SCHEDULES = {
    "vasile": [
        (5, 8, "Village Square", "draws well-water, muttering at the pigeons"),
        (8, 12, OFFSTAGE, "tends the churchyard graves"),
        (12, 14, "Village Square", "takes the midday air on the bench"),
        (14, 18, OFFSTAGE, "naps in his cottage; the joints demand it"),
        (18, 23, "The Blood of the Vine", "holds his corner with his ale"),
        (23, 24, OFFSTAGE, "sleeps"),
        (0, 5, OFFSTAGE, "sleeps"),
    ],
    "magda": [
        (5, 11, "Village Square", "works the wash at the well"),
        (11, 17, OFFSTAGE, "does her rounds with the linen basket"),
        (17, 23, "The Blood of the Vine", "holds court and collects"),
        (23, 24, OFFSTAGE, "sleeps"),
        (0, 5, OFFSTAGE, "sleeps"),
    ],
    "janos": [
        (6, 10, "Village Square", "walks a slow patrol, watching the roads"),
        (10, 18, OFFSTAGE, "works the woods edge"),
        (18, 24, "The Blood of the Vine", "drinks like the world's ending"),
        (0, 6, OFFSTAGE, "sleeps"),
    ],
}

# (regular_key, room_key) -> line shown in the room on arrival/departure.
# Offstage moves are silent: nobody there to see them go.
ARRIVE = {
    ("vasile", "The Blood of the Vine"): (
        "Old Vasile folds himself into his corner, joints complaining "
        "all the way down."
    ),
    ("vasile", "Village Square"): (
        "Old Vasile shuffles in from the lane, bucket in hand."
    ),
    ("magda", "The Blood of the Vine"): (
        "Magda bustles in, basket on hip, already mid-sentence with "
        "someone who isn't here yet."
    ),
    ("magda", "Village Square"): (
        "Magda claims her spot at the well, sleeves already rolling."
    ),
    ("janos", "The Blood of the Vine"): (
        "János comes in out of the cold, kit bag thumping against his leg."
    ),
    ("janos", "Village Square"): (
        "János crosses the square at a patrol's pace, eyes on the tree line."
    ),
}
DEPART = {
    ("vasile", "The Blood of the Vine"): (
        "Vasile drains his ale and rises with a sound like a coffin lid. "
        "\"Knees say home.\""
    ),
    ("vasile", "Village Square"): (
        "Vasile shoulders his bucket and shuffles off toward the lane."
    ),
    ("magda", "The Blood of the Vine"): (
        "Magda gathers her basket. \"Early water tomorrow. Don't burn "
        "the place down without me.\""
    ),
    ("magda", "Village Square"): (
        "Magda wrings out the last sheet and heads off on her rounds."
    ),
    ("janos", "The Blood of the Vine"): (
        "János hefts his kit bag. \"Roads don't watch themselves.\""
    ),
    ("janos", "Village Square"): (
        "János finishes his patrol circuit and heads for the tree line."
    ),
}


def _deltas():
    """Persisted per-regular schedule shifts (survives restarts)."""
    from evennia.scripts.models import ScriptDB

    try:
        routine = ScriptDB.objects.get(db_key="village_routine")
        return routine.db.schedule_deltas or {}
    except ScriptDB.DoesNotExist:
        return {}


def where_should_be(regular_key, hour, deltas=None):
    """Room key the schedule says for this hour. 'Offstage' if home."""
    if deltas is None:
        deltas = _deltas()
    shift = deltas.get(regular_key, {}).get("tavern_shift", 0)
    for start, end, room, _doing in SCHEDULES.get(regular_key, []):
        if room == "The Blood of the Vine":
            start, end = start + shift, end + shift
        if start <= hour < end:
            return room
    return OFFSTAGE


def doing_now(regular_key, hour):
    for start, end, _room, doing in SCHEDULES.get(regular_key, []):
        if start <= hour < end:
            return doing
    return "keeps his own counsel"


def _all_regulars():
    from evennia.objects.models import ObjectDB

    return list(
        ObjectDB.objects.filter(
            db_typeclass_path="typeclasses.characters.TavernRegular"
        )
    )


def _room(key):
    from evennia.utils import search

    found = [o for o in search.search_object(key) if o.key == key]
    return found[0] if found else None


def _hour():
    from evennia.scripts.models import ScriptDB

    try:
        clock = ScriptDB.objects.get(db_key="village_time")
        return clock.db.hour if clock.db.hour is not None else 21
    except ScriptDB.DoesNotExist:
        return 21


def _weather():
    from evennia.scripts.models import ScriptDB

    try:
        return ScriptDB.objects.get(db_key="village_weather").db.state
    except ScriptDB.DoesNotExist:
        return "fog"


def set_deviation(regular, room_key, until_hour, reason):
    """Park a regular somewhere else until an hour, with a reason.

    `regular` is the object or its regular_key. The override is honored
    by advance() and cleared when it expires. Events and player verbs
    call this — the reason keeps the deviation attributable.
    """
    if isinstance(regular, str):
        matches = [
            o for o in _all_regulars() if o.db.regular_key == regular
        ]
        if not matches:
            return False
        regular = matches[0]
    regular.db.routine_override = {
        "room": room_key,
        "until": until_hour,
        "reason": reason,
    }
    return True


def _target_room(reg, hour):
    """Where this regular should be: deviation beats schedule."""
    override = reg.db.routine_override
    if override and hour < override.get("until", -1):
        return override["room"], "deviation"
    if override:
        reg.db.routine_override = None  # expired
    return where_should_be(reg.db.regular_key, hour), "schedule"


def advance(hour=None, weather=None):
    """Move every regular to where they should be. Returns move count."""
    hour = _hour() if hour is None else hour
    weather = _weather() if weather is None else weather
    moves = 0
    for reg in _all_regulars():
        key = reg.db.regular_key
        target_key, source = _target_room(reg, hour)

        # Vasile's knees call rain before the sky does.
        if (
            source == "schedule"
            and key == "vasile"
            and weather == "rain"
            and target_key == "The Blood of the Vine"
        ):
            set_deviation(
                reg, OFFSTAGE, 23, "his knees said rain before the sky did"
            )
            tavern = _room("The Blood of the Vine")
            if tavern:
                tavern.msg_contents(
                    "No Vasile tonight — word is his knees called rain "
                    "before the sky did."
                )
            target_key, source = OFFSTAGE, "deviation"

        current = reg.location.key if reg.location else None
        if current == target_key:
            continue
        old_room = reg.location
        new_room = _room(target_key)
        if not new_room:
            continue
        if old_room and old_room.key != OFFSTAGE:
            line = DEPART.get((key, old_room.key))
            if line:
                old_room.msg_contents(line)
        reg.move_to(new_room, quiet=True)
        if target_key != OFFSTAGE:
            line = ARRIVE.get((key, target_key))
            if line:
                new_room.msg_contents(line)
        moves += 1
    return moves


def monthly_shift(day):
    """Every 30 game-days, nudge one regular's hours. Logged, observable."""
    from evennia.scripts.models import ScriptDB

    try:
        routine = ScriptDB.objects.get(db_key="village_routine")
    except ScriptDB.DoesNotExist:
        return None
    keys = list(SCHEDULES)
    idx = (routine.db.monthly_index or 0) % len(keys)
    routine.db.monthly_index = idx + 1
    key = keys[idx]
    name = {"vasile": "Vasile", "magda": "Magda", "janos": "János"}[key]
    pron = {"vasile": "he", "magda": "she", "janos": "he"}[key]
    # Push their tavern arrival one hour later. The shift is stored on the
    # routine script, not the module dict, so it survives restarts.
    deltas = routine.db.schedule_deltas or {}
    entry = deltas.get(key, {})
    entry["tavern_shift"] = entry.get("tavern_shift", 0) + 1
    deltas[key] = entry
    routine.db.schedule_deltas = deltas
    new_start = (
        [s for s in SCHEDULES[key] if s[2] == "The Blood of the Vine"][0][0]
        + entry["tavern_shift"]
    )
    try:
        from world.events import publish_world_event

        publish_world_event(
            "routine",
            actor=None,
            payload={"regular": key, "old_start": changed[0],
                     "new_start": changed[1]},
            rumor=(f"{name}'s been keeping different hours — in an hour "
                   f"later than {pron} used to be."),
        )
    except Exception:
        pass
    old_start = [s for s in SCHEDULES[key]
                 if s[2] == "The Blood of the Vine"][0][0]
    return {"regular": key, "old_start": old_start,
            "new_start": new_start}


def tick():
    """One routine pass: move the village, then check the month."""
    from evennia.scripts.models import ScriptDB

    moves = advance()
    try:
        clock = ScriptDB.objects.get(db_key="village_time")
        day = clock.db.day or 0
        routine = ScriptDB.objects.get(db_key="village_routine")
        if day and day % 30 == 0 and routine.db.last_monthly_day != day:
            routine.db.last_monthly_day = day
            monthly_shift(day)
    except ScriptDB.DoesNotExist:
        pass
    return moves
