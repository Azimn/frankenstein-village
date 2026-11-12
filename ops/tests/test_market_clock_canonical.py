"""Market hold and signed history must not inherit a corrupted village clock."""
import copy
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "spike/fvillage"))
from world import market_standards as market


class MarketClockCanonicalTests(unittest.TestCase):
    def test_corrupt_day_cannot_relabel_signed_hold_as_day_one(self):
        held, ok, reason = market.apply(
            None, "hold", day=1, hour=14,
            account_id=5, mask_id=105, mask="Merchant", event_id=10,
        )
        self.assertTrue(ok, reason)
        self.assertTrue(market.suspended(held, 1))
        for invalid in (True, 1.0, 1.5, "1.0", " 1", -1, "invalid"):
            with self.subTest(day=invalid):
                corrupt = copy.deepcopy(held)
                corrupt["day"] = invalid
                normalized = market.normalize(corrupt)
                self.assertEqual(normalized["day"], 0)
                self.assertIsNone(normalized["review"])
                self.assertFalse(market.suspended(corrupt, 1))
                self.assertEqual(corrupt["review"], held["review"])

    def test_canonical_persisted_day_preserves_real_hold_and_rollover(self):
        held, ok, reason = market.apply(
            None, "hold", day=1, hour=14,
            account_id=5, mask_id=105, mask="Merchant", event_id=10,
        )
        self.assertTrue(ok, reason)
        for valid in (1, "1"):
            with self.subTest(day=valid):
                persisted = copy.deepcopy(held)
                persisted["day"] = valid
                self.assertTrue(market.suspended(persisted, 1))
                later = market.refresh(persisted, 2)
                self.assertEqual(later["history"][-1]["review"]["event_id"], 10)
                self.assertTrue(later["history"][-1]["unresolved_hold"])


if __name__ == "__main__":
    unittest.main()
