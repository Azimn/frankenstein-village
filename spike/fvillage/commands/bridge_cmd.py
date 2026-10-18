"""Player-facing investigation and care of the missing bridge plaque."""
from evennia import Command


class CmdBridgeWork(Command):
    """Make a public bridge response from firsthand evidence.

    Usage:
        bridgework
        bridgework collect preserve  (at the Market Lane supply table)
        bridgework collect display
        bridgework preserve          (at the bridge, with real kit)
        bridgework display
        bridgework check

    Inspect the missing bridge plaque and river gauge in person before
    deciding. Later visits can inspect and maintain the physical result.
    """

    key = "bridgework"
    aliases = ["bridge-inquiry"]
    help_category = "Village"

    def func(self):
        from world import bridge_work
        caller = self.caller
        room = getattr(caller, "location", None)
        if not room or not room.tags.has("ic", category="side"):
            caller.msg("Enter the village through the Inn's front door first.")
            return
        verb = (self.args or "").strip().lower()
        if verb in {"", "status", "help"}:
            caller.msg(bridge_work.status_lines(caller))
            return
        if verb in {"collect preserve", "collect display"}:
            choice = verb.split()[1]
            result, error = bridge_work.collect(caller, choice)
            if error:
                caller.msg(error)
                return
            caller.msg(
                "You take a real " + choice + " kit from the Market Lane "
                "supply table. Carry it to the Old Stone Bridge or give "
                "it to another traveler. "
                f"{result['remaining']} matching kits remain today."
            )
            caller.location.msg_contents(
                f"{caller.key} takes a bridge-work kit from the public table.",
                exclude=[caller],
            )
            return
        if verb not in {"preserve", "display", "check"}:
            caller.msg(
                "Use: bridgework | bridgework collect preserve | "
                "bridgework collect display | bridgework preserve | "
                "bridgework display | bridgework check"
            )
            return
        result, error = bridge_work.act(caller, verb)
        if error:
            caller.msg(error)
            return
        caller.msg(
            f"Signed world event {result['event_id']}. "
            + (
                "You inspected the established bridge response. "
                if verb == "check"
                else "The village bridge has physically changed. "
            )
            + result["line"]
        )
        caller.location.msg_contents(
            f"{caller.key} attends to the missing plaque site.",
            exclude=[caller],
        )
