"""Branch outcomes, signed upkeep and anti-duplication for the bridge mystery."""
import sys
from pathlib import Path
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "spike/fvillage"))
from world import bridge_choices as bridge


def settle(choice="preserve", raw=None, day=2, event=81):
    return bridge.settle(
        raw, choice, account_id=12, mask_id=44,
        mask="Investigator", day=day, hour=19, event_id=event,
    )


class BridgeChoiceTests(unittest.TestCase):
    def test_unwitnessed_state_is_not_modified_by_invalid_input(self):
        original = bridge.normalize(None)
        for choice in ("secret", "", None, "solve"):
            after, accepted, error = settle(choice)
            self.assertFalse(accepted, error)
            self.assertEqual(after, original)
        state, ok, error = bridge.settle(
            None, "preserve", account_id=True, mask_id=44,
            mask="Fake", day=2, hour=19, event_id=1,
        )
        self.assertFalse(ok, error)
        self.assertIsNone(state["resolution"])

    def test_exclusive_in_world_outcomes_and_no_fake_culprit(self):
        for choice in bridge.CHOICES:
            with self.subTest(choice=choice):
                state, ok, error = settle(choice)
                self.assertTrue(ok, error)
                self.assertEqual(state["resolution"]["choice"], choice)
                self.assertEqual(state["resolution"]["event_id"], 81)
                line = bridge.public_line(state)
                self.assertIn("plaque socket", line)
                self.assertIn("unknown" if choice == "preserve" else "No suspect", line)
                other = "preserve" if choice == "display" else "display"
                repeated, accepted, reason = settle(other, state, event=82)
                self.assertFalse(accepted)
                self.assertIn("already settled", reason)
                self.assertEqual(repeated, state)
                self.assertIn(choice, bridge.PUBLIC_LINES)

    def test_upkeep_is_renewable_but_one_signed_account_daily(self):
        state, ok, reason = settle()
        self.assertTrue(ok, reason)
        before, ok, reason = bridge.check(
            state, account_id=21, mask_id=60, day=2, event_id=90
        )
        self.assertTrue(ok, reason)
        self.assertEqual(state["checks"], [])
        self.assertIn("1 signed upkeep inspection", bridge.public_line(before))
        repeated, ok, reason = bridge.check(
            before, account_id=21, mask_id=99, day=2, event_id=91
        )
        self.assertFalse(ok)
        self.assertIn("already inspected", reason)
        self.assertEqual(repeated, before)
        later, ok, reason = bridge.check(
            before, account_id=21, mask_id=60, day=3, event_id=92
        )
        self.assertTrue(ok, reason)
        other, ok, reason = bridge.check(
            later, account_id=22, mask_id=62, day=3, event_id=93
        )
        self.assertTrue(ok, reason)
        self.assertIn("2 signed upkeep inspections", bridge.public_line(other))
        rewind, ok, reason = bridge.check(
            other, account_id=23, mask_id=64, day=2, event_id=94
        )
        self.assertFalse(ok)
        self.assertIn("later inspection", reason)
        self.assertEqual(rewind, other)

    def test_bounded_records_and_no_mutation_of_previous_snapshots(self):
        state, accepted, error = settle("display")
        self.assertTrue(accepted, error)
        previous = state
        for day in range(2, 82):
            state, accepted, error = bridge.check(
                state, account_id=day + 1, mask_id=day + 2,
                day=day, event_id=day + 200,
            )
            self.assertTrue(accepted, error)
        self.assertEqual(len(state["checks"]), bridge.MAX_CHECKS)
        self.assertEqual(previous["checks"], [])
        self.assertEqual(state["resolution"]["event_id"], 81)
        self.assertIn("village day 81", bridge.public_line(state))

    def test_corrupt_records_do_not_forge_success(self):
        self.assertIsNone(bridge.normalize({"resolution": {
            "choice": "preserve", "account_id": True,
            "mask_id": 1, "day": 2, "hour": 3, "event_id": 9,
        }})["resolution"])
        bad = bridge.normalize({"checks": [
            {"account_id": False, "mask_id": 1, "day": 2, "event_id": 10},
            {"account_id": 1, "mask_id": 2, "day": -1, "event_id": 10},
            {"account_id": 1, "mask_id": 2, "day": 2, "event_id": 10},
        ]})
        self.assertEqual(len(bad["checks"]), 1)


if __name__ == "__main__":
    unittest.main()
