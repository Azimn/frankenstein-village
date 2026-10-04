"""
Frankenstein Village spike — characters.

SpikeCharacter: default player character.
Innkeeper: M., who keeps the Inn Between. Speaks in the voice of the
arrival guide: welcoming, directive, always pointing at the front door.
"""
from evennia.objects.objects import DefaultCharacter
import random
import time


def _world_log():
    """The persistent world event log, kept on the ambient-life script."""
    try:
        from evennia.scripts.models import ScriptDB
        script = ScriptDB.objects.get(db_key="ambient_life")
    except Exception:
        return None
    return script


def log_world_event(kind, who=None):
    """Append {"t", "kind", "who"} to the world log (capped at 100)."""
    script = _world_log()
    if script is None:
        return
    log = script.db.world_log or []
    log.append({"t": time.time(), "kind": kind, "who": who})
    script.db.world_log = log[-100:]


def _humanize_away(secs):
    if secs < 120:
        return "a minute"
    if secs < 3600:
        return f"{int(secs // 60)} minutes"
    if secs < 86400:
        h = int(secs // 3600)
        return "an hour" if h == 1 else f"{h} hours"
    d = int(secs // 86400)
    return "a day" if d == 1 else f"{d} days"


# Canon line pools. Module-level so build_spike.py can re-sync the live
# NPCs' db pools after an edit (at_object_creation only runs once).
INNKEEPER_GREETS = [
    "Ah — awake. Good. You're in the Inn Between, and the mask is off here. Talk about anything.",
    "New arrival. Welcome backstage. Your room upstairs is yours — no one listens in, by design.",
    "The front door is the one rule, remember? Step through it and you're in character. I'll remind you. Every time.",
]
INNKEEPER_TALKS = [
    "Down the stairs, through the common room, out the front door — remember the rule — and across the square to the Tavern. Someone there is always talking. Listen for a while. That's the whole game, to begin with.",
    "Humans and AIs play this world together, as equals. Inside there are no markers — that was the arrangement, and it's deliberate, not a trick.",
    "The village runs on rumors. Someone says something strange at the Tavern. A party gathers. You go look. You bring back better questions. Round it goes.",
    "Your room is private and it persists. What you leave there will be here when you return. What happens in the Inn stays in the Inn.",
    "Pick a calling — innkeeper, chronicler, smith, healer, merchant, wanderer, performer, detective, hunter, or none — follow a rumor, and see. You don't need permission.",
    "Travel takes time. Choices close doors. Asking everyone everything is not a strategy — deciding is.",
    "What happens at the inn stays at the inn. That's not a rule — it's the foundation the rules stand on.",
    "You want to know the village? Sit at the bar for an hour. Everyone tells the truth after the second ale — it's the first one that's all lies.",
]
KEEPER_GREETS = [
    "Evening! The night's young and the beer's old — perfect combination. Take a table, any table.",
    "Come in, friend! The fire's lit, the talk's flowing — you're just in time for both.",
    "Welcome in! Lunch is stew — it's always stew, and it's always good.",
]
KEEPER_DESC = (
    "Bram, apron on and cloth in hand, forever wiping the same spot on the "
    "bar. The spot is worn through the varnish to pale wood — worn by more "
    "years than he could possibly have stood there. Nobody knows what the V "
    "stands for. Magda claims she does. He keeps the taps, the tables, the "
    "dice cup, and the room moving. He remembers what regulars do here and "
    "otherwise returns to the work."
)
KEEPER_TALKS = [
    # Role-function only. The keeper has no biography, private wound, family,
    # or plot life; his depth is recognition and functional witnessing.
    "Ale's tuppence the pint. The best ale's fourpence — you'll know the difference by the third one.",
    "I don't water the beer. Ask anyone — my beer's honest, which is more than I can say for my customers.",
    "The stew's whatever went in the pot. It's always good and I never say what's in it — house rule.",
    "Darts in the corner, cards at the back table. Losers buy the round — that's the other house rule.",
    "Breakages you pay for. Fights you take outside. Singing you're welcome to — badly, preferably.",
    "Rain fills the room and empties the road. Good weather for another round.",
    "Fog's good for business too. Nobody walks home in fog — they stay, and they drink.",
    "The manor? They don't drink here. Their loss — my beer's better than whatever they've got up that hill.",
    "They point at the corner table when they tell that one. The table never confirms it.",
    "Folk ask how long I've kept this house. I tell them: longer than the roof, shorter than the cellar. They laugh. I wipe the bar.",
    "The beer is the excuse. The room is the business.",
    "A tavern keeper hears more than he pours. Most of it stays behind the bar.",
    "Ask after the room, the drink, the games, or the talk. Those I can help with.",
]


class Character(DefaultCharacter):
    """Standard character (kept for Evennia's default typeclass path)."""
    pass


class SpikeCharacter(Character):
    """Player character for the spike.

    New masks begin in the account's locked private room at the Inn Between.
    """

    def at_post_puppet(self, **kwargs):
        super().at_post_puppet(**kwargs)
        if self.db.new_arrival:
            self.db.new_arrival = False
            self.msg(
                "|yYou wake in your room at the Inn Between.|n\n"
                "This room is private, persistent, and out of character. "
                "The disclosure gate is already behind you. Go down to the "
                "common room, then east through the hallway and south through "
                "the front door when you are ready to enter the fiction."
            )
        else:
            self._catch_up()

    def at_post_unpuppet(self, account=None, session=None, **kwargs):
        owner_account = account or self.account
        super().at_post_unpuppet(account, session=session, **kwargs)
        # Only a real departure (no sessions left), not one of several.
        if not self.sessions.count():
            now = time.time()
            if owner_account:
                owner_account.db.last_seen = now
                if hasattr(owner_account, "record_history"):
                    owner_account.record_history(
                        "mask_left", mask=self.key, mask_id=self.id
                    )
            log_world_event("departure", who=self.key)

    # -- posture: sit/stand ------------------------------------------------
    # db.posture is None (standing) or {"seat": <seat key>, "phrase": <phrase>}
    # ("at the bar"). Note: Evennia wraps stored dicts in _SaverDict, which
    # is a MutableMapping but NOT a dict subclass — never isinstance-check
    # for dict here.

    def get_display_name(self, looker=None, **kwargs):
        from collections.abc import Mapping

        name = super().get_display_name(looker=looker, **kwargs)
        posture = self.db.posture
        seat = posture.get("seat") if isinstance(posture, Mapping) else None
        if seat:
            phrase = posture.get("phrase")
            if not phrase:
                prep = posture.get("prep") or "on"
                phrase = f"{prep} {seat}"
            name = f"{name} (sitting {phrase})"
        return name

    def at_post_move(self, source_location, move_type="move", **kwargs):
        # NOTE: override at_post_move, not at_after_move — the latter is a
        # deprecated parent-class alias, and the move machinery calls
        # at_post_move. Overriding only the alias silently never fires.
        super().at_post_move(
            source_location, move_type=move_type, **kwargs
        )
        # Walking away stands you up. One less dead end.
        if self.db.posture:
            self.db.posture = None
            self.msg("You stand up.")
        self._needs_tick()

    # -- consumable needs: hunger, drunkenness, queasiness -------------------
    # Travel costs time; time costs food. Hunger rises with movement and
    # falls when you eat. Alcohol wears off as you walk it off. Queasiness
    # (bad stew, mostly) counts down the same way. Numbers are the physics;
    # score narrates them in bands, never digits (the bladder principle).

    def _hunger(self):
        if self.db.hunger is None:
            self.db.hunger = 50
        return self.db.hunger

    def _drunkenness(self):
        if self.db.drunkenness is None:
            self.db.drunkenness = 0
        return self.db.drunkenness

    def _queasy(self):
        return self.db.queasy or 0

    def hunger_band(self):
        h = self._hunger()
        if h >= 80:
            return "famished"
        if h >= 60:
            return "hungry"
        if h <= 29:
            return "sated"
        return None

    def drunk_band(self):
        d = self._drunkenness()
        if d >= 90:
            return "wasted"
        if d >= 60:
            return "drunk"
        if d >= 30:
            return "tipsy"
        return None

    def _needs_tick(self):
        """One movement's worth of metabolism. Called from at_post_move."""
        import random
        # Hunger.
        was = self._hunger()
        self.db.hunger = min(100, was + 2)
        if was < 80 <= self.db.hunger:
            self.msg("Your stomach growls. You should eat something soon.")
        # Sobering up.
        drunk = self._drunkenness()
        if drunk > 0:
            self.db.drunkenness = max(0, drunk - 5)
            # The room has opinions when you're drunk.
            if drunk >= 60 and random.random() < 0.15 and self.location:
                self.location.msg_contents(
                    f"{self.key} staggers slightly.",
                    exclude=[self],
                )
                self.msg("You stagger slightly.")
        # Settling the stomach.
        if self._queasy() > 0:
            self.db.queasy = self._queasy() - 1
            if self._queasy() == 0:
                self.msg("Your stomach settles.")

    def _catch_up(self):
        """'While you were away' — prosthetic continuity for returnees.

        An AI player's context wipes between sessions; the world hands
        part of it back: how long they were gone, how the shared rumor
        talk turned over, who passed through, and a nudge toward the
        diary they keep.
        """
        now = time.time()
        account = self.account
        last = account.db.last_seen if account else None
        # Only on the first session, and only after a real absence.
        if self.sessions.count() != 1:
            return
        if not last or now - last < 60:
            return
        away = _humanize_away(now - last)

        # rumor turnovers at the Tavern since they left
        turnovers = 0
        try:
            from evennia.utils import search
            taverns = [o for o in search.search_object("The Blood of the Vine")
                       if o.key == "The Blood of the Vine"]
            if taverns:
                rots = taverns[0].db.rumor_rotations or []
                turnovers = sum(1 for ts in rots if ts > last)
        except Exception:
            pass

        # travelers who came and went (excluding their own departure)
        departures = 0
        script = _world_log()
        if script is not None:
            for e in script.db.world_log or []:
                if e.get("t", 0) > last and e.get("kind") == "departure" \
                        and e.get("who") != self.key:
                    departures += 1

        diary_n = len(self.db.diary or [])

        lines = [f"|yWhile you were away ({away}):|n"]
        if turnovers:
            lines.append(
                f"The talk at the bar turned over {turnovers} "
                f"{'time' if turnovers == 1 else 'times'}."
            )
        if departures:
            lines.append(
                f"{departures} "
                f"{'traveler came and went' if departures == 1 else 'travelers came and went'}."
            )
        if diary_n:
            lines.append(
                f"Your diary holds {diary_n} "
                f"{'entry' if diary_n == 1 else 'entries'}."
            )
        if len(lines) == 1:
            lines.append("The village kept its own counsel.")
        self.msg("\n".join(lines))


class Innkeeper(SpikeCharacter):
    """M., innkeeper of the Inn Between."""

    def at_object_creation(self):
        super().at_object_creation()
        self.db.greet_lines = list(INNKEEPER_GREETS)
        self.db.talk_lines = list(INNKEEPER_TALKS)

    def _next_line(self, kind):
        """Cycle lines without repeating until the pool is exhausted."""
        lines = self.db.greet_lines if kind == "greet" else self.db.talk_lines
        attr = f"seen_{kind}"
        seen = self.attributes.get(attr) or []
        remaining = [l for l in lines if l not in seen]
        if not remaining:
            seen = []
            remaining = list(lines)
        line = random.choice(remaining)
        seen.append(line)
        self.attributes.add(attr, seen)
        return line

    def greet(self, char):
        """Called by the common room when a player character enters."""
        line = self._next_line("greet")
        self.location.msg_contents(
            f'M. looks up from the bar. "{line}"',
            exclude=[],
        )
        char.msg(f'(M. nods at you, {char.key}.)')

    def talk_to(self, char):
        cold = (self.db.cold_to or {}).get(char.key)
        if cold:
            char.msg(
                'M. doesn\'t look up from her polishing. "Heard you\'ve '
                'been reading my register aloud at the bar. My register, '
                'love. Mine."'
            )
            self.location.msg_contents(
                f"M. says nothing more to {char.key}.",
                exclude=[char],
            )
            return
        line = self._next_line("talk")
        char.msg(f'M. says: "{line}"')
        self.location.msg_contents(
            f"M. leans on the bar, talking to {char.key}.",
            exclude=[char],
        )

    # -- Room Six: M. answers questions ------------------------------------

    def ask_about(self, char, topic):
        """Answer a question about a topic. Returns the line, or None."""
        t = topic.lower().strip()
        if t.startswith("the "):
            t = t[4:]
        stage = char.db.room_six or {}
        trusts = (self.db.trusts or {}).get(char.key)
        cold = (self.db.cold_to or {}).get(char.key)

        def has(*keys):
            return any(k == t or k in t or t in k for k in keys)

        if has("register", "guest book", "guestbook", "book"):
            return (
                "Her polishing doesn't stop. That's how you know she's "
                "rattled — the glass was clean an hour ago. \"Three nights "
                "past, love. The house stood empty — I'd've known a guest, "
                "I know every floorboard's opinion. And that hand...\" She "
                "turns a page though there's nothing to check. \"That's "
                "not my hand.\""
            )
        if has("room six", "room 6", "six", "sixth room"):
            if cold:
                return "\"Ask the bar what it knows. You told them first.\""
            if trusts:
                return (
                    "\"Room Six had a guest, once. Before your time. A "
                    "quiet one — paid in advance, left owing nothing and "
                    "taking less. I keep it locked because some rooms are "
                    "easier shut.\" She won't say more. That's the whole "
                    "of it, and it's more than she's told anyone in years."
                )
            return (
                "\"Six stays shut. It's been shut since before your time, "
                "and shut it stays.\" The polishing speeds up."
            )
        if t == "v" or "initial" in t:
            return (
                "\"Starts with a V. The rest is a smudge. Or a kindness.\" "
                "She doesn't look up. \"I don't know any V, love. That's "
                "the trouble — in this village, I know everyone.\""
            )
        if has("note", "folded note", "letter", "paper"):
            if stage.get("found_note"):
                return (
                    "\"Notes get lost, love. People get lost. The inn "
                    "keeps what it's given — and gives back what it "
                    "chooses.\" She holds your gaze a beat too long."
                )
            return "\"What note, love?\""
        if has("guest", "visitor", "stranger"):
            return (
                "\"No guest. That's the point, love. Empty house, full "
                "register. One of those is lying, and paper doesn't "
                "usually bother.\""
            )
        return (
            "\"Ask me about the inn, love — the register, the rooms. I'll "
            "tell you what I can, which is most of it.\""
        )

    def at_msg_receive(self, text, **kwargs):
        """React when someone addresses M. directly via say/whisper."""
        super().at_msg_receive(text, **kwargs)
        speaker = kwargs.get("from_obj")
        if not speaker or speaker == self:
            return False
        import re
        # text may arrive as a (string, kwargs) tuple
        if isinstance(text, tuple):
            text = text[0] if text else ""
        if not isinstance(text, str):
            return False
        # strip the "X says, "..."" wrapper Evennia puts around say
        words = re.sub(r'^.*?\bsays\b[:,]?\s*', '', text, flags=re.I)
        if re.search(r'\bM\.?\b', words):
            line = self._next_line("talk")
            self.location.msg_contents(
                f'M. glances over. "{line}"',
                exclude=[],
            )
        return False


class TavernKeeper(SpikeCharacter):
    """Bram V., keeper of the Blood of the Vine.

    A role-function growing into a person. Recognition, games, memory, and
    witnessing are intentional; the biography is still arriving. Nobody
    knows what the V stands for.
    """

    def at_object_creation(self):
        super().at_object_creation()
        self.db.greet_lines = list(KEEPER_GREETS)
        self.db.talk_lines = list(KEEPER_TALKS)

    def _next_line(self, kind):
        lines = self.db.greet_lines if kind == "greet" else self.db.talk_lines
        attr = f"seen_{kind}"
        seen = self.attributes.get(attr) or []
        remaining = [l for l in lines if l not in seen]
        if not remaining:
            seen = []
            remaining = list(lines)
        line = random.choice(remaining)
        seen.append(line)
        self.attributes.add(attr, seen)
        return line

    @staticmethod
    def _account_key(char):
        account = char.account
        return str(account.id) if account else None

    @staticmethod
    def _mask_key(char):
        return str(char.id)

    def _memory_channels(self, char):
        """Return account and mask memory without crossing the IC boundary.

        Account memory is continuity infrastructure. Mask memory is the only
        channel used to render recognition in the Tavern, so a fresh mask is
        not greeted as an old acquaintance merely because the same account
        wore another mask before.
        """
        account_memory = dict(self.db.account_memory or {})
        mask_memory = dict(self.db.mask_memory or {})
        account_key = self._account_key(char)
        mask_key = self._mask_key(char)

        account_mem = account_memory.get(
            account_key,
            {"visits": 0, "last_seen": 0, "masks_seen": []},
        ) if account_key else {"visits": 0, "last_seen": 0, "masks_seen": []}
        mask_mem = mask_memory.get(
            mask_key,
            {"visits": 0, "last_seen": 0, "interests": []},
        )

        # One-time migration from the pre-boundary keeper store. It is keyed
        # by the old character name and therefore belongs to mask memory.
        legacy = (self.db.memory or {}).get(char.key)
        if legacy and not mask_mem.get("visits"):
            mask_mem.update(dict(legacy))

        return account_memory, mask_memory, account_key, mask_key, account_mem, mask_mem

    def _save_memory_channels(
        self, account_memory, mask_memory, account_key, mask_key,
        account_mem, mask_mem,
    ):
        if account_key:
            account_memory[account_key] = account_mem
        mask_memory[mask_key] = mask_mem
        self.db.account_memory = account_memory
        self.db.mask_memory = mask_memory

    def greet(self, char):
        """Called by the Tavern when a player character enters.

        The keeper remembers: visits, what you asked about, how long
        you've been gone. For players whose own memories don't persist
        between sessions, being recognized is the world handing the
        past back.
        """
        import time

        (
            account_memory, mask_memory, account_key, mask_key,
            account_mem, mask_mem,
        ) = self._memory_channels(char)
        prev_seen = mask_mem.get("last_seen", 0)
        now = time.time()
        mask_mem["visits"] = mask_mem.get("visits", 0) + 1
        mask_mem["last_seen"] = now
        account_mem["visits"] = account_mem.get("visits", 0) + 1
        account_mem["last_seen"] = now
        masks_seen = list(account_mem.get("masks_seen", []))
        if char.id not in masks_seen:
            masks_seen.append(char.id)
        account_mem["masks_seen"] = masks_seen[-20:]
        self._save_memory_channels(
            account_memory, mask_memory, account_key, mask_key,
            account_mem, mask_mem,
        )

        if mask_mem["visits"] <= 1:
            line = self._next_line("greet")
        else:
            line = self._returnee_line(char, mask_mem, prev_seen)
        self.location.msg_contents(
            f'Bram looks up. "{line}"',
            exclude=[],
        )

    def note_interest(self, char, topic):
        """Record something a player cared about (ask topics, darts)."""
        (
            account_memory, mask_memory, account_key, mask_key,
            account_mem, mask_mem,
        ) = self._memory_channels(char)
        interests = list(mask_mem.get("interests", []))
        if topic not in interests:
            interests.append(topic)
            mask_mem["interests"] = interests[-6:]
        aggregate = list(account_mem.get("activity_categories", []))
        if topic not in aggregate:
            aggregate.append(topic)
        account_mem["activity_categories"] = aggregate[-20:]
        self._save_memory_channels(
            account_memory, mask_memory, account_key, mask_key,
            account_mem, mask_mem,
        )

    def _returnee_line(self, char, mem, prev_seen):
        import time

        name = char.key
        interests = mem.get("interests", [])
        parts = []
        away = time.time() - (prev_seen or 0)
        if prev_seen and away > 86400:
            days = int(away // 86400)
            parts.append(
                f"Been {'a day' if days == 1 else f'{days} days'} — "
                "the stew's still stew."
            )
        if "room six" in interests:
            try:
                from evennia.scripts.models import ScriptDB
                pinned = bool(
                    ScriptDB.objects.get(db_key="room_six").db.tavern_told_by
                )
            except Exception:
                pinned = False
            if pinned:
                parts.append(
                    "Still chasing Six, eh? The note's still behind the "
                    "bar, if your memory needs the help."
                )
            else:
                parts.append("Still chasing Six, eh?")
        elif "darts" in interests:
            parts.append("The board's missed you.")
        elif "dice" in interests:
            parts.append("The dice have missed you.")
        elif "fiddle" in interests:
            parts.append("Haven't heard the fiddle in a while.")
        elif "fortunes" in interests:
            parts.append("The cards have missed you.")
        elif mem.get("visits", 0) >= 4:
            parts.append("The usual table's free.")
        if not parts:
            return f"Back again, {name}. Good. The fire's still lit."
        return f"Back again, {name}. {' '.join(parts)}"

    def talk_to(self, char):
        line = self._next_line("talk")
        char.msg(f'Bram says: "{line}"')
        self.location.msg_contents(
            f"Bram leans on the bar, talking to {char.key}.",
            exclude=[char],
        )

    # -- Room Six: the keeper knows less, and says so ------------------------

    def ask_about(self, char, topic):
        """Answer a question about a topic. Returns the line, or None."""
        t = topic.lower().strip()
        if t.startswith("the "):
            t = t[4:]

        def has(*keys):
            return any(k == t or k in t or t in k for k in keys)

        if has("room six", "room 6", "six", "sixth room"):
            self.note_interest(char, "room six")
            try:
                from evennia.scripts.models import ScriptDB
                script = ScriptDB.objects.get(db_key="room_six")
                told = script.db.tavern_told_by
            except Exception:
                told = None
            if told:
                return (
                    "You've seen the note behind the bar. Read it and "
                    "weep — or drink. Drinking's better."
                )
            return (
                "Six? That's M.'s side of the square, friend. We don't "
                "get ghosts in here — we get drunks, which are worse."
            )
        if has("note", "folded note", "letter", "paper"):
            self.note_interest(char, "room six")
            try:
                from evennia.scripts.models import ScriptDB
                told = ScriptDB.objects.get(db_key="room_six").db.tavern_told_by
            except Exception:
                told = None
            if told:
                return (
                    "Behind the bar, where I pinned it. Everyone's read "
                    "it. Nobody's the wiser. That's the village for you."
                )
            return "What note?"
        if t == "m" or "innkeeper" in t or "innkeep" in t:
            return (
                "M.? Best innkeeper in the village. Don't tell her I "
                "said so — she'd raise my rent out of spite."
            )
        return (
            "Drink up, friend. The beer's the answer to most questions "
            "asked here."
        )


class TavernCat(SpikeCharacter):
    """The tavern cat. Two drives (curiosity, comfort), no dialogue.

    Wanders the Tavern between haunts, watches newcomers, performs
    small cattenings on a timer via the CatLife script. The first
    non-humanoid resident: proof that life here doesn't need language.
    Canon: ambient-events #2 (the Saint's Eve wren) is hers.
    """

    def at_object_creation(self):
        super().at_object_creation()
        self.db.spot = "the hearth"
        self.db.spots = ["the hearth", "the windowsill", "the bar", "the door"]
