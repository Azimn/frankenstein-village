"""Pure regression contract for a real firewood-funded public warming project."""
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "spike/fvillage"))
from world import square_brazier_state as fire


class SquareBrazierStateTests(unittest.TestCase):
    def change(self, state=None, *, mode="light", day=1, hour=21, event=10):
        return fire.contribute(
            state, day, hour, mode=mode,
            actor={"mask_id": 5, "mask": "Neighbor"},
            bundle_id=100 + event, gather_event_id=200 + event,
            event_id=event,
        )

    def test_real_wood_lights_for_six_hours_then_expires(self):
        state, okay, reason = self.change()
        self.assertTrue(okay, reason)
        self.assertEqual(state["warm_until"], fire.hour_index(1, 21) + 6)
        self.assertEqual(fire.remaining(state, 1, 21), 6)
        self.assertTrue(fire.active(state, 2, 2))
        self.assertFalse(fire.active(state, 2, 3))
        self.assertEqual(len(state["history"]), 1)
        self.assertEqual(state["history"][0]["gather_event_id"], 210)

    def test_feed_extends_existing_fire_but_not_past_horizon(self):
        first, okay, _ = self.change()
        self.assertTrue(okay)
        next_state, okay, reason = self.change(
            first, mode="feed", event=11)
        self.assertTrue(okay, reason)
        self.assertEqual(fire.remaining(next_state, 1, 21), 10)
        denied, okay, reason = self.change(
            next_state, mode="feed", event=12)
        self.assertFalse(okay)
        self.assertIn("well supplied", reason)
        self.assertEqual(denied, next_state)

    def test_refuses_light_while_lit_and_feed_while_cold(self):
        raw, okay, reason = self.change(mode="feed")
        self.assertFalse(okay)
        self.assertIn("cold", reason)
        first, okay, _ = self.change()
        self.assertTrue(okay)
        denied, okay, reason = self.change(first, event=11)
        self.assertFalse(okay)
        self.assertIn("already burning", reason)
        self.assertEqual(denied, first)

    def test_clock_rewind_never_extinguishes_or_restores_fuel(self):
        first, okay, _ = self.change()
        self.assertTrue(okay)
        fed, okay, _ = self.change(first, mode="feed", event=12, day=2, hour=1)
        self.assertTrue(okay)
        self.assertEqual(fire.remaining(fed, 1, 23), 0)
        denied, okay, reason = self.change(
            fed, mode="light", event=13, day=1, hour=23)
        self.assertFalse(okay)
        self.assertIn("later village hour", reason)
        self.assertEqual(denied, fed)
        self.assertTrue(fire.active(fed, 2, 1))

    def test_expired_fire_stays_cold_after_rewinding_one_hour(self):
        # Previously: day 1 21:00 burns until day 2 03:00. If the
        # canonical clock reached that expiry then rewound to 02:00,
        # naive "now < warm_until" logic invented an extra warm hour.
        lit, accepted, reason = self.change()
        self.assertTrue(accepted, reason)
        elapsed = fire.advance(lit, 2, 3)
        self.assertEqual(elapsed["observed_at"], fire.hour_index(2, 3))
        self.assertFalse(fire.active(elapsed, 2, 3))
        self.assertFalse(fire.active(elapsed, 2, 2))
        self.assertEqual(fire.remaining(elapsed, 2, 2), 0)
        refused, allowed, reason = self.change(
            elapsed, day=2, hour=2, event=11)
        self.assertFalse(allowed)
        self.assertIn("later village hour", reason)
        self.assertEqual(refused, elapsed)

    def test_clock_high_water_never_writes_fuel_or_event_history(self):
        lit, ok, _ = self.change()
        self.assertTrue(ok)
        snapshot = fire.advance(lit, 2, 8)
        self.assertEqual(snapshot["warm_until"], lit["warm_until"])
        self.assertEqual(snapshot["history"], lit["history"])
        self.assertEqual(snapshot["observed_at"], fire.hour_index(2, 8))
        self.assertEqual(lit["observed_at"], fire.hour_index(1, 21))
        again = fire.advance(snapshot, 1, 20)
        self.assertEqual(again, snapshot)

    def test_same_signed_event_cannot_double_count(self):
        first, okay, _ = self.change()
        self.assertTrue(okay)
        rejected, okay, reason = self.change(
            first, mode="feed", event=10)
        self.assertFalse(okay)
        self.assertIn("already accounted", reason)
        self.assertEqual(rejected["history"], first["history"])

    def test_history_is_bounded_and_does_not_inflate_long_away_time(self):
        state = None
        for i in range(30):
            state, okay, reason = self.change(
                state, day=i+1, hour=10, event=i+1)
            self.assertTrue(okay, reason)
        self.assertEqual(len(state["history"]), fire.MAX_HISTORY)
        self.assertEqual(state["history"][-1]["event_id"], 30)
        self.assertEqual(state["history"][0]["event_id"], 13)
        self.assertFalse(fire.active(state, 40, 10))
        self.assertEqual(fire.remaining(state, 40, 10), 0)

    def test_no_mutation_on_preflight_or_invalid_mode(self):
        state = {"warm_until": 0, "last_action_at": 0, "history": []}
        changed, okay, reason = self.change(state, mode="douse")
        self.assertFalse(okay)
        self.assertIn("light or brazier feed", reason)
        self.assertEqual(state, {"warm_until": 0,
                                 "last_action_at": 0, "history": []})


if __name__ == "__main__":
    unittest.main()
