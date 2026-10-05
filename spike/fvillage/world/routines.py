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
    "andrei": [
        (5, 7, "St. Lazarus Church", "says matins alone"),
        (7, 11, "Village Square", "does his parish rounds"),
        (11, 14, "St. Lazarus Church", "keeps the office, hears confessions"),
        (14, 17, OFFSTAGE, "visits the outlying farms"),
        (17, 19, "St. Lazarus Church", "says vespers"),
        (19, 22, "The Blood of the Vine", "argues theology with János over small beer"),
        (22, 24, OFFSTAGE, "sleeps"),
        (0, 5, OFFSTAGE, "sleeps"),
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
    ("andrei", "The Blood of the Vine"): (
        "Father Andrei comes in, cassock brushed, and takes the stool "
        "across from János. \"The usual argument, then.\""
    ),
    ("andrei", "Village Square"): (
        "Father Andrei crosses the square at an unhurried pace, stopping "
        "for every third person."
    ),
    ("andrei", "St. Lazarus Church"): (
        "Father Andrei slips into the church, candles taking his silhouette."
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
    ("andrei", "The Blood of the Vine"): (
        "Father Andrei drains his small beer. \"Same time tomorrow, "
        "János. Bring better arguments.\""
    ),
    ("andrei", "Village Square"): (
        "Father Andrei finishes his rounds and turns toward the church."
    ),
    ("andrei", "St. Lazarus Church"): (
        "Father Andrei steps out, pulling the church door to behind him."
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
    deltas = _deltas()
    shift = deltas.get(regular_key, {}).get("tavern_shift", 0)
    for start, end, _room, doing in SCHEDULES.get(regular_key, []):
        if _room == "The Blood of the Vine":
            start, end = start + shift, end + shift
        if start <= hour < end:
            return doing
    return "keeps his own counsel"


def _all_regulars():
    from evennia.objects.models import ObjectDB

    return list(
        ObjectDB.objects.filter(
            db_typeclass_path__in=[
                "typeclasses.characters.TavernRegular",
                "typeclasses.characters.FatherAndrei",
            ]
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


def set_deviation(regular, room_key, until_hour, reason, day=None):
    """Park a regular somewhere else until an hour, with a reason.

    `regular` is the object or its regular_key. The override is honored
    by advance() and cleared when it expires. Events and player verbs
    call this — the reason keeps the deviation attributable. `day`
    (game-day count) pins a deviation to a single day, for feasts.
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
        "day": day,
    }
    return True


def _target_room(reg, hour, day=None):
    """Where this regular should be: deviation beats schedule."""
    override = reg.db.routine_override
    if override:
        if override.get("day") is not None and override["day"] != day:
            override = None  # a feast day's deviation, expired overnight
            reg.db.routine_override = None
        elif hour < override.get("until", -1):
            return override["room"], "deviation"
        else:
            reg.db.routine_override = None  # expired
    return where_should_be(reg.db.regular_key, hour), "schedule"


def advance(hour=None, weather=None, day=None):
    """Move every regular to where they should be. Returns move count."""
    hour = _hour() if hour is None else hour
    weather = _weather() if weather is None else weather
    if day is None:
        try:
            from evennia.scripts.models import ScriptDB

            day = ScriptDB.objects.get(db_key="village_time").db.day or 1
        except ScriptDB.DoesNotExist:
            day = 1
    moves = 0
    for reg in _all_regulars():
        key = reg.db.regular_key
        target_key, source = _target_room(reg, hour, day)

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
    name = {"vasile": "Vasile", "magda": "Magda", "janos": "János",
            "andrei": "Father Andrei"}[key]
    pron = {"vasile": "he", "magda": "she", "janos": "he",
            "andrei": "he"}[key]
    # Push their tavern arrival one hour later. The shift is stored on the
    # routine script, not the module dict, so it survives restarts. Bounded
    # mod 4: without a bound the block drifts past midnight and they stop
    # coming at all (2026-10-04).
    deltas = routine.db.schedule_deltas or {}
    entry = deltas.get(key, {})
    entry["tavern_shift"] = (entry.get("tavern_shift", 0) + 1) % 4
    deltas[key] = entry
    routine.db.schedule_deltas = deltas
    old_start = [s for s in SCHEDULES[key]
                 if s[2] == "The Blood of the Vine"][0][0]
    new_start = old_start + entry["tavern_shift"]
    if entry["tavern_shift"] == 0:
        rumor = f"{name}'s back to keeping their old hours, by all accounts."
    else:
        rumor = (f"{name}'s been keeping different hours — in later than "
                 f"{pron} used to be.")
    try:
        from world.events import publish_world_event

        publish_world_event(
            "routine",
            actor=None,
            payload={"regular": key, "old_start": old_start,
                     "new_start": new_start},
            rumor=rumor,
        )
    except Exception:
        pass
    return {"regular": key, "old_start": old_start,
            "new_start": new_start}


# --- the sideboard: finite hospitality, keeper-resupplied ----------------------
# Backlog #13 (2026-10-04): fare used to be infinitely help-yourself. Each
# fare now carries servings_max, and eating/drinking decrements db.servings.
# The keeper refills the board on the routine tick — but only his hands do
# it, so if Bram is ever deviated away from the tavern, the board stays bare
# until he comes back. That's the deal: hospitality is work, not magic.


def restock_sideboard():
    """Refill depleted sideboard fare if Bram is in the tavern.

    Returns the list of refilled fare short names (for logs/tests). Fires
    only when something was actually refilled — quiet when the board's full.
    """
    tavern = _room("The Blood of the Vine")
    if not tavern:
        return []
    keeper = next((o for o in tavern.contents if o.key == "Bram"), None)
    if keeper is None:
        return []  # nobody's hands to set it out
    refilled = []
    for obj in tavern.contents:
        data = obj.db.consume or {}
        max_s = data.get("servings_max")
        if not max_s:
            continue  # water and the well mushrooms aren't the keeper's board
        left = obj.db.servings
        if left is None:
            left = max_s
        if left < max_s:
            obj.db.servings = max_s
            refilled.append(data.get("short") or obj.key)
    if refilled:
        tavern.msg_contents(
            "Bram comes out with a tray: "
            + ", ".join(refilled)
            + '. "There. The board\'s full again."'
        )
    return refilled


def tick():
    """One routine pass: move the village, apply feast observances, check month."""
    from evennia.scripts.models import ScriptDB

    moves = advance()
    try:
        from world.residents import population_tick
        population_result = population_tick()
        moves += int(population_result.get("moved") or 0)
    except Exception:
        population_result = None
    restock_sideboard()
    try:
        clock = ScriptDB.objects.get(db_key="village_time")
        day = clock.db.day or 1
        hour = clock.db.hour if clock.db.hour is not None else 21
        _apply_feast(day)
        _apply_mass(day, hour)
        routine = ScriptDB.objects.get(db_key="village_routine")
        if day and day % 30 == 0 and routine.db.last_monthly_day != day:
            routine.db.last_monthly_day = day
            monthly_shift(day)
    except ScriptDB.DoesNotExist:
        pass

    # Rumor traffic is part of the simulation, not a player-triggered effect.
    # One bounded retelling per occupied room per game-hour keeps it cheap.
    try:
        from world.rumors import propagate_colocated_npcs
        propagate_colocated_npcs(announce=False, max_per_room=1)
    except Exception:
        pass
    return moves


# --- Sunday mass ---------------------------------------------------------------
# 10:00 every Sunday. The congregation: Andrei, Magda, Vasile (back pew),
# and any players present. The homily reads the week's ledger — the priest
# comments on real events, obliquely. Attendees are blessed (db.blessed_day),
# which Andrei remembers and Magda notices.

MASS_CONGREGATION = (
    ("andrei", "says the mass"),
    ("magda", "sings loud enough for two"),
    ("vasile", "stands at the back, arms crossed, stays anyway"),
)

HOMILY_BY_KIND = {
    "confession": "We are grateful for the seal of the box, and for those "
                  "unburdened in it.",
    "routine": "We pray for those whose hours are unsettled.",
    "feast": "We give thanks for the turning year.",
}


def _homily_lines():
    """Two homily lines drawn from the week's real ledger events."""
    try:
        from world.events import get_event_ledger

        events = list(get_event_ledger().db.events or [])[-6:]
    except Exception:
        events = []
    lines = []
    for e in events:
        line = HOMILY_BY_KIND.get(e.get("kind"))
        if line and line not in lines:
            lines.append(line)
        if len(lines) >= 2:
            break
    if not lines:
        lines = ["We remember the week's small mercies, and name them quietly."]
    return lines


def hold_mass(day):
    """Ring the peal, gather the congregation, say the mass. Returns count."""
    from world import liturgical

    church = _room("St. Lazarus Church")
    if not church:
        return 0
    try:
        from evennia.scripts.models import ScriptDB
        routine = ScriptDB.objects.get(db_key="village_routine")
        if routine.db.last_mass_day == day:
            return 0  # already held today
        routine.db.last_mass_day = day
    except ScriptDB.DoesNotExist:
        return 0
    # Gather the authored congregation.
    for regular_key, _role in MASS_CONGREGATION:
        set_deviation(regular_key, "St. Lazarus Church", 11,
                      "Sunday mass", day=day)
    advance(day=day)

    # Gather the background population through the same persistent routine
    # machinery. Household attendance is deterministic and work exceptions are
    # explicit; no resident receives a per-NPC ticker.
    try:
        from world.residents import gather_population_for_mass
        gather_population_for_mass(day)
    except Exception:
        pass
    church.msg_contents("The church bell rings a full peal over the square.")
    # The 1890 ordo: this Sunday's name and Gospel, transcribed from the
    # Directory. Andrei preaches the text first, then the week's events.
    season, n, sunday_name, gospel_ref, gospel_topic, homily = (
        liturgical.sunday_ordo(day)
    )
    church.msg_contents(
        f'Father Andrei takes the altar. "In nomine Patris, et Filii, '
        f'et Spiritus Sancti. Today is the {sunday_name}."'
    )
    church.msg_contents(
        f'Andrei: "The Gospel is {gospel_ref}: {gospel_topic}. {homily}"'
    )
    for line in _homily_lines():
        church.msg_contents(f'Andrei: "{line}"')
    # The blessing: attendees are marked, and the village records it.
    # Only the living get blessed — not the pews, not the exits.
    attendees = []
    for o in church.contents:
        try:
            from world.residents import is_resident
            resident_person = is_resident(o)
        except Exception:
            resident_person = False
        is_person = (
            o.has_account
            or getattr(o.db, "regular_key", None)
            or resident_person
        )
        if is_person:
            o.db.blessed_day = day
            attendees.append(o.key)
    church.msg_contents(
        'Andrei raises his hands. "Benedicat vos omnipotens Deus." '
        "The candles bow, all at once, and straighten."
    )
    try:
        from world.events import publish_world_event

        publish_world_event(
            "mass",
            payload={"day": day, "attendees": attendees},
            rumor="Sunday mass was well attended.",
        )
    except Exception:
        pass
    return len(attendees)


def _apply_mass(day, hour):
    from world import liturgical

    if liturgical.is_sunday(day) and hour == 10:
        hold_mass(day)


def _apply_feast(day):
    """Feast-day observances: deviations with liturgical reasons."""
    from world import liturgical

    info = liturgical.feast_on_gameday(day)
    if not info or not info.get("observance"):
        return
    try:
        from evennia.scripts.models import ScriptDB
        routine = ScriptDB.objects.get(db_key="village_routine")
        if routine.db.last_feast_day == day:
            return  # already applied today
        routine.db.last_feast_day = day
    except ScriptDB.DoesNotExist:
        return
    for regular_key, room_key, reason in liturgical.observance_deviations(
        info["observance"]
    ):
        # Feast deviations last the whole day (until hour 24), pinned to
        # this game day so they expire overnight.
        set_deviation(regular_key, room_key, 24,
                      f"{info['name']}: {reason}", day=day)
    try:
        from world.events import publish_world_event

        m, dn = liturgical.game_date(day)
        publish_world_event(
            "feast",
            payload={"feast": info["name"], "date": f"{m}/{dn}"},
            rumor=f"Today is {info['name']}. {info['note']}",
        )
    except Exception:
        pass
