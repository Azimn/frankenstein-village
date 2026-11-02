"""GDD-EDGE-18: finite physical fitting and independent clinical approval."""
import json
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "spike/fvillage"))
from world import clinic_cot_edge18 as rules
from world import clinic_state

def brace(raw=None, **kw):
    data = dict(day=4, hour=9, event_id=81, account_id=11,
                mask_id=101, mask="SmithTester", cot_id=701,
                item_id=901, forge_event_id=80, workshop_id=702)
    data.update(kw)
    return rules.brace(raw, **data)

def certify(raw, **kw):
    data = dict(day=4, hour=10, event_id=83, account_id=12,
                mask_id=102, mask="HealerTester", cot_id=701,
                assessment_event_id=82)
    data.update(kw)
    return rules.certify(raw, **data)

class ClinicCotEdge18Tests(unittest.TestCase):
    def test_distinct_accounts_physical_fitting_and_clinical_approval(self):
        installed, ok, why = brace()
        self.assertTrue(ok, why)
        self.assertEqual(installed["condition"], "braced")
        self.assertIn("independent Healer", rules.public_lines(installed))
        certified, ok, why = certify(installed)
        self.assertTrue(ok, why)
        self.assertEqual(certified["condition"], "certified")
        self.assertEqual(certified["brace"]["item_id"], 901)
        self.assertEqual(certified["certification"]["assessment_event_id"], 82)
        self.assertIn("clinic treat supported", rules.public_lines(certified))
        self.assertEqual(rules.normalize(json.loads(json.dumps(certified))), certified)

    def test_no_clinical_approval_without_real_installed_brace(self):
        for raw in (None, {"condition": "worn"}, {"condition": "invalid"}):
            _, ok, why = certify(raw)
            self.assertFalse(ok, why)

    def test_no_same_account_or_mask_switching(self):
        installed, _, _ = brace()
        for kw in (dict(account_id=11, mask_id=333),
                   dict(account_id=333, mask_id=101)):
            _, ok, why = certify(installed, **kw)
            self.assertFalse(ok, why)
            self.assertIn("independent", why)

    def test_wrong_cot_and_missing_assessment(self):
        installed, _, _ = brace()
        for kw in (dict(cot_id=999), dict(assessment_event_id=0),
                   dict(assessment_event_id=True)):
            _, ok, why = certify(installed, **kw)
            self.assertFalse(ok, why)

    def test_clock_rewind_and_future_installation_rejected(self):
        installed, _, _ = brace()
        for kw in (dict(day=3), dict(day=4, hour=8),
                   dict(hour=24), dict(day=True), dict(hour=True)):
            _, ok, why = certify(installed, **kw)
            self.assertFalse(ok, why)

    def test_no_duplicate_fitting_or_clinical_approval(self):
        installed, _, _ = brace()
        _, ok, _ = brace(installed)
        self.assertFalse(ok)
        certified, _, _ = certify(installed)
        _, ok, _ = certify(certified)
        self.assertFalse(ok)
        _, ok, _ = brace(certified)
        self.assertFalse(ok)

    def test_bad_source_ids_fail_closed(self):
        for kw in (dict(item_id=0), dict(forge_event_id=0),
                   dict(workshop_id=None), dict(event_id=True),
                   dict(account_id="11"), dict(mask_id=-1)):
            _, ok, why = brace(**kw)
            self.assertFalse(ok, why)

    def test_corrupt_persistence_never_grants_safe_cot(self):
        invalid = [
            "invalid", {"condition": "certified"},
            {"condition": "braced", "brace": {"event_id": 2}},
            {"condition": "worn", "certification": {"event_id": 3}},
        ]
        for raw in invalid:
            self.assertEqual(rules.normalize(raw)["condition"], "invalid")
            _, ok, _ = brace(raw)
            self.assertFalse(ok)
            _, ok, _ = certify(raw)
            self.assertFalse(ok)

    def test_forged_clinical_approval_state_is_not_normalized(self):
        installed, _, _ = brace()
        forged = dict(installed, condition="certified")
        self.assertEqual(rules.normalize(forged)["condition"], "invalid")
        certified, _, _ = certify(installed)
        certified["certification"]["cot_id"] = 999
        self.assertEqual(rules.normalize(certified)["condition"], "invalid")

    def test_later_day_certification_keeps_original_signed_provenance(self):
        installed, _, _ = brace()
        certified, ok, why = certify(installed, day=5, hour=0)
        self.assertTrue(ok, why)
        self.assertEqual(certified["brace"]["day"], 4)
        self.assertEqual(certified["certification"]["day"], 5)

    def test_clinic_supported_rest_is_a_real_distinct_treatment(self):
        self.assertIn("supported", clinic_state.METHODS)
        raw, ok, why = clinic_state.assess(
            None, day=4, hour=10, account_id=12, mask_id=102,
            mask="HealerTester", event_id=82)
        self.assertTrue(ok, why)
        cared, ok, why = clinic_state.treat(
            raw, day=4, hour=11, account_id=12, mask_id=102,
            mask="HealerTester", event_id=84, method="supported")
        self.assertTrue(ok, why)
        self.assertEqual(cared["treatment"]["improvement"], 30)
        self.assertIn("reinforced cot", cared["treatment"]["outcome"])
        self.assertEqual(clinic_state.normalize(json.loads(json.dumps(cared))), cared)

if __name__ == "__main__":
    unittest.main()
