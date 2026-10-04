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


class CmdVillageCharCreate(default_account.CmdCharCreate):
    """Default character creation, blocked until disclosure is complete."""

    def func(self):
        if not _gate_open(self.account):
            self.msg(
                "Character creation is behind the disclosure gate. "
                "Use: substrate human  OR  substrate ai"
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
        ensure_private_room(self.account)
        return super().func()
