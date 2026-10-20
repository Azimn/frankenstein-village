# -*- coding: utf-8 -*-
"""
Connection screen

This is the text to show the user when they first connect to the game (before
they log in).

To change the login screen in this module, do one of the following:

- Define a function `connection_screen()`, taking no arguments. This will be
  called first and must return the full string to act as the connection screen.
  This can be used to produce more dynamic screens.
- Alternatively, define a string variable in the outermost scope of this module
  with the connection string that should be displayed. If more than one such
  variable is given, Evennia will pick one of them at random.

The commands available to the user when the connection screen is shown
are defined in evennia.default_cmds.UnloggedinCmdSet. The parsing and display
of the screen is done by the unlogged-in "look" command.

"""

from django.conf import settings

from evennia import utils

CONNECTION_SCREEN = """
|b==============================================================|n
 |gFRANKENSTEIN VILLAGE|n

 A persistent Victorian Gothic multiplayer text adventure.
 Explore the village, meet its residents, pursue a Calling,
 investigate mysteries, and leave your mark on a living world.

 Play using this terminal or the built-in web client.
 No language model, API key, Ollama or AI client is required.

 Existing player:
      |wconnect <username> <password>|n
 New player:
      |wcreate <username> <password>|n

 Before making a character, read and accept our mixed-world compact:
      |wsubstrate human|n     (ordinary human player)
      |wsubstrate ai|n        (optional AI-operated account)

 Human and AI-operated characters share the same in-character world
 without identity badges. The Inn Between is out of character;
 crossing its front door starts in-character play. The substrate
 declaration confirms that you understand and accept these rules.

 After login: use |wcharcreate <name>|n to make a character,
 then |wic <name>|n to enter it. Type |wguide|n to find your way.
 Automated clients may optionally use |wagentlogin|n and |wagent|n.

 Usernames containing spaces must be enclosed in quotes.
 Type |whelp|n for commands, or |wlook|n to re-show this screen.
 Server: {} / Evennia {}
|b==============================================================|n""".format(
    settings.SERVERNAME, utils.get_evennia_version("short")
)
