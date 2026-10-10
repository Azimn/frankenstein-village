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
                + "\nFor a lasting public account, a Chronicler can examine "
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
        else:
            caller.msg(
                "|wA way forward|n\n"
                "Use |wlook|n, |wlisten|n, and |wexamine <thing>|n "
                "to investigate this place. Check |wjournal|n for "
                "leads you actually found. Return to the village "
                "square and the Blood of the Vine to share what "
                "you learned, or use |whelp|n for commands."
            )
