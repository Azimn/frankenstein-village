"""Causal public-board NPC recognition, masking and bounded-memory tests."""
import sys
from pathlib import Path
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "spike/fvillage"))
from world import resident_civic as civic, route_surveys


def board(day=4):
    current, ok, error = route_surveys.report(
        None, day, "market_scale", 101, "SmokeTester", 902
    )
    assert ok, error
    current, ok, error = route_surveys.report(
        current, day, "river_gauge", 102, "SmithTester", 903
    )
    assert ok, error
    return current


class CivicRecognitionTests(unittest.TestCase):
    def test_public_provenance_really_names_this_mask(self):
        state = board()
        observed = civic.signed_checkpoint(
            state, 4, account_id=101, mask_name="SmokeTester"
        )
        self.assertEqual(observed["site"], "market_scale")
        self.assertEqual(observed["event_id"], 902)
        self.assertEqual(observed["count"], 2)
        self.assertFalse(observed["complete"])
        line, result = civic.public_route_line(
            state, 4, account_id=101, mask_name="SmokeTester"
        )
        self.assertIsNotNone(result)
        self.assertIn("your signed inspection", line)
        self.assertIn("Traders notice", line)
        self.assertIn("still needs 2", line)
        self.assertIn("wasn't there", line)

    def test_no_credit_for_same_account_other_mask_or_visitor(self):
        state = board()
        for account_id, mask_name in (
            (101, "DifferentMask"), (102, "SmokeTester"),
            (333, "SmokeTester"), (True, "SmokeTester"),
            (None, "SmokeTester"),
        ):
            with self.subTest(account_id=account_id, mask=mask_name):
                line, contribution = civic.public_route_line(
                    state, 4, account_id=account_id, mask_name=mask_name
                )
                self.assertIsNone(contribution)
                self.assertIn("2 of 4", line)
                self.assertNotIn("your signed inspection", line)
        self.assertIsNone(civic.signed_checkpoint(
            state, 5, account_id=101, mask_name="SmokeTester"
        ))
        self.assertIsNone(civic.signed_checkpoint(
            state, 3, account_id=101, mask_name="SmokeTester"
        ))

    def test_social_consequence_once_per_npc_per_mask_day(self):
        raw = None
        raw, accepted = civic.mark_recognized(
            raw, mask_id=501, day=4, site="market_scale", event_id=902
        )
        self.assertTrue(accepted)
        repeated, accepted = civic.mark_recognized(
            raw, mask_id=501, day=4, site="river_gauge", event_id=903
        )
        self.assertFalse(accepted)
        self.assertEqual(repeated, raw)
        next_day, accepted = civic.mark_recognized(
            raw, mask_id=501, day=5, site="market_scale", event_id=905
        )
        self.assertTrue(accepted)
        other, accepted = civic.mark_recognized(
            next_day, mask_id=502, day=5, site="market_scale", event_id=905
        )
        self.assertTrue(accepted)
        self.assertEqual(len(other), 3)
        current = civic.remembered_help(other, mask_id=501, current_day=5)
        self.assertIn("already put your name", current)
        previous = civic.remembered_help(other, mask_id=501, current_day=6)
        self.assertIn("remember you helping", previous)
        self.assertNotIn("SmokeTester", previous)
        self.assertIsNone(civic.remembered_help(
            other, mask_id=503, current_day=6
        ))

    def test_archival_bounds_and_corrupted_input(self):
        raw = []
        for mask_id in range(1, 170):
            raw, _added = civic.mark_recognized(
                raw, mask_id=mask_id, day=3, site="red_cord",
                event_id=mask_id + 200,
            )
        self.assertEqual(len(raw), civic.MAX_RECOGNITIONS)
        self.assertEqual(raw[-1]["mask_id"], 169)
        self.assertNotIn(1, [row["mask_id"] for row in raw])
        self.assertEqual(civic.normalized_recognitions(99), [])
        malformed = [
            {"mask_id": 0, "day": 2, "event_id": 1, "site": "red_cord"},
            {"mask_id": 1, "day": -1, "event_id": 1, "site": "red_cord"},
            {"mask_id": 1, "day": 2, "event_id": 1, "site": []},
            {"mask_id": 1, "day": 2, "event_id": 1, "site": "secret"},
            {"mask_id": 1, "day": 2, "event_id": 1, "site": "red_cord"},
            {"mask_id": 1, "day": 2, "event_id": 2, "site": "river_gauge"},
        ]
        self.assertEqual(len(civic.normalized_recognitions(malformed)), 1)
        rows, accepted = civic.mark_recognized(
            malformed, mask_id=0, day=2, site="red_cord", event_id=3
        )
        self.assertFalse(accepted)
        self.assertEqual(len(rows), 1)


if __name__ == "__main__":
    unittest.main()
