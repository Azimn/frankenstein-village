"""Publicly observable, state-aware starting leads; no hidden case flags revealed.

This adapter never completes actions, selects a mask's profession, discovers
private mystery evidence or writes quest progress. It reads shared public case
outcomes and translates them into an ordinary playable next step.
"""

from world.callings import active_calling
from world.situations import (
    LAMP_REPAIR_ID,
    TAVERN_COLD_CARE_ID,
    get_situation,
)


def lamp_lead(mask):
    case = get_situation(LAMP_REPAIR_ID)
    if not case or case.get("state") == "dormant":
        return (
            "Examine the north-square gas lamp in person. "
            "The |wcommons|n board remembers offers after logout."
        )
    if case.get("state") == "aftermath":
        if case.get("branch") == "repaired":
            return (
                "The north-square lamp is burning again because neighbors "
                "completed the repair. This is no longer an open job. "
                "Use |wrepair|n to read the public account, or "
                "|wcommons|n to find another need."
            )
        return (
            "The lamp's repair window closed without a successful repair. "
            "Use |wrepair|n for its public outcome, or |wcommons|n "
            "for another way to help."
        )

    changes = dict(case.get("objective_mutations") or {})
    role = active_calling(mask)
    if not changes.get("smith_diagnosis"):
        step = (
            "The north-square gas lamp is dark. A Smith here can use "
            "|wrepair diagnose north-square gas lamp|n. "
            "A Merchant will then have to bring the replacement."
        )
        if role is None:
            step += " See |wcalling list|n before choosing a profession."
        elif role != "smith":
            step += " Invite a Smith to investigate."
    elif not changes.get("merchant_procurement"):
        step = (
            "A Smith identified the damage. A Merchant can go "
            "|wsouth|n to the Lamp Shop and use |wrepair procure|n, "
            "spending one actual unit of stock."
        )
        if role != "merchant":
            step += " Ask a Merchant to take the next step."
    else:
        step = (
            "The part has been procured. A Smith at the square can use "
            "|wrepair finish north-square gas lamp|n to change the "
            "public lamp's physical state."
        )
        if role != "smith":
            step += " Find a Smith to finish the work."
    return (
        step + "\nCoordinate with real neighbors: "
        "|wcommons post need = The square lamp needs a neighbor's help.|n "
        "You can also |wcommons|n to read or answer somebody's note. "
        "Use |wrepair|n to inspect shared progress."
    )


def tavern_care_lead(mask):
    case = get_situation(TAVERN_COLD_CARE_ID)
    if not case or case.get("state") == "dormant":
        return "Listen to |wrumors|n or ask Bram who needs help."
    if case.get("state") == "aftermath":
        return (
            "Silas Crowe's care case has ended. Use |wcare|n for the "
            "outcome, not to repeat a spent action. Other travelers "
            "may still need a reply on |wcommons|n."
        )
    changes = dict(case.get("objective_mutations") or {})
    role = active_calling(mask)
    if not changes.get("healer_assessment"):
        step = (
            "Silas Crowe is cold and wet. A Healer present with him "
            "can use |wcare assess Silas Crowe|n."
        )
        if role != "healer":
            step += " Invite a Healer: this is not a solo job."
    elif not changes.get("innkeep_care"):
        step = (
            "A Healer recorded what Silas needs. An Innkeep here can use "
            "|wcare serve Silas Crowe|n to spend a real serving of stew."
        )
        if role != "innkeep":
            step += " Ask an Innkeep to follow through."
    else:
        return "Care contributions were recorded. Use |wcare|n for the outcome."
    return step + " Use |wcare|n to see the shared state."
