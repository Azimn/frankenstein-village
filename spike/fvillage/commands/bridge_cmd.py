"""Player-facing investigation and care of the missing bridge plaque."""
from evennia import Command


class CmdBridgeWork(Command):
    """Make a public bridge response from firsthand evidence.

    Usage:
        bridgework
        bridgework preserve
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
        if verb not in {"preserve", "display", "check"}:
            caller.msg(
                "Use: bridgework | bridgework preserve | "
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
