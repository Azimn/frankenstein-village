"""EDGE-08 renewable Hound caution, signed day gates and replay denial."""
import json
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "spike/fvillage"))
from world import route_surveys as route


def protect(state, *, day, event, marked=False, caution_day=None):
    return route.field_decision(
        state, day, "red_cord", "hound", "protect", marked,
        11, "Hound", event, caution_day=caution_day,
    )


class RenewableCordTests(unittest.TestCase):
    def test_later_day_retying_preserves_signed_history_and_json(self):
        first, ok, why = protect(None, day=1, event=90)
        self.assertTrue(ok, why)
        self.assertFalse(first["field_decisions"]["hound"]["retied_previous_day"])
        blocked, ok, why = protect(first, day=1, event=91, marked=True, caution_day=1)
        self.assertFalse(ok)
        self.assertEqual(blocked, first)
        second, ok, why = protect(route.refresh(first, 2), day=2, event=92,
                                  marked=True, caution_day=1)
        self.assertTrue(ok, why)
        self.assertTrue(second["field_decisions"]["hound"]["retied_previous_day"])
        self.assertEqual(second["history"][-1]["field_decisions"]["hound"]["event_id"], 90)
        self.assertIn("re-tied", " ".join(route.field_lines(second)))
        restored = route.normalize(json.loads(json.dumps(second)))
        self.assertEqual(restored["field_decisions"]["hound"]["event_id"], 92)
        third, ok, why = protect(route.refresh(restored, 3), day=3, event=93,
                                 marked=True, caution_day=2)
        self.assertTrue(ok, why)
        self.assertEqual(third["field_decisions"]["hound"]["event_id"], 93)

    def test_bad_prior_date_and_replay_fail_closed(self):
        for prior in (None, False, True, "1", 0, -1, 2, 3, 99):
            with self.subTest(prior=prior):
                state, ok, why = protect(None, day=2, event=90, marked=True,
                                         caution_day=prior)
                self.assertFalse(ok, (prior, state))
                self.assertIn("already tied", why)
                self.assertEqual(state["field_decisions"], {})
        state, ok, why = protect(None, day=2, event=90, marked=True, caution_day=1)
        self.assertTrue(ok, why)
        duplicate, ok, why = protect(state, day=2, event=91, marked=True,
                                     caution_day=1)
        self.assertFalse(ok)
        self.assertEqual(duplicate, state)

    def test_wanderer_sees_actual_marker_without_guaranteed_safety(self):
        state, ok, why = route.field_decision(
            None, 3, "red_cord", "wanderer", "passability",
            True, 22, "Wanderer", 95,
        )
        self.assertTrue(ok, why)
        self.assertEqual(state["field_decisions"]["wanderer"]["observation"], "marked_caution")
        self.assertIn("not guaranteed safety", " ".join(route.field_lines(state)))


if __name__ == "__main__":
    unittest.main()
