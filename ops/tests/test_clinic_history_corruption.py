"""Regression: persisted clinic archive corruption cannot break ordinary clinic use."""
import sys
import unittest
from collections import UserDict, UserList
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "spike/fvillage"))
from world import clinic_state


class ClinicHistoryRecovery(unittest.TestCase):
    def test_corrupt_archive_does_not_crash_public_clinic_or_consume_linen(self):
        for invalid in (7, True, "forged", {"history": "fake"}, object()):
            with self.subTest(archive=repr(invalid)):
                raw = {"day": 3, "condition": "fever", "linen": 2,
                       "history": invalid}
                before = dict(raw)
                state = clinic_state.normalize(raw)
                self.assertEqual(state["history"], [])
                self.assertEqual(state["linen"], 2)
                self.assertIn("St. Lazarus", clinic_state.public_lines(raw, 3))
                self.assertEqual(raw, before)

    def test_saver_backed_history_retains_valid_rows_and_bounded_archive(self):
        rows = UserList([UserDict({"day": n, "assessment": None})
                         for n in range(1, 50)])
        rows.append(UserDict({"day": "invalid", "assessment": "forged"}))
        raw = UserDict({"day": 50, "history": rows})
        state = clinic_state.normalize(raw)
        self.assertEqual(len(state["history"]), clinic_state.MAX_HISTORY)
        self.assertEqual(state["history"][0]["day"], 14)
        self.assertEqual(state["history"][-1]["day"], 49)
        self.assertIsInstance(state["history"][0], dict)

    def test_rollover_after_corrupt_archive_keeps_current_care_and_finite_linen(self):
        raw = {"day": 3, "condition": "fever", "linen": 1,
               "history": "malformed",
               "assessment": {"day": 3, "hour": 10, "event_id": 41,
                              "account_id": 101, "mask_id": 201}}
        state = clinic_state.refresh(raw, 4)
        self.assertEqual(state["day"], 4)
        self.assertEqual(state["linen"], clinic_state.DAILY_LINEN)
        self.assertEqual(len(state["history"]), 1)
        self.assertEqual(state["history"][0]["assessment"]["event_id"], 41)
        self.assertEqual(raw["linen"], 1)


if __name__ == "__main__":
    unittest.main()
