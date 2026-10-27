"""Evidence-honesty and live repository source trace for GDD §19.4."""
import copy
import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "ops"))
from phase_a_negative_case_trace import validate, markdown  # noqa: E402

class GDDNegativeCaseTraceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.matrix = validate(ROOT)

    def test_all_sixteen_gdd_negative_cases_have_actual_source_anchors(self):
        rows = self.matrix["cases"]
        self.assertEqual([r["id"] for r in rows],
                         ["T-%02d" % i for i in range(1, 17)])
        self.assertTrue(all(row["source_evidence"] and row["open_gap"] for row in rows))
        self.assertEqual(set(r["assessment"] for r in rows), {"partial", "gap"})

    def test_source_only_evidence_is_never_a_gameplay_certificate(self):
        self.assertEqual(self.matrix["full_pass_count"], 0)
        for row in self.matrix["cases"]:
            self.assertFalse(row["exact_gdd_scenario_executed_end_to_end"])
            self.assertFalse(row["uncoached_player_verified"])
        text = markdown(self.matrix)
        self.assertIn("source inspection only", text)
        self.assertIn("T-07 Hound versus Wanderer", text)

    def test_missing_test_or_script_anchor_fails_closed(self):
        altered = copy.deepcopy(self.matrix)
        altered["cases"][0]["source_evidence"][0]["symbol"] = "test_not_a_real_test"
        with self.assertRaisesRegex(ValueError, "missing actual unit test"):
            validate(ROOT, altered)
        altered = copy.deepcopy(self.matrix)
        fixture = altered["cases"][2]["source_evidence"][0]
        fixture["symbol"] = "NOT_A_REAL_REPAIR_SENTINEL"
        with self.assertRaisesRegex(ValueError, "missing actual scripted fixture"):
            validate(ROOT, altered)

    def test_cannot_launder_partial_as_fully_verified(self):
        altered = copy.deepcopy(self.matrix)
        altered["full_pass_count"] = 16
        with self.assertRaisesRegex(ValueError, "cannot assert fully passing"):
            validate(ROOT, altered)
        altered = copy.deepcopy(self.matrix)
        altered["cases"][6]["exact_gdd_scenario_executed_end_to_end"] = True
        with self.assertRaisesRegex(ValueError, "unsupported completion"):
            validate(ROOT, altered)

    def test_gdd_privacy_and_exhaustion_gaps_remain_open(self):
        rows = {r["id"]: r for r in self.matrix["cases"]}
        for key in ("T-07", "T-08", "T-09", "T-13"):
            self.assertEqual(rows[key]["assessment"], "gap")
        self.assertIn("consent", rows["T-08"]["scenario"])
        self.assertIn("alternate relief", rows["T-09"]["canonical_invariant"])
        self.assertEqual(rows["T-14"]["assessment"], "partial")

if __name__ == "__main__":
    unittest.main()
