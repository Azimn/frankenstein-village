"""Privacy-bounded guest register inquiry by Innkeep and Detective."""
from evennia import Command


class CmdLodging(Command):
    """Work from the actual guest register at the Blood of the Vine.

    Usage:
        lodging
        look register
        lodging disclose     (Innkeep)
        lodging inquire      (different Detective)

    The Innkeep authorizes only the existence of the Room Six entry.
    A Detective separately examines the original register within 48 village
    hours. No guest identity, room access or culprit is established.
    """

    key = "lodging"
    aliases = ["guestinquiry"]
    help_category = "Village"

    def func(self):
        from world import lodging_work
        action = (self.args or "").strip().lower()
        if action in ("", "status", "help"):
            self.caller.msg(lodging_work.status(self.caller))
            return
        if action not in ("disclose", "inquire"):
            self.caller.msg("Use lodging | look register | lodging disclose | lodging inquire.")
            return
        result, error = lodging_work.act(self.caller, action)
        if error:
            self.caller.msg(error)
            return
        if action == "disclose":
            self.caller.msg(
                "You authorize a redacted Room Six register entry only "
                "(signed world event %s). No guest identity or room access is disclosed."
                % result["event_id"]
            )
        else:
            self.caller.msg(
                "You preserve an independent qualified register observation "
                "(signed world event %s, verified Innkeep source %s). "
                "The entry does not prove who wrote it."
                % (result["event_id"], result["source_event_id"])
            )
        self.caller.location.msg_contents(
            "%s completes professional guest-register work." % self.caller.key,
            exclude=[self.caller],
        )
