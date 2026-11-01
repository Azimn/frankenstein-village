"""Pure, fail-closed one-shot tavern-pot repair for GDD-EDGE-02.

The original communal soup pot is the only equipment authority. A signed
Innkeep restriction precedes a distinct Smith's physical fitting installation.
The ordinary NPC kitchen remains open; only player simmering is suspended.
"""
from __future__ import annotations

import copy

CONDITIONS = ("loose", "restricted", "working")
MAX_NAME = 70


def _positive(value):
    if type(value) is not int or value <= 0:
        return None
    return value


def _clock(day, hour):
    return (_positive(day) is not None and type(hour) is int
            and 0 <= hour <= 23)


def normalize(raw):
    if raw is None:
        return {"condition": "loose", "restriction": None, "repair": None}
    if not hasattr(raw, "get"):
        return {"condition": "invalid", "restriction": None, "repair": None}
    state = copy.deepcopy(dict(raw))
    if state.get("condition") not in CONDITIONS:
        return {"condition": "invalid", "restriction": None, "repair": None}
    if state["condition"] == "loose":
        if state.get("restriction") or state.get("repair"):
            return {"condition": "invalid", "restriction": None, "repair": None}
        return {"condition": "loose", "restriction": None, "repair": None}
    restriction = state.get("restriction")
    if not hasattr(restriction, "get"):
        return {"condition": "invalid", "restriction": None, "repair": None}
    required = ("account_id", "mask_id", "event_id", "pot_id", "day")
    if any(_positive(restriction.get(key)) is None for key in required):
        return {"condition": "invalid", "restriction": None, "repair": None}
    if not _clock(restriction["day"], restriction.get("hour")):
        return {"condition": "invalid", "restriction": None, "repair": None}
    restriction = {key: restriction[key] for key in required}
    restriction["hour"] = state["restriction"]["hour"]
    restriction["mask"] = str(state["restriction"].get("mask") or "")[:MAX_NAME]
    if state["condition"] == "restricted":
        if state.get("repair"):
            return {"condition": "invalid", "restriction": None, "repair": None}
        return {"condition": "restricted", "restriction": restriction, "repair": None}
    repair = state.get("repair")
    if not hasattr(repair, "get"):
        return {"condition": "invalid", "restriction": None, "repair": None}
    fields = ("account_id", "mask_id", "event_id", "pot_id", "item_id",
              "forge_event_id", "restriction_event_id", "day")
    if any(_positive(repair.get(key)) is None for key in fields):
        return {"condition": "invalid", "restriction": None, "repair": None}
    if (not _clock(repair["day"], repair.get("hour"))
            or repair["pot_id"] != restriction["pot_id"]
            or repair["restriction_event_id"] != restriction["event_id"]
            or repair["account_id"] == restriction["account_id"]):
        return {"condition": "invalid", "restriction": None, "repair": None}
    if (repair["day"], repair["hour"]) < (restriction["day"], restriction["hour"]):
        return {"condition": "invalid", "restriction": None, "repair": None}
    result = {key: repair[key] for key in fields}
    result["hour"] = repair["hour"]
    result["mask"] = str(repair.get("mask") or "")[:MAX_NAME]
    return {"condition": "working", "restriction": restriction, "repair": result}


def restrict(raw, *, day, hour, account_id, mask_id, mask, pot_id, event_id):
    state = normalize(raw)
    if state["condition"] != "loose":
        return state, False, "The pot is already restricted, repaired, or invalid."
    if (not _clock(day, hour) or any(_positive(v) is None for v in
            (account_id, mask_id, pot_id, event_id))):
        return state, False, "A real Innkeep, pot, event and village time are required."
    state["condition"] = "restricted"
    state["restriction"] = {
        "day": day, "hour": hour, "account_id": account_id,
        "mask_id": mask_id, "mask": str(mask)[:MAX_NAME],
        "pot_id": pot_id, "event_id": event_id,
    }
    return state, True, None


def repair(raw, *, day, hour, account_id, mask_id, mask, pot_id,
           event_id, item_id, forge_event_id, restriction_event_id):
    state = normalize(raw)
    if state["condition"] != "restricted":
        return state, False, "There is no valid outstanding Innkeep restriction."
    restriction = state["restriction"]
    if (not _clock(day, hour) or any(_positive(v) is None for v in
            (account_id, mask_id, pot_id, event_id, item_id, forge_event_id,
             restriction_event_id))):
        return state, False, "The repair needs signed workers, a real fitting and time."
    if account_id == restriction["account_id"] or mask_id == restriction["mask_id"]:
        return state, False, "The Innkeep and Smith must be independent players."
    if pot_id != restriction["pot_id"] or restriction_event_id != restriction["event_id"]:
        return state, False, "This repair does not match the restricted physical pot."
    if (day, hour) < (restriction["day"], restriction["hour"]):
        return state, False, "The village clock moved behind the Innkeep's decision."
    state["condition"] = "working"
    state["repair"] = {
        "day": day, "hour": hour, "account_id": account_id,
        "mask_id": mask_id, "mask": str(mask)[:MAX_NAME],
        "pot_id": pot_id, "event_id": event_id, "item_id": item_id,
        "forge_event_id": forge_event_id,
        "restriction_event_id": restriction_event_id,
    }
    return state, True, None


def public_lines(raw):
    state = normalize(raw)
    if state["condition"] == "loose":
        return ("The soup pot's iron lid hinge is loose. An Innkeep can "
                "soup restrict service until a Smith fits a real replacement.")
    if state["condition"] == "restricted":
        return ("The Innkeep has restricted player soup simmering because "
                "the pot lid hinge is unsafe. A Smith needs a physical forged "
                "hinge and may use soup repair here. Bram's NPC fare remains.")
    if state["condition"] == "working":
        return ("The pot's iron lid hinge has been physically repaired by "
                + state["repair"]["mask"] + " (signed event "
                + str(state["repair"]["event_id"]) + ").")
    return "The pot's repair record is inconsistent; no repair can be accepted."
