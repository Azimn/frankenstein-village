"""Pure first-person rendering of existing player-character bodily state.

The modeled character has hunger, warmth, drunkenness and queasiness.
This creates NO new drives, physiological variables, hidden-world knowledge,
AI privileges or proof of subjective consciousness.
"""
from __future__ import annotations

def bounded(value, *, low=0.0, high=100.0, default=0.0):
    try:
        if value is None or isinstance(value, bool):
            return default
        number = float(value)
        if number != number or number == float("inf") or number == float("-inf"):
            return default
        return max(low, min(high, number))
    except (ValueError, TypeError, OverflowError):
        return default


def perception(*, hunger=50, warmth=1.0, drunkenness=0, queasy=0,
               seated=False, place=None):
    """One current snapshot, descriptive rather than a second state store.

    No environmental weather, wounds, movement penalty or other character's
    experiences are inferred from these personal variables.
    """
    h = bounded(hunger, default=50.0)
    w = bounded(warmth, low=0.0, high=1.0, default=1.0)
    d = bounded(drunkenness)
    q = bounded(queasy)
    hunger_band = ("famished" if h >= 80 else "hungry" if h >= 60
                   else "sated" if h <= 29 else "settled")
    warmth_band = ("warm" if w >= 0.75 else "cool" if w >= 0.5
                   else "cold" if w >= 0.25 else "freezing")
    drink_band = ("wasted" if d >= 90 else "drunk" if d >= 60
                  else "tipsy" if d >= 30 else "clear")
    queasy_band = "unsettled" if q > 0 else "settled"

    first = []
    if h >= 80:
        first.append(
            "I feel a persistent hollow pressure beneath my ribs. Hunger keeps "
            "interrupting my thoughts; even while I attend to something else, "
            "my body draws my attention back toward finding something to eat."
        )
    elif h >= 60:
        first.append(
            "There is an empty, tugging sensation low in my stomach. "
            "I can continue what I am doing, but I keep noticing that I need a meal."
        )
    elif h <= 29:
        first.append(
            "My stomach is comfortably settled. Food is not pressing for "
            "my attention just now."
        )
    else:
        first.append(
            "My stomach is quiet enough that I can give my attention "
            "to the village instead of my next meal."
        )

    first.append({
        "warm": ("Warmth settles through my shoulders and hands. "
                 "I am not fighting the cold right now."),
        "cool": ("A thin chill rests across my shoulders. My fingers feel "
                 "a little less willing to uncurl; shelter would be welcome."),
        "cold": ("I can feel myself shivering. My hands want to draw close "
                 "to my body, and the idea of a sheltered room is hard to ignore."),
        "freezing": ("The cold feels lodged beneath my clothes, down through "
                     "my arms into my fingers. I want to find shelter "
                     "before I try to settle into anything else."),
    }[warmth_band])

    if q > 0:
        first.append(
            "My stomach turns unexpectedly. A small wave of queasiness "
            "tightens my throat, complicating the simple thought of eating."
        )
    if drink_band != "clear":
        first.append({
            "tipsy": ("There is an unusual looseness in my balance. "
                       "My attention lingers a moment behind my movements."),
            "drunk": ("I have to take an extra moment to place myself "
                       "in the room; my balance is less certain than it should be."),
            "wasted": ("My sense of balance is unreliable. "
                        "I need to move carefully and let the haze pass."),
        }[drink_band])
    if seated:
        first.append(
            "The seat supports my weight. Sitting changes my posture, "
            "but it does not by itself supply food or cure anything."
        )

    relief = []
    if hunger_band in ("hungry", "famished"):
        if place == "The Blood of the Vine":
            relief.append(
                "Look at the actual Tavern sideboard and your carried food. "
                "Eat a serving that still exists; bread, cheese, stew and "
                "carried homemade soup have separate physical stock."
            )
        else:
            relief.append(
                "The Blood of the Vine serves physical food when its stock is "
                "available; inspect the serving before eating. Hunger is "
                "uncomfortable here, not damaging."
            )
    if warmth_band != "warm":
        relief.append(
            "Move to a real sheltered room such as the Inn or Blood of the Vine; "
            "the existing warmth clock can raise your body's warmth there."
        )
    if q > 0:
        relief.append(
            "Nausea can ease gradually with movement or a real cup of free "
            "water from the Tavern. It does not instantly cure illness; "
            "food waits until the stomach settles."
        )
    if drink_band != "clear":
        relief.append(
            "The village's free water and passing travel time can ease "
            "intoxication; check the actual drink and its effects."
        )
    if not relief:
        relief.append(
            "There is no pressing body need in these represented states. "
            "Keep exploring, work, or rest as you choose."
        )

    return {
        "body_model": "represented_character_sensations_not_ai_biology",
        "bands": {
            "hunger": hunger_band, "warmth": warmth_band,
            "intoxication": drink_band, "stomach": queasy_band,
        },
        "first_person": first,
        "possible_relief": relief,
    }


def deep_lines(percept):
    lines = ["|wA moment inside your character's body|n"]
    lines.extend(percept["first_person"])
    lines.append("|wWhat might help, in this actual village:|n")
    lines.extend("- " + text for text in percept["possible_relief"])
    lines.append(
        "These are simulated character sensations from current state, "
        "not a claim about the player's biology or hidden world truth."
    )
    return lines
