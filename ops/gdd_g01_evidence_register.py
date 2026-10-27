#!/usr/bin/env python3
"""FV-G01 evidence-card export for 21 GDD families, 10 Callings and 45 pairs.

This module indexes the existing AST audits. It never loads Evennia or treats
source declarations, class registration, a GDD design label or scripts as
evidence of real player discovery, state change, restart survival or enjoyment.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from content_inventory import REGISTRIES, build_inventory
from game_completion_audit import build_audit
from gdd_g01_ci_observations import load_ci_observations
from phase_a_calling_source_audit import audit as audit_calling_sources

ROOT = Path(__file__).resolve().parents[1]
# Relevant source-entrypoints or manuscripts for otherwise uncounted GDD families.
# These are navigation hints, NOT proof a content family has implementation,
# a working location or anything close to its full authoring quota.
FAMILY_REFERENCE_HINTS = {
    "newcomer_scenarios": "spike/fvillage/world/first_evening.py",
    "small_mysteries": "spike/fvillage/world/public_mysteries.py",
    "major_mystery_chains": "spike/fvillage/world/private_mysteries.py",
    "civic_quests": "spike/fvillage/world/civic_commissions.py",
    "authored_quests_per_calling": "spike/fvillage/world/calling_opportunities.py",
    "repeatable_jobs_per_calling": "spike/fvillage/world/calling_opportunities.py",
    "faction_quests_per_faction": "files/quest-generation-packet-v0.1.md",
    "cross_faction_conflicts": "files/quest-generation-packet-v0.1.md",
    "expedition_locations": "spike/fvillage/world/build_spike.py",
    "social_expeditions": "files/quest-generation-packet-v0.1.md",
    "group_investigations": "spike/fvillage/world/public_mysteries.py",
    "community_projects": "spike/fvillage/world/civic_commissions.py",
    "hidden_discoveries": "spike/fvillage/world/discoveries.py",
    "npc_arcs_per_major_npc": "spike/fvillage/world/resident_life.py",
    "ambient_room_events": "files/ambient-events-v0.1.md",
    "harbinger_templates": "spike/fvillage/world/harbinger_content.py",
    "player_request_templates": "files/quest-generation-packet-v0.1.md",
}

PROOF_FIELDS = (
    "ordinary_player_command", "observed_room", "distinct_role_decisions",
    "signed_world_transition", "finite_resource_or_time",
    "independent_account", "negative_or_absent_state",
    "real_restart", "uncoached_ux",
)


def empty_proof() -> dict:
    return {name: None for name in PROOF_FIELDS}


def build_register(root: Path = ROOT, *, source_ref: str | None = None) -> dict:
    """Return actionable, source-indexed G01 cards without false acceptance."""
    inventory = build_inventory(root)
    family_rows = build_audit(inventory, source_ref=source_ref)["categories"]
    owner_audit = audit_calling_sources(root, source_ref=source_ref)
    pairs = json.loads((root / "ops/MASTER_GDD_45_EDGE_REGISTER_2026-10-25.json")
                       .read_text(encoding="utf-8"))["edges"]
    if (len(family_rows), len(owner_audit["roles"]), len(pairs)) != (21, 10, 45):
        raise ValueError("FV-G01 design/source register dimensions changed")

    family_cards = []
    for row in family_rows:
        locator = row["measurement"]
        if locator in REGISTRIES:
            source_path = inventory["categories"][locator]["source"]
            initialized_in_source = inventory["categories"][locator]["bootstrap_initialization_called"]
        elif row["key"] == "rumor_seeds":
            source_path = "files/rumor-seeds-v0.1.md"
            initialized_in_source = inventory["rumors"]["seed_function_called"]
        else:
            source_path, initialized_in_source = None, None
        reference = FAMILY_REFERENCE_HINTS.get(row["key"], source_path)
        if reference is None or not (root / reference).is_file():
            raise ValueError("Missing source reference for GDD family " + row["key"])
        family_cards.append({
            "id": "GDD-FAMILY-" + row["key"],
            "content_family": row["label"],
            "minimum_target": row["minimum_target"],
            "declared_count": row["declared_count"],
            "source_path": source_path,
            "candidate_source_or_manuscript": reference,
            "candidate_source_scope": "reference_only_no_family_quota_claim",
            "bootstrap_reference_in_source": initialized_in_source,
            "status": "static_source_only" if source_path else "unmeasured",
            "evidence": empty_proof(),
            "verified_complete": False,
        })

    calling_cards = []
    for name, role in owner_audit["roles"].items():
        examples = []
        for entry in role["existing_entrypoint_examples"]:
            examples.append({
                "verb": entry["command_key"],
                "command_class": entry["command_class"],
                "command_source": entry["command_source"],
                "world_owner": entry["world_source"],
                "level": "registered_source_candidate_not_playtested",
            })
        calling_cards.append({
            "calling": name,
            "registered_command_candidates": examples,
            "workplace_room": None,
            "counted_distinct_jobs": None,
            "counted_authored_quests": None,
            "evidence": empty_proof(),
            "verified_complete": False,
        })

    calling_index = {c["calling"]: c for c in calling_cards}
    ci_observations = load_ci_observations(root)
    edges = []
    for design_edge, source_edge in zip(pairs, owner_audit["edges"]):
        if (design_edge["id"], design_edge["calling_a"], design_edge["calling_b"]) != (
            source_edge["id"], source_edge["calling_a"], source_edge["calling_b"]
        ):
            raise ValueError("Source-owner audit and Master GDD edges disagree")
        a, b = design_edge["calling_a"].lower(), design_edge["calling_b"].lower()
        if a not in calling_index or b not in calling_index:
            raise ValueError("GDD edge refers to an unregistered Calling")
        edges.append({
            "id": design_edge["id"],
            "number": design_edge["number"],
            "callings": [design_edge["calling_a"], design_edge["calling_b"]],
            "baseline_class": design_edge["baseline_class"],
            "design_contract": design_edge["design_contract"],
            "static_pair_world_owner_examples": source_edge["static_source_examples"],
            "candidate_verbs_not_pair_proof": {
                a: [cmd["verb"] for cmd in calling_index[a]["registered_command_candidates"]],
                b: [cmd["verb"] for cmd in calling_index[b]["registered_command_candidates"]],
            },
            "verified_pair_command": None,
            "verified_pair_room": None,
            "historical_ci_observation": ci_observations.get(design_edge["number"]),
            "evidence": empty_proof(),
            "verified_complete": False,
        })
    if [edge["number"] for edge in edges] != list(range(1, 46)):
        raise ValueError("GDD 45-pair order invalid")
    for card in calling_cards:
        name = card["calling"]
        card["partial_real_client_case_references"] = [
            {
                "edge": edge["id"],
                "ci_run": edge["historical_ci_observation"]["ci_run_url"],
                "reported_shared_location": edge["historical_ci_observation"]["observed_room"],
                "scope": "shared_scenario_example_not_independent_Calling_job_signoff",
            }
            for edge in edges
            if edge["historical_ci_observation"]
            and name in [role.lower() for role in edge["callings"]]
        ]
    return {
        "schema": "fvillage.gdd_g01_evidence_register.v1",
        "source_ref": source_ref,
        "source_registers": [
            "ops/MASTER_GDD_45_EDGE_REGISTER_2026-10-25.json",
            "ops/phase_a_calling_source_audit.py",
            "ops/content_inventory.py",
        ],
        "scope": "static source-indexed candidates, no player or restart verification",
        "live_game_session_executed": False,
        "source_declared_room_names_not_visited": [
            room["name"] for room in inventory["rooms"]["authored"]
            if room["side"] == "ic" and room["place"] != "offstage"
        ],
        "families": family_cards,
        "callings": calling_cards,
        "edges": edges,
        "verified_family_count": 0,
        "verified_calling_count": 0,
        "verified_edge_count": 0,
        "partial_ci_edge_count": len(ci_observations),
        "package_complete": False,
        "next_evidence": [
            "Record ordinary-client commands, actual rooms and attributable signed state transitions.",
            "Record conservation/permissions, independent second-account view and negative outcomes.",
            "Record genuine server restart and uncoached comprehension for qualified playable content.",
        ],
    }


def to_markdown(register: dict) -> str:
    out = [
        "# FV-G01: Executable-coverage evidence cards",
        "",
        f"Source checkout: {register['source_ref'] or 'unspecified'}.",
        "All source owner references are static. Null evidence means UNVERIFIED.",
        "No registered command, declared room, V/S/D/C baseline or manuscript",
        "count certifies world-state mutation, persistence or player enjoyment.",
        "", "## Twenty-one GDD content families", "",
        "| Family | Source file | Definitions | Gameplay evidence |",
        "| --- | --- | ---: | --- |",
    ]
    for card in register["families"]:
        hint = card["candidate_source_or_manuscript"]
        reference = card["source_path"] or (hint + " (candidate only)")
        out.append(f"| {card['content_family']} | {reference} | "
                   f"{card['declared_count'] if card['declared_count'] is not None else '?'} | UNVERIFIED |")
    out.extend(["", "## Ten Calling source entrypoints", "",
                "| Calling | Candidate verbs | Command/world owner sources | Room, restart and UX |",
                "| --- | --- | --- | --- |"])
    for card in register["callings"]:
        entries = card["registered_command_candidates"]
        commands = ", ".join(e["verb"] for e in entries)
        owners = ", ".join(sorted({e["world_owner"]["path"] for e in entries}))
        observed = len(card["partial_real_client_case_references"])
        role_status = (f"{observed} partial shared CI examples; full UX UNVERIFIED"
                       if observed else "UNVERIFIED")
        out.append(f"| {card['calling']} | {commands} | {owners} | {role_status} |")
    out.extend(["", "## Forty-five Calling collaboration contracts", "",
                "| Edge | Pair | Static pair-specific world owner | Actual pair evidence |",
                "| --- | --- | --- | --- |"])
    for edge in register["edges"]:
        sources = "; ".join(
            f"{x['path']}:{x['line']} ({x['name']})"
            for x in edge["static_pair_world_owner_examples"]
        ) or "unverified"
        status = ("Partial scripted real-client and restart evidence; full "
                  "acceptance UNVERIFIED" if edge["historical_ci_observation"]
                  else "UNVERIFIED")
        out.append(f"| {edge['number']:02} | {' + '.join(edge['callings'])} | "
                   f"{sources} | {status} |")
    # Render observations from validated, pinned receipts rather than a
    # hard-coded run/count that can become stale as the ledger evolves.
    partial = [edge for edge in register["edges"]
               if edge["historical_ci_observation"]]
    out.extend(["", "## Pinned normal-client and restart observations", "",
                "These are historical scripted observations, not full Calling signoffs.",
                "| Edge | Commands actually scripted | Observed room | Signed transition / limitations | Run |",
                "| --- | --- | --- | --- | --- |"])
    for edge in partial:
        receipt = edge["historical_ci_observation"]
        commands = ", ".join("`" + cmd.replace("|", "/") + "`"
                             for cmd in receipt["client_commands"])
        room = receipt["observed_room"].replace("|", "/")
        transition = receipt["observed_transition"].replace("|", "/")
        out.append(
            f"| {edge['number']:02} | {commands} | {room} | {transition} | "
            f"[CI]({receipt['ci_run_url']}) |"
        )
        out.append(
            f"| | Remaining: | | {receipt['remaining_gaps'].replace('|', '/')} | "
            f"[Restart source]({receipt['ci_run_url']}) |"
        )
    out.extend([
        "", "## Real-client evidence, bounded",
        f"Source-checked historical CI cases: {len(partial)} of 45. "
        "No edge is fully accepted; uncoached UX is UNVERIFIED.",
        "Actual receipt IDs and source-commit hashes are in the JSON cards.",
        "Historical CI is not a passing result for the latest checkout.",
        "",
        "## Required to advance evidence", "",
        "Obtain normal account commands and real observed rooms, distinct role",
        "decisions, signed world transitions, finite resources, second-account",
        "visibility, negative/late states, genuine restart, and uncoached UX",
        "with exact sources. Do not infer these from class registration.",
        "",
    ])
    return "\n".join(out)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--format", choices=("json", "markdown"), default="markdown")
    parser.add_argument("--source-ref", default=None)
    options = parser.parse_args()
    register = build_register(source_ref=options.source_ref)
    output = (json.dumps(register, indent=2, sort_keys=True)
              if options.format == "json" else to_markdown(register))
    print(output, end="\n")


if __name__ == "__main__":
    main()
