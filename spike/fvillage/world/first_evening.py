"""Read-only first-evening Square guidance over verified, public state.

The renderer is pure. Callers must supply observations from the live Evennia
world; the guide must not reserve supplies, accept jobs, record discoveries, or
suggest actions whose prerequisites are exhausted.
"""
from __future__ import annotations


def render_square(
    *,
    wood_remaining,
    hearth_reserve,
    hearth_limit,
    carrying_firewood,
    active_profession,
    unreported_sites,
    lamp_status,
):
    """Present three grounded choices without changing world or player state."""
    capacity_known = (
        isinstance(hearth_reserve, int)
        and isinstance(hearth_limit, int)
        and hearth_limit > 0
    )
    rack_has_space = capacity_known and hearth_reserve < hearth_limit
    if carrying_firewood and rack_has_space:
        practical = (
            "You already carry a real firewood bundle. Go |weast|n to the "
            "Blood of the Vine and use |whearth deliver|n while its rack "
            "has room. No second bundle can be gathered while carrying one."
        )
    elif carrying_firewood:
        practical = (
            "You already carry a real bundle, but the Tavern rack cannot "
            "accept it now. Keep it or give it to a neighbor; use |whearth|n "
            "to check later. Do not gather a second bundle."
        )
    elif (
        isinstance(wood_remaining, int)
        and wood_remaining > 0
        and rack_has_space
    ):
        practical = (
            f"{wood_remaining} public firewood bundle(s) remain today, and "
            "the Tavern rack has room. Use |whearth gather|n here, walk "
            "|weast|n to the Tavern, then use |whearth deliver|n to change "
            "the shared reserve. Other residents can use what you deliver."
        )
    else:
        practical = (
            "The firewood delivery route cannot be completed right now "
            "(stock or rack capacity is unavailable). Use |whearth|n to "
            "inspect the current supply and |wcommons|n for public requests; "
            "do not assume an old commission remains open."
        )

    if active_profession:
        career = (
            f"Your current Calling is {active_profession.title()}. Use "
            "|wcalling work|n to see its actual professional activities. "
            "Different work may be available after a neighbor acts."
        )
    else:
        career = (
            "No Calling is required to explore or help. Use |wcalling list|n "
            "to inspect the ten professions. If one fits, use "
            "|wcalling choose <name>|n, then |wcalling work|n to see "
            "its available professional routes."
        )

    if unreported_sites:
        site = str(unreported_sites[0])
        investigation = (
            f"Today's district survey still needs firsthand observation at "
            f"{site}. Use |wsurvey|n to check the public route, travel to "
            "an unreported landmark, examine its physical clue, then "
            "|wsurvey report|n while standing there. Your signed report "
            "survives logout. Rumors are not automatically evidence."
        )
    else:
        investigation = (
            "No unreported survey checkpoint is currently available. "
            "For independent investigation, visit the Old Stone Bridge, "
            "examine its plaque, compare the Riverside Path's river gauge, "
            "and use |wmystery bridge|n. You may hold a provisional theory "
            "without declaring it true."
        )

    profession_heading = (
        "|wYour profession|n" if active_profession
        else "|wChoose a profession|n"
    )
    return "\n".join(
        (
            "|wA first lead: the village square|n",
            "|wEveryday life|n: " + practical,
            "|wA shared village need or its aftermath:|n " + str(lamp_status),
            profession_heading + ": " + career,
            "|wFollow a mystery|n: " + investigation,
            "You can return to the Square's |wcommons|n and save a "
            "private intention with |wagenda note = <words>|n.",
        )
    )
