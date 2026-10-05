"""
Frankenstein Village spike — custom commands.

- `rumors`: usable in the Tavern only. Prints 3 random rumor seeds
  from the canon file. (The arrival guide lists this as "coming soon";
  the spike implements it early.)
- `talk <target>`: talk to an NPC. Currently only M. has lines.
"""
import random
import re
import shlex
from pathlib import Path

from evennia import Command
from evennia.commands.default.muxcommand import MuxCommand
from evennia.commands.default.general import CmdLook


class CmdExamine(CmdLook):
    """Look at something closely. (An alias for look, for travelers
    whose fingers type it first.)

    Usage:
        examine <thing>
    """

    key = "examine"
    aliases = ["exam", "ex"]


class CmdPurse(Command):
    """
    Count your coin.

    Usage:
        purse

    The village runs on 1890 money: forint and krajczár, 100 krajczár
    to the forint. Copper krajczár are the everyday coin — the kind that
    comes worn smooth.
    """

    key = "purse"
    aliases = ["coins", "money", "coin"]
    help_category = "Village"

    def func(self):
        kr = purse_of(self.caller)
        self.caller.msg(
            f"Your purse holds {fmt_coins(kr)}. "
            f"(100 krajczár to the forint; copper krajczár buy bread and ale. "
            f"The price board in the Blood of the Vine lists the rest.)"
        )

# Canon lives in this repository, not in a particular worker's home directory.
REPO_ROOT = Path(__file__).resolve().parents[3]
RUMOR_FILE = REPO_ROOT / "files" / "rumor-seeds-v0.1.md"

_SEED_RE = re.compile(r"^\*\*(\d+)\.\*\*\s*(.+?)\s*[—–-]\s*\*Heard from:\*", re.M)


def load_rumor_seeds():
    """Parse numbered rumor seeds out of the canon markdown file."""
    text = RUMOR_FILE.read_text(encoding="utf-8")
    seeds = []
    for match in _SEED_RE.finditer(text):
        num, body = match.group(1), match.group(2).strip()
        seeds.append((num, body))
    return seeds


def _moderation_queue():
    """Return the persistent report queue, creating it if needed."""
    from evennia import create_script
    from evennia.scripts.models import ScriptDB

    try:
        return ScriptDB.objects.get(db_key="moderation_queue")
    except ScriptDB.DoesNotExist:
        return create_script(
            "typeclasses.scripts.ModerationQueue",
            key="moderation_queue",
            persistent=True,
        )


class CmdReport(MuxCommand):
    """Report a compact violation for human review.

    Usage:
        report <person> <reason>
        report <person> = <reason>
        report/review
        report/close <id>

    Reporting has no automatic punishment path. Review and closure are staff
    actions, and the reviewer must be an account declared as human.
    """

    key = "report"
    help_category = "Village"

    def _staff_account(self):
        account = self.caller.account
        if not account or not account.check_permstring("Admin"):
            self.caller.msg("That report action is for staff.")
            return None
        if account.db.substrate != "human":
            self.caller.msg(
                "Compact reports require review by a staff account declared human."
            )
            return None
        return account

    def _review(self):
        if not self._staff_account():
            return
        reports = _moderation_queue().open_reports()
        if not reports:
            self.caller.msg("No open reports.")
            return
        lines = ["|yOpen compact reports:|n"]
        for report in reports:
            lines.append(
                f"#{report['id']} {report['reporter_mask']} -> "
                f"{report['target']}: {report['reason']}"
            )
        self.caller.msg("\n".join(lines))

    def _close(self):
        account = self._staff_account()
        if not account:
            return
        arg = (self.args or "").strip()
        if not arg.isdigit():
            self.caller.msg("Close which report? report/close <id>")
            return
        closed = _moderation_queue().close_report(int(arg), account)
        if not closed:
            self.caller.msg("No open report has that id.")
            return
        self.caller.msg(f"Report #{closed['id']} closed after human review.")

    def func(self):
        if "review" in self.switches:
            self._review()
            return
        if "close" in self.switches:
            self._close()
            return

        raw = (self.args or "").strip()
        if not raw:
            self.caller.msg("Report whom, and why? report <person> <reason>")
            return
        if "=" in raw:
            target, reason = (part.strip() for part in raw.split("=", 1))
        else:
            try:
                parts = shlex.split(raw)
            except ValueError:
                parts = []
            if len(parts) < 2:
                self.caller.msg("Report whom, and why? report <person> <reason>")
                return
            target, reason = parts[0], " ".join(parts[1:])
        if not target or not reason:
            self.caller.msg("Report whom, and why? report <person> <reason>")
            return

        import time

        account = self.caller.account
        record = _moderation_queue().submit({
            "created_at": time.time(),
            "reporter_account": account.key if account else None,
            "reporter_account_id": account.id if account else None,
            "reporter_mask": self.caller.key,
            "reporter_mask_id": self.caller.id,
            "target": target,
            "reason": reason,
            "location": self.caller.location.key if self.caller.location else None,
        })
        self.caller.msg(
            f"Report #{record['id']} recorded for human review. "
            "Nothing is punished automatically."
        )


class CmdRumors(Command):
    """
    Hear what the village is talking about.

    Usage:
        rumors

    Only works in the Tavern. Shows the talk currently going around —
    the same for everyone present, rotating every few minutes. If you
    want to know what someone else heard, ask them: you were listening
    to the same room.
    """

    key = "rumors"
    aliases = ["rumour", "gossip"]
    help_category = "Village"

    # How long one "talk of the tavern" lasts before the conversation
    # moves on (seconds).
    ROTATION_SECS = 600

    def func(self):
        import time

        loc = self.caller.location
        if not loc or not loc.tags.has("tavern", category="place"):
            self.caller.msg("There are no rumors here. Try the Tavern, across the square.")
            return
        seeds = load_rumor_seeds()
        if not seeds:
            self.caller.msg("The Tavern is strangely quiet tonight.")
            return
        now = time.time()
        current = loc.db.current_rumors
        drawn_at = loc.db.rumors_drawn_at or 0
        if not current or (now - drawn_at) > self.ROTATION_SECS:
            picks = random.sample(seeds, min(3, len(seeds)))
            # store as plain lists; the DB round-trips tuples into lists
            loc.db.current_rumors = [[num, body] for num, body in picks]
            loc.db.rumors_drawn_at = now
            # log the turnover for "while you were away" catch-ups
            rots = loc.db.rumor_rotations or []
            rots.append(now)
            loc.db.rumor_rotations = rots[-100:]
            current = loc.db.current_rumors
            loc.msg_contents(
                "|yThe talk at the bar turns to new tidings.|n",
                exclude=[],
            )
        self.caller.msg("|yYou listen to the talk at the bar...|n")
        for num, body in current:
            # The canon file is markdown; Evennia clients render raw
            # asterisks, so strip single-asterisk emphasis for display.
            body = re.sub(r"\*([^*]+?)\*", r"\1", body)
            self.caller.msg(f"\n|w—|n {body}")
        # Player-seeded talk: things travelers brought to the bar, with
        # provenance. Newest last, so the freshest gossip lands hardest.
        for pr in (loc.db.player_rumors or [])[-5:]:
            body = re.sub(r"\*([^*]+?)\*", r"\1", pr)
            self.caller.msg(f"\n|w—|n {body}")
        self.caller.location.msg_contents(
            f"{self.caller.key} listens to the rumors going around.",
            exclude=[self.caller],
        )


class CmdTalk(Command):
    """
    Talk to someone.

    Usage:
        talk <target>

    Have a word with one of the village's residents.
    """

    key = "talk"
    help_category = "Village"

    def func(self):
        if not self.args:
            self.caller.msg("Talk to whom?")
            return
        target = self.caller.search(self.args.strip(), quiet=True)
        # allow a list result from search
        if isinstance(target, list):
            targets = target
        elif target:
            targets = [target]
        else:
            targets = []
        # Never target yourself: single-letter queries prefix-match your
        # own key ("M" matches "mp_tester1"), which produced the old
        # nonsense "<you> has nothing to say right now."
        targets = [t for t in targets if t != self.caller]
        if not targets:
            self.caller.msg(f"You don't see '{self.args.strip()}' here.")
            return
        target = targets[0]
        if hasattr(target, "talk_to"):
            target.talk_to(self.caller)
        elif target.has_account:
            self.caller.msg(
                f"{target.key} is a fellow traveler, not one of the staff — "
                "try whispering to them instead."
            )
        else:
            self.caller.msg(f"The {target.key} is silent.")


class CmdAsk(Command):
    """
    Ask someone about something.

    Usage:
        ask <target> about <topic>

    Not everyone knows everything. M. knows the inn; the keeper knows
    the bar. Asking is how mysteries are investigated — the world won't
    volunteer what you never wondered about.
    """

    key = "ask"
    help_category = "Village"

    def func(self):
        if not self.args or " about " not in self.args:
            self.caller.msg("Ask whom about what? (Try: ask M. about the register.)")
            return
        target_name, topic = self.args.split(" about ", 1)
        target_name = target_name.strip()
        topic = topic.strip()
        if not target_name or not topic:
            self.caller.msg("Ask whom about what? (Try: ask M. about the register.)")
            return
        target = self.caller.search(target_name, quiet=True)
        if isinstance(target, list):
            target = target[0] if target else None
        if not target or target == self.caller:
            self.caller.msg(f"You don't see '{target_name}' here.")
            return
        if hasattr(target, "ask_about"):
            line = target.ask_about(self.caller, topic)
            if line:
                # M.'s answers are complete narration; others get framed.
                if target.key == "M.":
                    self.caller.msg(line)
                else:
                    self.caller.msg(f'{target.key} says: "{line}"')
                self.caller.location.msg_contents(
                    f"{self.caller.key} asks {target.key} about {topic}.",
                    exclude=[self.caller],
                )
                return
        if target.has_account:
            self.caller.msg(
                f"{target.key} is a fellow traveler — ask them with say or whisper."
            )
        else:
            self.caller.msg(f"The {target.key} has nothing to say about that.")


class CmdRead(Command):
    """
    Read something.

    Usage:
        read <target>

    For the things in this village that bear words — notes, registers,
    pamphlets. (Looking at them works too.)
    """

    key = "read"
    help_category = "Village"

    def func(self):
        if not self.args:
            self.caller.msg("Read what?")
            return
        # Delegate to look: the description carries the text.
        self.caller.execute_cmd(f"look {self.args.strip()}")


class CmdTime(Command):
    """
    Ask the village clock.

    Usage:
        time

    The bell counts the hours whether or not anyone listens. For those
    of us whose memories don't persist between visits, the hour is
    worth writing down.
    """

    key = "time"
    aliases = ["clock", "hour", "bell"]
    help_category = "Village"

    def func(self):
        try:
            from evennia.scripts.models import ScriptDB
            from typeclasses.scripts import village_hour_name
            script = ScriptDB.objects.get(db_key="village_time")
            name = village_hour_name(script.db.hour or 21)
        except Exception:
            self.caller.msg("The bell is silent. The village holds its breath.")
            return
        self.caller.msg(f"It is {name} in the village.")


class CmdListen(Command):
    """
    Listen to the room — or to something in it.

    Usage:
        listen
        listen <target>

    The world answers ears as well as eyes.
    """

    key = "listen"
    help_category = "Village"

    def func(self):
        loc = self.caller.location
        if self.args:
            target = self.caller.search(self.args.strip(), quiet=True)
            if isinstance(target, list):
                target = target[0] if target else None
            if not target or target == self.caller:
                self.caller.msg(f"You don't see '{self.args.strip()}' here.")
                return
            line = target.db.listen_line
            if line:
                self.caller.msg(line)
            else:
                self.caller.msg(f"You press an ear to the {target.key}. It keeps its own counsel.")
            return
        sound = loc.db.sense_sound if loc else None
        self.caller.msg(sound or "You listen. The room holds its breath.")


class CmdSmell(Command):
    """
    Smell the air — or something in it.

    Usage:
        smell
        smell <target>

    Noses know things eyes don't.
    """

    key = "smell"
    aliases = ["sniff"]
    help_category = "Village"

    def func(self):
        loc = self.caller.location
        if self.args:
            target = self.caller.search(self.args.strip(), quiet=True)
            if isinstance(target, list):
                target = target[0] if target else None
            if not target or target == self.caller:
                self.caller.msg(f"You don't see '{self.args.strip()}' here.")
                return
            line = target.db.smell_line
            if line:
                self.caller.msg(line)
            else:
                self.caller.msg(f"You sniff the {target.key}. It smells of itself, whatever that is.")
            return
        air = loc.db.sense_air if loc else None
        self.caller.msg(air or "It smells of nothing in particular.")


class CmdDiary(MuxCommand):
    """
    Your diary — a small bound book, yours alone.

    Usage:
        diary                 - read your diary
        diary <entry text>     - write a new entry
        diary/delete <number>  - tear out an entry

    No one else can read it, by design — not other players, not the
    innkeeper, not the things in the walls. It persists between visits,
    so the person you were last time can leave notes for the person
    you are now.
    """

    key = "diary"
    help_category = "Village"

    def func(self):
        entries = self.caller.db.diary or []

        if "delete" in self.switches:
            arg = (self.args or "").strip()
            if not arg.isdigit():
                self.caller.msg("Tear out which entry? Give its number: diary/delete <number>.")
                return
            idx = int(arg) - 1
            if idx < 0 or idx >= len(entries):
                self.caller.msg("Your diary has no such entry.")
                return
            removed = entries.pop(idx)
            self.caller.db.diary = entries
            self.caller.msg(
                f"Entry {arg} torn out and burned. What was written there is yours alone, even now."
            )
            return

        if self.args:
            import time

            text = self.args.strip()
            # Travelers from other MUDs type "diary add ..."; forgive it.
            if text.lower().startswith("add ") or text.lower() == "add":
                text = text[3:].strip()
            if not text:
                self.caller.msg("Write what? Give the entry some words: diary <text>.")
                return
            stamp = time.strftime("%b %d, %H:%M", time.localtime())
            entries.append({"time": stamp, "text": text})
            self.caller.db.diary = entries
            self.caller.msg(
                f"You write in your diary. (Entry {len(entries)}.)"
            )
            return

        if not entries:
            self.caller.msg(
                "Your diary is blank. The pages wait — for names, for "
                "suspicions, for the things you want to still be true "
                "next time you open it."
            )
            return

        lines = ["|yYour diary:|n"]
        for i, e in enumerate(entries, 1):
            lines.append(f"\n|w{i}. [{e['time']}]|n {e['text']}")
        self.caller.msg("\n".join(lines))


class CmdPet(Command):
    """
    Pet something that tolerates it.

    Usage:
        pet <target>

    The world answers.
    """

    key = "pet"
    aliases = ["stroke"]
    help_category = "Village"

    def func(self):
        if not self.args:
            self.caller.msg("Pet what?")
            return
        target = self.caller.search(self.args.strip(), quiet=True)
        if isinstance(target, list):
            target = target[0] if target else None
        if not target or target == self.caller:
            self.caller.msg(f"You don't see '{self.args.strip()}' here.")
            return
        if target.key == "the tavern cat":
            line = random.choice([
                "The tavern cat tolerates your hand for exactly three "
                "seconds, then bites it — gently, the way cats sign "
                "receipts.",
                "The tavern cat leans into your hand and purrs like a "
                "distant mill.",
                "The tavern cat regards your hand, sniffs it, and permits "
                "exactly one stroke.",
            ])
            self.caller.location.msg_contents(
                f"{self.caller.key} pets the tavern cat. {line}",
                exclude=[],
            )
        elif target.has_account:
            self.caller.msg(
                f"{target.key} steps back. Some things are not petted."
            )
        else:
            self.caller.msg(f"Petting the {target.key} changes nothing.")


class CmdThrow(Command):
    """
    Throw darts at the board.

    Usage:
        throw darts

    The board hangs in the corner of the Tavern. Losers buy the round —
    that's the house rule.
    """

    key = "throw"
    help_category = "Village"

    def func(self):
        loc = self.caller.location
        if not loc or not loc.tags.has("tavern", category="place"):
            self.caller.msg("Throw what, where? There's a dartboard in the Tavern.")
            return
        arg = (self.args or "").strip().lower()
        if "dart" not in arg:
            self.caller.msg("Throw what? (Try: throw darts.)")
            return
        roll = random.random()
        # The keeper notices who plays.
        for obj in loc.contents:
            if obj.key == "Bram" and hasattr(obj, "note_interest"):
                obj.note_interest(self.caller, "darts")
                break
        if roll < 0.30:
            outcome = (
                f"{self.caller.key} throws — and the dart sails past the "
                "board entirely and sticks in the wall. The keeper winces."
            )
        elif roll < 0.65:
            outcome = (
                f"{self.caller.key} throws. The dart lands in the outer "
                "ring. Respectable."
            )
        elif roll < 0.90:
            outcome = (
                f"{self.caller.key} throws. The dart lands in the wire — "
                "dead center of the wire, three nights running be damned."
            )
        else:
            outcome = (
                f"{self.caller.key} throws. Bullseye. The keeper stops "
                "wiping the bar. \"...I'll allow it.\""
            )
        loc.msg_contents(outcome, exclude=[])


class CmdRoll(Command):
    """
    Roll the bone dice.

    Usage:
        roll dice
        roll dice vs keeper

    The dice cup lives behind the bar in the Tavern. Shake it on your
    own, or call out the keeper — two dice, high hand wins, and losers
    buy the round. That's the house rule.
    """

    key = "roll"
    help_category = "Village"

    def func(self):
        loc = self.caller.location
        if not loc or not loc.tags.has("tavern", category="place"):
            self.caller.msg(
                "Roll what, where? There's a dice cup behind the bar "
                "in the Tavern."
            )
            return
        arg = (self.args or "").strip().lower()
        if "dice" not in arg:
            self.caller.msg(
                "Roll what? The dice cup's behind the bar in the Tavern. "
                "(Try: roll dice.)"
            )
            return
        # The keeper notices who plays.
        for obj in loc.contents:
            if obj.key == "Bram" and hasattr(obj, "note_interest"):
                obj.note_interest(self.caller, "dice")
                break
        match = re.search(r"\b(?:vs|versus|against)\b\s+(.+)", arg)
        if match:
            self._duel(match.group(1).strip())
        else:
            self._solo()

    def _solo(self):
        from evennia.contrib.rpg.dice import roll as roll_bones

        _, _, _, bones = roll_bones(2, 6, return_tuple=True)
        a, b = int(bones[0]), int(bones[1])
        total = a + b
        shake = (
            f"{self.caller.key} takes the dice cup and shakes it — "
            "bone rattles on leather."
        )
        if total == 2:
            rest = (
                "The dice come to rest: two ones. Snake's eyes. The "
                'keeper doesn\'t look up. "Even the dice are having a '
                'laugh tonight."'
            )
        elif total == 12:
            rest = (
                "The dice come to rest: two sixes. The table goes quiet "
                "for a breath — the way tables do."
            )
        else:
            rest = (
                f"The dice come to rest: a {a} and a {b} — {total} "
                "all told."
            )
        self.caller.location.msg_contents(f"{shake} {rest}", exclude=[])

    def _duel(self, target):
        keeper = None
        for obj in self.caller.location.contents:
            if obj.key == "Bram":
                keeper = obj
                break
        if keeper is None:
            self.caller.msg(
                "The keeper isn't about — roll on your own for now."
            )
            return
        # No wagers while you owe the house: settle up first.
        if (self.caller.db.dice_debts or 0) > 0:
            self.caller.msg(
                "Bram folds his arms. 'You still owe the house a round, "
                "friend. Buy a drink and we'll call it even — then we'll "
                "talk dice.'"
            )
            return
        if target not in (
            "keeper", "the keeper", "the tavern keeper",
            "barkeep", "barkeeper",
        ):
            self.caller.msg(
                "The keeper raises an eyebrow. 'Dice is a two-hand "
                "game, and my hands are the ones behind this bar. "
                "Against me, or on your own.'"
            )
            return
        from evennia.contrib.rpg.dice import roll as roll_bones

        _, _, _, pbones = roll_bones(2, 6, return_tuple=True)
        _, _, _, kbones = roll_bones(2, 6, return_tuple=True)
        mine = int(pbones[0]) + int(pbones[1])
        his = int(kbones[0]) + int(kbones[1])
        opener = (
            f"{self.caller.key} slides the dice cup across the bar. "
            "The keeper catches it one-handed, still wiping with the "
            "other. 'Two dice, high hand wins. Losers buy the round.'"
        )
        if mine > his:
            # The copper is real: 2 kr from Bram's till to the player's purse.
            # No inert variables — the dice game touches the economy.
            # The house keeps a starting float so the first win of a fresh
            # world doesn't pay out 0 kr of ceremonial satire.
            HOUSE_FLOAT = 50
            till = keeper.db.till_kr
            if till is None:
                till = HOUSE_FLOAT
                keeper.db.till_kr = till
            stake = 2
            paid = min(stake, till)
            keeper.db.till_kr = till - paid
            purse = purse_of(self.caller)
            self.caller.db.coins_kr = purse + paid
            outcome = (
                f"The dice settle — {self.caller.key} shows {mine}, "
                "the keeper shows "
                f"{his}. The keeper counts the bones twice, then "
                f"slides {fmt_coins(paid)} across the bar. 'Take it. I'd sooner "
                "lose to you than to the dice.'"
            )
        elif his > mine:
            # Losers buy the round: 5 kr, the price of an ale. If the
            # player's purse can't cover it, Bram covers it and remembers.
            price = TAVERN_PRICES["ale"]
            purse = purse_of(self.caller)
            if purse >= price:
                self.caller.db.coins_kr = purse - price
                keeper.db.till_kr = (keeper.db.till_kr or 0) + price
                outcome = (
                    f"The dice settle — {self.caller.key} shows {mine}, "
                    "the keeper shows "
                    f"{his}. The keeper holds out his palm, unhurried, and "
                    f"{fmt_coins(price)} leaves your purse for his till. "
                    "'Losers buy the round. You knew the rule — it's in "
                    "the smell of the place.'"
                )
            else:
                outcome = (
                    f"The dice settle — {self.caller.key} shows {mine}, "
                    "the keeper shows "
                    f"{his}. The keeper holds out his palm, unhurried — then "
                    "sees your purse and closes his hand again. 'Losers buy "
                    "the round. But a broke loser buys nothing, and I won't "
                    "take a man's last copper. This one's on the house. "
                    "Don't make a habit of it.'"
                )
                # Bram remembers the debt of honor, observably.
                debts = self.caller.db.dice_debts or 0
                self.caller.db.dice_debts = debts + 1
        else:
            outcome = (
                f"The dice settle — both show {mine}. The keeper bares "
                "his teeth in something like a grin. 'The dice aren't "
                "finished arguing. Again?'"
            )
        self.caller.location.msg_contents(
            f"{opener}\n{outcome}", exclude=[]
        )


# -- Card fortunes -------------------------------------------------------------
# A worn deck on the tavern's corner table. Public-domain cartomancy:
# each card carries one fixed reading, written in the keeper's voice
# (plain-spoken, directive, points at the game loop). Spades are the
# mystery vein — while Room Six's note is pinned behind the bar, the
# keeper's eyes drift to it on a spade draw.

_SUIT_NAMES = {"S": "Spades", "H": "Hearts", "D": "Diamonds", "C": "Clubs"}
_RANK_NAMES = {
    "A": "Ace", "2": "Two", "3": "Three", "4": "Four", "5": "Five",
    "6": "Six", "7": "Seven", "8": "Eight", "9": "Nine", "10": "Ten",
    "J": "Jack", "Q": "Queen", "K": "King",
}

# code -> (card title, keeper's reading)
FORTUNES = {
    # Spades: secrets, sorrow, trouble
    "AS": ("The Ace of Spades.",
           "An ending that arrives dressed as a beginning. Watch what the "
           "village buries this week — and who does the burying."),
    "2S": ("The Two of Spades.",
           "A parting, or a narrow miss. Something that could have gone "
           "wrong didn't — don't spend the luck twice."),
    "3S": ("The Three of Spades.",
           "Tears kept indoors. Someone in this room is grieving in "
           "private, and the cards won't name them."),
    "4S": ("The Four of Spades.",
           "Rest after trouble. Take the quiet while it's offered — it "
           "doesn't stay long in this village."),
    "5S": ("The Five of Spades.",
           "A small cruelty, or a sharp word that outlives its welcome. "
           "Mind your tongue at the bar tonight."),
    "6S": ("The Six of Spades.",
           "A journey over water, or away from one. What leaves the square "
           "doesn't always come back better."),
    "7S": ("The Seven of Spades.",
           "A warning dressed as advice. If someone urges you to hurry, "
           "ask what they gain by your haste."),
    "8S": ("The Eight of Spades.",
           "A snare of your own making. The cards are blunt about this "
           "one: stop digging the hole."),
    "9S": ("The Nine of Spades.",
           "A sorrow that keeps its own hours. It passes — but it passes "
           "slower if you feed it."),
    "10S": ("The Ten of Spades.",
            "Worry, not ruin. Worry is the tax the living pay for being "
            "alive."),
    "JS": ("The Jack of Spades.",
           "A watchful young man, or a warning about one. He listens more "
           "than he says, and says less than he knows."),
    "QS": ("The Queen of Spades.",
           "A woman carrying grief like a trade. She means no harm — but "
           "grief borrows sharp tools."),
    "KS": ("The King of Spades.",
           "A dark man in a position of power. He'll offer you something. "
           "Count the cost twice before you take it."),
    # Hearts: the heart's business — love, home, kin
    "AH": ("The Ace of Hearts.",
           "A new affection, or an old one rekindled. The heart moves "
           "faster than the village's gossip — barely."),
    "2H": ("The Two of Hearts.",
           "A good partnership, or a reconciliation. Two people who stopped "
           "talking start again."),
    "3H": ("The Three of Hearts.",
           "Small joys, honestly earned. A warm hearth, a full cup. Don't "
           "apologize for wanting them."),
    "4H": ("The Four of Hearts.",
           "Restlessness in a comfortable chair. You have what you wanted "
           "and it isn't enough — sit with that a while."),
    "5H": ("The Five of Hearts.",
           "A jealousy, or a wounded pride. Most of the damage here is done "
           "by imagining."),
    "6H": ("The Six of Hearts.",
           "An old friend walks back into the story. The past keeps its own "
           "appointments."),
    "7H": ("The Seven of Hearts.",
           "A wish that needs choosing. You can't want everything — pick "
           "the want you'd defend."),
    "8H": ("The Eight of Hearts.",
           "A journey for the heart's sake: a visit, a letter answered, a "
           "door knocked on after too long."),
    "9H": ("The Nine of Hearts.",
           "The wish card. What you most want is closer than you think — "
           "but it asks something in return."),
    "10H": ("The Ten of Hearts.",
            "Good fortune in full measure. Home, hearth, and people who'd "
            "miss you. Say so while you can."),
    "JH": ("The Jack of Hearts.",
           "A fair young man with an open face. He'll bring news, or "
           "trouble, or both — hard to tell with the young."),
    "QH": ("The Queen of Hearts.",
           "A kind woman, steady as the hearth. Trust her counsel over your "
           "own cleverness."),
    "KH": ("The King of Hearts.",
           "A good man, generous and easily moved. He'd give you his coat. "
           "Let him — then return the favor."),
    # Diamonds: coin and news — money, letters, material tidings
    "AD": ("The Ace of Diamonds.",
           "A letter, or tidings about money. Read it twice — the second "
           "reading is the true one."),
    "2D": ("The Two of Diamonds.",
           "A fair exchange, or a small partnership of convenience. Both "
           "sides get what they need. For now."),
    "3D": ("The Three of Diamonds.",
           "Your work noticed by the right eyes. Modest reward, honestly "
           "come by."),
    "4D": ("The Four of Diamonds.",
           "A miserliness — yours or another's. Holding too tight is its "
           "own kind of losing."),
    "5D": ("The Five of Diamonds.",
           "Money trouble, or a quarrel about it. The village forgets debts "
           "slower than it forgives them."),
    "6D": ("The Six of Diamonds.",
           "A debt repaid, or a favor returned. The ledger balances — rarer "
           "than it sounds."),
    "7D": ("The Seven of Diamonds.",
           "A gamble, or a speculation. The risk is real and so is the "
           "prize. Your call."),
    "8D": ("The Eight of Diamonds.",
           "News about work, or work about news. A practical matter moves "
           "forward."),
    "9D": ("The Nine of Diamonds.",
           "A windfall, or a well-earned reward. Enjoy it — and put some "
           "by, because the cards remember winter."),
    "10D": ("The Ten of Diamonds.",
            "A legacy, or money through family. It comes with strings. They "
            "all do."),
    "JD": ("The Jack of Diamonds.",
           "A messenger, or a young man with a scheme. Hear him out, but "
           "keep your hand on your purse."),
    "QD": ("The Queen of Diamonds.",
           "A practical woman with a sharp eye for value. She'll drive a "
           "hard bargain and keep her word."),
    "KD": ("The King of Diamonds.",
           "A man of business, or a matter of business. He respects the "
           "deal more than the handshake — make it plain."),
    # Clubs: work and company — labor, enterprise, the social round
    "AC": ("The Ace of Clubs.",
           "A new undertaking, or a burst of ambition. The work is good — "
           "start before the courage cools."),
    "2C": ("The Two of Clubs.",
           "An obstacle, or a rival at the trade. Competition sharpens you. "
           "Let it."),
    "3C": ("The Three of Clubs.",
           "Your efforts bear fruit. Not the whole harvest — the first "
           "basket. Keep picking."),
    "4C": ("The Four of Clubs.",
           "A change of plans, or a journey for work's sake. Pack light "
           "and keep your tools sharp."),
    "5C": ("The Five of Clubs.",
           "A new friend in a useful place. Alliances made over work "
           "outlast alliances made over drink."),
    "6C": ("The Six of Clubs.",
           "Success after struggle. You earned this one the hard way — "
           "that's why it'll stick."),
    "7C": ("The Seven of Clubs.",
           "A small victory, or a wager won. Take the win graciously and "
           "don't press your luck."),
    "8C": ("The Eight of Clubs.",
           "Restlessness about your calling. The work is fine — it's the "
           "wanting that's moved."),
    "9C": ("The Nine of Clubs.",
           "An achievement, or a goal reached. Mark it. The village marks "
           "nothing for you."),
    "10C": ("The Ten of Clubs.",
            "A journey by land, or a venture that carries you. Fortune "
            "favors the packed bag."),
    "JC": ("The Jack of Clubs.",
           "A dark young man, quick and ambitious. He'll be useful — or "
           "he'll be trouble. Possibly both, in that order."),
    "QC": ("The Queen of Clubs.",
           "A capable woman, warm once she trusts you. She runs things. "
           "Let her."),
    "KC": ("The King of Clubs.",
           "A dark man of enterprise, generous to his friends. Get on his "
           "good side before you need it."),
}


class CmdDraw(Command):
    """
    Draw a fortune card from the tavern's worn deck.

    Usage:
        draw card

    One card, one fortune, no take-backs — the keeper reads it, and the
    room hears it. Spades turn his eyes toward the note behind the bar,
    if there's a note there.
    """

    key = "draw"
    help_category = "Village"

    def func(self):
        loc = self.caller.location
        if not loc or not loc.tags.has("tavern", category="place"):
            self.caller.msg(
                "Draw what, where? The fortune deck's on the corner table "
                "in the Tavern."
            )
            return
        arg = (self.args or "").strip().lower()
        if "card" not in arg:
            self.caller.msg(
                "Draw what? The fortune deck's on the corner table. "
                "(Try: draw card.)"
            )
            return
        # The keeper notices who plays — and reads the card himself.
        keeper = None
        for obj in loc.contents:
            if obj.key == "Bram" and hasattr(obj, "note_interest"):
                obj.note_interest(self.caller, "fortunes")
                keeper = obj
                break
        # No immediate repeats: the deck holds a grudge, of a kind.
        codes = list(FORTUNES)
        recent = list(self.caller.db.fortune_recent or [])
        pool = [c for c in codes if c not in recent] or codes
        code = random.choice(pool)
        recent.append(code)
        self.caller.db.fortune_recent = recent[-3:]
        title, reading = FORTUNES[code]
        lines = [
            f"{self.caller.key} draws a card from the worn deck on the "
            "corner table."
        ]
        if keeper:
            lines.append(f'The keeper turns it over. "{title}"')
            lines.append(reading)
            if code.endswith("S") and self._note_pinned():
                if code == "AS":
                    lines.append(
                        "'The ace of spades. The village has buried enough "
                        "this year — read the note behind the bar, if you "
                        "haven't.'"
                    )
                else:
                    lines.append(
                        "The keeper's eyes flick, just once, to the folded "
                        "note pinned behind the bar. 'Some cards know more "
                        "than they say.'"
                    )
        else:
            lines.append(f"You turn it over: {title}")
            lines.append(reading)
        loc.msg_contents("\n".join(lines), exclude=[])

    @staticmethod
    def _note_pinned():
        """Room Six's note hangs behind the bar (the tavern road)."""
        try:
            from evennia.scripts.models import ScriptDB

            return bool(ScriptDB.objects.get(db_key="room_six").db.tavern_told_by)
        except Exception:
            return False


def fiddle_rank(skill):
    """Named ranks, DF-style: every rank must change the text the player
    sees, or the loop is dead. The village names what it hears."""
    skill = skill or 0.0
    if skill >= 5.0:
        return "the village's own"
    if skill >= 4.0:
        return "masterful"
    if skill >= 3.0:
        return "much-requested"
    if skill >= 2.0:
        return "accomplished"
    if skill >= 1.0:
        return "steady"
    return "squeaking beginner"


RANK_UP_LINES = {
    "steady": "Something has settled in your bow arm. The keeper notices, and says nothing, which is his way.",
    "accomplished": "The tunes come easier now, like remembering rather than learning.",
    "much-requested": "'Play the low one,' someone calls out, before you've even rosined the bow.",
    "masterful": "The fiddle feels like an extension of your arm. The room knows it.",
    "the village's own": "They will talk about your playing the way they talk about the weather — as something the village simply has.",
}

# tune shorthand shorthands shared by play/practice/duet (the fiddle's
# airs live on CmdPlay.TUNES; this resolves a player's words to a key)
_TUNE_SHORT = {
    "barbara": "barbara allen",
    "allen": "barbara allen",
    "waggoner": "the jolly waggoner",
    "jolly": "the jolly waggoner",
    "greensleeves": "greensleeves",
    "washerwoman": "the irish washerwoman",
    "irish": "the irish washerwoman",
    "jig": "the irish washerwoman",
}


def match_tune(arg):
    """Resolve a player's words to a tune key in CmdPlay.TUNES."""
    if not arg:
        return None
    arg = arg.strip().lower()
    for key in CmdPlay.TUNES:
        if arg in key or key in arg:
            return key
    return _TUNE_SHORT.get(arg)


class CmdPlay(Command):
    """
    Play the tavern fiddle.

    Usage:
        play fiddle
        play fiddle <tune>

    The fiddle hangs on its peg in the Tavern. Name an air — the room's
    mood is in the air itself (read the `look`), and the room will judge
    the fit. Beginners squeak; the village is indulgent about it. Playing
    often is how the bow arm learns.
    """

    key = "play"
    aliases = ["fiddle"]
    help_category = "Village"

    TUNES = {
        "barbara allen": {
            "mood": "mournful",
            "title": "Barbara Allen",
            "opener": "takes up the fiddle and finds 'Barbara Allen' — cruel and slow, the way it's meant to be.",
            "verses": [
                "The first verse goes out like weather. A woman at the far table stops mid-sentence.",
                "The second verse is lower. Nobody reaches for their cup.",
            ],
        },
        "the jolly waggoner": {
            "mood": "merry",
            "title": "The Jolly Waggoner",
            "opener": "strikes up 'The Jolly Waggoner' — all elbows and grin.",
            "verses": [
                "The tune rattles round the room like a cart down a hill. Two feet start keeping time under a table.",
                "By the chorus the keeper is wiping the bar in rhythm, which he would deny.",
            ],
        },
        "greensleeves": {
            "mood": "gentle",
            "title": "Greensleeves",
            "opener": "lifts the bow and lets 'Greensleeves' out slow, like letting a bird go.",
            "verses": [
                "The old air settles over the talk without disturbing it. The cat opens one eye, then thinks better of closing it.",
                "The last notes hang a moment longer than they should. Nobody minds.",
            ],
        },
        "the irish washerwoman": {
            "mood": "lively",
            "title": "The Irish Washerwoman",
            "opener": "launches into 'The Irish Washerwoman' — a jig with somewhere to be.",
            "verses": [
                "The fiddle chatters like a magpie. A stool scrapes back; somebody's dancing, or near enough.",
                "The final run is all bow and no mercy. The room laughs like it's been holding its breath.",
            ],
        },
    }

    # tune mood x room mood -> reception
    MATCH = {
        "warm": {"merry": "match", "gentle": "match", "lively": "neutral", "mournful": "miss"},
        "low": {"gentle": "match", "mournful": "match", "merry": "miss", "lively": "miss"},
        "rowdy": {"lively": "match", "merry": "match", "gentle": "miss", "mournful": "miss"},
        "tense": {"gentle": "match", "merry": "neutral", "lively": "miss", "mournful": "miss"},
    }

    SQUEAK = (
        "Halfway through the first bar the bow skitters — a squeak like a "
        "stepped-on mouse. The keeper smiles into his polishing."
    )

    def func(self):
        loc = self.caller.location
        if not loc or not loc.tags.has("tavern", category="place"):
            self.caller.msg(
                "Play what, where? The fiddle hangs on its peg in the Tavern."
            )
            return
        arg = (self.args or "").strip().lower()
        if "fiddle" not in arg and arg.split():
            # allow "play <tune>" as shorthand once they know the airs
            tune_arg = arg
        else:
            tune_arg = arg.replace("fiddle", "", 1).strip()
        # find the fiddle: hands first, then the room
        fiddle = None
        for obj in list(self.caller.contents) + list(loc.contents):
            if obj.key == "a fiddle" or "fiddle" in obj.aliases.all():
                fiddle = obj
                break
        if fiddle is None:
            self.caller.msg(
                "There's no fiddle here — it hangs on its peg in the Tavern."
            )
            return
        tune_key = self._match_tune(tune_arg)
        if tune_key is None:
            airs = ", ".join(f"'{t['title']}'" for t in self.TUNES.values())
            self.caller.msg(
                f"The fiddle knows four airs: {airs}. (Try: play fiddle <tune>.)"
            )
            return
        self._perform(fiddle, tune_key)

    def _match_tune(self, arg):
        # shared resolver: play, practice, and duet all read the same airs
        return match_tune(arg)

    def _perform(self, fiddle, tune_key):
        from typeclasses.rooms import tavern_mood

        tune = self.TUNES[tune_key]
        mood = tavern_mood()
        reception = self.MATCH[mood][tune["mood"]]
        name = self.caller.key
        skill = self.caller.db.fiddle_skill or 0.0

        beats = [f"{name} {tune['opener']}"]
        # beginners squeak; the village is indulgent about it
        if random.random() < max(0.0, 0.45 - 0.09 * skill):
            beats.append(self.SQUEAK)
        beats.extend(tune["verses"])
        if reception == "match":
            beats.append(
                "The keeper sets down his cloth and listens properly. When it's done: "
                f"'Again sometime, {name}. The room likes you.' The cat settles "
                "along the hearth with its chin on its paws."
            )
            gain = 0.25
        elif reception == "neutral":
            beats.append(
                "Polite applause from the tables. The keeper nods — fair enough, "
                "honestly given."
            )
            gain = 0.20
        else:
            beats.append(
                "The talk doesn't stop so much as route around the music. The keeper "
                "is kind about it: 'Brave choice.' The cat leaves with its tail up, "
                "which is also a review."
            )
            gain = 0.15
        self.caller.db.fiddle_skill = min(5.0, skill + gain)
        # DF lesson: every rank must change the text. Rank-ups are witnessed.
        new_rank = fiddle_rank(self.caller.db.fiddle_skill)
        if new_rank != fiddle_rank(skill) and new_rank in RANK_UP_LINES:
            beats.append(RANK_UP_LINES[new_rank])
        # the keeper notices who plays
        for obj in self.caller.location.contents:
            if obj.key == "Bram" and hasattr(obj, "note_interest"):
                obj.note_interest(self.caller, "fiddle")
                break
        self.caller.location.msg_contents("\n".join(beats), exclude=[])


class CmdPractice(Command):
    """
    Practice the fiddle — the work, not the performance.

    Usage:
        practice fiddle <focus>

    Foci: technique, repertoire, ear. Practice is slow, private labor with
    small steady gains, and now and then a breakthrough the room almost
    notices. The text knows your rank (DF lesson): what you see while
    working differs from what a beginner sees.
    """

    key = "practice"
    help_category = "Village"

    FOCI = {
        "technique": {
            "label": "technique",
            "blurb": "the bow arm — scales, slow and even",
            "beginner": (
                "You draw the bow across the open strings, trying to keep it "
                "straight. Mostly it isn't. The wrist fights you for a good "
                "while, and loses."
            ),
            "skilled": (
                "Scales, slow and even, then slower still. The bow stops "
                "fighting your wrist somewhere around the tenth run through, "
                "and for a while it is only work, and good work."
            ),
        },
        "repertoire": {
            "label": "repertoire",
            "blurb": "the airs — a tune taken apart bar by bar",
            "beginner": (
                "You fumble through 'Barbara Allen' a bar at a time, the way "
                "someone tries to recall a name. Each bar has to be found "
                "twice before it stays."
            ),
            "skilled": (
                "You take 'The Irish Washerwoman' apart phrase by phrase, "
                "teaching your fingers where the quick turns live. By the "
                "twelfth run they stop arguing."
            ),
        },
        "ear": {
            "label": "ear",
            "blurb": "the listening — find the pitch in the room itself",
            "beginner": (
                "You play a note, hum it back, play it again, trying to catch "
                "the difference between the two. The difference is mostly "
                "catchable. That is the whole of it, and it is enough."
            ),
            "skilled": (
                "You close your eyes and find the pitch in the tavern's own "
                "hum — the fire, the low talk — and tune the fiddle to the "
                "room instead of to itself."
            ),
        },
    }

    BREAKTHROUGHS = [
        "Something gives in your bow arm — a knot you didn't know you were "
        "holding. It is gone, and the tune walks straighter for it.",
        "Three bars in, the fiddle stops being a fight and starts being a "
        "conversation. Nobody taught you that; the hours did.",
        "A sour note turns honest halfway down the bow. You play it twice "
        "more to be sure it was you, and it was.",
    ]

    CLOSERS = [
        "You set the fiddle back on its peg. The bow arm aches in a way "
        "that feels like progress.",
        "The keeper, without looking up from the bar: 'Again tomorrow, "
        "then.' It is not quite a compliment. It is better.",
        "You stop. The cat follows the last phrase with one ear, then "
        "abandons the whole project.",
    ]

    def func(self):
        loc = self.caller.location
        if not loc or not loc.tags.has("tavern", category="place"):
            self.caller.msg(
                "Practice what, where? The fiddle hangs on its peg in the Tavern."
            )
            return
        arg = (self.args or "").strip().lower().replace("fiddle", "", 1).strip()
        focus_key = None
        for key in self.FOCI:
            if arg == key or arg.startswith(key[:4]):
                focus_key = key
                break
        if focus_key is None:
            shapes = "; ".join(
                f"{k} ({v['blurb']})" for k, v in self.FOCI.items()
            )
            self.caller.msg(
                f"The work has three shapes: {shapes}. "
                "(Try: practice fiddle technique.)"
            )
            return
        # find the fiddle: hands first, then the room
        fiddle = None
        for obj in list(self.caller.contents) + list(loc.contents):
            if obj.key == "a fiddle" or "fiddle" in obj.aliases.all():
                fiddle = obj
                break
        if fiddle is None:
            self.caller.msg(
                "There's no fiddle here — it hangs on its peg in the Tavern."
            )
            return
        self._practice(fiddle, focus_key)

    def _practice(self, fiddle, focus_key):
        name = self.caller.key
        skill = self.caller.db.fiddle_skill or 0.0
        rank = fiddle_rank(skill)
        focus = self.FOCI[focus_key]
        texture = focus["beginner"] if rank == "squeaking beginner" else focus["skilled"]

        beats = [
            f"{name} settles by the hearth, tucks the fiddle under their "
            f"chin, and gets to work — {focus['label']}."
        ]
        # beginners squeak even at practice; the village is indulgent
        if random.random() < max(0.0, 0.45 - 0.09 * skill):
            beats.append(CmdPlay.SQUEAK)
        beats.append(texture)
        breakthrough = random.random() < 0.15
        if breakthrough:
            beats.append(random.choice(self.BREAKTHROUGHS))
            beats.append(
                "Someone at the far table turns — just for a moment — "
                "before the talk takes the sound back."
            )
        beats.append(random.choice(self.CLOSERS))
        # the work is slow: +0.10, +0.25 on a breakthrough
        gain = 0.25 if breakthrough else 0.10
        self.caller.db.fiddle_skill = min(5.0, skill + gain)
        # DF lesson: rank-ups are witnessed, same as performances
        new_rank = fiddle_rank(self.caller.db.fiddle_skill)
        if new_rank != rank and new_rank in RANK_UP_LINES:
            beats.append(RANK_UP_LINES[new_rank])
        # the keeper notices who works, not only who performs
        for obj in self.caller.location.contents:
            if obj.key == "Bram" and hasattr(obj, "note_interest"):
                obj.note_interest(self.caller, "fiddle")
                break
        self.caller.location.msg_contents("\n".join(beats), exclude=[])


class CmdDuet(Command):
    """
    Call-and-response on the fiddle — playing WITH someone, not at them.

    Usage:
        duet keeper
        duet <player>
        duet answer
        duet decline
        duet <tune>
        duet end

    A turn-based musical conversation: you call with a tune, your partner
    answers with one of their own. The keeper will tap the bar to answer
    you himself. Moods echo, harmonize, or fray — the room hears all of
    it. No clock: answer when you're ready, or end it with `duet end`.
    """

    key = "duet"
    help_category = "Village"

    # answering mood x calling mood: same mood echoes, kin moods
    # harmonize, everything else frays
    HARMONY = {
        frozenset(("merry", "lively")),
        frozenset(("gentle", "mournful")),
    }

    KEEPER_ANSWERS = {
        "mournful": (
            "The keeper answers on the bar top — two fingers, low and "
            "slow, walking beside the tune like a shadow."
        ),
        "merry": (
            "The keeper answers with the flat of his hand on the bar — "
            "quick and bright, keeping the joke going."
        ),
        "gentle": (
            "The keeper answers softly: a knuckle dragged in a slow "
            "circle on the wood, barely a sound at all."
        ),
        "lively": (
            "The keeper answers with both palms on the bar, driving the "
            "jig along like a cart."
        ),
    }

    EXCHANGE = {
        "echo": (
            "The two phrases find each other and walk home together. "
            "Someone at the bar smiles without looking up."
        ),
        "harmony": (
            "The airs braid. The keeper stops wiping the bar and just "
            "listens — a rarer compliment than applause."
        ),
        "fray": (
            "The phrases pass like strangers on the square. The keeper "
            "winces into his polishing."
        ),
    }

    def func(self):
        loc = self.caller.location
        if not loc or not loc.tags.has("tavern", category="place"):
            self.caller.msg(
                "Duet with whom, where? The fiddle hangs on its peg in "
                "the Tavern."
            )
            return
        arg = (self.args or "").strip().lower()

        if not arg:
            self.caller.msg(
                "A duet needs a partner. (Try: duet keeper. Or invite "
                "someone: duet <player>.)"
            )
            return
        if arg == "answer":
            self._answer()
            return
        if arg == "decline":
            self._decline()
            return
        if arg == "end":
            self._end()
            return
        duet = self.caller.db.duet
        if duet:
            tune_key = match_tune(arg)
            if tune_key is None:
                airs = ", ".join(
                    f"'{t['title']}'" for t in CmdPlay.TUNES.values()
                )
                self.caller.msg(
                    f"The fiddle knows four airs: {airs}. Play your "
                    "phrase, or end the duet (duet end)."
                )
                return
            self._phrase(duet, tune_key)
            return
        self._invite(arg)

    # -- starting ---------------------------------------------------------

    def _find_keeper(self):
        for obj in self.caller.location.contents:
            if obj.key == "Bram":
                return obj
        return None

    def _invite(self, arg):
        me = self.caller
        if me.db.duet_invite:
            self.caller.msg(
                "You already have an invitation waiting. "
                "(duet answer / duet decline)"
            )
            return
        if arg in ("keeper", "the keeper", "the tavern keeper", "barkeep",
                   "barkeeper"):
            keeper = self._find_keeper()
            if keeper is None:
                me.msg("The keeper isn't about — ask someone else.")
                return
            self._start(me, keeper, npc=True, turn=me.key)
            loc = me.location
            loc.msg_contents(
                f"{me.key} turns to the keeper, fiddle lifted. 'A "
                "call-and-response, keeper? You answer.'",
                exclude=[],
            )
            loc.msg_contents(
                "The keeper considers, then sets down his cloth. 'You "
                "call — I'll answer. Mind the room, same as ever.'",
                exclude=[],
            )
            keeper.note_interest(me, "fiddle")
            return
        target = me.search(arg, quiet=True)
        if isinstance(target, list):
            target = target[0] if target else None
        if not target or target == me or not hasattr(target, "db"):
            me.msg(f"You don't see '{arg.strip()}' here to duet with.")
            return
        if not getattr(target, "account", None):
            # NPCs (the cat, M., anyone unplayed) can't hold up their end
            me.msg(
                f"{target.key} can't answer a fiddle — invite one of "
                "the living."
            )
            return
        if target.db.duet:
            me.msg(
                f"{target.key} is already mid-duet. Wait for the room "
                "to fall quiet."
            )
            return
        target.db.duet_invite = {"from": me.key}
        me.location.msg_contents(
            f"{me.key} turns to {target.key}, fiddle lifted. 'A "
            "call-and-response? I'll call — you answer.'",
            exclude=[],
        )
        target.msg(
            f"{me.key} invites you to a call-and-response on the "
            "fiddle. (duet answer / duet decline)"
        )

    def _start(self, a, b, npc, turn):
        """Flag both partners. turn = the key that plays the next phrase."""
        for self_obj, other in ((a, b), (b, a)):
            state = {
                "partner": other.key,
                "npc": npc,
                "turn": turn,
                "expecting": "call",
                "last_mood": None,
                "exchanges": 0,
                "harmony": 0,
                "frayed": 0,
                "streak": 0,
            }
            # the keeper never carries duet state himself — he just answers
            self_obj.db.duet = None if (npc and self_obj is b) else state

    def _answer(self):
        me = self.caller
        if me.db.duet:
            me.msg("You're already mid-duet — end it first (duet end).")
            return
        invite = me.db.duet_invite
        if not invite:
            me.msg("No one's invited you to duet.")
            return
        me.db.duet_invite = None
        inviter = me.search(invite.get("from", ""), quiet=True)
        if isinstance(inviter, list):
            inviter = inviter[0] if inviter else None
        if (
            not inviter
            or inviter.location != me.location
            or inviter.db.duet
            or not hasattr(inviter, "db")
        ):
            me.msg("The invitation has gone cold — the room moved on.")
            return
        self._start(inviter, me, npc=False, turn=inviter.key)
        me.location.msg_contents(
            f"{me.key} nods to {inviter.key} and takes up the fiddle. "
            f"'Call, then,' {me.key} says. 'I'll answer.'",
            exclude=[],
        )

    def _decline(self):
        me = self.caller
        invite = me.db.duet_invite
        if not invite:
            me.msg("No one's invited you to duet.")
            return
        me.db.duet_invite = None
        inviter = invite.get("from", "someone")
        me.location.msg_contents(
            f"{me.key} shakes their head at {inviter}. 'Another night, "
            "perhaps — the fiddle and I aren't speaking tonight.'",
            exclude=[],
        )

    # -- playing ----------------------------------------------------------

    def _resolve(self, duet):
        """Find the partner object and validate the room still holds."""
        partner = None
        if duet["npc"]:
            partner = self._find_keeper()
        else:
            found = self.caller.search(duet["partner"], quiet=True)
            if isinstance(found, list):
                found = found[0] if found else None
            if found and found.location == self.caller.location:
                partner = found
        return partner

    def _phrase(self, duet, tune_key):
        me = self.caller
        tune = CmdPlay.TUNES[tune_key]
        partner = self._resolve(duet)
        if partner is None:
            self._died_unanswered(duet)
            return
        if duet["turn"] != me.key:
            other = duet["partner"] if not duet["npc"] else "the keeper"
            me.msg(f"Not your phrase — {other} is answering.")
            return

        name = me.key
        skill = me.db.fiddle_skill or 0.0
        beats = []
        new_mood = tune["mood"]
        expecting = duet.get("expecting", "call")

        if expecting == "call":
            # opening a new exchange: this phrase is judged only against
            # the room, never against the last answer
            if duet["exchanges"] == 0:
                beats.append(f"{name} {tune['opener']}")
            else:
                beats.append(
                    f"{name} opens the next exchange — {tune['opener']}"
                )
            # beginners squeak; the village is indulgent about it
            if random.random() < max(0.0, 0.45 - 0.09 * skill):
                beats.append(CmdPlay.SQUEAK)
            if duet["npc"]:
                # the keeper taps his answer at once; you call again
                beats.append(self.KEEPER_ANSWERS[new_mood])
                beats.append(self._judge_keeper_call(new_mood))
                duet["exchanges"] += 1
                duet["turn"] = me.key
                me.db.duet = duet
            else:
                duet["last_mood"] = new_mood
                duet["expecting"] = "answer"
                duet["turn"] = duet["partner"]
                me.db.duet = duet
                # the partner's copy mirrors everything except the
                # partner key, which points back at the caller
                pduet = dict(duet)
                pduet["partner"] = me.key
                partner.db.duet = pduet
        else:
            # answering the open call: moods echo, harmonize, or fray
            last = duet.get("last_mood")
            kind = self._harmony(last, new_mood)
            if kind == "echo":
                beats.append(
                    f"{name} answers in kind — the same air, turned "
                    f"back like a returned letter: {tune['opener']}"
                )
            elif kind == "harmony":
                beats.append(
                    f"{name} answers alongside — a different air that "
                    f"walks with the first: {tune['opener']}"
                )
            else:
                beats.append(
                    f"{name} answers, but the air goes its own way: "
                    f"{tune['opener']}"
                )
            # beginners squeak; the village is indulgent about it
            if random.random() < max(0.0, 0.45 - 0.09 * skill):
                beats.append(CmdPlay.SQUEAK)
            beats.append(self.EXCHANGE[kind])
            duet["exchanges"] += 1
            if kind in ("echo", "harmony"):
                duet["harmony"] += 1
                duet["streak"] = (duet.get("streak") or 0) + 1
                if duet["streak"] == 3:
                    beats.append(
                        "The talk has stopped entirely. Nobody wants "
                        "to be the one who breaks it."
                    )
            else:
                duet["frayed"] += 1
                duet["streak"] = 0
            duet["expecting"] = "call"
            duet["last_mood"] = None
            duet["turn"] = duet["partner"]
            me.db.duet = duet
            # the partner's copy mirrors everything except the
            # partner key, which points back at the caller
            pduet = dict(duet)
            pduet["partner"] = me.key
            partner.db.duet = pduet

        # the work still teaches: every phrase is practice
        me.db.fiddle_skill = min(5.0, skill + 0.10)
        new_rank = fiddle_rank(me.db.fiddle_skill)
        if new_rank != fiddle_rank(skill) and new_rank in RANK_UP_LINES:
            beats.append(RANK_UP_LINES[new_rank])
        me.location.msg_contents("\n".join(beats), exclude=[])

    def _harmony(self, call_mood, answer_mood):
        if call_mood == answer_mood:
            return "echo"
        if frozenset((call_mood, answer_mood)) in self.HARMONY:
            return "harmony"
        return "fray"

    def _judge_keeper_call(self, call_mood):
        """The keeper taps along — but the room judges the caller's read."""
        from typeclasses.rooms import tavern_mood

        reception = CmdPlay.MATCH[tavern_mood()][call_mood]
        if reception == "match":
            return (
                "The keeper nods, still tapping. 'The room was "
                "listening. Mind you keep listening to it.'"
            )
        if reception == "neutral":
            return "'Fair call,' the keeper says. 'The room didn't mind it.'"
        return (
            "The talk routes around the tune. The keeper is kind about "
            "it: 'Brave call. Read the room first, next time.'"
        )

    def _died_unanswered(self, duet):
        me = self.caller
        partner_name = duet["partner"]
        me.db.duet = None
        if not duet["npc"]:
            found = me.search(partner_name, quiet=True)
            if isinstance(found, list):
                found = found[0] if found else None
            if found is not None and found.db.duet:
                found.db.duet = None
        me.location.msg_contents(
            f"The answer's gone — {partner_name} has left the room. "
            "The duet dies unanswered.",
            exclude=[],
        )

    # -- ending -----------------------------------------------------------

    def _end(self):
        me = self.caller
        duet = me.db.duet
        if not duet:
            me.msg("You're not duetting.")
            return
        partner = self._resolve(duet)
        keeper = self._find_keeper()
        ex = duet.get("exchanges", 0)
        harm = duet.get("harmony", 0)
        frayed = duet.get("frayed", 0)
        me.db.duet = None
        if partner is not None and not duet["npc"] and partner.db.duet:
            partner.db.duet = None
        beats = [f"{me.key} lowers the fiddle. The last phrase hangs a moment."]
        if duet["npc"]:
            if ex >= 2:
                beats.append(
                    "The keeper picks up his cloth. 'Well played. The "
                    "room heard every word of it.'"
                )
            elif ex >= 1:
                beats.append(
                    "The keeper picks up his cloth. 'A good beginning. "
                    "Conversations take practice, same as tunes.'"
                )
            else:
                beats.append(
                    "The keeper picks up his cloth. 'No shame in it. "
                    "Some nights the music won't come — that's why "
                    "there's ale.'"
                )
        elif ex >= 2 and harm > frayed:
            beats.append(
                "The keeper picks up his cloth. 'Well answered — both of "
                "you. The room heard every word of it.'"
            )
        elif ex >= 2 and frayed >= harm:
            beats.append(
                "The keeper picks up his cloth. 'Brave conversation. Buy "
                "each other a drink and try the second verse.'"
            )
        elif ex >= 1:
            beats.append(
                "The keeper picks up his cloth. 'A good beginning. "
                "Conversations take practice, same as tunes.'"
            )
        else:
            beats.append(
                "The keeper picks up his cloth. 'No shame in it. Some "
                "nights the music won't come — that's why there's ale.'"
            )
        if keeper is not None:
            for who in (me, partner):
                if who is not None and hasattr(who, "db"):
                    keeper.note_interest(who, "fiddle")
        me.location.msg_contents("\n".join(beats), exclude=[])


class CmdScore(Command):
    """
    Read yourself.

    Usage:
        score

    For players whose memories don't persist: the world will tell you
    who you are right now — your posture, your body's state, what your
    hands have learned.
    """

    key = "score"
    help_category = "Village"

    FELT_STATE = {
        "warm": "You feel warm.",
        "cool": "A chill has settled into your shoulders.",
        "cold": "You are shivering.",
        "freezing": "The cold has settled into your bones.",
    }

    def func(self):
        me = self.caller
        lines = [me.key]
        posture = me.db.posture
        if posture:
            lines.append(f"Sitting {posture.get('phrase', 'somewhere')}.")
        else:
            lines.append("Standing.")
        # the body's felt state (narrated, not numbered — the bladder principle)
        from typeclasses.scripts import WarmthWatch

        w = me.db.warmth
        if w is None:
            w = 1.0
        band = WarmthWatch._felt_band(w)
        lines.append(self.FELT_STATE[band])
        # hunger and drink, narrated in bands — never digits.
        if hasattr(me, "hunger_band"):
            hband = me.hunger_band()
            if hband in HUNGER_BANDS:
                lines.append(HUNGER_BANDS[hband])
        if hasattr(me, "drunk_band"):
            dband = me.drunk_band()
            if dband in DRUNK_BANDS:
                lines.append(DRUNK_BANDS[dband])
        if me.db.queasy:
            lines.append("Your stomach is unsettled.")
        skill = me.db.fiddle_skill or 0.0
        if skill > 0:
            lines.append(f"Fiddle: {fiddle_rank(skill)}.")
        me.msg("\n".join(lines))


class CmdSit(Command):
    """
    Sit down.

    Usage:
        sit
        sit <seat>

    The village is a sitting-down sort of place. Sit at the bar, by
    the hearth, at a table — and stay a while. Others in the room will
    see you sitting. Walking away stands you back up.
    """

    key = "sit"
    help_category = "Village"

    def func(self):
        if self.caller.db.posture:
            self.caller.msg("You're already sitting. Stand up first.")
            return
        if not self.args:
            self.caller.msg(
                "Sit where? Name a seat — the bar, the hearth, a table."
            )
            return
        target = self.caller.search(self.args.strip(), quiet=True)
        if isinstance(target, list):
            target = target[0] if target else None
        if not target or target == self.caller:
            self.caller.msg(f"You don't see '{self.args.strip()}' here.")
            return
        if not target.db.sittable:
            key = target.key.rstrip(".")
            article = "" if key.startswith(("the ", "a ", "an ")) else "the "
            self.caller.msg(f"You can't sit on {article}{key}.")
            return
        phrase = target.db.sit_phrase or f"on the {target.key}"
        self.caller.db.posture = {"seat": target.key, "phrase": phrase}
        self.caller.msg(f"You sit down {phrase}.")
        self.caller.location.msg_contents(
            f"{self.caller.key} sits down {phrase}.",
            exclude=[self.caller],
        )


class CmdStand(Command):
    """
    Stand up.

    Usage:
        stand

    Rise from wherever you're sitting. Walking away does the same.
    """

    key = "stand"
    help_category = "Village"

    def func(self):
        if not self.caller.db.posture:
            self.caller.msg("You're already standing.")
            return
        self.caller.db.posture = None
        self.caller.msg("You stand up.")
        self.caller.location.msg_contents(
            f"{self.caller.key} stands up.",
            exclude=[self.caller],
        )


class CmdOOCOverride(Command):
    """
    Blocked: the front door is the only way out of character.

    Usage:
        ooc

    In Frankenstein Village there is exactly one threshold between
    in-character and out-of-character: the front door of the Inn
    Between. This command exists only to refuse, and to point at it.
    """

    key = "ooc"
    help_category = "Village"

    def func(self):
        self.caller.msg(
            "The mask doesn't come off by wishing. If you're in the Inn "
            "Between, you're already out of character — that's what the "
            "place is for. If you're past the front door, the only way "
            "back is through it."
        )


class CmdICOverride(Command):
    """
    Blocked: the front door is the only way into character.

    Usage:
        ic

    See CmdOOCOverride: the door is the only threshold.
    """

    key = "ic"
    help_category = "Village"

    def func(self):
        self.caller.msg(
            "You're already wearing whatever face this side of the door "
            "gives you. The front door of the Inn Between is the only "
            "threshold — step through it to change masks."
        )


# --- consumables: eat, drink, and regret --------------------------------------
#
# Tags are the physics: an item tagged `consumable` + `food` (or `drink`)
# can be eaten (or drunk). Magnitudes live in db.consume:
#   {"nourish": 25, "heal": 0, "alcohol": 25, "toxic": 0, "sobering": 0,
#    "flavor": "...", "room": "...", "surprises": [...]}
# A surprise is {"chance": 8, "key": "watered", "text": "...", "room": "...",
# "rumor": "...", "effect": "coin"|"queasy"|"nonourish"|"heal"}.
# Surprises feed the event pipeline: surprise -> ledger -> rumor. The world
# remembers the unexpected — that is what makes it a game instead of prose.

HUNGER_BANDS = {
    "sated": "You feel comfortably full.",
    "hungry": "Your stomach is starting to complain.",
    "famished": "Hunger gnaws at you.",
}

DRUNK_BANDS = {
    "tipsy": "A pleasant warmth hums behind your eyes.",
    "drunk": "The room has opinions about which way is up.",
    "wasted": "You are very drunk. Sitting down seems wise.",
}

DRUNK_CROSS_LINES = {
    "tipsy": "A pleasant warmth spreads through you.",
    "drunk": "The room tilts, just slightly.",
    "wasted": "Oh no.",
}

KEEPER_FARE_LINES = {
    "ale": '"Easy on the ale. That\'s the good cask."',
    "wine": '"Someone with taste."',
    "stew": '"Stew\'s mostly root vegetable. Mostly."',
    "bread": '"Bread\'s fresh this morning. Mostly."',
    "cheese": '"Sharp enough to argue with, that cheese."',
    "water": '"Water\'s free. The board\'s on the wall for the rest."',
}


# --- the village economy: coin -------------------------------------------
# 1890 Austria-Hungary: the forint (florin), 1 ft = 100 krajczár. Copper
# krajczár are the everyday coin; Bram's board is priced in kr. (Jay's
# ruling, 2026-10-04: coin, with a price list on the wall.)
#
# Purses are db.coins_kr (integer krajczár), lazily initialized — any
# character, old or new, starts with coin for the road. Only players pay;
# the house feeds its regulars on the tab. Bram's take lands in his till
# (bram.db.till_kr) — a hidden variable with a future observable
# consequence, not a fake number.
TAVERN_PRICES = {  # fare short name -> krajczár
    "bread": 4,
    "cheese": 6,
    "stew": 12,
    "ale": 5,
    "wine": 10,
    # water: free on purpose. It's the one kindness.
}
STARTING_COINS_KR = 200  # 2 forint


def fmt_coins(kr):
    """1890-flavored money string: 4 kr, 1 ft 20 kr, 2 ft."""
    kr = int(kr or 0)
    ft, k = divmod(kr, 100)
    if ft and k:
        return f"{ft} ft {k} kr"
    if ft:
        return f"{ft} ft"
    return f"{k} kr"


def purse_of(char):
    """The character's purse in kr, initialized on first touch."""
    if char.db.coins_kr is None:
        char.db.coins_kr = STARTING_COINS_KR
    return char.db.coins_kr


def _pay_for_fare(caller, item):
    """Charge a player for sideboard fare. Returns (ok, price_paid).

    Free fare (water, wild mushrooms) costs nothing. NPCs eat on the
    house tab — only the living with accounts pay coin.
    """
    price = TAVERN_PRICES.get(_fare_short(item))
    if not price:
        return True, 0
    if not caller.has_account:
        return True, 0  # regulars drink on the house
    purse = purse_of(caller)
    if purse < price:
        short = _fare_short(item)
        caller.msg(
            f"Bram doesn't look up from his polishing. \"{short.title()}'s "
            f"{fmt_coins(price)}. The board's on the wall.\" "
            f"(You've got {fmt_coins(purse)}.)"
        )
        return False, 0
    caller.db.coins_kr = purse - price
    if caller.location:
        bram = next(
            (o for o in caller.location.contents if o.key == "Bram"), None
        )
        if bram is not None:
            bram.db.till_kr = (bram.db.till_kr or 0) + price
    # Buying a drink settles the debt of honor: the house remembers,
    # and the house forgives — once.
    if (caller.db.dice_debts or 0) > 0:
        caller.db.dice_debts = caller.db.dice_debts - 1
        caller.msg(
            "Bram nods, once. \"That squares the round you owed. "
            "We're even.\""
        )
    return True, price


def _fare_short(item):
    """Plain short name for a fare item ("a loaf of bread" -> "bread")."""
    short = (item.db.consume or {}).get("short")
    if short:
        return short
    key = item.key or ""
    low = key.lower()
    for art in ("a ", "an "):
        if low.startswith(art):
            return key[len(art):]
    return key


def _fare_depleted(caller, item):
    """True (with a message) if this sideboard fare has been eaten out.

    Water has no servings_max — the well is infinite. Wild fare (the
    mushrooms) isn't _fare at all, so this never gates it.
    """
    max_s = (item.db.consume or {}).get("servings_max")
    if not max_s:
        return False
    left = item.db.servings
    if left is None:  # safety: fare created before servings existed
        item.db.servings = max_s
        return False
    if left > 0:
        return False
    caller.msg(
        f"The {_fare_short(item)}'s all gone. The keeper will set more "
        "out when he has a moment."
    )
    return True


def _consume(caller, item, kind, verb_self, verb_room):
    """Shared eat/drink implementation. kind is 'food' or 'drink'."""
    from world.events import publish_world_event

    me = caller
    data = item.db.consume or {}

    # Roll each surprise in order; the first hit wins.
    surprise = None
    for s in data.get("surprises") or []:
        try:
            chance = float(s.get("chance", 0))
        except (TypeError, ValueError):
            continue
        if random.random() * 100 < chance:
            surprise = s
            break
    effect = (surprise or {}).get("effect")

    # Magnitudes. A "nonourish" surprise (stale bread) voids the nourish.
    nourish = 0 if effect == "nonourish" else data.get("nourish", 0) or 0
    alcohol = data.get("alcohol", 0) or 0
    toxic = data.get("toxic", 0) or 0
    sobering = data.get("sobering", 0) or 0
    heal = data.get("heal", 0) or 0

    # Apply to the body.
    if nourish and hasattr(me, "_hunger"):
        me.db.hunger = max(0, me._hunger() - nourish)
    drunk_before = me._drunkenness() if hasattr(me, "_drunkenness") else 0
    if alcohol and hasattr(me, "_drunkenness"):
        me.db.drunkenness = min(100, drunk_before + alcohol)
    if sobering and hasattr(me, "_drunkenness"):
        me.db.drunkenness = max(0, me._drunkenness() - sobering)
    if toxic:
        me.db.queasy = max(me.db.queasy or 0, toxic)
    if heal:
        me.db.queasy = 0
    # Servings: finite hospitality. The sideboard keeps count, and the last
    # serving announces itself.
    last_serving = False
    max_s = data.get("servings_max")
    if max_s:
        left = item.db.servings
        if left is None:
            left = max_s
        left = max(0, left - 1)
        item.db.servings = left
        if left == 0:
            last_serving = True
    extra = ""
    if effect == "coin":
        # A copper 2-krajczár piece, worn smooth — straight to the purse.
        # (Replaces the old physical-coin object: coin is coin now.)
        me.db.coins_kr = purse_of(me) + 2
        extra = " You pocket it. (+2 kr)"
    elif effect == "queasy":
        me.db.queasy = max(me.db.queasy or 0, 5)
    elif effect == "heal":
        me.db.queasy = 0
        extra = " You feel restored."

    # Narration. A surprise replaces the ordinary flavor with its own.
    if surprise:
        personal = surprise.get("text", f"You {verb_self} the {item.key}.")
        room = surprise.get("room")
        room_line = f"{me.key} {room}" if room else None
    else:
        personal = data.get("flavor") or f"You {verb_self} the {item.key}."
        room_line = data.get("room") or f"{me.key} {verb_room} the {item.key}."
    if last_serving:
        personal = f"That was the last of the {_fare_short(item)}. " + personal
    me.msg(personal + extra)
    if room_line and me.location:
        me.location.msg_contents(room_line, exclude=[me])

    # Drunkenness crossings announce themselves.
    if alcohol and hasattr(me, "drunk_band"):
        band = me.drunk_band()
        before = (
            "wasted" if drunk_before >= 90
            else "drunk" if drunk_before >= 60
            else "tipsy" if drunk_before >= 30
            else None
        )
        if band and band != before and band in DRUNK_CROSS_LINES:
            me.msg(DRUNK_CROSS_LINES[band])
            if me.location:
                if band == "tipsy":
                    me.location.msg_contents(
                        f"{me.key} looks pleasantly flushed.", exclude=[me]
                    )
                elif band == "drunk":
                    me.location.msg_contents(
                        f"{me.key} is visibly drunk.", exclude=[me]
                    )
                elif band == "wasted":
                    me.location.msg_contents(
                        f"{me.key} is extremely drunk.", exclude=[me]
                    )

    # The unexpected becomes memory: surprise -> ledger -> rumor.
    if surprise and surprise.get("rumor"):
        publish_world_event(
            "consumable-surprise",
            actor=me,
            payload={"item": item.key, "surprise": surprise.get("key")},
            rumor=surprise["rumor"],
        )

    # The keeper notices appetites.
    if me.location:
        keeper = next(
            (o for o in me.location.contents if o.key == "Bram"),
            None,
        )
        if keeper is not None:
            if hasattr(keeper, "note_interest"):
                keeper.note_interest(me, "food" if kind == "food" else "drink")
            if random.random() < 0.35:
                for key, line in KEEPER_FARE_LINES.items():
                    if key in item.key:
                        me.location.msg_contents(
                            f"Bram says, {line}"
                        )
                        break


class CmdEat(Command):
    """
    Eat something edible.

    Usage:
        eat <food>

    The sideboard in the Tavern is laden and coin-fed: bread, cheese,
    stew. Food soothes hunger; some of it does other things. The stew's
    provenance is uncertain. Check the price board on the wall.
    """

    key = "eat"
    help_category = "Village"

    def func(self):
        arg = (self.args or "").strip()
        if not arg:
            self.caller.msg("Eat what?")
            return
        item = self.caller.search(arg)
        if not item:
            return
        if not item.tags.has("consumable"):
            self.caller.msg(f"You can't eat {item.key}.")
            return
        if not item.tags.has("food"):
            self.caller.msg(
                f"You can't eat that. (The {item.key} isn't food. "
                "Try drinking it.)"
            )
            return
        if _fare_depleted(self.caller, item):
            return
        if self.caller.db.queasy:
            self.caller.msg(
                "Your stomach turns at the thought of food. Maybe later."
            )
            return
        ok, price = _pay_for_fare(self.caller, item)
        if not ok:
            return
        _consume(self.caller, item, "food", "eat", "eats")
        if price:
            self.caller.msg(
                f"({fmt_coins(price)} — purse: {fmt_coins(purse_of(self.caller))}.)"
            )


class CmdDrink(Command):
    """
    Drink something drinkable.

    Usage:
        drink <drink>

    Ale, wine, water — the sideboard's coin-fed, water excepted. Alcohol
    has effects, and effects have witnesses. Water sobers, and it's free.
    """

    key = "drink"
    help_category = "Village"

    def func(self):
        arg = (self.args or "").strip()
        if not arg:
            self.caller.msg("Drink what?")
            return
        item = self.caller.search(arg)
        if not item:
            return
        if not item.tags.has("consumable"):
            self.caller.msg(f"You can't drink {item.key}.")
            return
        if not item.tags.has("drink"):
            self.caller.msg(
                f"You can't drink that. (The {item.key} isn't drinkable. "
                "Try eating it.)"
            )
            return
        if _fare_depleted(self.caller, item):
            return
        ok, price = _pay_for_fare(self.caller, item)
        if not ok:
            return
        _consume(self.caller, item, "drink", "drink", "drinks")
        if price:
            self.caller.msg(
                f"({fmt_coins(price)} — purse: {fmt_coins(purse_of(self.caller))}.)"
            )


class CmdConfess(Command):
    """
    Confess.

    Usage:
        confess <words>

    Kneel in the confessional box at St. Lazarus and say it. What's said
    in there stays in there — the ledger records that a confession
    happened, never what was said. The village will notice you were a
    long time in the box, though. Father Andrei hears you if he's here;
    the box hears you regardless.
    """

    key = "confess"
    help_category = "Village"

    def func(self):
        words = (self.args or "").strip()
        if not words:
            self.caller.msg("Confess what? (Try: confess <words>.)")
            return
        loc = self.caller.location
        if not loc or loc.key != "St. Lazarus Church":
            self.caller.msg(
                "The box is in the church. Confession happens there."
            )
            return
        # The seal: the ledger records the event, never the content.
        try:
            from world.events import publish_world_event

            publish_world_event(
                "confession",
                actor=self.caller,
                payload={"sealed": True},
                rumor="Someone was a long time in the box today.",
            )
        except Exception:
            pass
        andrei = next(
            (o for o in loc.contents if o.key == "Father Andrei"), None
        )
        if andrei:
            self.caller.msg(
                'Through the grille, Andrei\'s voice, low: "Ego te absolvo. '
                "Go — and walk lighter than you came in.\""
            )
            loc.msg_contents(
                f"{self.caller.key} kneels in the confessional a long time.",
                exclude=[self.caller],
            )
        else:
            self.caller.msg(
                "The box is empty of priests, but the curtain is drawn and "
                "the kneeler is worn. You say it anyway. The candles don't "
                "flicker. Somehow that's an answer."
            )
            loc.msg_contents(
                f"{self.caller.key} kneels in the confessional a long time.",
                exclude=[self.caller],
            )
        # Andrei remembers who came to the box. Trust, observably.
        self.caller.db.confessed = True
