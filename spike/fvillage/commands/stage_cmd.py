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
        stage fit                (Smith with real Workshop hinge)
        stage soundcheck         (independent Performer)
        stage acoustic ballad    (finite tested rail)
        stage acoustic reel

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
        if raw in (["fit"], ["soundcheck"]) or (len(raw) == 2 and raw[0] == "acoustic"):
            from world import stage_fitting_work
            action = raw[0]
            tune = raw[1] if len(raw) == 2 else None
            result, error = stage_fitting_work.act(self.caller, action, tune)
            if error:
                self.caller.msg(error)
            else:
                self.caller.msg(
                    {"fit": "You install the real forged hinge on the Tavern rail",
                     "soundcheck": "You independently test the rail's acoustic response",
                     "acoustic": "You play an actual acoustic %s on the finite stage rail" % tune
                    }[action] + " (signed world event %s)." % result["event_id"]
                )
                self.caller.location.msg_contents(
                    "%s performs a real stage %s action." % (self.caller.key, action),
                    exclude=[self.caller],
                )
            return
        if raw == ["witness"]:
            result, error = stage_work.act(self.caller, "witness")
        elif len(raw) == 2 and raw[0] in ("rehearse", "perform"):
            result, error = stage_work.act(self.caller, raw[0], raw[1])
        else:
            self.caller.msg("Use stage, stage rehearse ballad, stage rehearse reel, stage perform ballad, stage perform reel, stage witness, stage fit, stage soundcheck, stage acoustic ballad, or stage acoustic reel")
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
        else:
            message = ("You sign that you actually witnessed this hour's music "
                       "(world event %s)." % result["event_id"])
        self.caller.msg(message)
        self.caller.location.msg_contents(
            "%s takes part in the Tavern stage's %s." %
            (self.caller.key, action), exclude=[self.caller],
        )
