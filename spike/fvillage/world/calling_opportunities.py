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
        "At the communal soup pot, inspect its lid hinge. Use soup restrict "
        "to suspend unsafe player simmering until an independent Smith "
        "installs a real Workshop-forged hinge with soup repair.",
        "After a real Performer show and signed audience witness at the Tavern, "
        "cook a real soup bowl and use stage cater during the same village hour "
        "to place it in public service. No show or audience means no demand claim.",
        "Watch the Cold Hunter at Supper care case; coordinate with a Healer "
        "only if that unresolved need remains in the village.",
    ),
    "chronicler": (
        "At Market Lane: inspect the crooked market scale, use trade, and "
        "trade audit after a signed Merchant decision, or trade attest "
        "after a Merchant decision and Smith calibration.",
        "In the village: read chronicle and rumors; investigate conflicting "
        "testimony before making a documented entry.",
        "At Village Square, use mystery bridge publish after an independent "
        "Detective signs a firsthand examination of the real bridge plaque. "
        "The bulletin is evidence-limited and does not identify a culprit.",
    ),
    "smith": (
        "At the Church, inspect the clinic cot. A Workshop-forged physical "
        "hinge can brace its worn folding rail with clinic brace; an "
        "independent Healer must certify its clinical suitability.",
        "At Market Lane: look market scale and use trade calibrate for a "
        "signed physical correction, once per village day.",
        "At the Tavern: inspect the communal soup pot. If an Innkeep "
        "has restricted unsafe simmering, carry a physical Workshop-forged "
        "hinge there and use soup repair. This spends the actual fitting.",
        "At the Square: examine north-square gas lamp; its repair is "
        "one-time and may already have been finished by a neighbor.",
    ),
    "healer": (
        "At the Church cot, inspect its folding rail. After a real Smith "
        "installs a fitting and you assess today\'s patient, clinic certify "
        "approves reinforced rest; clinic treat supported then uses it.",
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
        "If a Hound has firsthand signed a treeline caution, use stage adapt "
        "indoor or stage adapt cancel to decide how the real show proceeds.",
        "After a Healer has treated a real St. Lazarus visitor and signed "
        "a consented invitation, go to the Church, look at the clinic cot "
        "and use clinic music. Companionship is not a medical cure.",
        "After a witnessed show, an Innkeep can bring a real cooked soup bowl "
        "and use stage cater during the same hour; the stage preserves the "
        "signed food and attendance receipts.",
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
        "At the Old Stone Bridge, look plaque, then mystery bridge examine "
        "to sign a physical evidence record for an independent Chronicler.",
    ),
    "hound": (
        "At the Northern Treeline, examine the frayed red cord and use "
        "survey protect to tie its loose end into a real caution marker. "
        "The same cord can be re-tightened after a new firsthand "
        "inspection on a later village day, never twice in one day.",
        "After signing survey protect on the real treeline cord, travel to "
        "the Blood of the Vine and use stage warn before a public show. "
        "An independent Performer decides whether to play indoors or cancel.",
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
