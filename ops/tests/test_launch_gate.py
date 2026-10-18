"""Fail-closed release gate contract. Tests use a fixed clock, never the host date."""
from datetime import datetime, timedelta, timezone
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from launch_gate import REQUIRED, assess, _is_evidence_url

NOW = datetime(2026, 10, 17, 20, 0, tzinfo=timezone.utc)
VALID_SHA = "a" * 40
RECEIPT_URL = (
    "https://github.com/Azimn/frankenstein-village/actions/runs/39018163519"
)


def valid_record():
    return {
        "deployed_sha": VALID_SHA,
        "operator": "Release Reviewer",
        "checks": {
            key: {
                "passed": True,
                "evidence_url": RECEIPT_URL,
                "verified_at": "2026-10-17T19:00:00Z",
                "sha": VALID_SHA,
            }
            for key in REQUIRED
        },
    }


class LaunchGateTests(unittest.TestCase):
    def test_empty_or_corrupted_records_are_no_go(self):
        result = assess({}, now=NOW)
        self.assertEqual(result["decision"], "NO-GO")
        self.assertGreaterEqual(len(result["errors"]), len(REQUIRED))
        for bad in (None, "not-json-object", []):
            result = assess(bad, now=NOW)
            self.assertEqual(result["decision"], "NO-GO")
            self.assertIn("expected a JSON object", result["errors"][0])
        record = valid_record()
        record["checks"] = ["array-instead-of-dict"]
        self.assertEqual(assess(record, now=NOW)["decision"], "NO-GO")

    def test_one_unverified_check_is_no_go(self):
        record = valid_record()
        record["checks"]["disposable_restore"]["passed"] = False
        self.assertEqual(assess(record, now=NOW)["decision"], "NO-GO")
        record = valid_record()
        del record["checks"]["continuous_multiplayer_soak"]
        self.assertEqual(assess(record, now=NOW)["decision"], "NO-GO")

    def test_any_check_must_match_exact_deployed_sha(self):
        record = valid_record()
        record["checks"]["event_tick_under_load"]["sha"] = "b" * 40
        self.assertIn(
            "event_tick_under_load: SHA mismatch",
            assess(record, now=NOW)["errors"],
        )
        record = valid_record()
        record["deployed_sha"] = "g" * 40
        self.assertEqual(assess(record, now=NOW)["decision"], "NO-GO")
        record = valid_record()
        record["checks"]["main_ci_pass"]["sha"] = "b" * 40
        self.assertIn(
            "main_ci_pass: SHA mismatch",
            assess(record, now=NOW)["errors"],
        )

    def test_complete_current_evidence_still_requires_operator_approval(self):
        result = assess(valid_record(), now=NOW)
        self.assertEqual(result["decision"], "READY_FOR_OPERATOR_APPROVAL")
        self.assertEqual(result["errors"], [])
        self.assertIn("human", result["note"].lower())

    def test_rejects_placeholder_http_localhost_creds_and_fragment(self):
        for url in (
            "http://github.com/Azimn/frankenstein-village/issues/35",
            "https://example.org/evidence",
            "https://audit.example.net/host",
            "https://host.invalid/a",
            "https://localhost/a",
            "https://127.0.0.1/a",
            "https://192.168.1.2/a",
            "https://user:password@github.com/safe/a",
            "https://github.com/a#private",
            "https://github.com/",
            "file:///tmp/private.json",
            "https://github.com:99999/a",
        ):
            with self.subTest(url=url):
                self.assertFalse(_is_evidence_url(url))
                record = valid_record()
                record["checks"]["main_ci_pass"]["evidence_url"] = url
                self.assertEqual(assess(record, now=NOW)["decision"], "NO-GO")
        self.assertTrue(_is_evidence_url(RECEIPT_URL))
        self.assertTrue(_is_evidence_url("https://drive.google.com/file/d/123/view"))

    def test_fresh_aware_dates_only(self):
        invalid_times = (
            "2026-10-17", "not a timestamp", "",
            "2026-10-17T19:00:00",
            "2026-08-01T12:00:00Z",
            "2026-10-18T01:00:00Z",
        )
        for stamp in invalid_times:
            with self.subTest(stamp=stamp):
                record = valid_record()
                record["checks"]["return_session"]["verified_at"] = stamp
                self.assertEqual(assess(record, now=NOW)["decision"], "NO-GO")
        record = valid_record()
        record["checks"]["return_session"]["verified_at"] = (
            "2026-10-17T14:00:00-05:00"
        )
        self.assertEqual(
            assess(record, now=NOW)["decision"], "READY_FOR_OPERATOR_APPROVAL"
        )

    def test_falsified_pass_and_placeholder_operator_fail(self):
        for passed in (1, "yes", "true", None):
            record = valid_record()
            record["checks"]["main_ci_pass"]["passed"] = passed
            self.assertEqual(assess(record, now=NOW)["decision"], "NO-GO")
        for operator in ("todo", "TBD", "operator", "", None):
            record = valid_record()
            record["operator"] = operator
            self.assertEqual(assess(record, now=NOW)["decision"], "NO-GO")

    def test_clock_must_be_aware(self):
        with self.assertRaises(ValueError):
            assess(valid_record(), now=datetime(2026, 10, 17, 20, 0))


if __name__ == "__main__":
    unittest.main()
