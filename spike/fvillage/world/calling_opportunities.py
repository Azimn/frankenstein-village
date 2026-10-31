"""Playable, spoiler-safe work leads for every currently supported Calling.

Every verb below is an ordinary player command implemented elsewhere.
This is career discoverability, not an alternate reward or scheduler.
"""

WORK = {
    "innkeep": (
        "Work at the shared Tavern soup pot: soup prep turnip thyme "
        "reserves real pantry stock, soup simmer cooks a transferable edible "
        "bowl, soup notebook preserves experiments. Soup quality changes "
        "when a neighbor has tended the hearth. A Merchant can give you a "
        "physical kitchen roots crate; soup accept verifies its signed source "
        "and receives it into the pantry. soup deliver remains a solo fallback.",
        "At the Blood of the Vine: inspect the hearth, then use hearth "
        "tend when the fire has settled and delivered stock is available.",
        "Watch the Cold Hunter at Supper care case; coordinate with a Healer "
        "only if that unresolved need remains in the village.",
    ),
    "chronicler": (
        "At Market Lane: inspect the crooked market scale, use trade, and "
        "trade audit after a signed Merchant decision, or trade attest "
        "after a Merchant decision and Smith calibration.",
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
        "At St. Lazarus Church, clinic receive inspects and accepts a "
        "real Merchant-sourced linen parcel, adding two finite dressings "
        "to the shared cabinet. A separate Merchant must supply it.",
        "At St. Lazarus Church a patient comes to the staffed clinic every "
        "village day. Use clinic assess to record a firsthand finding; "
        "clinic prepare makes real transferable linen dressings, and "
        "clinic treat rest or compress offers consequential care with a "
        "signed, restart-safe history. After personally assessing the visitor, "
        "use clinic request records to obtain consent before opening private "
        "notes with clinic records. Public clinic status omits those notes.",
        "After completing real treatment at St. Lazarus, look at the cot "
        "and use clinic invite to ask whether the visitor wants voluntary "
        "music. This is separate from permission for private case notes.",
        "At the Square: investigate the pale well mushrooms; use assess "
        "on the real object, rather than trusting the public appearance.",
        "At the Tavern: inspect care needs; the Cold Hunter at Supper "
        "can change through actual help or through delay.",
    ),
    "merchant": (
        "At Market Lane, clinic procure withdraws one finite sealed linen "
        "parcel per village day. Carry it to St. Lazarus Church for a "
        "different Healer to use clinic receive; the shared cabinet gains "
        "stock only after clinical acceptance.",
        "At Market Lane use soup procure for a real crate of roots; "
        "carry it to the Blood of the Vine for soup deliver, or give it "
        "to a different Innkeep account for a signed soup accept receipt. "
        "Both routes consume the physical crate and restock finite pantry.",
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
        "After a Healer has treated a real St. Lazarus visitor and signed "
        "a consented invitation, go to the Church, look at the clinic cot "
        "and use clinic music. Companionship is not a medical cure.",
        "Also play, practice or perform a duet with a willing partner using "
        "the normal leisure commands.",
        "Read the public calendar, then invite neighbors to an in-world "
        "gathering through commons rather than claiming one occurred.",
    ),
    "detective": (
        "At Market Lane, inspect the physical crooked scale and use trade inspect "
        "after a different account signs Smith calibration. This records limited "
        "physical evidence, not guilt or an invented culprit.",
        "At Market Lane: inspect the real crooked market scale. After a Merchant " 
        "has signed trade hold, use trade investigate to open an independent " 
        "source-linked inquiry. A Merchant may answer with trade rebut.",
        "At the Old Stone Bridge: look plaque, inspect the river gauge "
        "on Riverside Path, and consider a provisional theory bridge.",
        "Use mystery bridge or mystery manor to compare public evidence. "
        "Claims and suspicions do not become facts just by being published.",
    ),
    "hound": (
        "At the Northern Treeline, examine the frayed red cord and use "
        "survey protect to tie its loose end into a real caution marker. "
        "The physical change is one-time; it cannot be repeated after "
        "someone else has already protected the route.",
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
