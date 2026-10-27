"""Open civic project: tend the actual public Square warming brazier."""
from evennia import Command


class CmdBrazier(Command):
    """Share physical firewood to create public warmth in the Village Square.

    Usage:
        brazier
        brazier light
        brazier feed

    Get a real bundle at the Square woodpile with hearth gather. The first
    bundle lights the public brazier for six village hours; another visitor
    may feed an existing fire for four more, with a twelve-hour horizon cap.
    An active fire helps the SAME existing character warmth state recover
    outdoors. This is open to any player regardless of Calling.
    """

    key = "brazier"
    aliases = ["square fire"]
    help_category = "Village"

    def func(self):
        from world import square_brazier
        caller = self.caller
        loc = getattr(caller, "location", None)
        if (not loc or loc.key != "Village Square"
                or not loc.tags.has("ic", category="side")):
            caller.msg(
                "Go to the in-character Village Square and inspect its "
                "public brazier. Fire cannot be tended from another room."
            )
            return
        raw = (self.args or "").strip().lower()
        if raw in ("", "status", "look"):
            caller.msg(square_brazier.status_lines(caller))
            return
        result, error = square_brazier.act(caller, raw)
        if error:
            caller.msg(error)
            return
        verb = "light" if result["mode"] == "light" else "feed"
        caller.msg(
            f"You {verb} the village's shared iron brazier with a real "
            "bundle of firewood. The bundle is consumed and the public "
            f"fire now has {result['remaining']} village hour(s) of warmth "
            f"remaining (signed world event {result['event_id']}). "
            "Any visitor standing here can benefit from the fire."
        )
        if caller.location:
            caller.location.msg_contents(
                f"{caller.key} tends the public brazier; the Square grows warmer.",
                exclude=[caller],
            )
