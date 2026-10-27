"""GDD-EDGE-31: Merchant freight, distinct Wanderer custody and real postbag."""
import copy
import json
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "spike/fvillage"))
from world import courier_state as c


class MerchantWandererFreight(unittest.TestCase):
    def setUp(self):
        self.freight = {
            "merchant_account_id": 12, "consignment_event_id": 91,
            "wanderer_account_id": 19, "accept_event_id": 92,
        }
        self.args = dict(
            day=7, account_id=19, mask="WandererTester",
            parcel_id=144, source_event_id=91,
            delivery_event_id=93, freight=self.freight,
        )

    def test_distinct_role_handoff_persists_with_exact_sources(self):
        state, ok, error = c.receive(None, **self.args)
        self.assertTrue(ok, error)
        receipt = state["receipts"][0]
        self.assertEqual(receipt["source_event_id"], 91)
        self.assertEqual(receipt["freight"], self.freight)
        restarted = c.manifest(json.loads(json.dumps(state)))
        self.assertEqual(restarted, state)
        self.assertEqual(restarted["receipts"][0]["account_id"], 19)

    def test_self_handoff_missing_and_forged_sources_fail_without_mutation(self):
        baseline, ok, error = c.receive(None, **self.args)
        self.assertTrue(ok, error)
        for alteration in (
            {"merchant_account_id": 19},
            {"merchant_account_id": True},
            {"consignment_event_id": 0},
            {"accept_event_id": 91},
            {"accept_event_id": None},
            {"wanderer_account_id": 12},
            {"wanderer_account_id": False},
        ):
            forged = dict(self.freight, **alteration)
            before = copy.deepcopy(baseline)
            after, ok, error = c.receive(
                baseline, **dict(self.args, parcel_id=145,
                                 source_event_id=94, delivery_event_id=95,
                                 freight=forged),
            )
            self.assertFalse(ok, alteration)
            self.assertEqual(after, before)
            self.assertTrue(error)
        for altered in (
            dict(self.args, account_id=20),
            dict(self.args, source_event_id=95),
            dict(self.args, freight={}),
        ):
            after, ok, _ = c.receive(None, **altered)
            self.assertFalse(ok)
            self.assertEqual(after["receipts"], [])

    def test_duplicate_late_and_canonical_manifest_fail_closed(self):
        state, ok, error = c.receive(None, **self.args)
        self.assertTrue(ok, error)
        for changed in (
            dict(self.args, delivery_event_id=94),
            dict(self.args, parcel_id=144, source_event_id=99,
                 delivery_event_id=94,
                 freight=dict(self.freight, consignment_event_id=99)),
            dict(self.args, day=6, parcel_id=145, source_event_id=99,
                 delivery_event_id=94,
                 freight=dict(self.freight, consignment_event_id=99)),
        ):
            unchanged, ok, _ = c.receive(state, **changed)
            self.assertFalse(ok)
            self.assertEqual(unchanged, state)
        corrupt = copy.deepcopy(state)
        corrupt["receipts"][0]["freight"]["merchant_account_id"] = 19
        self.assertEqual(c.manifest(corrupt)["receipts"], [])
        corrupt = copy.deepcopy(state)
        corrupt["receipts"][0]["freight"]["consignment_event_id"] = 99
        self.assertEqual(c.manifest(corrupt)["receipts"], [])

    def test_shared_finite_stock_and_ordinary_solo_delivery(self):
        stock, ok = c.issue(None, 7)
        self.assertTrue(ok)
        self.assertEqual(stock["remaining"], 1)
        stock, ok = c.issue(stock, 7)
        self.assertTrue(ok)
        self.assertEqual(stock["remaining"], 0)
        unchanged, ok = c.issue(stock, 7)
        self.assertFalse(ok)
        self.assertEqual(unchanged, stock)
        self.assertEqual(c.stock(stock, 8)["remaining"], 2)
        solo, ok, error = c.receive(
            None, day=7, account_id=19, mask="Solo Wanderer",
            parcel_id=100, source_event_id=70, delivery_event_id=71,
        )
        self.assertTrue(ok, error)
        self.assertNotIn("freight", solo["receipts"][0])
        self.assertEqual(c.manifest(json.loads(json.dumps(solo))), solo)


if __name__ == "__main__":
    unittest.main()
