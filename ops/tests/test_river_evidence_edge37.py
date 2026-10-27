"""GDD-EDGE-37: independently signed river evidence, adversarial pure tests."""
import json
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "spike/fvillage"))
from world import river_evidence as evidence


def witness(raw=None, **overrides):
    kwargs = dict(day=3, hour=11, account_id=10, mask_id=110,
                  mask="Wanderer", event_id=501, object_id=900)
    kwargs.update(overrides)
    return evidence.witness(raw, **kwargs)


def compare(raw, **overrides):
    kwargs = dict(day=3, hour=12, account_id=20, mask_id=120,
                  mask="Detective", event_id=502, object_id=900,
                  source_event_id=501)
    kwargs.update(overrides)
    return evidence.compare(raw, **kwargs)


class RiverEvidenceTests(unittest.TestCase):
    def test_two_account_signed_physical_comparison_and_json_restart(self):
        state, ok, error = witness()
        self.assertTrue(ok, error)
        compared, ok, error = compare(state)
        self.assertTrue(ok, error)
        self.assertEqual(compared["review"]["source_event_id"], 501)
        self.assertEqual(compared["witness"]["account_id"], 10)
        self.assertEqual(compared["review"]["account_id"], 20)
        self.assertIsNone(state["review"], "Prior snapshot must remain unchanged")
        restored = evidence.normalize(json.loads(json.dumps(compared)))
        self.assertEqual(restored, compared)
        self.assertIn("does not establish", " ".join(evidence.public_lines(restored, 3)))

    def test_independent_accounts_and_masks_required(self):
        state, ok, _ = witness()
        self.assertTrue(ok)
        for changes in (dict(account_id=10), dict(mask_id=110)):
            unchanged, ok, error = compare(state, **changes)
            self.assertFalse(ok)
            self.assertIn("separate", error)
            self.assertEqual(unchanged, state)

    def test_no_forged_source_or_mismatched_physical_object(self):
        state, ok, _ = witness()
        self.assertTrue(ok)
        for changes in (dict(source_event_id=999), dict(object_id=901),
                        dict(source_event_id=True), dict(object_id=True)):
            unchanged, ok, error = compare(state, **changes)
            self.assertFalse(ok)
            self.assertTrue(error)
            self.assertEqual(unchanged, state)

    def test_no_comparison_without_real_source(self):
        state, ok, error = compare(None)
        self.assertFalse(ok)
        self.assertIn("Wanderer", error)
        self.assertIsNone(state["review"])

    def test_no_double_signatures_or_event_reuse(self):
        state, ok, _ = witness()
        self.assertTrue(ok)
        again, ok, error = witness(state, event_id=510)
        self.assertFalse(ok)
        self.assertIn("already signed", error)
        self.assertEqual(again, state)
        reused, ok, error = compare(state, event_id=501)
        self.assertFalse(ok)
        self.assertIn("new canonical event", error)
        compared, ok, _ = compare(state)
        self.assertTrue(ok)
        again, ok, error = compare(compared, event_id=503)
        self.assertFalse(ok)
        self.assertIn("already", error)
        self.assertEqual(again, compared)

    def test_clock_rewind_early_comparison_and_day_rollover(self):
        state, ok, _ = witness()
        self.assertTrue(ok)
        earlier, ok, error = compare(state, hour=10)
        self.assertFalse(ok)
        self.assertIn("predates", error)
        rewind, ok, error = compare(state, day=2)
        self.assertFalse(ok)
        self.assertIn("later village day", error)
        compared, ok, _ = compare(state)
        self.assertTrue(ok)
        nextday, ok, error = evidence.refresh(compared, 4)
        self.assertTrue(ok, error)
        self.assertIsNone(nextday["witness"])
        self.assertEqual(nextday["history"][-1]["review"]["event_id"], 502)
        too_late, ok, error = compare(nextday, day=4)
        self.assertFalse(ok)
        self.assertIn("Wanderer", error)

    def test_bad_id_clock_and_mask_values_rejected(self):
        for changes in (dict(account_id=True), dict(mask_id=False),
                        dict(event_id="501"), dict(object_id=0),
                        dict(hour=24), dict(day=0), dict(mask="")):
            state, ok, error = witness(**changes)
            self.assertFalse(ok, changes)
            self.assertTrue(error)
            self.assertIsNone(state["witness"])
        self.assertFalse(evidence.refresh(None, True)[1])

    def test_corrupt_persisted_review_does_not_create_custody(self):
        state, ok, _ = witness()
        self.assertTrue(ok)
        compared, ok, _ = compare(state)
        self.assertTrue(ok)
        for field, invalid in (("source_event_id", 999),
                               ("account_id", 10), ("object_id", 901),
                               ("event_id", 501), ("hour", 10)):
            corrupted = json.loads(json.dumps(compared))
            corrupted["review"][field] = invalid
            self.assertIsNone(evidence.normalize(corrupted)["review"], field)

    def test_history_bounded_and_public_source_limits(self):
        state = None
        for day in range(1, 35):
            state, ok, error = witness(state, day=day, event_id=day + 500)
            self.assertTrue(ok, error)
        self.assertLessEqual(len(state["history"]), evidence.MAX_HISTORY)
        self.assertIn("not a forecast", " ".join(evidence.public_lines(state, 34)))
        self.assertIn("later dated record", " ".join(evidence.public_lines(state, 33)))


if __name__ == "__main__":
    unittest.main()
