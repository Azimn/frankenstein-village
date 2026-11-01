"""Physical and renewable village post route."""
from evennia import Command


class CmdCourier(Command):
    """Carry a real ferry-post parcel from Market Lane to the riverside.

    Usage:
        courier
        courier collect
        courier consign   (Merchant, Market Lane)
        courier accept    (Wanderer, Market Lane)
        courier deliver

    Wanderers collect ordinary mail from the finite daily postbag. Merchants
    can consign a real parcel from the SAME finite stock; a different Wanderer
    must accept and deliver that freight. Ordinary mail retains its solo path.
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
        elif raw == "consign":
            result, error = courier_work.consign(self.caller)
            if error:
                self.caller.msg(error)
                return
            self.caller.msg(
                f"You seal actual Merchant freight in Market Lane (world event "
                f"{result['event_id']}). {result['remaining']} parcels remain "
                "in the shared postbag. A different Wanderer must accept it."
            )
        elif raw == "accept":
            result, error = courier_work.accept_freight(self.caller)
            if error:
                self.caller.msg(error)
                return
            self.caller.msg(
                f"You accept the Merchant's physical freight (world event "
                f"{result['event_id']}, consignment "
                f"{result['consignment_event_id']}). Carry it to Riverside Path."
            )
        elif raw == "deliver":
            result, error = courier_work.deliver(self.caller)
            if error:
                self.caller.msg(error)
                return
            self.caller.msg(
                f"The actual parcel enters the ferry-post register "
                f"(world event {result['event_id']}, collection "
                f"{result['source_event_id']}). A signed receipt now names "
                "this delivery in the public ferry-post register. "
                "It is no longer in your inventory."
            )
        else:
            self.caller.msg(
                "Use courier | courier collect | courier consign | "
                "courier accept | courier deliver."
            )
            return
        self.caller.location.msg_contents(
            f"{self.caller.key} completes a real ferry-post {raw} action.",
            exclude=[self.caller],
        )
