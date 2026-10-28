"""Returning-player continuity across logout, restart, and OOC entry."""
from evennia import Command
from evennia.scripts.models import ScriptDB

from world import civic_work, commons, commons_follow, return_agenda


class CmdAgenda(Command):
    """Recall personal next steps and followed public correspondence.

    Usage:
        agenda
        agenda note = <your reminder>
        agenda clear

    A private intention belongs to this one mask, not another account.
    Hidden Commons notices are never reproduced from a cached copy.
    """

    key = "agenda"
    aliases = ["resume", "my-next-step"]
    help_category = "Village"

    def func(self):
        mask = self.caller
        if not getattr(mask, "account", None):
            mask.msg("Only a logged-in player mask has a personal agenda.")
            return
        raw = (self.args or "").strip()
        if raw.lower() == "clear":
            mask.db.player_return_note = None
            mask.msg("This mask's private next-step reminder is cleared.")
            return
        if raw.lower().startswith("note"):
            heading, equal, text = raw.partition("=")
            if heading.strip().lower() != "note" or not equal:
                mask.msg("Use: agenda note = <your next step>.")
                return
            cleaned = return_agenda.clean_note(text)
            if not cleaned:
                mask.msg("Write 1 to 200 printable characters in one line.")
                return
            mask.db.player_return_note = cleaned
            mask.msg("Your private reminder was saved on this mask for next time.")
            return
        if raw:
            mask.msg("Use: agenda | agenda note = <words> | agenda clear")
            return

        try:
            clock = ScriptDB.objects.get(db_key="village_time")
            day = int(clock.db.day or 1)
        except ScriptDB.DoesNotExist:
            day = 1
        public = commons.current()
        followed = commons_follow.summaries(mask.db.commons_following, public)
        mask.msg(return_agenda.summary(
            note=mask.db.player_return_note,
            followed=followed,
            day=day,
            location=mask.location.key if mask.location else "nowhere",
            work_lines=civic_work.personal_agenda(mask),
        ))
