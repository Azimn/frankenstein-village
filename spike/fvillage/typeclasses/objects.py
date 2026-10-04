"""
Object

The Object is the class for general items in the game world.

Use the ObjectParent class to implement common features for *all* entities
with a location in the game world (like Characters, Rooms, Exits).

"""

from evennia.objects.objects import DefaultObject
from evennia.utils import create as _create
from evennia.utils import search as _search

from world.events import publish_world_event


def _room_six_script():
    """The persistent Room Six mystery script (world flags), if present."""
    try:
        from evennia.scripts.models import ScriptDB
        return ScriptDB.objects.get(db_key="room_six")
    except Exception:
        return None


def _player_stage(char):
    """Per-player Room Six stage dict (never None)."""
    return char.db.room_six or {}


def _set_stage(char, **kwargs):
    stage = _player_stage(char)
    stage.update(kwargs)
    char.db.room_six = stage


class Register(DefaultObject):
    """M.'s register, open on the bar of the Tavern.

    The hook of the Room Six mystery: every entry is in M.'s neat,
    impatient hand except one — Room 6, three nights past, in a tall
    hurried hand she doesn't recognize, on a night the house stood empty.
    """

    def at_object_creation(self):
        super().at_object_creation()
        self.db.desc = (
            "A heavy leather register, cracked at the spine, open on the "
            "bar. It smells faintly of iron and lamp oil. M.'s hand "
            "throughout — neat, impatient, the hand of someone who'd "
            "rather be polishing:\n\n"
            "'T. Okafor — Rm 2 — one night.'\n"
            "'The Widow Hessel — Rm 4 — three nights, paid.'\n"
            "'J. Marlowe — Rm 1 — one night, left before dawn.'\n\n"
            "And then, three nights past, in a hand like nothing else on "
            "the page — tall, hurried, the ink pressed hard enough to "
            "scar the paper:\n\n"
            "'Rm 6 — V. [smudge] — — —.'\n\n"
            "The surname is a smudge. Or a kindness."
        )
        self.aliases.add("guest book", "guestbook", "book")

    def at_desc(self, looker=None):
        desc = self.db.desc or ""
        if looker and looker.has_account:
            stage = _player_stage(looker)
            if not stage.get("seen_register"):
                _set_stage(looker, seen_register=True)
        return desc


class RoomSixDoor(DefaultObject):
    """The door of Room Six, in the Tavern's IC back hall.

    Six doors, five honest with dust. The sixth has a number plate
    polished like it was touched this morning. First close look reveals
    the folded note at its foot — one per player, so every traveler can
    walk the mystery themselves.
    """

    def at_object_creation(self):
        super().at_object_creation()
        self.db.desc = (
            "Six doors line the hallway, numbered 1 through 6 in brass "
            "gone green with age — except the sixth. Room Six's number "
            "plate gleams like it was polished this morning. The door "
            "itself is shut fast, the doorknob cold enough to ache. Five "
            "doors wear their dust honestly. The sixth doesn't."
        )
        self.aliases.add("sixth door")

    REVEAL_TEXT = (
        "\n\nWait — something white at the foot of the door. A "
        "folded note, half under the frame, as if slipped *out* "
        "rather than in."
    )
    WARM_TEXT = (
        "\n\nYou try the doorknob without thinking. It is warm "
        "under your hand. It wasn't, before."
    )

    def get_display_desc(self, looker=None, **kwargs):
        """Dynamic description: Evennia builds `look` output from this.

        (Note: at_desc's return value is discarded by Evennia — it is a
        side-effect hook only. Display logic belongs here.)
        """
        desc = self.db.desc or ""
        if not looker or not looker.has_account:
            return desc
        if not _player_stage(looker).get("found_note"):
            return desc + self.REVEAL_TEXT
        # Sensory beat for whoever carries the secret: the world
        # answers what you hold.
        carrying = any(
            o.typeclass_path == "typeclasses.objects.MysteryNote"
            for o in looker.contents
        )
        if carrying:
            return desc + self.WARM_TEXT
        return desc

    def at_desc(self, looker=None, **kwargs):
        # Finding the note is the first persistent Room Six event. Record it
        # before creating inventory state so the causal order is durable.
        if looker and looker.has_account:
            if not _player_stage(looker).get("found_note"):
                def apply_consequence(_event):
                    note = _create.create_object(
                        "typeclasses.objects.MysteryNote",
                        key="a folded note",
                        location=looker,
                    )
                    note.aliases.add("note")
                    note.db.owner_character_id = looker.id
                    note.locks.add(
                        f"get:id({looker.id}) or perm(Admin);"
                        f"give:id({looker.id}) or perm(Admin);"
                        f"drop:id({looker.id}) or perm(Admin);"
                        f"search:id({looker.id}) or perm(Admin);"
                        f"control:id({looker.id}) or perm(Admin)"
                    )
                    _set_stage(looker, found_note=True)
                    looker.msg("You take the folded note before anyone else can.")
                    return {"found_note": True, "note_id": note.id}

                publish_world_event(
                    "room_six.note_found",
                    actor=looker,
                    payload={"door_id": self.id},
                    consequence=apply_consequence,
                )
        return super().at_desc(looker, **kwargs)


class MysteryNote(DefaultObject):
    """The folded note from Room Six's door, in the unknown hand.

    The choice point of the mystery, expressed through world verbs:
    give it to M. (she burns it and trusts you), let the Tavern hear
    it (drop it / give it to the keeper — it becomes gossip with your
    name on it), or keep it in your pocket and say nothing.
    """

    NOTE_TEXT = (
        "A folded note, in the same tall hurried hand as the register "
        "entry. It reads:\n\n"
        "'Tell M. the room is paid for. — V.'\n\n"
        "The paper is good paper — too good for this village. It smells "
        "faintly of chemicals: sharp, clean, wrong for paper.\n\n"
        "Three roads, and the note won't walk them for you: give it to "
        "M. (give note to M.), keep it in your pocket and say nothing, "
        "or let the Tavern hear it — talk travels fastest where the "
        "beer flows."
    )
    PINNED_TEXT = (
        "The folded note, pinned behind the Tavern bar where everyone "
        "can see it and no one can reach it. In the tall hurried hand:\n\n"
        "'Tell M. the room is paid for. — V.'"
    )

    def at_object_creation(self):
        super().at_object_creation()
        self.db.desc = self.NOTE_TEXT

    # -- the M. road --------------------------------------------------------

    def at_pre_give(self, giver, getter, **kwargs):
        owner_id = self.db.owner_character_id
        if owner_id and giver.id != owner_id and not giver.check_permstring("Admin"):
            giver.msg("The note is not yours to pass on.")
            return False
        if getter.key == "M.":
            script = _room_six_script()
            if script is not None and script.db.m_told_by:
                giver.msg(
                    "M. glances at the note and waves it off. \"Someone "
                    "beat you to it, love. It's burned and done. But "
                    "thank you for the road.\""
                )
                return False
        if getter.key == "Bram":
            script = _room_six_script()
            if script is not None and script.db.tavern_told_by:
                giver.msg(
                    "The keeper doesn't look up. \"Old news, friend. It's "
                    "behind the bar.\""
                )
                return False
        return True

    def at_give(self, giver, getter, **kwargs):
        if getter.key == "M.":
            self._tell_m(giver)
        elif getter.key == "Bram":
            self._tell_tavern(giver)

    def _tell_m(self, giver):
        """Ledger the choice, then apply M.'s persistent consequence."""
        loc = giver.location

        def apply_consequence(_event):
            script = _room_six_script()
            if script is not None:
                script.db.m_told_by = giver.key
            _set_stage(giver, told_m=True)
            m = next(
                (obj for obj in _search.search_object("M.") if obj.key == "M."),
                None,
            )
            if m is not None:
                trusts = m.db.trusts or {}
                trusts[giver.key] = True
                m.db.trusts = trusts
            if loc:
                loc.msg_contents(
                    "M. takes the note. Her polishing stops; the glass hangs "
                    "forgotten in her hand, which has never happened before, "
                    "which is how the room knows something is wrong. She "
                    "reads. Once. Twice. Then she crosses to the hearth and "
                    "feeds the paper to the fire. It catches with a green-edged "
                    "flame.\n"
                    "\"Paid for,\" she says to no one. \"Paid for by whom, "
                    f"love?\" She looks at {giver.key}. \"Room Six stays shut "
                    "until I understand what was bought. You brought it to me "
                    "first. I won't forget that.\"",
                    exclude=[],
                )
            giver.msg("(M. will answer you truly now, about Room Six. Ask her.)")
            self.db.burned = True
            self.move_to(None, quiet=True, to_none=True)
            return {"route": "m", "m_told_by": giver.key, "note_burned": True}

        publish_world_event(
            "room_six.note_to_m",
            actor=giver,
            payload={"note_id": self.id, "route": "m"},
            consequence=apply_consequence,
        )

    # -- the Tavern road -----------------------------------------------------

    def at_pre_drop(self, dropper, **kwargs):
        owner_id = self.db.owner_character_id
        if owner_id and dropper.id != owner_id and not dropper.check_permstring("Admin"):
            dropper.msg("The note is not yours to place.")
            return False
        loc = dropper.location
        if loc is not None and loc.tags.has("tavern", category="place"):
            script = _room_six_script()
            if script is not None and script.db.tavern_told_by:
                dropper.msg(
                    "The keeper doesn't look up. \"Old news, friend. It's "
                    "behind the bar.\""
                )
                return False
        return True

    def at_drop(self, dropper, **kwargs):
        loc = dropper.location
        if loc is not None and loc.tags.has("tavern", category="place"):
            self._tell_tavern(dropper)

    def _tell_tavern(self, giver):
        """Ledger, publish rumor, then apply the Tavern consequence."""
        loc = giver.location
        rumor = (
            f"Room Six behind the Tavern was let three nights past — "
            f"though M. swears the house stood empty, and the hand in the "
            f"register isn't hers. *Heard from: {giver.key}, who found a "
            f"note under the door.*"
        )

        def apply_consequence(_event):
            script = _room_six_script()
            if script is not None:
                script.db.tavern_told_by = giver.key
            _set_stage(giver, tavern_talk=True)
            for obj in _search.search_object("M."):
                if obj.key == "M.":
                    cold = obj.db.cold_to or {}
                    cold[giver.key] = True
                    obj.db.cold_to = cold
                    break
            if loc:
                loc.msg_contents(
                    f"{giver.key} lets the folded note fall where the talk is "
                    "thickest. The keeper unfolds it, turns it over twice "
                    "though there's nothing on the back, and lets out a long "
                    "low whistle.\n"
                    "\"...V., is it?\" He looks at the door, then at "
                    f"{giver.key}. \"Well. The bar hears everything eventually "
                    "— might as well hear it clean.\" He pins the note behind "
                    "the bar, where everyone can see it and no one can reach it.",
                    exclude=[],
                )
                if self.location != loc:
                    self.move_to(loc, quiet=True)
            self.db.pinned = True
            self.db.desc = self.PINNED_TEXT
            self.locks.add(
                "get:false();give:false();drop:false();search:all();"
                "view:all();control:perm(Admin)"
            )
            return {"route": "tavern", "tavern_told_by": giver.key, "note_pinned": True}

        publish_world_event(
            "room_six.note_to_tavern",
            actor=giver,
            payload={"note_id": self.id, "route": "tavern"},
            rumor=rumor,
            consequence=apply_consequence,
        )


class Seat(DefaultObject):
    """Something you can sit on / at / by.

    The `sit`/`stand` commands (commands/village_cmds.py) own the posture
    logic; a Seat is just sittable scenery. db.sit_phrase holds the full
    sit phrase ("at the bar", "by the hearth") — seat keys stay bare nouns
    ("bar") because Evennia's look listing prepends its own article.
    Posture lives on the character (db.posture), so the seat itself needs
    no state.
    """

    def at_object_creation(self):
        super().at_object_creation()
        self.db.sittable = True
        if not self.db.sit_phrase:
            self.db.sit_phrase = f"on the {self.key}"


class ObjectParent:
    """
    This is a mixin that can be used to override *all* entities inheriting at
    some distance from DefaultObject (Objects, Exits, Characters and Rooms).

    Just add any method that exists on `DefaultObject` to this class. If one
    of the derived classes has itself defined that same hook already, that will
    take precedence.

    """


class Object(ObjectParent, DefaultObject):
    """
    This is the root Object typeclass, representing all entities that
    have an actual presence in-game. DefaultObjects generally have a
    location. They can also be manipulated and looked at. Game
    entities you define should inherit from DefaultObject at some distance.

    It is recommended to create children of this class using the
    `evennia.create_object()` function rather than to initialize the class
    directly - this will both set things up and efficiently save the object
    without `obj.save()` having to be called explicitly.

    Note: Check the autodocs for complete class members, this may not always
    be up-to date.

    * Base properties defined/available on all Objects

     key (string) - name of object
     name (string)- same as key
     dbref (int, read-only) - unique #id-number. Also "id" can be used.
     date_created (string) - time stamp of object creation

     account (Account) - controlling account (if any, only set together with
                       sessid below)
     sessid (int, read-only) - session id (if any, only set together with
                       account above). Use `sessions` handler to get the
                       Sessions directly.
     location (Object) - current location. Is None if this is a room
     home (Object) - safety start-location
     has_account (bool, read-only)- will only return *connected* accounts
     contents (list, read only) - returns all objects inside this object
     exits (list of Objects, read-only) - returns all exits from this
                       object, if any
     destination (Object) - only set if this object is an exit.
     is_superuser (bool, read-only) - True/False if this user is a superuser
     is_connected (bool, read-only) - True if this object is associated with
                            an Account with any connected sessions.
     has_account (bool, read-only) - True is this object has an associated account.
     is_superuser (bool, read-only): True if this object has an account and that
                        account is a superuser.

    * Handlers available

     aliases - alias-handler: use aliases.add/remove/get() to use.
     permissions - permission-handler: use permissions.add/remove() to
                   add/remove new perms.
     locks - lock-handler: use locks.add() to add new lock strings
     scripts - script-handler. Add new scripts to object with scripts.add()
     cmdset - cmdset-handler. Use cmdset.add() to add new cmdsets to object
     nicks - nick-handler. New nicks with nicks.add().
     sessions - sessions-handler. Get Sessions connected to this
                object with sessions.get()
     attributes - attribute-handler. Use attributes.add/remove/get.
     db - attribute-handler: Shortcut for attribute-handler. Store/retrieve
            database attributes using self.db.myattr=val, val=self.db.myattr
     ndb - non-persistent attribute handler: same as db but does not create
            a database entry when storing data

    * Helper methods (see src.objects.objects.py for full headers)

     get_search_query_replacement(searchdata, **kwargs)
     get_search_direct_match(searchdata, **kwargs)
     get_search_candidates(searchdata, **kwargs)
     get_search_result(searchdata, attribute_name=None, typeclass=None,
                       candidates=None, exact=False, use_dbref=None, tags=None, **kwargs)
     get_stacked_result(results, **kwargs)
     handle_search_results(searchdata, results, **kwargs)
     search(searchdata, global_search=False, use_nicks=True, typeclass=None,
            location=None, attribute_name=None, quiet=False, exact=False,
            candidates=None, use_locks=True, nofound_string=None,
            multimatch_string=None, use_dbref=None, tags=None, stacked=0)
     search_account(searchdata, quiet=False)
     execute_cmd(raw_string, session=None, **kwargs))
     msg(text=None, from_obj=None, session=None, options=None, **kwargs)
     for_contents(func, exclude=None, **kwargs)
     msg_contents(message, exclude=None, from_obj=None, mapping=None,
                  raise_funcparse_errors=False, **kwargs)
     move_to(destination, quiet=False, emit_to_obj=None, use_destination=True)
     clear_contents()
     create(key, account, caller, method, **kwargs)
     copy(new_key=None)
     at_object_post_copy(new_obj, **kwargs)
     delete()
     is_typeclass(typeclass, exact=False)
     swap_typeclass(new_typeclass, clean_attributes=False, no_default=True)
     access(accessing_obj, access_type='read', default=False,
            no_superuser_bypass=False, **kwargs)
     filter_visible(obj_list, looker, **kwargs)
     get_default_lockstring()
     get_cmdsets(caller, current, **kwargs)
     check_permstring(permstring)
     get_cmdset_providers()
     get_display_name(looker=None, **kwargs)
     get_extra_display_name_info(looker=None, **kwargs)
     get_numbered_name(count, looker, **kwargs)
     get_display_header(looker, **kwargs)
     get_display_desc(looker, **kwargs)
     get_display_exits(looker, **kwargs)
     get_display_characters(looker, **kwargs)
     get_display_things(looker, **kwargs)
     get_display_footer(looker, **kwargs)
     format_appearance(appearance, looker, **kwargs)
     return_apperance(looker, **kwargs)

    * Hooks (these are class methods, so args should start with self):

     basetype_setup()     - only called once, used for behind-the-scenes
                            setup. Normally not modified.
     basetype_posthook_setup() - customization in basetype, after the object
                            has been created; Normally not modified.

     at_object_creation() - only called once, when object is first created.
                            Object customizations go here.
     at_object_delete() - called just before deleting an object. If returning
                            False, deletion is aborted. Note that all objects
                            inside a deleted object are automatically moved
                            to their <home>, they don't need to be removed here.

     at_init()            - called whenever typeclass is cached from memory,
                            at least once every server restart/reload
     at_first_save()
     at_cmdset_get(**kwargs) - this is called just before the command handler
                            requests a cmdset from this object. The kwargs are
                            not normally used unless the cmdset is created
                            dynamically (see e.g. Exits).
     at_pre_puppet(account)- (account-controlled objects only) called just
                            before puppeting
     at_post_puppet()     - (account-controlled objects only) called just
                            after completing connection account<->object
     at_pre_unpuppet()    - (account-controlled objects only) called just
                            before un-puppeting
     at_post_unpuppet(account) - (account-controlled objects only) called just
                            after disconnecting account<->object link
     at_server_reload()   - called before server is reloaded
     at_server_shutdown() - called just before server is fully shut down

     at_access(result, accessing_obj, access_type) - called with the result
                            of a lock access check on this object. Return value
                            does not affect check result.

     at_pre_move(destination)             - called just before moving object
                        to the destination. If returns False, move is cancelled.
     announce_move_from(destination)         - called in old location, just
                        before move, if obj.move_to() has quiet=False
     announce_move_to(source_location)       - called in new location, just
                        after move, if obj.move_to() has quiet=False
     at_post_move(source_location)          - always called after a move has
                        been successfully performed.
     at_pre_object_leave(leaving_object, destination, **kwargs)
     at_object_leave(obj, target_location, move_type="move", **kwargs)
     at_object_leave(obj, target_location)   - called when an object leaves
                        this object in any fashion
     at_pre_object_receive(obj, source_location)
     at_object_receive(obj, source_location, move_type="move", **kwargs) - called when this object receives
                        another object
     at_post_move(source_location, move_type="move", **kwargs)

     at_traverse(traversing_object, target_location, **kwargs) - (exit-objects only)
                              handles all moving across the exit, including
                              calling the other exit hooks. Use super() to retain
                              the default functionality.
     at_post_traverse(traversing_object, source_location) - (exit-objects only)
                              called just after a traversal has happened.
     at_failed_traverse(traversing_object)      - (exit-objects only) called if
                       traversal fails and property err_traverse is not defined.

     at_msg_receive(self, msg, from_obj=None, **kwargs) - called when a message
                             (via self.msg()) is sent to this obj.
                             If returns false, aborts send.
     at_msg_send(self, msg, to_obj=None, **kwargs) - called when this objects
                             sends a message to someone via self.msg().

     return_appearance(looker) - describes this object. Used by "look"
                                 command by default
     at_desc(looker=None)      - called by 'look' whenever the
                                 appearance is requested.
     at_pre_get(getter, **kwargs)
     at_get(getter)            - called after object has been picked up.
                                 Does not stop pickup.
     at_pre_give(giver, getter, **kwargs)
     at_give(giver, getter, **kwargs)
     at_pre_drop(dropper, **kwargs)
     at_drop(dropper, **kwargs)          - called when this object has been dropped.
     at_pre_say(speaker, message, **kwargs)
     at_say(message, msg_self=None, msg_location=None, receivers=None, msg_receivers=None, **kwargs)

     at_look(target, **kwargs)
     at_desc(looker=None)

    """

    pass
