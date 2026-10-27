"""Three Calling decisions change real supply access and public evidence."""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "spike/fvillage"))
from world import market_standards as market
from world.calling_opportunities import WORK, lines


def sign(state, action, *, day=1, actor=5, event=10):
    return market.apply(
        state, action, day=day, hour=14,
        account_id=actor, mask_id=actor + 100,
        mask="Witness", event_id=event,
    )


class MarketStandardsTests(unittest.TestCase):
    def test_merchant_hold_physically_blocks_until_smith_calibrates(self):
        held, ok, error = sign(None, "hold")
        self.assertTrue(ok, error)
        self.assertTrue(market.suspended(held, 1))
        self.assertIn("temporarily on hold", "\n".join(market.public_lines(held, 1)))
        unchanged, ok, error = sign(held, "honor", actor=8, event=11)
        self.assertFalse(ok)
        self.assertEqual(unchanged, held)
        corrected, ok, error = sign(held, "calibrate", actor=9, event=12)
        self.assertTrue(ok, error)
        self.assertFalse(market.suspended(corrected, 1))
        self.assertTrue(market.suspended(held, 1), "Old snapshot was mutated")
        self.assertEqual(corrected["calibration"]["event_id"], 12)
        witnessed, ok, error = sign(corrected, "attest", actor=11, event=13)
        self.assertTrue(ok, error)
        self.assertEqual(witnessed["attestation"]["review_event_id"], 10)
        self.assertEqual(witnessed["attestation"]["calibration_event_id"], 12)
        self.assertIn("attested", "\n".join(market.public_lines(witnessed, 1)))

    def test_honor_keeps_stock_available_and_attestation_requires_two_sources(self):
        state, ok, error = sign(None, "honor")
        self.assertTrue(ok, error)
        self.assertFalse(market.suspended(state, 1))
        failed, ok, error = sign(state, "attest", actor=11, event=17)
        self.assertFalse(ok)
        self.assertIn("both", error)
        self.assertEqual(failed, state)
        calibrated, ok, error = sign(state, "calibrate", actor=9, event=20)
        self.assertTrue(ok, error)
        result, ok, error = sign(calibrated, "attest", actor=11, event=21)
        self.assertTrue(ok, error)
        again, ok, error = sign(result, "attest", event=22)
        self.assertFalse(ok)
        self.assertEqual(again, result)

    def test_merchant_release_and_daily_renewal_with_explicit_history(self):
        held, ok, _ = sign(None, "hold")
        self.assertTrue(ok)
        released, ok, error = sign(held, "release", actor=17, event=25)
        self.assertTrue(ok, error)
        self.assertFalse(market.suspended(released, 1))
        duplicate, ok, error = sign(released, "release", actor=18, event=26)
        self.assertFalse(ok)
        self.assertEqual(duplicate, released)
        old, ok, error = sign(held, "attest", actor=20, event=30)
        self.assertFalse(ok)
        nextday = market.refresh(held, 2)
        self.assertFalse(market.suspended(nextday, 2))
        self.assertTrue(nextday["history"][-1]["unresolved_hold"])
        self.assertEqual(nextday["history"][-1]["day"], 1)
        after, ok, error = sign(nextday, "honor", day=2, event=31)
        self.assertTrue(ok, error)
        self.assertEqual(after["review"]["day"], 2)
        self.assertEqual(nextday["review"], None)
        rejected, ok, error = sign(after, "calibrate", day=1, event=40)
        self.assertFalse(ok)
        self.assertIn("later village day", error)
        self.assertEqual(rejected, after)

    def test_double_calibration_and_out_of_order_review(self):
        fixed, ok, error = sign(None, "calibrate")
        self.assertTrue(ok, error)
        blocked, ok, error = sign(fixed, "hold", actor=7, event=12)
        self.assertFalse(ok)
        self.assertIn("already calibrated", error)
        honored, ok, error = sign(fixed, "honor", actor=7, event=13)
        self.assertTrue(ok, error)
        again, ok, error = sign(honored, "calibrate", actor=8, event=14)
        self.assertFalse(ok)
        self.assertEqual(again, honored)

    def test_t16_market_return_agenda_tracks_real_three_role_resolution(self):
        import json

        held, ok, error = sign(None, "hold", actor=5, event=10)
        self.assertTrue(ok, error)
        merchant = " ".join(market.personal_agenda(held, 1, 105))
        self.assertIn("your Merchant market hold remains active", merchant)
        self.assertIn("trade release", merchant)
        self.assertEqual(market.personal_agenda(held, 1, 109), [])
        self.assertEqual(market.personal_agenda(held, 1, True), [])
        self.assertEqual(market.personal_agenda(held, True, 105), [])

        calibrated, ok, error = sign(held, "calibrate", actor=9, event=12)
        self.assertTrue(ok, error)
        calibrated = json.loads(json.dumps(calibrated))
        merchant = " ".join(market.personal_agenda(calibrated, 1, 105))
        self.assertIn("market hold was resolved", merchant)
        self.assertIn("Smith calibrated", merchant)
        smith = " ".join(market.personal_agenda(calibrated, 1, 109))
        self.assertIn("your Smith calibration", smith)
        self.assertIn("Chronicler can attest", smith)

        attested, ok, error = sign(calibrated, "attest", actor=11, event=13)
        self.assertTrue(ok, error)
        chronicler = " ".join(market.personal_agenda(attested, 1, 111))
        self.assertIn("your Chronicler attestation", chronicler)
        self.assertIn("both source events", chronicler)
        self.assertEqual(market.personal_agenda(attested, 1, 999), [])
        nextday = market.refresh(json.loads(json.dumps(attested)), 2)
        self.assertIn("previous day's standards work is archived",
                      " ".join(market.personal_agenda(nextday, 2, 105)))
        self.assertNotIn("hold remains active",
                         " ".join(market.personal_agenda(nextday, 2, 105)))
        self.assertEqual(market.personal_agenda(nextday, 1, 105), [])
        self.assertEqual(market.personal_agenda(nextday, 3, 105), [])

    def test_t16_market_release_and_honor_have_truthful_personal_outcomes(self):
        held, ok, error = sign(None, "hold", actor=5, event=10)
        self.assertTrue(ok, error)
        released, ok, error = sign(held, "release", actor=17, event=25)
        self.assertTrue(ok, error)
        self.assertIn("market hold was released",
                      " ".join(market.personal_agenda(released, 1, 105)))
        self.assertIn("your Merchant release of the hold",
                      " ".join(market.personal_agenda(released, 1, 117)))
        self.assertNotIn("trade release",
                         " ".join(market.personal_agenda(released, 1, 105)))
        honored, ok, error = sign(None, "honor", actor=5, event=30)
        self.assertTrue(ok, error)
        self.assertIn("decision to honor the disputed prices",
                      " ".join(market.personal_agenda(honored, 1, 105)))

    def test_bad_actor_does_not_create_public_event_record(self):
        state, ok, error = market.apply(
            None, "hold", day=1, hour=13, account_id=True,
            mask_id=1, mask="Fake", event_id=9,
        )
        self.assertFalse(ok)
        self.assertIsNone(state["review"])
        self.assertIn("signed", error)
        self.assertEqual(set(WORK), {
            "innkeep", "chronicler", "smith", "healer", "merchant",
            "wanderer", "performer", "detective", "hound", "mystic",
        })
        self.assertIn("Market Lane", " ".join(lines("merchant")))
        self.assertIn("Calling", " ".join(lines(None)))


if __name__ == "__main__":
    unittest.main()
