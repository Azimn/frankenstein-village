"""Physical Smith forging and community market installation."""
from evennia import Command


class CmdWorkshop(Command):
    """Work with finite iron and real market fittings.

    Usage:
        workshop
        workshop forge
        workshop install

    An active Smith forges one physical hinge at the Market Workshop east of
    Market Lane, spending one of its daily iron offcuts. A carrier, including
    a different player, can install the actual item on Market Lane.
    """

    key = "workshop"
    aliases = ["marketrepair", "smithwork"]
    help_category = "Village"

    def func(self):
        from world import workshop_work
        caller = self.caller
        raw = (self.args or "").strip().lower()
        if raw in ("", "help", "status"):
            caller.msg(workshop_work.status(caller))
            return
        if raw == "forge":
            result, error = workshop_work.forge(caller)
            if error:
                caller.msg(error)
                return
            count = result["remaining"]
            stock_phrase = "iron offcut remains" if count == 1 else "iron offcuts remain"
            caller.msg(
                f"You forge a real transferable iron market hinge "
                f"(world event {result['event_id']}). "
                f"{count} {stock_phrase} at the public bench. "
                "Carry it west to Market Lane, or give it to a neighbor."
            )
        elif raw == "install":
            result, error = workshop_work.install(caller)
            if error:
                caller.msg(error)
                return
            caller.msg(
                f"You physically install the forged market hinge "
                f"(signed world event {result['event_id']}, "
                f"forging source {result['source_event_id']}). "
                "The carried hinge has been consumed, and the public "
                "market repair board now records the outcome."
            )
        else:
            caller.msg("Use workshop | workshop forge | workshop install.")
            return
        if caller.location:
            caller.location.msg_contents(
                f"{caller.key} completes actual workshop {raw} work.",
                exclude=[caller],
            )
