"""Public village route survey work for any registered character."""
from evennia import Command


class CmdSurvey(Command):
    """Survey a real district landmark for the public daily travel record.

    Usage:
        survey
        survey report
        survey protect       (Hound, Northern Treeline)
        survey passability   (Wanderer, Northern Treeline)

    Read the board, go to an outstanding district, examine the actual
    landmark and sign a firsthand report. Anyone can contribute. Wanderers,
    Hounds and Detectives additionally get documented Calling participation,
    not automatic rank or XP.
    """

    key = "survey"
    aliases = ["route-survey"]
    help_category = "Village"

    def func(self):
        from world import route_work
        caller = self.caller
        room = getattr(caller, "location", None)
        if not room or not room.tags.has("ic", category="side"):
            caller.msg("Daily village surveys are in-character work.")
            return
        verb = (self.args or "").strip().lower()
        if verb in {"", "status", "help"}:
            caller.msg(route_work.status_lines())
            return
        if verb in {"report", "inspect"}:
            result, error = route_work.report(caller)
            if error:
                caller.msg(error)
                return
            caller.msg(
                f"Firsthand route report signed (event {result['event_id']}). "
                f"{result['count']} of 4 public landmarks inspected today."
                + (
                    " Today's shared route report is now complete."
                    if result["completed"] else
                    " Neighbors may inspect the remaining districts."
                )
            )
            caller.location.msg_contents(
                f"{caller.key} records a firsthand district route inspection.",
                exclude=[caller],
            )
            return
        if verb in {"protect", "passability"}:
            result, error = route_work.field_action(caller, verb)
            if error:
                caller.msg(error)
                return
            if verb == "protect":
                caller.msg(
                    f"You tie the original frayed cord as a visible warning, "
                    f"without repairing it (signed event {result['event_id']})."
                )
            else:
                caller.msg(
                    f"You record firsthand passability evidence from the "
                    f"actual red cord (signed event {result['event_id']})."
                )
            caller.location.msg_contents(
                f"{caller.key} completes a firsthand professional treeline action.",
                exclude=[caller],
            )
            return
        caller.msg("Use: survey | survey report | survey protect | survey passability")
