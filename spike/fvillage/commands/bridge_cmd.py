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

class CmdBridgeFitting(Command):
    """Physical Smith fittings with independent Wanderer and Hound sources.

    Usage: bridgefit | bridgefit forge span|cord | bridgefit install span|cord
           bridgefit test cord | bridgefit cross

    Wanderer: examine the Riverside gauge and survey gauge.
    Hound: examine the Northern Treeline cord and survey protect.
    """

    key = "bridgefit"
    aliases = ["routefitting"]
    help_category = "Village"

    def func(self):
        from world import route_fitting_work
        caller = self.caller
        room = getattr(caller, "location", None)
        if not room or not room.tags.has("ic", category="side"):
            caller.msg("Enter the village through the Inn's front door first.")
            return
        verb = (self.args or "").strip().lower()
        if verb in {"", "status", "help"}:
            caller.msg(route_fitting_work.status())
            return
        parts = verb.split()
        if len(parts) == 2 and parts[0] == "forge":
            result, error = route_fitting_work.forge(caller, parts[1])
            success = "You forge a finite physical " + parts[1] + " fitting."
        elif len(parts) == 2 and parts[0] == "install":
            result, error = route_fitting_work.install(caller, parts[1])
            success = "The original site is physically fitted from independent signed field evidence."
        elif verb == "test cord":
            result, error = route_fitting_work.test_cord(caller)
            success = "The Hound tests the local red-cord anchor, without claiming global safety."
        elif verb == "cross":
            result, error = route_fitting_work.cross(caller)
            success = "You cross the repaired inspection span to Riverside Path."
        else:
            caller.msg("Use bridgefit, bridgefit forge span|cord, "
                       "bridgefit install span|cord, bridgefit test cord, "
                       "or bridgefit cross.")
            return
        if error:
            caller.msg(error)
            return
        caller.msg(success + (
            f" Signed world event {result['event_id']}."
            if "event_id" in result else ""))
        if verb != "cross":
            caller.location.msg_contents(
                f"{caller.key} works at a physical village route fitting.",
                exclude=[caller])
