"""
File-based help entries. These complements command-based help and help entries
added in the database using the `sethelp` command in-game.

Control where Evennia reads these entries with `settings.FILE_HELP_ENTRY_MODULES`,
which is a list of python-paths to modules to read.

A module like this should hold a global `HELP_ENTRY_DICTS` list, containing
dicts that each represent a help entry. If no `HELP_ENTRY_DICTS` variable is
given, all top-level variables that are dicts in the module are read as help
entries.

Each dict is on the form
::

    {'key': <str>,
     'text': <str>}``     # the actual help text. Can contain # subtopic sections
     'category': <str>,   # optional, otherwise settings.DEFAULT_HELP_CATEGORY
     'aliases': <list>,   # optional
     'locks': <str>       # optional, 'view' controls seeing in help index, 'read'
                          #           if the entry can be read. If 'view' is unset,
                          #           'read' is used for the index. If unset, everyone
                          #           can read/view the entry.

"""

HELP_ENTRY_DICTS = [
    {
        "key": "evennia",
        "aliases": ["ev"],
        "category": "General",
        "locks": "read:perm(Developer)",
        "text": """
            Evennia is a MU-game server and framework written in Python. You can read more
            on https://www.evennia.com.

            # subtopics

            ## Installation

            You'll find installation instructions on https://www.evennia.com.

            ## Community

            There are many ways to get help and communicate with other devs!

            ### Discussions

            The Discussions forum is found at https://github.com/evennia/evennia/discussions.

            ### Discord

            There is also a discord channel for chatting - connect using the
            following link: https://discord.gg/AJJpcRUhtF

        """,
    },
    {
        "key": "movement",
        "aliases": ["move", "go", "walk", "directions", "exits"],
        "category": "General",
        "text": """
            Moving around the village.

            Every room lists its exits: "Exits: north, east, south, and
            west". To move, name a direction — north, south, east, west,
            up, down — or its short form: n, s, e, w, u, d.

            "go north", "walk east", "move up" all work too.

            Some things that look like scenery are ways through: the
            front door of the Inn Between answers to "door" as well as
            "south". When in doubt, read the Exits line — it never lies.
        """,
    },
    {
        "key": "guide",
        "aliases": ["newbie", "new", "start", "begin", "beginner"],
        "category": "General",
        "text": """
            First evening in Frankenstein Village.

            You woke in the Inn Between, which is out of character —
            backstage. M. keeps the bar there; talk to her (talk M.)
            and mind the front door: step through it and you are in
            character, a traveler in a strange village.

            Useful first verbs:

              look / examine <thing> — see the room, or look closer
              go north (or just: north) — move; every room lists Exits
              talk <someone> — have a word with a resident
              ask <someone> about <thing> — the way mysteries are solved
              rumors — hear the talk of the tavern (in the tavern only)
              whisper <someone> = <words> — speak privately, in character
              say <words> — speak aloud, in character
              help <command> — every command explains itself

            There is no wrong way to spend an evening here. Follow a
            rumor. See what happens.
        """,
    },
]
