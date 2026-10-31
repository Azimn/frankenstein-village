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
        self.assertEqual(c.freight_contract(
            {"merchant_account_id": 12, "consignment_event_id": 91}
        ), {"merchant_account_id": 12, "consignment_event_id": 91})
        self.assertIsNone(c.freight_contract(self.freight), (
            "Already accepted freight must not be accepted a second time"
        ))
        self.assertEqual(c.freight_contract(self.freight, accepted=True), self.freight)
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




class PublicManifestProvenance(unittest.TestCase):
    """Public signed claims require original ledger events, even after restart."""

    def setUp(self):
        self.freight = {
            "merchant_account_id": 12, "consignment_event_id": 91,
            "wanderer_account_id": 19, "accept_event_id": 92,
        }
        self.receipt = {
            "day": 7, "account_id": 19, "mask": "WandererTester",
            "parcel_id": 144, "source_event_id": 91,
            "delivery_event_id": 93, "freight": self.freight,
        }
        self.events = {
            91: {
                "id": 91, "status": "complete", "kind": "village.freight_consigned",
                "actor": {"account_id": 12, "mask": "MerchantTester"},
                "payload": {"day": 7, "market_room_id": 31,
                            "professional_calling": "merchant"},
                "consequence": {"parcel_id": 144},
            },
            92: {
                "id": 92, "status": "complete", "kind": "village.freight_accepted",
                "actor": {"account_id": 19, "mask": "WandererTester"},
                "payload": {"day": 7, "parcel_id": 144, "source_event_id": 91,
                            "professional_calling": "wanderer"},
                "consequence": {"parcel_id": 144, "consignment_event_id": 91},
            },
            93: {
                "id": 93, "status": "complete", "kind": "village.ferry_post_delivered",
                "actor": {"account_id": 19, "mask": "WandererTester"},
                "payload": {"day": 7, "parcel_id": 144, "source_event_id": 91,
                            "freight_accept_event_id": 92},
                "consequence": {"riverside_room_id": 44, "parcel_id": 144,
                                "source_event_id": 91},
            },
        }

    def read(self, state=None, events=None):
        events = self.events if events is None else events
        state = {"receipts": [self.receipt]} if state is None else state
        return c.public_manifest(state, events.get, riverside_room_id=44, market_room_id=31)

    def test_real_signed_freight_and_json_roundtrip(self):
        receipts, verified = self.read()
        self.assertTrue(verified)
        self.assertEqual(receipts, [self.receipt])
        self.assertEqual(
            self.read(json.loads(json.dumps({"receipts": [self.receipt]}))),
            ([self.receipt], True),
        )
        self.assertEqual(self.read({"receipts": []}), ([], True))
        self.assertEqual(
            c.public_manifest(None, self.events.get,
                              riverside_room_id=44, market_room_id=31),
            ([], True),
        )

    def test_wrong_positive_market_room_cannot_be_signed_as_market_lane(self):
        events = copy.deepcopy(self.events)
        events[91]["payload"]["market_room_id"] = 999
        self.assertEqual(self.read(events=events), ([], False))
        events = copy.deepcopy(self.events)
        events[91]["payload"]["market_room_id"] = 31
        self.assertEqual(self.read(events=events), ([self.receipt], True))

    def test_missing_failed_and_forged_canonical_events_fail_closed(self):
        for event_id in (91, 92, 93):
            events = copy.deepcopy(self.events)
            events.pop(event_id)
            self.assertEqual(self.read(events=events), ([], False))
            for path, bad in (
                (("status",), "consequence_failed"),
                (("id",), 999),
                (("actor", "account_id"), 400),
                (("payload", "day"), 9),
                (("consequence", "parcel_id"), 999),
            ):
                events = copy.deepcopy(self.events)
                obj = events[event_id]
                for key in path[:-1]:
                    obj = obj[key]
                obj[path[-1]] = bad
                self.assertEqual(
                    self.read(events=events), ([], False),
                    (event_id, path, bad),
                )
        for event_id, path, bad in (
            (91, ("kind",), "village.ferry_post_collected"),
            (91, ("payload", "professional_calling"), "wanderer"),
            (91, ("payload", "market_room_id"), 0),
            (92, ("payload", "professional_calling"), "merchant"),
            (92, ("payload", "source_event_id"), 55),
            (92, ("consequence", "consignment_event_id"), 55),
            (93, ("payload", "freight_accept_event_id"), None),
            (93, ("consequence", "riverside_room_id"), 31),
            (93, ("actor", "mask"), "OtherMask"),
        ):
            events = copy.deepcopy(self.events)
            obj = events[event_id]
            for key in path[:-1]:
                obj = obj[key]
            obj[path[-1]] = bad
            self.assertEqual(self.read(events=events), ([], False), (event_id, path))

    def test_corrupt_newest_cannot_make_older_signed_case_look_latest(self):
        good = copy.deepcopy(self.receipt)
        for bad in (
            dict(self.receipt, day=0, parcel_id=145, source_event_id=94,
                 delivery_event_id=95),
            dict(self.receipt, day=8, parcel_id=145, source_event_id=94,
                 delivery_event_id=95, freight={
                     "merchant_account_id": 12, "consignment_event_id": 94,
                     "wanderer_account_id": 19, "accept_event_id": 95,
                 }),
            dict(self.receipt, parcel_id=145, source_event_id=91,
                 delivery_event_id=95),
            "damaged record",
        ):
            self.assertEqual(self.read({"receipts": [good, bad]}), ([], False))
        for invalid in ({"receipts": 17}, {"receipts": "not-a-list"},
                        {"receipts": [None]}, {"receipts": [good] * 49}):
            self.assertEqual(self.read(invalid), ([], False))
        self.assertEqual(self.read({"receipts": [good, good]}), ([], False))

    def test_ordinary_solo_courier_is_still_signed_without_merchant(self):
        receipt = {
            "day": 7, "account_id": 19, "mask": "WandererTester",
            "parcel_id": 100, "source_event_id": 70, "delivery_event_id": 71,
        }
        events = {
            70: {"id": 70, "status": "complete",
                 "kind": "village.ferry_post_collected",
                 "actor": {"account_id": 15, "mask": "FirstCollector"},
                 "payload": {"day": 7, "market_room_id": 31},
                 "consequence": {"parcel_id": 100}},
            71: {"id": 71, "status": "complete",
                 "kind": "village.ferry_post_delivered",
                 "actor": {"account_id": 19, "mask": "WandererTester"},
                 "payload": {"day": 7, "parcel_id": 100,
                             "source_event_id": 70,
                             "freight_accept_event_id": None},
                 "consequence": {"riverside_room_id": 44, "parcel_id": 100,
                                 "source_event_id": 70}},
        }
        state = {"receipts": [receipt]}
        self.assertEqual(self.read(state, events), ([receipt], True))
        events[70]["kind"] = "village.freight_consigned"
        self.assertEqual(self.read(state, events), ([], False))
        events[70]["kind"] = "village.ferry_post_collected"
        events[70]["payload"]["market_room_id"] = 999
        self.assertEqual(self.read(state, events), ([], False))

if __name__ == "__main__":
    unittest.main()
