"""Diegetic, spoiler-safe orientation for a player's first village session.

The guide never reads undiscovered situations or private rumor state. It
only describes publicly accessible rooms and commands already available.
"""

from evennia import Command
from world.newcomer_leads import lamp_lead, lamp_shop_lead, tavern_care_lead


class CmdGuide(Command):
    """Find the next useful step without revealing hidden world state.

    Usage:
        guide
        next

    A route from the Inn to the village's rumor, profession, and
    collaboration loops. This does not accept quests or change world state.
    """

    key = "guide"
    aliases = ["next", "wayfinder"]
    help_category = "Village"

    def func(self):
        caller = self.caller
        room = caller.location
        if room is None:
            caller.msg("You have no location. Ask a builder to restore your room.")
            return

        if room.tags.has("ooc", category="side"):
            room_name = room.key
            if room_name == "Inn Hallway":
                route = "Go |wsouth|n through the front door to enter the village."
            elif room_name == "Inn Common Room":
                route = (
                    "Go |weast|n into the hallway, then |wsouth|n "
                    "through the front door."
                )
            else:
                route = (
                    "Leave your private room with |wdown|n, then go "
                    "|weast|n and |wsouth|n through the front door."
                )
            caller.msg(
                "|wA way into the village|n\n"
                "The Inn is out of character. In the Common Room you can "
                "|wtalk M.|n before crossing the front door. Your calling "
                "is optional; |wcalling list|n shows what is available.\n"
                + route
                + "\nOnce outside, use |wguide|n again for a starting lead."
            )
            return

        place = room.key
        if room.tags.has("tavern", category="place"):
            caller.msg(
                "|wA first lead: the Blood of the Vine|n\n"
                "Use |wrumors|n to hear what is circulating here. Pick a "
                "numbered story and use |wrumors R<number>|n to trace it. "
                "Do not mistake a telling for proven fact. "
                "If you're newly arrived, |wtalk Bram|n and "
                "|wask Bram about work|n, |wask Bram about commons|n, "
                "or |wask Bram about news|n. A notice can outlast "
                "your visit: |wcommons follow <number>|n keeps it "
                "on this mask's list for next time.\n"
                "An Innkeep can make real, edible meals at the shared pot: "
                "try |wsoup|n, |wsoup prep turnip thyme|n, then "
                "|wsoup simmer|n. Musicians may use |wstage|n to rehearse "
                "and perform actual public sets, which other visitors "
                "can witness. These are renewable jobs, even when the "
                "lamp or care cases have ended.\\n"
                "Speak with someone nearby, or use "
                "|wretell <person> R<number>|n to pass the story on. "
                "|wjournal|n records situations your mask actually "
                "encountered.\n"
                + tavern_care_lead(caller)
                + "\nFor a solo contribution, go |wwest|n to the Square, "
                "check |whearth|n and use |whearth gather|n when wood is "
                "available. Return |weast|n and use |whearth deliver|n "
                "here if the rack has space. The bundle stays in the "
                "shared reserve. An Innkeep can use |whearth tend|n, "
                "while |wcommission|n offers cooperative delivery.\n"
                "For a lasting public account, "
                "a Chronicler can examine "
                "|wchronicle|n and file testimony from a known rumor."
            )
        elif place == "Village Square":
            # Read authoritative public state, without reserving or spending.
            from world import community_hearth, route_surveys, route_work
            from world.callings import active_calling
            from world.discoveries import LANDMARKS
            from world.first_evening import render_square
            from world.situations import LAMP_REPAIR_ID, get_situation

            lamp_case = get_situation(LAMP_REPAIR_ID)
            hearth = community_hearth._status()
            source = hearth["woodpile"]
            rack = hearth["hearth"]
            survey_square = route_work._square()
            if survey_square:
                day, _hour = route_work._day_hour()
                surveys = route_surveys.refresh(
                    survey_square.db.daily_route_survey, day
                )
                open_sites = tuple(
                    LANDMARKS[ident]["room"]
                    for ident in route_surveys.SITES
                    if ident not in surveys["reports"]
                )
            else:
                open_sites = None
            caller.msg(render_square(
                wood_remaining=(
                    source["remaining"] if source is not None else None
                ),
                hearth_reserve=(rack["reserve"] if rack is not None else None),
                hearth_limit=community_hearth.hearth_state.MAX_RESERVE,
                carrying_firewood=bool(community_hearth._carried(caller)),
                active_profession=active_calling(caller),
                unreported_sites=open_sites,
                lamp_status=lamp_lead(caller),
                lamp_case_state=(lamp_case or {}).get("state"),
            ))
        elif place == "The Lamp Shop":
            caller.msg(
                "|wA first lead: the Lamp Shop|n\n"
                "Examine what the shop offers. "
                + lamp_shop_lead(caller)
            )
        elif place == "St. Lazarus Church":
            caller.msg(
                "|wA first lead: St. Lazarus|n\n"
                "Look about the church and use |wclinic|n to inspect its "
                "real treatment cot and daily patient. An active Healer "
                "can |wclinic assess|n, |wclinic prepare|n a physical "
                "linen compress, and |wclinic treat rest|n or "
                "|wclinic treat compress|n. The clinic and its history "
                "persist after departure. Use |wcalendar|n for "
                "the public village schedule. Go |weast|n to the "
                "square, then |weast|n again to the Tavern for "
                "rumors. |wjournal|n remembers only discoveries "
                "you have actually made."
            )
        elif place in {
            "St. Lazarus Churchyard", "The Northern Treeline",
            "Market Lane", "Riverside Path", "The Old Stone Bridge",
            "The Market Workshop",
        }:
            routes = {
                "St. Lazarus Churchyard": (
                    "Examine the grave marker. East returns to St. Lazarus, "
                    "while north reaches the treeline."
                ),
                "The Northern Treeline": (
                    "Examine the frayed cord; no road leads farther into "
                    "the forest yet. Hunters sometimes pass this edge in "
                    "daylight; if one is present, use |wtalk <name>|n or "
                    "|wask <name> about <topic>|n. South returns to "
                    "the churchyard."
                ),
                "Market Lane": (
                    "Examine the market scale and its slate prices. "
                    "Daytime sellers and craft workers have routines along "
                    "this street, and the Chronicler visits her office. "
                    "The crooked market scale is also a profession lead: "
                    "Merchants, Smiths and Chroniclers can use |wtrade|n "
                    "to affect how the market operates. "
                    "A civic material table holds finite construction kits "
                    "for the bridge mystery; inspect it, then use "
                    "|wbridgework collect preserve|n or "
                    "|wbridgework collect display|n to carry a real kit. "
                    "A Wanderer can collect a real sealed ferry-post parcel "
                    "with |wcourier collect|n, carry it toward the river, "
                    "and use |wcourier deliver|n on Riverside Path. "
                    "A Merchant may procure tangible kitchen crates with "
                    "|wsoup procure|n; carrying one north, north and east "
                    "to the Tavern supports the shared kitchen. "
                    "The public Smith's Workshop is now open eastward. "
                    "Inspect its repair bench and use |wworkshop|n for "
                    "an actual daily forge-and-install commission. "
                    "A forged hinge must be physically carried back "
                    "and installed here, not merely promised. "
                    "Talk to anyone actually present. North returns to "
                    "the Lamp Shop."
                ),
                "The Market Workshop": (
                    "Examine the public smithing bench to see the finite "
                    "iron stock and signed repair docket. Active Smiths use "
                    "|wworkshop forge|n to make a real hinge; take it west "
                    "to Market Lane and use |wworkshop install|n, or hand it "
                    "to another player. Forge stock renews daily but "
                    "installed repairs are recorded permanently."
                ),
                "Riverside Path": (
                    "Examine the river gauge. Wanderers and their neighbors "
                    "can deposit an actual carried ferry-post parcel using "
                    "|wcourier deliver|n; |wcourier|n shows the signed route history. "
                    "West returns to the Tavern, "
                    "and east leads to the bridge."
                ),
                "The Old Stone Bridge": (
                    "Examine the empty plaque socket. Compare observations with "
                    "|wmystery bridge|n, then offer an unresolved interpretation "
                    "using |wtheory bridge = <words>|n. After examining "
                    "the plaque, compare the river gauge one room west, "
                    "then use |wbridgework|n for a physical civic response. "
                    "West returns to the "
                    "Riverside Path. The night watch is often at "
                    "the bridge late in the evening; you can speak "
                    "to the watchman if he is actually on patrol."
                ),
            }
            caller.msg(
                "|wA quiet lead: " + place + "|n\n"
                + routes[place]
                + (
                    "\nThis place is on the shared daily route. After "
                    "|wlooking at its clue|n, use |wsurvey report|n to "
                    "sign one real inspection, then |wsurvey|n to see "
                    "which districts still need a neighbor."
                    if place in {
                        "St. Lazarus Churchyard", "The Northern Treeline",
                        "Market Lane", "Riverside Path",
                    } else ""
                )
                + "\nUse |wdiary|n to write your own account, "
                "or return to the Tavern and discuss what you saw."
            )
        else:
            caller.msg(
                "|wA way forward|n\n"
                "Use |wlook|n, |wlisten|n, and |wexamine <thing>|n "
                "to investigate this place. Check |wjournal|n for "
                "leads you actually found. Return to the village "
                "square and the Blood of the Vine to share what "
                "you learned, or use |whelp|n for commands."
            )
