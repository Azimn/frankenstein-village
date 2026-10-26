#!/usr/bin/env python3
"""Source-owner audit for the existing ten Callings and the Master GDD 45 edges.

A static registry, NOT a new quest system or gameplay-completion certificate.
It checks the repo's actual cmdset/commands/world functions using Python AST
without importing Evennia or touching a game database.
"""
from __future__ import annotations

import argparse
import ast
import json
from pathlib import Path

from content_inventory import build_inventory

ROOT = Path(__file__).resolve().parents[1]
WORLD = Path("spike/fvillage/world")
CMDS = Path("spike/fvillage/commands")
PAIR_REGISTER = Path("ops/MASTER_GDD_45_EDGE_REGISTER_2026-10-25.json")

# Existing player verb, command-module, command class, world-module, callable.
# Multiple commands can share one world owner, and one command can appear in
# several Callings: DO NOT count these entries as distinct completed jobs.
ANCHORS = {
    "innkeep": (
        ("soup", "soup_cmd.py", "CmdSoup", "soup_kitchen.py", "prep"),
        ("hearth", "hearth_cmd.py", "CmdHearth", "community_hearth.py", "tend"),
        ("care", "village_cmds.py", "CmdCare", "tavern_care.py", "provide_innkeep_care"),
    ),
    "chronicler": (
        ("chronicle", "village_cmds.py", "CmdChronicle", "publications.py", "annotate_chronicle"),
        ("trade", "market_cmd.py", "CmdTrade", "market_work.py", "perform"),
    ),
    "smith": (
        ("workshop", "workshop_cmd.py", "CmdWorkshop", "workshop_work.py", "forge"),
        ("trade", "market_cmd.py", "CmdTrade", "market_work.py", "perform"),
    ),
    "healer": (
        ("clinic", "clinic_cmd.py", "CmdClinic", "clinic_work.py", "act"),
        ("care", "village_cmds.py", "CmdCare", "tavern_care.py", "submit_healer_care_assessment"),
    ),
    "merchant": (
        ("trade", "market_cmd.py", "CmdTrade", "market_work.py", "perform"),
        ("soup", "soup_cmd.py", "CmdSoup", "soup_kitchen.py", "procure"),
        ("commission", "commission_cmd.py", "CmdCommission", "civic_work.py", "pledge"),
    ),
    "wanderer": (
        ("courier", "courier_cmd.py", "CmdCourier", "courier_work.py", "collect"),
        ("survey", "survey_cmd.py", "CmdSurvey", "route_work.py", "report"),
    ),
    "performer": (
        ("stage", "stage_cmd.py", "CmdStage", "stage_work.py", "act"),
    ),
    "detective": (
        ("bridgework", "bridge_cmd.py", "CmdBridgeWork", "bridge_work.py", "act"),
        ("mystery", "village_cmds.py", "CmdMystery", "public_mysteries.py", "submit_theory"),
    ),
    "hound": (
        ("survey", "survey_cmd.py", "CmdSurvey", "route_work.py", "report"),
    ),
    "mystic": (
        ("mystic", "mystic_cmd.py", "CmdMystic", "mystic_work.py", "study"),
    ),
}
# V numbering in final GDD: V3 is Innkeep/Healer, V4 Innkeep/Merchant.
V_OWNERS = {
    3: (("tavern_care.py", "submit_healer_care_assessment"),
        ("tavern_care.py", "provide_innkeep_care")),
    4: (("soup_kitchen.py", "procure"), ("soup_kitchen.py", "deliver")),
    10: (("market_work.py", "perform"), ("market_standards.py", "apply")),
    11: (("well_mushroom_warning.py", "submit_healer_finding"),
         ("well_mushroom_warning.py", "publish_public_warning")),
    12: (("market_work.py", "perform"), ("market_standards.py", "apply")),
    19: (("repair_case.py", "procure_merchant_repair_part"),
         ("repair_case.py", "complete_smith_lamp_repair")),
}

def _tree(file: Path) -> ast.Module:
    return ast.parse(file.read_text(encoding="utf-8"), filename=str(file))

def _definitions(file: Path) -> dict[str, int]:
    return {node.name: node.lineno for node in _tree(file).body
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef))}

def _command_key(file: Path, name: str) -> str:
    for node in _tree(file).body:
        if isinstance(node, ast.ClassDef) and node.name == name:
            for field in node.body:
                if isinstance(field, ast.Assign) and any(
                    isinstance(t, ast.Name) and t.id == "key" for t in field.targets
                ):
                    return str(ast.literal_eval(field.value))
            raise ValueError(f"{name} lacks literal command key in {file}")
    raise ValueError(f"{name} not defined in {file}")

def _registered_commands(file: Path) -> set[str]:
    commands = set()
    for node in ast.walk(_tree(file)):
        if (isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute)
            and node.func.attr == "add"
            and isinstance(node.func.value, ast.Name)
            and node.func.value.id == "self"
            and node.args and isinstance(node.args[0], ast.Call)
            and isinstance(node.args[0].func, ast.Name)):
            commands.add(node.args[0].func.id)
    return commands

def audit(root: Path = ROOT, *, source_ref: str | None = None) -> dict:
    design = json.loads((root / PAIR_REGISTER).read_text(encoding="utf-8"))
    pairs = design["edges"]
    if [e["number"] for e in pairs] != list(range(1, 46)):
        raise ValueError("Master GDD edge register must contain ordered numbers 1–45")
    if design["baselines"] != {"V": 6, "S": 6, "D": 24, "C": 9}:
        raise ValueError("Master GDD baseline edge types changed unexpectedly")
    configured = set(build_inventory(root)["calling_definitions"]["ids"])
    if configured != set(ANCHORS):
        raise ValueError(f"Role drift: {configured ^ set(ANCHORS)}")
    registered = _registered_commands(root / CMDS / "default_cmdsets.py")
    cache = {}
    def function_reference(module: str, name: str) -> dict:
        if module not in cache:
            cache[module] = _definitions(root / WORLD / module)
        line = cache[module].get(name)
        if line is None:
            raise ValueError(f"Missing world function: {module}:{name}")
        return {"path": str(WORLD / module), "line": line, "name": name}
    roles = {}
    for role, anchors in ANCHORS.items():
        entries = []
        for key, command_file, cls, module, fn in anchors:
            path = CMDS / command_file
            actual_key = _command_key(root / path, cls)
            if actual_key != key:
                raise ValueError(f"{role}: {cls} key changed: {actual_key}")
            if cls not in registered:
                raise ValueError(f"{role}: {cls} not in character cmdset")
            source_line = _definitions(root / path)[cls]
            entries.append({
                "command_key": key,
                "command_class": cls,
                "command_source": {"path": str(path), "line": source_line},
                "world_source": function_reference(module, fn),
                "proof_level": "static_class_and_source_function",
            })
        roles[role] = {
            "existing_entrypoint_examples": entries,
            "distinct_jobs_verified": None,
            "authored_quests_verified": None,
            "normal_client_proof": None,
            "return_and_replay_proof": None,
            "uncoached_player_quality": None,
        }
    edges = []
    for pair in pairs:
        row = {
            "id": pair["id"],
            "number": pair["number"],
            "calling_a": pair["calling_a"],
            "calling_b": pair["calling_b"],
            "gdd_baseline": pair["baseline_class"],
            "static_source_examples": [
                function_reference(module, fn)
                for module, fn in V_OWNERS.get(pair["number"], ())
            ],
            "two_distinct_role_actions_playtested": None,
            "world_transition_evidence": None,
            "two_account_evidence": None,
            "post_restart_evidence": None,
            "uncoached_quality_evidence": None,
            "gameplay_complete": False,
        }
        if (pair["number"] in V_OWNERS) != (pair["baseline_class"] == "V"):
            raise ValueError(f"V owner mismatch: GDD edge {pair['number']}")
        edges.append(row)
    if (edges[2]["calling_a"], edges[2]["calling_b"]) != ("Innkeep", "Healer"):
        raise ValueError("Final PDF V3 was transcribed incorrectly")
    if (edges[3]["calling_a"], edges[3]["calling_b"]) != ("Innkeep", "Merchant"):
        raise ValueError("Final PDF V4 was transcribed incorrectly")
    return {
        "schema": "fvillage.gdd_phase_a_source_audit.v1",
        "source_ref": source_ref,
        "scope": "static AST source and cmdset checks only",
        "live_world_executed": False,
        "roles": roles,
        "edges": edges,
        "design_gaps_to_validate": [
            "Hound: current source guide offers the shared route survey, not proof of distinct patrol/protection/rescue gameplay; GDD 8.9 and edge 38.",
            "Six V chains have source anchors but do not, by themselves, certify 45 completed interactions, ten fulfilled job quotas or enjoyment.",
        ],
    }

def markdown(data: dict) -> str:
    out = [
        "# Phase A: source-backed Calling entrypoints",
        "",
        "All evidence below is source inspection, NOT proof of successful game play.",
        f"Source: {data['source_ref'] or 'unspecified working copy'}",
        "",
        "| Calling | Registered example commands | Source owners | Playable complete |",
        "| --- | --- | --- | --- |",
    ]
    for role, item in data["roles"].items():
        commands = ", ".join(e["command_key"] for e in item["existing_entrypoint_examples"])
        paths = ", ".join(sorted({
            e["world_source"]["path"].rsplit("/", 1)[-1]
            for e in item["existing_entrypoint_examples"]
        }))
        out.append(f"| {role.title()} | {commands} | {paths} | UNVERIFIED |")
    out += ["", "## GDD V relationships with static source examples", "",
            "| Pair | Existing source functions | Gameplay verified |",
            "| --- | --- | --- |"]
    for edge in data["edges"]:
        if edge["gdd_baseline"] != "V":
            continue
        owners = "; ".join(
            f"{ref['path']}:{ref['line']}" for ref in edge["static_source_examples"]
        )
        out.append(
            f"| V{edge['number']} {edge['calling_a']} + {edge['calling_b']} | "
            f"{owners} | UNVERIFIED by this script |"
        )
    out += [
        "", "## First implementation gap to test",
        "",
        "Wanderer and Hound both use the registered survey command and",
        "route_work.report. This does not establish distinct Hound protection",
        "and rescue activities promised by GDD 8.9 and edge 38.",
        "Test live current behavior before changing the shared route system.",
        "",
        "Source-checked entrypoints are not content quotas, gameplay coverage,",
        "player enjoyment, or a reason to create another quest framework.",
    ]
    return "\n".join(out) + "\n"

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-ref", default=None)
    parser.add_argument("--format", choices=("json", "markdown"), default="markdown")
    args = parser.parse_args()
    result = audit(source_ref=args.source_ref)
    print(json.dumps(result, indent=2) if args.format == "json" else markdown(result), end="\n")

if __name__ == "__main__":
    main()
