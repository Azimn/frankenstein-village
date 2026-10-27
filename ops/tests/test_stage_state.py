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
        state, ok, _ = stage.perform(state, tune="reel", audience_account_ids=[8], **args(event=101))
        self.assertTrue(ok)
        _, ok, why = stage.witness(state, **args(aid=7, event=102))
        self.assertFalse(ok)
        self.assertIn("own audience", why)
        _, ok, why = stage.witness(state, **args(aid=8, hour=21, event=103))
        self.assertFalse(ok)
        self.assertIn("this hour", why)
        _, ok, why = stage.witness(state, **args(aid=9, mid=90, event=106))
        self.assertFalse(ok)
        self.assertIn("present for the actual performance", why)
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


    def test_innkeep_serves_real_performer_or_signed_witness_once(self):
        state, ok, _ = stage.rehearse(None, tune="ballad", **args())
        self.assertTrue(ok)
        state, ok, _ = stage.perform(
            state, tune="ballad", audience_account_ids=[8],
            **args(event=101),
        )
        self.assertTrue(ok)
        state, ok, _ = stage.witness(
            state, **args(aid=8, mid=80, mask="Audience", event=102),
        )
        self.assertTrue(ok)
        catering = dict(
            day=1, hour=20, account_id=9, mask_id=90, mask="Innkeep",
            event_id=103, recipient_account_id=7, recipient_mask_id=70,
            bowl_id=501, cook_event_id=55,
        )
        served, ok, reason = stage.serve(state, **catering)
        self.assertTrue(ok, reason)
        row = served["performance"]["hospitality"][0]
        self.assertEqual(row["recipient_role"], "performer")
        self.assertEqual(row["bowl_id"], 501)
        self.assertEqual(row["cook_event_id"], 55)
        self.assertIn("1 real soup serving", stage.public_lines(served, 1))
        retry, ok, reason = stage.serve(served, **dict(catering, event_id=104, bowl_id=502))
        self.assertFalse(ok)
        self.assertIn("already been served", reason)
        self.assertEqual(retry, served)
        guest, ok, reason = stage.serve(
            served, **dict(catering, event_id=105, bowl_id=502,
                           recipient_account_id=8, recipient_mask_id=80),
        )
        self.assertTrue(ok, reason)
        self.assertEqual(guest["performance"]["hospitality"][-1]["recipient_role"],
                         "signed_witness")
        tomorrow = stage.refresh(guest, 2)
        self.assertEqual(len(tomorrow["history"][-1]["performance"]["hospitality"]), 2)
        self.assertEqual(len(stage.normalize(guest)["performance"]["hospitality"]), 2)

    def test_catering_rejects_late_guests_self_service_and_fake_stock(self):
        state, ok, _ = stage.rehearse(None, tune="reel", **args())
        self.assertTrue(ok)
        state, ok, _ = stage.perform(
            state, tune="reel", audience_account_ids=[8],
            **args(event=101),
        )
        self.assertTrue(ok)
        base = dict(
            day=1, hour=20, account_id=9, mask_id=90, mask="Innkeep",
            event_id=102, recipient_account_id=8, recipient_mask_id=80,
            bowl_id=501, cook_event_id=55,
        )
        _, ok, reason = stage.serve(state, **base)
        self.assertFalse(ok)
        self.assertIn("signed firsthand witness", reason)
        _, ok, reason = stage.serve(state, **dict(base, recipient_account_id=9,
                                                 recipient_mask_id=90))
        self.assertFalse(ok)
        self.assertIn("yourself", reason)
        _, ok, reason = stage.serve(state, **dict(base, recipient_account_id=7,
                                                 recipient_mask_id=70, bowl_id=0))
        self.assertFalse(ok)
        self.assertIn("physical bowl", reason)
        _, ok, reason = stage.serve(state, **dict(base, recipient_account_id=7,
                                                 recipient_mask_id=70, hour=21))
        self.assertFalse(ok)
        self.assertIn("this hour", reason)
        self.assertFalse(stage.normalize(state)["performance"].get("hospitality"))
        damaged = stage.normalize({
            **state, "performance": {**state["performance"],
                "hospitality": [{"account_id": 9, "mask_id": 90,
                    "recipient_account_id": 100, "recipient_mask_id": 1000,
                    "bowl_id": 501, "cook_event_id": 55, "event_id": 104}]}
        })
        self.assertEqual(damaged["performance"]["hospitality"], [])



if __name__ == "__main__":
    unittest.main()
