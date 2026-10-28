"""Playable, spoiler-safe work leads for every currently supported Calling.

Every verb below is an ordinary player command implemented elsewhere.
This is career discoverability, not an alternate reward or scheduler.
"""

WORK = {
    "innkeep": (
        "Work at the shared Tavern soup pot: soup prep turnip thyme "
        "reserves real pantry stock, soup simmer cooks a transferable edible "
        "bowl, soup notebook preserves experiments. Soup quality changes "
        "when a neighbor has tended the hearth.",
        "At the Blood of the Vine: inspect the hearth, then use hearth "
        "tend when the fire has settled and delivered stock is available.",
        "Watch the Cold Hunter at Supper care case; coordinate with a Healer "
        "only if that unresolved need remains in the village.",
    ),
    "chronicler": (
        "After a Hound physically protects the Northern Treeline cord, "
        "visit the Village Square board and use survey caution to publish "
        "a source-linked warning. It records uncertainty, not hazard truth.",
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
        "At St. Lazarus Church a patient comes to the staffed clinic every "
        "village day. Use clinic assess to record a firsthand finding; "
        "clinic prepare makes real transferable linen dressings, and "
        "clinic treat rest or compress offers consequential care with a "
        "signed, restart-safe history. After personally assessing the visitor, "
        "use clinic request records to obtain consent before opening private "
        "notes with clinic records. Public clinic status omits those notes.",
        "At the Square: investigate the pale well mushrooms; use assess "
        "on the real object, rather than trusting the public appearance.",
        "At the Tavern: inspect care needs; the Cold Hunter at Supper "
        "can change through actual help or through delay.",
    ),
    "merchant": (
        "At Market Lane use soup procure for a real crate of roots; "
        "carry or transfer it to the Blood of the Vine, then soup deliver "
        "to restock the working kitchen's finite pantry.",
        "At Market Lane: look market scale, then trade honor to keep "
        "goods moving or trade hold to suspend disputed distributions. "
        "A Smith can calibrate, and a Merchant can trade release.",
        "Help with a real commissioned firewood bundle through "
        "commission. At the Square, examine the noticeboard for needs.",
    ),
    "wanderer": (
        "Collect actual sealed ferry-post parcels in Market Lane with courier collect. "
        "Carry or give them to another person for courier deliver at Riverside Path. "
        "The limited daily supply and signed ferry manifest persist.",
        "At the Northern Treeline, examine the frayed red cord and use "
        "survey passability to record whether a real caution marker was "
        "present when you visited. This is a dated route judgment, not "
        "a guarantee of safety.",
        "Use survey to see the four current district checkpoints. "
        "Travel there, look at each actual clue, and use survey report.",
        "Examine the Riverside Path, churchyard, treeline, and market "
        "before forming route judgments; the daily reports are renewable.",
    ),
    "performer": (
        "At the Blood of the Vine: use stage rehearse ballad or reel, "
        "then stage perform the rehearsed piece. Other real visitors can "
        "stage witness during that hour; the signed performance remains in "
        "the public Tavern history.",
        "Also play, practice or perform a duet with a willing partner using "
        "the normal leisure commands.",
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
        "At the Northern Treeline, examine the frayed red cord and use "
        "survey protect to tie its loose end into a real caution marker. "
        "The same day cannot be signed twice. On a later village day, "
        "inspect the cord again and re-tighten a verified older marker.",
        "Use survey and perform signed firsthand inspections in the "
        "churchyard, treeline, market and riverside districts.",
        "Talk to residents you physically encounter during their "
        "routines and compare their accounts against actual locations.",
    ),
    "mystic": (
        "At St. Lazarus Churchyard, inspect the weathered grave marker. "
        "Use mystic to examine the guild's evidence and methods; an "
        "unusual gravestone event is possible on a particular night.",
        "Meet Beatrice Harcourt or Mirela Dobre while they are present "
        "and ask about their research. With first-hand evidence, a Mystic "
        "can use mystic study measure or mystic study vigil at the site.",
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
