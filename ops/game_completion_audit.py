#!/usr/bin/env python3
"""Full-game 1.0 source-coverage audit, deliberately not a readiness certificate.

Maps the authoritative section 7 inventory targets to the existing conservative
static inventory. Missing measurement remains unknown, NEVER zero or complete.
Any declared content still requires runtime discoverability, outcome and restart
evidence. This module never imports Evennia or changes game state.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from content_inventory import build_inventory

# Lower bounds, transcribed from quest-handoff-v0.3.md section 7.
# "Per" requirements are not multiplied into presumed total implementations.
TARGETS = (
    ("newcomer_scenarios", "Newcomer scenarios", 12, None),
    ("small_mysteries", "Small mysteries", 30, None),
    ("major_mystery_chains", "Major mystery chains", 10, None),
    ("civic_quests", "Civic quests", 30, None),
    ("authored_quests_per_calling", "Authored quests per Calling", 6, None),
    ("repeatable_jobs_per_calling", "Repeatable jobs per Calling", 8, None),
    ("faction_quests_per_faction", "Faction quests per faction", 8, None),
    ("cross_faction_conflicts", "Cross-faction conflicts", 20, None),
    ("expedition_locations", "Expedition locations", 10, None),
    ("social_expeditions", "Social expeditions", 12, None),
    ("group_investigations", "Group investigations", 12, None),
    ("timed_incidents", "Timed incidents", 30, "timed_incident_definitions"),
    ("random_incidents", "Random incident templates", 75, "random_incident_definitions"),
    ("server_wide_events", "Server-wide event frameworks", 10, "server_event_definitions"),
    ("community_projects", "Community projects", 6, None),
    ("hidden_discoveries", "Hidden discoveries", 50, None),
    ("npc_arcs_per_major_npc", "Personal arcs per major NPC", 3, None),
    ("rumor_seeds", "Rumor seeds", 250, "rumors.accepted_corpus_ids"),
    ("ambient_room_events", "Ambient room events", 300, None),
    ("harbinger_templates", "Harbinger templates", 50, None),
    ("player_request_templates", "Player-request templates", 30, None),
)

CALLING_FIELDS = (
    "first_workplace", "distinct_renewable_jobs", "authored_quests",
    "finite_material_source", "physical_or_institutional_consequence",
    "social_handoff", "solo_route", "progression",
    "normal_client_discovery", "restart_and_return",
)


def _source_count(source: dict, locator: str | None) -> int | None:
    if locator is None:
        return None
    if locator == "rumors.accepted_corpus_ids":
        return int(source["rumors"]["accepted_corpus_ids"])
    return int(source["categories"][locator]["count"])


def build_audit(source: dict | None = None, *, source_ref: str | None = None) -> dict:
    source = build_inventory() if source is None else source
    categories = []
    for key, label, minimum, locator in TARGETS:
        count = _source_count(source, locator)
        # Source quantities are not a gameplay-completion metric.
        status = ("unmeasured" if count is None else
                  "source_below_target" if count < minimum else
                  "source_target_met_playability_unverified")
        categories.append({
            "key": key, "label": label, "minimum_target": minimum,
            "declared_count": count, "measurement": locator,
            "minimum_definition_gap": max(0, minimum - count) if count is not None else None,
            "source_status": status, "playability_verified": False,
            "evidence_needed": [
                "ordinary_player_discovery", "executed_world_state_change",
                "aftermath_or_repeatability", "real_restart",
            ],
        })
    professions = {
        role: {field: None for field in CALLING_FIELDS}
        for role in source["calling_definitions"]["ids"]
    }
    return {
        "schema": "fvillage.game_completion_audit.v1",
        "source_ref": source_ref,
        "reference": "files/frankenstein-village-quest-handoff-v0.3.md section 7",
        "evidence_scope": "static definitions only; runtime and player quality are unverified",
        "declared_ic_rooms": source["rooms"]["ic_walkable_declared"],
        "declared_residents": source["resident_definitions"],
        "professions": professions,
        "categories": categories,
        "game_complete": False,
        "not_measured": [
            "player_success", "player_fun", "verified_role_job_counts",
            "quest_completion", "balance", "long_session_quality",
            "defect_free_game", "genuine_voluntary_return",
        ],
    }


def to_markdown(audit: dict) -> str:
    source = audit["source_ref"] or "unknown (not supplied)"
    lines = [
        "# Frankenstein Village 1.0 content coverage",
        "", f"Source ref: {source}", "",
        "This is a **static source audit**, not a gameplay-completion or quality certificate.",
        "Unknown counts mean **unmeasured**, not zero. A source target reached still",
        "requires discovery, executable choices, signed consequences, aftermath",
        "and real-restart checks for the whole playable family.",
        "", "| Content family | §7 minimum | Source declarations | Source-only gap | Assessment |",
        "| --- | ---: | ---: | ---: | --- |",
    ]
    for row in audit["categories"]:
        count = "?" if row["declared_count"] is None else str(row["declared_count"])
        gap = "?" if row["minimum_definition_gap"] is None else str(row["minimum_definition_gap"])
        lines.append(
            f"| {row['label']} | {row['minimum_target']} | {count} | {gap} | {row['source_status']} |"
        )
    lines += [
        "", f"Declared walkable IC rooms: {audit['declared_ic_rooms']}.",
        f"Declared residents: {audit['declared_residents']}.",
        "", "## Calling completion evidence",
        "",
        "A registered Calling is **not** evidence of finished activities.",
        "For each Calling verify workplace, 6 authored quests, at least 8",
        "repeatable jobs, finite inputs, effects, cooperation, solo progress,",
        "advancement, discoverability and state after real restart.",
        "",
        "| Calling | Job count | Authored quests | Playable-complete |",
        "| --- | ---: | ---: | --- |",
    ]
    for role in audit["professions"]:
        lines.append(f"| {role} | unmeasured | unmeasured | unverified |")
    lines += [
        "", "## Actual next evidence",
        "",
        "1. Generate a per-Calling command-to-world-effect register with source locations.",
        "2. Execute representative solo, social, shortage and restart paths for each job.",
        "3. Audit every mystery/incident for discovery, choices, attribution and aftermath.",
        "4. Create work batches around playable professions, locations, and mysteries.",
        "5. Repeat scripted and uncoached gameplay after each batch; keep verified",
        "   coverage and player enjoyment separate.",
        "", "Host selection and deployment do not block the game-complete milestone.",
        "",
    ]
    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--format", choices=["markdown", "json"], default="markdown")
    parser.add_argument("--source-ref", default=None)
    opts = parser.parse_args()
    audit = build_audit(source_ref=opts.source_ref)
    print(json.dumps(audit, indent=2, sort_keys=True) if opts.format == "json"
          else to_markdown(audit), end="\n")


if __name__ == "__main__":
    main()
