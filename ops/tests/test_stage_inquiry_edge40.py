"""GDD-EDGE-40: source-verified Performer and independent Detective timeline."""
import copy
import json
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "spike/fvillage"))
from world import stage_state as stage


def actor(aid, mid, eid, hour=21):
    return dict(day=1, hour=hour, account_id=aid, mask_id=mid,
                mask="Player" + str(aid), event_id=eid)


def performed(*, witnessed=True):
    state, ok, why = stage.rehearse(None, tune="ballad", **actor(7, 70, 10))
    assert ok, why
    state, ok, why = stage.perform(
        state, tune="ballad", audience_account_ids=[8],
        **actor(7, 70, 11)
    )
    assert ok, why
    if witnessed:
        state, ok, why = stage.witness(state, **actor(8, 80, 12))
        assert ok, why
    return state


def ledger(witnessed=True):
    result = {
        10: {"kind": "village.stage_rehearse", "status": "complete",
             "actor": {"account_id": 7, "mask_id": 70},
             "payload": {"day": 1, "hour": 21, "tune": "ballad"}},
        11: {"kind": "village.stage_perform", "status": "complete",
             "actor": {"account_id": 7, "mask_id": 70},
             "payload": {"day": 1, "hour": 21, "tune": "ballad"},
             "consequence": {"tavern_room_id": 99, "performance_event_id": 11}},
    }
    if witnessed:
        result[12] = {
            "kind": "village.stage_witness", "status": "complete",
            "actor": {"account_id": 8, "mask_id": 80},
            "payload": {"day": 1, "hour": 21, "tune": None},
            "consequence": {"tavern_room_id": 99, "performance_event_id": 11},
        }
    return result


def inquire(state, *, aid=9, mid=90, eid=13, hour=21,
            source=11, source_account=7, source_mask=70,
            source_hour=21, tune="ballad", witnesses=None, stage_id=50,
            day=1):
    if witnesses is None:
        witnesses = [12]
    return stage.investigate(
        state, day=day, hour=hour, account_id=aid, mask_id=mid,
        mask="Detective", event_id=eid, source_event_id=source,
        source_account_id=source_account, source_mask_id=source_mask,
        source_hour=source_hour, source_tune=tune,
        witness_event_ids=witnesses, stage_object_id=stage_id,
    )


class StageInquiryEdge40Tests(unittest.TestCase):
    def test_real_signed_two_account_chain_and_public_limits(self):
        state = performed()
        events = ledger()
        verified, why = stage.verify_sources(
            state, day=1, tavern_room_id=99, get_event=events.get
        )
        self.assertIsNone(why)
        self.assertEqual(verified, [12])
        result, ok, why = inquire(state, witnesses=verified)
        self.assertTrue(ok, why)
        self.assertEqual(result["inquiries"][0]["source_event_id"], 11)
        self.assertEqual(result["inquiries"][0]["witness_event_ids"], [12])
        self.assertFalse(result["inquiries"][0]["firsthand_witness"])
        self.assertIn("not proof of an alibi", stage.public_lines(result, 1))
        self.assertEqual(state["inquiries"], [])

    def test_signed_show_without_a_witness_is_not_an_invented_alibi(self):
        state = performed(witnessed=False)
        events = ledger(witnessed=False)
        verified, why = stage.verify_sources(
            state, day=1, tavern_room_id=99, get_event=events.get
        )
        self.assertEqual(verified, [])
        self.assertIsNone(why)
        result, ok, why = inquire(state, witnesses=[])
        self.assertTrue(ok, why)
        self.assertEqual(result["inquiries"][0]["witness_event_ids"], [])
        self.assertIn("0 signed firsthand witness", stage.public_lines(result, 1))

    def test_no_show_wrong_actor_and_same_account_switch_fail_closed(self):
        empty, ok, why = inquire(None)
        self.assertFalse(ok)
        self.assertIn("no actual performance", why)
        state = performed()
        for changes, expected in (
            ({"aid": 7}, "performing account"),
            ({"aid": 0}, "real Detective"),
            ({"mid": False}, "real Detective"),
            ({"eid": True}, "real Detective"),
            ({"stage_id": 0}, "real Detective"),
            ({"source": 999}, "does not match"),
            ({"source_account": 10}, "does not match"),
            ({"source_mask": 71}, "does not match"),
            ({"source_hour": 20}, "does not match"),
            ({"tune": "reel"}, "does not match"),
            ({"witnesses": []}, "Witness evidence"),
            ({"witnesses": [12, 99]}, "Witness evidence"),
            ({"hour": 20}, "future"),
            ({"hour": 24}, "clock"),
        ):
            changed, ok, why = inquire(state, **changes)
            self.assertFalse(ok, changes)
            self.assertIn(expected.lower(), why.lower(), changes)
            self.assertEqual(changed, state)

    def test_duplicate_docket_capacity_and_distinct_accounts(self):
        state = performed()
        state, ok, why = inquire(state)
        self.assertTrue(ok, why)
        denied, ok, why = inquire(state, mid=91, eid=14)
        self.assertFalse(ok)
        self.assertIn("already investigated", why)
        self.assertEqual(denied, state)
        for account in range(10, 15):
            state, ok, why = inquire(
                state, aid=account, mid=account * 10, eid=account + 20
            )
            self.assertTrue(ok, why)
        denied, ok, why = inquire(state, aid=15, mid=150, eid=40)
        self.assertFalse(ok)
        self.assertIn("docket is full", why)

    def test_provenance_rejects_forged_or_failed_sources(self):
        state = performed()
        originals = ledger()
        corruptions = (
            (11, "status", "consequence_failed"),
            (11, "kind", "village.stage_rehearse"),
            (11, "actor", {"account_id": 9, "mask_id": 70}),
            (11, "payload", {"day": 1, "hour": 20, "tune": "ballad"}),
            (11, "consequence", {"tavern_room_id": 55, "performance_event_id": 11}),
            (10, "status", "recorded"),
            (10, "actor", {"account_id": 7, "mask_id": 71}),
            (10, "payload", {"day": 1, "hour": 22, "tune": "ballad"}),
            (12, "status", "consequence_failed"),
            (12, "actor", {"account_id": 7, "mask_id": 80}),
            (12, "consequence", {"tavern_room_id": 99, "performance_event_id": 999}),
        )
        for eid, field, value in corruptions:
            events = copy.deepcopy(originals)
            events[eid][field] = value
            verified, why = stage.verify_sources(
                state, day=1, tavern_room_id=99, get_event=events.get
            )
            self.assertIsNone(verified, (eid, field))
            self.assertTrue(why)
        events = copy.deepcopy(originals)
        del events[11]
        verified, why = stage.verify_sources(
            state, day=1, tavern_room_id=99, get_event=events.get
        )
        self.assertIsNone(verified)
        self.assertIn("canonical source", why)

    def test_audience_was_present_not_automatically_a_signed_witness(self):
        state = performed(witnessed=False)
        self.assertEqual(state["performance"]["eligible_audience_ids"], [8])
        self.assertEqual(state["witnesses"], [])
        verified, why = stage.verify_sources(
            state, day=1, tavern_room_id=99,
            get_event=ledger(witnessed=False).get
        )
        self.assertEqual(verified, [])
        self.assertIsNone(why)
        forged = copy.deepcopy(state)
        forged["witnesses"].append({
            "account_id": 9, "mask_id": 90, "event_id": 12, "mask": "Late"
        })
        verified, why = stage.verify_sources(
            forged, day=1, tavern_room_id=99, get_event=ledger().get
        )
        self.assertIsNone(verified)
        self.assertIn("signed firsthand", why)

    def test_json_restart_history_and_late_day_denial(self):
        state = performed()
        state, ok, why = inquire(state)
        self.assertTrue(ok, why)
        snapshot = stage.normalize(json.loads(json.dumps(state)))
        self.assertEqual(snapshot["inquiries"], state["inquiries"])
        next_day = stage.refresh(snapshot, 2)
        self.assertEqual(next_day["inquiries"], [])
        self.assertEqual(next_day["history"][-1]["inquiries"][0]["event_id"], 13)
        denied, ok, why = inquire(next_day, day=1)
        self.assertFalse(ok)
        self.assertIn("rewound", why)
        denied, ok, why = inquire(next_day, day=2, hour=21)
        self.assertFalse(ok)
        self.assertIn("no actual performance", why)
        self.assertEqual(denied, next_day)

    def test_corrupted_inquiry_does_not_survive_normalization(self):
        state = performed()
        state, ok, why = inquire(state)
        self.assertTrue(ok, why)
        for field, value in (
            ("account_id", 7), ("source_event_id", 999),
            ("stage_object_id", 0), ("witness_event_ids", [999]),
            ("hour", 20), ("event_id", False),
        ):
            corrupted = copy.deepcopy(state)
            corrupted["inquiries"][0][field] = value
            self.assertEqual(stage.normalize(corrupted)["inquiries"], [])



class StagePublicInquiryProvenanceTests(unittest.TestCase):
    """A signed-looking persisted inquiry is never itself public authority."""

    def setUp(self):
        original = performed()
        self.state, ok, reason = inquire(original)
        self.assertTrue(ok, reason)
        self.row = self.state["inquiries"][0]
        self.event = {
            "id": 13, "kind": "village.stage_investigated",
            "status": "complete",
            "actor": {"account_id": 9, "mask_id": 90, "mask": "Detective"},
            "payload": {"day": 1, "hour": 21, "tavern_room_id": 99,
                        "stage_object_id": 50,
                        "source_performance_event_id": 11,
                        "verified_witness_event_ids": [12]},
            "consequence": {"tavern_room_id": 99, "stage_object_id": 50,
                            "performance_event_id": 11,
                            "witness_event_ids": [12],
                            "independent_detective_account_id": 9,
                            "inquiry_event_id": 13,
                            "conclusion": "signed_show_not_alibi"},
        }

    def valid(self, event=None, row=None, **overrides):
        kwargs = dict(day=1, tavern_room_id=99, stage_object_id=50,
                      performance=self.state["performance"],
                      witness_event_ids=[12])
        kwargs.update(overrides)
        return stage.verified_public_inquiry(
            self.row if row is None else row,
            self.event if event is None else event, **kwargs)

    def test_completed_canonical_inquiry_qualifies_for_public_projection(self):
        self.assertTrue(self.valid())
        self.assertTrue(self.valid(event=json.loads(json.dumps(self.event))))

    def test_missing_failed_forged_and_foreign_inquiry_denied(self):
        for field, value in (
            ("status", "failed"), ("kind", "village.stage_witness"),
            ("id", 999), ("actor.account_id", 99),
            ("actor.mask_id", 99), ("actor.mask", "Forged"),
            ("payload.day", 2), ("payload.hour", 20),
            ("payload.tavern_room_id", 999),
            ("payload.stage_object_id", 999),
            ("payload.source_performance_event_id", 999),
            ("payload.verified_witness_event_ids", []),
            ("consequence.tavern_room_id", 999),
            ("consequence.stage_object_id", 999),
            ("consequence.performance_event_id", 999),
            ("consequence.witness_event_ids", []),
            ("consequence.independent_detective_account_id", 7),
            ("consequence.inquiry_event_id", 999),
            ("consequence.conclusion", "alibi_proven"),
        ):
            event = copy.deepcopy(self.event)
            if "." in field:
                parent, child = field.split(".")
                event[parent][child] = value
            else:
                event[field] = value
            with self.subTest(field=field):
                self.assertFalse(self.valid(event=event))

    def test_missing_ledger_and_wrong_physical_platform_denied(self):
        self.assertFalse(stage.verified_public_inquiry(
            self.row, None, day=1, tavern_room_id=99,
            stage_object_id=50, performance=self.state["performance"],
            witness_event_ids=[12]))
        self.assertFalse(self.valid(stage_object_id=51))
        self.assertFalse(self.valid(tavern_room_id=100))
        self.assertFalse(self.valid(witness_event_ids=[]))
        self.assertFalse(self.valid(day=2))

    def test_mutated_persisted_inquiry_is_not_authority(self):
        row = copy.deepcopy(self.row)
        row["event_id"] = 999
        self.assertFalse(self.valid(row=row))
        row = copy.deepcopy(self.row)
        row["account_id"] = 7
        self.assertFalse(self.valid(row=row))


if __name__ == "__main__":
    unittest.main()
