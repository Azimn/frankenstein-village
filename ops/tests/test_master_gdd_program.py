"""Structural checks for PDF-derived master GDD and game-completion workboard.

Documentation assertions only: they never certify that gameplay is implemented
or the PDF's proposed rules have been approved by the World Bible.
"""
import json
import re
import unittest
from pathlib import Path

ROOT=Path(__file__).resolve().parents[2]
GDD=ROOT/"docs/FRANKENSTEIN_VILLAGE_MASTER_GDD_REVIEW_2026-10-25.md"
PLAN=ROOT/"ops/MASTER_GDD_GAME_COMPLETION_PROGRAM_2026-10-25.md"
DATA=ROOT/"ops/MASTER_GDD_GAME_COMPLETION_PROGRAM_2026-10-25.json"

class MasterGDDProgramTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.gdd=GDD.read_text(encoding="utf-8")
        cls.plan=PLAN.read_text(encoding="utf-8")
        cls.data=json.loads(DATA.read_text(encoding="utf-8"))

    def test_all_31_source_pages_are_preserved_in_order(self):
        labels=[int(x) for x in re.findall(r'<!-- Source PDF physical page (\d+) of 31 -->',self.gdd)]
        self.assertEqual(labels,list(range(1,32)))
        self.assertIn('eaae1b0139de8453a74116b463ada8eacc93822010a665dbfb7976034524b567',self.gdd)

    def test_master_sections_and_appendices_present(self):
        for item in ("8. The ten Callings", "9. The complete interdependence graph",
                     "10. All 45 pairwise collaboration contracts",
                     "15. Narrative, content and authoring inventory",
                     "19. QA strategy and acceptance matrix",
                     "21. Production roadmap and dependency-managed slices",
                     "22. Shipping policy and readiness gates",
                     "Appendix A. Professional job/quest production card",
                     "Appendix C. Release decision record"):
            with self.subTest(item=item):
                self.assertIn(item,self.gdd)

    def test_full_gdd_45_edge_review_stats_are_preserved(self):
        self.assertIn("V=6; S=6; D=24; C=9",self.gdd)
        self.assertIn("V3 = Innkeep",self.gdd)
        self.assertIn("V4 = Innkeep",self.gdd)

    def test_work_packages_are_valid_acyclic_dag(self):
        work=self.data["work_packages"]
        self.assertEqual(len(work),14)
        ids=[x["id"] for x in work]
        self.assertEqual(len(ids),len(set(ids)))
        statuses={x["status"] for x in work}
        self.assertTrue(statuses <= {"planned", "in_progress", "verified"})
        self.assertEqual(len(work),14)
        parents={x["id"]:x["depends"] for x in work}
        indexed={x["id"]:x for x in work}
        for package in work:
            status=package["status"]
            evidence=package["verified_evidence"]
            self.assertIsInstance(evidence,list)
            if status=="planned":
                self.assertEqual(evidence,[],package["id"])
            if status=="verified":
                self.assertTrue(evidence,"Verified package needs recorded proof")
                self.assertTrue(
                    all(indexed[parent]["status"]=="verified"
                        for parent in package["depends"]),
                    "Verified package requires verified dependencies",
                )
                if package["id"]=="FV-G00":
                    for prefix in ("main_sha:", "main_ci:", "review:"):
                        self.assertTrue(
                            any(isinstance(item,str) and item.startswith(prefix)
                                for item in evidence),
                            "FV-G00 lacks "+prefix+" acceptance proof",
                        )
        for k,prereqs in parents.items():
            self.assertNotIn(k,prereqs)
            self.assertTrue(all(x in parents for x in prereqs))
        def visit(node,stack):
            self.assertNotIn(node,stack,"cycle "+node)
            for req in parents[node]:
                visit(req,stack | {node})
        for k in parents:
            visit(k,set())

    def test_gdd_content_contract_kept_full_scope(self):
        for string in ("60 minimum","80–120 distinct loops","75+","30","10","250+",
                       "45 pairwise","T-01","T-16"):
            with self.subTest(string=string):
                self.assertIn(string,self.plan)

    def test_source_pair_register_has_all_45_with_evidence_unverified(self):
        register=json.loads(
            (ROOT/"ops/MASTER_GDD_45_EDGE_REGISTER_2026-10-25.json").read_text(encoding="utf-8")
        )
        edges=register["edges"]
        self.assertEqual(len(edges),45)
        self.assertEqual([e["number"] for e in edges],list(range(1,46)))
        self.assertEqual(register["baselines"],{"V":6,"S":6,"D":24,"C":9})
        unique={(e["calling_a"],e["calling_b"]) for e in edges}
        self.assertEqual(len(unique),45)
        self.assertEqual((edges[2]["calling_a"],edges[2]["calling_b"],edges[2]["baseline_class"]),
                         ("Innkeep","Healer","V"))
        self.assertEqual((edges[3]["calling_a"],edges[3]["calling_b"],edges[3]["baseline_class"]),
                         ("Innkeep","Merchant","V"))
        for edge in edges:
            self.assertFalse(edge["verified_complete"])
            # A draft can contain traceable candidate evidence without being
            # accepted. Never mistake a PR path or CI marker for main proof.
            for field in (
                "ordinary_player_discovery_proof", "two_account_test",
                "post_restart_test",
            ):
                value = edge[field]
                if value is not None:
                    self.assertIsInstance(value, str)
                    self.assertTrue(value.startswith("candidate:"), (edge["id"], field))
            self.assertIsNone(edge["uncoached_gameplay_evidence"])
            self.assertGreater(len(edge["design_contract"]),60)

    def test_does_not_claim_implementation_or_canon_approval(self):
        self.assertIn("REVIEW DRAFT",self.gdd)
        self.assertIn("Do not describe this file as a lossless PDF",self.gdd)
        self.assertIn("Mystic B1",self.plan)
        self.assertTrue(any("Mystic keeper B1" in x for x in self.data["warnings"]))
        self.assertTrue(all(x["verified_evidence"]==[] for x in self.data["work_packages"]
                            if x["status"]=="planned"))
        self.assertIn("separate",self.plan.lower())
        self.assertIn("No new repository",self.plan)

if __name__=="__main__":
    unittest.main()
