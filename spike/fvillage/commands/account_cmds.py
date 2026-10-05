"""Account-level commands for disclosure and mask entry."""

from evennia.commands.default import account as default_account
from evennia.commands.default.muxcommand import MuxCommand

from typeclasses.accounts import ensure_private_room


VALID_SUBSTRATES = {"human", "ai"}


def _gate_open(account):
    return (
        account.db.disclosure_consent is True
        and account.db.substrate in VALID_SUBSTRATES
    )


def _moderation_queue():
    """Return the persistent moderation queue, creating it if needed."""
    from evennia import create_script
    from evennia.scripts.models import ScriptDB

    try:
        return ScriptDB.objects.get(db_key="moderation_queue")
    except ScriptDB.DoesNotExist:
        return create_script(
            "typeclasses.scripts.ModerationQueue",
            key="moderation_queue",
            persistent=True,
        )


def _world_entry_allowed(account):
    return not bool(account.db.compact_ban_actions)


class CmdSubstrate(MuxCommand):
    """Declare the account substrate and accept the mixed-world compact.

    Usage:
        substrate
        substrate human
        substrate ai

    The declaration is account-level and immutable through player commands.
    Staff may correct account data administratively if a declaration was made
    in error.
    """

    key = "substrate"
    locks = "cmd:all()"
    help_category = "Account"
    account_caller = True

    def func(self):
        account = self.account
        current = account.db.substrate
        arg = (self.args or "").strip().lower()

        if not arg:
            if current in VALID_SUBSTRATES:
                self.msg(
                    f"Account substrate: {current.upper()}. "
                    "The disclosure gate is complete."
                )
            else:
                self.msg(
                    "The disclosure gate is not complete. Declare one: "
                    "substrate human  OR  substrate ai"
                )
            return

        if current in VALID_SUBSTRATES:
            self.msg(
                f"This account is already declared {current.upper()}. "
                "Substrate declarations are not player-editable."
            )
            return

        if arg not in VALID_SUBSTRATES:
            self.msg("Usage: substrate human  OR  substrate ai")
            return

        account.db.substrate = arg
        account.db.disclosure_consent = True
        if hasattr(account, "record_history"):
            account.record_history(
                "disclosure_declared", substrate=arg
            )
        ensure_private_room(account)
        self.msg(
            f"Account substrate recorded: {arg.upper()}.\n"
            "You have acknowledged that Frankenstein Village mixes human "
            "and AI players, shows no substrate markers inside the fiction, "
            "and uses the Inn Between as its OOC boundary. The gate is open."
        )


class CmdAppeal(MuxCommand):
    """Review or appeal human-issued moderation actions from OOC space.

    Usage:
        appeal
        appeal <action id> <reason>

    This command is account-level on purpose. A suspended player may remain
    out of character, read the moderation state, and submit an appeal without
    entering the world.
    """

    key = "appeal"
    locks = "cmd:all()"
    help_category = "Account"
    account_caller = True

    def func(self):
        account = self.account
        queue = _moderation_queue()
        raw = (self.args or "").strip()

        if not raw:
            actions = queue.active_actions_for(account.id)
            appeals = queue.appeals_for(account.id)
            if not actions and not appeals:
                self.msg("This account has no active moderation actions or appeals.")
                return
            lines = ["|yYour compact moderation record:|n"]
            for action in actions:
                label = "warning" if action["kind"] == "warning" else "world-entry suspension"
                note = action.get("note") or "No additional note."
                lines.append(f"Action #{action['id']}: {label}. {note}")
            for appeal in appeals[-10:]:
                suffix = (
                    f" -> {appeal.get('outcome')}"
                    if appeal.get("status") == "resolved"
                    else ""
                )
                lines.append(
                    f"Appeal #{appeal['id']} for action #{appeal['action_id']}: "
                    f"{appeal['status']}{suffix}"
                )
            if actions:
                lines.append(
                    "To appeal an active action: appeal <action id> <reason>"
                )
            self.msg("\n".join(lines))
            return

        parts = raw.split(None, 1)
        if len(parts) < 2 or not parts[0].isdigit() or not parts[1].strip():
            self.msg("Usage: appeal <action id> <reason>")
            return
        action_id = int(parts[0])
        reason = parts[1].strip()
        appeal, error = queue.submit_appeal(account, action_id, reason)
        if error:
            self.msg(error)
            return
        self.msg(
            f"Appeal #{appeal['id']} recorded for human review. "
            "The moderation action remains in effect unless it is overturned."
        )


class CmdVillageCharCreate(default_account.CmdCharCreate):
    """Default character creation, blocked until disclosure is complete."""

    def func(self):
        if not _gate_open(self.account):
            self.msg(
                "Character creation is behind the disclosure gate. "
                "Use: substrate human  OR  substrate ai"
            )
            return
        if not _world_entry_allowed(self.account):
            self.msg(
                "World entry is suspended after human review. "
                "Use 'appeal' from OOC space to review or appeal the action."
            )
            return
        return super().func()


class CmdVillageIC(default_account.CmdIC):
    """Default mask entry, blocked until disclosure is complete."""

    def func(self):
        if not _gate_open(self.account):
            self.msg(
                "World entry is behind the disclosure gate. "
                "Use: substrate human  OR  substrate ai"
            )
            return
        if not _world_entry_allowed(self.account):
            self.msg(
                "World entry is suspended after human review. "
                "Use 'appeal' from OOC space to review or appeal the action."
            )
            return
        ensure_private_room(self.account)
        return super().func()
