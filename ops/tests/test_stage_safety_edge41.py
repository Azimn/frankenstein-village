"""GDD-EDGE-41: independent Hound warning and Performer decision rules.

These pure tests cover state and negative cases. The live ledger and physical
source adapter require separate authenticated Evennia integration testing.
"""
import json
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "spike/fvillage"))
from world import stage_state as stage


def who(account=11, mask=111, event=100, day=1, hour=20, name="Player"):
    return {"day": day, "hour": hour, "account_id": account,
            "mask_id": mask, "mask": name, "event_id": event}


def warning(raw=None, **overrides):
    args = who()
    args.update(overrides)
    return stage.warn(raw, source_event_id=90, cord_id=777, **args)


def decision(raw, choice="indoor", **overrides):
    args = who(account=22, mask=222, event=101, name="Performer")
    args.update(overrides)
    return stage.adapt(raw, choice=choice, **args)


class StageSafetyTests(unittest.TestCase):
    def test_signed_warning_requires_independent_performer_choice(self):
        state, ok, why = warning()
        self.assertTrue(ok, why)
        state, ok, why = stage.rehearse(state, tune="ballad", **who(account=22, mask=222, event=102))
        self.assertTrue(ok, why)
        before = stage.normalize(state)
        blocked, ok, why = stage.perform(state, tune="ballad", **who(account=22, mask=222, event=103))
        self.assertFalse(ok)
        self.assertIn("requires a Performer decision", why)
        self.assertEqual(blocked, before)
        state, ok, why = decision(state)
        self.assertTrue(ok, why)
        state, ok, why = stage.perform(state, tune="ballad", **who(account=22, mask=222, event=104))
        self.assertTrue(ok, why)
        self.assertEqual(state["performance"]["safety_mode"], "indoor")
        self.assertEqual(state["performance"]["safety_decision_event_id"], 101)
        self.assertEqual(state["safety_decision"]["warning_event_id"], 100)

    def test_cancel_blocks_show_and_retains_restart_history(self):
        state, ok, why = warning()
        self.assertTrue(ok, why)
        state, ok, why = decision(state, "cancel")
        self.assertTrue(ok, why)
        state, ok, why = stage.rehearse(state, tune="reel", **who(account=22, mask=222, event=102))
        self.assertTrue(ok, why)
        _, ok, why = stage.perform(state, tune="reel", **who(account=22, mask=222, event=103))
        self.assertFalse(ok)
        self.assertIn("cancelled", why)
        restored = json.loads(json.dumps(state))
        self.assertEqual(stage.normalize(restored)["safety_decision"]["choice"], "cancel")
        next_day = stage.refresh(restored, 2)
        self.assertIsNone(next_day["safety_decision"])
        self.assertIsNone(next_day["safety_warning"])
        self.assertEqual(next_day["history"][-1]["safety_decision"]["choice"], "cancel")
        self.assertIn("Previous stage decision", stage.public_lines(next_day, 2))

    def test_no_warning_no_adaptation(self):
        before = stage.normalize(None)
        after, ok, why = decision(None)
        self.assertFalse(ok)
        self.assertIn("warning", why)
        self.assertEqual(before, after)

    def test_same_account_role_switch_denied(self):
        state, ok, _ = warning()
        self.assertTrue(ok)
        _, ok, why = decision(state, account=11, mask=333)
        self.assertFalse(ok)
        self.assertIn("Hound", why)

    def test_duplicates_are_denied(self):
        state, ok, _ = warning()
        self.assertTrue(ok)
        _, ok, why = warning(state, event_id=120)
        self.assertFalse(ok)
        self.assertIn("already signed", why)
        state, ok, _ = decision(state)
        self.assertTrue(ok)
        _, ok, why = decision(state, event_id=130, choice="cancel")
        self.assertFalse(ok)
        self.assertIn("already signed", why)

    def test_retroactive_warning_and_adaptation_denied(self):
        state, ok, _ = stage.rehearse(None, tune="ballad", **who(account=22, mask=222))
        self.assertTrue(ok)
        state, ok, _ = stage.perform(state, tune="ballad", **who(account=22, mask=222, event=101))
        self.assertTrue(ok)
        _, ok, why = warning(state)
        self.assertFalse(ok)
        self.assertIn("retroactively", why)

    def test_bad_ids_time_and_choices_fail_closed(self):
        for overrides in ({"account_id": True}, {"mask_id": 0},
                          {"event_id": "bad"}, {"day": 0},
                          {"hour": 24}, {"hour": -1}):
            with self.subTest(overrides=overrides):
                _, ok, _ = warning(**overrides)
                self.assertFalse(ok)
        state, ok, _ = warning()
        self.assertTrue(ok)
        for choice in ("teleport", "", None):
            _, ok, why = decision(state, choice)
            self.assertFalse(ok)
            self.assertIn("Choose", why)
        _, ok, why = decision(state, day=0)
        self.assertFalse(ok)
        self.assertIn("rewound", why)

    def test_day_rollover_cannot_reuse_old_warning(self):
        state, ok, _ = warning()
        self.assertTrue(ok)
        tomorrow = stage.refresh(state, 2)
        _, ok, why = decision(tomorrow, day=2, hour=10)
        self.assertFalse(ok)
        self.assertIn("warning", why)

    def test_corrupt_warning_and_same_account_persisted_decision_ignored(self):
        state, ok, _ = warning()
        self.assertTrue(ok)
        state["safety_decision"] = {"account_id": 11, "mask_id": 333,
                                    "event_id": 200, "warning_event_id": 100,
                                    "hour": 20, "choice": "indoor"}
        self.assertIsNone(stage.normalize(state)["safety_decision"])
        state["safety_warning"]["source_event_id"] = False
        self.assertIsNone(stage.normalize(state)["safety_warning"])

    def test_public_status_does_not_invent_crowd(self):
        state, ok, _ = warning()
        self.assertTrue(ok)
        state, ok, _ = decision(state)
        self.assertTrue(ok)
        lines = stage.public_lines(state, 1)
        self.assertIn("Hound signed", lines)
        self.assertIn("Performer chose indoor", lines)
        self.assertIn("No public performance", lines)
        self.assertNotIn("attended", lines)


if __name__ == "__main__":
    unittest.main()
