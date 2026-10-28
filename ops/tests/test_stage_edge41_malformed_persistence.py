"""EDGE-41: malformed persisted stage containers must fail closed.

These are pure production-state tests. Authenticated two-account gameplay and
actual Evennia restart assertions remain in the clean-checkout regression.
"""
import sys
import unittest
from collections import UserDict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "spike/fvillage"))
from world import stage_state as stage


class MalformedStagePersistenceTests(unittest.TestCase):
    def test_non_sequence_rehearsals_and_history_do_not_crash_or_grant_show(self):
        for malformed in (17, True, "not a record", {"fake": "row"}, object()):
            with self.subTest(value=type(malformed).__name__):
                raw = {"day": 4, "rehearsals": malformed,
                       "history": malformed, "witnesses": malformed}
                state = stage.normalize(raw)
                self.assertEqual(state["rehearsals"], [])
                self.assertEqual(state["history"], [])
                self.assertIsNone(state["performance"])
                self.assertIn("No public performance", stage.public_lines(raw, 4))
                _, allowed, reason = stage.perform(
                    raw, day=4, hour=20, account_id=11, mask_id=111,
                    mask="Performer", tune="ballad", event_id=99)
                self.assertFalse(allowed)
                self.assertIn("Rehearse", reason)

    def test_malformed_witnesses_do_not_create_phantom_audience(self):
        state, ok, reason = stage.rehearse(
            None, day=4, hour=19, account_id=11, mask_id=111,
            mask="Performer", tune="ballad", event_id=90)
        self.assertTrue(ok, reason)
        state, ok, reason = stage.perform(
            state, day=4, hour=20, account_id=11, mask_id=111,
            mask="Performer", tune="ballad", event_id=91,
            audience_account_ids=[22])
        self.assertTrue(ok, reason)
        for malformed in (23, "witness", {"account_id": 22}, True):
            with self.subTest(value=malformed):
                restored = {**state, "witnesses": malformed}
                self.assertEqual(stage.normalize(restored)["witnesses"], [])
                self.assertIn("0 other player account(s) witnessed",
                              stage.public_lines(restored, 4))

    def test_malformed_historical_nested_rows_are_not_public_claims(self):
        raw = {"day": 5, "history": [
            {"day": 4, "performance": "forged",
             "safety_decision": 7},
            UserDict({"day": 3, "performance": ["invalid"],
                      "safety_decision": "cancel"}),
        ]}
        lines = stage.public_lines(raw, 5)
        self.assertNotIn("Previous recorded show:", lines)
        self.assertNotIn("Previous stage decision:", lines)
        self.assertEqual(len(stage.normalize(raw)["history"]), 2)

    def test_valid_mapping_wrappers_and_real_history_still_render(self):
        raw = UserDict({"day": 5, "history": [
            UserDict({"day": 4, "performance": UserDict({
                "mask": "Actual Performer"}), "safety_decision": None}),
        ]})
        self.assertIn("Previous recorded show: Actual Performer, day 4",
                      stage.public_lines(raw, 5))


if __name__ == "__main__":
    unittest.main()
