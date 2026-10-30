"""Tests for honest full-game content coverage accounting."""
from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "ops"))

from content_inventory import build_inventory  # noqa: E402
from game_completion_audit import TARGETS, CALLING_FIELDS, build_audit, to_markdown  # noqa: E402
from gdd_g01_evidence_register import (  # noqa: E402
    PROOF_FIELDS, COVERAGE_FIELDS, build_register, to_markdown as g01_markdown,
)
from gdd_g01_ci_observations import (  # noqa: E402
    load_ci_observations, _call_nodes, _player_command, _printed_marker,
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
        self.assertTrue(evidence["coverage_index_complete"])
        self.assertEqual(evidence["package_gate"],
                         "index_built_pending_independent_review_and_main_integration")
        self.assertFalse(evidence["live_game_session_executed"])

    def test_g01_command_line_exports_reproducible_evidence_json(self):
        import subprocess
        process = subprocess.run(
            [sys.executable, str(ROOT / "ops/gdd_g01_evidence_register.py"),
             "--format", "json", "--source-ref", "ci-checked-head"],
            capture_output=True, text=True, check=True, timeout=30,
            cwd=ROOT,
        )
        cards = json.loads(process.stdout)
        self.assertEqual(cards["source_ref"], "ci-checked-head")
        self.assertEqual(len(cards["families"]), 21)
        self.assertEqual(len(cards["callings"]), 10)
        self.assertEqual(len(cards["edges"]), 45)
        self.assertFalse(cards["live_game_session_executed"])
        self.assertFalse(cards["package_complete"])
        self.assertTrue(cards["coverage_index_complete"])

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

    def test_g01_every_card_has_explicit_evidence_contract(self):
        cards = build_register(ROOT, source_ref="coverage-fixture")
        self.assertTrue(cards["coverage_index_complete"])
        self.assertEqual(
            sum(len(cards[group]) for group in ("families", "callings", "edges")),
            76,
        )
        for group in ("families", "callings", "edges"):
            for card in cards[group]:
                with self.subTest(group=group, id=card.get("id", card.get("calling"))):
                    cover = card["coverage"]
                    self.assertEqual(
                        set(cover), set(COVERAGE_FIELDS) | {"proof_level", "unknown_fields"}
                    )
                    self.assertTrue(cover["source_file"])
                    self.assertEqual(
                        set(cover["unknown_fields"]),
                        {key for key in COVERAGE_FIELDS if cover[key] is None},
                    )
                    self.assertIsNone(cover["uncoached_ux"])
                    self.assertFalse(card["verified_complete"])
                    if group in ("callings", "edges"):
                        self.assertTrue(cover["world_owner"])
        partial = [e for e in cards["edges"]
                   if e["coverage"]["proof_level"].startswith("historical")]
        self.assertEqual({e["number"] for e in partial},
                         {3, 4, 6, 10, 12, 19, 38})
        for edge in partial:
            cover = edge["coverage"]
            self.assertTrue(cover["player_command"])
            self.assertTrue(cover["room"])
            self.assertTrue(cover["signed_transition"])
            self.assertTrue(cover["restart_proof"]["marker"])
            self.assertIsNone(cover["uncoached_ux"])
        for edge in cards["edges"]:
            if edge not in partial:
                self.assertIsNone(edge["coverage"]["signed_transition"])
                self.assertIsNone(edge["coverage"]["restart_proof"])

    def test_g01_real_client_restart_ci_receipts_are_bounded(self):
        source = load_ci_observations(ROOT)
        self.assertEqual(set(source), {3, 4, 6, 10, 12, 19, 38})
        evidence = build_register(ROOT)
        self.assertEqual(evidence["partial_ci_edge_count"], 7)
        self.assertEqual(evidence["verified_edge_count"], 0)
        self.assertFalse(evidence["package_complete"])
        for edge in evidence["edges"]:
            receipt = edge["historical_ci_observation"]
            if edge["number"] in source:
                self.assertIsNotNone(receipt)
                self.assertEqual(receipt["observed_on_commit"],
                                 "f1ada1cb9b1e640d2ed839063a6b10ceba47f9a5")
                self.assertIn("/runs/40455328096", receipt["ci_run_url"])
                self.assertTrue(receipt["remaining_gaps"])
                self.assertTrue(receipt["client_commands"])
                self.assertIn("partial_not_accepted", receipt["proof_level"])
            else:
                self.assertIsNone(receipt)
            self.assertFalse(edge["verified_complete"])
            self.assertTrue(all(value is None for value in edge["evidence"].values()))

    def test_g01_markdown_cites_pinned_cases_and_never_hardcodes_run_count(self):
        import copy

        evidence = build_register(ROOT)
        report = g01_markdown(evidence)
        self.assertIn("Pinned normal-client and restart observations", report)
        self.assertIn("Explicit G01 coverage fields for every pair", report)
        self.assertIn("HISTORICAL means a source-pinned scripted CI observation", report)
        self.assertIn("| 38 |", report)
        self.assertIn("UNVERIFIED |", report)
        self.assertIn("Coverage index COMPLETE", report)
        self.assertIn("Source-checked historical CI cases: 7 of 45", report)
        self.assertIn("`care serve Silas Crowe`", report)
        self.assertIn("`survey passability`", report)
        self.assertIn("Northern Treeline", report)
        self.assertIn("No edge is fully accepted; uncoached UX is UNVERIFIED", report)
        self.assertEqual(report.count(
            "[CI](https://github.com/Azimn/frankenstein-village/actions/runs/40455328096)"
        ), 7)

        # The human-readable report must come from the validated card values,
        # not a fixed historic CI URL or fixed number of documented cases.
        alternate = copy.deepcopy(evidence)
        alternate["edges"][2]["historical_ci_observation"]["observed_room"] = "Test-only distinct room"
        alternate["edges"][2]["historical_ci_observation"]["ci_run_url"] = (
            "https://github.com/Azimn/frankenstein-village/actions/runs/999"
        )
        changed = g01_markdown(alternate)
        self.assertIn("Test-only distinct room", changed)
        self.assertIn("[CI](https://github.com/Azimn/frankenstein-village/actions/runs/999)", changed)
        empty = copy.deepcopy(evidence)
        for edge in empty["edges"]:
            edge["historical_ci_observation"] = None
        empty_report = g01_markdown(empty)
        self.assertIn("Source-checked historical CI cases: 0 of 45", empty_report)
        self.assertNotIn("/runs/40455328096", empty_report)

    def test_g01_ci_marker_source_drift_fails_closed(self):
        import shutil
        with tempfile.TemporaryDirectory(prefix="g01-source-drift-") as tmp:
            sandbox = Path(tmp)
            for rel in (
                "ops/GDD_G01_CI_OBSERVATIONS_2026-10-27.json",
                "spike/tests/run_all.py",
                "spike/tests/telnet_playthrough.py",
                "spike/tests/post_restart_assertions.py",
            ):
                dest = sandbox / rel
                dest.parent.mkdir(parents=True, exist_ok=True)
                shutil.copyfile(ROOT / rel, dest)
            self.assertEqual(len(load_ci_observations(sandbox)), 7)
            telnet = sandbox / "spike/tests/telnet_playthrough.py"
            changed = telnet.read_text(encoding="utf-8").replace(
                'print("TELNET_TWO_ACCOUNT_PHYSICAL_MARKET_WORKSHOP_GREEN")',
                'print("STAGED_WORKSHOP_MARKER_NO_LONGER_MATCHES")',
            )
            telnet.write_text(changed, encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "CI source blob mismatch"):
                load_ci_observations(sandbox)

    def test_g01_commented_out_calls_and_markers_never_count_as_evidence(self):
        import shutil
        with tempfile.TemporaryDirectory(prefix="g01-ast-receipt-") as tmp:
            sandbox = Path(tmp)
            for rel in (
                "ops/GDD_G01_CI_OBSERVATIONS_2026-10-27.json",
                "spike/tests/run_all.py",
                "spike/tests/telnet_playthrough.py",
                "spike/tests/post_restart_assertions.py",
            ):
                dest = sandbox / rel
                dest.parent.mkdir(parents=True, exist_ok=True)
                shutil.copyfile(ROOT / rel, dest)
            self.assertEqual(len(load_ci_observations(sandbox)), 7)
            telnet = sandbox / "spike/tests/telnet_playthrough.py"
            original = telnet.read_text(encoding="utf-8")
            muted_commands = original.replace(
                'out = smith.command("workshop forge")',
                'out = ""  # smith.command("workshop forge")',
            )
            self.assertNotEqual(original, muted_commands)
            telnet.write_text(muted_commands, encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "CI source blob mismatch"):
                load_ci_observations(sandbox)
            muted_marker = original.replace(
                'print("TELNET_TWO_ACCOUNT_PHYSICAL_MARKET_WORKSHOP_GREEN")',
                '# print("TELNET_TWO_ACCOUNT_PHYSICAL_MARKET_WORKSHOP_GREEN")',
            )
            self.assertNotEqual(original, muted_marker)
            telnet.write_text(muted_marker, encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "CI source blob mismatch"):
                load_ci_observations(sandbox)

    def test_g01_constant_dead_branches_do_not_validate_ci_receipts(self):
        import shutil
        with tempfile.TemporaryDirectory(prefix="g01-unreachable-") as tmp:
            sandbox = Path(tmp)
            for rel in (
                "ops/GDD_G01_CI_OBSERVATIONS_2026-10-27.json",
                "spike/tests/run_all.py",
                "spike/tests/telnet_playthrough.py",
                "spike/tests/post_restart_assertions.py",
            ):
                destination = sandbox / rel
                destination.parent.mkdir(parents=True, exist_ok=True)
                shutil.copyfile(ROOT / rel, destination)
            self.assertEqual(len(load_ci_observations(sandbox)), 7)
            telnet = sandbox / "spike/tests/telnet_playthrough.py"
            original = telnet.read_text(encoding="utf-8")
            # Matches the independent review's actual repro, preserving syntax
            # and line numbers while making workshop forge impossible to run.
            dead_commands = original.replace(
                'out = smith.command("workshop forge")',
                'out = "" if True else smith.command("workshop forge")',
            )
            self.assertNotEqual(original, dead_commands)
            telnet.write_text(dead_commands, encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "CI source blob mismatch"):
                load_ci_observations(sandbox)
            # The AST contains print(...), but Python cannot evaluate it.
            dead_marker = original.replace(
                'print("TELNET_TWO_ACCOUNT_PHYSICAL_MARKET_WORKSHOP_GREEN")',
                'False and print("TELNET_TWO_ACCOUNT_PHYSICAL_MARKET_WORKSHOP_GREEN")',
            )
            self.assertNotEqual(original, dead_marker)
            telnet.write_text(dead_marker, encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "CI source blob mismatch"):
                load_ci_observations(sandbox)

    def test_g01_ast_rejects_inert_calls_even_without_blob_pinning(self):
        with tempfile.TemporaryDirectory(prefix="g01-ast-only-") as tmp:
            source = Path(tmp) / "fake_commands.py"
            source.write_text(
                "def scenario():\n"
                "    out = '' if True else smith.command('workshop forge')\n"
                "    False and print('BAD_MARKER')\n"
                "    if False:\n"
                "        smith.command('another disabled command')\n"
                "    True or smith.command('short circuited')\n"
                "    0 and print('ZERO_DISABLED_MARKER')\n"
                "    out = '' if not 0 else smith.command('zero disabled')\n"
                "    smith.command('genuine command')\n"
                "    print('GOOD_MARKER')\n",
                encoding="utf-8",
            )
            calls = _call_nodes(source)
            self.assertFalse(any(_player_command(node, "workshop forge") for node in calls))
            self.assertFalse(any(_player_command(node, "another disabled command") for node in calls))
            self.assertFalse(any(_player_command(node, "short circuited") for node in calls))
            self.assertFalse(any(_player_command(node, "zero disabled") for node in calls))
            self.assertFalse(any(_printed_marker(node, "BAD_MARKER") for node in calls))
            self.assertFalse(any(_printed_marker(node, "ZERO_DISABLED_MARKER") for node in calls))
            self.assertTrue(any(_player_command(node, "genuine command") for node in calls))
            self.assertTrue(any(_printed_marker(node, "GOOD_MARKER") for node in calls))

    def test_g01_owner_cards_resolve_real_repo_files_without_claiming_gameplay(self):
        evidence = build_register(ROOT)
        for card in evidence["families"]:
            self.assertTrue((ROOT / card["candidate_source_or_manuscript"]).is_file())
            self.assertEqual(card["candidate_source_scope"],
                             "reference_only_no_family_quota_claim")
            if card["source_path"]:
                self.assertTrue((ROOT / card["source_path"]).is_file())
            else:
                self.assertIsNone(card["declared_count"])
                self.assertEqual(card["status"], "unmeasured")
        for calling in evidence["callings"]:
            self.assertTrue(calling["registered_command_candidates"])
            self.assertIsNone(calling["workplace_room"])
            for entry in calling["registered_command_candidates"]:
                self.assertTrue((ROOT / entry["command_source"]["path"]).is_file())
                self.assertTrue((ROOT / entry["world_owner"]["path"]).is_file())
                self.assertIn("not_playtested", entry["level"])
        partial_roles = {r["calling"] for r in evidence["callings"]
                         if r["partial_real_client_case_references"]}
        self.assertEqual(partial_roles,
                         {"innkeep", "healer", "merchant", "performer", "chronicler",
                          "smith", "wanderer", "hound"})
        self.assertFalse({"detective", "mystic"} & partial_roles)
        for role in evidence["callings"]:
            for example in role["partial_real_client_case_references"]:
                self.assertIn("/runs/40455328096", example["ci_run"])
                self.assertIn("not_independent_Calling_job_signoff", example["scope"])
        markdown = g01_markdown(evidence)
        self.assertIn("Twenty-one GDD content families", markdown)
        self.assertIn("Forty-five Calling collaboration contracts", markdown)
        self.assertIn("UNVERIFIED", markdown)
        self.assertIn("No registered command", markdown)


if __name__ == "__main__":
    unittest.main()
