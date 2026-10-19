"""Physical and renewable village post route."""
from evennia import Command


class CmdCourier(Command):
    """Carry a real ferry-post parcel from Market Lane to the riverside.

    Usage:
        courier
        courier collect
        courier deliver

    Wanderers collect from the market's finite daily postbag. Anyone carrying
    their real parcel may deliver it. The signed ferry register persists.
    """

    key = "courier"
    aliases = ["postroute", "ferrypost"]
    help_category = "Village"

    def func(self):
        from world import courier_work
        raw = (self.args or "").strip().lower()
        if raw in ("", "status", "help"):
            self.caller.msg(courier_work.status(self.caller))
            return
        if raw == "collect":
            result, error = courier_work.collect(self.caller)
            if error:
                self.caller.msg(error)
                return
            self.caller.msg(
                f"You collect an actual sealed ferry-post parcel (world event "
                f"{result['event_id']}). There are {result['remaining']} "
                f"parcels left in today's market postbag. Carry or give it."
            )
        elif raw == "deliver":
            result, error = courier_work.deliver(self.caller)
            if error:
                self.caller.msg(error)
                return
            self.caller.msg(
                f"The actual parcel enters the ferry-post register "
                f"(world event {result['event_id']}, collection "
                f"{result['source_event_id']}). It is no longer in your inventory."
            )
        else:
            self.caller.msg("Use courier | courier collect | courier deliver.")
            return
        self.caller.location.msg_contents(
            f"{self.caller.key} completes a real ferry-post {raw} action.",
            exclude=[self.caller],
        )
