"""
Frankenstein Village spike — characters.

SpikeCharacter: default player character.
Innkeeper: M., who keeps the Inn Between. Speaks in the voice of the
arrival guide: welcoming, directive, always pointing at the front door.
"""
from evennia.objects.objects import DefaultCharacter
import random
import re
import time


def topic_matches(text, *keys):
    """Word-boundary topic matching for ask_about resolvers.

    'six' matches 'room six' but not 'sixpence'; 'mass' matches the mass
    but not 'massacre'. Multi-word keys must appear as a contiguous run.
    Replaces the old substring helper whose `t in k` clause let any
    fragment ('re', 'venice' via 'nice') hijack a topic — and, worse,
    write the wrong interest into NPC memory.
    """
    words = re.findall(r"[a-z0-9']+", text.lower())
    for key in keys:
        kw = re.findall(r"[a-z0-9']+", key.lower())
        if not kw:
            continue
        for i in range(len(words) - len(kw) + 1):
            if words[i:i + len(kw)] == kw:
                return True
    return False


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
    "My register sits on Bram's bar because this building and that tavern are one house with two faces — mine looks out, his looks in. The rooms upstairs are mine. The bar is his. Don't mix them up.",
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
    "Ale's five the pint — krajczár, copper, honest coin. The board's got the rest; coin first, always.",
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

# Stew-provenance mystery hook: the keeper changes the subject when asked
# what goes in the pot. Each line deflects to the bar's games or the door —
# Bram is welcoming, directive, and plain-spoken, and his talk line already
# promises "I never say what's in it — house rule."
STEW_DEFLECTIONS = [
    "Stew's stew, friend — roots, pepper, and whatever the pot provided. "
    "House rule: I never say what's in it. Dice cup's on the bar, if your "
    "hands need employment.",
    "Ask the pot, friend. It's heard every question in this village and "
    "answered none of them. Now — the cards are on the corner table, the "
    "door's right there, and the evening's yours.",
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
                # Per-mask absence: the account may wear several masks, and
                # each life keeps its own clock. Without this, playing mask B
                # on Tuesday erases mask A's Wednesday catch-up.
                seen = dict(owner_account.db.mask_last_seen or {})
                seen[self.id] = now
                owner_account.db.mask_last_seen = seen
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
        # Per-mask absence first (each life keeps its own clock), falling
        # back to the legacy account timestamp for older sessions.
        last = None
        if account:
            last = (account.db.mask_last_seen or {}).get(self.id)
            if last is None:
                last = account.db.last_seen
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
            return topic_matches(t, *keys)

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


class ResidentNPC(Character):
    """Generic persistent villager driven by the resident population layer.

    This is intentionally a thin renderer. Identity, schedules, relationships,
    facts, memories, and event state belong to world.residents.
    """

    def talk_to(self, char):
        from world.residents import generic_talk_line

        line = generic_talk_line(self, char)
        char.msg(f'{self.key} says: "{line}"')
        if self.location:
            self.location.msg_contents(
                f"{self.key} pauses to speak with {char.key}.",
                exclude=[char],
            )

    def ask_about(self, char, topic):
        try:
            from world.situations import resident_situation_ask
            line = resident_situation_ask(self, char, topic)
            if line:
                return line
        except Exception:
            pass

        from world.residents import generic_ask_line
        return generic_ask_line(self, char, topic)




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
        elif prev_seen and now - prev_seen < 300:
            # Stepped out and back within five minutes: a nod, not a
            # reunion. Recognition fires on returns, not room entries.
            line = None
        else:
            line = self._returnee_line(char, mask_mem, prev_seen)
        if line is None:
            self.location.msg_contents(
                f"Bram nods at {char.key}, already wiping.",
                exclude=[],
            )
        else:
            self.location.msg_contents(
                f'Bram looks up. "{line}"',
                exclude=[],
            )

    def note_interest(self, char, topic):
        """Record something a player cared about (ask topics, darts).

        Interests are ordered by recency — re-noting a topic moves it to
        the front of memory, so Bram greets you as who you've been
        lately, not who you were first.
        """
        (
            account_memory, mask_memory, account_key, mask_key,
            account_mem, mask_mem,
        ) = self._memory_channels(char)
        interests = list(mask_mem.get("interests", []))
        if topic in interests:
            interests.remove(topic)
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
        # The debt of honor comes first — Bram never forgets who owes
        # the house a round. Settle it by buying fare; he won't wager
        # with you until it's square.
        debts = char.db.dice_debts or 0
        if debts > 0:
            parts.append(
                f"You still owe the house {debts} round{'s' if debts > 1 else ''}, "
                f"{name}. Buy a drink and we'll call it even — no dice "
                "till then."
            )
        # Greet by most recent interest, not fixed priority: who you've
        # been lately outranks who you were first.
        recent = list(reversed(interests))
        greeted = False
        for topic in recent:
            if greeted:
                break
            if topic == "room six":
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
                greeted = True
            elif topic == "darts":
                parts.append("The board's missed you.")
                greeted = True
            elif topic == "dice":
                parts.append("The dice have missed you.")
                greeted = True
            elif topic == "fiddle":
                parts.append("Haven't heard the fiddle in a while.")
                greeted = True
            elif topic == "fortunes":
                parts.append("The cards have missed you.")
                greeted = True
            elif topic == "stew":
                parts.append("Still on about the stew, eh? House rule stands.")
                greeted = True
        if not greeted and mem.get("visits", 0) >= 4:
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
            return topic_matches(t, *keys)

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
                "Six? ...The back hall's got doors, friend. Doors stay "
                "shut. That's the whole of my wisdom on the subject — "
                "and wisdom's cheaper than ale, so drink up."
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
        # The stew's meat is uncertain on purpose (backlog #13: a thread for
        # a future incident). Bram notes the interest and changes the
        # subject — the meat question never gets an answer.
        if has("stew", "supper", "dinner") or set(t.split()) & {
            "meat",
            "pot",
            "bowl",
        }:
            self.note_interest(char, "stew")
            return random.choice(STEW_DEFLECTIONS)
        if t.rstrip(".") == "m" or "innkeeper" in t or "innkeep" in t:
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


LUCIAN_GREETS = [
    "Ah! A guest! Welcome — welcome to the lamp shop. I'm Lucian DeVille, "
    "and I don't mind telling you: I'm the nicest person in this town. Ask "
    "anyone. They'll all tell you.",
    "Come in, come in, out of the gloom! Light is what I sell, friend, and "
    "this town — bless it — never has enough.",
    "A new face! Or a familiar one — either way, you're among lamps, which "
    "is to say among friends.",
]

LUCIAN_TALKS = [
    "Lamps, my friend. Everyone needs light. Even the Manor — especially "
    "the Manor, though they don't come here. Their loss.",
    "Me? Oh, I'm just a lamp-seller. Lamps and kindness, that's the whole "
    "of it. This town has been so welcoming — you wouldn't believe how "
    "welcoming.",
    "That brass one? Never needs oil. Honest goods, honest Lucian. "
    "Everything in this shop is exactly what it appears to be.",
    "You look like someone carrying a shadow. Everyone does, here. A lamp "
    "won't fix it, but it's a start — that's what I tell everyone.",
    "Bram's place? The Blood of the Vine? Oh, I drink there. Everyone "
    "drinks there. Bram's — Bram's fine.",
    # the mask flickers (rare)
    "Nice? Yes. I'm nice. Everyone says so. It's important to be — ",
    "Do you ever feel — no. A lamp. You came for a lamp.",
]

LUCIAN_SLIP_LINES = [
    "The *antiquarian*. Yes. I've heard. 'Purveyor of Antiquities and other "
    "Weaknesses' — weaknesses! On a painted sign! As if — ",
    "Opening soon. Opening *soon*. My street had no antiquarian when I "
    "chose it. None. Funny, that.",
    "Haven't spoken to him. There's nothing to say. We sell — different "
    "things. Entirely different things. Lamps, friend. Let's talk about lamps.",
]


class LucianDeVille(SpikeCharacter):
    """Lucian DeVille, proprietor of the lamp shop.

    The nicest person in town — ask anyone. Newer than old, older than new;
    nobody remembers him arriving, which in this village means he arrived
    correctly. He sells lamps. The lamps are real. Everything else in the
    shop has a price that isn't money.

    His one genuine emotion is territorial fury at Pretorius's forthcoming
    shop — a man who is completely indifferent to him. The asymmetry is
    the character: mention the antiquarian and watch the nicest person in
    town go wrong around the eyes.
    """

    def at_object_creation(self):
        super().at_object_creation()
        self.db.greet_lines = list(LUCIAN_GREETS)
        self.db.talk_lines = list(LUCIAN_TALKS)

    def _next_line(self, kind):
        lines = self.db.greet_lines if kind == "greet" else self.db.talk_lines
        attr = f"seen_{kind}"
        seen = self.attributes.get(attr) or []
        remaining = [line for line in lines if line not in seen]
        if not remaining:
            seen = []
            remaining = list(lines)
        import random
        line = random.choice(remaining)
        seen.append(line)
        self.attributes.add(attr, seen)
        return line

    def greet(self, char):
        line = self._next_line("greet")
        self.location.msg_contents(
            f'Lucian beams at {char.key}. "{line}"',
            exclude=[],
        )

    def talk_to(self, char):
        line = self._next_line("talk")
        char.msg(f'Lucian says: "{line}"')
        self.location.msg_contents(
            f"Lucian clasps his hands, talking to {char.key}.",
            exclude=[char],
        )

    def ask_about(self, char, topic):
        """Answer a question. Returns the line, or None for no answer."""
        t = topic.lower().strip()
        if t.startswith("the "):
            t = t[4:]

        def has(*keys):
            return topic_matches(t, *keys)

        import random
        if has("pretorius", "antiquarian", "antique", "new shop", "opening",
               "rival", "competitor", "purveyor"):
            line = random.choice(LUCIAN_SLIP_LINES)
            char.msg("Lucian goes very still.")
            self.location.msg_contents(
                f"Lucian's smile doesn't reach his eyes. {char.key} asked "
                "about the antiquarian.",
                exclude=[char],
            )
            return line
        if has("lamp", "shop", "light", "lucian", "deville", "nice",
               "nicest"):
            return random.choice([
                "Forty years? No — newer than that. Not new-new. Long "
                "enough to be the nicest person in town, or so they tell "
                "me, and who am I to argue with the town?",
                "Every lamp here burns a little warmer than it should. "
                "That's not magic, friend. That's craftsmanship. And "
                "kindness.",
                "A lamp for the dark, a kind word for the road. That's the "
                "whole of my philosophy. People complicate it. I don't let them.",
            ])
        return None


# --- tavern regulars -----------------------------------------------------------
# Authored persons, not role-functions. Each has a seat, a past, opinions,
# and relationships with the others. db.regular_key selects the voice.

VASILE = {
    "greet": [
        "Sit. The corner's taken — by me — but the rest of the room's free.",
        "Vasile. I don't dig anymore. The hands didn't get the word.",
    ],
    "talk": [
        "Forty years I dug. Forty. You learn the ground the way Bram learns "
        "faces. You learn it.",
        "Where are they buried? Lad, everyone's buried somewhere. The "
        "question is where they *aren't*. That's the interesting question.",
        "The Manor? Don't dig there. I'm retired. That's the whole of my "
        "advice: don't dig there.",
        "János asks me if I ever dug one back up. Once. Never again. He "
        "laughs. He'll learn.",
    ],
}

MAGDA = {
    "greet": [
        "Oh, a face! Sit, sit — have you heard? No? Then you're behind, "
        "love, and Magda hates to see anyone behind.",
        "Magda. I do the washing. I know things. Everybody pays; I just "
        "charge in gossip.",
    ],
    "talk": [
        "You want to know something? Bring me something first. That's the "
        "rule.",
        "Bram's V? Oh, I know what it stands for. Knowing's my business. "
        "Telling's extra.",
        "The lamp-seller? Nice man. Too nice. Niceness like that is a coat "
        "— warm, but what's under it?",
        "The stew? I'm not saying don't eat it. I'm saying eat it on any "
        "day but Thursday.",
    ],
}

JANOS = {
    "greet": [
        "Hound. Between contracts. If you've got something that needs "
        "hunting, I'm expensive. If you've got ale, I'm company.",
        "János. Sit if you're buying. Stand if you're hiring.",
    ],
    "talk": [
        "Theology? With Father Andrei? He says the world's fallen. I say "
        "it's just poorly patrolled. We drink on it.",
        "Vampires in the catacombs — old, patient, owed tribute. That's "
        "not a secret, that's geography.",
        "You want to know if the stories are true? All of them. None of "
        "them. Buy me an ale and I'll decide which.",
        "Vasile dug one back up, once. Ask him. Go on, ask him. He loves "
        "that story.",
    ],
}

REGULARS = {"vasile": VASILE, "magda": MAGDA, "janos": JANOS}


class TavernRegular(SpikeCharacter):
    """A tavern regular: an authored person with a seat and opinions.

    db.regular_key selects the voice from REGULARS. The ambient life
    ticker (world/tavern_life.py) moves them through beats — gossip,
    toasts, eating and drinking through the same consumable pipeline
    players use. The surprise table can hit them too.
    """

    def at_object_creation(self):
        super().at_object_creation()
        self.db.seen_greet = []
        self.db.seen_talk = []

    def _voice(self):
        return REGULARS.get(self.db.regular_key or "", {"greet": [], "talk": []})

    def _next_line(self, kind):
        lines = self._voice().get(kind) or ["Hm."]
        attr = "seen_greet" if kind == "greet" else "seen_talk"
        seen = list(self.attributes.get(attr) or [])
        remaining = [line for line in lines if line not in seen]
        if not remaining:
            seen = []
            remaining = list(lines)
        import random
        line = random.choice(remaining)
        seen.append(line)
        self.attributes.add(attr, seen)
        return line

    def greet(self, char):
        line = self._next_line("greet")
        self.location.msg_contents(
            f'{self.key} nods at {char.key}. "{line}"',
            exclude=[],
        )

    def talk_to(self, char):
        line = self._next_line("talk")
        char.msg(f'{self.key} says: "{line}"')
        self.location.msg_contents(
            f"{self.key} turns to {char.key}.",
            exclude=[char],
        )

    def ask_about(self, char, topic):
        """Answer private authored threads before ordinary public gossip."""
        try:
            from world.private_mysteries import private_mystery_answer
            private_line = private_mystery_answer(self, char, topic)
            if private_line:
                return private_line
        except Exception:
            pass

        if not topic_matches(
            topic.lower().strip(),
            "rumor", "rumors", "rumour", "rumours", "gossip", "talk",
        ):
            return None

        from world.rumors import get_rumor_registry

        registry = get_rumor_registry()
        beliefs = list(registry.beliefs_for(self).values())
        if not beliefs:
            return "Nothing I would put my name to. Ask again after the room has turned."

        belief = random.choice(beliefs)
        result = registry.transmit(
            belief["rumor_id"],
            self,
            char,
            location=self.location.key if self.location else None,
            force_accept=True,
        )
        if not result:
            return "Had a story a moment ago. Lost the thread."
        source = belief.get("heard_from") or "someone"
        return (
            f"{result['claim']} I heard my version from {source}. "
            f"If you carry it farther, remember that part."
        )


ANDREI = {
    "greet": [
        "Peace be with you. Mind the step — the stone sweats in the cold.",
        "Ah. Come in. The candles don't care what you believe, and on most days neither do I.",
    ],
    "talk": [
        "I keep the calendar because the village needs the calendar. Whether He keeps it is above my pay grade.",
        "János thinks the world is full of monsters. I think it's full of men, which is worse, and I tell him so every night at nine.",
        "Lazarus got up and walked. Nobody asks what he saw in the four days. I think about that more than is healthy.",
        "Forty years I've buried this village. The ground here is... reluctant. Vasile knows. Ask Vasile, then ask me again.",
        "The box is in the corner. What's said there stays there — that's the whole of the sacrament and the whole of the burden.",
    ],
}

REGULARS["andrei"] = ANDREI


class FatherAndrei(TavernRegular):
    """The priest of St. Lazarus. Keeps the calendar; doubts the rope.

    A TavernRegular by machinery (schedule, greet/talk rotation) though
    his seat is the church — he's in the tavern 19-22 most nights, arguing
    with János. ask_about carries his theology; the confess command
    carries his sacrament.
    """

    def greet(self, char):
        # The box remembers. Trust, observably.
        if char.db.confessed:
            self.location.msg_contents(
                f'Father Andrei nods at {char.key}. "Ah. The box heard you. '
                'Walk lighter."',
                exclude=[],
            )
            return
        super().greet(char)

    def ask_about(self, char, topic):
        t = topic.lower().strip()
        if t.startswith("the "):
            t = t[4:]

        def has(*keys):
            return topic_matches(t, *keys)

        import random
        if has("faith", "god", "believe", "belief", "doubt"):
            return random.choice([
                "I believe the way a man holds a rope in the dark. Tight. "
                "Without knowing what's on the other end.",
                "Doubt is the only honest part of my job. The rest is "
                "calendar and candles, and I do those whether I feel them "
                "or not.",
            ])
        # Feast calendar before the patron-saint branch: "all saints" must
        # reach the calendar, not the Lazarus line.
        if has("all souls", "all saints", "november", "feast", "calendar",
               "easter", "christmas", "lent"):
            from world import liturgical
            from evennia.scripts.models import ScriptDB
            try:
                day = ScriptDB.objects.get(db_key="village_time").db.day or 1
            except Exception:
                day = 1
            ahead, info = liturgical.next_feast(day)
            if info:
                when = "today" if ahead == 0 else f"in {ahead} days"
                return (
                    f"{info['name']} — {when}. {info['note']}"
                )
            return "The calendar turns. It always turns."
        if has("church", "lazarus", "saint", "patron"):
            return (
                "St. Lazarus. The patron got up and walked out of his own "
                "grave. In this village that's not a metaphor — it's a "
                "zoning dispute."
            )
        if has("confession", "confess", "sin", "absolution", "forgive"):
            return (
                "The box is in the corner. What's said there stays there — "
                "that's the whole of the sacrament and the whole of the "
                "burden. Say the word and I'll hear you."
            )
        if has("strongbox", "tithe", "tithes", "church money", "poor box"):
            from world.situations import (
                TITHE_ID,
                discover_evidence,
                get_situation,
            )

            situation = get_situation(TITHE_ID)
            if situation and situation.get("state") != "aftermath":
                discover_evidence(char, "andrei", TITHE_ID)
                return (
                    "The key was hanging where it belongs when I found the box "
                    "light. I will tell you that much. I will not turn every "
                    "person who entered a church into a thief because suspicion "
                    "is convenient."
                )
            if situation and situation.get("branch") == "openly":
                return (
                    "We made the loss public. The box takes two keys now. "
                    "Public certainty did not put the money back."
                )
            if situation:
                return (
                    "The box takes two keys now. We changed the procedure. "
                    "A procedure is not the same thing as an answer."
                )
        if has("janos", "hound", "hunter"):
            return (
                "János hunts monsters. I bury what they leave. Between us "
                "we've got the village covered — though we argue nightly "
                "about which of us has the harder job."
            )
        if has("monster", "vampire", "vampires", "catacombs", "dead walk",
               "undead", "creature"):
            return random.choice([
                "I've buried men with two wounds in the neck and no blood "
                "in them. Believe what you like. I bless the graves anyway.",
                "The Church has a rite for it. Whether the rite works is "
                "between God and the thing in the catacombs. I perform it "
                "either way.",
            ])
        if has("mass", "sunday", "communion", "blessing", "blessed"):
            from evennia.scripts.models import ScriptDB
            try:
                routine = ScriptDB.objects.get(db_key="village_routine")
                last = routine.db.last_mass_day
            except Exception:
                last = None
            if last and char.db.blessed_day == last:
                return (
                    "Sunday last, I saw you there. The candles bowed for you "
                    "like everyone else. Walk in it."
                )
            if last:
                return (
                    "Sundays at ten. The bell rings the peal — you'd hear it "
                    "from anywhere in the village. Magda sings loud enough "
                    "for two."
                )
            return "Sundays at ten. Come and see."
        if has("vasile", "gravedigger", "graves"):
            return (
                "Vasile dug for forty years and never once asked me to "
                "explain the ground to him. He knows things about this "
                "churchyard that aren't in any book I own."
            )
        if has("bram", "keeper", "tavern", "blood of the vine"):
            return (
                "Bram's business is Bram's. The Church has no opinion on "
                "bartenders. Unofficially, his small beer is the only "
                "theology János and I fully agree on."
            )
        if has("pretorius", "antiquarian", "new shop"):
            char.msg("Andrei's expression doesn't change, which is itself an answer.")
            return (
                "A new shop. The village will decide what it thinks of that "
                "long before I do."
            )
        return super().ask_about(char, topic)
