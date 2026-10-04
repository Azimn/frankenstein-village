"""
Frankenstein Village spike — the front door.

The front door is the most important object in the building: the
IC/OOC threshold. Crossing it in either direction fires the reminder
and records which side the character is on (char.db.ic_side).
"""
from evennia.objects.objects import DefaultExit


class Exit(DefaultExit):
    """Standard exit (kept for Evennia's default typeclass path)."""
    pass


class FrontDoorExit(DefaultExit):
    """
    An exit that knows which way the threshold runs. The destination
    room's ic/ooc tag decides the message.
    """

    def at_traverse(self, traversing_object, target_location, **kwargs):
        if traversing_object.has_account:
            if target_location.tags.has("ic", category="side"):
                traversing_object.db.ic_side = True
                traversing_object.msg(
                    "|yYou step through the front door.|n\n"
                    "You are in character now: a traveler in a strange "
                    "village. Act like one."
                )
            elif target_location.tags.has("ooc", category="side"):
                traversing_object.db.ic_side = False
                traversing_object.msg(
                    "|yYou step back through the front door.|n\n"
                    "The mask comes off. You are out of character — "
                    "this is the Inn Between."
                )
        super().at_traverse(traversing_object, target_location, **kwargs)
