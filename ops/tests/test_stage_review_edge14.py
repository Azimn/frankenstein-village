"""GDD-EDGE-14: reviews require real, independent signed stage witnesses."""
import json
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "spike/fvillage"))
from world import stage_state as s


def source(kind, eid, aid, mid, *, tune=None, performance_id=None):
    return {
        "id": eid, "kind": "village.stage_" + kind, "status": "complete",
        "actor": {"account_id": aid, "mask_id": mid},
        "payload": {"day": 1, "hour": 20, "tune": tune},
        "consequence": {"performance_event_id": performance_id},
    }


def setup():
    state, ok, _ = s.rehearse(None, day=1, hour=20, account_id=1,
                             mask_id=11, mask="Musician", event_id=100, tune="ballad")
    assert ok
    state, ok, _ = s.perform(state, day=1, hour=20, account_id=1,
                            mask_id=11, mask="Musician", event_id=101,
                            tune="ballad", audience_account_ids=[2])
    assert ok
    state, ok, _ = s.witness(state, day=1, hour=20, account_id=2,
                            mask_id=22, mask="Reporter", event_id=102)
    assert ok
    sources = {
        "rehearsal": source("rehearse", 100, 1, 11, tune="ballad"),
        "performance": source("perform", 101, 1, 11, tune="ballad", performance_id=101),
        "witness": source("witness", 102, 2, 22, performance_id=101),
    }
    return state, sources


def review(state, **overrides):
    kwargs = dict(day=1, hour=20, account_id=2, mask_id=22,
                  mask="Reporter", event_id=103, verdict="praise",
                  performance_event_id=101, witness_event_id=102)
    kwargs.update(overrides)
    return s.review(state, **kwargs)


class StageReviewTests(unittest.TestCase):
    def test_signed_review_and_contest_survive_json_and_rollover(self):
        state, sources = setup()
        self.assertTrue(s.verify_review_sources(state["performance"], state["witnesses"][0], sources, day=1))
        state, ok, why = review(state)
        self.assertTrue(ok, why)
        record = state["performance"]["reviews"][0]
        event = source("review", 103, 2, 22, performance_id=101)
        event["payload"].update(source_performance_event_id=101, source_witness_event_id=102, verdict="praise")
        event["consequence"]["review_event_id"] = 103
        self.assertTrue(s.verify_review_event(record, event, state["performance"]))
        state, ok, why = s.contest(state, day=1, hour=21, account_id=1, mask_id=11,
                                   mask="Musician", event_id=104, review_event_id=103)
        self.assertTrue(ok, why)
        self.assertIn("contested by the Performer", s.public_lines(state, 1))
        state = s.normalize(json.loads(json.dumps(state)))
        self.assertEqual(state["performance"]["reviews"][0]["contest_event_id"], 104)
        tomorrow = s.refresh(state, 2)
        self.assertEqual(tomorrow["history"][-1]["performance"]["reviews"][0]["contest_event_id"], 104)
        archive = s.archive_lines(json.loads(json.dumps(tomorrow)), 2)
        self.assertIn("attributed praise review", archive)
        self.assertIn("Performer contested in event 104", archive)
        self.assertIn("not objective proof", archive)

    def test_forged_or_failed_sources_never_certify_review(self):
        state, sources = setup()
        mutations = (
            lambda x: x["performance"].update(status="consequence_failed"),
            lambda x: x["witness"]["actor"].update(account_id=1),
            lambda x: x["witness"]["consequence"].update(performance_event_id=999),
            lambda x: x["rehearsal"].update(id=999),
            lambda x: x["performance"]["payload"].update(tune="reel"),
        )
        for mutation in mutations:
            broken = json.loads(json.dumps(sources))
            mutation(broken)
            self.assertFalse(s.verify_review_sources(state["performance"], state["witnesses"][0], broken, day=1))

    def test_no_self_review_late_witness_duplicate_or_false_truth(self):
        state, _ = setup()
        for override, fragment in (
            ({"account_id": 1, "mask_id": 11}, "own work"),
            ({"account_id": 3, "mask_id": 33}, "firsthand"),
            ({"witness_event_id": 999}, "firsthand"),
            ({"verdict": "verified_truth"}, "praise or critique"),
        ):
            _, ok, why = review(state, **override)
            self.assertFalse(ok)
            self.assertIn(fragment, why)
        state, ok, _ = review(state)
        self.assertTrue(ok)
        _, ok, why = review(state, event_id=105)
        self.assertFalse(ok)
        self.assertIn("already reviewed", why)
        _, ok, why = review(s.refresh(state, 2), day=1, event_id=106)
        self.assertFalse(ok)
        self.assertIn("rewound", why)

    def test_only_performer_can_contest_and_review_source_is_immutable(self):
        state, _ = setup()
        state, ok, _ = review(state)
        self.assertTrue(ok)
        for aid, mid, rid, fragment in (
            (2, 22, 103, "original Performer"),
            (1, 11, 999, "No such signed review"),
        ):
            _, ok, why = s.contest(state, day=1, hour=20, account_id=aid,
                                   mask_id=mid, mask="Test", event_id=104,
                                   review_event_id=rid)
            self.assertFalse(ok)
            self.assertIn(fragment, why)
        record = state["performance"]["reviews"][0]
        event = source("review", 103, 2, 22, performance_id=101)
        event["payload"].update(source_performance_event_id=101, source_witness_event_id=102, verdict="praise")
        event["consequence"]["review_event_id"] = 103
        for mutation in (
            lambda x: x.update(status="consequence_failed"),
            lambda x: x["payload"].update(source_witness_event_id=999),
            lambda x: x["actor"].update(account_id=1),
            lambda x: x["consequence"].update(review_event_id=999),
        ):
            bad = json.loads(json.dumps(event))
            mutation(bad)
            self.assertFalse(s.verify_review_event(record, bad, state["performance"]))


if __name__ == "__main__":
    unittest.main()
