"""GDD-EDGE-06: a Performer show and Innkeep's finite physical food service."""
import copy
import json
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "spike/fvillage"))
from world import stage_state as stage


def args(aid, event, *, day=3, hour=19, mid=None, mask=None):
    return {
        "day": day, "hour": hour, "account_id": aid,
        "mask_id": mid or aid * 10, "mask": mask or f"Mask{aid}",
        "event_id": event,
    }


def witnessed_show():
    state, ok, why = stage.rehearse(
        None, tune="ballad", **args(7, 101))
    assert ok, why
    state, ok, why = stage.perform(
        state, tune="ballad", audience_account_ids=[8],
        **args(7, 102))
    assert ok, why
    state, ok, why = stage.witness(state, **args(8, 103))
    assert ok, why
    return state


def cater(state, aid=8, event=105, bowl=201, cooked=104, hour=19, day=3):
    return stage.cater(
        state, bowl_id=bowl, cook_event_id=cooked,
        **args(aid, event, day=day, hour=hour),
    )


class InnkeepPerformerCateringTests(unittest.TestCase):
    def test_two_independent_accounts_and_actual_bowl_receipt(self):
        source = witnessed_show()
        before = copy.deepcopy(source)
        updated, ok, reason = cater(source)
        self.assertTrue(ok, reason)
        self.assertIsNone(before["service"])
        self.assertIsNone(source["service"], "Pure function must not mutate input")
        service = updated["service"]
        self.assertEqual(service["account_id"], 8)
        self.assertEqual(service["performance_event_id"], 102)
        self.assertEqual(service["witness_event_id"], 103)
        self.assertEqual(service["cook_event_id"], 104)
        self.assertEqual(service["bowl_id"], 201)
        self.assertEqual(service["witness_count"], 1)
        self.assertIn("one real cooked soup bowl", stage.public_lines(updated, 3))

    def test_no_show_or_audience_does_not_invent_demand(self):
        _, ok, reason = cater(None)
        self.assertFalse(ok)
        self.assertIn("No real Performer show", reason)
        state, ok, _ = stage.rehearse(None, tune="ballad", **args(7, 101))
        self.assertTrue(ok)
        state, ok, _ = stage.perform(
            state, tune="ballad", audience_account_ids=[8], **args(7, 102))
        self.assertTrue(ok)
        result, ok, reason = cater(state)
        self.assertFalse(ok)
        self.assertIn("No audience member", reason)
        self.assertIsNone(result["service"])

    def test_performer_cannot_supply_own_pairwise_service(self):
        state = witnessed_show()
        result, ok, reason = cater(state, aid=7)
        self.assertFalse(ok)
        self.assertIn("independent Innkeep", reason)
        self.assertIsNone(result["service"])

    def test_missing_bowl_and_forged_identifiers_fail_closed(self):
        state = witnessed_show()
        for changes in (
            {"bowl": 0}, {"bowl": True}, {"cooked": False},
            {"cooked": -2}, {"event": 0}, {"aid": True},
            {"event": 102}, {"event": 104},
        ):
            result, ok, reason = cater(state, **changes)
            self.assertFalse(ok, reason)
            self.assertIsNone(result["service"])

    def test_duplicate_and_late_service_do_not_change_world(self):
        state = witnessed_show()
        late, ok, reason = cater(state, hour=20)
        self.assertFalse(ok)
        self.assertIn("audience has left", reason)
        self.assertIsNone(late["service"])
        served, ok, reason = cater(state)
        self.assertTrue(ok, reason)
        original = copy.deepcopy(served)
        duplicate, ok, reason = cater(served, event=106, bowl=202, cooked=107)
        self.assertFalse(ok)
        self.assertIn("already received", reason)
        self.assertEqual(duplicate, original)

    def test_later_witness_does_not_rewrite_service_attendance(self):
        state, ok, why = stage.rehearse(
            None, tune="ballad", **args(7, 101))
        self.assertTrue(ok, why)
        state, ok, why = stage.perform(
            state, tune="ballad", audience_account_ids=[8, 9],
            **args(7, 102))
        self.assertTrue(ok, why)
        state, ok, why = stage.witness(state, **args(8, 103))
        self.assertTrue(ok, why)
        served, ok, why = cater(state)
        self.assertTrue(ok, why)
        after, ok, why = stage.witness(served, **args(9, 106))
        self.assertTrue(ok, why)
        self.assertEqual(len(after["witnesses"]), 2)
        self.assertEqual(after["service"]["witness_count"], 1)
        self.assertEqual(stage.normalize(after)["service"]["witness_count"], 1)

    def test_json_restart_and_rollover_preserve_signed_causality(self):
        state, ok, reason = cater(witnessed_show())
        self.assertTrue(ok, reason)
        loaded = stage.normalize(json.loads(json.dumps(state)))
        self.assertEqual(loaded["service"], state["service"])
        tomorrow = stage.refresh(loaded, 4)
        self.assertIsNone(tomorrow["service"])
        self.assertEqual(tomorrow["history"][-1]["service"], state["service"])
        stale, ok, reason = cater(tomorrow, day=3)
        self.assertFalse(ok)
        self.assertIn("rewound", reason)
        self.assertIsNone(stale["service"])

    def test_corrupt_stored_service_never_becomes_valid(self):
        state, ok, reason = cater(witnessed_show())
        self.assertTrue(ok, reason)
        for field, value in (
            ("account_id", 7), ("bowl_id", False),
            ("performance_event_id", 999),
            ("witness_event_id", 999), ("hour", 21),
            ("event_id", 102), ("witness_count", False),
            ("witness_count", 9),
        ):
            forged = copy.deepcopy(state)
            forged["service"][field] = value
            self.assertIsNone(stage.normalize(forged)["service"], field)


if __name__ == "__main__":
    unittest.main()
