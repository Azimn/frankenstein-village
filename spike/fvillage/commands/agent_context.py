"""Shared low-friction machine-readable context for humans and AI players.

This is an observational adapter over normal gameplay, not a parallel API
with extra privileges or objective omniscient world information.
"""

from __future__ import annotations

import json

from evennia import Command


VERSION = 1


def payload_for(mask):
    """Only reveal the location and exits already available to this mask."""
    room = getattr(mask, "location", None)
    side = "unknown"
    if room and room.tags.has("ooc", category="side"):
        side = "ooc"
    elif room and room.tags.has("ic", category="side"):
        side = "ic"
    visible_exits = []
    exit_targets = {}
    nearby = []
    if room:
        for doorway in room.exits:
            # A search-locked or view-locked exit must not appear here.
            if not doorway.access(mask, "search", default=True):
                continue
            if not doorway.access(mask, "view", default=True):
                continue
            if doorway.access(mask, "traverse", default=True):
                visible_exits.append(str(doorway.key))
                destination = getattr(doorway, "destination", None)
                # Traversable exit destinations are available from normal
                # look/exit inspection, not a hidden world map.
                if destination and destination.access(mask, "view", default=True):
                    exit_targets[str(doorway.key)] = str(destination.key)
        exit_ids = {doorway.id for doorway in room.exits}
        for obj in room.contents:
            if obj == mask or obj.id in exit_ids:
                continue
            if not obj.access(mask, "view", default=True):
                continue
            if not obj.access(mask, "search", default=True):
                continue
            label = " ".join(str(obj.get_display_name(mask)).split())
            if label:
                nearby.append(label[:100])
    result = {
        "version": VERSION,
        "schema": "fvillage.agent_context.v1",
        "side": side,
        "location": str(room.key) if room else None,
        "exits": sorted(set(visible_exits)),
        "exit_targets": {key: exit_targets[key] for key in sorted(exit_targets)},
        "visible_nearby": sorted(set(nearby), key=str.casefold)[:32],
        "turn_model": "send one text command, read its response, observe again",
        "auth": "regular account and character rules apply",
        "commands": {
            "observe": "look",
            "inspect": "examine <visible thing>",
            "move": "<visible exit>",
            "help": "help <topic>",
        },
    }
    if side == "ooc":
        result["commands"].update({
            "world_entry": "follow the Inn front door",
            "calling": "calling list",
            "guide": "guide",
            "personal_return": "agenda",
        })
        result["boundary"] = "out_of_character"
    elif side == "ic":
        result["commands"].update({
            "speak": "say <words>",
            "whisper": "whisper <person> = <words>",
            "profession": "calling",
            "events": "journal",
            "field_notes": "journal discoveries",
            "route_reports": "survey",
            "route_inspection": "survey report",
            "social": "commons",
            "local_guide": "guide",
            "personal_return": "agenda",
            "community_work": "commission",
            "public_schedule": "calendar",
        })
        result["boundary"] = "in_character"
        if room and room.tags.has("tavern", category="place"):
            result["commands"]["public_rumors"] = "rumors"
            result["commands"]["hearth"] = "hearth"
        if room and room.key == "Village Square":
            result["commands"]["public_commons"] = "commons"
            result["commands"]["firewood"] = "hearth gather"
        if room and room.key == "St. Lazarus Church":
            result["commands"]["confessional"] = "confess"
        if room and room.key == "The Lamp Shop":
            result["commands"]["shop"] = "look"
    return result


class CmdAgentContext(Command):
    """Show machine-readable observations and valid public interaction syntax.

    Usage:
        agent
        agent context

    Returns a single FV_AGENT_JSON line of JSON. This is the same information
    humans are entitled to, using the same ordinary character permissions.
    The command never chooses an action or reveals private world flags.
    """

    key = "agent"
    aliases = ["context"]
    help_category = "Village"

    def func(self):
        raw = (self.args or "").strip().lower()
        if raw not in {"", "context"}:
            self.caller.msg('Use "agent" or "agent context".')
            return
        self.caller.msg(
            "FV_AGENT_JSON "
            + json.dumps(
                payload_for(self.caller), sort_keys=True, ensure_ascii=True,
                separators=(",", ":"),
            )
        )


class CmdAgentLobby(Command):
    """Account-stage bootstrap hints without world entry or privileged data.

    Usage:
        agentlogin

    Works before choosing a mask. This is a read-only explanation.
    """

    key = "agentlogin"
    help_category = "Village"
    account_caller = True

    def func(self):
        account = self.account
        substrate = getattr(account.db, "substrate", None) if account else None
        gate_open = bool(
            substrate in {"human", "ai"}
            and account.db.disclosure_consent is True
        )
        steps = {
            "version": VERSION,
            "schema": "fvillage.agent_login.v1",
            "side": "account_ooc",
            "disclosure_declared": gate_open,
            "commands": {
                "declare": (
                    ["substrate human", "substrate ai"]
                    if not gate_open else None
                ),
                "create_mask": "charcreate <character name>" if gate_open else None,
                "choose_mask": "ic <character name>" if gate_open else None,
                "help": "help",
            },
            "rule": "One active mask per account. Front door separates OOC and IC.",
        }
        self.caller.msg(
            "FV_AGENT_JSON "
            + json.dumps(
                steps, sort_keys=True, ensure_ascii=True,
                separators=(",", ":"),
            )
        )
