"""
Command sets

All commands in the game must be grouped in a cmdset.  A given command
can be part of any number of cmdsets and cmdsets can be added/removed
and merged onto entities at runtime.

To create new commands to populate the cmdset, see
`commands/command.py`.

This module wraps the default command sets of Evennia; overloads them
to add/remove commands from the default lineup. You can create your
own cmdsets by inheriting from them or directly from `evennia.CmdSet`.

"""

from evennia import default_cmds


class CharacterCmdSet(default_cmds.CharacterCmdSet):
    """
    The `CharacterCmdSet` contains general in-game commands like `look`,
    `get`, etc available on in-game Character objects. It is merged with
    the `AccountCmdSet` when an Account puppets a Character.
    """

    key = "DefaultCharacter"

    def at_cmdset_creation(self):
        """
        Populates the cmdset
        """
        super().at_cmdset_creation()
        #
        # any commands you add below will overload the default ones.
        #
        from commands.village_cmds import CmdReport, CmdRumors, CmdTalk, CmdAsk, CmdRead, CmdTime, CmdListen, CmdSmell, CmdDiary, CmdPet, CmdThrow, CmdRoll, CmdDraw, CmdSit, CmdStand, CmdPlay, CmdPractice, CmdDuet, CmdScore, CmdEat, CmdDrink, CmdConfess, CmdOOCOverride, CmdICOverride, CmdExamine, CmdPurse, CmdTake

        self.add(CmdReport())
        self.add(CmdRumors())
        self.add(CmdTalk())
        self.add(CmdAsk())
        self.add(CmdRead())
        self.add(CmdTime())
        self.add(CmdListen())
        self.add(CmdSmell())
        self.add(CmdDiary())
        self.add(CmdPet())
        self.add(CmdThrow())
        self.add(CmdPlay())
        self.add(CmdPractice())
        self.add(CmdDuet())
        self.add(CmdScore())
        self.add(CmdRoll())
        self.add(CmdDraw())
        self.add(CmdSit())
        self.add(CmdStand())
        self.add(CmdEat())
        self.add(CmdDrink())
        self.add(CmdConfess())
        self.add(CmdExamine())
        self.add(CmdTake())
        self.add(CmdPurse())
        # The front door is the only IC/OOC threshold: block Evennia's
        # default ooc/ic commands everywhere so they can't bypass it.
        self.add(CmdOOCOverride())
        self.add(CmdICOverride())


class AccountCmdSet(default_cmds.AccountCmdSet):
    """
    This is the cmdset available to the Account at all times. It is
    combined with the `CharacterCmdSet` when the Account puppets a
    Character. It holds game-account-specific commands, channel
    commands, etc.
    """

    key = "DefaultAccount"

    def at_cmdset_creation(self):
        """
        Populates the cmdset
        """
        super().at_cmdset_creation()
        from commands.account_cmds import (
            CmdSubstrate,
            CmdVillageCharCreate,
            CmdVillageIC,
        )

        # Same keys as Evennia's defaults intentionally replace the default
        # entry paths. The substrate command is the account-level gate.
        self.add(CmdSubstrate())
        self.add(CmdVillageCharCreate())
        self.add(CmdVillageIC())


class UnloggedinCmdSet(default_cmds.UnloggedinCmdSet):
    """
    Command set available to the Session before being logged in.  This
    holds commands like creating a new account, logging in, etc.
    """

    key = "DefaultUnloggedin"

    def at_cmdset_creation(self):
        """
        Populates the cmdset
        """
        super().at_cmdset_creation()
        #
        # any commands you add below will overload the default ones.
        #


class SessionCmdSet(default_cmds.SessionCmdSet):
    """
    This cmdset is made available on Session level once logged in. It
    is empty by default.
    """

    key = "DefaultSession"

    def at_cmdset_creation(self):
        """
        This is the only method defined in a cmdset, called during
        its creation. It should populate the set with command instances.

        As and example we just add the empty base `Command` object.
        It prints some info.
        """
        super().at_cmdset_creation()
        #
        # any commands you add below will overload the default ones.
        #
