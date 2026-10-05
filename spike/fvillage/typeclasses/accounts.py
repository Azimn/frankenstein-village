"""
Account

The Account represents the game "account" and each login has only one
Account object. An Account is what chats on default channels but has no
other in-game-world existence. Rather the Account puppets Objects (such
as Characters) in order to actually participate in the game world.


Guest

Guest accounts are simple low-level accounts that are created/deleted
on the fly and allows users to test the game without the commitment
of a full registration. Guest accounts are deactivated by default; to
activate them, add the following line to your settings file:

    GUEST_ENABLED = True

You will also need to modify the connection screen to reflect the
possibility to connect with a guest account. The setting file accepts
several more options for customizing the Guest account system.

"""

import time

from evennia.accounts.accounts import DefaultAccount, DefaultGuest


PRIVATE_ROOM_DESC = (
    "Your room at the Inn Between. It is private and it persists; no one "
    "else can enter. A short guide lies on the nightstand. Stairs lead "
    "down to the common room."
)
PRIVATE_ROOM_AIR = (
    "The air is close and warm, smelling of clean linen and lamp oil."
)
PRIVATE_ROOM_SOUND = "The inn settles around you: a creak, a sigh, then quiet."
PRIVATE_GUIDE = (
    "A short pamphlet in a careful hand. It reads:\n\n"
    "'So you've woken up at the Inn. This room and the common room are "
    "out of character. Your room is private and persistent. The front "
    "door is the threshold: beyond it you are in character. The account "
    "disclosure gate was accepted before you were allowed to enter.'"
)


def _find_common_room():
    from evennia.utils import search

    rooms = [
        obj for obj in search.search_object("Inn Common Room")
        if obj.key == "Inn Common Room"
    ]
    return rooms[0] if rooms else None


def ensure_private_room(account):
    """Return the account's private room, creating/repairing it as needed."""
    from evennia.utils import create, search

    rooms = [
        obj for obj in search.search_object("Private Room")
        if obj.key == "Private Room" and obj.db.owner_account_id == account.id
    ]
    if rooms:
        room = rooms[0]
    else:
        room = create.create_object(
            "typeclasses.rooms.PrivateRoom",
            key="Private Room",
        )

    room.db.owner_account_id = account.id
    room.db.desc = PRIVATE_ROOM_DESC
    room.db.sense_air = PRIVATE_ROOM_AIR
    room.db.sense_sound = PRIVATE_ROOM_SOUND
    room.tags.add("ooc", category="side")
    room.tags.add("private_room", category="place")
    room.locks.add(
        f"view:pid({account.id}) or perm(Admin);"
        f"search:pid({account.id}) or perm(Admin);"
        f"enter:pid({account.id}) or perm(Admin)"
    )

    if not any(obj.key == "nightstand" for obj in room.contents):
        stand = create.create_object(
            "evennia.objects.objects.DefaultObject",
            key="nightstand",
            location=room,
            aliases=["stand", "table"],
        )
        stand.db.desc = "A plain oak nightstand. The guide lies on top of it."
    if not any(obj.key == "guide" for obj in room.contents):
        guide = create.create_object(
            "evennia.objects.objects.DefaultObject",
            key="guide",
            location=room,
            aliases=["pamphlet", "booklet"],
        )
        guide.db.desc = PRIVATE_GUIDE

    common = _find_common_room()
    if common:
        # Converge legacy per-account "up" exits into the single shared
        # PrivateRoomExit. (B5, 2026-10-04: N same-keyed exits made 'up'
        # ambiguous — "More than one match for 'up'" — and spammed the
        # exit listing. One exit routes each traveler to their own room.)
        for ex in list(common.exits):
            dest = ex.destination
            if (
                ex.key == "up"
                and dest is not None
                and dest.tags.has("private_room", category="place")
                and not ex.is_typeclass(
                    "typeclasses.exits.PrivateRoomExit", exact=True
                )
            ):
                ex.delete()
        shared_ups = [
            ex
            for ex in common.exits
            if ex.is_typeclass(
                "typeclasses.exits.PrivateRoomExit", exact=True
            )
        ]
        if shared_ups:
            up_exit = shared_ups[0]
        else:
            up_exit = create.create_object(
                "typeclasses.exits.PrivateRoomExit",
                key="up",
                location=common,
                destination=room,  # placeholder; at_traverse routes per-account
                aliases=["u", "room", "my room"],
            )
        up_exit.locks.add("traverse:all()")

        downs = [
            ex for ex in room.exits
            if ex.destination and ex.destination.id == common.id
        ]
        if downs:
            down_exit = downs[0]
        else:
            down_exit = create.create_object(
                "evennia.objects.objects.DefaultExit",
                key="down",
                location=room,
                destination=common,
                aliases=["d"],
            )
        # The room desc says "Stairs lead down" — make that examinable.
        if "stairs" not in (down_exit.aliases.all() or []):
            down_exit.aliases.add("stairs")
        down_exit.locks.add(
            f"traverse:pid({account.id}) or perm(Admin);"
            f"view:pid({account.id}) or perm(Admin);"
            f"search:pid({account.id}) or perm(Admin)"
        )

    return room


class Account(DefaultAccount):
    """
    An Account is the actual OOC player entity. It doesn't exist in the game,
    but puppets characters.

    This is the base Typeclass for all Accounts. Accounts represent
    the person playing the game and tracks account info, password
    etc. They are OOC entities without presence in-game. An Account
    can connect to a Character Object in order to "enter" the
    game.

    Account Typeclass API:

    * Available properties (only available on initiated typeclass objects)

     - key (string) - name of account
     - name (string)- wrapper for user.username
     - aliases (list of strings) - aliases to the object. Will be saved to
            database as AliasDB entries but returned as strings.
     - dbref (int, read-only) - unique #id-number. Also "id" can be used.
     - date_created (string) - time stamp of object creation
     - permissions (list of strings) - list of permission strings
     - user (User, read-only) - django User authorization object
     - obj (Object) - game object controlled by account. 'character' can also
                     be used.
     - is_superuser (bool, read-only) - if the connected user is a superuser

    * Handlers

     - locks - lock-handler: use locks.add() to add new lock strings
     - db - attribute-handler: store/retrieve database attributes on this
                              self.db.myattr=val, val=self.db.myattr
     - ndb - non-persistent attribute handler: same as db but does not
                                  create a database entry when storing data
     - scripts - script-handler. Add new scripts to object with scripts.add()
     - cmdset - cmdset-handler. Use cmdset.add() to add new cmdsets to object
     - nicks - nick-handler. New nicks with nicks.add().
     - sessions - session-handler. Use session.get() to see all sessions connected, if any
     - options - option-handler. Defaults are taken from settings.OPTIONS_ACCOUNT_DEFAULT
     - characters - handler for listing the account's playable characters

    * Helper methods (check autodocs for full updated listing)

     - msg(text=None, from_obj=None, session=None, options=None, **kwargs)
     - execute_cmd(raw_string)
     - search(searchdata, return_puppet=False, search_object=False, typeclass=None,
                      nofound_string=None, multimatch_string=None, use_nicks=True,
                      quiet=False, **kwargs)
     - is_typeclass(typeclass, exact=False)
     - swap_typeclass(new_typeclass, clean_attributes=False, no_default=True)
     - access(accessing_obj, access_type='read', default=False, no_superuser_bypass=False, **kwargs)
     - check_permstring(permstring)
     - get_cmdsets(caller, current, **kwargs)
     - get_cmdset_providers()
     - uses_screenreader(session=None)
     - get_display_name(looker, **kwargs)
     - get_extra_display_name_info(looker, **kwargs)
     - disconnect_session_from_account()
     - puppet_object(session, obj)
     - unpuppet_object(session)
     - unpuppet_all()
     - get_puppet(session)
     - get_all_puppets()
     - is_banned(**kwargs)
     - get_username_validators(validator_config=settings.AUTH_USERNAME_VALIDATORS)
     - authenticate(username, password, ip="", **kwargs)
     - normalize_username(username)
     - validate_username(username)
     - validate_password(password, account=None)
     - set_password(password, **kwargs)
     - get_character_slots()
     - get_available_character_slots()
     - create_character(*args, **kwargs)
     - create(*args, **kwargs)
     - delete(*args, **kwargs)
     - channel_msg(message, channel, senders=None, **kwargs)
     - idle_time()
     - connection_time()

    * Hook methods

     basetype_setup()
     at_account_creation()

     > note that the following hooks are also found on Objects and are
       usually handled on the character level:

     - at_init()
     - at_first_save()
     - at_access()
     - at_cmdset_get(**kwargs)
     - at_password_change(**kwargs)
     - at_first_login()
     - at_pre_login()
     - at_post_login(session=None)
     - at_failed_login(session, **kwargs)
     - at_disconnect(reason=None, **kwargs)
     - at_post_disconnect(**kwargs)
     - at_message_receive()
     - at_message_send()
     - at_server_reload()
     - at_server_shutdown()
     - at_look(target=None, session=None, **kwargs)
     - at_post_create_character(character, **kwargs)
     - at_post_add_character(char)
     - at_post_remove_character(char)
     - at_pre_channel_msg(message, channel, senders=None, **kwargs)
     - at_post_chnnel_msg(message, channel, senders=None, **kwargs)

    """

    def record_history(self, kind, **fields):
        """Append private, account-level continuity history."""
        history = list(self.db.long_term_history or [])
        event = {"t": time.time(), "kind": kind}
        event.update(fields)
        history.append(event)
        self.db.long_term_history = history
        return event

    def at_post_login(self, session=None, **kwargs):
        super().at_post_login(session=session, **kwargs)
        ensure_private_room(self)
        if self.db.disclosure_consent is not True or self.db.substrate not in {
            "human", "ai"
        }:
            self.msg(
                "|yDisclosure gate:|n before character creation or world "
                "entry, declare |wsubstrate human|n or |wsubstrate ai|n.",
                session=session,
            )

    def at_look(self, target=None, session=None, **kwargs):
        base = super().at_look(target=target, session=session, **kwargs)
        substrate = self.db.substrate
        label = substrate.upper() if substrate in {"human", "ai"} else "UNDECLARED"
        gate = "OPEN" if self.db.disclosure_consent is True else "CLOSED"
        return f"|wAccount substrate:|n {label}    |wDisclosure gate:|n {gate}\n\n{base}"

    def puppet_object(self, session, obj):
        """Enforce disclosure plus one-active-mask account policy."""
        if self.db.disclosure_consent is not True or self.db.substrate not in {
            "human", "ai"
        }:
            self.msg(
                "World entry is blocked until you declare substrate human or ai.",
                session=session,
            )
            return None
        active = [puppet for puppet in self.get_all_puppets() if puppet]
        if any(puppet.id != obj.id for puppet in active):
            self.msg(
                "One account may wear only one mask at a time. Return OOC "
                "before entering another.",
                session=session,
            )
            return None
        ensure_private_room(self)
        result = super().puppet_object(session, obj)
        self.record_history(
            "mask_entered", mask=obj.key, mask_id=obj.id
        )
        return result

    def at_post_create_character(self, character, **kwargs):
        """Start every player mask in the owning account's private OOC room."""
        super().at_post_create_character(character, **kwargs)

        # Evennia creates its special Account #1 character before it creates
        # Limbo #2 during first-database setup. Creating a normal room at that
        # instant fails because DEFAULT_HOME does not exist yet. Defer only
        # this framework bootstrap character; the first login repairs its room.
        from evennia.objects.models import ObjectDB
        if not ObjectDB.objects.filter(id=2).exists():
            return

        room = ensure_private_room(self)
        character.db.new_arrival = True
        character.home = room
        if character.location != room:
            character.move_to(room, quiet=True)
        self.record_history(
            "mask_created", mask=character.key, mask_id=character.id
        )


class Guest(DefaultGuest):
    """
    This class is used for guest logins. Unlike Accounts, Guests and their
    characters are deleted after disconnection.
    """

    pass
    """
    This class is used for guest logins. Unlike Accounts, Guests and their
    characters are deleted after disconnection.
    """

    pass
