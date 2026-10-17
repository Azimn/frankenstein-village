import sys
import unittest
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "spike" / "fvillage"))
from world.civic_commissions import refresh, supply, finish


class CivicCommissionTests(unittest.TestCase):
    def test_cooperation_and_idempotence(self):
        state = refresh(None, 1)
        state, ok, _ = supply(state, 1, 101, material_available=True, event_id=1)
        self.assertTrue(ok)
        rejected, ok, _ = supply(state, 1, 102, material_available=True, event_id=2)
        self.assertFalse(ok)
        self.assertEqual(rejected, state)
        rejected, ok, _ = finish(state, 1, 101, at_destination=True, event_id=3)
        self.assertFalse(ok)
        self.assertEqual(rejected, state)
        rejected, ok, _ = finish(state, 1, 102, at_destination=False, event_id=3)
        self.assertFalse(ok)
        state, ok, _ = finish(state, 1, 102, at_destination=True, event_id=3)
        self.assertTrue(ok)
        self.assertEqual(state["commission"]["status"], "complete")
        again, ok, _ = finish(state, 1, 103, at_destination=True, event_id=4)
        self.assertFalse(ok)
        self.assertEqual(again, state)

    def test_resource_guard_and_day_renewal(self):
        state = refresh(None, 1)
        denied, ok, _ = supply(state, 1, 1, material_available=False, event_id=1)
        self.assertFalse(ok)
        self.assertEqual(denied, state)
        state, ok, _ = supply(state, 1, 1, material_available=True, event_id=1)
        state = refresh(state, 2)
        self.assertEqual(state["history"][-1]["status"], "expired")
        self.assertEqual(state["commission"]["status"], "open")
        self.assertEqual(refresh(state, 1), state)

    def test_restart_serialization(self):
        import json
        state = refresh(None, 4)
        state, _, _ = supply(state, 4, 10, material_available=True, event_id=7)
        restored = json.loads(json.dumps(state))
        restored, ok, _ = finish(restored, 4, 11, at_destination=True, event_id=8)
        self.assertTrue(ok)
        self.assertEqual(restored["commission"]["event_ids"], [7, 8])


if __name__ == "__main__":
    unittest.main()
