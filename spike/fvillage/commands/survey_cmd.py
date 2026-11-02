"""Public village route survey work for any registered character."""
from evennia import Command


class CmdSurvey(Command):
    """Survey a real district landmark for the public daily travel record.

    Usage:
        survey
        survey report
        survey protect       (Hound, Northern Treeline)
        survey passability   (Wanderer, Northern Treeline)
        survey corroborate   (Wanderer, after signed Hound protection)
        survey publish       (Chronicler, Village Square; sourced map)
        survey caution       (Chronicler, Village Square; signed Hound marker)
        survey preserve      (Detective, signed Hound caution marker)
        survey custody       (read physical custody record at treeline)

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
        if verb in {"preserve", "custody"}:
            from world import route_trace_work
            if verb == "custody":
                caller.msg(route_trace_work.status(caller))
                return
            result, error = route_trace_work.preserve(caller)
            if error:
                caller.msg(error)
                return
            caller.msg(
                f"You preserve an independent Detective trace record "
                f"(signed event {result['event_id']}, Hound source "
                f"{result['source_event_id']}). " + result["lines"]
            )
            caller.location.msg_contents(
                f"{caller.key} documents the physical cord without naming a culprit.",
                exclude=[caller],
            )
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
        if verb == "publish":
            result, error = route_work.publish_advisory(caller)
            if error:
                caller.msg(error)
                return
            caller.msg(
                f"You publish dated route map v{result['version']} for day "
                f"{result['day']} from the independent Wanderer report "
                f"(source event {result['source_event_id']}; "
                f"publication event {result['event_id']}). "
                "The edition is a qualified observation, not a safety guarantee."
            )
            caller.location.msg_contents(
                f"{caller.key} posts a sourced, dated route map at the public board.",
                exclude=[caller],
            )
            return
        if verb == "caution":
            result, error = route_work.publish_caution(caller)
            if error:
                caller.msg(error)
                return
            caller.msg(
                f"You publish a sourced public caution (event {result['event_id']}) "
                f"based on the Hound's physical marker (event {result['source_event_id']}). "
                "This does not prove danger or safety."
            )
            caller.location.msg_contents(
                f"{caller.key} posts a sourced caution at the route board.",
                exclude=[caller],
            )
            return
        if verb in {"protect", "passability", "corroborate"}:
            result, error = route_work.field_action(caller, verb)
            if error:
                caller.msg(error)
                return
            if verb == "protect":
                caller.msg(
                    f"You tie the original frayed cord as a visible warning, or re-tighten its older marker, "
                    f"without repairing it (signed event {result['event_id']})."
                )
            elif verb == "passability":
                caller.msg(
                    f"You record firsthand passability evidence from the "
                    f"actual red cord (signed event {result['event_id']})."
                )
            else:
                caller.msg(
                    f"You independently confirm the Hound's physical caution "
                    f"marker (Hound source {result['hound_source_event_id']}, "
                    f"your signed event {result['event_id']}). This is not "
                    "a claim that the route is safe."
                )
            caller.location.msg_contents(
                f"{caller.key} completes a firsthand professional treeline action.",
                exclude=[caller],
            )
            return
        caller.msg("Use: survey | survey report | survey protect | survey passability | survey publish | survey corroborate | survey caution | survey preserve | survey custody")
