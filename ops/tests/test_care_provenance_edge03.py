"""GDD-EDGE-03 hostile-record and durable source contract tests.

Pure source checks supplement the existing authenticated two-account telnet
care scenario and the actual Evennia restart assertions.
"""
import copy
import json
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "spike/fvillage"))
from world.care_provenance import validate_healer_source


CASE = "cold_hunter_at_supper"


def sample():
    assessment = {
        "calling": "healer", "account_id": 12, "mask_id": 22,
        "mask": "HealerTester", "resident_id": "silas_crowe",
        "event_id": 104, "day": 2, "hour": 21,
    }
    event = {
        "id": 104, "status": "complete",
        "kind": "professional.healer_cold_assessment",
        "actor": {"account_id": 12, "mask_id": 22, "mask": "HealerTester"},
        "payload": {
            "professional_calling": "healer",
            "situation_id": CASE, "resident_ids": ["silas_crowe"],
            "finding": "cold exposure", "day": 2, "hour": 21,
        },
    }
    return assessment, event


def check(assessment, event, **kwargs):
    return validate_healer_source(
        assessment, event, innkeep_account_id=kwargs.get("innkeep_account_id", 13),
        case_event_ids=kwargs.get("case_event_ids", [101, 104]),
        situation_id=CASE, resident_id="silas_crowe",
    )


class SignedCareSourceTests(unittest.TestCase):
    def test_two_real_accounts_with_matching_completed_source(self):
        a, e = sample()
        proof, error = check(a, e)
        self.assertIsNone(error)
        self.assertEqual(proof, {
            "event_id": 104, "account_id": 12, "mask_id": 22,
            "day": 2, "hour": 21,
        })

    def test_source_survives_json_restart_without_live_account(self):
        a, e = json.loads(json.dumps(sample()))
        proof, error = check(a, e)
        self.assertIsNone(error)
        self.assertEqual(proof["account_id"], 12)

    def test_same_account_cannot_switch_callings_to_self_certify(self):
        a, e = sample()
        proof, error = check(a, e, innkeep_account_id=12)
        self.assertIsNone(proof)
        self.assertIn("different player accounts", error)

    def test_missing_or_failed_source_never_qualifies(self):
        a, e = sample()
        for source in (None, {}, dict(e, status="consequence_failed"),
                       dict(e, kind="professional.innkeep_recovery_care")):
            with self.subTest(source=source):
                self.assertIsNone(check(a, source)[0])

    def test_forged_event_or_unregistered_source_is_refused(self):
        a, e = sample()
        for change in ({"id": 105}, {"actor": {"account_id": 99,
                        "mask_id": 22, "mask": "HealerTester"}}):
            with self.subTest(change=change):
                self.assertIsNone(check(a, dict(e, **change))[0])
        self.assertIsNone(check(a, e, case_event_ids=[101])[0])

    def test_wrong_patient_role_case_or_finding_is_refused(self):
        a, e = sample()
        for key, value in (
            ("resident_ids", ["someone_else"]),
            ("professional_calling", "innkeep"),
            ("situation_id", "unrelated_case"),
            ("finding", "unrelated"),
            ("day", 3),
            ("hour", 20),
        ):
            changed = copy.deepcopy(e)
            changed["payload"][key] = value
            with self.subTest(key=key):
                self.assertIsNone(check(a, changed)[0])

    def test_row_tampering_cannot_borrow_another_healers_event(self):
        a, e = sample()
        for key, value in (
            ("event_id", 105), ("account_id", 13), ("mask_id", 99),
            ("mask", "SomeoneElse"), ("calling", "innkeep"),
            ("resident_id", "other"), ("day", 3), ("hour", 0),
        ):
            changed = dict(a, **{key: value})
            with self.subTest(key=key):
                self.assertIsNone(check(changed, e)[0])

    def test_malformed_ids_and_time_are_refused(self):
        a, e = sample()
        for key, value in (
            ("account_id", None), ("mask_id", True), ("event_id", "104.0"),
            ("day", -1), ("hour", 24), ("hour", False),
        ):
            with self.subTest(key=key, value=value):
                self.assertIsNone(check(dict(a, **{key: value}), e)[0])
        self.assertIsNone(check(a, e, innkeep_account_id=0)[0])


if __name__ == "__main__":
    unittest.main()
