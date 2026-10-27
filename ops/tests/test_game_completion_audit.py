"""Tests for honest full-game content coverage accounting."""
from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "ops"))

from content_inventory import build_inventory  # noqa: E402
from game_completion_audit import TARGETS, CALLING_FIELDS, build_audit, to_markdown  # noqa: E402
from gdd_g01_evidence_register import (  # noqa: E402
    PROOF_FIELDS, build_register, to_markdown as g01_markdown,
)


class CompletionAuditTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.source = build_inventory(ROOT)
        cls.audit = build_audit(cls.source, source_ref="test-main-source")

    def test_full_section_seven_target_categories_are_preserved(self):
        target_map = {key: minimum for key, _label, minimum, _src in TARGETS}
        self.assertEqual(len(TARGETS), 21)
        self.assertEqual(target_map["authored_quests_per_calling"], 6)
        self.assertEqual(target_map["repeatable_jobs_per_calling"], 8)
        self.assertEqual(target_map["major_mystery_chains"], 10)
        self.assertEqual(target_map["random_incidents"], 75)
        self.assertEqual(target_map["timed_incidents"], 30)
        self.assertEqual(target_map["server_wide_events"], 10)
        self.assertEqual(target_map["rumor_seeds"], 250)

    def test_unknown_is_unknown_not_an_unimplemented_zero(self):
        rows = {r["key"]: r for r in self.audit["categories"]}
        for key in ("small_mysteries", "repeatable_jobs_per_calling", "hidden_discoveries"):
            self.assertIsNone(rows[key]["declared_count"])
            self.assertIsNone(rows[key]["minimum_definition_gap"])
            self.assertEqual(rows[key]["source_status"], "unmeasured")
            self.assertFalse(rows[key]["playability_verified"])

    def test_counted_definitions_are_not_certified_gameplay(self):
        rows = {r["key"]: r for r in self.audit["categories"]}
        mapping = {
            "timed_incidents": "timed_incident_definitions",
            "random_incidents": "random_incident_definitions",
            "server_wide_events": "server_event_definitions",
        }
        for target, src in mapping.items():
            with self.subTest(target=target):
                self.assertEqual(rows[target]["declared_count"],
                                 self.source["categories"][src]["count"])
                self.assertFalse(rows[target]["playability_verified"])
        self.assertEqual(rows["rumor_seeds"]["declared_count"],
                         self.source["rumors"]["accepted_corpus_ids"])
        self.assertFalse(rows["rumor_seeds"]["playability_verified"])
        self.assertFalse(self.audit["game_complete"])

    def test_over_target_still_unverified(self):
        artificial = json.loads(json.dumps(self.source))
        artificial["categories"]["random_incident_definitions"]["count"] = 80
        rows = {r["key"]: r for r in build_audit(artificial)["categories"]}
        self.assertEqual(rows["random_incidents"]["minimum_definition_gap"], 0)
        self.assertEqual(rows["random_incidents"]["source_status"],
                         "source_target_met_playability_unverified")
        self.assertFalse(rows["random_incidents"]["playability_verified"])

    def test_professions_have_explicit_unverified_evidence_dimensions(self):
        professions = self.audit["professions"]
        self.assertEqual(len(professions), 10)
        for role, scorecard in professions.items():
            with self.subTest(role=role):
                self.assertEqual(set(scorecard), set(CALLING_FIELDS))
                self.assertTrue(all(v is None for v in scorecard.values()))

    def test_report_disclaims_readiness_and_missing_counts(self):
        report = to_markdown(self.audit)
        self.assertIn("not a gameplay-completion or quality certificate", report)
        self.assertIn("unmeasured", report)
        self.assertIn("not zero", report)
        self.assertIn("Host selection and deployment do not block", report)
        self.assertIn("test-main-source", report)
        self.assertIn("| detective | unmeasured", report)

    def test_log_static_counts_without_claiming_playable_success(self):
        rows = {r["key"]: r for r in self.audit["categories"]}
        counts = {
            "source_ref": self.audit["source_ref"],
            "ic_rooms": self.audit["declared_ic_rooms"],
            "residents": self.audit["declared_residents"],
            "callings": len(self.audit["professions"]),
            **{k: rows[k]["declared_count"] for k in
               ("random_incidents", "timed_incidents", "server_wide_events", "rumor_seeds")},
        }
        print("GAME_COMPLETION_AUDIT_SOURCE_COUNTS " + json.dumps(counts, sort_keys=True))
        self.assertFalse(self.audit["game_complete"])


    def test_g01_register_has_exact_21_10_45_card_set(self):
        evidence = build_register(ROOT, source_ref="explicit-fixture-commit")
        self.assertEqual(evidence["schema"], "fvillage.gdd_g01_evidence_register.v1")
        self.assertEqual((len(evidence["families"]), len(evidence["callings"]),
                          len(evidence["edges"])), (21, 10, 45))
        self.assertEqual([edge["number"] for edge in evidence["edges"]],
                         list(range(1, 46)))
        self.assertEqual({kind: sum(edge["baseline_class"] == kind
                                    for edge in evidence["edges"])
                          for kind in "VSDC"}, {"V": 6, "S": 6, "D": 24, "C": 9})
        self.assertEqual(evidence["source_ref"], "explicit-fixture-commit")
        self.assertFalse(evidence["package_complete"])
        self.assertFalse(evidence["live_game_session_executed"])

    def test_g01_verified_evidence_is_never_invented_from_source(self):
        evidence = build_register(ROOT, source_ref="unit-fixture")
        for category in ("families", "callings", "edges"):
            for card in evidence[category]:
                with self.subTest(category=category, identifier=card.get("id", card.get("calling"))):
                    self.assertFalse(card["verified_complete"])
                    self.assertEqual(set(card["evidence"]), set(PROOF_FIELDS))
                    self.assertTrue(all(v is None for v in card["evidence"].values()))
        for edge in evidence["edges"]:
            self.assertIsNone(edge["verified_pair_command"])
            self.assertIsNone(edge["verified_pair_room"])
        self.assertEqual([e["number"] for e in evidence["edges"]
                          if e["static_pair_world_owner_examples"]],
                         [3, 4, 10, 11, 12, 19])
        self.assertEqual((evidence["verified_family_count"],
                          evidence["verified_calling_count"],
                          evidence["verified_edge_count"]), (0, 0, 0))

    def test_g01_owner_cards_resolve_real_repo_files_without_claiming_gameplay(self):
        evidence = build_register(ROOT)
        for card in evidence["families"]:
            if card["source_path"]:
                self.assertTrue((ROOT / card["source_path"]).is_file())
        for calling in evidence["callings"]:
            self.assertTrue(calling["registered_command_candidates"])
            self.assertIsNone(calling["workplace_room"])
            for entry in calling["registered_command_candidates"]:
                self.assertTrue((ROOT / entry["command_source"]["path"]).is_file())
                self.assertTrue((ROOT / entry["world_owner"]["path"]).is_file())
                self.assertIn("not_playtested", entry["level"])
        markdown = g01_markdown(evidence)
        self.assertIn("21 content families", markdown.lower().replace("twenty-one", "21"))
        self.assertIn("Forty-five Calling collaboration contracts", markdown)
        self.assertIn("UNVERIFIED", markdown)
        self.assertNotIn("certifies world-state", markdown)


if __name__ == "__main__":
    unittest.main()
