"""Behavioral and adversarial tests for the physical GDD-EDGE-02 pot repair."""
import json
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "spike/fvillage"))
from world import kitchen_repair_edge02 as rules


def restrict(raw=None, **kwargs):
    values = dict(day=3, hour=12, account_id=11, mask_id=101,
                  mask="InnkeepTester", pot_id=701, event_id=81)
    values.update(kwargs)
    return rules.restrict(raw, **values)


def repair(raw, **kwargs):
    values = dict(day=3, hour=13, account_id=12, mask_id=102,
                  mask="SmithTester", pot_id=701, event_id=83,
                  item_id=901, forge_event_id=82, restriction_event_id=81)
    values.update(kwargs)
    return rules.repair(raw, **values)


class KitchenRepairEdge02Tests(unittest.TestCase):
    def test_independent_innkeep_smith_repair_consumes_one_fitting(self):
        restricted, ok, why = restrict()
        self.assertTrue(ok, why)
        self.assertEqual(restricted["condition"], "restricted")
        self.assertIn("restricted", rules.public_lines(restricted))
        completed, ok, why = repair(restricted)
        self.assertTrue(ok, why)
        self.assertEqual(completed["condition"], "working")
        self.assertEqual(completed["repair"]["item_id"], 901)
        self.assertEqual(completed["repair"]["forge_event_id"], 82)
        self.assertEqual(completed["repair"]["restriction_event_id"], 81)
        self.assertIn("SmithTester", rules.public_lines(completed))
        self.assertEqual(rules.normalize(json.loads(json.dumps(completed))), completed)

    def test_no_second_restriction_or_duplicate_repair(self):
        restricted, _, _ = restrict()
        _, ok, _ = restrict(restricted)
        self.assertFalse(ok)
        completed, _, _ = repair(restricted)
        _, ok, _ = repair(completed)
        self.assertFalse(ok)
        _, ok, _ = restrict(completed)
        self.assertFalse(ok)

    def test_no_same_account_even_if_mask_changes(self):
        restricted, _, _ = restrict()
        _, ok, why = repair(restricted, account_id=11, mask_id=333)
        self.assertFalse(ok)
        self.assertIn("independent", why)

    def test_no_same_mask_even_if_account_changes(self):
        restricted, _, _ = restrict()
        _, ok, _ = repair(restricted, mask_id=101)
        self.assertFalse(ok)

    def test_no_wrong_pot_or_forged_restriction_id(self):
        restricted, _, _ = restrict()
        for override in (dict(pot_id=999), dict(restriction_event_id=999)):
            with self.subTest(override=override):
                _, ok, _ = repair(restricted, **override)
                self.assertFalse(ok)

    def test_no_rewound_clock_or_invalid_hours(self):
        restricted, _, _ = restrict()
        for override in (dict(day=2), dict(day=3, hour=11),
                         dict(hour=24), dict(day=True), dict(hour=True)):
            with self.subTest(override=override):
                _, ok, _ = repair(restricted, **override)
                self.assertFalse(ok)

    def test_reject_malformed_ids_and_missing_physical_part(self):
        restricted, _, _ = restrict()
        for override in (dict(item_id=0), dict(forge_event_id=None),
                         dict(event_id=True), dict(account_id="12"),
                         dict(mask_id=-1)):
            with self.subTest(override=override):
                _, ok, _ = repair(restricted, **override)
                self.assertFalse(ok)

    def test_invalid_persisted_state_fails_closed(self):
        for raw in ("corrupt", {"condition": "working"},
                    {"condition": "restricted", "restriction": {"event_id": 1}},
                    {"condition": "loose", "repair": {"event_id": 1}}):
            with self.subTest(raw=raw):
                self.assertEqual(rules.normalize(raw)["condition"], "invalid")
                _, ok, _ = restrict(raw)
                self.assertFalse(ok)
                _, ok, _ = repair(raw)
                self.assertFalse(ok)

    def test_no_unverified_repair_can_unlock_player_simmering(self):
        restricted, _, _ = restrict()
        self.assertEqual(rules.normalize(restricted)["condition"], "restricted")
        forged = dict(restricted)
        forged["condition"] = "working"
        self.assertEqual(rules.normalize(forged)["condition"], "invalid")

    def test_later_day_repair_retains_original_signed_source(self):
        restricted, _, _ = restrict()
        completed, ok, why = repair(restricted, day=5, hour=1)
        self.assertTrue(ok, why)
        self.assertEqual(completed["restriction"]["day"], 3)
        self.assertEqual(completed["repair"]["day"], 5)


if __name__ == "__main__":
    unittest.main()
