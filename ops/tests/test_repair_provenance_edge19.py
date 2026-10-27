"""GDD-EDGE-19: hostile source records cannot authorize a physical repair."""
import copy
import json
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "spike/fvillage"))
from world import repair_provenance as proof


CASE = "the_broken_mantle"
PART = "brass mantle collar"


def receipts():
    diagnosis = {
        "calling": "smith", "mask_id": 11, "mask": "SmithTester",
        "event_id": 31, "lamp_object_id": 71, "required_part": PART,
        "finding": "cracked mantle collar", "day": 2, "hour": 17,
    }
    d_event = {
        "id": 31, "kind": "professional.smith_lamp_diagnosis",
        "status": "complete",
        "actor": {"mask_id": 11, "mask": "SmithTester", "account_id": 101},
        "payload": {"professional_calling": "smith", "situation_id": CASE,
                    "lamp_object_id": 71, "required_part": PART,
                    "finding": "cracked mantle collar"},
    }
    procurement = {
        "calling": "merchant", "mask_id": 22, "mask": "MerchantTester",
        "event_id": 32, "source_smith_event_id": 31, "required_part": PART,
        "resource_object_id": 72, "units_before": 4, "units_after": 3,
        "unit_worth": 7, "day": 2, "hour": 18,
    }
    p_event = {
        "id": 32, "kind": "professional.merchant_repair_procurement",
        "status": "complete",
        "actor": {"mask_id": 22, "mask": "MerchantTester", "account_id": 202},
        "payload": {"professional_calling": "merchant", "situation_id": CASE,
                    "source_smith_event_id": 31, "resource_object_id": 72,
                    "required_part": PART, "units_before": 4,
                    "units_after": 3, "unit_worth": 7},
    }
    return diagnosis, d_event, procurement, p_event


def valid(d, de, p, pe):
    return (
        proof.verify_diagnosis(d, de, lamp_id=71,
                               situation_id=CASE, part=PART)
        and proof.verify_procurement(p, pe, d, de, stock_id=72,
                                     situation_id=CASE, part=PART)
    )


class RepairSourceTests(unittest.TestCase):
    def test_independent_two_account_signed_handoff(self):
        self.assertTrue(valid(*receipts()))

    def test_restart_json_preserves_provenance_without_new_truth(self):
        before = receipts()
        after = json.loads(json.dumps(before))
        self.assertTrue(valid(*after))
        self.assertEqual(after[0]["event_id"], after[2]["source_smith_event_id"])
        self.assertNotEqual(after[1]["actor"]["account_id"],
                            after[3]["actor"]["account_id"])

    def test_same_account_role_switch_is_not_second_actor(self):
        d, de, p, pe = receipts()
        pe["actor"]["account_id"] = de["actor"]["account_id"]
        self.assertFalse(valid(d, de, p, pe))

    def test_fake_incomplete_or_missing_smith_event(self):
        d, de, p, pe = receipts()
        self.assertFalse(proof.verify_diagnosis(d, None, lamp_id=71,
                                                situation_id=CASE, part=PART))
        for field, value in [
            ("status", "consequence_failed"),
            ("kind", "professional.merchant_repair_procurement"),
            ("id", 999),
        ]:
            bad = copy.deepcopy(de)
            bad[field] = value
            self.assertFalse(valid(d, bad, p, pe), field)

    def test_wrong_object_role_and_source_are_rejected(self):
        d, de, p, pe = receipts()
        for field, value in [
            ("lamp_object_id", 999), ("professional_calling", "mystic"),
            ("situation_id", "another_case"), ("required_part", "gold collar"),
        ]:
            bad = copy.deepcopy(de)
            bad["payload"][field] = value
            self.assertFalse(valid(d, bad, p, pe), field)
        for field, value in [
            ("resource_object_id", 999), ("source_smith_event_id", 777),
            ("professional_calling", "smith"), ("required_part", "tin"),
        ]:
            bad = copy.deepcopy(pe)
            bad["payload"][field] = value
            self.assertFalse(valid(d, de, p, bad), field)

    def test_stock_cannot_be_fabricated_or_duplicated(self):
        d, de, p, pe = receipts()
        for before, after in [(0, -1), (4, 4), (4, 2), (True, 0)]:
            bad = copy.deepcopy(p)
            bad["units_before"], bad["units_after"] = before, after
            self.assertFalse(valid(d, de, bad, pe), (before, after))
        bad = copy.deepcopy(pe)
        bad["payload"]["units_after"] = 4
        self.assertFalse(valid(d, de, p, bad))

    def test_corrupted_actor_and_late_state_fail_closed(self):
        d, de, p, pe = receipts()
        bad = copy.deepcopy(pe)
        bad["actor"]["mask_id"] = 11
        self.assertFalse(valid(d, de, p, bad))
        bad = copy.deepcopy(p)
        bad["day"] = 0
        self.assertFalse(valid(d, de, bad, pe))
        bad = copy.deepcopy(d)
        bad["event_id"] = True
        self.assertFalse(valid(bad, de, p, pe))
        bad = copy.deepcopy(pe)
        bad["status"] = "consequence_failed"
        self.assertFalse(valid(d, de, p, bad))


if __name__ == "__main__":
    unittest.main()
