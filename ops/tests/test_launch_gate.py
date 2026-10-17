import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from launch_gate import REQUIRED, assess


class LaunchGateTests(unittest.TestCase):
    def test_empty_is_no_go(self):
        result = assess({})
        self.assertEqual(result["decision"], "NO-GO")
        self.assertGreaterEqual(len(result["errors"]), len(REQUIRED))

    def test_unverified_evidence_is_no_go(self):
        sha = "a" * 40
        checks = {k: {"passed": True, "evidence_url": "https://example.org/evidence",
                      "verified_at": "2026-10-16", "sha": sha} for k in REQUIRED}
        checks["disposable_restore"]["passed"] = False
        self.assertEqual(assess({"deployed_sha": sha, "operator": "Test Operator",
                                 "checks": checks})["decision"], "NO-GO")

    def test_sha_mismatch_is_no_go(self):
        sha = "a" * 40
        checks = {k: {"passed": True, "evidence_url": "https://example.org/evidence",
                      "verified_at": "2026-10-16", "sha": sha} for k in REQUIRED}
        checks["main_ci_pass"]["sha"] = "b" * 40
        self.assertIn("main_ci_pass: SHA mismatch",
                      assess({"deployed_sha": sha, "operator": "Test Operator",
                              "checks": checks})["errors"])

    def test_complete_evidence_requires_operator_approval(self):
        sha = "a" * 40
        checks = {k: {"passed": True, "evidence_url": "https://example.org/evidence",
                      "verified_at": "2026-10-16", "sha": sha} for k in REQUIRED}
        self.assertEqual(assess({"deployed_sha": sha, "operator": "Test Operator",
                                 "checks": checks})["decision"], "READY_FOR_OPERATOR_APPROVAL")


if __name__ == "__main__":
    unittest.main()
