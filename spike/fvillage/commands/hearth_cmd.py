"""Village hearth: gather physical wood, deliver it, tend shared warmth."""

from evennia import Command


class CmdHearth(Command):
    """Tend a shared, renewable Tavern fire without automatic rewards.

    Usage:
        hearth
        hearth gather
        hearth deliver
        hearth tend

    The square woodpile has a finite daily supply. Anyone may gather and
    carry one actual bundle; an active Innkeep must tend the Tavern fire.
    Heat lasts eight village hours. No new quest is assigned or claimed.
    """

    key = "hearth"
    aliases = ["firewood"]
    help_category = "Village"

    def func(self):
        from world import community_hearth
        caller = self.caller
        location = getattr(caller, "location", None)
        if not location or not location.tags.has("ic", category="side"):
            caller.msg("This is village work. Cross the Inn's front door first.")
            return
        action = (self.args or "").strip().lower()
        if not action:
            caller.msg(community_hearth.status_lines())
            return
        methods = {
            "gather": community_hearth.gather,
            "collect": community_hearth.gather,
            "deliver": community_hearth.deliver,
            "tend": community_hearth.tend,
            "stoke": community_hearth.tend,
        }
        if action not in methods:
            caller.msg("Use: hearth | hearth gather | hearth deliver | hearth tend")
            return
        result, error = methods[action](caller)
        if error:
            caller.msg(error)
            return
        if action in {"gather", "collect"}:
            caller.msg(
                "You lift a real bundle of split firewood from the square pile. "
                f"{result['remaining']} bundles remain today. "
                "Carry it east to the Tavern and use |whearth deliver|n, "
                "or give it to another traveler."
            )
            caller.location.msg_contents(
                f"{caller.key} takes a bundle of firewood from the public pile.",
                exclude=[caller],
            )
        elif action == "deliver":
            caller.msg(
                "You stack your firewood beside the Tavern hearth. "
                f"The shared rack now holds {result['reserve']} bundles; "
                "someone with the Innkeep calling can tend the fire."
            )
            caller.location.msg_contents(
                f"{caller.key} carries firewood to the hearth rack.",
                exclude=[caller],
            )
        else:
            caller.msg(
                "You feed a delivered log onto the embers. The Blood of "
                "the Vine's hearth catches and throws a deeper, welcome heat "
                f"through the room. {result['reserve']} bundles remain "
                "in the shared rack."
            )
            caller.location.msg_contents(
                f"{caller.key} tends the hearth; the fire climbs.",
                exclude=[caller],
            )
