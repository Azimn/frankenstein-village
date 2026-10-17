"""Pure deterministic and adversarial route survey tests."""
import sys
from pathlib import Path
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "spike/fvillage"))
from world import route_surveys as r


class SurveyTests(unittest.TestCase):
    def test_collaboration_repeatability_and_event_receipts(self):
        state = None
        for index, site in enumerate(r.SITES):
            account = 101 + index
            state, ok, error = r.report(
                state, 6, site, account, f"Mask{account}", index + 20,
            )
            self.assertTrue(ok, error)
            self.assertEqual(state["reports"][site]["event_id"], index + 20)
            self.assertEqual(r.complete(state), index == len(r.SITES) - 1)
        same, ok, error = r.report(state, 6, r.SITES[0], 999, "Fake", 88)
        self.assertFalse(ok)
        self.assertIn("already signed", error)
        self.assertEqual(same, state)
        next_day = r.refresh(state, 7)
        self.assertEqual(next_day["day"], 7)
        self.assertEqual(next_day["reports"], {})
        self.assertEqual(len(next_day["history"]), 1)
        self.assertTrue(next_day["history"][0]["completed"])
        self.assertEqual(len(next_day["history"][0]["reports"]), len(r.SITES))
        later, ok, err = r.report(next_day, 7, r.SITES[0], 101, "Mask101", 90)
        self.assertTrue(ok, err)
        self.assertEqual(later["reports"][r.SITES[0]]["event_id"], 90)

    def test_expired_unfinished_days_and_no_clock_rewind(self):
        state, ok, err = r.report(None, 2, "red_cord", 3, "First", 30)
        self.assertTrue(ok, err)
        advanced = r.refresh(state, 4)
        self.assertFalse(advanced["history"][0]["completed"])
        self.assertEqual(len(advanced["history"][0]["reports"]), 1)
        rewind, ok, message = r.report(advanced, 3, "grave_marker", 2, "Back", 44)
        self.assertFalse(ok)
        self.assertIn("later village day", message)
        self.assertEqual(rewind, advanced)

    def test_invalid_actions_never_create_state(self):
        for ident, account, event in [
            ("forbidden", 1, 3), ("grave_marker", 0, 1),
            ("grave_marker", 1, -1), ("grave_marker", "x", 5),
        ]:
            state, ok, err = r.report(None, 1, ident, account, "A", event)
            self.assertFalse(ok)
            self.assertEqual(state["reports"], {})
            self.assertTrue(err)
        with self.assertRaises(ValueError):
            r.refresh(None, 0)

    def test_history_is_bounded_and_does_not_mutate_previous_snapshots(self):
        state = r.fresh()
        for day in range(1, 90):
            state, ok, err = r.report(state, day, "river_gauge", 5, "A", day)
            self.assertTrue(ok, err)
        self.assertEqual(len(state["history"]), r.MAX_HISTORY)
        self.assertEqual(state["history"][-1]["day"], 88)
        original = state["history"][-1]["reports"]["river_gauge"]["mask"]
        newer = r.refresh(state, 90)
        newer["history"][-1]["reports"]["river_gauge"]["mask"] = "Modified"
        self.assertEqual(state["history"][-1]["reports"]["river_gauge"]["mask"], original)


if __name__ == "__main__":
    unittest.main()
