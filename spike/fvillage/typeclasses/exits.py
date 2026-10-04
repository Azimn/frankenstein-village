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


class PrivateRoomExit(DefaultExit):
    """
    The single shared 'up' exit in the Inn Common Room.

    One object, many rooms: at_traverse routes each traveler to their own
    account's private room (created on demand). This replaced the earlier
    per-account 'up' exits, which multiplied in the room's exit listing and
    made 'up' ambiguous ("More than one match for 'up'"). Privacy holds by
    construction — you can only ever arrive in your own room — so the
    traverse lock stays open.
    """

    def at_traverse(self, traversing_object, target_location, **kwargs):
        # Deferred import: accounts imports nothing from exits at module
        # level, but keep the dependency one-directional anyway.
        from typeclasses.accounts import ensure_private_room

        account = traversing_object.account
        if account is None:
            traversing_object.msg("You have no room of your own here.")
            return
        room = ensure_private_room(account)
        traversing_object.msg("You climb the stairs to your room.")
        super().at_traverse(traversing_object, room, **kwargs)


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
