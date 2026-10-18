"""Playable, spoiler-safe work leads for every currently supported Calling.

Every verb below is an ordinary player command implemented elsewhere.
This is career discoverability, not an alternate reward or scheduler.
"""

WORK = {
    "innkeep": (
        "At the Blood of the Vine: inspect the hearth, then use hearth "
        "tend when the fire has settled and delivered stock is available.",
        "Watch the Cold Hunter at Supper care case; coordinate with a Healer "
        "only if that unresolved need remains in the village.",
    ),
    "chronicler": (
        "At Market Lane: inspect the crooked market scale, use trade, and "
        "trade attest after an actual Merchant decision and Smith calibration.",
        "In the village: read chronicle and rumors; investigate conflicting "
        "testimony before making a documented entry.",
    ),
    "smith": (
        "At Market Lane: look market scale and use trade calibrate for a "
        "signed physical correction, once per village day.",
        "At the Square: examine north-square gas lamp; its repair is "
        "one-time and may already have been finished by a neighbor.",
    ),
    "healer": (
        "At the Square: investigate the pale well mushrooms; use assess "
        "on the real object, rather than trusting the public appearance.",
        "At the Tavern: inspect care needs; the Cold Hunter at Supper "
        "can change through actual help or through delay.",
    ),
    "merchant": (
        "At Market Lane: look market scale, then trade honor to keep "
        "goods moving or trade hold to suspend disputed distributions. "
        "A Smith can calibrate, and a Merchant can trade release.",
        "Help with a real commissioned firewood bundle through "
        "commission. At the Square, examine the noticeboard for needs.",
    ),
    "wanderer": (
        "Use survey to see the four current district checkpoints. "
        "Travel there, look at each actual clue, and use survey report.",
        "Examine the Riverside Path, churchyard, treeline, and market "
        "before forming route judgments; the daily reports are renewable.",
    ),
    "performer": (
        "At the Blood of the Vine: play, practice or perform a duet "
        "with a willing partner using the normal leisure commands.",
        "Read the public calendar, then invite neighbors to an in-world "
        "gathering through commons rather than claiming one occurred.",
    ),
    "detective": (
        "At the Old Stone Bridge: look plaque, inspect the river gauge "
        "on Riverside Path, and consider a provisional theory bridge.",
        "Use mystery bridge or mystery manor to compare public evidence. "
        "Claims and suspicions do not become facts just by being published.",
    ),
    "hound": (
        "Use survey and perform signed firsthand inspections in the "
        "churchyard, treeline, market and riverside districts.",
        "Talk to residents you physically encounter during their "
        "routines and compare their accounts against actual locations.",
    ),
}


def lines(role):
    if role not in WORK:
        return ["Choose a Calling with calling list to see professional leads."]
    return [
        "|wCurrent professional opportunities|n",
        *("* " + item for item in WORK[role]),
        "Professional work is finite or renewable depending on the situation; "
        "other players may have already changed its state. "
        "Your Calling does not grant hidden knowledge or free resources.",
    ]
