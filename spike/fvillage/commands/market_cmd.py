"""Real market duty for three established social Callings."""
from evennia import Command


class CmdTrade(Command):
    """Review the Market Lane scale and perform signed professional work.

    Usage:
        trade
        trade honor       (Merchant: honor disputed prices)
        trade hold        (Merchant: suspend disputed material distribution)
        trade release     (Merchant: reopen distribution)
        trade calibrate   (Smith: correct the scale)
        trade attest      (Chronicler: attest both source records)
        trade inspect     (Detective: qualified inquiry after Smith calibration)

    Examine the physical crooked market scale on the current village day.
    Only that Calling's active practitioner may sign an action.
    """

    key = "trade"
    aliases = ["marketstandards"]
    help_category = "Village"

    def func(self):
        from world import market_work
        caller = self.caller
        room = getattr(caller, "location", None)
        if not room or not room.tags.has("ic", category="side"):
            caller.msg("This is village business. Enter through the Inn door.")
            return
        action = (self.args or "").strip().lower()
        if action in {"", "status"}:
            caller.msg(market_work.state_lines())
            return
        result, error = market_work.perform(caller, action)
        if error:
            caller.msg(error)
            return
        caller.msg(
            f"Market action signed (world event {result['event_id']}).\n"
            + result["lines"]
        )
        caller.location.msg_contents(
            f"{caller.key} signs the Market Lane standards ledger.",
            exclude=[caller],
        )
