"""GDD-EDGE-04 signed supply checks, independent of Evennia."""
import copy
import json
import sys
import unittest
from collections import UserDict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "spike/fvillage"))
from world import soup_supply_edge04 as supply


def fixture():
    event = {
        "id": 17, "kind": "professional.merchant_kitchen_procurement",
        "status": "complete",
        "actor": {"mask": "Trader", "mask_id": 42, "account_id": 12},
        "payload": {
            "day": 3, "hour": 10, "market_room_id": 61,
            "professional_calling": "merchant",
        },
        "consequence": {"crate_id": 99, "remaining_crates": 1},
    }
    crate = {
        "day": 3, "market_id": 61, "procurement_event_id": 17,
        "merchant_id": 42, "merchant_account_id": 12,
        "merchant": "Trader",
    }
    return event, crate


def verify(event, crate, **kwargs):
    return supply.verify_procurement(
        event, crate, crate_id=99, market_id=61, day=3,
        receiving_account_id=25, require_distinct=True, **kwargs
    )


class SignedKitchenSupplyTests(unittest.TestCase):
    def test_distinct_merchant_and_innkeep_accounts(self):
        event, crate = fixture()
        self.assertEqual(verify(event, crate), (True, None))
        self.assertTrue(supply.verify_procurement(
            event, crate, crate_id=99, market_id=61, day=3,
            receiving_account_id=12, require_distinct=False
        )[0], "A signed solo courier fallback must remain possible")

    def test_same_account_role_switch_is_rejected(self):
        event, crate = fixture()
        good, reason = supply.verify_procurement(
            event, crate, crate_id=99, market_id=61, day=3,
            receiving_account_id=12, require_distinct=True
        )
        self.assertFalse(good)
        self.assertIn("separate account", reason)

    def test_json_restart_and_mapping_backed_source(self):
        event, crate = fixture()
        event, crate = json.loads(json.dumps([event, crate]))
        event["actor"] = UserDict(event["actor"])
        event["payload"] = UserDict(event["payload"])
        event["consequence"] = UserDict(event["consequence"])
        self.assertTrue(verify(event, crate)[0])

    def test_failed_missing_or_wrong_kind_source(self):
        event, crate = fixture()
        self.assertFalse(verify(None, crate)[0])
        self.assertFalse(verify(event, None)[0])
        for field, value in (
            ("status", "consequence_failed"),
            ("kind", "village.kitchen_delivery"),
            ("consequence", {}),
            ("actor", {}),
            ("payload", {}),
        ):
            bad = copy.deepcopy(event)
            bad[field] = value
            self.assertFalse(verify(bad, crate)[0], field)

    def test_forged_crate_and_actor_mismatches(self):
        event, crate = fixture()
        for key, value in (
            ("procurement_event_id", 18), ("merchant_id", 77),
            ("merchant_account_id", 25), ("merchant", "Impostor"),
            ("market_id", 62), ("day", 4),
        ):
            bad = dict(crate, **{key: value})
            self.assertFalse(verify(event, bad)[0], key)
        for key, value in (
            ("id", 18), ("mask_id", 77), ("account_id", 25),
            ("mask", "Impostor"),
        ):
            bad = copy.deepcopy(event)
            bad["actor" if key != "id" else "id"] = (
                dict(bad["actor"], **{key: value}) if key != "id" else value
            )
            self.assertFalse(verify(bad, crate)[0], key)
        bad = copy.deepcopy(event)
        bad["consequence"]["crate_id"] = 100
        self.assertFalse(verify(bad, crate)[0])

    def test_wrong_location_and_role(self):
        event, crate = fixture()
        bad = copy.deepcopy(event)
        bad["payload"]["market_room_id"] = 1
        self.assertFalse(verify(bad, crate)[0])
        bad = copy.deepcopy(event)
        bad["payload"]["professional_calling"] = "innkeep"
        self.assertFalse(verify(bad, crate)[0])

    def test_future_stale_and_clock_rewind(self):
        event, crate = fixture()
        for day in (2, 6):
            good, _ = supply.verify_procurement(
                event, crate, crate_id=99, market_id=61, day=day,
                receiving_account_id=25, require_distinct=True
            )
            self.assertFalse(good)
        good, _ = supply.verify_procurement(
            event, crate, crate_id=99, market_id=61, day=5,
            receiving_account_id=25, require_distinct=True
        )
        self.assertTrue(good)
        for hour in (-1, 24, True):
            bad = copy.deepcopy(event)
            bad["payload"]["hour"] = hour
            self.assertFalse(verify(bad, crate)[0])

    def test_boolean_ids_and_untrusted_receiving_account(self):
        event, crate = fixture()
        for key in ("id",):
            bad = copy.deepcopy(event)
            bad[key] = True
            self.assertFalse(verify(bad, crate)[0])
        for value in (None, True, 0, -1):
            good, _ = supply.verify_procurement(
                event, crate, crate_id=99, market_id=61, day=3,
                receiving_account_id=value, require_distinct=True
            )
            self.assertFalse(good)

    def test_pure_verification_never_mutates_source(self):
        event, crate = fixture()
        before = copy.deepcopy([event, crate])
        self.assertTrue(verify(event, crate)[0])
        self.assertEqual([event, crate], before)


if __name__ == "__main__":
    unittest.main()
