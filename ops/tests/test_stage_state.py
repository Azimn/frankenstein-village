"""Stage performance rules require real musicians and actual witnesses."""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "spike/fvillage"))
from world import stage_state as stage


def args(aid=7, mid=70, event=100, day=1, hour=20, mask="Musician"):
    return {"day": day, "hour": hour, "account_id": aid, "mask_id": mid,
            "mask": mask, "event_id": event}


class PerformanceTests(unittest.TestCase):
    def test_rehearse_before_performing_and_prevent_fake_duplicate(self):
        state, ok, why = stage.perform(None, tune="ballad", **args())
        self.assertFalse(ok)
        self.assertIn("Rehearse", why)
        state, ok, why = stage.rehearse(None, tune="ballad", **args())
        self.assertTrue(ok, why)
        original = stage.normalize(state)
        dup, ok, why = stage.rehearse(state, tune="ballad", **args(mid=71,event=101))
        self.assertFalse(ok)
        self.assertEqual(original, dup)
        played, ok, why = stage.perform(state, tune="ballad", **args(event=102))
        self.assertTrue(ok, why)
        self.assertEqual(played["performance"]["rehearsal_event_id"], 100)
        _, ok, why = stage.perform(played, tune="reel", **args(event=103))
        self.assertFalse(ok)
        self.assertIn("already taken place", why)
        self.assertEqual(len(played["rehearsals"]), 1)

    def test_real_audience_and_hour_guard(self):
        state, ok, _ = stage.rehearse(None, tune="reel", **args())
        self.assertTrue(ok)
        state, ok, _ = stage.perform(state, tune="reel", **args(event=101))
        self.assertTrue(ok)
        _, ok, why = stage.witness(state, **args(aid=7, event=102))
        self.assertFalse(ok)
        self.assertIn("own audience", why)
        _, ok, why = stage.witness(state, **args(aid=8, hour=21, event=103))
        self.assertFalse(ok)
        self.assertIn("this hour", why)
        state, ok, why = stage.witness(state, **args(aid=8, mid=80, event=104, mask="Listener"))
        self.assertTrue(ok, why)
        _, ok, why = stage.witness(state, **args(aid=8, mid=90, event=105))
        self.assertFalse(ok)
        self.assertIn("already witnessed", why)
        self.assertIn("1 other player", stage.public_lines(state, 1))

    def test_renewal_retains_actual_history_and_rejects_clock_rewind(self):
        state, ok, _ = stage.rehearse(None, tune="reel", **args())
        self.assertTrue(ok)
        state, ok, _ = stage.perform(state, tune="reel", **args(event=101))
        self.assertTrue(ok)
        tomorrow = stage.refresh(state, 2)
        self.assertIsNone(tomorrow["performance"])
        self.assertEqual(tomorrow["history"][-1]["performance"]["event_id"], 101)
        self.assertEqual(stage.refresh(tomorrow, 1), tomorrow)
        _, ok, why = stage.rehearse(tomorrow, tune="reel", **args(day=1, event=102))
        self.assertFalse(ok)
        self.assertIn("rewound", why)
        nextstate, ok, why = stage.rehearse(tomorrow, tune="ballad", **args(day=2, event=103))
        self.assertTrue(ok, why)
        self.assertEqual(nextstate["day"], 2)

    def test_invalid_id_input_is_fail_closed(self):
        s, ok, _ = stage.rehearse(None, tune="ballad", **args(aid=True))
        self.assertFalse(ok)
        self.assertFalse(s["rehearsals"])
        s, ok, _ = stage.rehearse(None, tune="not-a-song", **args())
        self.assertFalse(ok)
        s, ok, _ = stage.rehearse(None, tune="ballad", **args(hour=24))
        self.assertFalse(ok)
        self.assertEqual(stage.normalize({"rehearsals":[{"account_id": False, "tune":"ballad"}]})["rehearsals"], [])


if __name__ == "__main__":
    unittest.main()
