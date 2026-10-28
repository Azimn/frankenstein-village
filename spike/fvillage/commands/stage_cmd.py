"""Actual, witnessed player performances at the Tavern."""
from evennia import Command


class CmdStage(Command):
    """A modest stage with rehearsals and real audience witnesses.

    Usage:
        stage
        stage rehearse ballad
        stage rehearse reel
        stage perform ballad
        stage perform reel
        stage witness
        stage serve <musician or signed witness>   (Innkeep, real soup bowl)

    Performers must practice before playing a public set. The world records
    only real player action, never an imagined audience.
    """

    key = "stage"
    aliases = ["tavernstage"]
    help_category = "Village"

    def func(self):
        from world import stage_work
        raw = (self.args or "").strip().lower().split()
        if not raw or raw in (["status"], ["help"]):
            self.caller.msg(stage_work.status(self.caller))
            return
        if raw == ["witness"]:
            result, error = stage_work.act(self.caller, "witness")
        elif len(raw) >= 2 and raw[0] == "serve":
            result, error = stage_work.serve(self.caller, " ".join(raw[1:]))
        elif len(raw) == 2 and raw[0] in ("rehearse", "perform"):
            result, error = stage_work.act(self.caller, raw[0], raw[1])
        else:
            self.caller.msg("Use stage | stage rehearse ballad|reel | stage perform ballad|reel | stage witness | stage serve <player>")
            return
        if error:
            self.caller.msg(error)
            return
        action = result["action"]
        if action == "rehearse":
            message = ("You rehearse the %s on the real Tavern stage. "
                       "The work is signed as world event %s. You can now perform it."
                       % (result["tune"], result["event_id"]))
        elif action == "perform":
            message = ("You actually perform the %s before whoever is present. "
                       "The Tavern records the music as world event %s, "
                       "without inventing spectators."
                       % (result["tune"], result["event_id"]))
        elif action == "serve":
            message = ("You serve a real cooked soup bowl to %s after the actual "
                       "Tavern performance (world event %s). The bowl is now "
                       "in their inventory." % (result["recipient"], result["event_id"]))
        else:
            message = ("You sign that you actually witnessed this hour's music "
                       "(world event %s)." % result["event_id"])
        self.caller.msg(message)
        self.caller.location.msg_contents(
            "%s takes part in the Tavern stage's %s." %
            (self.caller.key, action), exclude=[self.caller],
        )
