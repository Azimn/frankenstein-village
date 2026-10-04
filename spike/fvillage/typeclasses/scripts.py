"""
Scripts

Scripts are powerful jacks-of-all-trades. They have no in-game
existence and can be used to represent persistent game systems in some
circumstances. Scripts can also have a time component that allows them
to "fire" regularly or a limited number of times.

There is generally no "tree" of Scripts inheriting from each other.
Rather, each script tends to inherit from the base Script class and
just overloads its hooks to have it perform its function.

"""

from pathlib import Path

from evennia.scripts.scripts import DefaultScript

REPO_ROOT = Path(__file__).resolve().parents[3]


class Script(DefaultScript):
    """
    This is the base TypeClass for all Scripts. Scripts describe
    all entities/systems without a physical existence in the game world
    that require database storage (like an economic system or
    combat tracker). They
    can also have a timer/ticker component.

    A script type is customized by redefining some or all of its hook
    methods and variables.

    * available properties (check docs for full listing, this could be
      outdated).

     key (string) - name of object
     name (string)- same as key
     aliases (list of strings) - aliases to the object. Will be saved
              to database as AliasDB entries but returned as strings.
     dbref (int, read-only) - unique #id-number. Also "id" can be used.
     date_created (string) - time stamp of object creation
     permissions (list of strings) - list of permission strings

     desc (string)      - optional description of script, shown in listings
     obj (Object)       - optional object that this script is connected to
                          and acts on (set automatically by obj.scripts.add())
     interval (int)     - how often script should run, in seconds. <0 turns
                          off ticker
     start_delay (bool) - if the script should start repeating right away or
                          wait self.interval seconds
     repeats (int)      - how many times the script should repeat before
                          stopping. 0 means infinite repeats
     persistent (bool)  - if script should survive a server shutdown or not
     is_active (bool)   - if script is currently running

    * Handlers

     locks - lock-handler: use locks.add() to add new lock strings
     db - attribute-handler: store/retrieve database attributes on this
                        self.db.myattr=val, val=self.db.myattr
     ndb - non-persistent attribute handler: same as db but does not
                        create a database entry when storing data

    * Helper methods

     create(key, **kwargs)
     start() - start script (this usually happens automatically at creation
               and obj.script.add() etc)
     stop()  - stop script, and delete it
     pause() - put the script on hold, until unpause() is called. If script
               is persistent, the pause state will survive a shutdown.
     unpause() - restart a previously paused script. The script will continue
                 from the paused timer (but at_start() will be called).
     time_until_next_repeat() - if a timed script (interval>0), returns time
                 until next tick

    * Hook methods (should also include self as the first argument):

     at_script_creation() - called only once, when an object of this
                            class is first created.
     is_valid() - is called to check if the script is valid to be running
                  at the current time. If is_valid() returns False, the running
                  script is stopped and removed from the game. You can use this
                  to check state changes (i.e. an script tracking some combat
                  stats at regular intervals is only valid to run while there is
                  actual combat going on).
      at_start() - Called every time the script is started, which for persistent
                  scripts is at least once every server start. Note that this is
                  unaffected by self.delay_start, which only delays the first
                  call to at_repeat().
      at_repeat() - Called every self.interval seconds. It will be called
                  immediately upon launch unless self.delay_start is True, which
                  will delay the first call of this method by self.interval
                  seconds. If self.interval==0, this method will never
                  be called.
      at_pause()
      at_stop() - Called as the script object is stopped and is about to be
                  removed from the game, e.g. because is_valid() returned False.
      at_script_delete()
      at_server_reload() - Called when server reloads. Can be used to
                  save temporary variables you want should survive a reload.
      at_server_shutdown() - called at a full server shutdown.
      at_server_start()

    """

    pass


class SpikeScript(DefaultScript):
    """Base class for village scripts: self-healing tickers.

    Scripts created via `evennia shell` start their tickers in the shell's
    process, not the server's. After a reload the server then sees
    is_active=True but has no task (ndb._task is None), and the normal
    pause/unpause cycle has no paused state to resume from — so the ticker
    silently never runs. This safety net starts it in-server on boot.
    (2026-10-02: every script ticker in the village was dead this way.)
    """

    def at_server_start(self):
        if not self.is_active:
            return
        task = self.ndb._task
        if not task or not task.running:
            self.start()


class AmbientLife(SpikeScript):
    """Ticking ambient life for the spike, from canon ambient-events v0.1.

    Every few minutes (irregularly), one observable happening from the
    canon file is emitted to the room it belongs to — a bell, a cat, a
    guttering candle. No mechanics, no choices; seeds for gossip. Rooms
    that currently hold players are preferred, so the life lands where
    someone can witness it.
    """

    # Canon sections mapped onto spike rooms. Sections for locations the
    # spike doesn't have yet (manor, marshes, ...) are skipped.
    SECTION_ROOMS = {
        "tavern & the inn": ["The Blood of the Vine", "Inn Common Room"],
        "well & the square": ["Village Square"],
    }

    def at_script_creation(self):
        self.key = "ambient_life"
        self.desc = "Canon ambient events, ticking."
        self.interval = 150
        self.persistent = True

    def _load_events(self):
        """Parse {room_key: [event texts]} out of the canon markdown."""
        import re

        path = REPO_ROOT / "files" / "ambient-events-v0.1.md"
        try:
            text = path.read_text(encoding="utf-8")
        except OSError:
            return {}
        events = {}
        current_rooms = []
        entry_re = re.compile(r"^\*\*(\d+)\.\*\*\s*(.+?)\s*—\s*\*Seen by:\*", re.M)
        for line in text.splitlines():
            m = re.match(r"^##\s+(.+?)\s*\(\d+[–-]\d+\)\s*$", line)
            if m:
                section = m.group(1).lower()
                current_rooms = []
                for key, rooms in self.SECTION_ROOMS.items():
                    if key in section:
                        current_rooms = rooms
                        break
                continue
            m = entry_re.match(line)
            if m and current_rooms:
                body = m.group(2).strip()
                for room_key in current_rooms:
                    events.setdefault(room_key, []).append(body)
        return events

    def at_repeat(self):
        import random
        from evennia.utils import search

        # Irregular rhythm: roughly two out of three ticks speak.
        if random.random() > 0.65:
            return
        events = self._load_events()
        if not events:
            return
        candidates = []
        for room_key, texts in events.items():
            found = [o for o in search.search_object(room_key) if o.key == room_key]
            if not found or not texts:
                continue
            room = found[0]
            players = sum(1 for o in room.contents if o.has_account)
            # Weight rooms with witnesses; empty rooms still tick quietly.
            candidates.extend([room] * (1 + 3 * players))
        if not candidates:
            return
        room = random.choice(candidates)
        text = random.choice(events[room.key])
        room.msg_contents(text)


class RoomSixMystery(DefaultScript):
    """Materialized world flags for Room Six. No ticker.

    Canonical causal history lives in WorldEventLedger; these flags are the
    fast projection used by the current gameplay code.

    db.m_told_by: key of the first player who gave the note to M.
    db.tavern_told_by: key of the first player who let the Tavern hear it.
    Per-player stages live on the characters themselves (db.room_six).
    """

    def at_script_creation(self):
        self.key = "room_six"
        self.desc = "Room Six mystery: world flags."
        self.interval = -1
        self.persistent = True


class ModerationQueue(DefaultScript):
    """Persistent, human-reviewed report queue.

    Reports create records only. They never warn, mute, move, or punish a
    player automatically. A human staff account must explicitly review and
    close each record.
    """

    def at_script_creation(self):
        self.key = "moderation_queue"
        self.desc = "Human-reviewed compact reports."
        self.interval = -1
        self.persistent = True
        if self.db.reports is None:
            self.db.reports = []
        if self.db.next_report_id is None:
            self.db.next_report_id = 1

    def submit(self, report):
        reports = list(self.db.reports or [])
        report = dict(report)
        report["id"] = int(self.db.next_report_id or 1)
        report["status"] = "open"
        self.db.next_report_id = report["id"] + 1
        reports.append(report)
        self.db.reports = reports
        return report

    def open_reports(self):
        return [
            dict(report)
            for report in (self.db.reports or [])
            if report.get("status") == "open"
        ]

    def close_report(self, report_id, reviewer_account):
        import time

        reports = list(self.db.reports or [])
        for report in reports:
            if report.get("id") == report_id and report.get("status") == "open":
                report["status"] = "closed"
                report["reviewed_at"] = time.time()
                report["reviewed_by"] = reviewer_account.key
                report["reviewed_by_id"] = reviewer_account.id
                self.db.reports = reports
                return dict(report)
        return None


class WorldEventLedger(DefaultScript):
    """Canonical persistent event ledger for world changes."""

    def at_script_creation(self):
        self.key = "world_event_ledger"
        self.desc = "Canonical persistent event ledger."
        self.interval = -1
        self.persistent = True
        if self.db.events is None:
            self.db.events = []
        if self.db.next_event_id is None:
            self.db.next_event_id = 1

    def begin_event(self, event):
        events = list(self.db.events or [])
        event = dict(event)
        event["id"] = int(self.db.next_event_id or 1)
        event["status"] = "recorded"
        self.db.next_event_id = event["id"] + 1
        events.append(event)
        self.db.events = events
        return dict(event)

    def update_event(self, event_id, **fields):
        events = list(self.db.events or [])
        updated = None
        for index, event in enumerate(events):
            if event.get("id") != event_id:
                continue
            replacement = dict(event)
            replacement.update(fields)
            events[index] = replacement
            updated = replacement
            break
        if updated is not None:
            self.db.events = events
            return dict(updated)
        return None

    def get_event(self, event_id):
        for event in self.db.events or []:
            if event.get("id") == event_id:
                return dict(event)
        return None


_NUMWORDS = [
    "twelve", "one", "two", "three", "four", "five", "six", "seven",
    "eight", "nine", "ten", "eleven",
]


def village_hour_name(hour):
    """'nine of the evening' — the bell's vocabulary."""
    if hour == 0:
        return "midnight"
    if hour == 12:
        return "noon"
    if 1 <= hour <= 4:
        return f"{_NUMWORDS[hour]} of the small hours"
    if 5 <= hour <= 11:
        return f"{_NUMWORDS[hour]} of the morning"
    return f"{_NUMWORDS[hour - 12]} of the {'afternoon' if hour < 18 else 'evening'}"


class WarmthWatch(SpikeScript):
    """The body, prototyped: one internal variable with a voice.

    Jay's bladder principle (2026-09-29): the underlying variable and the
    perceived/narrated state are SEPARATE layers that may legitimately
    diverge (0.73 on the slider vs the felt urgency). Here: db.warmth is
    the runtime's number; _felt_band() is the narrator's words. They are
    aligned today; the split is architectural, so fever, fear, or drink
    can later move the feeling without touching the number.

    Rain + square drains; hearths restore. Threshold-crossing narration
    only — no mechanical penalties yet. This is the prototype the whole
    needs-slider architecture (hunger, fatigue) will follow.
    """

    ROOM_KEYS = (
        "Private Room", "Inn Common Room", "Inn Hallway",
        "Village Square", "The Blood of the Vine", "Tavern Back Hall",
    )

    def at_script_creation(self):
        self.key = "warmth_watch"
        self.desc = "The body's warmth, ticking."
        self.interval = 60
        self.persistent = True

    @staticmethod
    def _felt_band(warmth):
        if warmth >= 0.75:
            return "warm"
        if warmth >= 0.5:
            return "cool"
        if warmth >= 0.25:
            return "cold"
        return "freezing"

    @staticmethod
    def _band_line(band):
        return {
            "cool": "A chill settles into your shoulders.",
            "cold": "You are shivering.",
            "freezing": "The cold has settled into your bones. Find a hearth.",
            "warm": "Warmth spreads through you.",
        }.get(band)

    def _tick_char(self, char, room_key, weather):
        w = char.db.warmth
        if w is None:
            w = 1.0
        if room_key == "Village Square":
            if weather == "rain":
                w -= 0.08
            elif weather == "fog":
                w -= 0.03
            else:
                w -= 0.02
        elif room_key == "Inn Hallway":
            w -= 0.01
        else:
            # Private Room, Inn Common Room, The Tavern: hearths.
            w += 0.08
        w = max(0.0, min(1.0, w))
        char.db.warmth = w
        band = self._felt_band(w)
        old = char.db.warmth_band
        if old is None:
            # First sighting: calibrate silently.
            char.db.warmth_band = band
            return
        if old != band:
            char.db.warmth_band = band
            line = self._band_line(band)
            if line:
                char.msg(line)

    def at_repeat(self):
        from evennia.utils import search
        from evennia.scripts.models import ScriptDB

        try:
            weather = ScriptDB.objects.get(db_key="village_weather").db.state
        except Exception:
            weather = "clear"
        for key in self.ROOM_KEYS:
            found = [o for o in search.search_object(key) if o.key == key]
            if not found:
                continue
            for room in found:
                for char in room.contents:
                    if not char.has_account:
                        continue
                    self._tick_char(char, key, weather)


class VillageTime(SpikeScript):
    """The village clock. One game-hour per ten real minutes.

    Time is prosthetic memory for players whose context resets: the bell
    gives every session temporal landmarks worth writing down.
    """

    def at_script_creation(self):
        self.key = "village_time"
        self.desc = "The village clock."
        self.interval = 600
        self.persistent = True
        if self.db.hour is None:
            self.db.hour = 21  # the village starts at night

    def at_repeat(self):
        from evennia.utils import search

        # NOTE: do NOT write `(self.db.hour or 21)` — midnight is 0,
        # which is falsy, and the old expression jumped 0 -> 22 after
        # every midnight (caught by the 2026-10-03 lurker playtest).
        hour = self.db.hour
        if hour is None:
            hour = 21
        hour = (hour + 1) % 24
        self.db.hour = hour
        name = village_hour_name(hour)
        for key in ("Village Square", "The Blood of the Vine", "Inn Common Room",
                    "Inn Hallway", "Private Room", "Tavern Back Hall"):
            found = [o for o in search.search_object(key) if o.key == key]
            if not found:
                continue
            for room in found:
                if any(o.has_account for o in room.contents):
                    room.msg_contents(f"The village bell counts {name}.")


class VillageWeather(SpikeScript):
    """Weather over the square. Shifts every ~25 minutes, irregularly.

    The square's description has smelled of rain that hasn't fallen since
    the spike began. Now it falls.
    """

    WEATHER_SENSE = {
        "clear": "The night air is cold and clear.",
        "fog": "Fog deadens every sound; the gaslight is a smear.",
        "rain": "Rain drums on the cobbles; the smell of wet stone rises.",
    }
    ARRIVE_MSGS = {
        "clear": "The sky clears over the square.",
        "fog": "Fog rolls into the square, deadening every sound.",
        "rain": "Rain begins to fall on the square, hissing on the gaslight.",
    }
    LEAVE_MSGS = {
        "fog": "The fog thins over the square.",
        "rain": "The rain eases off over the square.",
    }

    def at_script_creation(self):
        self.key = "village_weather"
        self.desc = "Weather over the village square."
        self.interval = 1500
        self.persistent = True
        if not self.db.state:
            self.db.state = "fog"

    def set_weather(self, state):
        """Transition to `state`, announcing and updating the square."""
        from evennia.utils import search

        old = self.db.state
        if old == state:
            return
        self.db.state = state
        found = [o for o in search.search_object("Village Square")
                 if o.key == "Village Square"]
        if found:
            square = found[0]
            square.db.weather_sense = self.WEATHER_SENSE[state]
            leave = self.LEAVE_MSGS.get(old)
            arrive = self.ARRIVE_MSGS[state]
            msg = f"{leave} {arrive}" if leave else arrive
            square.msg_contents(msg)

    def at_repeat(self):
        import random

        old = self.db.state or "fog"
        # Weather lingers: half the time nothing changes.
        if random.random() < 0.5:
            return
        choices = [s for s in self.WEATHER_SENSE if s != old]
        self.set_weather(random.choice(choices))


class CatLife(SpikeScript):
    """The tavern cat's drives, ticking.

    Curiosity moves her between haunts; comfort keeps her there a while.
    She watches newcomers, performs small cattenings, and once in a blue
    moon does the wren thing (ambient-events #2). She never speaks — which
    is the point, except on the rarest of ticks, when she does, and that
    is also the point: not all residents need language to be alive, but
    the world is never 100% reliable, and the exceptions are what make
    players ask how much is scripted. A miracle with no witness is
    wasted, so the rarest beats only fire when players are present.
    """

    # Per effective tick (the quiet gate already passed). ~15 effective
    # ticks/hour of occupied time -> 1/800 lands roughly once every two
    # days of someone actually being there. Rare enough to be doubted.
    MIRACLE_CHANCE = 1 / 800

    def at_script_creation(self):
        self.key = "cat_life"
        self.desc = "The tavern cat, being a cat."
        self.interval = 110
        self.persistent = True

    def _miracle(self, loc, players):
        """One of the rare beats. Returns True if one fired."""
        import random

        from evennia.utils import create

        player = random.choice(players)
        roll = random.random()
        if roll < 0.34:
            # the gift: an inventory item, presented with ceremony
            mouse = create.create_object(
                "typeclasses.objects.Object",
                key="a dead mouse",
                location=player,
            )
            mouse.db.desc = (
                "A dead mouse, laid at your feet with terrible ceremony. "
                "The cat is watching to see what you do with it."
            )
            loc.msg_contents(
                f"The tavern cat pads to {player.key}, drops something "
                "small and still at their feet, and looks up — waiting."
            )
        elif roll < 0.67:
            # the word: she speaks, once, and denies it utterly
            loc.msg_contents(
                f"The tavern cat looks directly at {player.key} and says, "
                "quite clearly: \"Again.\" Then she begins washing her face "
                "with great dignity, as if nothing happened."
            )
        else:
            # the leading: she wants you to follow
            loc.msg_contents(
                "The tavern cat walks to the tavern door, stops, and looks "
                f"back at {player.key}. Waiting."
            )
        return True

    def at_repeat(self):
        import random

        cat = self.obj
        if not cat or not cat.location:
            return
        loc = cat.location
        # Quiet more often than not: a cat mostly sleeps.
        if random.random() > 0.55:
            return

        spots = cat.db.spots or ["the hearth"]
        spot = cat.db.spot or spots[0]
        players = [o for o in loc.contents if o.has_account and o != cat]

        # the miracle tier: checked first, fires almost never
        if players and random.random() < self.MIRACLE_CHANCE:
            self._miracle(loc, players)
            return

        roll = random.random()
        if roll < 0.35:
            # curiosity: relocate
            new_spot = random.choice([s for s in spots if s != spot] or spots)
            cat.db.spot = new_spot
            loc.msg_contents(
                f"The tavern cat pads from {spot} to {new_spot}."
            )
        elif roll < 0.55 and players:
            # watch someone
            watcher = random.choice(players)
            loc.msg_contents(
                f"The tavern cat watches {watcher.key} from {spot}, "
                "unblinking."
            )
        elif roll < 0.75:
            loc.msg_contents(
                random.choice([
                    f"The tavern cat stretches along {spot}, claws out, "
                    "then thinks better of it.",
                    f"The tavern cat washes one paw at {spot} with total "
                    "commitment.",
                    f"The tavern cat sleeps at {spot}. Her sides rise and "
                    "fall like a tiny bellows.",
                ])
            )
        elif roll < 0.93:
            loc.msg_contents(
                random.choice([
                    "The tavern cat chases a dust mote through a bar of "
                    "lamplight, misses, and sits down as if that was the "
                    "plan.",
                    "Somewhere under a table, the tavern cat purrs at "
                    "something only she can see.",
                ])
            )
        else:
            # the wren thing, rarely and without explanation
            loc.msg_contents(
                "The tavern cat carries something small and dark to the "
                "hearth, lays it precisely before the empty chair, and "
                "stares at it."
            )


class TavernLife(SpikeScript):
    """Ambient life for the Blood of the Vine.

    Every interval, one beat: gossip, toasts, brooding, cross-talk, a
    regular eating or drinking through the real consumable pipeline, or
    Bram polishing. The room is mid-conversation when players arrive —
    the NPC pub doesn't need an audience.
    """

    def at_script_creation(self):
        self.key = "tavern_life"
        self.desc = "Ambient life in the Blood of the Vine."
        self.interval = 150
        self.persistent = True

    def at_repeat(self):
        from world.tavern_life import run_beat
        run_beat()
