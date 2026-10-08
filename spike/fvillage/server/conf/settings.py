r"""
Evennia settings file.

The available options are found in the default settings file found
here:

https://www.evennia.com/docs/latest/Setup/Settings-Default.html

Remember:

Don't copy more from the default file than you actually intend to
change; this will make sure that you don't overload upstream updates
unnecessarily.

When changing a setting requiring a file system path (like
path/to/actual/file.py), use GAME_DIR and EVENNIA_DIR to reference
your game folder and the Evennia library folders respectively. Python
paths (path.to.module) should be given relative to the game's root
folder (typeclasses.foo) whereas paths within the Evennia library
needs to be given explicitly (evennia.foo).

If you want to share your game dir, including its settings, you can
put secret game- or server-specific settings in secret_settings.py.

"""

# Use the defaults from Evennia unless explicitly overridden
from evennia.settings_default import *

######################################################################
# Evennia base server config
######################################################################

# This is the name of your game. Make it catchy!
SERVERNAME = "fvillage"

# Frankenstein Village: player characters use the spike typeclass so the
# arrival flow (Account.at_post_create_character +
# SpikeCharacter.at_post_puppet) runs for every new character. Without
# this, Evennia creates DefaultCharacters and new arrivals skip the Inn
# Between entirely.
BASE_CHARACTER_TYPECLASS = "typeclasses.characters.SpikeCharacter"

# The compact requires an account-level gate before any character can enter
# the world. Mode 2 starts accounts OOC and exposes the normal character
# roster/selection flow instead of silently creating and puppeting a character.
MULTISESSION_MODE = 2
AUTO_CREATE_CHARACTER_WITH_ACCOUNT = False
AUTO_PUPPET_ON_LOGIN = False

# One account may own several masks, but only one may be active at a time.
# Item 6 adds the explicit policy check in addition to this engine limit.
MAX_NR_SIMULTANEOUS_PUPPETS = 1
MAX_NR_CHARACTERS = 5

# Guest accounts do not have a disclosure model and may not bypass the gate.
GUEST_ENABLED = False


######################################################################
# Settings given in secret_settings.py override those in this file.
######################################################################
try:
    from server.conf.secret_settings import *
except ImportError:
    print("secret_settings.py file not found or failed to import.")

# Public alpha is an explicit, validated mode. Apply these security-critical
# settings LAST, including after secret_settings.py, so a stale local override
# cannot accidentally expose raw Evennia ports or disable HTTPS protections.
# Normal development and clean-checkout CI retain their previous defaults.
import os as _fv_os
from server.conf.deployment_profile import public_profile as _fv_public_profile

globals().update(_fv_public_profile(_fv_os.environ))
