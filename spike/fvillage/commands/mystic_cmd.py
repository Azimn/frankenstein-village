"""Mystic Calling: two schools of thought, one physical world."""
from evennia import Command


class CmdMystic(Command):
    """Inspect the guild and submit a professional firsthand study.

    Usage:
        mystic
        mystic circles
        mystic study measure
        mystic study vigil

    Study requires an active Mystic in the churchyard during an actual
    manifestation, who has personally looked at the grave marker that hour.
    The method is a point of view, not a certified metaphysical explanation.
    """

    key = "mystic"
    aliases = ["psychical"]
    help_category = "Village"

    def func(self):
        from world import mystic_work
        caller = self.caller
        room = getattr(caller, "location", None)
        if not room or not room.tags.has("ic", category="side"):
            caller.msg("Guild matters are in-character. Cross the Inn front door.")
            return
        raw = (self.args or "").strip().lower()
        if raw in {"", "circles", "status"}:
            caller.msg(mystic_work.status(caller))
            return
        if raw not in {"study measure", "study vigil"}:
            caller.msg("Use mystic | mystic circles | mystic study measure | mystic study vigil")
            return
        result, error = mystic_work.study(caller, raw.split()[-1])
        if error:
            caller.msg(error)
            return
        caller.msg(
            f"You file a signed {result['method']} study "
            f"(world event {result['event_id']}). "
            "The physical change is recorded, not its unknown cause.\n"
            + result["public"]
        )
        caller.location.msg_contents(
            f"{caller.key} files a churchyard observation with the Guild of Mystics.",
            exclude=[caller],
        )
