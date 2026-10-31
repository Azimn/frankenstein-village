"""EDGE-27: real clinic patient, independent professional actions and consent."""
import copy
import json
import sys
import unittest
from collections import UserDict
from collections.abc import Mapping
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "spike/fvillage"))
from world import clinic_comfort_edge27 as rules, clinic_state


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
                 treatment_event=e if treatment_event is None else treatment_event,
                 visitor_choice="accepts")
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
                     professional_calling="healer",
                     room_id=invitation["room_id"], cot_id=invitation["cot_id"],
                     source_healer_event_id=invitation["source_event_id"],
                     visitor_choice=invitation["visitor_choice"]),
        consequence=dict(room_id=invitation["room_id"],
                         cot_id=invitation["cot_id"],
                         day=invitation["day"], hour=invitation["hour"],
                         source_event_id=invitation["source_event_id"],
                         source_healer_event_id=invitation["source_event_id"],
                         consent="accepted", outcome="invited",
                         visitor_choice=invitation["visitor_choice"]))


def music(state, event=None, **changes):
    props = dict(day=1, hour=21, account_id=12, mask_id=102,
                 mask="PerformerTester", event_id=32, room_id=70, cot_id=71,
                 invitation_event=(signed_invitation(state) if event is None
                                   and state.get("invitation") else event))
    props.update(changes)
    return rules.offer(state, **props)




def signed_music(state):
    record = state["music"]
    return dict(
        id=record["event_id"], kind="village.clinic_music_offered",
        status="complete",
        actor=dict(account_id=record["account_id"],
                   mask_id=record["mask_id"], mask=record["mask"]),
        payload=dict(day=record["day"], hour=record["hour"],
                     professional_calling="performer",
                     room_id=record["room_id"], cot_id=record["cot_id"],
                     source_healer_event_id=state["invitation"]["source_event_id"]),
        consequence=dict(room_id=record["room_id"], cot_id=record["cot_id"],
                         day=record["day"], hour=record["hour"],
                         source_event_id=record["source_event_id"],
                         source_healer_event_id=state["invitation"]["source_event_id"],
                         consent="respected", outcome="music_offered"))


def public(state, *, events=None, treatment=None, treatment_event=None,
           room_id=70, cot_id=71, day=1):
    original_treatment, original_event = fixture()
    if events is None:
        events = {}
        if isinstance(state.get("invitation"), Mapping):
            events[state["invitation"]["event_id"]] = signed_invitation(state)
        if isinstance(state.get("music"), Mapping):
            events[state["music"]["event_id"]] = signed_music(state)
    return rules.public_lines(
        state, day, event_lookup=events.get,
        treatment=original_treatment if treatment is None else treatment,
        treatment_event=original_event if treatment_event is None else treatment_event,
        room_id=room_id, cot_id=cot_id)


class ClinicMusicRules(unittest.TestCase):
    def test_independent_two_account_consent_and_music(self):
        state, ok, reason = invite()
        self.assertTrue(ok, reason)
        state, ok, reason = music(state)
        self.assertTrue(ok, reason)
        self.assertEqual(state["music"]["source_event_id"], 31)
        self.assertEqual(state["music"]["healer_account_id"], 11)
        self.assertIn("not a treatment", public(state))
        self.assertNotIn("cold", public(state))
        self.assertNotIn("HealerTester", public(state))

    def test_anonymous_visitor_independently_accepts_declines_or_is_unavailable(self):
        # This choice belongs to the new daily visitor, never to the Healer.
        self.assertEqual(clinic_state.music_preference(1), "accepts")
        self.assertEqual(clinic_state.music_preference(2), "declines")
        self.assertEqual(clinic_state.music_preference(3), "unavailable")
        self.assertIsNone(clinic_state.music_preference(True))
        self.assertEqual(clinic_state.refresh(None, 2)["music_preference"], "declines")
        forged_case = clinic_state.refresh(None, 2)
        forged_case["music_preference"] = "accepts"
        self.assertEqual(clinic_state.normalize(forged_case)["music_preference"], "declines")
        self.assertEqual(clinic_state.normalize(
            json.loads(json.dumps(clinic_state.refresh(None, 3)))
        )["music_preference"], "unavailable")
        for day, choice, expected in (
            (2, "declines", "declines music"),
            (3, "unavailable", "unavailable to answer"),
        ):
            with self.subTest(day=day):
                treatment, event = fixture(day=day)
                state, ok, reason = invite(
                    day=day, visitor_choice=choice,
                    treatment=treatment, treatment_event=event,
                )
                self.assertFalse(ok)
                self.assertIn(expected, reason)
                self.assertIsNone(state["invitation"])
                self.assertIsNone(state["music"])
                # A forged Healer-supplied "accepts" cannot override the patient.
                _, ok, reason = invite(
                    day=day, visitor_choice="accepts",
                    treatment=treatment, treatment_event=event,
                )
                self.assertFalse(ok)
                self.assertIn("independent preference", reason)
                _, ok, _ = music(state, day=day)
                self.assertFalse(ok)

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
            dict(valid, payload=dict(valid["payload"], visitor_choice="declines")),
            dict(valid, consequence=dict(valid["consequence"], visitor_choice="declines")),
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


    def test_public_readback_requires_actual_three_signed_events(self):
        state, ok, _ = invite()
        self.assertTrue(ok)
        state, ok, _ = music(state)
        self.assertTrue(ok)
        signed = public(state)
        self.assertIn("signed music event 32, consent event 31", signed)
        self.assertNotIn("cold", signed)
        self.assertNotIn("HealerTester", signed)
        self.assertNotIn("PerformerTester", signed)
        self.assertIn("cannot be verified", rules.public_lines(state, 1))
        self.assertIn("cannot be verified", public(state, events={}))
        self.assertIn("cannot be verified", public(state, room_id=72))
        self.assertIn("cannot be verified", public(state, cot_id=72))
        self.assertIn("cannot be verified", public(state, treatment={}))
        self.assertIn("cannot be verified", public(
            state, treatment_event=dict(fixture()[1], status="consequence_failed")))
        persisted = UserDict(json.loads(json.dumps(state)))
        self.assertIn("signed music event 32", public(persisted))
        self.assertNotIn("signed music", public(persisted, events={}))
        self.assertNotIn("signed music", public(state, day=2))

    def test_public_readback_rejects_forged_invitation_and_music_events(self):
        state, ok, _ = invite()
        self.assertTrue(ok)
        state, ok, _ = music(state)
        self.assertTrue(ok)
        invitation = signed_invitation(state)
        offered = signed_music(state)
        tampered_invitation = (
            dict(invitation, id=999991),
            dict(invitation, status="consequence_failed"),
            dict(invitation, actor=dict(invitation["actor"], account_id=90)),
            dict(invitation, payload=dict(invitation["payload"], cot_id=72)),
            dict(invitation, payload=dict(invitation["payload"], room_id=72)),
            dict(invitation, consequence=dict(invitation["consequence"],
                                               source_event_id=900)),
            dict(invitation, consequence=dict(invitation["consequence"],
                                               consent="refused")),
            dict(invitation, payload=dict(invitation["payload"],
                                          visitor_choice="declines")),
            dict(invitation, consequence=dict(invitation["consequence"],
                                              visitor_choice="declines")),
            dict(invitation, consequence=dict(invitation["consequence"],
                                               outcome="unknown")),
            dict(invitation, consequence=dict(invitation["consequence"],
                                               hour=20)),
        )
        for bad in tampered_invitation:
            with self.subTest(invitation=bad):
                text = public(state, events={31: bad, 32: offered})
                self.assertIn("cannot be verified", text)
                self.assertNotIn("signed music event", text)
        tampered_music = (
            dict(offered, id=999992),
            dict(offered, status="consequence_failed"),
            dict(offered, kind="village.clinic_treat"),
            dict(offered, actor=dict(offered["actor"], mask_id=99)),
            dict(offered, payload=dict(offered["payload"], cot_id=72)),
            dict(offered, payload=dict(offered["payload"], day=2)),
            dict(offered, consequence=dict(offered["consequence"],
                                            source_event_id=900)),
            dict(offered, consequence=dict(offered["consequence"],
                                            consent="refused")),
            dict(offered, consequence=dict(offered["consequence"],
                                            outcome="treatment")),
            dict(offered, consequence=dict(offered["consequence"],
                                            hour=20)),
        )
        for bad in tampered_music:
            with self.subTest(music=bad):
                text = public(state, events={31: invitation, 32: bad})
                self.assertIn("cannot be verified", text)
                self.assertNotIn("signed music event", text)

    def test_public_readback_handles_absent_sources_corrupt_cot_and_ledger_errors(self):
        state, ok, _ = invite()
        self.assertTrue(ok)
        self.assertIn("accepted a short", public(state))
        self.assertIn("cannot be verified", public(state, events={}))
        state, ok, _ = music(state)
        self.assertTrue(ok)
        canonical = {31: signed_invitation(state), 32: signed_music(state)}
        damaged = copy.deepcopy(state)
        damaged["music"]["event_id"] = 999992
        self.assertIn("cannot be verified", public(damaged, events=canonical))
        damaged = copy.deepcopy(state)
        damaged["invitation"]["cot_id"] = 72
        self.assertIn("cannot be verified", public(damaged))
        damaged = copy.deepcopy(state)
        damaged["music"] = "forged"
        self.assertIn("cannot be verified", public(damaged))
        self.assertIn("cannot be verified", rules.public_lines(
            state, 1, event_lookup=lambda _: (_ for _ in ()).throw(
                RuntimeError("ledger unavailable")),
            treatment=fixture()[0], treatment_event=fixture()[1],
            room_id=70, cot_id=71))
        self.assertNotIn("cold", public(state, events={}))

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
