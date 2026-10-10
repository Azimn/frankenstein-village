"""Bram's grounded tavern talk: public facts, not a quest feed.

No private rumor handles, hidden object properties, NPC internal state, or
account substrate information enters this conversation. A spoken lead points
the player toward ordinary IC investigation and cooperation; it does not
perform actions, grant Calling authority, or fabricate quests.
"""

from world.situations import (
    LAMP_REPAIR_ID,
    TAVERN_COLD_CARE_ID,
    get_situation,
)


def _stage(case):
    if not case or case.get("state") == "dormant":
        return "unavailable"
    if case.get("state") == "aftermath":
        return "done" if case.get("branch") in {"repaired", "cared_for"} else "closed"
    changes = dict(case.get("objective_mutations") or {})
    return changes


def lamp_state():
    case = get_situation(LAMP_REPAIR_ID)
    return _stage(case)


def care_state():
    case = get_situation(TAVERN_COLD_CARE_ID)
    return _stage(case)


def lamp_talk():
    stage = lamp_state()
    if stage == "done":
        return (
            "That north-square lamp's burning. Two sets of hands, at least: "
            "the Smith who knew what failed and the Merchant who had the "
            "part. I hear the light's better for seeing your mistakes by."
        )
    if stage == "closed":
        return (
            "The north-square lamp stayed dark after they missed their "
            "chance. That doesn't make the fault disappear. Ask in the "
            "square before anyone promises you a simple fix."
        )
    if stage == "unavailable":
        return (
            "There's a lamp by the square that's worth looking at. "
            "Don't take my word for it. Go west and see."
        )
    if not stage.get("smith_diagnosis"):
        return (
            "One lamp in the square is dark. Not the whole street, mind. "
            "A Smith ought to look at the fitting first. Buying brass "
            "before you know what's cracked is how merchants get rich."
        )
    if not stage.get("merchant_procurement"):
        return (
            "The Smith found the crack. Now it's a Merchant's turn to "
            "find a collar at the Lamp Shop. The square's west of here; "
            "the shop's south from there."
        )
    return (
        "They've got the collar now, and the lamp's still dark. "
        "Someone has to fit it. Takes a Smith's hands, not a toast. "
        "The work's at the square, west of here."
    )


def care_talk():
    stage = care_state()
    if stage == "done":
        return (
            "Silas has had his supper and his care. Someone checked him "
            "properly, someone else spent a hot bowl on him. "
            "I'd call that a good evening, even if he wouldn't."
        )
    if stage == "closed":
        return (
            "Silas got warm eventually, with or without our help. "
            "I'm not going to pretend yesterday's supper can be served "
            "again. There'll be another cold evening."
        )
    if stage == "unavailable":
        return (
            "Nobody's asked me to keep a meal back for Silas. "
            "Ask him how the road treated him; I only know the bar."
        )
    if not stage.get("healer_assessment"):
        return (
            "Silas came in soaked and shaking. He can sit by the fire, "
            "but I'd rather have a Healer look at him before I start "
            "calling stew a cure. He's here in the Tavern."
        )
    if not stage.get("innkeep_care"):
        return (
            "The Healer's seen Silas. Good. Now an Innkeep needs to "
            "spend a bowl of stew on him. A real bowl, from the pot; "
            "you can't warm a man with paperwork."
        )
    return (
        "The care's on record. Ask after Silas instead of trying "
        "to serve the same bowl twice."
    )


def work_talk():
    """Prefer an active civic need; fall back to genuine social play."""
    lamp = lamp_state()
    if isinstance(lamp, dict):
        return (
            "If you're itching to be useful, see that dark lamp in the "
            "square. It's west of here. A Smith and a Merchant will both "
            "be needed; ask me about the lamp if you want the gossip. "
            "If there's no partner about, leave a note on the Commons board."
        )
    care = care_state()
    if isinstance(care, dict):
        return (
            "Silas came in cold enough to make the hearth seem mean. "
            "A Healer and an Innkeep can help, if they're still in time. "
            "Ask me about Silas; you can speak to him yourself."
        )
    return (
        "Don't ask me for a list of jobs. Ask the people. "
        "There's a Commons board in the square: one traveler can "
        "leave a need, another can answer it tomorrow. "
        "Or find a story here and follow it out the door."
    )


def rumor_talk():
    return (
        "There's talk enough to feed a winter. Type rumors if you want "
        "to hear the public stories, but a story isn't a witness. "
        "Ask who told it before you take it to the Chronicle."
    )


def first_talk():
    return (
        "New to my bar, are you? The beer can wait. "
        "If you want to find your feet, ask me about work, "
        "the lamp, or Silas. I know what reaches this counter; "
        "you'll have to go and see the rest yourself."
    )


def returning_topic(topic):
    if topic == "lamp":
        stage = lamp_state()
        if stage == "done":
            return (
                "That lamp you asked about? Burning again. "
                "The square looks different after an answer."
            )
        if stage == "closed":
            return "That lamp you asked after never got its repair in time."
        return "Still keeping an eye on the square lamp?"
    if topic == "silas":
        stage = care_state()
        if stage == "done":
            return "Silas got warm, if that's what you came back to ask."
        if stage == "closed":
            return "Silas got through his cold evening; the hour passed."
        return "Silas is still on your mind, eh?"
    if topic == "work":
        return "Still looking for something useful to do? The board's in the square."
    if topic == "rumors":
        return "Still turning over those stories? Ask who first told them."
    return None
