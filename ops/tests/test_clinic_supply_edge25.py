"""GDD-EDGE-25: finite Merchant linen, distinct Healer acceptance and provenance."""
import json
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "spike/fvillage"))
from world import clinic_state, clinic_supply


def parcel(day=1, source=15, merchant=7, mask=70, market=88):
    return {
        "day": day, "hour": 12, "source_event_id": source,
        "market_room_id": market, "merchant_account_id": merchant,
        "merchant_mask_id": mask, "units": 2, "material": "clean_linen",
    }


def receipt(item=31, source=15, merchant=7, mask=70, market=88, day=1):
    return {
        "id": source, "kind": "professional.merchant_clinic_supply",
        "status": "complete",
        "actor": {"account_id": merchant, "mask_id": mask},
        "payload": {
            "professional_calling": "merchant", "day": day,
            "hour": 12, "market_room_id": market,
        },
        "consequence": {"parcel_id": item, "market_room_id": market, "units": 2,
                        "remaining": 0},
    }


def accept(state=None, **changes):
    data = dict(day=1, event_id=16, source_event_id=15, source_day=1,
                parcel_id=31, merchant_account_id=7, healer_account_id=8)
    data.update(changes)
    return clinic_supply.accept(state, **data)


class ClinicSupplyEdge25(unittest.TestCase):
    def test_market_stock_is_finite_and_day_rollover_does_not_rewind(self):
        stock, good, reason = clinic_supply.issue(None, 1)
        self.assertTrue(good, reason)
        self.assertEqual(stock["remaining"], 0)
        same, good, reason = clinic_supply.issue(stock, 1)
        self.assertFalse(good)
        self.assertEqual(same, stock)
        self.assertRaises(ValueError, clinic_supply.issue, stock, 0)
        fresh, good, reason = clinic_supply.issue(stock, 2)
        self.assertTrue(good, reason)
        self.assertEqual(fresh["day"], 2)
        old, good, reason = clinic_supply.issue(fresh, 1)
        self.assertFalse(good)
        self.assertEqual(old, fresh)
        self.assertEqual(clinic_supply.stock(json.loads(json.dumps(stock)), 1), stock)

    def test_source_checks_exact_completed_event_and_real_parcel(self):
        valid, reason = clinic_supply.verify_source(
            receipt(), parcel(), item_id=31, market_id=88,
            healer_account_id=8, day=1)
        self.assertTrue(valid, reason)
        for field, value in (
            ("id", 99), ("kind", "professional.merchant_kitchen_procurement"),
            ("status", "consequence_failed"),
        ):
            altered = receipt()
            altered[field] = value
            self.assertFalse(clinic_supply.verify_source(
                altered, parcel(), item_id=31, market_id=88,
                healer_account_id=8, day=1)[0], field)

    def test_rejects_actor_role_item_time_and_market_forgeries(self):
        for path, value in (
            (("actor", "account_id"), 10),
            (("actor", "mask_id"), 10),
            (("payload", "professional_calling"), "healer"),
            (("payload", "day"), 2),
            (("payload", "hour"), 13),
            (("payload", "market_room_id"), 9),
            (("consequence", "parcel_id"), 30),
            (("consequence", "market_room_id"), 9),
            (("consequence", "units"), 99),
        ):
            altered = receipt()
            altered[path[0]][path[1]] = value
            self.assertFalse(clinic_supply.verify_source(
                altered, parcel(), item_id=31, market_id=88,
                healer_account_id=8, day=1)[0], path)

    def test_rejects_unsigned_or_contradictory_market_stock_consequence(self):
        # MARKET_DAILY is one: a signed completed withdrawal must leave zero.
        # These are pure admission controls, not a substitute for live-client tests.
        for remaining in ("missing", 1, -1, True, False, None, "0", 0.0, {}, [0]):
            signed = receipt()
            if remaining == "missing":
                del signed["consequence"]["remaining"]
            else:
                signed["consequence"]["remaining"] = remaining
            physical_parcel = parcel()
            cabinet = clinic_state.refresh(None, 1)
            before = json.dumps((signed, physical_parcel, cabinet), sort_keys=True)
            accepted, reason = clinic_supply.verify_source(
                signed, physical_parcel, item_id=31, market_id=88,
                healer_account_id=8, day=1,
            )
            self.assertFalse(accepted, remaining)
            self.assertIn("no valid completed Merchant source", reason)
            # Admission fails before clinic_supply.accept or item deletion.
            self.assertEqual(json.dumps(
                (signed, physical_parcel, cabinet), sort_keys=True), before)
            self.assertEqual(cabinet["linen"], clinic_state.refresh(None, 1)["linen"])
        accepted, reason = clinic_supply.verify_source(
            receipt(), parcel(), item_id=31, market_id=88,
            healer_account_id=8, day=1,
        )
        self.assertTrue(accepted, reason)

    def test_rejects_malformed_source_and_same_account(self):
        for source in (None, {}, {"status": "complete"}):
            self.assertFalse(clinic_supply.verify_source(
                source, parcel(), item_id=31, market_id=88,
                healer_account_id=8, day=1)[0])
        for changed in (
            {"merchant_account_id": 8}, {"source_event_id": True},
            {"units": 1}, {"material": "unknown"},
            {"day": 4}, {"market_room_id": 9},
        ):
            forged = parcel()
            forged.update(changed)
            self.assertFalse(clinic_supply.verify_source(
                receipt(), forged, item_id=31, market_id=88,
                healer_account_id=8, day=1)[0], changed)
        self.assertFalse(clinic_supply.verify_source(
            receipt(), parcel(), item_id=31, market_id=88,
            healer_account_id=7, day=1)[0])

    def test_real_acceptance_increases_shared_stock_and_is_once_only(self):
        accepted, good, reason = accept()
        self.assertTrue(good, reason)
        self.assertEqual(accepted["linen"], 4)
        self.assertEqual(accepted["supply"]["source_event_id"], 15)
        again, good, reason = accept(accepted, event_id=17, parcel_id=32)
        self.assertFalse(good)
        self.assertEqual(again, accepted)
        self.assertIn("already accepted", reason)

    def test_accept_after_preparation_and_persisted_restart(self):
        initial, good, _ = clinic_state.prepare(None, day=1)
        self.assertTrue(good)
        accepted, good, reason = accept(initial)
        self.assertTrue(good, reason)
        self.assertEqual(accepted["linen"], 3)
        saved = json.loads(json.dumps(accepted))
        self.assertEqual(clinic_state.normalize(saved), accepted)
        used, good, reason = clinic_state.prepare(saved, day=1)
        self.assertTrue(good, reason)
        self.assertEqual(used["linen"], 2)
        tomorrow = clinic_state.refresh(used, 2)
        self.assertEqual(tomorrow["linen"], 2)
        self.assertIsNone(tomorrow["supply"])
        self.assertEqual(tomorrow["history"][-1]["supply"]["event_id"], 16)
        self.assertEqual(clinic_state.refresh(used, 1)["linen"], 2)

    def test_stale_future_same_account_and_invalid_ids_are_rejected(self):
        for changes in (
            {"source_day": 3}, {"day": 3}, {"healer_account_id": 7},
            {"source_event_id": True}, {"parcel_id": 0},
        ):
            _state, good, _reason = accept(**changes)
            self.assertFalse(good, changes)
        old, good, reason = accept(
            clinic_state.refresh(None, 3), day=2)
        self.assertFalse(good)
        self.assertIn("later", reason)

    def test_public_status_omits_patient_details_and_shows_stock(self):
        state, good, _ = accept()
        self.assertTrue(good)
        lines = clinic_state.public_lines(state, 1).lower()
        self.assertIn("4 of 4", lines)
        self.assertIn("merchant parcel", lines)
        self.assertNotIn("cold", lines)
        self.assertNotIn("healer account", lines)


if __name__ == "__main__":
    unittest.main()
