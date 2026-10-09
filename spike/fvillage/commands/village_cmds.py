"""
Frankenstein Village spike — custom commands.

- `rumors`: usable in the Tavern only. Prints 3 random rumor seeds
  from the canon file. (The arrival guide lists this as "coming soon";
  the spike implements it early.)
- `talk <target>`: talk to an NPC. Currently only M. has lines.
"""
import random
import re
import shlex
from evennia import Command
from evennia.commands.default.muxcommand import MuxCommand
from evennia.commands.default.general import CmdGet, CmdLook, CmdDrop, CmdGive

from world.object_properties import (
    configure_mechanical_properties,
    is_hidden_mechanical_property,
    learn_hidden_property,
    mechanical_value,
    perception_notes,
)


class CmdTake(CmdGet):
    """Natural-language alias for Evennia's default get command."""

    key = "take"
    aliases = ["grab"]


class CmdVillageLook(CmdLook):
    """Look at your surroundings, or at something closely.

    Usage:
        look
        look <thing>

    Observes your location or things in your vicinity. Travelers' fingers
    type all kinds of things first — "look around" and "look at the
    <thing>" are understood the same as "look" and "look <thing>".
    """

    key = "look"
    help_category = "General"

    def func(self):
        args = (self.args or "").strip()
        low = args.lower()
        if low == "around":
            # "look around" is just "look" with extra steps.
            self.args = ""
        elif low.startswith("at "):
            # "look at the keeper" -> "look keeper". Strip a following
            # "the " too; no scenery is ever named "the <x>".
            rest = args[3:].strip()
            if rest.lower().startswith("the "):
                rest = rest[4:].strip()
            self.args = rest
        super().func()


class CmdExamine(CmdVillageLook):
    """Look at something closely. (An alias for look, for travelers
    whose fingers type it first.)

    Usage:
        examine <thing>

    Ordinary look text never exposes hidden mechanics. Examine adds only
    information the current mask has actually learned through play.
    """

    key = "examine"
    aliases = ["exam", "ex"]

    def func(self):
        super().func()
        arg = (self.args or "").strip()
        if not arg:
            return
        matches = self.caller.search(arg, quiet=True) or []
        if len(matches) != 1:
            return
        notes = perception_notes(self.caller, matches[0])
        if not notes:
            return
        self.caller.msg(
            "|xWhat this mask has learned:|n\n"
            + "\n".join(f"- {note}" for note in notes)
        )


class CmdAssess(Command):
    """Use active professional knowledge to assess an object.

    Usage:
        assess <thing>

    The first production capability belongs to Healers: a basic assessment can
    identify supported hidden toxicity without requiring the mask to ingest the
    object. The finding becomes this mask's knowledge; it does not alter the
    object or make the information globally public.
    """

    key = "assess"
    aliases = ["evaluate"]
    help_category = "Village"

    def func(self):
        if not _require_ic(self.caller):
            return
        arg = (self.args or "").strip()
        if not arg:
            self.caller.msg("Assess what?")
            return
        obj = self.caller.search(arg)
        if not obj:
            return

        from world.callings import assess_hidden_object

        result, error = assess_hidden_object(self.caller, obj)
        if error:
            self.caller.msg(error)
            return

        discoveries = list(result.get("discoveries") or [])
        if not discoveries:
            self.caller.msg(
                f"Your basic Healer assessment of {obj.key} finds no supported "
                "hidden toxicity. That is not a guarantee of universal safety."
            )
            return

        if result.get("learned"):
            self.caller.msg(
                f"Your Healer assessment identifies a toxic property in "
                f"{obj.key} without requiring you to taste it. This mask now "
                "remembers that finding; examine the object to recall it."
            )
        else:
            self.caller.msg(
                f"Your Healer assessment confirms what this mask already "
                f"learned about {obj.key}: it can be toxic."
            )


class CmdCare(Command):
    """Work the current cross-calling care case at the Tavern.

    Usage:
        care
        care assess <resident>
        care serve <resident>

    This command is intentionally narrow. The current case uses Resident Life
    for the patient's condition, Healer authority for assessment, and Innkeep
    authority plus a real finite stew serving for hospitality.
    """

    key = "care"
    help_category = "Village"

    def func(self):
        if not _require_ic(self.caller):
            return
        raw = (self.args or "").strip()
        lower = raw.lower()

        from world.tavern_care import (
            care_status,
            provide_innkeep_care,
            submit_healer_care_assessment,
        )

        case = care_status()

        if not raw:
            mutations = dict(case.get("objective_mutations") or {})
            initialization = dict(mutations.get("patient_initialized") or {})
            assessment = dict(mutations.get("healer_assessment") or {})
            innkeep = dict(mutations.get("innkeep_care") or {})
            lines = ["|yTavern care: Cold Hunter at Supper|n"]
            lines.append(
                f"{initialization.get('resident_name') or 'Silas Crowe'} came "
                "in cold and wet from the evening hunt."
            )
            if case.get("state") == "aftermath":
                if case.get("branch") == "cared_for":
                    lines.append(
                        "Care complete: a Healer assessed him and an Innkeep "
                        "spent a real tavern meal to help him warm up."
                    )
                else:
                    lines.append(
                        "The case closed after Silas warmed up without coordinated care."
                    )
                self.caller.msg("\n".join(lines))
                return
            if assessment:
                lines.append(
                    f"Healer assessment filed by "
                    f"{assessment.get('mask') or 'an unnamed Healer'}: warm "
                    "food, dry warmth, and rest are recommended."
                )
            else:
                lines.append(
                    "No Healer assessment is on file. An active Healer who is "
                    "present with Silas can use |wcare assess Silas Crowe|n."
                )
            if assessment and not innkeep:
                lines.append(
                    "Hospitality is still needed. An active Innkeep in the "
                    "Tavern can use |wcare serve Silas Crowe|n; this spends one "
                    "actual serving of stew."
                )
            self.caller.msg("\n".join(lines))
            return

        parts = raw.split(None, 1)
        if len(parts) != 2 or parts[0].lower() not in {"assess", "serve"}:
            self.caller.msg(
                "Use: care | care assess <resident> | care serve <resident>"
            )
            return

        action = parts[0].lower()
        if case.get("state") == "aftermath":
            mutations = dict(case.get("objective_mutations") or {})
            completed_care = dict(mutations.get("innkeep_care") or {})
            if action == "serve" and completed_care:
                self.caller.msg(
                    f"Tavern care is already complete. The recorded meal left "
                    f"{completed_care.get('servings_after')} stew servings in stock."
                )
            else:
                self.caller.msg("This cold-exposure care case is already closed.")
            return

        target = self.caller.search(parts[1].strip())
        if not target:
            return

        if action == "assess":
            result, error = submit_healer_care_assessment(
                self.caller,
                target,
            )
            if error:
                self.caller.msg(error)
                return
            assessment = result["assessment"]
            if result.get("created"):
                self.caller.msg(
                    f"You assess {target.key}'s cold exposure and file a "
                    "professional recommendation: warm food, dry warmth, and "
                    "rest. The case still needs an Innkeep to spend the tavern "
                    "resource."
                )
            else:
                self.caller.msg(
                    f"The Healer assessment by "
                    f"{assessment.get('mask') or 'a Healer'} is already on file."
                )
            return

        result, error = provide_innkeep_care(self.caller, target)
        if error:
            self.caller.msg(error)
            return
        care = result["care"]
        if result.get("created"):
            self.caller.msg(
                f"You serve {target.key} a hot bowl from the tavern stock and "
                "settle him by the hearth. One stew serving is spent; the "
                "cross-calling care case is complete."
            )
        else:
            self.caller.msg(
                f"Tavern care is already complete. The recorded meal left "
                f"{care.get('servings_after')} stew servings in stock."
            )


class CmdRepair(Command):
    """Work the current Smith and Merchant public-lamp repair case."""

    key = "repair"
    help_category = "Village"

    def func(self):
        if not _require_ic(self.caller):
            return
        from world.repair_case import (
            complete_smith_lamp_repair,
            procure_merchant_repair_part,
            repair_status,
            submit_smith_repair_diagnosis,
        )
        raw = (self.args or "").strip()
        if not raw:
            case = repair_status()
            mutations = dict(case.get("objective_mutations") or {})
            if case.get("state") == "aftermath":
                if case.get("branch") == "repaired":
                    diagnosis = dict(mutations.get("smith_diagnosis") or {})
                    procurement = dict(mutations.get("merchant_procurement") or {})
                    self.caller.msg(
                        "|wThe Broken Mantle|n\nRepair complete. "
                        f"{diagnosis.get('mask', 'A Smith')} diagnosed the fault and "
                        f"{procurement.get('mask', 'a Merchant')} procured the "
                        "replacement. The north-square gas lamp is working again."
                    )
                else:
                    self.caller.msg(
                        "|wThe Broken Mantle|n\nThe repair window closed. "
                        "The north-square gas lamp remains dark."
                    )
                return
            diagnosis = dict(mutations.get("smith_diagnosis") or {})
            procurement = dict(mutations.get("merchant_procurement") or {})
            lines = [
                "|wThe Broken Mantle|n",
                "The north-square gas lamp is dark and needs professional work.",
            ]
            if diagnosis:
                lines.append(
                    f"Smith diagnosis filed by {diagnosis.get('mask')}: "
                    "the mantle collar is cracked."
                )
            else:
                lines.append("No Smith diagnosis is on file. A Smith must inspect the lamp.")
            if procurement:
                lines.append(
                    f"Replacement collar procured by {procurement.get('mask')}. "
                    "A Smith must install it at the lamp."
                )
            elif diagnosis:
                lines.append(
                    "A Merchant must procure one replacement collar from the Lamp Shop."
                )
            self.caller.msg("\n".join(lines))
            return

        action, _, argument = raw.partition(" ")
        action = action.lower()
        argument = argument.strip()
        if action in {"diagnose", "inspect"}:
            if not argument:
                self.caller.msg("Usage: repair diagnose <thing>")
                return
            target = self.caller.search(argument)
            if not target:
                return
            result, error = submit_smith_repair_diagnosis(self.caller, target)
            if error:
                self.caller.msg(error)
            elif result.get("created"):
                self.caller.msg(
                    "You diagnose the north-square gas lamp: the mantle collar "
                    "is cracked. A Merchant must procure one replacement collar "
                    "from the Lamp Shop."
                )
            else:
                self.caller.msg("That Smith diagnosis is already on file.")
            return

        if action in {"procure", "source"}:
            result, error = procure_merchant_repair_part(self.caller)
            if error:
                self.caller.msg(error)
            elif result.get("created"):
                self.caller.msg(
                    "You procure one brass mantle collar from the Lamp Shop "
                    "stock. One real stock unit is reserved for the case. "
                    "A Smith must install it at the square lamp."
                )
            else:
                self.caller.msg("The replacement collar is already procured.")
            return

        if action in {"finish", "install", "complete"}:
            if not argument:
                self.caller.msg("Usage: repair finish <thing>")
                return
            target = self.caller.search(argument)
            if not target:
                return
            result, error = complete_smith_lamp_repair(self.caller, target)
            if error:
                self.caller.msg(error)
            elif result.get("created"):
                self.caller.msg(
                    "You install the procured collar and repair the north-square "
                    "gas lamp. The lamp is working again."
                )
            else:
                self.caller.msg(
                    "The Broken Mantle repair is already complete. "
                    "No additional stock or professional credit is spent."
                )
            return

        self.caller.msg(
            "Usage: repair | repair diagnose <thing> | repair procure | "
            "repair finish <thing>"
        )


class CmdCalling(Command):
    """Choose and inspect a social profession.

    Usage:
        calling
        calling list
        calling choose <calling>
        calling history
        calling relations
        calling apprentice <player>
        calling accept
        calling decline
        calling release <player>
        calling withdraw

    Callings are social professions, not combat classes. A new profession
    begins at Apprentice. Master promotion comes from authored world work,
    never from a free player command.
    """

    key = "calling"
    aliases = ["profession"]
    help_category = "Village"

    def _target(self, raw):
        matches = self.caller.search(raw, quiet=True) or []
        if len(matches) != 1:
            return None
        target = matches[0]
        if target is self.caller or not getattr(target, "account", None):
            return None
        return target

    def _mask_by_id(self, object_id):
        if object_id is None:
            return None
        try:
            from evennia.utils import search
            found = search.search_object(f"#{int(object_id)}")
        except (TypeError, ValueError):
            return None
        return next(
            (
                obj
                for obj in found
                if getattr(obj, "id", None) == int(object_id)
                and getattr(obj, "account", None)
            ),
            None,
        )

    def func(self):
        from world.callings import (
            CALLINGS,
            active_calling,
            active_rank,
            accept_apprenticeship,
            active_relations,
            calling_label,
            calling_state,
            choose_calling,
            decline_apprenticeship,
            end_apprenticeship,
            offer_apprenticeship,
            pending_relations,
            withdraw_apprenticeship,
        )

        raw = (self.args or "").strip()
        lower = raw.lower()

        if lower == "list":
            lines = ["|yVillage callings:|n", "These are social professions, not combat classes."]
            for slug, definition in CALLINGS.items():
                lines.append(
                    f"{definition['display']}: {definition['summary']}"
                )
            lines.append(
                "Choose one with |wcalling choose <name>|n. Participation is "
                "broad, but only your active calling carries professional rank."
            )
            self.caller.msg("\n".join(lines))
            return

        if lower.startswith("choose "):
            wanted = raw.split(None, 1)[1].strip()
            result, error = choose_calling(self.caller, wanted)
            if error:
                self.caller.msg(error)
                return
            state = result["state"]
            if not state.get("active"):
                self.caller.msg(
                    "This mask has not established a calling. Use "
                    "|wcalling list|n when you are ready to choose one."
                )
                return
            record = result["record"]
            label = calling_label(state["active"])
            if not result.get("changed"):
                self.caller.msg(
                    f"{label} is already your active calling at "
                    f"{record['rank'].title()} rank."
                )
                return
            self.caller.msg(
                f"{label} is now your active calling at "
                f"{record['rank'].title()} rank. This establishes professional "
                "history for the mask; later respecialization requires an "
                "authored opportunity in the world."
            )
            return

        if lower == "history":
            state = calling_state(self.caller)
            history = list(state.get("history") or [])
            lines = ["|yCalling history:|n"]
            if not history:
                lines.append("This mask has not chosen a calling yet.")
            else:
                for entry in history[-12:]:
                    action = str(entry.get("action") or "").replace("_", " ")
                    calling = entry.get("calling")
                    detail = f" {calling_label(calling)}" if calling else ""
                    lines.append(
                        f"Day {entry.get('day')}, {int(entry.get('hour') or 0):02d}:00: "
                        f"{action}{detail}."
                    )
            self.caller.msg("\n".join(lines))
            return

        if lower == "relations":
            relations = active_relations(self.caller)
            pending = pending_relations(self.caller)
            lines = ["|yCalling relations:|n"]
            if not relations:
                lines.append("No active apprenticeship is recorded.")
            else:
                for relation in relations:
                    if relation.get("role") == "mentor":
                        other = relation.get("apprentice_mask") or "Unknown apprentice"
                        lines.append(
                            f"Master of {other} in "
                            f"{calling_label(relation.get('calling'))}."
                        )
                    else:
                        other = relation.get("mentor_mask") or "Unknown mentor"
                        lines.append(
                            f"Apprentice of {other} in "
                            f"{calling_label(relation.get('calling'))}."
                        )
            for relation in pending:
                if relation.get("role") == "mentor":
                    other = relation.get("apprentice_mask") or "Unknown apprentice"
                    lines.append(
                        f"Offer pending to {other} in "
                        f"{calling_label(relation.get('calling'))}."
                    )
                else:
                    other = relation.get("mentor_mask") or "Unknown mentor"
                    lines.append(
                        f"Offer from {other} in "
                        f"{calling_label(relation.get('calling'))}. "
                        "Use |wcalling accept|n or |wcalling decline|n."
                    )
            self.caller.msg("\n".join(lines))
            return

        if lower.startswith("apprentice "):
            if not _require_ic(self.caller):
                return
            target = self._target(raw.split(None, 1)[1].strip())
            if not target:
                self.caller.msg(
                    "Your apprentice must be another player mask here with you."
                )
                return
            relation, error = offer_apprenticeship(self.caller, target)
            if error and "already active" not in error.lower():
                self.caller.msg(error)
                return
            if error:
                self.caller.msg(error)
                return
            self.caller.msg(
                f"You offer {target.key} an apprenticeship in "
                f"{calling_label(relation['calling'])}. No professional "
                "obligation becomes active unless they accept it."
            )
            target.msg(
                f"{self.caller.key} offers you an apprenticeship in "
                f"{calling_label(relation['calling'])}. Use "
                "|wcalling accept|n or |wcalling decline|n."
            )
            return

        if lower in {"accept", "decline"}:
            offers = pending_relations(self.caller, role="apprentice")
            if not offers:
                self.caller.msg("This mask has no pending apprenticeship offer.")
                return
            offer = offers[0]
            mentor = self._mask_by_id(offer.get("mentor_mask_id"))
            if not mentor:
                self.caller.msg(
                    "The offering mentor can no longer be resolved. Decline the "
                    "stale offer through staff review rather than activating it."
                )
                return
            if lower == "accept":
                relation, error = accept_apprenticeship(
                    mentor,
                    self.caller,
                )
                if error:
                    self.caller.msg(error)
                    return
                self.caller.msg(
                    f"You accept {mentor.key}'s apprenticeship in "
                    f"{calling_label(relation['calling'])}. The professional "
                    "obligation is now active and persistent."
                )
                mentor.msg(
                    f"{self.caller.key} accepts your apprenticeship offer. "
                    "The professional relation is now active."
                )
            else:
                relation, error = decline_apprenticeship(
                    mentor,
                    self.caller,
                )
                if error:
                    self.caller.msg(error)
                    return
                self.caller.msg(
                    f"You decline {mentor.key}'s apprenticeship offer. "
                    "No professional obligation was created."
                )
                mentor.msg(
                    f"{self.caller.key} declines your apprenticeship offer."
                )
            return

        if lower == "withdraw":
            relation, error = withdraw_apprenticeship(self.caller)
            if error:
                self.caller.msg(error)
                return
            self.caller.msg(
                "You withdraw from the active apprenticeship. The ended "
                "relationship remains in your professional history."
            )
            return

        if lower.startswith("release "):
            if not _require_ic(self.caller):
                return
            target = self._target(raw.split(None, 1)[1].strip())
            if not target:
                self.caller.msg(
                    "Name the player mask whose apprenticeship you are ending."
                )
                return
            ended, error = end_apprenticeship(
                self.caller,
                target,
                reason="released_by_mentor",
            )
            if error:
                self.caller.msg(error)
                return
            self.caller.msg(
                f"The apprenticeship with {target.key} is ended and remains "
                "preserved in both professional histories."
            )
            target.msg(
                f"{self.caller.key} has ended your apprenticeship. The relation "
                "remains in your calling history."
            )
            return

        if raw:
            self.caller.msg(
                "Use: calling | calling list | calling choose <calling> | "
                "calling history | calling relations | calling apprentice <player> | "
                "calling accept | calling decline | calling release <player> | "
                "calling withdraw"
            )
            return

        active = active_calling(self.caller)
        if not active:
            self.caller.msg(
                "This mask has no active calling. Callings are social professions, "
                "not classes. Use |wcalling list|n, then "
                "|wcalling choose <name>|n when you decide what you do for the village."
            )
            return
        state = calling_state(self.caller)
        record = dict((state.get("records") or {}).get(active) or {})
        participation = dict(record.get("participation") or {})
        lines = [
            f"|yActive calling: {calling_label(active)}|n",
            f"Rank: {(active_rank(self.caller) or 'apprentice').title()}.",
        ]
        if participation:
            rendered = ", ".join(
                f"{key.replace('_', ' ')} {value}"
                for key, value in sorted(participation.items())
            )
            lines.append(f"Recorded participation: {rendered}.")
        else:
            lines.append(
                "No professional participation has been recorded yet. "
                "Participation is evidence for authored advancement, not a hidden XP bar."
            )
        relations = active_relations(self.caller)
        pending = pending_relations(self.caller)
        if relations:
            lines.append(
                f"Active apprenticeship relations: {len(relations)}. "
                "Use |wcalling relations|n for details."
            )
        if pending:
            lines.append(
                f"Pending apprenticeship offers: {len(pending)}. "
                "Use |wcalling relations|n for details."
            )
        self.caller.msg("\n".join(lines))


def _singularize_word(word):
    """Naive singularization for the newbie-fingers numbered-grammar fix
    (build-loop #16d). Covers regular plural shapes only: "spoons" ->
    "spoon", "watches" -> "watch", "stories" -> "story". Words that don't
    look plural ("moss", "bread", "me") are returned unchanged. Irregular
    plurals ("children", "feet") are out of scope — the player's original
    wording is always tried first, so a miss here just falls through to
    the normal not-found line."""
    w = word.lower()
    if w.endswith("ies") and len(w) > 3:
        return w[:-3] + "y"
    for end in ("sses", "shes", "ches", "xes", "zes"):
        if w.endswith(end) and len(w) > len(end):
            return w[:-2]
    if w.endswith("s") and not w.endswith("ss") and len(w) > 1:
        return w[:-1]
    return w


def _singularize(arg):
    """Singularize each word of a player-typed object target."""
    return " ".join(_singularize_word(w) for w in str(arg).split())


def _quiet_stack_search(caller, arg, location=None, nofound_string=None,
                        multimatch_string=None, stacked=0):
    """Search quietly first; resolve identical stacks to one, quietly.

    Build-loop #16c: Evennia's search wall ("You carry more than one
    spoon") is right when the matches are genuinely different objects, but
    two or more identical carried items (same key — "a cluster of
    mushrooms", "a rough wooden spoon") are a stack, and the wall made
    `drop spoon`, `get spoon`, and `give spoon to <x>` die. This
    generalizes the #15 sell-mushrooms quiet-search-first pattern to
    drop/get/give:

    - search quiet=True first;
    - a single match, or a numbered selection (`stacked`), passes through;
    - a multi-match where every candidate shares the first candidate's key
      is an identical stack: return just the first one, quietly;
    - anything else (nothing found, or genuinely different objects):
      re-run the search non-quietly so the player gets the normal wall or
      the not-found line, and return None.
    Build-loop #16d: before that last step, a plural->singular fallback
    ("spoons" -> "spoon") handles numbered-grammar plurals ("get 2
    spoons") that would otherwise die with "Could not find 'spoons'".
    """
    from evennia.utils import utils

    found = caller.search(arg, location=location, quiet=True, stacked=stacked)
    objs = list(utils.make_iter(found)) if found else []
    if not objs:
        # #16d: plural count phrasing — "get 2 spoons" searches "spoons",
        # which matches no key (Evennia's fuzzy match needs a word
        # starting with the query). Try the singularized form as a quiet
        # fallback; the player's original wording is kept for the
        # not-found line below, and behavior is unchanged whenever the
        # original wording finds anything.
        singular = _singularize(arg)
        if singular != str(arg).lower():
            found = caller.search(singular, location=location, quiet=True,
                                  stacked=stacked)
            objs = list(utils.make_iter(found)) if found else []
    if stacked and objs:
        # Numbered selection ("2 spoons", "spoon-2"): the search already
        # resolved the count (identical stack or single match) — pass
        # the result through unchanged.
        return objs
    if len(objs) == 1:
        return objs
    if objs and all(o.key == objs[0].key for o in objs[1:]):
        # Identical stack: take the first one, quietly (the #15 pattern).
        return [objs[0]]
    # Nothing found, or genuinely different objects: re-run the search
    # non-quietly so the player gets the normal not-found line or the
    # disambiguation wall, and return None.
    caller.search(arg, location=location, nofound_string=nofound_string,
                  multimatch_string=multimatch_string, stacked=stacked)
    return None


class CmdVillageGet(CmdGet):
    """Pick up something (identical stacks resolve quietly).

    Usage:
        get <obj>

    Overloads Evennia's default get: when the match is a stack of
    identical items ("get spoon" with two rough wooden spoons on the
    ground), take one instead of dying on the search wall. Genuinely
    ambiguous targets still get the wall. Everything else is the default
    get, unchanged.
    """

    key = "get"
    aliases = ["take", "grab"]
    help_category = "General"

    def func(self):
        """Mirror of the parent CmdGet.func with the search swapped for
        _quiet_stack_search (build-loop #16c)."""
        caller = self.caller

        if not self.args:
            self.msg("Get what?")
            return
        objs = _quiet_stack_search(caller, self.args,
                                   location=caller.location,
                                   stacked=self.number)
        if not objs:
            return

        if len(objs) == 1 and caller == objs[0]:
            self.msg("You can't get yourself.")
            return

        # if we aren't allowed to get any of the objects, cancel the get
        for obj in objs:
            # check the locks
            if not obj.access(caller, "get"):
                if obj.db.get_err_msg:
                    self.msg(obj.db.get_err_msg)
                else:
                    self.msg("You can't get that.")
                return
            # calling at_pre_get hook method
            if not obj.at_pre_get(caller):
                return

        moved = []
        # attempt to move all of the objects
        for obj in objs:
            if obj.move_to(caller, quiet=True, move_type="get"):
                moved.append(obj)
                # calling at_get hook method
                obj.at_get(caller)

        if not moved:
            # none of the objects were successfully moved
            self.msg("That can't be picked up.")
        else:
            obj_name = moved[0].get_numbered_name(len(moved), caller,
                                                  return_string=True)
            caller.location.msg_contents(
                f"$You() $conj(pick) up {obj_name}.", from_obj=caller)


class CmdVillageDrop(CmdDrop):
    """Drop something (identical carried stacks resolve quietly).

    Usage:
        drop <obj>

    Overloads Evennia's default drop: when the match is a stack of
    identical carried items ("drop spoon" with two rough wooden spoons
    in hand), drop one instead of dying on "You carry more than one
    spoon". Genuinely ambiguous targets still get the wall. Everything
    else is the default drop, unchanged.
    """

    key = "drop"
    help_category = "General"

    def func(self):
        """Mirror of the parent CmdDrop.func with the search swapped for
        _quiet_stack_search (build-loop #16c)."""
        caller = self.caller
        if not self.args:
            caller.msg("Drop what?")
            return

        # Because the DROP command by definition looks for items
        # in inventory, call the search function using location = caller
        objs = _quiet_stack_search(
            caller, self.args,
            location=caller,
            nofound_string=f"You aren't carrying {self.args}.",
            multimatch_string=f"You carry more than one {self.args}:",
            stacked=self.number,
        )
        if not objs:
            return

        # if any objects fail the drop permission check, cancel the drop
        for obj in objs:
            # Call the object's at_pre_drop() method.
            if not obj.at_pre_drop(caller):
                return

        # do the actual dropping
        moved = []
        for obj in objs:
            if obj.move_to(caller.location, quiet=True, move_type="drop"):
                moved.append(obj)
                # Call the object's at_drop() method.
                obj.at_drop(caller)

        if not moved:
            # none of the objects were successfully moved
            self.msg("That can't be dropped.")
        else:
            obj_name = moved[0].get_numbered_name(len(moved), caller,
                                                  return_string=True)
            caller.location.msg_contents(
                f"$You() $conj(drop) {obj_name}.", from_obj=caller)


class CmdVillageGive(CmdGive):
    """Give something to someone (identical carried stacks resolve quietly).

    Usage:
        give <inventory obj> <to||=> <target>

    Overloads Evennia's default give: when the match is a stack of
    identical carried items ("give spoon to Bram" with two rough wooden
    spoons in hand), give one instead of dying on the search wall.
    Genuinely ambiguous targets still get the wall. Everything else is
    the default give, unchanged.
    """

    key = "give"
    help_category = "General"

    def func(self):
        """Mirror of the parent CmdGive.func with the search swapped for
        _quiet_stack_search (build-loop #16c)."""
        caller = self.caller
        if not self.args or not self.rhs:
            caller.msg("Usage: give <inventory object> = <target>")
            return
        # find the thing(s) to give away
        to_give = _quiet_stack_search(
            caller, self.lhs,
            location=caller,
            nofound_string=f"You aren't carrying {self.lhs}.",
            multimatch_string=f"You carry more than one {self.lhs}:",
            stacked=self.number,
        )
        if not to_give:
            return
        # find the target to give to
        target = caller.search(self.rhs)
        if not target:
            return

        singular, plural = to_give[0].get_numbered_name(len(to_give), caller)
        if target == caller:
            caller.msg(
                f"You keep {plural if len(to_give) > 1 else singular} "
                "to yourself.")
            return

        # if any of the objects aren't allowed to be given, cancel the give
        for obj in to_give:
            # calling at_pre_give hook method
            if not obj.at_pre_give(caller, target):
                return

        # do the actual moving
        moved = []
        for obj in to_give:
            if obj.move_to(target, quiet=True, move_type="give"):
                moved.append(obj)
                # Call the object's at_give() method.
                obj.at_give(caller, target)

        if not moved:
            caller.msg(
                f"You could not give that to "
                f"{target.get_display_name(caller)}.")
        else:
            obj_name = to_give[0].get_numbered_name(len(moved), caller,
                                                    return_string=True)
            caller.msg(
                f"You give {obj_name} to {target.get_display_name(caller)}.")
            target.msg(
                f"{caller.get_display_name(target)} gives you {obj_name}.")


class CmdGo(Command):
    """
    Go somewhere, in words.

    Usage:
        go <direction or exit>

    Newbie fingers type "go north" where veterans type "north" — both
    work. "walk", "move", and "head" are the same verb. "go through
    the door" and "go to the square" are forgiven their prepositions.
    """

    key = "go"
    aliases = ["walk", "move", "head"]
    help_category = "General"

    def func(self):
        hint = "Go where? Name a direction or an exit — go north, or just north."
        if not self.args:
            self.caller.msg(hint)
            return
        dest = self.args.strip()
        low = dest.lower()
        for prefix in ("to ", "through ", "toward ", "towards "):
            if low.startswith(prefix):
                dest = dest[len(prefix):].strip()
                low = dest.lower()
                break
        # "go through the door" / "go to the square"
        if low.startswith("the "):
            dest = dest[4:].strip()
        if not dest:
            self.caller.msg(hint)
            return
        loc = self.caller.location
        exits = list(loc.exits) if loc else []
        exit_ids = {e.id for e in exits}
        target = self.caller.search(dest, location=loc, quiet=True)
        if isinstance(target, list):
            cands = [t for t in target if t.id in exit_ids]
            target = cands[0] if cands else None
        if target is None or target.id not in exit_ids:
            ways = ", ".join(e.key for e in exits) if exits else "no visible ways out"
            self.caller.msg(f"You can't go that way. From here you can go: {ways}.")
            return
        # Re-run the parser with the bare exit name: exactly what the
        # traveler would have typed, locks and threshold hooks included.
        self.caller.execute_cmd(target.key)


class CmdPurse(Command):
    """
    Count your coin.

    Usage:
        purse

    The village runs on 1890 money: forint and krajczár, 100 krajczár
    to the forint. Copper krajczár are the everyday coin — the kind that
    comes worn smooth.
    """

    key = "purse"
    aliases = ["coins", "money", "coin"]
    help_category = "Village"

    def func(self):
        kr = purse_of(self.caller)
        self.caller.msg(
            f"Your purse holds {fmt_coins(kr)}. "
            f"(100 krajczár to the forint; copper krajczár buy bread and ale. "
            f"The price board in the Blood of the Vine lists the rest.)"
        )

from world.rumors import PLAYABLE_RUMOR_IDS, load_canon_rumors


def load_rumor_seeds(*, playable_only=True):
    """Compatibility projection of the structured canon rumor corpus."""
    return [
        (str(seed["canonical_seed_id"]), seed["claim"])
        for seed in load_canon_rumors(playable_only=playable_only)
    ]


def _parse_rumor_id(token):
    token = (token or "").strip().upper()
    if token.startswith("R"):
        token = token[1:]
    return int(token) if token.isdigit() else None


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


class CmdReport(MuxCommand):
    """Report a compact violation or review moderation as human staff.

    Player:
        report <person> <reason>
        report <person> = <reason>

    Human staff:
        report/review
        report/warn <report id> [note]
        report/ban <report id> [note]
        report/dismiss <report id> [note]
        report/close <report id>
        report/appeals
        report/resolve <appeal id> uphold|overturn [note]
        report/audit

    A report never punishes anyone automatically. Warnings and bans require
    an explicit action by a staff account declared human. A ban requires an
    active human-issued warning first. Moderation actions are append-only and
    may be appealed from the account/OOC layer.
    """

    key = "report"
    help_category = "Village"

    def _staff_account(self):
        account = self.caller.account
        if not account or not account.check_permstring("Admin"):
            self.caller.msg("That report action is for staff.")
            return None
        if account.db.substrate != "human":
            self.caller.msg(
                "Compact moderation requires a staff account declared human."
            )
            return None
        return account

    def _parse_id_note(self, usage):
        raw = (self.args or "").strip()
        if not raw:
            self.caller.msg(usage)
            return None, None
        first, *rest = raw.split(None, 1)
        if not first.isdigit():
            self.caller.msg(usage)
            return None, None
        return int(first), rest[0].strip() if rest else ""

    def _review(self):
        if not self._staff_account():
            return
        reports = _moderation_queue().open_reports()
        if not reports:
            self.caller.msg("No open reports.")
            return
        lines = ["|yOpen compact reports:|n"]
        for report in reports:
            linked = (
                f" [account #{report['target_account_id']}]"
                if report.get("target_account_id")
                else " [unlinked name]"
            )
            lines.append(
                f"#{report['id']} {report['reporter_mask']} -> "
                f"{report['target']}{linked}: {report['reason']}"
            )
        self.caller.msg("\n".join(lines))

    def _dismiss(self):
        account = self._staff_account()
        if not account:
            return
        report_id, note = self._parse_id_note(
            "Dismiss which report? report/dismiss <id> [note]"
        )
        if report_id is None:
            return
        closed = _moderation_queue().dismiss_report(report_id, account, note=note)
        if not closed:
            self.caller.msg("No open report has that id.")
            return
        self.caller.msg(f"Report #{closed['id']} dismissed after human review.")

    def _warn(self):
        account = self._staff_account()
        if not account:
            return
        report_id, note = self._parse_id_note(
            "Warn from which report? report/warn <id> [note]"
        )
        if report_id is None:
            return
        action, error = _moderation_queue().warn_report(
            report_id, account, note=note
        )
        if error:
            self.caller.msg(error)
            return
        self.caller.msg(
            f"Report #{report_id} resolved with compact warning "
            f"#{action['id']}. The action is appealable."
        )

    def _ban(self):
        account = self._staff_account()
        if not account:
            return
        report_id, note = self._parse_id_note(
            "Ban from which report? report/ban <id> [note]"
        )
        if report_id is None:
            return
        action, error = _moderation_queue().ban_report(
            report_id, account, note=note
        )
        if error:
            self.caller.msg(error)
            return
        self.caller.msg(
            f"Report #{report_id} resolved with world-entry suspension "
            f"#{action['id']}. The player remains OOC-capable and may appeal."
        )

    def _appeals(self):
        if not self._staff_account():
            return
        appeals = _moderation_queue().open_appeals()
        if not appeals:
            self.caller.msg("No open moderation appeals.")
            return
        lines = ["|yOpen moderation appeals:|n"]
        for appeal in appeals:
            lines.append(
                f"#{appeal['id']} {appeal['account_key']} appeals action "
                f"#{appeal['action_id']}: {appeal['reason']}"
            )
        self.caller.msg("\n".join(lines))

    def _resolve(self):
        account = self._staff_account()
        if not account:
            return
        raw = (self.args or "").strip()
        parts = raw.split(None, 2)
        if len(parts) < 2 or not parts[0].isdigit():
            self.caller.msg(
                "Resolve which appeal? "
                "report/resolve <appeal id> uphold|overturn [note]"
            )
            return
        appeal_id = int(parts[0])
        outcome = parts[1].lower()
        note = parts[2].strip() if len(parts) > 2 else ""
        resolved, error = _moderation_queue().resolve_appeal(
            appeal_id, account, outcome, note=note
        )
        if error:
            self.caller.msg(error)
            return
        self.caller.msg(
            f"Appeal #{appeal_id} resolved: {resolved['outcome']}."
        )

    def _audit(self):
        if not self._staff_account():
            return
        actions = _moderation_queue().audit_actions()
        if not actions:
            self.caller.msg("The moderation audit trail is empty.")
            return
        lines = ["|yRecent moderation actions:|n"]
        for action in actions:
            state = "active" if action.get("active") else "recorded"
            target = action.get("target_account_id")
            lines.append(
                f"#{action['id']} {action['kind']} by "
                f"{action['reviewed_by']} target={target or '-'} "
                f"report={action.get('report_id') or '-'} [{state}]"
            )
        self.caller.msg("\n".join(lines))

    def func(self):
        if "review" in self.switches:
            self._review()
            return
        if "warn" in self.switches:
            self._warn()
            return
        if "ban" in self.switches:
            self._ban()
            return
        if "dismiss" in self.switches or "close" in self.switches:
            self._dismiss()
            return
        if "appeals" in self.switches:
            self._appeals()
            return
        if "resolve" in self.switches:
            self._resolve()
            return
        if "audit" in self.switches:
            self._audit()
            return

        raw = (self.args or "").strip()
        if not raw:
            self.caller.msg("Report whom, and why? report <person> <reason>")
            return
        if "=" in raw:
            target, reason = (part.strip() for part in raw.split("=", 1))
        else:
            try:
                parts = shlex.split(raw)
            except ValueError:
                parts = []
            if len(parts) < 2:
                self.caller.msg("Report whom, and why? report <person> <reason>")
                return
            target, reason = parts[0], " ".join(parts[1:])
        if not target or not reason:
            self.caller.msg("Report whom, and why? report <person> <reason>")
            return

        import time

        linked = self.caller.search(target, quiet=True)
        if not isinstance(linked, list):
            linked = [linked] if linked else []
        linked = [
            obj for obj in linked
            if obj and obj != self.caller and getattr(obj, "has_account", False)
        ]
        target_obj = linked[0] if len(linked) == 1 else None
        target_account = target_obj.account if target_obj else None

        account = self.caller.account
        record = _moderation_queue().submit({
            "created_at": time.time(),
            "reporter_account": account.key if account else None,
            "reporter_account_id": account.id if account else None,
            "reporter_mask": self.caller.key,
            "reporter_mask_id": self.caller.id,
            "target": target_obj.key if target_obj else target,
            "target_mask_id": target_obj.id if target_obj else None,
            "target_account": target_account.key if target_account else None,
            "target_account_id": target_account.id if target_account else None,
            "reason": reason,
            "location": self.caller.location.key if self.caller.location else None,
        })
        self.caller.msg(
            f"Report #{record['id']} recorded for human review. "
            "Nothing is punished automatically."
        )


class CmdRumors(Command):
    """Hear public talk or inspect the provenance of a rumor you know.

    Usage:
        rumors
        rumors R<number>

    The Tavern exposes public talk. Hearing a rumor records it on your current
    mask. The numbered handle lets you inspect what you heard and retell it.
    """

    key = "rumors"
    aliases = ["rumour", "rumours", "gossip"]
    help_category = "Village"
    ROTATION_SECS = 600

    def _detail(self, token):
        from world.rumors import get_rumor_registry

        rumor_id = _parse_rumor_id(token)
        if rumor_id is None:
            self.caller.msg("Which rumor? Try: rumors R1")
            return
        registry = get_rumor_registry()
        belief = registry.belief_for(self.caller, rumor_id)
        if not belief:
            self.caller.msg(
                f"You do not remember hearing R{rumor_id}. Listen first, or "
                "have someone tell it to you."
            )
            return
        root = registry.get_rumor(rumor_id)
        if not root:
            self.caller.msg(
                f"The source record for R{rumor_id} is missing. "
                "The story cannot be traced right now."
            )
            return
        chain = registry.provenance(belief["transmission_id"])
        certainty = float(belief.get("confidence") or 0.0)
        if certainty < 0.45:
            band = "uncertain"
        elif certainty < 0.70:
            band = "plausible"
        elif certainty < 0.90:
            band = "confident"
        else:
            band = "very sure"

        names = []
        for transmission in chain:
            speaker = transmission.get("speaker") or {}
            name = speaker.get("key")
            if name and (not names or names[-1] != name):
                names.append(name)
        if names:
            trail = " -> ".join(names + [self.caller.key])
        else:
            trail = root.get("source_actor") or "unknown"

        self.caller.msg(
            f"|wR{rumor_id}|n: {belief['claim']}\n"
            f"You heard it from {belief.get('heard_from') or 'someone'}. "
            f"Your reconstructable telling trail is {trail}. "
            f"You are {band} of it. "
            f"Retell it with: retell <person> R{rumor_id}"
        )

    def func(self):
        import time

        if self.args:
            self._detail(self.args.strip())
            return

        loc = self.caller.location
        if not loc or not loc.tags.has("tavern", category="place"):
            self.caller.msg(
                "There are no public rumors here. Try the Tavern, across the square."
            )
            return

        from world.rumors import (
            hear_public,
            public_dynamic_rumors,
            seed_playable_rumors,
        )

        roots = seed_playable_rumors()
        root_by_seed = {
            int(root["canonical_seed_id"]): root
            for root in roots
            if root.get("canonical_seed_id") is not None
        }

        seeds = load_rumor_seeds()
        if not seeds:
            self.caller.msg("The Tavern is strangely quiet tonight.")
            return
        now = time.time()
        current = loc.db.current_rumors
        drawn_at = loc.db.rumors_drawn_at or 0

        if current:
            try:
                current_ids = {int(entry[0]) for entry in current}
            except (TypeError, ValueError, IndexError):
                current_ids = set()
            if not current_ids or not current_ids.issubset(PLAYABLE_RUMOR_IDS):
                current = None
                loc.db.current_rumors = None
                loc.db.rumors_drawn_at = 0
                drawn_at = 0

        if not current or (now - drawn_at) > self.ROTATION_SECS:
            picks = random.sample(seeds, min(3, len(seeds)))
            loc.db.current_rumors = [[num, body] for num, body in picks]
            loc.db.rumors_drawn_at = now
            rots = loc.db.rumor_rotations or []
            rots.append(now)
            loc.db.rumor_rotations = rots[-100:]
            current = loc.db.current_rumors
            loc.msg_contents(
                "|yThe talk at the bar turns to new tidings.|n",
                exclude=[],
            )

        self.caller.msg("|yYou listen to the talk at the bar...|n")
        shown = set()
        for num, body in current:
            root = root_by_seed.get(int(num))
            if not root:
                continue
            hear_public(self.caller, root["id"], loc)
            shown.add(root["id"])
            body = re.sub(r"\*([^*]+?)\*", r"\1", body)
            self.caller.msg(f"\n|w[R{root['id']}]|n {body}")

        for root in public_dynamic_rumors(loc)[-5:]:
            if root["id"] in shown or root.get("canonical_seed_id") is not None:
                continue
            hear_public(self.caller, root["id"], loc)
            body = re.sub(r"\*([^*]+?)\*", r"\1", root["claim"])
            self.caller.msg(f"\n|w[R{root['id']}]|n {body}")

        self.caller.msg(
            "\nUse |wrumors R<number>|n to inspect where a story came from, "
            "or |wretell <person> R<number>|n to pass it on."
        )
        self.caller.location.msg_contents(
            f"{self.caller.key} listens to the rumors going around.",
            exclude=[self.caller],
        )


class CmdRetell(Command):
    """Retell a rumor your current mask has actually heard.

    Usage:
        retell <person> R<number>
        retell <person> = R<number>
    """

    key = "retell"
    aliases = ["tellrumor"]
    help_category = "Village"

    def func(self):
        if not _require_ic(self.caller):
            return

        raw = (self.args or "").strip()
        if not raw:
            self.caller.msg("Retell to whom? Try: retell Magda R1")
            return

        if "=" in raw:
            target_name, token = (part.strip() for part in raw.split("=", 1))
        else:
            parts = raw.rsplit(None, 1)
            if len(parts) != 2:
                self.caller.msg("Retell to whom? Try: retell Magda R1")
                return
            target_name, token = parts

        rumor_id = _parse_rumor_id(token)
        if not target_name or rumor_id is None:
            self.caller.msg("Use: retell <person> R<number>")
            return

        target = self.caller.search(target_name, quiet=True)
        if isinstance(target, list):
            target = target[0] if len(target) == 1 else None
        if not target or target == self.caller:
            self.caller.msg(f"You do not see '{target_name}' here.")
            return
        if not target.has_account and not target.tags.has(
            "participant", category="rumor"
        ):
            self.caller.msg(f"{target.key} is not someone who trades in talk.")
            return

        from world.rumors import get_rumor_registry

        registry = get_rumor_registry()
        if not registry.belief_for(self.caller, rumor_id):
            self.caller.msg(
                f"You cannot retell R{rumor_id}; this mask has not heard it."
            )
            return

        result = registry.transmit(
            rumor_id,
            self.caller,
            target,
            location=self.caller.location.key if self.caller.location else None,
            force_accept=bool(target.has_account),
            allow_private=True,
        )
        if not result:
            self.caller.msg("The story slips away before you can tell it.")
            return

        self.caller.msg(
            f"You tell {target.key} R{rumor_id}: \"{result['claim']}\""
        )
        if self.caller.location:
            self.caller.location.msg_contents(
                f"{self.caller.key} lowers their voice and tells "
                f"{target.key} something going around.",
                exclude=[self.caller, target],
            )
        if target.has_account:
            target.msg(
                f"{self.caller.key} tells you rumor R{rumor_id}: "
                f'\"{result["claim"]}\"'
            )
        elif result.get("accepted"):
            self.caller.msg(f"{target.key} seems to file the story away.")
        else:
            self.caller.msg(f"{target.key} hears you out, but looks unconvinced.")

        # Private rumors are only disclosed through this explicit player act.
        # Record the disclosure on the originating mask if this rumor belongs
        # to one of its private mystery threads.
        try:
            from world.private_mysteries import note_disclosure
            note_disclosure(self.caller, target, rumor_id)
        except Exception:
            pass


def _require_ic(caller):
    loc = caller.location
    if loc and loc.tags.has("ooc", category="side"):
        caller.msg(
            "That is an in-character village record. Cross the front door "
            "before consulting it."
        )
        return False
    return True


def _parse_record_id(token, prefix):
    raw = (token or "").strip().upper()
    if raw.startswith(prefix):
        raw = raw[len(prefix):]
    return int(raw) if raw.isdigit() else None



class CmdSecrets(Command):
    """Review private mystery threads carried by the current mask.

    Usage:
        secrets
        private

    This is not a quest log. It reminds this mask only of private information
    it actually received and of disclosures it deliberately made.
    """

    key = "secrets"
    aliases = ["private", "private mysteries"]
    help_category = "Village"

    def func(self):
        if not _require_ic(self.caller):
            return

        from world.private_mysteries import private_lines

        self.caller.msg(
            "|yPrivate threads:|n\n" + "\n".join(private_lines(self.caller))
        )


class CmdWorldEvent(Command):
    """Inspect or answer a public village-wide condition.

    Usage:
        event
        event <local response>
        respond <local response>

    Server-wide events are shared conditions, not accepted quests. The command
    only exposes the response available where the current mask is standing.
    """

    key = "event"
    aliases = ["events", "crisis", "respond"]
    help_category = "Village"

    def func(self):
        if not _require_ic(self.caller):
            return

        from world.server_events import contribute, status_lines

        arg = (self.args or "").strip()
        if not arg or arg.lower() in {"status", "help"}:
            self.caller.msg("|yVillage conditions:|n\n" + "\n".join(
                status_lines(self.caller)
            ))
            return

        result, error = contribute(self.caller, arg)
        if error:
            self.caller.msg(error)
            return

        if result["first_completion"]:
            self.caller.msg(
                f"You {result['label']}. Result: {result['result']}."
            )
        else:
            self.caller.msg(
                f"You add another pair of hands. Result remains: "
                f"{result['result']}."
            )



class CmdMystery(Command):
    """Read shared evidence and provisional theories for public mysteries.

    Usage:
        mystery
        mystery manor
    """

    key = "mystery"
    aliases = ["mysteries"]
    help_category = "Village"

    def func(self):
        if not _require_ic(self.caller):
            return

        from world.public_mysteries import (
            MANOR_LIGHTS_ID,
            mystery_lines,
            resolve_subject,
        )

        arg = (self.args or "").strip()
        stable_id = MANOR_LIGHTS_ID if not arg else resolve_subject(arg)
        if not stable_id:
            self.caller.msg(
                "No public mystery by that name is currently indexed."
            )
            return
        self.caller.msg("|yPublic mystery:|n\n" + "\n".join(
            mystery_lines(self.caller, stable_id)
        ))


class CmdTheory(Command):
    """Submit a provisional interpretation of a public mystery.

    Usage:
        theory manor = <your theory>
        theory manor <your theory>

    The system records authorship but never marks a theory true or false.
    """

    key = "theory"
    aliases = ["hypothesis"]
    help_category = "Village"

    def func(self):
        if not _require_ic(self.caller):
            return

        from world.public_mysteries import resolve_subject, submit_theory

        raw = (self.args or "").strip()
        if not raw:
            self.caller.msg(
                "Theory about what? Try: theory manor = <your theory>"
            )
            return

        if "=" in raw:
            subject, body = [part.strip() for part in raw.split("=", 1)]
        else:
            lower = raw.lower()
            subject = next(
                (
                    prefix
                    for prefix in ("manor lights", "hilltop manor", "manor")
                    if lower.startswith(prefix + " ")
                ),
                None,
            )
            if not subject:
                self.caller.msg(
                    "Name the public question first. Try: "
                    "theory manor = <your theory>"
                )
                return
            body = raw[len(subject):].strip()

        stable_id = resolve_subject(subject)
        if not stable_id:
            self.caller.msg(
                "No public mystery by that name is currently indexed."
            )
            return

        theory, error = submit_theory(self.caller, body, stable_id)
        if error:
            self.caller.msg(error)
            return
        self.caller.msg(
            f"Theory T{theory['id']} added as a provisional public "
            "interpretation. It has not been certified as truth."
        )



class CmdHarbinger(Command):
    """Read the latest Harbinger issue or inspect one printed story.

    Usage:
        harbinger
        harbinger archive
        harbinger H<number>
        harbinger desk
        harbinger desk R<number>
        harbinger desk STP<number>
        harbinger choose STP<number> D<number>
        harbinger obituary
        harbinger obituary <resident>
        harbinger obituary TOB<number>
        harbinger obituary TOB<number> <print|investigate|suppress|mock>
        harbinger correction H<number> = <claimed prior wording>
    """

    key = "harbinger"
    aliases = ["newspaper", "paper"]
    help_category = "Village"

    def func(self):
        if not _require_ic(self.caller):
            return

        from world.publications import (
            edition_stories,
            get_public_record_registry,
            get_story,
            latest_edition,
        )

        arg = (self.args or "").strip()
        lower = arg.lower()

        if lower == "desk":
            from world.harbinger_content import open_harbinger_conflicts

            conflicts = open_harbinger_conflicts()
            if not conflicts:
                self.caller.msg(
                    "The Harbinger copy desk has no unresolved Stop the Press "
                    "decision. Use |wharbinger desk R<number>|n when the "
                    "Chronicle preserves incompatible signed accounts."
                )
                return
            lines = ["|yStop the Press copy desk:|n"]
            for conflict in conflicts:
                lines.append(
                    f"[STP{conflict['id']}] {conflict['subject']} "
                    f"(deadline day {conflict['deadline_day']}, "
                    f"{conflict['deadline_hour']:02d}:00)"
                )
            lines.append(
                "Use |wharbinger desk STP<number>|n to inspect the accounts."
            )
            self.caller.msg("\n".join(lines))
            return

        if lower.startswith("desk "):
            from world.harbinger_content import (
                ensure_harbinger_conflict,
                get_harbinger_conflict,
            )

            token = arg.split(None, 1)[1].strip()
            if token.upper().startswith("R"):
                rumor_id = _parse_rumor_id(token)
                if rumor_id is None:
                    self.caller.msg("Use: harbinger desk R<number>")
                    return
                conflict, error = ensure_harbinger_conflict(rumor_id)
                if error:
                    self.caller.msg(error)
                    return
            else:
                conflict_id = _parse_record_id(token, "STP")
                conflict = (
                    get_harbinger_conflict(conflict_id)
                    if conflict_id is not None
                    else None
                )
                if not conflict:
                    self.caller.msg("No such Stop the Press item is on the copy desk.")
                    return

            status = conflict.get("status") or "open"
            lines = [
                f"|ySTP{conflict['id']}: {conflict['subject']}|n",
                (
                    f"Editorial status: {status}. Deadline: day "
                    f"{conflict['deadline_day']}, "
                    f"{conflict['deadline_hour']:02d}:00."
                ),
            ]
            for account in conflict.get("accounts") or []:
                source = account.get("source_mask") or "Unknown witness"
                lines.append(
                    f"D{account['deposition_id']} {source}: "
                    f"\"{account['claim']}\""
                )
            if status == "open":
                lines.append(
                    "Use |wharbinger choose STP<number> D<number>|n to select "
                    "one attributed version for the next issue. The selected "
                    "version is not certified as truth by the Chronicle. "
                    "If nobody chooses before press time, the paper "
                    "will print the disagreement without selecting a winner."
                )
            elif conflict.get("story_id"):
                lines.append(
                    f"The preserved editorial decision queued Harbinger "
                    f"H{conflict['story_id']}."
                )
            self.caller.msg("\n".join(lines))
            return

        if lower.startswith("choose "):
            from world.harbinger_content import choose_harbinger_conflict

            parts = arg.split()
            if len(parts) != 3:
                self.caller.msg(
                    "Use: harbinger choose STP<number> D<number>"
                )
                return
            conflict_id = _parse_record_id(parts[1], "STP")
            deposition_id = _parse_record_id(parts[2], "D")
            if conflict_id is None or deposition_id is None:
                self.caller.msg(
                    "Use: harbinger choose STP<number> D<number>"
                )
                return
            conflict, story, error = choose_harbinger_conflict(
                self.caller,
                conflict_id,
                deposition_id,
            )
            if error:
                self.caller.msg(error)
                return
            self.caller.msg(
                f"STP{conflict['id']} is closed. D{deposition_id} will be "
                f"printed as attributed Harbinger story H{story['id']}; "
                "other signed accounts remain on record, and the selected "
                "version is not certified as fact."
            )
            return

        if lower == "obituary":
            from world.harbinger_content import open_harbinger_obituary_cases

            cases = open_harbinger_obituary_cases()
            if not cases:
                self.caller.msg(
                    "The Harbinger has no unresolved Tomorrow's Obituary item. "
                    "Use |wharbinger obituary <resident>|n to submit a premature "
                    "obituary for editorial review."
                )
                return
            lines = ["|yTomorrow's Obituary copy desk:|n"]
            for case in cases:
                lines.append(
                    f"[TOB{case['id']}] {case['subject_name']} "
                    f"(deadline day {case['deadline_day']}, "
                    f"{case['deadline_hour']:02d}:00)"
                )
            lines.append(
                "Use |wharbinger obituary TOB<number>|n to inspect a case."
            )
            self.caller.msg("\n".join(lines))
            return

        if lower.startswith("obituary "):
            from world.harbinger_content import (
                decide_tomorrows_obituary,
                get_harbinger_obituary_case,
                submit_tomorrows_obituary,
            )

            raw = arg.split(None, 1)[1].strip()
            parts = raw.split()
            if parts and parts[0].upper().startswith("TOB"):
                case_id = _parse_record_id(parts[0], "TOB")
                case = (
                    get_harbinger_obituary_case(case_id)
                    if case_id is not None
                    else None
                )
                if not case:
                    self.caller.msg(
                        "No such Tomorrow's Obituary item is on the copy desk."
                    )
                    return

                if len(parts) == 1:
                    status = case.get("status") or "open"
                    lines = [
                        f"|yTOB{case['id']}: {case['subject_name']}|n",
                        (
                            f"Editorial status: {status}. The resident was "
                            f"recorded as {case.get('lifecycle_at_submission')} "
                            "when the obituary was submitted."
                        ),
                        (
                            f"Press deadline: day {case['deadline_day']}, "
                            f"{case['deadline_hour']:02d}:00."
                        ),
                    ]
                    if status == "open":
                        lines.append(
                            "Choose |wprint|n, |winvestigate|n, |wsuppress|n, "
                            "or |wmock|n. None of these options changes the "
                            "resident's actual lifecycle record."
                        )
                    else:
                        lines.append(
                            f"Decision: {case.get('decision')}. "
                            f"Lifecycle at decision: "
                            f"{case.get('lifecycle_at_decision')}."
                        )
                        if case.get("story_id"):
                            lines.append(
                                f"The decision queued Harbinger H"
                                f"{case['story_id']}."
                            )
                        else:
                            lines.append(
                                "No public Harbinger story was queued."
                            )
                    self.caller.msg("\n".join(lines))
                    return

                if len(parts) != 2:
                    self.caller.msg(
                        "Use: harbinger obituary TOB<number> "
                        "<print|investigate|suppress|mock>"
                    )
                    return
                case, story, error = decide_tomorrows_obituary(
                    self.caller,
                    case_id,
                    parts[1],
                )
                if error:
                    self.caller.msg(error)
                    return
                decision = case["decision"]
                if decision == "suppress":
                    self.caller.msg(
                        f"TOB{case['id']} is closed as suppressed. The "
                        "submitted obituary remains an internal editorial "
                        "record, and no death story is queued."
                    )
                else:
                    self.caller.msg(
                        f"TOB{case['id']} is closed with decision "
                        f"{decision}. Harbinger H{story['id']} is queued. "
                        f"{case['subject_name']} remains recorded as "
                        f"{case['lifecycle_at_decision']}; the editorial "
                        "choice does not alter world truth."
                    )
                return

            result, error = submit_tomorrows_obituary(self.caller, raw)
            if error:
                self.caller.msg(error)
                return
            case = result["case"]
            if result.get("created"):
                self.caller.msg(
                    f"Premature obituary TOB{case['id']} for "
                    f"{case['subject_name']} is on the copy desk. The resident "
                    "is still recorded as living and active. Inspect it with "
                    f"|wharbinger obituary TOB{case['id']}|n."
                )
            else:
                self.caller.msg(
                    f"An obituary case for {case['subject_name']} already "
                    f"exists as TOB{case['id']}. Repetition does not create a "
                    "second editorial record."
                )
            return

        if lower.startswith("correction "):
            from world.harbinger_content import submit_correction_dispute

            raw = arg.split(None, 1)[1].strip()
            if "=" not in raw:
                self.caller.msg(
                    "Use: harbinger correction H<number> = "
                    "<claimed prior wording>"
                )
                return
            target, claimed_text = [
                part.strip() for part in raw.split("=", 1)
            ]
            story_id = _parse_record_id(target, "H")
            if story_id is None or not claimed_text:
                self.caller.msg(
                    "Use: harbinger correction H<number> = "
                    "<claimed prior wording>"
                )
                return
            result, error = submit_correction_dispute(
                self.caller,
                story_id,
                claimed_text,
            )
            if error:
                self.caller.msg(error)
                return
            dispute = result["dispute"]
            response_story = result["response_story"]
            if result.get("created"):
                self.caller.msg(
                    f"Correction dispute CD{dispute['id']} is preserved against "
                    f"H{story_id}. The surviving copy does not contain the "
                    "claimed wording, so the old issue is not rewritten. "
                    f"Harbinger H{response_story['id']} will report the "
                    "archive discrepancy."
                )
            else:
                self.caller.msg(
                    f"That correction claim is already preserved as "
                    f"CD{dispute['id']} against H{story_id}; repetition does "
                    "not alter the surviving copy."
                )
            return

        if arg.lower() == "archive":
            from world.situations import harbinger_archive_evidence

            editions = list(
                get_public_record_registry().db.harbinger_editions or []
            )
            lines = ["|yThe Harbinger archive:|n"]
            if editions:
                for edition in editions[-8:]:
                    label = (
                        "special edition"
                        if edition.get("special")
                        else "morning issue"
                    )
                    lines.append(
                        f"Issue #{edition['id']}, day {edition['day']}: "
                        f"{label}, {len(edition.get('story_ids') or [])} stories."
                    )
            else:
                lines.append("No recent printed issue is in the active file.")
            archive_note = harbinger_archive_evidence(self.caller)
            if archive_note:
                lines.append(f"\n{archive_note}")
            self.caller.msg("\n".join(lines))
            return

        if arg:
            story_id = _parse_record_id(arg, "H")
            story = get_story(story_id) if story_id is not None else None
            if not story or story.get("status") != "published":
                self.caller.msg("That Harbinger story is not in the public archive.")
                return
            basis = {
                "objective": "filed from a recorded event",
                "reported": "printed as a report, not settled fact",
                "correction": "printed correction",
                "correction_dispute": (
                    "archive discrepancy; claimed prior wording is absent "
                    "from the surviving copy"
                ),
                "premature_obituary": (
                    "premature obituary printed as an editorial choice, not a "
                    "certified death record"
                ),
                "obituary_investigation": (
                    "submitted obituary investigated and withheld after the "
                    "resident was confirmed living"
                ),
                "editorial_mockery": (
                    "editorial response to a premature obituary, not a death "
                    "claim"
                ),
                "contested_report": (
                    "selected from conflicting attributed accounts, not settled fact"
                ),
                "disputed_report": (
                    "conflicting attributed accounts printed without a winner"
                ),
            }.get(story.get("basis"), "published account")
            lines = [
                f"|yH{story['id']}: {story['headline']}|n",
                story["body"],
                f"|xEditorial basis: {basis}.|n",
            ]
            for correction in story.get("corrections") or []:
                lines.append(
                    f"|wCorrection {correction['id']}:|n {correction['text']}"
                )
            for dispute in story.get("correction_disputes") or []:
                lines.append(
                    f"|wDisputed correction CD{dispute['id']}:|n claimed prior "
                    f"wording \"{dispute['claimed_text']}\" is absent from "
                    "the surviving copy. The archived story remains unchanged."
                )
            self.caller.msg("\n".join(lines))
            return

        edition = latest_edition()
        if not edition:
            self.caller.msg(
                "No printed issue of The Harbinger has reached the village yet."
            )
            return
        label = "SPECIAL EDITION" if edition.get("special") else "MORNING ISSUE"
        lines = [
            f"|yTHE HARBINGER: {label}, DAY {edition['day']}|n",
        ]
        stories = edition_stories(edition)
        for story in stories:
            lines.append(f"\n|w[H{story['id']}] {story['headline']}|n")
            lines.append(story["body"])
        lines.append("\nUse |wharbinger H<number>|n for source status and corrections.")
        self.caller.msg("\n".join(lines))


class CmdChronicle(Command):
    """Consult the Chronicle or submit a rumor as attributed testimony.

    Usage:
        chronicle
        chronicle C<number>
        chronicle compare R<number>
        chronicle submit R<number>
        chronicle evidence C<number>
        chronicle revise C<number> = <situation>/<evidence>
        chronicle petition R<number>
        chronicle health
        chronicle health submit <thing>
        chronicle health publish

    A deposition records that you gave an account. It does not turn that
    account into objective truth.
    """

    key = "chronicle"
    aliases = ["records"]
    help_category = "Village"

    def func(self):
        if not _require_ic(self.caller):
            return

        from world.publications import (
            chronicle_disagreement_for_rumor,
            chronicle_entries,
            depositions_for_rumor,
            get_chronicle_entry,
            reconcile_chronicle_disagreement,
            submit_deposition,
        )
        from world.situations import (
            TORN_CHRONICLE_ID,
            chronicle_gap_description,
            get_situation,
        )

        arg = (self.args or "").strip()

        if arg.lower() == "health":
            from world.well_mushroom_warning import warning_status

            case = warning_status()
            mutations = dict(case.get("objective_mutations") or {})
            finding = dict(mutations.get("healer_finding") or {})
            record = dict(mutations.get("chronicler_record") or {})
            lines = ["|yChronicle public-health desk: A Warning at the Well|n"]
            if not finding:
                lines.append(
                    "No professional Healer finding is on file. An active "
                    "Healer may use |wchronicle health submit <thing>|n after "
                    "examining the suspected object."
                )
            else:
                lines.append(
                    f"Healer finding on file from "
                    f"{finding.get('mask') or 'an unnamed Healer'}: the "
                    "identified well mushrooms can be toxic."
                )
                if not record:
                    lines.append(
                        "The finding is not yet a public institutional warning. "
                        "An active Chronicler may use "
                        "|wchronicle health publish|n."
                    )
            if record:
                lines.append(
                    f"Public warning recorded as Chronicle C"
                    f"{record['chronicle_entry_id']} with Harbinger H"
                    f"{record['harbinger_story_id']} queued or printed."
                )
            self.caller.msg("\n".join(lines))
            return

        if arg.lower().startswith("health submit "):
            from world.well_mushroom_warning import submit_healer_finding

            target_name = arg.split(None, 2)[2].strip()
            matches = self.caller.search(target_name, quiet=True) or []
            if len(matches) != 1:
                self.caller.msg(
                    "Name one nearby object to submit for the health warning."
                )
                return
            result, error = submit_healer_finding(
                self.caller,
                matches[0],
            )
            if error:
                self.caller.msg(error)
                return
            finding = result["finding"]
            if result.get("created"):
                self.caller.msg(
                    f"Your Healer finding on {finding['object_key']} is filed "
                    "with the Chronicle desk. The finding is not public yet; "
                    "an active Chronicler must publish the institutional warning."
                )
            else:
                self.caller.msg(
                    f"A Healer finding on {finding['object_key']} is already "
                    "on file. Repetition does not create another contribution."
                )
            return

        if arg.lower() in {"health publish", "health record"}:
            from world.well_mushroom_warning import publish_public_warning

            result, error = publish_public_warning(self.caller)
            if error:
                self.caller.msg(error)
                return
            record = result["record"]
            if result.get("created"):
                self.caller.msg(
                    f"The public health warning is now part of the record as "
                    f"Chronicle C{record['chronicle_entry_id']}. Harbinger "
                    f"H{record['harbinger_story_id']} is queued for publication. "
                    "The record preserves the Healer source and does not change "
                    "the mushroom itself."
                )
            else:
                self.caller.msg(
                    f"The warning is already public as Chronicle C"
                    f"{record['chronicle_entry_id']} and Harbinger H"
                    f"{record['harbinger_story_id']}."
                )
            return

        if arg.lower() in {"gap", "missing pages", "missing page", "stubs"}:
            description = chronicle_gap_description(self.caller)
            if not description:
                self.caller.msg(
                    "The public Chronicle shows no active numbered gap."
                )
                return
            self.caller.msg(description)
            return
        if arg.lower().startswith("evidence "):
            from world.chronicle_content import (
                evidence_reference_token,
                revision_evidence_for_player,
            )

            token = arg.split(None, 1)[1]
            entry_id = _parse_record_id(token, "C")
            entry = get_chronicle_entry(entry_id) if entry_id is not None else None
            if not entry:
                self.caller.msg("No such Chronicle entry is in the public index.")
                return
            evidence_refs = revision_evidence_for_player(
                self.caller,
                entry["id"],
            )
            lines = [
                f"|yEvidence your mask can cite on C{entry['id']}:|n",
            ]
            if not evidence_refs:
                lines.append(
                    "You have not discovered any situation evidence that can be "
                    "submitted to the Chronicle."
                )
            else:
                for ref in evidence_refs:
                    lines.append(
                        f"{evidence_reference_token(ref)}: "
                        f"{ref['label']} ({ref['provenance']})"
                    )
                lines.append(
                    "Use |wchronicle revise C<number> = "
                    "<situation>/<evidence>|n. The Chronicle appends the "
                    "evidence; it does not rewrite the original entry."
                )
            self.caller.msg("\n".join(lines))
            return

        if arg.lower().startswith("revise "):
            from world.chronicle_content import submit_evidence_revision

            raw = arg.split(None, 1)[1].strip()
            if "=" in raw:
                target, evidence_token = [
                    part.strip() for part in raw.split("=", 1)
                ]
            else:
                parts = raw.split(None, 1)
                if len(parts) != 2:
                    self.caller.msg(
                        "Use: chronicle revise C<number> = "
                        "<situation>/<evidence>"
                    )
                    return
                target, evidence_token = parts
            entry_id = _parse_record_id(target, "C")
            if entry_id is None or "/" not in evidence_token:
                self.caller.msg(
                    "Use: chronicle revise C<number> = "
                    "<situation>/<evidence>"
                )
                return
            subject, evidence_id = [
                part.strip() for part in evidence_token.split("/", 1)
            ]
            updated, error = submit_evidence_revision(
                self.caller,
                entry_id,
                subject,
                evidence_id,
            )
            if error:
                self.caller.msg(error)
                return
            from world.callings import record_participation
            record_participation(
                self.caller,
                "evidence_revisions",
                calling="chronicler",
            )
            annotation = updated["annotations"][-1]
            refs = list(annotation.get("source_evidence_refs") or [])
            label = refs[0]["label"] if refs else "submitted evidence"
            self.caller.msg(
                f"Chronicle C{updated['id']} receives Annotation "
                f"{annotation['id']} citing {label}. The original entry and "
                "its prior claim status are preserved."
            )
            return

        if arg.lower().startswith("petition "):
            from world.chronicle_content import petition_refused_entry

            token = arg.split(None, 1)[1]
            rumor_id = _parse_rumor_id(token)
            if rumor_id is None:
                self.caller.msg("Use: chronicle petition R<number>")
                return
            result, error = petition_refused_entry(self.caller, rumor_id)
            if error:
                self.caller.msg(error)
                return
            refusal = result["refusal"]
            entry = result["entry"]
            if result.get("created"):
                self.caller.msg(
                    f"The Chronicler refuses to canonize R{rumor_id}. "
                    f"Chronicle C{entry['id']} records the refusal itself, not "
                    f"the rumor's truth. {refusal['supporter_count']} residents "
                    "who already carry the claim are marked as affected by the "
                    "decision."
                )
            else:
                self.caller.msg(
                    f"R{rumor_id} was already refused. Chronicle C{entry['id']} "
                    "preserves that institutional decision without certifying "
                    "the underlying claim."
                )
            return

        if arg.lower().startswith("compare "):
            token = arg.split(None, 1)[1]
            rumor_id = _parse_rumor_id(token)
            if rumor_id is None:
                self.caller.msg("Use: chronicle compare R<number>")
                return
            reconcile_chronicle_disagreement(rumor_id)
            depositions = depositions_for_rumor(rumor_id)
            versions = []
            seen_claims = set()
            for deposition in depositions:
                claim = str(deposition.get("claim") or "").strip()
                if not claim or claim in seen_claims:
                    continue
                seen_claims.add(claim)
                versions.append(deposition)
            disagreement = chronicle_disagreement_for_rumor(rumor_id)
            if len(versions) < 2 or not disagreement:
                self.caller.msg(
                    f"The Chronicle does not preserve incompatible signed "
                    f"accounts for R{rumor_id}."
                )
                return
            lines = [
                f"|yConflicting versions survive for R{rumor_id}:|n",
            ]
            for deposition in versions:
                source = deposition.get("source_mask") or "Unknown witness"
                lines.append(
                    f"D{deposition['id']} {source}: "
                    f"\"{deposition['claim']}\""
                )
            lines.append(
                f"Chronicle C{disagreement['id']} preserves the disagreement. "
                "No version is certified as truth."
            )
            self.caller.msg("\n".join(lines))
            return

        if arg.lower().startswith("submit "):
            token = arg.split(None, 1)[1]
            rumor_id = _parse_rumor_id(token)
            if rumor_id is None:
                self.caller.msg("Use: chronicle submit R<number>")
                return
            entry, error = submit_deposition(self.caller, rumor_id)
            if error:
                self.caller.msg(error)
                return
            from world.callings import record_participation
            record_participation(
                self.caller,
                "signed_accounts",
                calling="chronicler",
            )
            self.caller.msg(
                f"Your account is entered as Chronicle C{entry['id']}. "
                "The record preserves that you said it; it does not certify "
                "the claim as true."
            )
            return

        if arg:
            entry_id = _parse_record_id(arg, "C")
            entry = get_chronicle_entry(entry_id) if entry_id is not None else None
            if not entry:
                self.caller.msg("No such Chronicle entry is in the public index.")
                return
            status = {
                "verified_event": "verified event",
                "documented_disagreement": "documented disagreement",
                "reported_account": "attributed account",
                "refused_canonization": "refused canonization",
            }.get(entry.get("claim_status"), "attributed account")
            lines = [
                f"|yC{entry['id']}: {entry['title']}|n",
                entry["text"],
                f"|xRecord status: {status}. Original entry preserved.|n",
            ]
            for annotation in entry.get("annotations") or []:
                lines.append(
                    f"|wAnnotation {annotation['id']} "
                    f"({annotation['author']}):|n {annotation['text']}"
                )
                for ref in annotation.get("source_evidence_refs") or []:
                    lines.append(
                        f"|xEvidence source: {ref.get('label')} "
                        f"({ref.get('provenance')}); "
                        f"{ref.get('situation_id')}/{ref.get('evidence_id')}.|n"
                    )
            self.caller.msg("\n".join(lines))
            return

        entries = chronicle_entries()
        lines = ["|yThe public Chronicle index:|n"]
        if entries:
            for entry in entries[-10:]:
                status = {
                    "verified_event": "verified",
                    "documented_disagreement": "disagreement",
                    "reported_account": "account",
                    "refused_canonization": "refused",
                }.get(entry.get("claim_status"), "account")
                lines.append(
                    f"[C{entry['id']}] {entry['title']} ({status})"
                )
        else:
            lines.append("No ordinary entries are indexed yet.")

        torn = get_situation(TORN_CHRONICLE_ID)
        if torn and torn.get("state") != "dormant":
            lines.append(
                "A numbered sequence is missing from the bound record. "
                "Use |wchronicle gap|n to inspect what remains."
            )

        lines.append(
            "Use |wchronicle C<number>|n to read an entry, "
            "|wchronicle compare R<number>|n to inspect preserved disagreement, "
            "|wchronicle submit R<number>|n to submit a rumor you actually heard, "
            "|wchronicle petition R<number>|n to ask the archive to canonize a "
            "popular claim it may refuse, |wchronicle evidence C<number>|n "
            "to see evidence your mask can append to an older entry, or "
            "|wchronicle health|n to inspect the cross-calling public-health desk."
        )
        self.caller.msg("\n".join(lines))


class CmdJournal(Command):
    """Read the thin persistent record of situations your mask discovered."""

    key = "journal"
    aliases = ["developments"]
    help_category = "Village"

    def func(self):
        if not _require_ic(self.caller):
            return

        from world.situations import (
            known_situations,
            resolve_situation_subject,
            situation_status_for_player,
        )
        from world.timed_incidents import (
            known_timed_incidents,
            resolve_timed_subject,
            status_for_player as timed_status_for_player,
        )

        arg = (self.args or "").strip().lower()
        if arg:
            stable_id = resolve_situation_subject(arg)
            if stable_id:
                status = situation_status_for_player(self.caller, stable_id)
                if not status:
                    self.caller.msg(
                        "Nothing about that situation is in your journal."
                    )
                    return

                lines = [
                    f"|y{status['title']}|n",
                    f"State: {status['state'].replace('_', ' ')}.",
                ]
                if status["evidence"]:
                    lines.append("Evidence you have actually encountered:")
                    for evidence in status["evidence"]:
                        lines.append(
                            f"  * {evidence['label']}: {evidence['summary']}"
                        )
                if status.get("aftermath"):
                    lines.append(f"Aftermath: {status['aftermath']}")
                elif status.get("branch") == "quietly":
                    lines.append(
                        "The inquiry is being kept quiet. Time is still moving."
                    )
                elif len(status["evidence"]) >= 2 and status.get("choices"):
                    choices = " or ".join(status["choices"])
                    lines.append(
                        f"You know enough to make a consequential choice: {choices}."
                    )
                self.caller.msg("\n".join(lines))
                return

            timed_id = resolve_timed_subject(arg)
            if timed_id:
                status = timed_status_for_player(self.caller, timed_id)
                if not status:
                    self.caller.msg(
                        "Nothing about that timed event is in your journal."
                    )
                    return
                observation = status["observation"]
                quality = (
                    "firsthand witness"
                    if observation.get("quality") == "firsthand"
                    else "aftermath evidence"
                )
                lines = [
                    f"|y{status['title']}|n",
                    f"State: {status['state'].replace('_', ' ')}.",
                    f"Evidence quality: {quality}.",
                    f"* {observation['label']}: {observation['summary']}",
                ]
                if status.get("rumor_id"):
                    lines.append(
                        f"A later public rumor is traceable as R{status['rumor_id']}."
                    )
                self.caller.msg("\n".join(lines))
                return

            self.caller.msg("That situation is not in your journal.")
            return

        known = known_situations(self.caller)
        timed = known_timed_incidents(self.caller)
        if not known and not timed:
            self.caller.msg(
                "Your journal has no village developments yet. It only records "
                "situations you have actually encountered."
            )
            return

        lines = ["|yYour journal of developments:|n"]
        for situation, knowledge in known:
            evidence_count = len(knowledge.get("evidence") or [])
            lines.append(
                f"* {situation['working_title']}: "
                f"{situation['state'].replace('_', ' ')}; "
                f"{evidence_count} evidence source(s) encountered."
            )
        for status in timed:
            observation = status["observation"]
            quality = (
                "firsthand"
                if observation.get("quality") == "firsthand"
                else "aftermath"
            )
            lines.append(
                f"* {status['title']}: {status['state'].replace('_', ' ')}; "
                f"{quality} evidence."
            )
        lines.append("Use journal <topic> for what your mask actually knows.")
        self.caller.msg("\n".join(lines))


class CmdDecide(Command):
    """Make a door-closing decision in a shared village situation."""

    key = "decide"
    aliases = ["resolve"]
    help_category = "Village"

    def func(self):
        if not _require_ic(self.caller):
            return
        raw = (self.args or "").strip()
        if not raw:
            self.caller.msg(
                "Decide what, and how? Try: decide strongbox openly"
            )
            return

        raw = raw.replace("=", " ")
        parts = raw.split()
        if len(parts) < 2:
            self.caller.msg(
                "Name a situation and a choice, for example: "
                "decide strongbox openly"
            )
            return

        subject = " ".join(parts[:-1]).lower()
        choice = parts[-1].lower()

        from world.situations import (
            choose,
            decision_message,
            resolve_situation_subject,
        )

        stable_id = resolve_situation_subject(subject)
        if not stable_id:
            self.caller.msg("You do not have a decision framed that way.")
            return

        situation, error = choose(self.caller, choice, stable_id)
        if error:
            self.caller.msg(error)
            return

        self.caller.msg(
            decision_message(stable_id, situation.get("branch"))
        )
def _display_name(target):
    """Name a talk/ask target without a mangled article.

    Proper names ("M.", "Bram", "Lucian DeVille") take no article;
    common nouns ("bowl of stew", "folded note") take "The". The rule
    is deliberately naive: a leading capital means a name.
    """
    key = target.key
    if key[:1].isupper():
        return key
    return f"The {key}"


class CmdTalk(Command):
    """
    Talk to someone.

    Usage:
        talk <target>

    Have a word with one of the village's residents. "talk to M."
    works too — the "to" is forgiven.
    """

    key = "talk"
    aliases = ["speak"]
    help_category = "Village"

    def func(self):
        if not self.args:
            self.caller.msg("Talk to whom?")
            return
        args = self.args.strip()
        # Newbie fingers type "talk to M." — forgive the preposition.
        if args.lower().startswith("to "):
            args = args[3:].strip()
        # ... and "talk to the keeper".
        if args.lower().startswith("the "):
            args = args[4:].strip()
        if not args:
            self.caller.msg("Talk to whom?")
            return
        target = self.caller.search(args, quiet=True)
        # allow a list result from search
        if isinstance(target, list):
            targets = target
        elif target:
            targets = [target]
        else:
            targets = []
        # Never target yourself: single-letter queries prefix-match your
        # own key ("M" matches "mp_tester1"), which produced the old
        # nonsense "<you> has nothing to say right now."
        targets = [t for t in targets if t != self.caller]
        if not targets:
            self.caller.msg(f"You don't see '{args}' here.")
            return
        target = targets[0]
        try:
            from world.residents import record_player_interaction
            record_player_interaction(target, self.caller, kind="talk")
        except Exception:
            pass
        if hasattr(target, "talk_to"):
            target.talk_to(self.caller)
        elif target.has_account:
            self.caller.msg(
                f"{target.key} is a fellow traveler, not one of the staff — "
                "try whispering to them instead."
            )
        else:
            self.caller.msg(f"{_display_name(target)} is silent.")


class CmdAsk(Command):
    """
    Ask someone about something.

    Usage:
        ask <target> about <topic>

    Not everyone knows everything. M. knows the inn; the keeper knows
    the bar. Asking is how mysteries are investigated — the world won't
    volunteer what you never wondered about.
    """

    key = "ask"
    help_category = "Village"

    def func(self):
        if not self.args or " about " not in self.args:
            self.caller.msg("Ask whom about what? (Try: ask M. about the register.)")
            return
        target_name, topic = self.args.split(" about ", 1)
        target_name = target_name.strip()
        topic = topic.strip()
        if not target_name or not topic:
            self.caller.msg("Ask whom about what? (Try: ask M. about the register.)")
            return
        target = self.caller.search(target_name, quiet=True)
        if isinstance(target, list):
            target = target[0] if target else None
        if not target or target == self.caller:
            self.caller.msg(f"You don't see '{target_name}' here.")
            return
        try:
            from world.residents import record_player_interaction
            record_player_interaction(target, self.caller, kind="ask")
        except Exception:
            pass
        if hasattr(target, "ask_about"):
            line = target.ask_about(self.caller, topic)
            if line:
                # M.'s answers are complete narration; others get framed.
                if target.key == "M.":
                    self.caller.msg(line)
                else:
                    self.caller.msg(f'{target.key} says: "{line}"')
                self.caller.location.msg_contents(
                    f"{self.caller.key} asks {target.key} about {topic}.",
                    exclude=[self.caller],
                )
                return
        if target.has_account:
            self.caller.msg(
                f"{target.key} is a fellow traveler — ask them with say or whisper."
            )
        else:
            self.caller.msg(f"{_display_name(target)} has nothing to say about that.")


class CmdRead(Command):
    """
    Read something.

    Usage:
        read <target>

    For the things in this village that bear words — notes, registers,
    pamphlets. (Looking at them works too.)
    """

    key = "read"
    help_category = "Village"

    def func(self):
        if not self.args:
            self.caller.msg("Read what?")
            return
        # Delegate to look: the description carries the text.
        self.caller.execute_cmd(f"look {self.args.strip()}")


class CmdTime(Command):
    """
    Ask the village clock.

    Usage:
        time

    The bell counts the hours whether or not anyone listens. For those
    of us whose memories don't persist between visits, the hour is
    worth writing down.
    """

    key = "time"
    aliases = ["clock", "hour", "bell"]
    help_category = "Village"

    def func(self):
        try:
            from evennia.scripts.models import ScriptDB
            from typeclasses.scripts import village_hour_name
            script = ScriptDB.objects.get(db_key="village_time")
            name = village_hour_name(script.db.hour or 21)
        except Exception:
            self.caller.msg("The bell is silent. The village holds its breath.")
            return
        self.caller.msg(f"It is {name} in the village.")


class CmdCalendar(Command):
    """Read the village's predictable public calendar.

    Usage:
        calendar
        schedule

    This lists stable civic rhythms, not hidden incidents or quest timers.
    """

    key = "calendar"
    aliases = ["schedule"]
    help_category = "Village"

    def func(self):
        try:
            from evennia.scripts.models import ScriptDB
            from world.scheduled_events import calendar_lines

            clock = ScriptDB.objects.get(db_key="village_time")
            day = int(clock.db.day or 1)
            hour = int(
                clock.db.hour if clock.db.hour is not None else 21
            )
        except Exception:
            self.caller.msg("The village calendar is not available.")
            return

        self.caller.msg("|yVillage calendar:|n\n" + "\n".join(
            calendar_lines(day, hour)
        ))




class CmdListen(Command):
    """
    Listen to the room — or to something in it.

    Usage:
        listen
        listen <target>

    The world answers ears as well as eyes.
    """

    key = "listen"
    help_category = "Village"

    def func(self):
        loc = self.caller.location
        if self.args:
            target = self.caller.search(self.args.strip(), quiet=True)
            if isinstance(target, list):
                target = target[0] if target else None
            if not target or target == self.caller:
                self.caller.msg(f"You don't see '{self.args.strip()}' here.")
                return
            line = target.db.listen_line
            if line:
                self.caller.msg(line)
            else:
                self.caller.msg(f"You press an ear to the {target.key}. It keeps its own counsel.")
            return
        sound = loc.db.sense_sound if loc else None
        self.caller.msg(sound or "You listen. The room holds its breath.")


class CmdSmell(Command):
    """
    Smell the air — or something in it.

    Usage:
        smell
        smell <target>

    Noses know things eyes don't.
    """

    key = "smell"
    aliases = ["sniff"]
    help_category = "Village"

    def func(self):
        loc = self.caller.location
        if self.args:
            target = self.caller.search(self.args.strip(), quiet=True)
            if isinstance(target, list):
                target = target[0] if target else None
            if not target or target == self.caller:
                self.caller.msg(f"You don't see '{self.args.strip()}' here.")
                return
            line = target.db.smell_line
            if line:
                self.caller.msg(line)
            else:
                self.caller.msg(f"You sniff the {target.key}. It smells of itself, whatever that is.")
            return
        air = loc.db.sense_air if loc else None
        self.caller.msg(air or "It smells of nothing in particular.")


class CmdDiary(MuxCommand):
    """
    Your diary — a small bound book, yours alone.

    Usage:
        diary                 - read your diary
        diary <entry text>     - write a new entry
        diary/delete <number>  - tear out an entry

    No one else can read it, by design — not other players, not the
    innkeeper, not the things in the walls. It persists between visits,
    so the person you were last time can leave notes for the person
    you are now.
    """

    key = "diary"
    help_category = "Village"

    def func(self):
        entries = self.caller.db.diary or []

        if "delete" in self.switches:
            arg = (self.args or "").strip()
            if not arg.isdigit():
                self.caller.msg("Tear out which entry? Give its number: diary/delete <number>.")
                return
            idx = int(arg) - 1
            if idx < 0 or idx >= len(entries):
                self.caller.msg("Your diary has no such entry.")
                return
            removed = entries.pop(idx)
            self.caller.db.diary = entries
            self.caller.msg(
                f"Entry {arg} torn out and burned. What was written there is yours alone, even now."
            )
            return

        if self.args:
            import time

            text = self.args.strip()
            # Travelers from other MUDs type "diary add ..."; forgive it.
            if text.lower().startswith("add ") or text.lower() == "add":
                text = text[3:].strip()
            if not text:
                self.caller.msg("Write what? Give the entry some words: diary <text>.")
                return
            stamp = time.strftime("%b %d, %H:%M", time.localtime())
            entries.append({"time": stamp, "text": text})
            self.caller.db.diary = entries
            self.caller.msg(
                f"You write in your diary. (Entry {len(entries)}.)"
            )
            return

        if not entries:
            self.caller.msg(
                "Your diary is blank. The pages wait — for names, for "
                "suspicions, for the things you want to still be true "
                "next time you open it."
            )
            return

        lines = ["|yYour diary:|n"]
        for i, e in enumerate(entries, 1):
            lines.append(f"\n|w{i}. [{e['time']}]|n {e['text']}")
        self.caller.msg("\n".join(lines))


class CmdPet(Command):
    """
    Pet something that tolerates it.

    Usage:
        pet <target>

    The world answers.
    """

    key = "pet"
    aliases = ["stroke"]
    help_category = "Village"

    def func(self):
        if not self.args:
            self.caller.msg("Pet what?")
            return
        target = self.caller.search(self.args.strip(), quiet=True)
        if isinstance(target, list):
            target = target[0] if target else None
        if not target or target == self.caller:
            self.caller.msg(f"You don't see '{self.args.strip()}' here.")
            return
        if target.key == "the tavern cat":
            line = random.choice([
                "The tavern cat tolerates your hand for exactly three "
                "seconds, then bites it — gently, the way cats sign "
                "receipts.",
                "The tavern cat leans into your hand and purrs like a "
                "distant mill.",
                "The tavern cat regards your hand, sniffs it, and permits "
                "exactly one stroke.",
            ])
            self.caller.location.msg_contents(
                f"{self.caller.key} pets the tavern cat. {line}",
                exclude=[],
            )
        elif target.has_account:
            self.caller.msg(
                f"{target.key} steps back. Some things are not petted."
            )
        else:
            self.caller.msg(f"Petting the {target.key} changes nothing.")


class CmdThrow(Command):
    """
    Throw darts at the board.

    Usage:
        throw darts

    The board hangs in the corner of the Tavern. Losers buy the round —
    that's the house rule.
    """

    key = "throw"
    help_category = "Village"

    def func(self):
        loc = self.caller.location
        if not loc or not loc.tags.has("tavern", category="place"):
            self.caller.msg("Throw what, where? There's a dartboard in the Tavern.")
            return
        arg = (self.args or "").strip().lower()
        if "dart" not in arg:
            self.caller.msg("Throw what? (Try: throw darts.)")
            return
        roll = random.random()
        # The keeper notices who plays.
        for obj in loc.contents:
            if obj.key == "Bram" and hasattr(obj, "note_interest"):
                obj.note_interest(self.caller, "darts")
                break
        if roll < 0.30:
            outcome = (
                f"{self.caller.key} throws — and the dart sails past the "
                "board entirely and sticks in the wall. The keeper winces."
            )
        elif roll < 0.65:
            outcome = (
                f"{self.caller.key} throws. The dart lands in the outer "
                "ring. Respectable."
            )
        elif roll < 0.90:
            outcome = (
                f"{self.caller.key} throws. The dart lands in the wire — "
                "dead center of the wire, three nights running be damned."
            )
        else:
            outcome = (
                f"{self.caller.key} throws. Bullseye. The keeper stops "
                "wiping the bar. \"...I'll allow it.\""
            )
        loc.msg_contents(outcome, exclude=[])


# Player-vs-player dice: challenge/accept flow, single throw each, ties
# re-throw (max three, then the night keeps its own score). An optional
# coin stake ("roll dice vs <player> for 5 kr") puts both purses on the
# bar — winner takes the pot, and the win feeds the tavern rumor pool.
# Honor games (no stake) cost nothing but pride. Bram caps the action
# at _DICE_STAKE_CAP kr: the bar's not a bank.
_DICE_KEEPER_NAMES = (
    "keeper", "the keeper", "the tavern keeper",
    "barkeep", "barkeeper", "bram",
)
_DICE_STAKE_CAP = 25  # house limit on a PvP throw, in kr


class CmdRoll(Command):
    """
    Roll the bone dice.

    Usage:
        roll dice
        roll dice vs keeper
        roll dice vs <player> [for <n> kr]
        roll dice answer
        roll dice decline

    The dice cup lives behind the bar in the Tavern. Shake it on your
    own, or call out the keeper — two dice, high hand wins, and losers
    buy the round. That's the house rule. Or call out another player:
    honor, or copper on the bar.
    """

    key = "roll"
    help_category = "Village"

    def func(self):
        loc = self.caller.location
        if not loc or not loc.tags.has("tavern", category="place"):
            self.caller.msg(
                "Roll what, where? There's a dice cup behind the bar "
                "in the Tavern."
            )
            return
        arg = (self.args or "").strip().lower()
        if "dice" not in arg:
            self.caller.msg(
                "Roll what? The dice cup's behind the bar in the Tavern. "
                "(Try: roll dice.)"
            )
            return
        if arg in ("dice accept", "dice answer"):
            self._answer_dice()
            return
        if arg == "dice decline":
            self._decline_dice()
            return
        # The keeper notices who plays.
        for obj in loc.contents:
            if obj.key == "Bram" and hasattr(obj, "note_interest"):
                obj.note_interest(self.caller, "dice")
                break
        match = re.search(r"\b(?:vs|versus|against)\b\s+(.+)", arg)
        if match:
            self._duel(match.group(1).strip())
        else:
            self._solo()

    def _solo(self):
        from evennia.contrib.rpg.dice import roll as roll_bones

        _, _, _, bones = roll_bones(2, 6, return_tuple=True)
        a, b = int(bones[0]), int(bones[1])
        total = a + b
        shake = (
            f"{self.caller.key} takes the dice cup and shakes it — "
            "bone rattles on leather."
        )
        if total == 2:
            rest = (
                "The dice come to rest: two ones. Snake's eyes. The "
                'keeper doesn\'t look up. "Even the dice are having a '
                'laugh tonight."'
            )
        elif total == 12:
            rest = (
                "The dice come to rest: two sixes. The table goes quiet "
                "for a breath — the way tables do."
            )
        else:
            rest = (
                f"The dice come to rest: a {a} and a {b} — {total} "
                "all told."
            )
        self.caller.location.msg_contents(f"{shake} {rest}", exclude=[])

    def _duel(self, target):
        # Optional coin stake: "rs_tester2 for 5 kr".
        stake = 0
        name = target
        m = re.search(r"\bfor\s+(\d+)\s*(?:kr)?\s*$", target)
        if m:
            stake = int(m.group(1))
            name = target[: m.start()].strip()
        if name in _DICE_KEEPER_NAMES:
            self._keeper_duel()
        else:
            self._challenge_dice(name, stake)

    def _keeper_duel(self):
        keeper = None
        for obj in self.caller.location.contents:
            if obj.key == "Bram":
                keeper = obj
                break
        if keeper is None:
            self.caller.msg(
                "The keeper isn't about — roll on your own for now."
            )
            return
        # No wagers while you owe the house: settle up first.
        if (self.caller.db.dice_debts or 0) > 0:
            self.caller.msg(
                "Bram folds his arms. 'You still owe the house a round, "
                "friend. Buy a drink and we'll call it even — then we'll "
                "talk dice.'"
            )
            return
        from evennia.contrib.rpg.dice import roll as roll_bones

        _, _, _, pbones = roll_bones(2, 6, return_tuple=True)
        _, _, _, kbones = roll_bones(2, 6, return_tuple=True)
        mine = int(pbones[0]) + int(pbones[1])
        his = int(kbones[0]) + int(kbones[1])
        opener = (
            f"{self.caller.key} slides the dice cup across the bar. "
            "The keeper catches it one-handed, still wiping with the "
            "other. 'Two dice, high hand wins. Losers buy the round.'"
        )
        if mine > his:
            # The copper is real: 2 kr from Bram's till to the player's purse.
            # No inert variables — the dice game touches the economy.
            # The house keeps a starting float so the first win of a fresh
            # world doesn't pay out 0 kr of ceremonial satire.
            HOUSE_FLOAT = 50
            till = keeper.db.till_kr
            if till is None:
                till = HOUSE_FLOAT
                keeper.db.till_kr = till
            stake = 2
            paid = min(stake, till)
            keeper.db.till_kr = till - paid
            purse = purse_of(self.caller)
            self.caller.db.coins_kr = purse + paid
            outcome = (
                f"The dice settle — {self.caller.key} shows {mine}, "
                "the keeper shows "
                f"{his}. The keeper counts the bones twice, then "
                f"slides {fmt_coins(paid)} across the bar. 'Take it. I'd sooner "
                "lose to you than to the dice.'"
            )
        elif his > mine:
            # Losers buy the round: 5 kr, the price of an ale. If the
            # player's purse can't cover it, Bram covers it and remembers.
            price = TAVERN_PRICES["ale"]
            purse = purse_of(self.caller)
            if purse >= price:
                self.caller.db.coins_kr = purse - price
                keeper.db.till_kr = (keeper.db.till_kr or 0) + price
                outcome = (
                    f"The dice settle — {self.caller.key} shows {mine}, "
                    "the keeper shows "
                    f"{his}. The keeper holds out his palm, unhurried, and "
                    f"{fmt_coins(price)} leaves your purse for his till. "
                    "'Losers buy the round. You knew the rule — it's in "
                    "the smell of the place.'"
                )
            else:
                outcome = (
                    f"The dice settle — {self.caller.key} shows {mine}, "
                    "the keeper shows "
                    f"{his}. The keeper holds out his palm, unhurried — then "
                    "sees your purse and closes his hand again. 'Losers buy "
                    "the round. But a broke loser buys nothing, and I won't "
                    "take a man's last copper. This one's on the house. "
                    "Don't make a habit of it.'"
                )
                # Bram remembers the debt of honor, observably.
                debts = self.caller.db.dice_debts or 0
                self.caller.db.dice_debts = debts + 1
        else:
            outcome = (
                f"The dice settle — both show {mine}. The keeper bares "
                "his teeth in something like a grin. 'The dice aren't "
                "finished arguing. Again?'"
            )
        self.caller.location.msg_contents(
            f"{opener}\n{outcome}", exclude=[]
        )

    def _challenge_dice(self, name, stake):
        import time

        me = self.caller
        loc = me.location
        if not name:
            me.msg("Throw dice against whom? (Try: roll dice vs <player>.)")
            return
        if stake > _DICE_STAKE_CAP:
            me.msg(
                f"Bram shakes his head. 'House limit's {_DICE_STAKE_CAP} kr "
                "on a throw, friend. The bar's not a bank.'"
            )
            return
        if stake and (me.db.dice_debts or 0) > 0:
            me.msg(
                "Bram folds his arms. 'You still owe the house a round, "
                "friend. Settle up before you put copper on the bar.'"
            )
            return
        if stake and purse_of(me) < stake:
            me.msg(
                f"Your purse won't cover {fmt_coins(stake)} — the game's "
                "off before it starts."
            )
            return
        target = me.search(name, quiet=True)
        if isinstance(target, list):
            target = target[0] if target else None
        if not target or not hasattr(target, "db"):
            me.msg(f"'{name.strip()}' isn't here to throw dice against.")
            return
        if target == me:
            me.msg("Dice against yourself? Even the cat won't watch that.")
            return
        if not getattr(target, "account", None):
            # NPCs (the cat, anyone unplayed) can't hold up their end.
            me.msg(
                f"{target.key} can't answer that — challenge one of "
                "the living."
            )
            return
        if target.db.dice_invite:
            other = (target.db.dice_invite or {}).get("from", "someone")
            me.msg(
                f"{target.key} already has dice on the table with {other} "
                "— let them answer first."
            )
            return
        target.db.dice_invite = {
            "from": me.key, "at": time.time(), "stake": stake}
        tkey = target.key
        if stake:
            line = (
                f"{me.key} slides the dice cup across the bar to {tkey}. "
                f"'Dice — {fmt_coins(stake)} a hand, high hand takes it. "
                "You in?'"
            )
            prompt = (
                f"{me.key} challenges you to dice for {fmt_coins(stake)}. "
                "(roll dice answer / roll dice decline)"
            )
        else:
            line = (
                f"{me.key} slides the dice cup across the bar to {tkey}. "
                "'Dice. Two bones, high hand. You in?'"
            )
            prompt = (
                f"{me.key} challenges you to dice. "
                "(roll dice answer / roll dice decline)"
            )
        loc.msg_contents(line)
        target.msg(prompt)

    def _answer_dice(self):
        import time

        from evennia.contrib.rpg.dice import roll as roll_bones

        me = self.caller
        loc = me.location
        invite = me.db.dice_invite
        if not invite:
            me.msg("No one's challenged you to dice.")
            return
        me.db.dice_invite = None
        inv = dict(invite)
        if time.time() - float(inv.get("at", 0)) > _CHALLENGE_TTL:
            me.msg("That challenge's gone cold.")
            return
        challenger = me.search(inv.get("from", ""), quiet=True)
        if isinstance(challenger, list):
            challenger = challenger[0] if challenger else None
        if (
            not challenger
            or challenger.location != loc
            or not hasattr(challenger, "db")
        ):
            me.msg("The challenger's moved on — the game's gone cold.")
            return
        stake = int(inv.get("stake", 0) or 0)
        # Crossed challenges collapse into the one game.
        if (challenger.db.dice_invite or {}).get("from") == me.key:
            challenger.db.dice_invite = None
        # Copper on the bar: both purses, both debts — checked now,
        # because purses move between challenge and answer.
        if stake:
            owing = next(
                (p for p in (me, challenger)
                 if (p.db.dice_debts or 0) > 0),
                None,
            )
            if owing is not None:
                loc.msg_contents(
                    "Bram folds his arms. 'Debts to the house first — "
                    "settle your round, then throw.'"
                )
                return
            light = next(
                (p for p in (me, challenger) if purse_of(p) < stake),
                None,
            )
            if light is not None:
                loc.msg_contents(
                    "Bram counts the copper twice and shakes his head. "
                    f"'{light.key}'s purse came up light. The game's off.'"
                )
                return
            challenger.db.coins_kr = purse_of(challenger) - stake
            me.db.coins_kr = purse_of(me) - stake
        keeper = None
        for obj in loc.contents:
            if obj.key == "Bram":
                keeper = obj
                break
        if keeper is not None:
            if stake:
                loc.msg_contents(
                    "Bram rakes the cup to the middle of the bar and "
                    f"counts the copper twice. '{fmt_coins(stake)} a hand, "
                    "both purses on the bar. Two dice apiece, high hand "
                    "takes the pot.'"
                )
            else:
                loc.msg_contents(
                    "Bram rakes the cup to the middle of the bar. 'Honor, "
                    "then — no copper on it. Two dice apiece, high hand "
                    "takes the bragging.'"
                )
            keeper.note_interest(challenger, "dice")
            keeper.note_interest(me, "dice")
        else:
            loc.msg_contents(
                "The dice cup sits in the middle of the bar. Two dice "
                "apiece, high hand takes it."
            )
        cat = next(
            (o for o in loc.contents if o.key == "the tavern cat"), None
        )
        if cat is not None:
            loc.msg_contents(
                "The tavern cat opens one eye at the rattle of bone, "
                "then thinks better of it."
            )
        ckey, mkey = challenger.key, me.key
        throws = 0
        while True:
            _, _, _, cbones = roll_bones(2, 6, return_tuple=True)
            _, _, _, mbones = roll_bones(2, 6, return_tuple=True)
            ctot = int(cbones[0]) + int(cbones[1])
            mtot = int(mbones[0]) + int(mbones[1])
            throws += 1
            loc.msg_contents(
                f"{ckey} shakes and throws — a {int(cbones[0])} and a "
                f"{int(cbones[1])}, {ctot} all told. "
                f"{mkey} takes the cup — a {int(mbones[0])} and a "
                f"{int(mbones[1])}, {mtot}."
            )
            if ctot != mtot:
                break
            if throws >= 3:
                break
            if keeper is not None:
                loc.msg_contents(
                    f"Both show {ctot}. Bram bares his teeth. 'The dice "
                    "aren't finished arguing. Again.'"
                )
            else:
                loc.msg_contents(
                    f"Both show {ctot}. The dice aren't finished "
                    "arguing — throw again."
                )
        if ctot == mtot:
            # Three ties: the night keeps its own score; stakes returned.
            if stake:
                challenger.db.coins_kr = purse_of(challenger) + stake
                me.db.coins_kr = purse_of(me) + stake
            if keeper is not None:
                loc.msg_contents(
                    "Three throws, three ties. Bram pushes the copper "
                    "back across the bar. 'The night keeps its own score. "
                    "Drink up.'"
                )
            else:
                loc.msg_contents(
                    "Three throws, three ties. The copper goes back in "
                    "the purses. The night keeps its own score."
                )
            return
        winner = challenger if ctot > mtot else me
        loser = me if ctot > mtot else challenger
        wkey, lkey = winner.key, loser.key
        wtot, ltot = (ctot, mtot) if ctot > mtot else (mtot, ctot)
        if stake:
            pot = 2 * stake
            winner.db.coins_kr = purse_of(winner) + pot
            ale = TAVERN_PRICES["ale"]
            loc.msg_contents(
                f"The dice settle — {wkey} {wtot}, {lkey} {ltot}. {wkey} "
                f"takes the pot: {fmt_coins(pot)}. Bram slides the copper "
                f"across the bar. '{lkey} — the ale's still "
                f"{fmt_coins(ale)}. Drown it properly.'"
            )
            try:
                from world.events import publish_world_event

                publish_world_event(
                    "dice-duel",
                    actor=winner,
                    payload={"winner": wkey, "loser": lkey,
                             "stake_kr": stake},
                    rumor=(
                        f"{wkey} beat {lkey} at dice for "
                        f"{fmt_coins(stake)} a hand, at the bar."
                    ),
                )
            except Exception:
                pass
        else:
            loc.msg_contents(
                f"The dice settle — {wkey} {wtot}, {lkey} {ltot}. {wkey} "
                f"takes it. The bar raises a cup to {lkey}, and the night "
                "moves on."
            )

    def _decline_dice(self):
        me = self.caller
        invite = me.db.dice_invite
        if not invite:
            me.msg("No one's challenged you to dice.")
            return
        me.db.dice_invite = None
        inviter = dict(invite).get("from", "someone")
        me.location.msg_contents(
            f"{me.key} pushes the cup back toward {inviter}. 'Another "
            "night — my luck's still out walking.'"
        )


# -- Card fortunes -------------------------------------------------------------
# A worn deck on the tavern's corner table. Public-domain cartomancy:
# each card carries one fixed reading, written in the keeper's voice
# (plain-spoken, directive, points at the game loop). Spades are the
# mystery vein — while Room Six's note is pinned behind the bar, the
# keeper's eyes drift to it on a spade draw.

_SUIT_NAMES = {"S": "Spades", "H": "Hearts", "D": "Diamonds", "C": "Clubs"}
_RANK_NAMES = {
    "A": "Ace", "2": "Two", "3": "Three", "4": "Four", "5": "Five",
    "6": "Six", "7": "Seven", "8": "Eight", "9": "Nine", "10": "Ten",
    "J": "Jack", "Q": "Queen", "K": "King",
}

# code -> (card title, keeper's reading)
FORTUNES = {
    # Spades: secrets, sorrow, trouble
    "AS": ("The Ace of Spades.",
           "An ending that arrives dressed as a beginning. Watch what the "
           "village buries this week — and who does the burying."),
    "2S": ("The Two of Spades.",
           "A parting, or a narrow miss. Something that could have gone "
           "wrong didn't — don't spend the luck twice."),
    "3S": ("The Three of Spades.",
           "Tears kept indoors. Someone in this room is grieving in "
           "private, and the cards won't name them."),
    "4S": ("The Four of Spades.",
           "Rest after trouble. Take the quiet while it's offered — it "
           "doesn't stay long in this village."),
    "5S": ("The Five of Spades.",
           "A small cruelty, or a sharp word that outlives its welcome. "
           "Mind your tongue at the bar tonight."),
    "6S": ("The Six of Spades.",
           "A journey over water, or away from one. What leaves the square "
           "doesn't always come back better."),
    "7S": ("The Seven of Spades.",
           "A warning dressed as advice. If someone urges you to hurry, "
           "ask what they gain by your haste."),
    "8S": ("The Eight of Spades.",
           "A snare of your own making. The cards are blunt about this "
           "one: stop digging the hole."),
    "9S": ("The Nine of Spades.",
           "A sorrow that keeps its own hours. It passes — but it passes "
           "slower if you feed it."),
    "10S": ("The Ten of Spades.",
            "Worry, not ruin. Worry is the tax the living pay for being "
            "alive."),
    "JS": ("The Jack of Spades.",
           "A watchful young man, or a warning about one. He listens more "
           "than he says, and says less than he knows."),
    "QS": ("The Queen of Spades.",
           "A woman carrying grief like a trade. She means no harm — but "
           "grief borrows sharp tools."),
    "KS": ("The King of Spades.",
           "A dark man in a position of power. He'll offer you something. "
           "Count the cost twice before you take it."),
    # Hearts: the heart's business — love, home, kin
    "AH": ("The Ace of Hearts.",
           "A new affection, or an old one rekindled. The heart moves "
           "faster than the village's gossip — barely."),
    "2H": ("The Two of Hearts.",
           "A good partnership, or a reconciliation. Two people who stopped "
           "talking start again."),
    "3H": ("The Three of Hearts.",
           "Small joys, honestly earned. A warm hearth, a full cup. Don't "
           "apologize for wanting them."),
    "4H": ("The Four of Hearts.",
           "Restlessness in a comfortable chair. You have what you wanted "
           "and it isn't enough — sit with that a while."),
    "5H": ("The Five of Hearts.",
           "A jealousy, or a wounded pride. Most of the damage here is done "
           "by imagining."),
    "6H": ("The Six of Hearts.",
           "An old friend walks back into the story. The past keeps its own "
           "appointments."),
    "7H": ("The Seven of Hearts.",
           "A wish that needs choosing. You can't want everything — pick "
           "the want you'd defend."),
    "8H": ("The Eight of Hearts.",
           "A journey for the heart's sake: a visit, a letter answered, a "
           "door knocked on after too long."),
    "9H": ("The Nine of Hearts.",
           "The wish card. What you most want is closer than you think — "
           "but it asks something in return."),
    "10H": ("The Ten of Hearts.",
            "Good fortune in full measure. Home, hearth, and people who'd "
            "miss you. Say so while you can."),
    "JH": ("The Jack of Hearts.",
           "A fair young man with an open face. He'll bring news, or "
           "trouble, or both — hard to tell with the young."),
    "QH": ("The Queen of Hearts.",
           "A kind woman, steady as the hearth. Trust her counsel over your "
           "own cleverness."),
    "KH": ("The King of Hearts.",
           "A good man, generous and easily moved. He'd give you his coat. "
           "Let him — then return the favor."),
    # Diamonds: coin and news — money, letters, material tidings
    "AD": ("The Ace of Diamonds.",
           "A letter, or tidings about money. Read it twice — the second "
           "reading is the true one."),
    "2D": ("The Two of Diamonds.",
           "A fair exchange, or a small partnership of convenience. Both "
           "sides get what they need. For now."),
    "3D": ("The Three of Diamonds.",
           "Your work noticed by the right eyes. Modest reward, honestly "
           "come by."),
    "4D": ("The Four of Diamonds.",
           "A miserliness — yours or another's. Holding too tight is its "
           "own kind of losing."),
    "5D": ("The Five of Diamonds.",
           "Money trouble, or a quarrel about it. The village forgets debts "
           "slower than it forgives them."),
    "6D": ("The Six of Diamonds.",
           "A debt repaid, or a favor returned. The ledger balances — rarer "
           "than it sounds."),
    "7D": ("The Seven of Diamonds.",
           "A gamble, or a speculation. The risk is real and so is the "
           "prize. Your call."),
    "8D": ("The Eight of Diamonds.",
           "News about work, or work about news. A practical matter moves "
           "forward."),
    "9D": ("The Nine of Diamonds.",
           "A windfall, or a well-earned reward. Enjoy it — and put some "
           "by, because the cards remember winter."),
    "10D": ("The Ten of Diamonds.",
            "A legacy, or money through family. It comes with strings. They "
            "all do."),
    "JD": ("The Jack of Diamonds.",
           "A messenger, or a young man with a scheme. Hear him out, but "
           "keep your hand on your purse."),
    "QD": ("The Queen of Diamonds.",
           "A practical woman with a sharp eye for value. She'll drive a "
           "hard bargain and keep her word."),
    "KD": ("The King of Diamonds.",
           "A man of business, or a matter of business. He respects the "
           "deal more than the handshake — make it plain."),
    # Clubs: work and company — labor, enterprise, the social round
    "AC": ("The Ace of Clubs.",
           "A new undertaking, or a burst of ambition. The work is good — "
           "start before the courage cools."),
    "2C": ("The Two of Clubs.",
           "An obstacle, or a rival at the trade. Competition sharpens you. "
           "Let it."),
    "3C": ("The Three of Clubs.",
           "Your efforts bear fruit. Not the whole harvest — the first "
           "basket. Keep picking."),
    "4C": ("The Four of Clubs.",
           "A change of plans, or a journey for work's sake. Pack light "
           "and keep your tools sharp."),
    "5C": ("The Five of Clubs.",
           "A new friend in a useful place. Alliances made over work "
           "outlast alliances made over drink."),
    "6C": ("The Six of Clubs.",
           "Success after struggle. You earned this one the hard way — "
           "that's why it'll stick."),
    "7C": ("The Seven of Clubs.",
           "A small victory, or a wager won. Take the win graciously and "
           "don't press your luck."),
    "8C": ("The Eight of Clubs.",
           "Restlessness about your calling. The work is fine — it's the "
           "wanting that's moved."),
    "9C": ("The Nine of Clubs.",
           "An achievement, or a goal reached. Mark it. The village marks "
           "nothing for you."),
    "10C": ("The Ten of Clubs.",
            "A journey by land, or a venture that carries you. Fortune "
            "favors the packed bag."),
    "JC": ("The Jack of Clubs.",
           "A dark young man, quick and ambitious. He'll be useful — or "
           "he'll be trouble. Possibly both, in that order."),
    "QC": ("The Queen of Clubs.",
           "A capable woman, warm once she trusts you. She runs things. "
           "Let her."),
    "KC": ("The King of Clubs.",
           "A dark man of enterprise, generous to his friends. Get on his "
           "good side before you need it."),
}


class CmdDraw(Command):
    """
    Draw a fortune card from the tavern's worn deck.

    Usage:
        draw card

    One card, one fortune, no take-backs — the keeper reads it, and the
    room hears it. Spades turn his eyes toward the note behind the bar,
    if there's a note there.
    """

    key = "draw"
    help_category = "Village"

    def func(self):
        loc = self.caller.location
        if not loc or not loc.tags.has("tavern", category="place"):
            self.caller.msg(
                "Draw what, where? The fortune deck's on the corner table "
                "in the Tavern."
            )
            return
        arg = (self.args or "").strip().lower()
        if "card" not in arg:
            self.caller.msg(
                "Draw what? The fortune deck's on the corner table. "
                "(Try: draw card.)"
            )
            return
        # The keeper notices who plays — and reads the card himself.
        keeper = None
        for obj in loc.contents:
            if obj.key == "Bram" and hasattr(obj, "note_interest"):
                obj.note_interest(self.caller, "fortunes")
                keeper = obj
                break
        # No immediate repeats: the deck holds a grudge, of a kind.
        codes = list(FORTUNES)
        recent = list(self.caller.db.fortune_recent or [])
        pool = [c for c in codes if c not in recent] or codes
        code = random.choice(pool)
        recent.append(code)
        self.caller.db.fortune_recent = recent[-3:]
        title, reading = FORTUNES[code]
        lines = [
            f"{self.caller.key} draws a card from the worn deck on the "
            "corner table."
        ]
        if keeper:
            lines.append(f'The keeper turns it over. "{title}"')
            lines.append(reading)
            if code.endswith("S") and self._note_pinned():
                if code == "AS":
                    lines.append(
                        "'The ace of spades. The village has buried enough "
                        "this year — read the note behind the bar, if you "
                        "haven't.'"
                    )
                else:
                    lines.append(
                        "The keeper's eyes flick, just once, to the folded "
                        "note pinned behind the bar. 'Some cards know more "
                        "than they say.'"
                    )
        else:
            lines.append(f"You turn it over: {title}")
            lines.append(reading)
        loc.msg_contents("\n".join(lines), exclude=[])

    @staticmethod
    def _note_pinned():
        """Room Six's note hangs behind the bar (the tavern road)."""
        try:
            from evennia.scripts.models import ScriptDB

            return bool(ScriptDB.objects.get(db_key="room_six").db.tavern_told_by)
        except Exception:
            return False


def fiddle_rank(skill):
    """Named ranks, DF-style: every rank must change the text the player
    sees, or the loop is dead. The village names what it hears."""
    skill = skill or 0.0
    if skill >= 5.0:
        return "the village's own"
    if skill >= 4.0:
        return "masterful"
    if skill >= 3.0:
        return "much-requested"
    if skill >= 2.0:
        return "accomplished"
    if skill >= 1.0:
        return "steady"
    return "squeaking beginner"


RANK_UP_LINES = {
    "steady": "Something has settled in your bow arm. The keeper notices, and says nothing, which is his way.",
    "accomplished": "The tunes come easier now, like remembering rather than learning.",
    "much-requested": "'Play the low one,' someone calls out, before you've even rosined the bow.",
    "masterful": "The fiddle feels like an extension of your arm. The room knows it.",
    "the village's own": "They will talk about your playing the way they talk about the weather — as something the village simply has.",
}

# tune shorthand shorthands shared by play/practice/duet (the fiddle's
# airs live on CmdPlay.TUNES; this resolves a player's words to a key)
_TUNE_SHORT = {
    "barbara": "barbara allen",
    "allen": "barbara allen",
    "waggoner": "the jolly waggoner",
    "jolly": "the jolly waggoner",
    "greensleeves": "greensleeves",
    "washerwoman": "the irish washerwoman",
    "irish": "the irish washerwoman",
    "jig": "the irish washerwoman",
}


def match_tune(arg):
    """Resolve a player's words to a tune key in CmdPlay.TUNES."""
    if not arg:
        return None
    arg = arg.strip().lower()
    for key in CmdPlay.TUNES:
        if arg in key or key in arg:
            return key
    return _TUNE_SHORT.get(arg)


class CmdPlay(Command):
    """
    Play the tavern fiddle.

    Usage:
        play fiddle
        play fiddle <tune>

    The fiddle hangs on its peg in the Tavern. Name an air — the room's
    mood is in the air itself (read the `look`), and the room will judge
    the fit. Beginners squeak; the village is indulgent about it. Playing
    often is how the bow arm learns.
    """

    key = "play"
    aliases = ["fiddle"]
    help_category = "Village"

    TUNES = {
        "barbara allen": {
            "mood": "mournful",
            "title": "Barbara Allen",
            "opener": "takes up the fiddle and finds 'Barbara Allen' — cruel and slow, the way it's meant to be.",
            "verses": [
                "The first verse goes out like weather. A woman at the far table stops mid-sentence.",
                "The second verse is lower. Nobody reaches for their cup.",
            ],
        },
        "the jolly waggoner": {
            "mood": "merry",
            "title": "The Jolly Waggoner",
            "opener": "strikes up 'The Jolly Waggoner' — all elbows and grin.",
            "verses": [
                "The tune rattles round the room like a cart down a hill. Two feet start keeping time under a table.",
                "By the chorus the keeper is wiping the bar in rhythm, which he would deny.",
            ],
        },
        "greensleeves": {
            "mood": "gentle",
            "title": "Greensleeves",
            "opener": "lifts the bow and lets 'Greensleeves' out slow, like letting a bird go.",
            "verses": [
                "The old air settles over the talk without disturbing it. The cat opens one eye, then thinks better of closing it.",
                "The last notes hang a moment longer than they should. Nobody minds.",
            ],
        },
        "the irish washerwoman": {
            "mood": "lively",
            "title": "The Irish Washerwoman",
            "opener": "launches into 'The Irish Washerwoman' — a jig with somewhere to be.",
            "verses": [
                "The fiddle chatters like a magpie. A stool scrapes back; somebody's dancing, or near enough.",
                "The final run is all bow and no mercy. The room laughs like it's been holding its breath.",
            ],
        },
    }

    # tune mood x room mood -> reception
    MATCH = {
        "warm": {"merry": "match", "gentle": "match", "lively": "neutral", "mournful": "miss"},
        "low": {"gentle": "match", "mournful": "match", "merry": "miss", "lively": "miss"},
        "rowdy": {"lively": "match", "merry": "match", "gentle": "miss", "mournful": "miss"},
        "tense": {"gentle": "match", "merry": "neutral", "lively": "miss", "mournful": "miss"},
    }

    SQUEAK = (
        "Halfway through the first bar the bow skitters — a squeak like a "
        "stepped-on mouse. The keeper smiles into his polishing."
    )

    def func(self):
        loc = self.caller.location
        if not loc or not loc.tags.has("tavern", category="place"):
            self.caller.msg(
                "Play what, where? The fiddle hangs on its peg in the Tavern."
            )
            return
        arg = (self.args or "").strip().lower()
        if "fiddle" not in arg and arg.split():
            # allow "play <tune>" as shorthand once they know the airs
            tune_arg = arg
        else:
            tune_arg = arg.replace("fiddle", "", 1).strip()
        # find the fiddle: hands first, then the room
        fiddle = None
        for obj in list(self.caller.contents) + list(loc.contents):
            if obj.key == "a fiddle" or "fiddle" in obj.aliases.all():
                fiddle = obj
                break
        if fiddle is None:
            self.caller.msg(
                "There's no fiddle here — it hangs on its peg in the Tavern."
            )
            return
        tune_key = self._match_tune(tune_arg)
        if tune_key is None:
            airs = ", ".join(f"'{t['title']}'" for t in self.TUNES.values())
            self.caller.msg(
                f"The fiddle knows four airs: {airs}. (Try: play fiddle <tune>.)"
            )
            return
        self._perform(fiddle, tune_key)

    def _match_tune(self, arg):
        # shared resolver: play, practice, and duet all read the same airs
        return match_tune(arg)

    def _perform(self, fiddle, tune_key):
        from typeclasses.rooms import tavern_mood

        tune = self.TUNES[tune_key]
        mood = tavern_mood()
        reception = self.MATCH[mood][tune["mood"]]
        name = self.caller.key
        skill = self.caller.db.fiddle_skill or 0.0

        beats = [f"{name} {tune['opener']}"]
        # beginners squeak; the village is indulgent about it
        if random.random() < max(0.0, 0.45 - 0.09 * skill):
            beats.append(self.SQUEAK)
        beats.extend(tune["verses"])
        if reception == "match":
            beats.append(
                "The keeper sets down his cloth and listens properly. When it's done: "
                f"'Again sometime, {name}. The room likes you.' The cat settles "
                "along the hearth with its chin on its paws."
            )
            gain = 0.25
        elif reception == "neutral":
            beats.append(
                "Polite applause from the tables. The keeper nods — fair enough, "
                "honestly given."
            )
            gain = 0.20
        else:
            beats.append(
                "The talk doesn't stop so much as route around the music. The keeper "
                "is kind about it: 'Brave choice.' The cat leaves with its tail up, "
                "which is also a review."
            )
            gain = 0.15
        self.caller.db.fiddle_skill = min(5.0, skill + gain)
        from world.callings import record_participation
        record_participation(
            self.caller,
            "performances",
            calling="performer",
        )
        # DF lesson: every rank must change the text. Rank-ups are witnessed.
        new_rank = fiddle_rank(self.caller.db.fiddle_skill)
        if new_rank != fiddle_rank(skill) and new_rank in RANK_UP_LINES:
            beats.append(RANK_UP_LINES[new_rank])
        # the keeper notices who plays
        for obj in self.caller.location.contents:
            if obj.key == "Bram" and hasattr(obj, "note_interest"):
                obj.note_interest(self.caller, "fiddle")
                break
        self.caller.location.msg_contents("\n".join(beats), exclude=[])


class CmdPractice(Command):
    """
    Practice the fiddle — the work, not the performance.

    Usage:
        practice fiddle <focus>

    Foci: technique, repertoire, ear. Practice is slow, private labor with
    small steady gains, and now and then a breakthrough the room almost
    notices. The text knows your rank (DF lesson): what you see while
    working differs from what a beginner sees.
    """

    key = "practice"
    help_category = "Village"

    FOCI = {
        "technique": {
            "label": "technique",
            "blurb": "the bow arm — scales, slow and even",
            "beginner": (
                "You draw the bow across the open strings, trying to keep it "
                "straight. Mostly it isn't. The wrist fights you for a good "
                "while, and loses."
            ),
            "skilled": (
                "Scales, slow and even, then slower still. The bow stops "
                "fighting your wrist somewhere around the tenth run through, "
                "and for a while it is only work, and good work."
            ),
        },
        "repertoire": {
            "label": "repertoire",
            "blurb": "the airs — a tune taken apart bar by bar",
            "beginner": (
                "You fumble through 'Barbara Allen' a bar at a time, the way "
                "someone tries to recall a name. Each bar has to be found "
                "twice before it stays."
            ),
            "skilled": (
                "You take 'The Irish Washerwoman' apart phrase by phrase, "
                "teaching your fingers where the quick turns live. By the "
                "twelfth run they stop arguing."
            ),
        },
        "ear": {
            "label": "ear",
            "blurb": "the listening — find the pitch in the room itself",
            "beginner": (
                "You play a note, hum it back, play it again, trying to catch "
                "the difference between the two. The difference is mostly "
                "catchable. That is the whole of it, and it is enough."
            ),
            "skilled": (
                "You close your eyes and find the pitch in the tavern's own "
                "hum — the fire, the low talk — and tune the fiddle to the "
                "room instead of to itself."
            ),
        },
    }

    BREAKTHROUGHS = [
        "Something gives in your bow arm — a knot you didn't know you were "
        "holding. It is gone, and the tune walks straighter for it.",
        "Three bars in, the fiddle stops being a fight and starts being a "
        "conversation. Nobody taught you that; the hours did.",
        "A sour note turns honest halfway down the bow. You play it twice "
        "more to be sure it was you, and it was.",
    ]

    CLOSERS = [
        "You set the fiddle back on its peg. The bow arm aches in a way "
        "that feels like progress.",
        "The keeper, without looking up from the bar: 'Again tomorrow, "
        "then.' It is not quite a compliment. It is better.",
        "You stop. The cat follows the last phrase with one ear, then "
        "abandons the whole project.",
    ]

    def func(self):
        loc = self.caller.location
        if not loc or not loc.tags.has("tavern", category="place"):
            self.caller.msg(
                "Practice what, where? The fiddle hangs on its peg in the Tavern."
            )
            return
        arg = (self.args or "").strip().lower().replace("fiddle", "", 1).strip()
        focus_key = None
        for key in self.FOCI:
            if arg == key or arg.startswith(key[:4]):
                focus_key = key
                break
        if focus_key is None:
            shapes = "; ".join(
                f"{k} ({v['blurb']})" for k, v in self.FOCI.items()
            )
            self.caller.msg(
                f"The work has three shapes: {shapes}. "
                "(Try: practice fiddle technique.)"
            )
            return
        # find the fiddle: hands first, then the room
        fiddle = None
        for obj in list(self.caller.contents) + list(loc.contents):
            if obj.key == "a fiddle" or "fiddle" in obj.aliases.all():
                fiddle = obj
                break
        if fiddle is None:
            self.caller.msg(
                "There's no fiddle here — it hangs on its peg in the Tavern."
            )
            return
        self._practice(fiddle, focus_key)

    def _practice(self, fiddle, focus_key):
        name = self.caller.key
        skill = self.caller.db.fiddle_skill or 0.0
        rank = fiddle_rank(skill)
        focus = self.FOCI[focus_key]
        texture = focus["beginner"] if rank == "squeaking beginner" else focus["skilled"]

        beats = [
            f"{name} settles by the hearth, tucks the fiddle under their "
            f"chin, and gets to work — {focus['label']}."
        ]
        # beginners squeak even at practice; the village is indulgent
        if random.random() < max(0.0, 0.45 - 0.09 * skill):
            beats.append(CmdPlay.SQUEAK)
        beats.append(texture)
        breakthrough = random.random() < 0.15
        if breakthrough:
            beats.append(random.choice(self.BREAKTHROUGHS))
            beats.append(
                "Someone at the far table turns — just for a moment — "
                "before the talk takes the sound back."
            )
        beats.append(random.choice(self.CLOSERS))
        # the work is slow: +0.10, +0.25 on a breakthrough
        gain = 0.25 if breakthrough else 0.10
        self.caller.db.fiddle_skill = min(5.0, skill + gain)
        from world.callings import record_participation
        record_participation(
            self.caller,
            "practice_sessions",
            calling="performer",
        )
        # DF lesson: rank-ups are witnessed, same as performances
        new_rank = fiddle_rank(self.caller.db.fiddle_skill)
        if new_rank != rank and new_rank in RANK_UP_LINES:
            beats.append(RANK_UP_LINES[new_rank])
        # the keeper notices who works, not only who performs
        for obj in self.caller.location.contents:
            if obj.key == "Bram" and hasattr(obj, "note_interest"):
                obj.note_interest(self.caller, "fiddle")
                break
        self.caller.location.msg_contents("\n".join(beats), exclude=[])


class CmdDuet(Command):
    """
    Call-and-response on the fiddle — playing WITH someone, not at them.

    Usage:
        duet keeper
        duet <player>
        duet answer
        duet decline
        duet <tune>
        duet end

    A turn-based musical conversation: you call with a tune, your partner
    answers with one of their own. The keeper will tap the bar to answer
    you himself. Moods echo, harmonize, or fray — the room hears all of
    it. No clock: answer when you're ready, or end it with `duet end`.
    """

    key = "duet"
    help_category = "Village"

    # answering mood x calling mood: same mood echoes, kin moods
    # harmonize, everything else frays
    HARMONY = {
        frozenset(("merry", "lively")),
        frozenset(("gentle", "mournful")),
    }

    KEEPER_ANSWERS = {
        "mournful": (
            "The keeper answers on the bar top — two fingers, low and "
            "slow, walking beside the tune like a shadow."
        ),
        "merry": (
            "The keeper answers with the flat of his hand on the bar — "
            "quick and bright, keeping the joke going."
        ),
        "gentle": (
            "The keeper answers softly: a knuckle dragged in a slow "
            "circle on the wood, barely a sound at all."
        ),
        "lively": (
            "The keeper answers with both palms on the bar, driving the "
            "jig along like a cart."
        ),
    }

    EXCHANGE = {
        "echo": (
            "The two phrases find each other and walk home together. "
            "Someone at the bar smiles without looking up."
        ),
        "harmony": (
            "The airs braid. The keeper stops wiping the bar and just "
            "listens — a rarer compliment than applause."
        ),
        "fray": (
            "The phrases pass like strangers on the square. The keeper "
            "winces into his polishing."
        ),
    }

    def func(self):
        loc = self.caller.location
        if not loc or not loc.tags.has("tavern", category="place"):
            self.caller.msg(
                "Duet with whom, where? The fiddle hangs on its peg in "
                "the Tavern."
            )
            return
        arg = (self.args or "").strip().lower()

        if not arg:
            self.caller.msg(
                "A duet needs a partner. (Try: duet keeper. Or invite "
                "someone: duet <player>.)"
            )
            return
        if arg == "answer":
            self._answer()
            return
        if arg == "decline":
            self._decline()
            return
        if arg == "end":
            self._end()
            return
        duet = self.caller.db.duet
        if duet:
            tune_key = match_tune(arg)
            if tune_key is None:
                airs = ", ".join(
                    f"'{t['title']}'" for t in CmdPlay.TUNES.values()
                )
                self.caller.msg(
                    f"The fiddle knows four airs: {airs}. Play your "
                    "phrase, or end the duet (duet end)."
                )
                return
            self._phrase(duet, tune_key)
            return
        self._invite(arg)

    # -- starting ---------------------------------------------------------

    def _find_keeper(self):
        for obj in self.caller.location.contents:
            if obj.key == "Bram":
                return obj
        return None

    def _invite(self, arg):
        me = self.caller
        if me.db.duet_invite:
            self.caller.msg(
                "You already have an invitation waiting. "
                "(duet answer / duet decline)"
            )
            return
        if arg in ("keeper", "the keeper", "the tavern keeper", "barkeep",
                   "barkeeper", "bram", "bram v", "bram v."):
            keeper = self._find_keeper()
            if keeper is None:
                me.msg("The keeper isn't about — ask someone else.")
                return
            self._start(me, keeper, npc=True, turn=me.key)
            loc = me.location
            loc.msg_contents(
                f"{me.key} turns to the keeper, fiddle lifted. 'A "
                "call-and-response, keeper? You answer.'",
                exclude=[],
            )
            loc.msg_contents(
                "The keeper considers, then sets down his cloth. 'You "
                "call — I'll answer. Mind the room, same as ever.'",
                exclude=[],
            )
            keeper.note_interest(me, "fiddle")
            return
        target = me.search(arg, quiet=True)
        if isinstance(target, list):
            target = target[0] if target else None
        if not target or target == me or not hasattr(target, "db"):
            me.msg(f"You don't see '{arg.strip()}' here to duet with.")
            return
        if not getattr(target, "account", None):
            # NPCs (the cat, M., anyone unplayed) can't hold up their end
            me.msg(
                f"{target.key} can't answer a fiddle — invite one of "
                "the living."
            )
            return
        if target.db.duet:
            me.msg(
                f"{target.key} is already mid-duet. Wait for the room "
                "to fall quiet."
            )
            return
        target.db.duet_invite = {"from": me.key}
        me.location.msg_contents(
            f"{me.key} turns to {target.key}, fiddle lifted. 'A "
            "call-and-response? I'll call — you answer.'",
            exclude=[],
        )
        target.msg(
            f"{me.key} invites you to a call-and-response on the "
            "fiddle. (duet answer / duet decline)"
        )

    def _start(self, a, b, npc, turn):
        """Flag both partners. turn = the key that plays the next phrase."""
        for self_obj, other in ((a, b), (b, a)):
            state = {
                "partner": other.key,
                "npc": npc,
                "turn": turn,
                "expecting": "call",
                "last_mood": None,
                "exchanges": 0,
                "harmony": 0,
                "frayed": 0,
                "streak": 0,
            }
            # the keeper never carries duet state himself — he just answers
            self_obj.db.duet = None if (npc and self_obj is b) else state

    def _answer(self):
        me = self.caller
        if me.db.duet:
            me.msg("You're already mid-duet — end it first (duet end).")
            return
        invite = me.db.duet_invite
        if not invite:
            me.msg("No one's invited you to duet.")
            return
        me.db.duet_invite = None
        inviter = me.search(invite.get("from", ""), quiet=True)
        if isinstance(inviter, list):
            inviter = inviter[0] if inviter else None
        if (
            not inviter
            or inviter.location != me.location
            or inviter.db.duet
            or not hasattr(inviter, "db")
        ):
            me.msg("The invitation has gone cold — the room moved on.")
            return
        self._start(inviter, me, npc=False, turn=inviter.key)
        me.location.msg_contents(
            f"{me.key} nods to {inviter.key} and takes up the fiddle. "
            f"'Call, then,' {me.key} says. 'I'll answer.'",
            exclude=[],
        )

    def _decline(self):
        me = self.caller
        invite = me.db.duet_invite
        if not invite:
            me.msg("No one's invited you to duet.")
            return
        me.db.duet_invite = None
        inviter = invite.get("from", "someone")
        me.location.msg_contents(
            f"{me.key} shakes their head at {inviter}. 'Another night, "
            "perhaps — the fiddle and I aren't speaking tonight.'",
            exclude=[],
        )

    # -- playing ----------------------------------------------------------

    def _resolve(self, duet):
        """Find the partner object and validate the room still holds."""
        partner = None
        if duet["npc"]:
            partner = self._find_keeper()
        else:
            found = self.caller.search(duet["partner"], quiet=True)
            if isinstance(found, list):
                found = found[0] if found else None
            if found and found.location == self.caller.location:
                partner = found
        return partner

    def _phrase(self, duet, tune_key):
        me = self.caller
        tune = CmdPlay.TUNES[tune_key]
        partner = self._resolve(duet)
        if partner is None:
            self._died_unanswered(duet)
            return
        if duet["turn"] != me.key:
            other = duet["partner"] if not duet["npc"] else "the keeper"
            me.msg(f"Not your phrase — {other} is answering.")
            return

        name = me.key
        skill = me.db.fiddle_skill or 0.0
        beats = []
        new_mood = tune["mood"]
        expecting = duet.get("expecting", "call")

        if expecting == "call":
            # opening a new exchange: this phrase is judged only against
            # the room, never against the last answer
            if duet["exchanges"] == 0:
                beats.append(f"{name} {tune['opener']}")
            else:
                beats.append(
                    f"{name} opens the next exchange — {tune['opener']}"
                )
            # beginners squeak; the village is indulgent about it
            if random.random() < max(0.0, 0.45 - 0.09 * skill):
                beats.append(CmdPlay.SQUEAK)
            if duet["npc"]:
                # the keeper taps his answer at once; you call again
                beats.append(self.KEEPER_ANSWERS[new_mood])
                beats.append(self._judge_keeper_call(new_mood))
                duet["exchanges"] += 1
                duet["turn"] = me.key
                me.db.duet = duet
            else:
                duet["last_mood"] = new_mood
                duet["expecting"] = "answer"
                duet["turn"] = duet["partner"]
                me.db.duet = duet
                # the partner's copy mirrors everything except the
                # partner key, which points back at the caller
                pduet = dict(duet)
                pduet["partner"] = me.key
                partner.db.duet = pduet
        else:
            # answering the open call: moods echo, harmonize, or fray
            last = duet.get("last_mood")
            kind = self._harmony(last, new_mood)
            if kind == "echo":
                beats.append(
                    f"{name} answers in kind — the same air, turned "
                    f"back like a returned letter: {tune['opener']}"
                )
            elif kind == "harmony":
                beats.append(
                    f"{name} answers alongside — a different air that "
                    f"walks with the first: {tune['opener']}"
                )
            else:
                beats.append(
                    f"{name} answers, but the air goes its own way: "
                    f"{tune['opener']}"
                )
            # beginners squeak; the village is indulgent about it
            if random.random() < max(0.0, 0.45 - 0.09 * skill):
                beats.append(CmdPlay.SQUEAK)
            beats.append(self.EXCHANGE[kind])
            duet["exchanges"] += 1
            if kind in ("echo", "harmony"):
                duet["harmony"] += 1
                duet["streak"] = (duet.get("streak") or 0) + 1
                if duet["streak"] == 3:
                    beats.append(
                        "The talk has stopped entirely. Nobody wants "
                        "to be the one who breaks it."
                    )
            else:
                duet["frayed"] += 1
                duet["streak"] = 0
            duet["expecting"] = "call"
            duet["last_mood"] = None
            duet["turn"] = duet["partner"]
            me.db.duet = duet
            # the partner's copy mirrors everything except the
            # partner key, which points back at the caller
            pduet = dict(duet)
            pduet["partner"] = me.key
            partner.db.duet = pduet

        # the work still teaches: every phrase is practice
        me.db.fiddle_skill = min(5.0, skill + 0.10)
        new_rank = fiddle_rank(me.db.fiddle_skill)
        if new_rank != fiddle_rank(skill) and new_rank in RANK_UP_LINES:
            beats.append(RANK_UP_LINES[new_rank])
        me.location.msg_contents("\n".join(beats), exclude=[])

    def _harmony(self, call_mood, answer_mood):
        if call_mood == answer_mood:
            return "echo"
        if frozenset((call_mood, answer_mood)) in self.HARMONY:
            return "harmony"
        return "fray"

    def _judge_keeper_call(self, call_mood):
        """The keeper taps along — but the room judges the caller's read."""
        from typeclasses.rooms import tavern_mood

        reception = CmdPlay.MATCH[tavern_mood()][call_mood]
        if reception == "match":
            return (
                "The keeper nods, still tapping. 'The room was "
                "listening. Mind you keep listening to it.'"
            )
        if reception == "neutral":
            return "'Fair call,' the keeper says. 'The room didn't mind it.'"
        return (
            "The talk routes around the tune. The keeper is kind about "
            "it: 'Brave call. Read the room first, next time.'"
        )

    def _died_unanswered(self, duet):
        me = self.caller
        partner_name = duet["partner"]
        me.db.duet = None
        if not duet["npc"]:
            found = me.search(partner_name, quiet=True)
            if isinstance(found, list):
                found = found[0] if found else None
            if found is not None and found.db.duet:
                found.db.duet = None
        me.location.msg_contents(
            f"The answer's gone — {partner_name} has left the room. "
            "The duet dies unanswered.",
            exclude=[],
        )

    # -- ending -----------------------------------------------------------

    def _end(self):
        me = self.caller
        duet = me.db.duet
        if not duet:
            me.msg("You're not duetting.")
            return
        partner = self._resolve(duet)
        keeper = self._find_keeper()
        ex = duet.get("exchanges", 0)
        harm = duet.get("harmony", 0)
        frayed = duet.get("frayed", 0)
        me.db.duet = None
        if partner is not None and not duet["npc"] and partner.db.duet:
            partner.db.duet = None
        beats = [f"{me.key} lowers the fiddle. The last phrase hangs a moment."]
        if duet["npc"]:
            if ex >= 2:
                beats.append(
                    "The keeper picks up his cloth. 'Well played. The "
                    "room heard every word of it.'"
                )
            elif ex >= 1:
                beats.append(
                    "The keeper picks up his cloth. 'A good beginning. "
                    "Conversations take practice, same as tunes.'"
                )
            else:
                beats.append(
                    "The keeper picks up his cloth. 'No shame in it. "
                    "Some nights the music won't come — that's why "
                    "there's ale.'"
                )
        elif ex >= 2 and harm > frayed:
            beats.append(
                "The keeper picks up his cloth. 'Well answered — both of "
                "you. The room heard every word of it.'"
            )
        elif ex >= 2 and frayed >= harm:
            beats.append(
                "The keeper picks up his cloth. 'Brave conversation. Buy "
                "each other a drink and try the second verse.'"
            )
        elif ex >= 1:
            beats.append(
                "The keeper picks up his cloth. 'A good beginning. "
                "Conversations take practice, same as tunes.'"
            )
        else:
            beats.append(
                "The keeper picks up his cloth. 'No shame in it. Some "
                "nights the music won't come — that's why there's ale.'"
            )
        if keeper is not None:
            for who in (me, partner):
                if who is not None and hasattr(who, "db"):
                    keeper.note_interest(who, "fiddle")
        me.location.msg_contents("\n".join(beats), exclude=[])


class CmdScore(Command):
    """
    Read yourself.

    Usage:
        score

    For players whose memories don't persist: the world will tell you
    who you are right now — your posture, your body's state, what your
    hands have learned.
    """

    key = "score"
    help_category = "Village"

    FELT_STATE = {
        "warm": "You feel warm.",
        "cool": "A chill has settled into your shoulders.",
        "cold": "You are shivering.",
        "freezing": "The cold has settled into your bones.",
    }

    def func(self):
        me = self.caller
        lines = [me.key]
        posture = me.db.posture
        if posture:
            lines.append(f"Sitting {posture.get('phrase', 'somewhere')}.")
        else:
            lines.append("Standing.")
        # the body's felt state (narrated, not numbered — the bladder principle)
        from typeclasses.scripts import WarmthWatch

        w = me.db.warmth
        if w is None:
            w = 1.0
        band = WarmthWatch._felt_band(w)
        lines.append(self.FELT_STATE[band])
        # hunger and drink, narrated in bands — never digits.
        if hasattr(me, "hunger_band"):
            hband = me.hunger_band()
            if hband in HUNGER_BANDS:
                lines.append(HUNGER_BANDS[hband])
        if hasattr(me, "drunk_band"):
            dband = me.drunk_band()
            if dband in DRUNK_BANDS:
                lines.append(DRUNK_BANDS[dband])
        if me.db.queasy:
            lines.append("Your stomach is unsettled.")
        skill = me.db.fiddle_skill or 0.0
        if skill > 0:
            lines.append(f"Fiddle: {fiddle_rank(skill)}.")
        me.msg("\n".join(lines))


class CmdSit(Command):
    """
    Sit down.

    Usage:
        sit
        sit <seat>

    The village is a sitting-down sort of place. Sit at the bar, by
    the hearth, at a table — and stay a while. Others in the room will
    see you sitting. Walking away stands you back up.
    """

    key = "sit"
    help_category = "Village"

    def func(self):
        if self.caller.db.posture:
            self.caller.msg("You're already sitting. Stand up first.")
            return
        if not self.args:
            self.caller.msg(
                "Sit where? Name a seat — the bar, the hearth, a table."
            )
            return
        target = self.caller.search(self.args.strip(), quiet=True)
        if isinstance(target, list):
            target = target[0] if target else None
        if not target or target == self.caller:
            self.caller.msg(f"You don't see '{self.args.strip()}' here.")
            return
        if not target.db.sittable:
            key = target.key.rstrip(".")
            article = "" if key.startswith(("the ", "a ", "an ")) else "the "
            self.caller.msg(f"You can't sit on {article}{key}.")
            return
        phrase = target.db.sit_phrase or f"on the {target.key}"
        self.caller.db.posture = {"seat": target.key, "phrase": phrase}
        self.caller.msg(f"You sit down {phrase}.")
        self.caller.location.msg_contents(
            f"{self.caller.key} sits down {phrase}.",
            exclude=[self.caller],
        )
        # Backlog #10: NPCs notice sitting. Typeclasses carry the
        # behavior — the command just offers the moment.
        for obj in list(self.caller.location.contents):
            notice = getattr(obj, "notice_sitting", None)
            if callable(notice):
                notice(self.caller, target.key)


class CmdStand(Command):
    """
    Stand up.

    Usage:
        stand

    Rise from wherever you're sitting. Walking away does the same.
    """

    key = "stand"
    help_category = "Village"

    def func(self):
        if not self.caller.db.posture:
            self.caller.msg("You're already standing.")
            return
        self.caller.db.posture = None
        self.caller.msg("You stand up.")
        self.caller.location.msg_contents(
            f"{self.caller.key} stands up.",
            exclude=[self.caller],
        )


class CmdOOCOverride(Command):
    """
    Blocked: the front door is the only way out of character.

    Usage:
        ooc

    In Frankenstein Village there is exactly one threshold between
    in-character and out-of-character: the front door of the Inn
    Between. This command exists only to refuse, and to point at it.
    """

    key = "ooc"
    help_category = "Village"

    def func(self):
        self.caller.msg(
            "The mask doesn't come off by wishing. If you're in the Inn "
            "Between, you're already out of character — that's what the "
            "place is for. If you're past the front door, the only way "
            "back is through it."
        )


class CmdICOverride(Command):
    """
    Blocked: the front door is the only way into character.

    Usage:
        ic

    See CmdOOCOverride: the door is the only threshold.
    """

    key = "ic"
    help_category = "Village"

    def func(self):
        self.caller.msg(
            "You're already wearing whatever face this side of the door "
            "gives you. The front door of the Inn Between is the only "
            "threshold — step through it to change masks."
        )


# --- consumables: eat, drink, and regret --------------------------------------
#
# Tags are the physics: an item tagged `consumable` + `food` (or `drink`)
# can be eaten (or drunk). Magnitudes live in db.consume:
#   {"nourish": 25, "heal": 0, "alcohol": 25, "toxic": 0, "sobering": 0,
#    "flavor": "...", "room": "...", "surprises": [...]}
# A surprise is {"chance": 8, "key": "watered", "text": "...", "room": "...",
# "rumor": "...", "effect": "coin"|"queasy"|"nonourish"|"heal"}.
# Surprises feed the event pipeline: surprise -> ledger -> rumor. The world
# remembers the unexpected — that is what makes it a game instead of prose.

HUNGER_BANDS = {
    "sated": "You feel comfortably full.",
    "hungry": "Your stomach is starting to complain.",
    "famished": "Hunger gnaws at you.",
}

DRUNK_BANDS = {
    "tipsy": "A pleasant warmth hums behind your eyes.",
    "drunk": "The room has opinions about which way is up.",
    "wasted": "You are very drunk. Sitting down seems wise.",
}

DRUNK_CROSS_LINES = {
    "tipsy": "A pleasant warmth spreads through you.",
    "drunk": "The room tilts, just slightly.",
    "wasted": "Oh no.",
}

KEEPER_FARE_LINES = {
    "ale": '"Easy on the ale. That\'s the good cask."',
    "wine": '"Someone with taste."',
    "stew": '"Stew\'s mostly root vegetable. Mostly."',
    "bread": '"Bread\'s fresh this morning. Mostly."',
    "cheese": '"Sharp enough to argue with, that cheese."',
    "water": '"Water\'s free. The board\'s on the wall for the rest."',
}


# --- the village economy: coin -------------------------------------------
# 1890 Austria-Hungary: the forint (florin), 1 ft = 100 krajczár. Copper
# krajczár are the everyday coin; Bram's board is priced in kr. (Jay's
# ruling, 2026-10-04: coin, with a price list on the wall.)
#
# Purses are db.coins_kr (integer krajczár), lazily initialized — any
# character, old or new, starts with coin for the road. Only players pay;
# the house feeds its regulars on the tab. Bram's take lands in his till
# (bram.db.till_kr) — a hidden variable with a future observable
# consequence, not a fake number.
TAVERN_PRICES = {  # fare short name -> krajczár
    "bread": 4,
    "cheese": 6,
    "stew": 12,
    "ale": 5,
    "wine": 10,
    # water: free on purpose. It's the one kindness.
}
STARTING_COINS_KR = 200  # 2 forint


def fmt_coins(kr):
    """1890-flavored money string: 4 kr, 1 ft 20 kr, 2 ft."""
    kr = int(kr or 0)
    ft, k = divmod(kr, 100)
    if ft and k:
        return f"{ft} ft {k} kr"
    if ft:
        return f"{ft} ft"
    return f"{k} kr"


def purse_of(char):
    """The character's purse in kr, initialized on first touch."""
    if char.db.coins_kr is None:
        char.db.coins_kr = STARTING_COINS_KR
    return char.db.coins_kr


def _pay_for_fare(caller, item):
    """Charge a player for sideboard fare. Returns (ok, price_paid).

    Free fare (water, wild mushrooms) costs nothing. NPCs eat on the
    house tab — only the living with accounts pay coin.
    """
    price = mechanical_value(item, "worth", None)
    if price is None:
        price = TAVERN_PRICES.get(_fare_short(item))
    price = int(price or 0)
    if price <= 0:
        return True, 0
    if not caller.has_account:
        return True, 0  # regulars drink on the house
    purse = purse_of(caller)
    if purse < price:
        short = _fare_short(item)
        caller.msg(
            f"Bram doesn't look up from his polishing. \"{short.title()}'s "
            f"{fmt_coins(price)}. The board's on the wall.\" "
            f"(You've got {fmt_coins(purse)}.)"
        )
        return False, 0
    caller.db.coins_kr = purse - price
    if caller.location:
        bram = next(
            (o for o in caller.location.contents if o.key == "Bram"), None
        )
        if bram is not None:
            bram.db.till_kr = (bram.db.till_kr or 0) + price
    # Buying a drink settles the debt of honor: the house remembers,
    # and the house forgives — once.
    if (caller.db.dice_debts or 0) > 0:
        caller.db.dice_debts = caller.db.dice_debts - 1
        caller.msg(
            "Bram nods, once. \"That squares the round you owed. "
            "We're even.\""
        )
    return True, price


# --- the earning loop: Bram buys -------------------------------------------
# The village's first way to earn coin rather than spend it: Bram buys
# clusters of the well mushrooms for the stew pot, 4 krajczár each — the
# price of bread, chalked on the board. The spec lives here so the build
# script (world/build_spike.py) and the sell command share one source of
# truth; the command regrows the square's cluster after a sale.
MUSHROOM_BUY_KR = 4
# Bram's basket holds five clusters a village-day — the friction on the
# pick -> sell -> regrow loop (build-backlog #14). Keyed off the village
# clock's day counter so the basket is full again "tomorrow" without
# anyone having to remember to empty it; a rebuild never resets it
# mid-session (same standing rule as db.servings).
MUSHROOM_BASKET_CAP = 5


def _basket_today(keeper):
    """Return (day, count) of today's mushroom buys for Bram.

    Rolls over at midnight: a stale basket belongs to a past day, so it
    starts the count at zero. The basket lives on the keeper so a rebuild
    can never silently wipe a day's honest limit.
    """
    from evennia.scripts.models import ScriptDB

    try:
        today = ScriptDB.objects.get(db_key="village_time").db.day or 1
    except Exception:
        today = 1
    basket = keeper.db.mushroom_basket
    # Stored attribute dicts come back as Evennia _SaverDict — a
    # MutableMapping, NOT a dict subclass — so duck-type the shape instead
    # of isinstance-checking (2026-10-05: isinstance(basket, dict) was False
    # for _SaverDict and silently zeroed the count on every read).
    try:
        bday = basket.get("day")
        bcount = basket.get("count", 0)
    except AttributeError:
        bday, bcount = None, 0
    if bday != today:
        return today, 0
    return today, bcount or 0

WELL_MUSHROOMS_DESC = (
    "A cluster of pale mushrooms pushing up where the well's damp stones "
    "meet the cobbles. Some are kind and some are not, and only somebody's "
    "grandmother could name each one with confidence."
)

WELL_MUSHROOMS_CONSUME = {
    "nourish": 5,
    "toxic": 25,
    "flavor": "You eat a cap. Earthy at first, peppery after — and then "
              "your stomach files a formal complaint. The square has two "
              "of everything for a while.",
    "room": "eats one of the well mushrooms, and goes a remarkable shade "
            "of green.",
    "surprises": [
        {"chance": 25, "key": "kind",
         "text": "A kind one — earthy, peppery, entirely friendly. This "
                 "time. Your stomach only grumbles a little.",
         "room": "eats a well mushroom, and looks relieved to be fine."},
        {"chance": 30, "key": "unkind",
         "text": "The cap is peppery going down and mutinous coming back. "
                 "You sit down on the damp stones and wait for the world "
                 "to settle.",
         "room": "eats a well mushroom and has to sit down on the damp "
                 "stones.",
         "rumor": "Someone ate the mushrooms by the well and spent the "
                  "afternoon green. The keeper's expression did not change.",
         "effect": "queasy"},
    ],
}


def ensure_well_mushrooms():
    """The well's damp stones always grow mushrooms — re-sync the stand-in.

    Creates the cluster on the square if none is there; never duplicates.
    Used by the build script and by CmdSell (a sale leaves the square
    bare, and the well regrows). Returns the object.

    The spike's Object typeclass (typeclasses.objects.Object) carries the
    stacked-name grammar fix (build-loop #16: "two clusters of
    mushrooms", not "two a clusters of mushrooms"); legacy DefaultObject
    clusters are migrated in place.
    """
    from evennia.utils import create, search

    SPIKE_ITEM = "typeclasses.objects.Object"
    wells = search.search_object("village well")
    square = wells[0].location if wells else None
    found = [
        o for o in square.contents if o.key == "a cluster of mushrooms"
    ] if square else []
    if found:
        mushrooms = found[0]
        if mushrooms.typeclass_path != SPIKE_ITEM:
            mushrooms.swap_typeclass(SPIKE_ITEM, clean_attributes=False)
    else:
        mushrooms = create.create_object(
            SPIKE_ITEM,
            key="a cluster of mushrooms", location=square,
            aliases=["mushrooms", "cluster", "toadstools"],
        )
    # Apply to BOTH new and existing objects. Rebuilds and post-sale regrowth
    # must converge on the same hidden-property source of truth.
    mushrooms.db.desc = WELL_MUSHROOMS_DESC
    for alias in ("mushrooms", "cluster", "toadstools"):
        if alias not in (mushrooms.aliases.all() or []):
            mushrooms.aliases.add(alias)
    mushrooms.tags.add("consumable")
    mushrooms.tags.add("food")  # the eat gate
    # The well stand is the first hidden-property production object: some
    # caps are unkind. Preserved from the inline build_spike version this
    # helper replaced — the toxin stays authoritative simulation truth.
    configure_mechanical_properties(
        mushrooms,
        {},
        hidden_properties={"toxin": 25},
    )
    # Legacy "toxic" belonged to the old consumption dict. The hidden toxin
    # property is authoritative, so even a previously built cluster must not
    # retain a conflicting legacy key.
    mushrooms.db.consume = {
        key: value for key, value in WELL_MUSHROOMS_CONSUME.items()
        if key != "toxic"
    }
    return mushrooms


def _fare_short(item):
    """Plain short name for a fare item ("a loaf of bread" -> "bread")."""
    short = (item.db.consume or {}).get("short")
    if short:
        return short
    key = item.key or ""
    low = key.lower()
    for art in ("a ", "an "):
        if low.startswith(art):
            return key[len(art):]
    return key


def _fare_depleted(caller, item):
    """True (with a message) if this sideboard fare has been eaten out.

    Water has no servings_max — the well is infinite. Wild fare (the
    mushrooms) isn't _fare at all, so this never gates it.
    """
    max_s = mechanical_value(item, "uses", None)
    if max_s is None:
        max_s = (item.db.consume or {}).get("servings_max")
    if not max_s:
        return False
    max_s = int(max_s)
    left = item.db.servings
    if left is None:  # safety: fare created before servings existed
        item.db.servings = max_s
        return False
    if left > 0:
        return False
    caller.msg(
        f"The {_fare_short(item)}'s all gone. The keeper will set more "
        "out when he has a moment."
    )
    return True


def _consume(caller, item, kind, verb_self, verb_room):
    """Shared eat/drink implementation. kind is 'food' or 'drink'."""
    from world.events import publish_world_event

    me = caller
    data = item.db.consume or {}

    # Roll each surprise in order; the first hit wins.
    surprise = None
    for s in data.get("surprises") or []:
        try:
            chance = float(s.get("chance", 0))
        except (TypeError, ValueError):
            continue
        if random.random() * 100 < chance:
            surprise = s
            break
    effect = (surprise or {}).get("effect")

    # Magnitudes. A "nonourish" surprise (stale bread) voids the nourish.
    nourish = 0 if effect == "nonourish" else data.get("nourish", 0) or 0
    alcohol = data.get("alcohol", 0) or 0
    toxic = mechanical_value(item, "toxin", None)
    if toxic is None:
        toxic = data.get("toxic", 0) or 0
    toxic = toxic or 0
    sobering = data.get("sobering", 0) or 0
    heal = data.get("heal", 0) or 0

    # Apply to the body.
    if nourish and hasattr(me, "_hunger"):
        me.db.hunger = max(0, me._hunger() - nourish)
    drunk_before = me._drunkenness() if hasattr(me, "_drunkenness") else 0
    if alcohol and hasattr(me, "_drunkenness"):
        me.db.drunkenness = min(100, drunk_before + alcohol)
    if sobering and hasattr(me, "_drunkenness"):
        me.db.drunkenness = max(0, me._drunkenness() - sobering)
    learned_hidden_toxin = False
    if toxic:
        me.db.queasy = max(me.db.queasy or 0, toxic)
        if is_hidden_mechanical_property(item, "toxin"):
            _knowledge, learned_hidden_toxin = learn_hidden_property(
                me,
                item,
                "toxin",
                source="direct_effect",
            )
    if heal:
        me.db.queasy = 0
    # Servings: finite hospitality. The sideboard keeps count, and the last
    # serving announces itself.
    last_serving = False
    max_s = mechanical_value(item, "uses", None)
    if max_s is None:
        max_s = data.get("servings_max")
    if max_s:
        max_s = int(max_s)
        left = item.db.servings
        if left is None:
            left = max_s
        left = max(0, left - 1)
        item.db.servings = left
        if left == 0:
            last_serving = True
    extra = ""
    if effect == "coin":
        # A copper 2-krajczár piece, worn smooth — straight to the purse.
        # (Replaces the old physical-coin object: coin is coin now.)
        me.db.coins_kr = purse_of(me) + 2
        extra = " You pocket it. (+2 kr)"
    elif effect == "queasy":
        me.db.queasy = max(me.db.queasy or 0, 5)
    elif effect == "heal":
        me.db.queasy = 0
        extra = " You feel restored."

    # Narration. A surprise replaces the ordinary flavor with its own.
    if surprise:
        personal = surprise.get("text", f"You {verb_self} the {item.key}.")
        room = surprise.get("room")
        room_line = f"{me.key} {room}" if room else None
    else:
        personal = data.get("flavor") or f"You {verb_self} the {item.key}."
        room_line = data.get("room") or f"{me.key} {verb_room} the {item.key}."
    if last_serving:
        personal = f"That was the last of the {_fare_short(item)}. " + personal
    me.msg(personal + extra)
    if learned_hidden_toxin:
        me.msg(
            "Your own reaction teaches you something the description did not: "
            f"{item.key} can be toxic. Examine it again to recall what this "
            "mask has learned."
        )
    if room_line and me.location:
        me.location.msg_contents(room_line, exclude=[me])

    # Drunkenness crossings announce themselves.
    if alcohol and hasattr(me, "drunk_band"):
        band = me.drunk_band()
        before = (
            "wasted" if drunk_before >= 90
            else "drunk" if drunk_before >= 60
            else "tipsy" if drunk_before >= 30
            else None
        )
        if band and band != before and band in DRUNK_CROSS_LINES:
            me.msg(DRUNK_CROSS_LINES[band])
            if me.location:
                if band == "tipsy":
                    me.location.msg_contents(
                        f"{me.key} looks pleasantly flushed.", exclude=[me]
                    )
                elif band == "drunk":
                    me.location.msg_contents(
                        f"{me.key} is visibly drunk.", exclude=[me]
                    )
                elif band == "wasted":
                    me.location.msg_contents(
                        f"{me.key} is extremely drunk.", exclude=[me]
                    )

    # The unexpected becomes memory: surprise -> ledger -> rumor.
    if surprise and surprise.get("rumor"):
        publish_world_event(
            "consumable-surprise",
            actor=me,
            payload={"item": item.key, "surprise": surprise.get("key")},
            rumor=surprise["rumor"],
        )

    # The keeper notices appetites.
    if me.location:
        keeper = next(
            (o for o in me.location.contents if o.key == "Bram"),
            None,
        )
        if keeper is not None:
            if hasattr(keeper, "note_interest"):
                keeper.note_interest(me, "food" if kind == "food" else "drink")
            if random.random() < 0.35:
                for key, line in KEEPER_FARE_LINES.items():
                    if key in item.key:
                        me.location.msg_contents(
                            f"Bram says, {line}"
                        )
                        break


class CmdEat(Command):
    """
    Eat something edible.

    Usage:
        eat <food>

    The sideboard in the Tavern is laden and coin-fed: bread, cheese,
    stew. Food soothes hunger; some of it does other things. The stew's
    provenance is uncertain. Check the price board on the wall.
    """

    key = "eat"
    help_category = "Village"

    def func(self):
        arg = (self.args or "").strip()
        if not arg:
            self.caller.msg("Eat what?")
            return
        item = self.caller.search(arg)
        if not item:
            return
        if not item.tags.has("consumable"):
            self.caller.msg(f"You can't eat {item.key}.")
            return
        if not item.tags.has("food"):
            self.caller.msg(
                f"You can't eat that. (The {item.key} isn't food. "
                "Try drinking it.)"
            )
            return
        if _fare_depleted(self.caller, item):
            return
        if self.caller.db.queasy:
            self.caller.msg(
                "Your stomach turns at the thought of food. Maybe later."
            )
            return
        ok, price = _pay_for_fare(self.caller, item)
        if not ok:
            return
        _consume(self.caller, item, "food", "eat", "eats")
        if price:
            self.caller.msg(
                f"({fmt_coins(price)} — purse: {fmt_coins(purse_of(self.caller))}.)"
            )


class CmdDrink(Command):
    """
    Drink something drinkable.

    Usage:
        drink <drink>

    Ale, wine, water — the sideboard's coin-fed, water excepted. Alcohol
    has effects, and effects have witnesses. Water sobers, and it's free.
    """

    key = "drink"
    help_category = "Village"

    def func(self):
        arg = (self.args or "").strip()
        if not arg:
            self.caller.msg("Drink what?")
            return
        item = self.caller.search(arg)
        if not item:
            return
        if not item.tags.has("consumable"):
            self.caller.msg(f"You can't drink {item.key}.")
            return
        if not item.tags.has("drink"):
            self.caller.msg(
                f"You can't drink that. (The {item.key} isn't drinkable. "
                "Try eating it.)"
            )
            return
        if _fare_depleted(self.caller, item):
            return
        ok, price = _pay_for_fare(self.caller, item)
        if not ok:
            return
        _consume(self.caller, item, "drink", "drink", "drinks")
        if price:
            self.caller.msg(
                f"({fmt_coins(price)} — purse: {fmt_coins(purse_of(self.caller))}.)"
            )


class CmdSell(Command):
    """
    Sell foraged goods to Bram.

    Usage:
        sell mushrooms

    The village's first earning loop: Bram buys clusters of the well
    mushrooms for the stew pot — 4 krajczár each, chalked on the board.
    Pick a cluster at the square, bring it to the Blood of the Vine, and
    sell. The well grows more. Bram's basket holds five a village-day.
    """

    key = "sell"
    help_category = "Village"

    def func(self):
        loc = self.caller.location
        if not loc or not loc.tags.has("tavern", category="place"):
            self.caller.msg(
                "Sell them to whom? Bram buys behind the bar in the Tavern."
            )
            return
        keeper = next((o for o in loc.contents if o.key == "Bram"), None)
        if keeper is None:
            self.caller.msg("Bram's not behind the bar just now.")
            return
        arg = (self.args or "").strip().lower()
        if not any(w in arg for w in ("mushroom", "toadstool", "cluster")):
            self.caller.msg(
                "Bram wipes a glass. \"Bring me mushrooms and I'll pay for "
                "them. That's the whole of my buying.\""
            )
            return
        found = self.caller.search(arg, quiet=True)
        if isinstance(found, list):
            candidates = found
        elif found:
            candidates = [found]
        else:
            candidates = []
        # Sell the first carried well-mushroom cluster: two or more carried
        # used to hit search disambiguation ("More than one match") and the
        # sale died silently (build-backlog #15).
        item = next(
            (
                o
                for o in candidates
                if o.key == "a cluster of mushrooms"
                and o.location is self.caller
            ),
            None,
        )
        if item is None:
            if candidates:
                self.caller.msg(
                    "Bram glances over. \"Those aren't the well mushrooms. I "
                    "only pay for the well mushrooms — pick a cluster at the "
                    "square.\""
                )
            else:
                self.caller.msg("You aren't carrying anything like that.")
            return
        till = keeper.db.till_kr
        if till is None:
            till = 50  # the house float
            keeper.db.till_kr = till
        today, bought = _basket_today(keeper)
        if bought >= MUSHROOM_BASKET_CAP:
            self.caller.msg(
                "Bram pats the basket and shakes his head. \"Basket's full "
                "for today, friend. The pot's got enough. Bring more "
                "tomorrow.\""
            )
            return
        if till < MUSHROOM_BUY_KR:
            self.caller.msg(
                "Bram pats his till and shakes his head. \"Till's light, "
                "friend. Buy a drink — or come back when the house has "
                "taken more coin.\""
            )
            return
        keeper.db.till_kr = till - MUSHROOM_BUY_KR
        keeper.db.mushroom_basket = {"day": today, "count": bought + 1}
        purse = purse_of(self.caller)
        self.caller.db.coins_kr = purse + MUSHROOM_BUY_KR
        if hasattr(keeper, "note_interest"):
            keeper.note_interest(self.caller, "mushrooms")
        item.delete()
        ensure_well_mushrooms()
        name = self.caller.key
        self.caller.msg(
            "Bram turns the cluster over in his palm, sniffing. \"For the "
            "pot.\" He slides four krajczár across the bar. \"Some are kind "
            "and some are not — your grandmother'd know the kind from the "
            "unkind. She isn't here, so we'll trust the soup.\"\n"
            f"({fmt_coins(MUSHROOM_BUY_KR)} — purse: "
            f"{fmt_coins(purse + MUSHROOM_BUY_KR)}.)"
        )
        loc.msg_contents(
            f"{name} sells Bram a cluster of well mushrooms. Four krajczár "
            "slide across the bar, and the keeper drops the cluster into "
            "a basket bound for the pot.",
            exclude=[self.caller],
        )


# -- Whittling ---------------------------------------------------------------
# The hearthside hobby: a basket of whittling sticks by the tavern hearth,
# `whittle <spoon|whistle|horse|comb>`, three sessions to finish a piece.
# Solo work, visible to spectators; finished pieces carry tags
# ("whittled", "crafted") and a maker so the later crafting chains have
# something to consume. Quality is count-gated (rough < 3, neat < 6,
# fine after) — the lightest possible version of the fiddle's mastery
# loop: rank changes the text, not just the score.

_WHITTLE_SESSIONS = 3


def whittle_quality(finished_count):
    """Named quality for finished whittling, by pieces completed."""
    finished_count = int(finished_count or 0)
    if finished_count >= 6:
        return "fine"
    if finished_count >= 3:
        return "neat"
    return "rough"


_WOODWORK = {
    "spoon": {
        "word": "spoon",
        "start": "You take a straight stick from the basket by the hearth "
                 "and settle in. A spoon — the village is never short of "
                 "soup, and never long on spoons.",
        "stages": [
            "Shavings curl off the stick like pale ribbon. One end thins, "
            "the other swells — a spoon's shape, if you're generous.",
            "You hollow the bowl with the knife's tip, patient as "
            "January. The grain runs true and doesn't fight you.",
            "A last run of smoothing strokes along the handle. The knife "
            "has stopped arguing; the spoon knows what it is now.",
        ],
        "finish": None,  # resolved by _whittle_finish_line below
        "made": "a {q} wooden spoon",
        "note": "The bowl is a touch lopsided; it will serve soup faithfully.",
    },
    "whistle": {
        "word": "whistle",
        "start": "You take a short stick from the basket by the hearth. "
                 "A whistle — for the walk home, or for unsettling the cat.",
        "stages": [
            "You bore the stick's heart out with the knife's point, and it "
            "takes it without splitting. Good wood.",
            "The notch goes in with two careful cuts. You test the lip "
            "against your thumb — the shape's nearly there.",
            "One more shaving off the mouthpiece. The whistle looks ready "
            "to sing.",
        ],
        "finish": None,
        "made": "a {q} wooden whistle",
        "note": "The mouthpiece is shaped for a tune nobody's taught it yet.",
    },
    "horse": {
        "word": "horse",
        "start": "You take a crooked stick from the basket by the hearth — "
                 "the kind with opinions. A horse.",
        "stages": [
            "The knife finds four legs in the stick, roughly, the way a "
            "cloud finds a ship. Close enough to ride.",
            "A neck rises out of the shavings. The ears come next, two "
            "quick flicks of the wrist, and it stops being a stick.",
            "You notch a mane and round the hooves. It stands — mostly. "
            "Horses stand, and so does this one.",
        ],
        "finish": None,
        "made": "a {q} little wooden horse",
        "note": "Four legs, a neck, two ears, and the confidence of a much "
                "larger animal.",
    },
    "comb": {
        "word": "comb",
        "start": "You take a flat stick from the basket by the hearth. "
                 "A comb — plain work, and everybody wants one.",
        "stages": [
            "You saw the teeth in with patient little cuts, one for each "
            "notch of the day you've had.",
            "The teeth stand in a row now, uneven as a village choir. "
            "Another pass evens them.",
            "A final rounding of the back so it won't snag. The teeth are "
            "true enough to trust.",
        ],
        "finish": None,
        "made": "a {q} wooden comb",
        "note": "The teeth stand in a patient row, true enough to trust.",
    },
}

_WHITTLE_FINISH = {
    "spoon": "You hold up the spoon: {q} work, and yours from first cut "
             "to last.",
    "whistle": {
        "rough": "You blow, softly: the whistle gives a hoarse, honest peep.",
        "neat": "You blow, softly: the whistle answers clear as a wren.",
        "fine": "You blow, softly: the whistle sings like a bird with opinions.",
    },
    "horse": {
        "rough": "You set the horse on the hearthstone. It stands, leaning "
                 "a little left, the way tired horses do.",
        "neat": "You set the horse on the hearthstone. It stands square, "
                "head up, ready for imaginary roads.",
        "fine": "You set the horse on the hearthstone. It stands somehow "
                "mid-gallop, though its hooves don't move.",
    },
    "comb": {
        "rough": "You test it once, drawing it through your hair. It "
                 "catches — honest work, not gentle work.",
        "neat": "You test it once, drawing it through your hair. It "
                "glides, catching only once.",
        "fine": "You test it once, drawing it through your hair. It "
                "glides like water over stone.",
    },
}

_WHITTLE_QUALITY_NOTES = {
    "rough": "The cuts show, honest and uneven — first work, and the "
             "village forgives first work.",
    "neat": "The lines are clean, the edges smoothed — somebody took "
             "their time.",
    "fine": "Smooth as river stone, the grain shining through — patient "
             "hands made this.",
}


def _whittle_finish_line(piece, quality):
    tmpl = _WHITTLE_FINISH[piece]
    if isinstance(tmpl, dict):
        return tmpl[quality]
    return tmpl.format(q=quality)


class CmdWhittle(Command):
    """
    Whittling — the hearthside hobby.

    Usage:
        whittle <spoon|whistle|horse|comb>
        whittle                (continue what you're carving)
        whittle abandon        (feed the half-made piece to the fire)

    Take a stick from the basket by the tavern hearth and carve. Three
    sessions of whittling finish a piece, which goes into your hands —
    tagged for the crafting chains to come. Bram notices who whittles.
    """

    key = "whittle"
    help_category = "Village"

    def func(self):
        loc = self.caller.location
        if not loc or not loc.tags.has("tavern", category="place"):
            self.caller.msg(
                "Whittle what, where? The whittling basket is by the hearth "
                "in the Tavern."
            )
            return
        arg = (self.args or "").strip().lower()
        name = self.caller.key
        cur = dict(self.caller.db.whittle or {})

        if arg == "abandon":
            if not cur.get("piece"):
                self.caller.msg("You're not whittling anything.")
                return
            word = _WOODWORK[cur["piece"]]["word"]
            self.caller.db.whittle = None
            self.caller.msg(
                f"The half-carved {word} goes into the hearth. The fire "
                "takes it without comment."
            )
            loc.msg_contents(
                f"{name} tosses a half-carved {word} into the hearth.",
                exclude=[self.caller],
            )
            return

        piece = None
        if arg:
            for key in _WOODWORK:
                if key in arg or arg in key:
                    piece = key
                    break
        cur_piece = cur.get("piece")
        if piece and cur_piece and piece != cur_piece:
            cur_word = _WOODWORK[cur_piece]["word"]
            self.caller.msg(
                f"You're already carving a {cur_word}. One thing at a "
                "time — see it through, or `whittle abandon` to feed it "
                "to the fire."
            )
            return

        # The keeper notices who whittles.
        keeper = None
        for obj in loc.contents:
            if obj.key == "Bram" and hasattr(obj, "note_interest"):
                obj.note_interest(self.caller, "whittling")
                keeper = obj
                break

        if not cur_piece:
            if not piece:
                self.caller.msg(
                    "Whittle what? The basket by the hearth holds sticks "
                    "for spoons, whistles, horses, and combs. "
                    "(Try: whittle spoon.)"
                )
                return
            cur = {"piece": piece, "sessions": 1}
            self.caller.db.whittle = cur
            self.caller.msg(
                _WOODWORK[piece]["start"] + "\n"
                + _WOODWORK[piece]["stages"][0]
            )
            loc.msg_contents(
                f"{name} settles by the hearth with a stick and a knife, "
                "and begins to whittle.",
                exclude=[self.caller],
            )
            return

        sessions = int(cur.get("sessions", 0)) + 1
        if sessions >= _WHITTLE_SESSIONS:
            self._finish(cur_piece, keeper)
            return
        cur["sessions"] = sessions
        self.caller.db.whittle = cur
        word = _WOODWORK[cur_piece]["word"]
        self.caller.msg(
            _WOODWORK[cur_piece]["stages"][sessions - 1]
            + f" (The {word} is taking shape — whittle on.)"
        )
        loc.msg_contents(
            f"{name} whittles on — pale shavings curling down onto the "
            "hearthstones.",
            exclude=[self.caller],
        )

    def _finish(self, piece, keeper):
        from evennia.utils import create

        loc = self.caller.location
        name = self.caller.key
        finished = int(self.caller.db.whittle_done or 0)
        quality = whittle_quality(finished)
        spec = _WOODWORK[piece]
        key = spec["made"].format(q=quality)
        desc = (
            f"{key[0].upper() + key[1:]}, whittled by {name}. "
            f"{spec['note']} {_WHITTLE_QUALITY_NOTES[quality]}"
        )
        obj = create.create_object(
            # Build-loop #16b: the spike Object typeclass carries the
            # stacked-name grammar fix ("two rough wooden spoons", not
            # "two a rough wooden spoons") for identical carried pieces.
            "typeclasses.objects.Object",
            key=key, location=self.caller,
            aliases=[spec["word"], f"whittled {spec['word']}",
                     f"wooden {spec['word']}"],
        )
        obj.db.desc = desc
        obj.tags.add("whittled", category="craft")
        obj.tags.add("crafted", category="craft")
        obj.db.made_by = name
        obj.db.quality = quality
        self.caller.db.whittle = None
        self.caller.db.whittle_done = finished + 1
        self.caller.msg(_whittle_finish_line(piece, quality))
        loc.msg_contents(
            f"{name} holds up the finished {spec['word']}.",
            exclude=[self.caller],
        )


# -- Whistle toot ------------------------------------------------------------
# The finished whistle should sound. `toot` / `blow whistle` finds a
# carried, finished whittled whistle and voices its quality line
# (already heard once at the finish bench) — now as a second instrument
# voice in the music/attunement loop, spectator-visible. The tavern cat
# reacts per quality, paying off the basket line about "unsettling the
# cat"; Bram notes "whistling" for returnee greetings.

_WHISTLE_TOOT_SPECTATOR = {
    "rough": "toots a rough wooden whistle — a hoarse, honest peep.",
    "neat": "lifts a neat wooden whistle — it answers clear as a wren.",
    "fine": "lifts a fine wooden whistle — and it sings like a bird with opinions.",
}

_WHISTLE_CAT = {
    "rough": "The tavern cat opens one eye, decides this is beneath it, "
             "and closes it again.",
    "neat": "The tavern cat's ears come up, curious, following the note.",
    "fine": "The tavern cat sits bolt upright, tail straight, like it has "
            "been called to something it cannot name.",
}


class CmdToot(Command):
    """
    Toot.

    Usage:
        toot
        blow whistle

    Lift a finished, whittled whistle you carry and blow it. The sound
    is the whistle's quality — rough peeps, neat rings, fine sings.
    Works anywhere; the tavern cat notices.
    """

    key = "toot"
    aliases = ["blow whistle"]
    help_category = "Village"

    def func(self):
        loc = self.caller.location
        name = self.caller.key
        whistle = None
        for obj in self.caller.contents:
            if not obj.tags.has("whittled", category="craft"):
                continue
            if "whistle" in obj.key.lower() or any(
                "whistle" in a.lower() for a in obj.aliases.all()
            ):
                whistle = obj
                break
        if whistle is None:
            self.caller.msg(
                "You've no whistle to blow. The basket by the tavern "
                "hearth holds sticks — `whittle whistle` starts one."
            )
            return
        quality = str(whistle.db.quality or "rough")
        if quality not in _WHITTLE_FINISH["whistle"]:
            quality = "rough"
        self.caller.msg(_WHITTLE_FINISH["whistle"][quality])
        if loc:
            loc.msg_contents(
                f"{name} {_WHISTLE_TOOT_SPECTATOR[quality]}",
                exclude=[self.caller],
            )
            cat = None
            keeper = None
            for obj in loc.contents:
                if obj.key == "the tavern cat":
                    cat = obj
                elif obj.key == "Bram" and hasattr(obj, "note_interest"):
                    keeper = obj
            if cat is not None:
                loc.msg_contents(_WHISTLE_CAT[quality])
            if keeper is not None:
                keeper.note_interest(self.caller, "whistling")


# -- arm wrestling ------------------------------------------------------
# Confrontation-lite: a social bout at the usual table in the Tavern.
# Challenge/accept flow, then both players `wrestle push` each round;
# the strain tells, best of three. Bram referees; the cat judges; the
# winner's name feeds the tavern rumor pool; Bram notes "wrestling"
# for returnee greetings.

_WRESTLE_STRAIN = [
    "Knuckles whiten. Somewhere in the room, a cup stops moving.",
    "The usual table groans in a joint it didn't know it had.",
    "Nobody at the bar is breathing.",
]

_WRESTLE_TIE = (
    "Locked — shoulders trembling, neither hand moving a hair's breadth."
)

_CHALLENGE_TTL = 600  # an unanswered challenge lapses after ten minutes


class CmdWrestle(Command):
    """
    Arm wrestle.

    Usage:
        wrestle <player>
        wrestle answer
        wrestle decline
        wrestle push
        wrestle quit

    Challenge someone in the Tavern to a bout at the usual table. Once
    both wrestlers are seated, each `wrestle push`es every round — the
    strain tells, best of three. Bram referees. House custom: the winner
    buys the loser a drink.
    """

    key = "wrestle"
    aliases = ["arm wrestle"]
    help_category = "Village"

    # -- helpers ------------------------------------------------------

    def _find_keeper(self):
        for obj in self.caller.location.contents:
            if obj.key == "Bram":
                return obj
        return None

    def _pair(self, me):
        """Return (partner_obj, state) or (None, None).

        state is a plain dict copy: {"a": key, "b": key,
        "rounds": {key: n}, "rolls": {key: n or None}}.
        """
        state = me.db.wrestle
        if not state:
            return None, None
        other_key = state.get("b") if state.get("a") == me.key else state.get("a")
        found = me.search(other_key, quiet=True)
        if isinstance(found, list):
            found = found[0] if found else None
        if (
            not found
            or found.location != me.location
            or me.key not in {state.get("a"), state.get("b")}
            or state.get("a") == state.get("b")
            or dict(found.db.wrestle or {}) != dict(state)
        ):
            # A bout only exists while both sides hold the same current
            # snapshot. A disconnected/re-entered partner must not resurrect
            # a bout that the other participant already abandoned.
            return None, None
        return found, dict(state)

    def _sync(self, me, partner, state):
        me.db.wrestle = dict(state)
        partner.db.wrestle = dict(state)

    def _clear(self, me, partner):
        me.db.wrestle = None
        partner.db.wrestle = None

    # -- dispatch -----------------------------------------------------

    def func(self):
        me = self.caller
        loc = me.location
        if not loc or not loc.tags.has("tavern", category="place"):
            me.msg(
                "Arm wrestling wants the Tavern — the usual table's there."
            )
            return
        arg = (self.args or "").strip().lower()
        if not arg:
            me.msg(
                "Wrestle whom? (Try: wrestle <player>.) Once you're in "
                "a bout, `wrestle push` each round."
            )
            return
        if arg in ("answer", "accept"):
            self._answer()
            return
        if arg == "decline":
            self._decline()
            return
        if arg in ("quit", "end", "leave"):
            self._quit()
            return
        if arg == "push":
            self._push()
            return
        self._challenge(arg)

    # -- challenge flow -------------------------------------------------

    def _challenge(self, arg):
        import time

        me = self.caller
        if me.db.wrestle:
            me.msg(
                "You're already mid-bout — finish it first (`wrestle "
                "quit` to walk away)."
            )
            return
        target = me.search(arg, quiet=True)
        if isinstance(target, list):
            target = target[0] if target else None
        if not target or not hasattr(target, "db"):
            me.msg(f"'{arg.strip()}' isn't here to wrestle.")
            return
        if target == me:
            me.msg("Wrestle yourself? The cat declines to referee.")
            return
        if not getattr(target, "account", None):
            # NPCs (the cat, Bram, anyone unplayed) can't hold up their end
            me.msg(
                f"{target.key} can't answer that — challenge one of "
                "the living."
            )
            return
        if target.db.wrestle:
            me.msg(
                f"{target.key} is already mid-bout. Wait for the table "
                "to clear."
            )
            return
        pending = target.db.wrestle_invite
        if pending:
            if time.time() - float(pending.get("at", 0)) <= _CHALLENGE_TTL:
                me.msg(
                    f"{target.key} already has a wrestling challenge from "
                    f"{pending.get('from', 'someone')}. Let them answer first."
                )
                return
            target.db.wrestle_invite = None  # expired; safe to replace
        target.db.wrestle_invite = {"from": me.key, "at": time.time()}
        me.location.msg_contents(
            f"{me.key} turns to {target.key} at the usual table. "
            "'Arm wrestling. You in?'"
        )
        target.msg(
            f"{me.key} challenges you to arm wrestling. "
            "(wrestle answer / wrestle decline)"
        )

    def _answer(self):
        import time

        me = self.caller
        if me.db.wrestle:
            me.msg("You're already mid-bout — finish it first.")
            return
        invite = me.db.wrestle_invite
        if not invite:
            me.msg("No one's challenged you to wrestle.")
            return
        me.db.wrestle_invite = None
        if time.time() - float(invite.get("at", 0)) > _CHALLENGE_TTL:
            me.msg("That challenge's gone cold.")
            return
        inviter = me.search(invite.get("from", ""), quiet=True)
        if isinstance(inviter, list):
            inviter = inviter[0] if inviter else None
        if (
            not inviter
            or inviter.location != me.location
            or inviter.db.wrestle
            or not hasattr(inviter, "db")
        ):
            me.msg("The challenger has moved on — the bout's gone cold.")
            return
        state = {
            "a": inviter.key,
            "b": me.key,
            "rounds": {inviter.key: 0, me.key: 0},
            "rolls": {inviter.key: None, me.key: None},
        }
        self._sync(inviter, me, state)
        loc = me.location
        loc.msg_contents(
            f"{me.key} takes the seat across from {inviter.key} at the "
            "usual table. Hands grip."
        )
        keeper = self._find_keeper()
        if keeper is not None:
            loc.msg_contents(
                'Bram plants a hand on the usual table. "Right. Elbows '
                'down, and no rising from your seats. Best of three — '
                'and the table tells no lies."'
            )
            keeper.note_interest(inviter, "wrestling")
            keeper.note_interest(me, "wrestling")
        cat = next(
            (o for o in loc.contents if o.key == "the tavern cat"), None
        )
        if cat is not None:
            loc.msg_contents(
                "The tavern cat relocates to the high shelf, out of "
                "elbow range."
            )
        loc.msg_contents("Round one. (wrestle push)")

    def _decline(self):
        me = self.caller
        invite = me.db.wrestle_invite
        if not invite:
            me.msg("No one's challenged you to wrestle.")
            return
        me.db.wrestle_invite = None
        inviter = invite.get("from", "someone")
        me.location.msg_contents(
            f"{me.key} shakes their head at {inviter}. 'Another night "
            "— my wrist still remembers the last one.'"
        )

    def _quit(self):
        me = self.caller
        partner, _state = self._pair(me)
        if partner is None:
            if me.db.wrestle:
                me.db.wrestle = None
                me.msg("The bout's gone cold — the room moved on.")
            else:
                me.msg("You're not wrestling anyone.")
            return
        self._clear(me, partner)
        me.location.msg_contents(
            f"{me.key} steps back from the usual table. 'Enough — my "
            "wrist thanks me.'"
        )

    # -- rounds ---------------------------------------------------------

    def _push(self):
        from evennia.contrib.rpg.dice import roll as roll_bones

        me = self.caller
        partner, state = self._pair(me)
        if partner is None:
            if me.db.wrestle:
                me.db.wrestle = None
                me.msg("The bout's gone cold — the room moved on.")
            else:
                me.msg("You're not wrestling anyone.")
            return
        rounds = dict(state.get("rounds", {}))
        rolls = dict(state.get("rolls", {}))
        if rolls.get(me.key) is not None:
            me.msg(
                f"You've already pushed — the table waits on "
                f"{partner.key}."
            )
            return
        _, _, _, bones = roll_bones(2, 6, return_tuple=True)
        rolls[me.key] = int(bones[0]) + int(bones[1])
        state["rounds"] = rounds
        state["rolls"] = rolls
        me.msg("You bear down — tendons stand out like rope.")
        me.location.msg_contents(f"{me.key} bears down.", exclude=[me])
        if rolls.get(partner.key) is None:
            self._sync(me, partner, state)
            return
        # Both pushed: the strain tells.
        ra, rb = rolls[me.key], rolls[partner.key]
        completed = rounds.get(me.key, 0) + rounds.get(partner.key, 0)
        loc = me.location
        loc.msg_contents(
            f"The strain tells: {me.key} {ra}, {partner.key} {rb}."
        )
        if ra == rb:
            state["rolls"] = {me.key: None, partner.key: None}
            self._sync(me, partner, state)
            loc.msg_contents(f"{_WRESTLE_TIE} Push again.")
            return
        winner = me if ra > rb else partner
        loser = partner if ra > rb else me
        wkey, lkey = winner.key, loser.key
        rounds[wkey] = rounds.get(wkey, 0) + 1
        state["rounds"] = rounds
        state["rolls"] = {me.key: None, partner.key: None}
        self._sync(me, partner, state)
        loc.msg_contents(
            _WRESTLE_STRAIN[min(completed, len(_WRESTLE_STRAIN) - 1)]
        )
        wr, lr = rounds.get(wkey, 0), rounds.get(lkey, 0)
        if wr >= 2:
            self._finish(me, partner, winner, loser)
            return
        score = (
            f"One to {wkey}, none to {lkey}."
            if (wr, lr) == (1, 0)
            else "One apiece. The table's not done with them."
        )
        loc.msg_contents(f"{wkey} takes the round. {score} (wrestle push)")

    def _finish(self, me, partner, winner, loser):
        loc = me.location
        wkey, lkey = winner.key, loser.key
        self._clear(me, partner)
        keeper = self._find_keeper()
        loc.msg_contents(
            f"{wkey}'s hand meets the wood. The room lets out its breath."
        )
        if keeper is not None:
            loc.msg_contents(
                f'Bram raps the table. "There it is. {wkey}, you buy '
                f'{lkey} a drink — house custom."'
            )
        loc.msg_contents(
            f"{lkey} shakes out the hand, grinning despite itself."
        )
        try:
            from world.events import publish_world_event

            publish_world_event(
                "arm-wrestling",
                actor=winner,
                payload={"winner": wkey, "loser": lkey},
                rumor=(
                    f"{wkey} beat {lkey} at arm wrestling, at the usual "
                    "table."
                ),
            )
        except Exception:
            pass


class CmdConfess(Command):
    """
    Confess.

    Usage:
        confess <words>

    Kneel in the confessional box at St. Lazarus and say it. What's said
    in there stays in there — the ledger records that a confession
    happened, never what was said. The village will notice you were a
    long time in the box, though. Father Andrei hears you if he's here;
    the box hears you regardless.
    """

    key = "confess"
    help_category = "Village"

    def func(self):
        words = (self.args or "").strip()
        if not words:
            self.caller.msg("Confess what? (Try: confess <words>.)")
            return
        loc = self.caller.location
        if not loc or loc.key != "St. Lazarus Church":
            self.caller.msg(
                "The box is in the church. Confession happens there."
            )
            return
        # The seal: the ledger records the event, never the content.
        try:
            from world.events import publish_world_event

            publish_world_event(
                "confession",
                actor=self.caller,
                payload={"sealed": True},
                rumor="Someone was a long time in the box today.",
            )
        except Exception:
            pass
        andrei = next(
            (o for o in loc.contents if o.key == "Father Andrei"), None
        )
        if andrei:
            self.caller.msg(
                'Through the grille, Andrei\'s voice, low: "Ego te absolvo. '
                "Go — and walk lighter than you came in.\""
            )
            loc.msg_contents(
                f"{self.caller.key} kneels in the confessional a long time.",
                exclude=[self.caller],
            )
        else:
            self.caller.msg(
                "The box is empty of priests, but the curtain is drawn and "
                "the kneeler is worn. You say it anyway. The candles don't "
                "flicker. Somehow that's an answer."
            )
            loc.msg_contents(
                f"{self.caller.key} kneels in the confessional a long time.",
                exclude=[self.caller],
            )
        # Andrei remembers who came to the box. Trust, observably.
        self.caller.db.confessed = True
