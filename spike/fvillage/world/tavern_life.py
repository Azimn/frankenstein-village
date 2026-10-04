"""Ambient life for the Blood of the Vine.

The room mid-conversation: regulars gossip, toast, brood, eat and drink
through the same consumable pipeline players use. The surprise table can
hit them too — Vasile getting the watered ale announces it to the room.

run_beat(say=None) performs one beat. `say` defaults to the tavern room's
msg_contents; pass a collector for testing.
"""

import random

TAVERN_KEY = "The Blood of the Vine"

MAGDA_GOSSIP = [
    "Magda leans in conspiratorially. \"You know what I heard about the "
    "stew? Thursday. That's all I'm saying.\"",
    "Magda: \"Lucian's lamps. My cousin bought one. Never been warmer. "
    "Her *dreams*, though.\"",
    "Magda: \"The new shop. OPENING SOON, it says. I mentioned it to "
    "Lucian. He smiled *wrong*.\"",
    "Magda, to no one in particular: \"Bram's V. I know what it stands "
    "for. (She knows.)\"",
]

VASILE_TOASTS = [
    "Old Vasile raises his ale. \"To the ones that stay buried.\"",
    "Old Vasile: \"The ground's soft tonight. Soft ground tells stories.\"",
    "Old Vasile stares into his ale like it's a window. It isn't. He "
    "drinks anyway.",
]

JANOS_BROOD = [
    "J\u00e1nos checks the straps on his kit bag. Still packed. Always packed.",
    "J\u00e1nos: \"Father Andrei says pray. I say patrol. We drink on the "
    "difference.\"",
    "J\u00e1nos turns his ale in slow circles, watching the foam. Thinking "
    "about catacombs, probably.",
]

CROSS_TALK = [
    "Magda nudges Vasile. \"Tell the one about the Manor.\" Vasile: \"No.\"",
    "Vasile squints at J\u00e1nos's kit bag. \"Packed. Always packed. You Hounds.\"",
    "J\u00e1nos: \"Magda. The lamp-seller. What do you know?\" Magda: \"Too "
    "nice. Next question.\"",
    "Bram, without looking up: \"Easy on the ale. That's the good cask.\"",
    "Vasile: \"Bram. The V.\" Bram: \"Drink your ale, old man.\"",
    "Magda: \"J\u00e1nos, love, you're brooding again.\" J\u00e1nos: \"It's "
    "called vigilance.\"",
]


def _tavern():
    from evennia.utils import search
    found = [
        o for o in search.search_object(TAVERN_KEY) if o.key == TAVERN_KEY
    ]
    return found[0] if found else None


def _regulars(tavern):
    return [
        o for o in tavern.contents
        if o.is_typeclass("typeclasses.characters.TavernRegular", exact=True)
    ]


def _bram(tavern):
    for o in tavern.contents:
        if o.key == "Bram":
            return o
    return None


def _beat_gossip(regulars, bram, say):
    say(random.choice(MAGDA_GOSSIP))
    return "gossip"


def _beat_toast(regulars, bram, say):
    say(random.choice(VASILE_TOASTS))
    return "toast"


def _beat_brood(regulars, bram, say):
    say(random.choice(JANOS_BROOD))
    return "brood"


def _beat_cross(regulars, bram, say):
    say(random.choice(CROSS_TALK))
    return "cross"


def _beat_consume(regulars, bram, say):
    """A regular eats or drinks — through the real pipeline."""
    from evennia.utils import search as _s  # noqa: F401 (import side effects)
    tavern = _tavern()
    if not tavern or not regulars:
        return "consume-skipped"
    who = random.choice(regulars)
    stew = next(
        (o for o in tavern.contents if o.key == "a bowl of stew"), None
    )
    ale = next(
        (o for o in tavern.contents if o.key == "a tankard of ale"), None
    )
    pick = random.choice([p for p in (stew, ale) if p is not None])
    if pick is None:
        return "consume-skipped"
    from commands.village_cmds import _consume
    kind = "food" if pick.tags.has("food") else "drink"
    _consume(who, pick, kind, "eat" if kind == "food" else "drink",
             "eats" if kind == "food" else "drinks")
    return "consume"


def _beat_bram(regulars, bram, say):
    say("Bram wipes the same spot on the bar. The spot is winning.")
    return "bram"


BEATS = [
    (3, _beat_gossip),
    (2, _beat_toast),
    (2, _beat_brood),
    (3, _beat_cross),
    (2, _beat_consume),
    (1, _beat_bram),
]


def run_beat(say=None):
    """Perform one ambient beat in the Blood of the Vine. Returns its kind."""
    tavern = _tavern()
    if tavern is None:
        return "no-tavern"
    if say is None:
        say = tavern.msg_contents
    regulars = _regulars(tavern)
    bram = _bram(tavern)
    if not regulars:
        return "no-regulars"
    total = sum(w for w, _ in BEATS)
    roll = random.uniform(0, total)
    acc = 0.0
    for weight, fn in BEATS:
        acc += weight
        if roll < acc:
            return fn(regulars, bram, say)
    return BEATS[-1][1](regulars, bram, say)
