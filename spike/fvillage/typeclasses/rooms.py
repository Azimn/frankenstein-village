"""
Frankenstein Village spike — room typeclasses.

Tags drive the front-door mechanic: rooms tagged "ic" are in-character
(the village), rooms tagged "ooc" are the Inn Between (backstage).
"""
from evennia.objects.objects import DefaultRoom


def tavern_mood():
    """The room's mood, derived — the MUD states it the way it states the
    weather. This is the prosthetic sense the attunement loop reads:
    humans infer it from the line in `look`, AI players read the same
    value. Rain outside makes the hearth-room warmer by contrast; fog
    presses at the windows; the hour does the rest."""
    from evennia.scripts.models import ScriptDB

    try:
        hour = ScriptDB.objects.get(db_key="village_time").db.hour
    except Exception:
        hour = 20
    try:
        weather = ScriptDB.objects.get(db_key="village_weather").db.state
    except Exception:
        weather = "clear"
    if weather == "rain":
        return "warm"
    if weather == "fog":
        return "tense"
    if 18 <= hour <= 22:
        return "rowdy"
    if hour >= 23 or hour <= 4:
        return "low"
    return "warm"


class Room(DefaultRoom):
    """Standard room (kept for Evennia's default typeclass path)."""
    pass


class SpikeRoom(DefaultRoom):
    """Base room for the spike. Tagged ic or ooc at build time.

    Rooms carry persistent senses (db.sense_air, db.sense_sound): the
    village is not visual-only. Air is appended to the description;
    sound answers the `listen` command. Weather appends its own line
    via db.weather_sense.
    """

    def get_display_desc(self, looker=None, **kwargs):
        desc = super().get_display_desc(looker, **kwargs)
        air = self.db.sense_air
        if air:
            desc = f"{desc}\n{air}"
        weather = self.db.weather_sense
        if weather:
            desc = f"{desc} {weather}"
        overlays = dict(self.db.scheduled_overlays or {})
        for _key in sorted(overlays):
            line = overlays[_key]
            if line:
                desc = f"{desc}\n{line}"
        return desc


class PrivateRoom(SpikeRoom):
    """One account's private OOC room at the Inn Between.

    The exit lock is the ordinary access path. This hook is the second
    boundary: even a direct move with hooks enabled cannot place another
    connected player in the room.
    """

    def at_pre_object_receive(self, arriving_object, source_location, **kwargs):
        account = getattr(arriving_object, "account", None)
        if account:
            owner_id = self.db.owner_account_id
            if account.id != owner_id and not account.is_superuser:
                arriving_object.msg("That room is private.")
                return False
        return super().at_pre_object_receive(
            arriving_object, source_location, **kwargs
        )


class CommonRoom(SpikeRoom):
    """The Inn Between common room. M. greets arrivals."""

    def at_object_receive(self, moved_obj, source_location, **kwargs):
        super().at_object_receive(moved_obj, source_location, **kwargs)
        # Only greet actual player characters, not objects being moved around.
        if not moved_obj.has_account:
            return
        for obj in self.contents:
            if obj.key == "M." and hasattr(obj, "greet"):
                obj.greet(moved_obj)
                break


class TavernRoom(SpikeRoom):
    """The Tavern. The keeper greets arrivals, IC side."""

    def get_display_desc(self, looker=None, **kwargs):
        desc = super().get_display_desc(looker, **kwargs)
        mood = tavern_mood()
        line = {
            "warm": "The talk is easy, and the hearth is doing its work.",
            "low": "The talk is low and tired tonight.",
            "rowdy": "The room is loud with evening talk.",
            "tense": "The talk keeps dying and starting again.",
        }[mood]
        from world.community_hearth import public_hearth_line
        return f"{desc}\n{line}\n{public_hearth_line()}"

    def at_object_receive(self, moved_obj, source_location, **kwargs):
        super().at_object_receive(moved_obj, source_location, **kwargs)
        if not moved_obj.has_account:
            return
        for obj in self.contents:
            if obj.key == "Bram" and hasattr(obj, "greet"):
                obj.greet(moved_obj)
                break


class LampShopRoom(SpikeRoom):
    """The Lamp Shop. Lucian greets arrivals — always delighted."""

    def at_object_receive(self, moved_obj, source_location, **kwargs):
        super().at_object_receive(moved_obj, source_location, **kwargs)
        if not moved_obj.has_account:
            return
        for obj in self.contents:
            if obj.key == "Lucian DeVille" and hasattr(obj, "greet"):
                obj.greet(moved_obj)
                break
