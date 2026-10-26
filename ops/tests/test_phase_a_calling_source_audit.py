"""Static Calling source-owner evidence: not a simulated playtest."""
import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "ops"))

from phase_a_calling_source_audit import (  # noqa: E402
    ANCHORS, V_OWNERS, audit, markdown,
)

class PhaseACallingAuditTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.result = audit(ROOT, source_ref="test-source")

    def test_all_ten_callings_use_real_registered_commands_and_world_functions(self):
        result = self.result
        self.assertEqual(len(result["roles"]), 10)
        self.assertEqual(set(result["roles"]), set(ANCHORS))
        self.assertTrue(all(role["existing_entrypoint_examples"]
                            for role in result["roles"].values()))
        for role, item in result["roles"].items():
            for entry in item["existing_entrypoint_examples"]:
                with self.subTest(role=role, key=entry["command_key"]):
                    self.assertEqual(entry["proof_level"], "static_class_and_source_function")
                    self.assertGreater(entry["command_source"]["line"], 0)
                    self.assertGreater(entry["world_source"]["line"], 0)
                    self.assertTrue((ROOT / entry["command_source"]["path"]).exists())
                    self.assertTrue((ROOT / entry["world_source"]["path"]).exists())

    def test_final_pdf_all_45_pair_ids_preserved_and_all_claims_unverified(self):
        result = self.result
        edges = result["edges"]
        self.assertEqual([p["number"] for p in edges], list(range(1, 46)))
        self.assertEqual(
            {c: sum(e["gdd_baseline"] == c for e in edges) for c in "VSDC"},
            {"V": 6, "S": 6, "D": 24, "C": 9}
        )
        for edge in edges:
            self.assertFalse(edge["gameplay_complete"])
            self.assertIsNone(edge["world_transition_evidence"])
            self.assertIsNone(edge["two_account_evidence"])
            self.assertIsNone(edge["uncoached_quality_evidence"])
        self.assertFalse(result["live_world_executed"])

    def test_V3_and_V4_use_correct_master_GDD_pairs(self):
        edges = self.result["edges"]
        self.assertEqual([edges[2]["calling_a"], edges[2]["calling_b"]],
                         ["Innkeep", "Healer"])
        self.assertEqual([edges[3]["calling_a"], edges[3]["calling_b"]],
                         ["Innkeep", "Merchant"])
        self.assertEqual(set(V_OWNERS), {3, 4, 10, 11, 12, 19})
        for pair in edges:
            self.assertEqual(bool(pair["static_source_examples"]),
                             pair["number"] in V_OWNERS)

    def test_hound_and_wanderer_shared_route_is_not_two_finished_jobs(self):
        roles = self.result["roles"]
        for name in ("hound", "wanderer"):
            paths = [e["world_source"]["path"] for e in roles[name]["existing_entrypoint_examples"]]
            self.assertIn("spike/fvillage/world/route_work.py", paths)
        self.assertIsNone(roles["hound"]["distinct_jobs_verified"])
        self.assertIsNone(roles["wanderer"]["distinct_jobs_verified"])
        self.assertIn("GDD 8.9", markdown(self.result))

    def test_source_drift_fails_closed_instead_of_inventing_progress(self):
        import shutil
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            repo = ROOT
            import os
            for item in ("ops/MASTER_GDD_45_EDGE_REGISTER_2026-10-25.json",
                         "spike/fvillage/commands/default_cmdsets.py"):
                destination = root / item
                destination.parent.mkdir(parents=True, exist_ok=True)
                shutil.copyfile(repo / item, destination)
            # On an intentionally incomplete source checkout, never issue a
            # status report claiming a verified implementation.
            with self.assertRaises((OSError, ValueError)):
                audit(root)

if __name__ == "__main__":
    unittest.main()
