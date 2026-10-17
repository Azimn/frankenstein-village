#!/usr/bin/env python3
"""Conservative, reproducible static inventory for Frankenstein Village.

This scanner deliberately counts definitions and bootstrap references, never
claims that a path is discoverable, completable, enjoyable, or reachable through
an ordinary player session. No Evennia import or database access is required.
"""

from __future__ import annotations

import argparse
import ast
import json
import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
WORLD = Path("spike/fvillage/world")

REGISTRIES = {
    "situation_templates": ("situations.py", "TEMPLATES", "ensure_situations"),
    "random_incident_definitions": ("random_incidents.py", "DEFINITIONS", "ensure_random_incidents"),
    "timed_incident_definitions": ("timed_incidents.py", "TEMPLATES", "ensure_timed_incidents"),
    "server_event_definitions": ("server_events.py", "DEFINITIONS", "ensure_server_events"),
    "scheduled_event_definitions": ("scheduled_events.py", "DEFINITIONS", "ensure_scheduled_events"),
    "seasonal_framework_definitions": ("seasonal_frameworks.py", "DEFINITIONS", "ensure_seasonal_frameworks"),
    "public_mystery_definitions": ("public_mysteries.py", "DEFINITIONS", "ensure_public_mysteries"),
    "private_mystery_definitions": ("private_mysteries.py", "DEFINITIONS", "ensure_private_mysteries"),
}
FULL_LAUNCH_TARGETS = {
    "random_incident_definitions": 75,
    "timed_incident_definitions": 30,
    "server_event_definitions": 10,
}


def _parse(path: Path) -> ast.Module:
    return ast.parse(path.read_text(encoding="utf-8"), filename=str(path))


def _assignment(tree: ast.Module, name: str) -> ast.AST:
    for statement in tree.body:
        if isinstance(statement, ast.Assign):
            if any(isinstance(target, ast.Name) and target.id == name for target in statement.targets):
                return statement.value
        elif isinstance(statement, ast.AnnAssign):
            if isinstance(statement.target, ast.Name) and statement.target.id == name:
                return statement.value
    raise ValueError(f"Missing top-level assignment: {name}")


def _names(tree: ast.Module) -> dict[str, object]:
    resolved = {}
    for statement in tree.body:
        if not isinstance(statement, ast.Assign):
            continue
        if len(statement.targets) != 1 or not isinstance(statement.targets[0], ast.Name):
            continue
        try:
            resolved[statement.targets[0].id] = ast.literal_eval(statement.value)
        except (ValueError, TypeError, SyntaxError, MemoryError, RecursionError):
            pass
    return resolved


def _resolve_key(node: ast.AST, names: dict[str, object]) -> str:
    if isinstance(node, ast.Name) and isinstance(names.get(node.id), (str, int)):
        return str(names[node.id])
    try:
        value = ast.literal_eval(node)
    except (ValueError, TypeError, SyntaxError, MemoryError, RecursionError):
        raise ValueError(f"Non-static inventory key at line {getattr(node, 'lineno', '?')}") from None
    if not isinstance(value, (str, int)):
        raise ValueError("Inventory key is not a stable string or integer")
    return str(value)


def _mapping_keys(tree: ast.Module, name: str) -> list[str]:
    assignment = _assignment(tree, name)
    if not isinstance(assignment, ast.Dict):
        raise ValueError(f"{name} is no longer a static dictionary")
    names = _names(tree)
    keys = [_resolve_key(node, names) for node in assignment.keys]
    if len(keys) != len(set(keys)):
        raise ValueError(f"Repeated identifiers in {name}")
    return keys


def _seed_ids(tree: ast.Module) -> list[int]:
    expression = _assignment(tree, "PLAYABLE_RUMOR_IDS")
    if not (
        isinstance(expression, ast.Call)
        and isinstance(expression.func, ast.Name)
        and expression.func.id in {"frozenset", "set"}
        and len(expression.args) == 1
    ):
        raise ValueError("PLAYABLE_RUMOR_IDS no longer uses a static set")
    values = ast.literal_eval(expression.args[0])
    if not isinstance(values, (set, tuple, list)):
        raise ValueError("PLAYABLE_RUMOR_IDS must be a literal collection")
    return sorted({int(value) for value in values})


def _rooms(tree: ast.Module) -> list[dict[str, str]]:
    """Inspect only top-level world-construction calls, excluding room factories."""
    result = []
    for statement in tree.body:
        if not isinstance(statement, (ast.Expr, ast.Assign)):
            continue
        call = statement.value
        if not (isinstance(call, ast.Call) and isinstance(call.func, ast.Name)
                and call.func.id == "get_or_create_room" and call.args):
            continue
        name = ast.literal_eval(call.args[0])
        fields = {kw.arg: ast.literal_eval(kw.value) for kw in call.keywords
                  if kw.arg in {"side", "place"}}
        result.append({"name": name, "side": fields.get("side", "unknown"),
                       "place": fields.get("place", "")})
    return result


def _resident_count(tree: ast.Module) -> int:
    assignment = _assignment(tree, "RESIDENTS")
    if not isinstance(assignment, (ast.Tuple, ast.List)):
        raise ValueError("RESIDENTS is no longer a static population declaration")
    count = sum(
        isinstance(node, ast.Call) and isinstance(node.func, ast.Name)
        and node.func.id == "_resident"
        for node in assignment.elts
    )
    if count != len(assignment.elts):
        raise ValueError("Some residents no longer use the audited _resident constructor")
    return count


def _top_level_calls(tree: ast.Module) -> set[str]:
    calls: set[str] = set()
    for statement in tree.body:
        if isinstance(statement, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            continue
        for node in ast.walk(statement):
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Name):
                calls.add(node.func.id)
    return calls


def build_inventory(root: Path = ROOT) -> dict:
    world_root = root / WORLD
    build = _parse(world_root / "build_spike.py")
    bootstrap_calls = _top_level_calls(build)
    categories = {}
    for category, (module, constant, initializer) in REGISTRIES.items():
        ids = _mapping_keys(_parse(world_root / module), constant)
        categories[category] = {
            "count": len(ids),
            "ids": ids,
            "source": str(WORLD / module),
            "bootstrap_initialization_called": initializer in bootstrap_calls,
            "interpretation": "static_definition_only",
        }

    room_specs = _rooms(build)
    if len({spec["name"] for spec in room_specs}) != len(room_specs):
        raise ValueError("The world builder declares duplicate room names")

    residents = _resident_count(_parse(world_root / "resident_data.py"))
    callings = _mapping_keys(_parse(world_root / "callings.py"), "CALLINGS")
    selected_rumors = _seed_ids(_parse(world_root / "rumors.py"))
    seeds_file = root / "files/rumor-seeds-v0.1.md"
    corpus_ids = {
        int(number)
        for number in re.findall(r"^\*\*(\d+)\.\*\*", seeds_file.read_text(encoding="utf-8"), flags=re.M)
    }
    missing = sorted(set(selected_rumors) - corpus_ids)
    if missing:
        raise ValueError(f"Play-selected rumor IDs are missing from the source bank: {missing}")

    by_side = {side: sum(room["side"] == side and room["place"] != "offstage"
                         for room in room_specs) for side in ("ic", "ooc")}
    offstage = sum(room["place"] == "offstage" for room in room_specs)

    return {
        "schema": "fvillage.static_content_inventory.v1",
        "evidence_scope": "source declarations and world-builder references; no running game or agent playtest",
        "rooms": {"ic_walkable_declared": by_side["ic"],
                  "ooc_walkable_declared": by_side["ooc"],
                  "offstage_declared": offstage,
                  "authored": room_specs,
                  "note": "account-owned private rooms are created dynamically and not counted"},
        "resident_definitions": residents,
        "calling_definitions": {"count": len(callings), "ids": callings,
                                "note": "a profession identity is not a verified playable job"},
        "rumors": {"accepted_corpus_ids": len(corpus_ids),
                   "selected_for_bootstrap": len(selected_rumors),
                   "bootstrap_seed_ids": selected_rumors,
                   "seed_function_called": "seed_playable_rumors" in bootstrap_calls,
                   "note": "runtime may add user/event rumors; manuscript seeds are not all active"},
        "categories": categories,
        "full_launch_reference_targets": FULL_LAUNCH_TARGETS,
        "quality_checks_unverified": [
            "uncoached_AI_or_human_discovery", "completion_of_all_declared_cases",
            "meaningful_return_after_1_day_1_week_6_months", "live_host_recovery",
            "real_concurrent_multiplayer_soak",
        ],
    }


def to_markdown(data: dict) -> str:
    rooms, rumors = data["rooms"], data["rumors"]
    lines = [
        "# Static gameplay inventory",
        "",
        "Generated from source declarations only. These counts are not proof of",
        "discoverability, completion, sustained enjoyment, or public-host readiness.",
        "",
        "| Definition class | Count | Bootstrap initializer | Full-launch target |",
        "| --- | ---: | --- | ---: |",
    ]
    lines.append(f"| In-character built rooms | {rooms['ic_walkable_declared']} | builder | n/a |")
    lines.append(f"| Out-of-character built rooms | {rooms['ooc_walkable_declared']} | builder | n/a |")
    lines.append(f"| Offstage, inaccessible room | {rooms['offstage_declared']} | builder | n/a |")
    lines.append(f"| Defined residents | {data['resident_definitions']} | population | n/a |")
    lines.append(f"| Calling identities | {data['calling_definitions']['count']} | other systems | n/a |")
    lines.append(f"| Canon rumor manuscript entries | {rumors['accepted_corpus_ids']} | source only | 250 |")
    lines.append(f"| Selected initial canon rumors | {rumors['selected_for_bootstrap']} | {rumors['seed_function_called']} | n/a |")
    for name, entry in data["categories"].items():
        target = data["full_launch_reference_targets"].get(name, "n/a")
        lines.append(f"| {name.replace('_', ' ')} | {entry['count']} | {entry['bootstrap_initialization_called']} | {target} |")
    lines.extend([
        "", "## Evidence boundary", "",
        "Bootstrap initializer = a reference in the world builder, not proof that",
        "the player can reach, resolve, replay, or meaningfully experience every definition.",
        "Run independent scripted and uncoached playthroughs before claiming coverage.",
        "", "The full-launch targets in files/frankenstein-village-quest-handoff-v0.3.md",
        "section 7 remain authoritative. Invited-alpha scope is separately gated.",
    ])
    return "\n".join(lines) + "\n"


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--format", choices=("json", "markdown"), default="markdown")
    args = parser.parse_args()
    inventory = build_inventory()
    if args.format == "json":
        print(json.dumps(inventory, indent=2, sort_keys=True))
    else:
        print(to_markdown(inventory), end="")


if __name__ == "__main__":
    main()
