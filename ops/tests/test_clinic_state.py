"""Pure village clinic service model: real assessments, material and aftercare."""
import sys
import unittest
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "spike/fvillage"))
from world import clinic_state as clinic


def actor(day=1, event=11, aid=10, mid=100):
    return dict(day=day, hour=20, account_id=aid, mask_id=mid,
                mask="HealerTester", event_id=event)


class ClinicRules(unittest.TestCase):
    def test_today_requires_real_signed_assessment(self):
        state, ok, why = clinic.treat(None, method="rest", **actor())
        self.assertFalse(ok)
        self.assertIn("examine", why)
        state, ok, why = clinic.assess(None, **actor())
        self.assertTrue(ok, why)
        self.assertEqual(state["condition"], "cold")
        newer, ok, why = clinic.assess(state, **actor(event=12))
        self.assertFalse(ok)
        self.assertEqual(newer, state)
        treated, ok, why = clinic.treat(state, method="rest", **actor(event=13))
        self.assertTrue(ok, why)
        self.assertEqual(treated["treatment"]["improvement"], 25)
        self.assertEqual(treated["treatment"]["assessment_event_id"], 11)
        _, ok, why = clinic.treat(treated, method="compress", **actor(event=14))
        self.assertFalse(ok)
        self.assertIn("already received", why)

    def test_method_matters_and_episodes_are_different(self):
        state, ok, _ = clinic.assess(None, **actor())
        state, ok, _ = clinic.treat(state, method="compress", **actor(event=15))
        self.assertTrue(ok)
        self.assertEqual(state["treatment"]["improvement"], 10)
        daytwo = clinic.refresh(state, 2)
        self.assertEqual(daytwo["condition"], "sprain")
        self.assertIsNone(daytwo["assessment"])
        self.assertEqual(daytwo["history"][0]["day"], 1)
        daytwo, ok, _ = clinic.assess(daytwo, **actor(day=2, event=16))
        self.assertTrue(ok)
        daytwo, ok, _ = clinic.treat(daytwo, method="compress",
                                   **actor(day=2, event=17))
        self.assertEqual(daytwo["treatment"]["improvement"], 25)

    def test_dressings_are_finite_and_clock_cannot_refill_backwards(self):
        stock = clinic.refresh(None, 1)
        self.assertEqual(stock["linen"], 2)
        stock, ok, why = clinic.prepare(stock, day=1)
        self.assertTrue(ok, why)
        stock, ok, why = clinic.prepare(stock, day=1)
        self.assertTrue(ok, why)
        stock, ok, why = clinic.prepare(stock, day=1)
        self.assertFalse(ok)
        self.assertEqual(stock["linen"], 0)
        yesterday = clinic.refresh(stock, 1)
        self.assertEqual(yesterday["linen"], 0)
        tomorrow = clinic.refresh(stock, 2)
        self.assertEqual(tomorrow["linen"], 2)
        rewind, ok, why = clinic.prepare(tomorrow, day=1)
        self.assertFalse(ok)
        self.assertEqual(rewind, tomorrow)

    def test_invalid_actor_and_missing_method_are_rejected(self):
        state, ok, why = clinic.assess(None, **actor(aid=True))
        self.assertFalse(ok)
        self.assertIsNone(state["assessment"])
        state, ok, why = clinic.assess(None, **actor(event=-5))
        self.assertFalse(ok)
        state, ok, why = clinic.treat(None, method="wish", **actor())
        self.assertFalse(ok)
        state, ok, why = clinic.assess(None, **actor())
        self.assertTrue(ok)
        state, ok, why = clinic.treat(state, method="wish", **actor(event=17))
        self.assertFalse(ok)
        self.assertIn("Choose", why)

    def test_bounded_prior_history(self):
        state = None
        for day in range(1, 60):
            state, ok, _ = clinic.assess(state, **actor(day=day,event=day*4))
            self.assertTrue(ok)
            state, ok, _ = clinic.treat(state, method="rest",
                                       **actor(day=day,event=day*4+1))
            self.assertTrue(ok)
        state = clinic.refresh(state, 60)
        self.assertEqual(len(state["history"]), clinic.MAX_HISTORY)
        self.assertEqual(state["history"][-1]["day"], 59)


if __name__ == "__main__":
    unittest.main()
