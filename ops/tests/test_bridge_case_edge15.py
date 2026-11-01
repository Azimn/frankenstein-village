"""EDGE-15 behavioral, adversarial, two-account and JSON-restart state tests."""
import copy
import json
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "spike/fvillage"))
from world import bridge_case_state as case


def observation(day=3, account=11, mask_id=111, event=90):
    return {
        "day": day, "pattern": "daylight", "source_event_id": event,
        "witnesses": [{"account_id": account, "mask_id": mask_id}],
    }


def detective(state=None, day=3, hour=11, account=11, mask_id=111,
              event=101, observed=None):
    return case.examine(
        state, day=day, hour=hour, account_id=account,
        mask_id=mask_id, mask="DetectiveTester", event_id=event,
        observation=observation(day, account, mask_id) if observed is None else observed,
    )


def source(event=101, account=11, mask_id=111, day=3, hour=11):
    return {
        "id": event, "status": "complete",
        "kind": "village.bridge_plaque_examined",
        "actor": {
            "account_id": account, "mask_id": mask_id,
            "mask": "DetectiveTester",
        },
        "payload": {
            "day": day, "hour": hour, "location": "The Old Stone Bridge",
            "professional_calling": "detective", "observation_event_id": 90,
        },
        "consequence": {
            "case_exam_event_id": event, "observation_event_id": 90,
            "pattern": "daylight", "finding": "physical_marks_only",
        },
    }


def chronicler(state, *, day=3, hour=12, account=22, mask_id=222,
              event=102, signed=None):
    return case.publish(
        state, day=day, hour=hour, account_id=account,
        mask_id=mask_id, mask="ChroniclerTester", event_id=event,
        source=source() if signed is None else signed,
    )


class BridgeCaseEdge15Tests(unittest.TestCase):
    def test_two_distinct_accounts_sign_physical_examination_and_bulletin(self):
        state, ok, why = detective()
        self.assertTrue(ok, why)
        before = copy.deepcopy(state)
        published, ok, why = chronicler(state)
        self.assertTrue(ok, why)
        self.assertEqual(state, before, "The pure transition mutated its input")
        exam = published["case_examinations"][0]
        bulletin = published["case_bulletins"][0]
        self.assertEqual(bulletin["source_event_id"], exam["event_id"])
        self.assertEqual(bulletin["observation_event_id"], 90)
        self.assertNotEqual(bulletin["account_id"], exam["account_id"])
        text = " ".join(case.case_lines(published, 3))
        self.assertIn("bulletin event 102", text)
        self.assertIn("Detective source 101", text)
        self.assertIn("do not identify a culprit", text)

    def test_json_roundtrip_and_next_day_history_without_resetting_truth(self):
        state, ok, why = detective()
        self.assertTrue(ok, why)
        state, ok, why = chronicler(state)
        self.assertTrue(ok, why)
        restarted = json.loads(json.dumps(state))
        self.assertEqual(restarted, state)
        self.assertIn("No independently published", " ".join(case.case_lines(restarted, 4)))
        later, ok, why = detective(
            restarted, day=4, hour=10, event=103,
            observed=observation(day=4, event=92),
        )
        self.assertTrue(ok, why)
        later_source = source(event=103, day=4, hour=10)
        later_source["payload"]["observation_event_id"] = 92
        later_source["consequence"]["observation_event_id"] = 92
        later, ok, why = chronicler(
            later, day=4, hour=11, event=104, signed=later_source,
        )
        self.assertTrue(ok, why)
        self.assertEqual([b["event_id"] for b in later["case_bulletins"]], [102, 104])

    def test_no_examination_without_firsthand_physical_observation(self):
        for observed in (
            {}, observation(day=2), observation(account=999),
            {**observation(), "source_event_id": 0},
            {**observation(), "pattern": "supernatural"},
        ):
            state, ok, why = detective(observed=observed)
            self.assertFalse(ok, why)
            self.assertFalse(state.get("case_examinations"))
        state, ok, why = detective(day=0)
        self.assertFalse(ok)
        state, ok, why = detective(account=True)
        self.assertFalse(ok)

    def test_same_account_role_switch_and_duplicate_examination_rejected(self):
        state, ok, why = detective()
        self.assertTrue(ok, why)
        same, ok, why = chronicler(state, account=11)
        self.assertFalse(ok)
        self.assertIn("independent account", why)
        self.assertNotIn("case_bulletins", same)
        duplicate, ok, why = detective(state, event=105)
        self.assertFalse(ok)
        self.assertEqual(duplicate, state)

    def test_forged_or_failed_source_and_wrong_profession_rejected(self):
        state, ok, why = detective()
        self.assertTrue(ok, why)
        edits = [
            ("status", "consequence_failed"),
            ("kind", "village.bridge_plaque_culprit_proven"),
            ("id", 999),
        ]
        for field, value in edits:
            forged = source()
            forged[field] = value
            unchanged, ok, why = chronicler(state, signed=forged)
            self.assertFalse(ok, (field, why))
            self.assertEqual(unchanged, state)
        for group, field, value in [
            ("actor", "account_id", 999),
            ("actor", "mask_id", 999),
            ("actor", "mask", "Impostor"),
            ("payload", "professional_calling", "chronicler"),
            ("payload", "location", "Village Square"),
            ("payload", "day", 2),
            ("payload", "hour", True),
            ("payload", "observation_event_id", 777),
            ("consequence", "case_exam_event_id", 999),
            ("consequence", "pattern", "ghost"),
            ("consequence", "finding", "culprit_proven"),
        ]:
            forged = source()
            forged[group][field] = value
            unchanged, ok, why = chronicler(state, signed=forged)
            self.assertFalse(ok, (group, field, why))
            self.assertEqual(unchanged, state)

    def test_physical_witness_and_observation_event_require_strict_identity(self):
        for bad in (11.0, True):
            with self.subTest(account=bad):
                observed = observation()
                observed["witnesses"][0]["account_id"] = bad
                _state, ok, _why = detective(observed=observed)
                self.assertFalse(ok)
        for bad in (111.0, True):
            with self.subTest(mask=bad):
                observed = observation()
                observed["witnesses"][0]["mask_id"] = bad
                self.assertFalse(detective(observed=observed)[1])
        observed = observation()
        observed["day"] = 3.0
        self.assertFalse(detective(observed=observed)[1])
        observed = observation()
        observed["source_event_id"] = 101
        self.assertFalse(detective(observed=observed)[1])
        self.assertFalse(detective(observed=observation(), event=90)[1])

    def test_public_bulletin_requires_exact_signed_integer_source(self):
        state, ok, why = detective()
        self.assertTrue(ok, why)
        for group, field, bad in (
            ("actor", "account_id", 11.0),
            ("actor", "mask_id", 111.0),
            ("payload", "observation_event_id", 90.0),
            ("consequence", "case_exam_event_id", 101.0),
            ("consequence", "observation_event_id", 90.0),
        ):
            with self.subTest(group=group, field=field):
                forged = source()
                forged[group][field] = bad
                changed, ok, _why = chronicler(state, signed=forged)
                self.assertFalse(ok)
                self.assertEqual(changed, state)
        forged = source()
        forged["id"] = 101.0
        self.assertFalse(chronicler(state, signed=forged)[1])
        changed, ok, _why = chronicler(state, event=101)
        self.assertFalse(ok)
        self.assertEqual(changed, state)

    def test_tampered_persisted_examination_cannot_publish(self):
        state, ok, why = detective()
        self.assertTrue(ok, why)
        for key, bad in (("account_id", 11.0),
                         ("mask_id", 111.0),
                         ("event_id", 101.0),
                         ("observation_event_id", 90.0),
                         ("hour", 11.0),
                         ("day", 3.0)):
            with self.subTest(field=key):
                altered = copy.deepcopy(state)
                altered["case_examinations"][0][key] = bad
                changed, ok, _why = chronicler(altered)
                self.assertFalse(ok)
                self.assertEqual(changed, altered)
        altered = copy.deepcopy(state)
        altered["case_examinations"][0]["hour"] = 13
        self.assertFalse(chronicler(altered, hour=12)[1])

    def test_no_publication_without_source_or_with_wrong_time(self):
        state, ok, why = chronicler({})
        self.assertFalse(ok)
        state, ok, why = detective()
        self.assertTrue(ok, why)
        for changes in ({"day": 4}, {"hour": 10}, {"account": True},
                        {"event": 0}):
            _, ok, why = chronicler(state, **changes)
            self.assertFalse(ok, changes)
        signed, ok, why = chronicler(state)
        self.assertTrue(ok, why)
        duplicate, ok, why = chronicler(signed, event=109)
        self.assertFalse(ok)
        self.assertEqual(duplicate, signed)


if __name__ == "__main__":
    unittest.main()
