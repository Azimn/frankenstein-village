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
            caller.msg(
                "|wA first lead: the village square|n\n"
                "Go |weast|n to the Blood of the Vine and use |wrumors|n "
                "to find a story worth following. The |wcommons|n board "
                "holds requests, offers, and gatherings left by real visitors.\n"
                "|wcalling list|n describes available professions. "
                "Choose one with |wcalling choose <name>|n, or keep "
                "exploring without one. |wjournal|n only shows what "
                "you have personally discovered.\n"
                "|wA shared village need:|n "
                + lamp_lead(caller)
                + "\n|wA practical action you can take alone:|n "
                "Use |whearth|n to check the public wood supply. "
                "If there is wood and the Tavern rack has space, "
                "|whearth gather|n here, go |weast|n to the Tavern, "
                "and use |whearth deliver|n. That changes a shared "
                "physical reserve even when no neighbor is online. "
                "You can also use |wsurvey|n for firsthand district "
                "investigation without taking a calling. "
                "|wcommission|n offers cooperative work when someone "
                "else is available."
            )
        elif place == "The Lamp Shop":
            caller.msg(
                "|wA first lead: the Lamp Shop|n\n"
                "Examine what the shop offers. "
                + lamp_shop_lead(caller)
            )
        elif place == "St. Lazarus Church":
            caller.msg(
                "|wA first lead: St. Lazarus|n\n"
                "Look about the church and use |wcalendar|n for "
                "the public village schedule. Go |weast|n to the "
                "square, then |weast|n again to the Tavern for "
                "rumors. |wjournal|n remembers only discoveries "
                "you have actually made."
            )
        elif place in {
            "St. Lazarus Churchyard", "The Northern Treeline",
            "Market Lane", "Riverside Path", "The Old Stone Bridge",
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
                    "A civic material table holds finite construction kits "
                    "for the bridge mystery; inspect it, then use "
                    "|wbridgework collect preserve|n or "
                    "|wbridgework collect display|n to carry a real kit. "
                    "Talk to anyone actually present. North returns to "
                    "the Lamp Shop."
                ),
                "Riverside Path": (
                    "Examine the river gauge. West returns to the Tavern, "
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
                    if place != "The Old Stone Bridge" else ""
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
