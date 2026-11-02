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



class RiverPublicProvenanceTests(unittest.TestCase):
    """Public readback must not trust signed-looking persisted gauge fields."""

    def setUp(self):
        observed, ok, reason = witness()
        self.assertTrue(ok, reason)
        self.state, ok, reason = compare(observed)
        self.assertTrue(ok, reason)
        w, d = self.state["witness"], self.state["review"]
        self.witness_event = {
            "id": w["event_id"], "kind": "village.river_gauge_witnessed",
            "status": "complete",
            "actor": {"account_id": w["account_id"],
                      "mask_id": w["mask_id"], "mask": w["mask"]},
            "payload": {"calling": "wanderer", "day": w["day"],
                        "hour": w["hour"], "object_id": 900,
                        "room_id": 800, "location": "Riverside Path",
                        "source_event_id": None},
            "consequence": {"gauge_object_id": 900, "room_id": 800,
                            "account_id": w["account_id"],
                            "witness_event_id": w["event_id"],
                            "review_event_id": None, "source_event_id": None},
        }
        self.review_event = {
            "id": d["event_id"], "kind": "village.river_evidence_compared",
            "status": "complete",
            "actor": {"account_id": d["account_id"],
                      "mask_id": d["mask_id"], "mask": d["mask"]},
            "payload": {"calling": "detective", "day": d["day"],
                        "hour": d["hour"], "object_id": 900,
                        "room_id": 800, "location": "Riverside Path",
                        "source_event_id": w["event_id"]},
            "consequence": {"gauge_object_id": 900, "room_id": 800,
                            "account_id": d["account_id"],
                            "witness_event_id": w["event_id"],
                            "review_event_id": d["event_id"],
                            "source_event_id": w["event_id"]},
        }

    def public(self, state=None, witness_event=None, review_event=None,
               gauge_id=900, room_id=800):
        return " ".join(evidence.verified_public_lines(
            self.state if state is None else state, 3,
            gauge_id=gauge_id, room_id=room_id,
            witness_event=(self.witness_event if witness_event is None
                           else witness_event),
            review_event=(self.review_event if review_event is None
                          else review_event),
        ))

    def test_two_completed_events_project_bounded_public_claims(self):
        text = self.public()
        self.assertIn("Wanderer Wanderer recorded", text)
        self.assertIn("Detective Detective preserved", text)
        self.assertIn("does not establish", text)
        restored = json.loads(json.dumps(self.state))
        self.assertEqual(self.public(restored), text)

    def test_missing_source_event_suppresses_both_claims(self):
        text = " ".join(evidence.verified_public_lines(
            self.state, 3, gauge_id=900, room_id=800,
            witness_event=None, review_event=self.review_event))
        self.assertNotIn("recorded firsthand", text)
        self.assertNotIn("preserved a separate", text)

    def test_forged_failed_or_foreign_wanderer_suppresses_both(self):
        variants = (
            ("status", "failed"),
            ("kind", "village.river_evidence_compared"),
            ("id", 999),
            ("actor.account_id", 999),
            ("actor.mask_id", 999),
            ("actor.mask", "Forged"),
            ("payload.calling", "detective"),
            ("payload.hour", 20),
            ("payload.object_id", 901),
            ("payload.room_id", 801),
            ("payload.location", "Village Square"),
            ("consequence.gauge_object_id", 901),
            ("consequence.witness_event_id", 999),
            ("consequence.account_id", 999),
        )
        for key, value in variants:
            event = json.loads(json.dumps(self.witness_event))
            if "." in key:
                part, field = key.split(".")
                event[part][field] = value
            else:
                event[key] = value
            with self.subTest(key=key):
                text = self.public(witness_event=event)
                self.assertNotIn("recorded firsthand", text)
                self.assertNotIn("preserved a separate", text)

    def test_forged_failed_or_foreign_detective_suppresses_only_review(self):
        variants = (
            ("status", "failed"),
            ("kind", "village.river_gauge_witnessed"),
            ("id", 999),
            ("actor.account_id", 999),
            ("actor.mask_id", 999),
            ("actor.mask", "Forged"),
            ("payload.calling", "wanderer"),
            ("payload.hour", 10),
            ("payload.object_id", 901),
            ("payload.room_id", 801),
            ("payload.source_event_id", 999),
            ("consequence.review_event_id", 999),
            ("consequence.source_event_id", 999),
            ("consequence.account_id", 999),
        )
        for key, value in variants:
            event = json.loads(json.dumps(self.review_event))
            if "." in key:
                part, field = key.split(".")
                event[part][field] = value
            else:
                event[key] = value
            with self.subTest(key=key):
                text = self.public(review_event=event)
                self.assertIn("recorded firsthand", text)
                self.assertNotIn("preserved a separate", text)

    def test_foreign_physical_gauge_and_malformed_event_fail_closed(self):
        for kw in ({"gauge_id": 901}, {"room_id": 801},
                   {"gauge_id": True}, {"room_id": None}):
            with self.subTest(kw=kw):
                text = self.public(**kw)
                self.assertNotIn("recorded firsthand", text)
                self.assertNotIn("preserved a separate", text)
        event = json.loads(json.dumps(self.review_event))
        event["actor"] = "fake actor"
        self.assertNotIn("preserved a separate",
                         self.public(review_event=event))

    def test_first_signed_event_one_allows_distinct_detective_event_two(self):
        state, ok, reason = witness(event_id=1)
        self.assertTrue(ok, reason)
        review, ok, reason = compare(state, event_id=2, source_event_id=1)
        self.assertTrue(ok, reason)
        self.assertEqual(review["witness"]["event_id"], 1)
        self.assertEqual(review["review"]["event_id"], 2)

    def test_mutated_persisted_signature_does_not_invent_ledger_event(self):
        fake = json.loads(json.dumps(self.state))
        fake["review"]["event_id"] = 999
        self.assertIn("recorded firsthand", self.public(state=fake))
        self.assertNotIn("preserved a separate", self.public(state=fake))


if __name__ == "__main__":
    unittest.main()
