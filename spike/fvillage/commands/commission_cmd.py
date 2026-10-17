"""Public command for cooperative, renewable village supplies."""
from evennia import Command


class CmdCommission(Command):
    """Take part in a shared daily Tavern commission.

    Usage:
        commission
        commission pledge
        commission deliver

    Gather one real firewood bundle in the Square, pledge it, then hand it to
    someone else. That person's account must carry the same bundle into the
    Tavern to complete the work. Completed delivery fills the real hearth rack.
    """

    key = "commission"
    aliases = ["commissions", "workorder"]
    help_category = "Village"

    def func(self):
        from world import civic_work
        caller = self.caller
        room = getattr(caller, "location", None)
        if room is None or not room.tags.has("ic", category="side"):
            caller.msg("Village commissions are in-character work. Cross the Inn door first.")
            return
        action = (self.args or "").strip().lower()
        if action in {"", "status", "help"}:
            caller.msg(civic_work.status_lines())
            return
        if action in {"pledge", "supply"}:
            result, error = civic_work.pledge(caller)
            if error:
                caller.msg(error)
                return
            caller.msg(
                "You pledge your physical firewood bundle to today's Tavern commission. "
                "Give this exact bundle to another player. They must take it east into "
                "the Blood of the Vine and use |wcommission deliver|n. "
                "You still own the bundle until you hand it over."
            )
            caller.location.msg_contents(
                f"{caller.key} signs the public firewood pledge.", exclude=[caller],
            )
            return
        if action in {"deliver", "finish"}:
            result, error = civic_work.deliver(caller)
            if error:
                caller.msg(error)
                return
            caller.msg(
                f"Commission complete with {result['supplier_mask']}. "
                "You stack the pledged wood into the Tavern's real shared rack. "
                f"It now holds {result['reserve']} bundles. "
                "An Innkeep can use |whearth tend|n when the fire settles."
            )
            caller.location.msg_contents(
                f"{caller.key} completes a neighbor's firewood commission; "
                "the public Tavern rack gains one bundle.",
                exclude=[caller],
            )
            return
        caller.msg("Use: commission | commission pledge | commission deliver")
