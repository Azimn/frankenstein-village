"""EDGE-27: real clinic patient, independent professional actions and consent."""
import copy
import json
import sys
import unittest
from collections import UserDict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "spike/fvillage"))
from world import clinic_comfort_edge27 as rules


def fixture(day=1, hour=21):
    treatment = dict(day=day, hour=hour, account_id=11, mask_id=101,
                     mask="HealerTester", event_id=30, method="compress",
                     assessment_event_id=29)
    event = dict(
        id=30, kind="village.clinic_treat", status="complete",
        actor=dict(account_id=11, mask_id=101, mask="HealerTester"),
        payload=dict(day=day, hour=hour, professional_calling="healer",
                     method="compress"),
        consequence=dict(room_id=70, assessment_event_id=29,
                         patient_condition="cold"))
    return treatment, event


def invite(raw=None, treatment=None, treatment_event=None, **changes):
    t, e = fixture()
    props = dict(day=1, hour=21, account_id=11, mask_id=101,
                 mask="HealerTester", event_id=31, room_id=70, cot_id=71,
                 treatment=t if treatment is None else treatment,
                 treatment_event=e if treatment_event is None else treatment_event)
    props.update(changes)
    return rules.invite(raw, **props)


def signed_invitation(state):
    invitation = state["invitation"]
    return dict(
        id=invitation["event_id"], kind="village.clinic_music_invited",
        status="complete",
        actor=dict(account_id=invitation["account_id"],
                   mask_id=invitation["mask_id"], mask=invitation["mask"]),
        payload=dict(day=invitation["day"], hour=invitation["hour"],
                     professional_calling="healer", cot_id=invitation["cot_id"],
                     source_healer_event_id=invitation["source_event_id"]),
        consequence=dict(room_id=invitation["room_id"],
                         cot_id=invitation["cot_id"],
                         source_healer_event_id=invitation["source_event_id"],
                         consent="accepted"))


def music(state, event=None, **changes):
    props = dict(day=1, hour=21, account_id=12, mask_id=102,
                 mask="PerformerTester", event_id=32, room_id=70, cot_id=71,
                 invitation_event=signed_invitation(state) if event is None else event)
    props.update(changes)
    return rules.offer(state, **props)


class ClinicMusicRules(unittest.TestCase):
    def test_independent_two_account_consent_and_music(self):
        state, ok, reason = invite()
        self.assertTrue(ok, reason)
        state, ok, reason = music(state)
        self.assertTrue(ok, reason)
        self.assertEqual(state["music"]["source_event_id"], 31)
        self.assertEqual(state["music"]["healer_account_id"], 11)
        self.assertIn("not a treatment", rules.public_lines(state, 1))
        self.assertNotIn("cold", rules.public_lines(state, 1))
        self.assertNotIn("HealerTester", rules.public_lines(state, 1))

    def test_requires_real_completed_healer_treatment(self):
        t, e = fixture()
        for changed in (
            dict(e, status="consequence_failed"),
            dict(e, kind="village.clinic_assess"),
            dict(e, id=999),
            dict(e, actor=dict(e["actor"], account_id=44)),
            dict(e, payload=dict(e["payload"], method="rest")),
            dict(e, consequence=dict(e["consequence"], room_id=999)),
            dict(e, consequence=dict(e["consequence"], assessment_event_id=999)),
            dict(e, consequence=None),
        ):
            with self.subTest(event=changed):
                state, ok, _ = invite(treatment=t, treatment_event=changed)
                self.assertFalse(ok)
                self.assertIsNone(state["invitation"])

    def test_healer_cannot_impersonate_treater_or_repeat_invitation(self):
        state, ok, _ = invite(account_id=13)
        self.assertFalse(ok)
        state, ok, _ = invite(mask_id=999)
        self.assertFalse(ok)
        state, ok, _ = invite()
        self.assertTrue(ok)
        again, ok, _ = invite(state, event_id=33)
        self.assertFalse(ok)
        self.assertEqual(again, state)

    def test_performer_cannot_self_sign_or_switch_masks(self):
        state, ok, _ = invite()
        self.assertTrue(ok)
        for props in (
            dict(account_id=11), dict(mask_id=101), dict(account_id=True),
            dict(mask_id=-1), dict(event_id=31), dict(event_id=30),
        ):
            with self.subTest(props=props):
                newer, ok, _ = music(state, **props)
                self.assertFalse(ok)
                self.assertIsNone(newer["music"])

    def test_music_requires_signed_cot_specific_consent(self):
        state, ok, _ = invite()
        self.assertTrue(ok)
        valid = signed_invitation(state)
        forged = (
            dict(valid, status="consequence_failed"),
            dict(valid, id=800),
            dict(valid, actor=dict(valid["actor"], account_id=12)),
            dict(valid, payload=dict(valid["payload"], cot_id=900)),
            dict(valid, consequence=dict(valid["consequence"], consent="refused")),
            dict(valid, consequence=dict(valid["consequence"], room_id=900)),
            dict(valid, consequence=None),
        )
        for event in forged:
            with self.subTest(event=event):
                newer, ok, _ = music(state, event=event)
                self.assertFalse(ok)
                self.assertIsNone(newer["music"])

    def test_no_remote_or_future_or_duplicate_music(self):
        state, ok, _ = invite()
        self.assertTrue(ok)
        for props in (dict(cot_id=72), dict(room_id=72),
                      dict(day=2), dict(hour=20)):
            with self.subTest(props=props):
                _, ok, _ = music(state, **props)
                self.assertFalse(ok)
        state, ok, _ = music(state)
        self.assertTrue(ok)
        again, ok, _ = music(state, event_id=40)
        self.assertFalse(ok)
        self.assertEqual(again, state)

    def test_daily_patient_does_not_inherit_consent(self):
        state, ok, _ = invite()
        self.assertTrue(ok)
        state, ok, _ = music(state)
        self.assertTrue(ok)
        tomorrow = rules.refresh(state, 2)
        self.assertIsNone(tomorrow["invitation"])
        self.assertIsNone(tomorrow["music"])
        self.assertEqual(tomorrow["history"][-1]["day"], 1)
        _, ok, _ = music(tomorrow, day=2)
        self.assertFalse(ok)
        self.assertIn("After today's signed care", rules.public_lines(tomorrow, 2))

    def test_json_restart_and_evennia_mapping_normalization(self):
        state, ok, _ = invite()
        self.assertTrue(ok)
        state, ok, _ = music(state)
        self.assertTrue(ok)
        stored = json.loads(json.dumps(state))
        restored = rules.normalize(UserDict(stored))
        self.assertEqual(restored["music"]["event_id"], 32)
        self.assertEqual(restored["invitation"]["source_event_id"], 30)
        self.assertEqual(restored, stored)

    def test_corrupt_history_or_unsupported_clock_fails_closed(self):
        state, ok, _ = invite()
        self.assertTrue(ok)
        for props in (dict(day=True), dict(hour=24), dict(hour=-1),
                      dict(event_id=False)):
            with self.subTest(props=props):
                _, ok, _ = invite(None, **props)
                self.assertFalse(ok)
        corrupt = copy.deepcopy(state)
        corrupt["invitation"]["cot_id"] = -1
        self.assertIsNone(rules.normalize(corrupt)["invitation"])
        self.assertIsNone(rules.normalize({"day": 1, "invitation": "forged"})["invitation"])
        self.assertFalse(rules.invitation_valid({}, {}))

    def test_bounded_history(self):
        state, ok, _ = invite()
        self.assertTrue(ok)
        for day in range(2, 60):
            state = rules.refresh(state, day)
            self.assertEqual(state["day"], day)
            self.assertLessEqual(len(state["history"]), rules.MAX_HISTORY)
        self.assertEqual(state["history"][-1]["day"], 1)


if __name__ == "__main__":
    unittest.main()
