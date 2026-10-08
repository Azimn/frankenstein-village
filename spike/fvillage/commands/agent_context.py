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
    if room:
        for doorway in room.exits:
            # A search-locked or view-locked exit must not appear here.
            if not doorway.access(mask, "search", default=True):
                continue
            if not doorway.access(mask, "view", default=True):
                continue
            if doorway.access(mask, "traverse", default=True):
                visible_exits.append(str(doorway.key))
    result = {
        "version": VERSION,
        "schema": "fvillage.agent_context.v1",
        "side": side,
        "location": str(room.key) if room else None,
        "exits": sorted(set(visible_exits)),
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
        })
        result["boundary"] = "out_of_character"
    elif side == "ic":
        result["commands"].update({
            "speak": "say <words>",
            "whisper": "whisper <person> = <words>",
            "profession": "calling",
            "events": "journal",
            "social": "commons",
            "local_guide": "guide",
        })
        result["boundary"] = "in_character"
        if room and room.tags.has("tavern", category="place"):
            result["commands"]["public_rumors"] = "rumors"
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
                "declare": "substrate ai" if not gate_open else None,
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
