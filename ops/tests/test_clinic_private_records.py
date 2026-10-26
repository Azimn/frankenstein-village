"""GDD §19 T-08: a professional role is not blanket consent to private care notes."""
import copy
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "spike/fvillage"))
from world import clinic_state as clinic


def actor(day=1, event=101, aid=9, mid=90, mask="AssessingHealer"):
    return dict(day=day, hour=20, account_id=aid, mask_id=mid,
                mask=mask, event_id=event)


class ClinicPrivateRecordTests(unittest.TestCase):
    def test_public_board_does_not_publish_diagnosis_clinician_or_history(self):
        state, ok, reason = clinic.assess(None, **actor())
        self.assertTrue(ok, reason)
        state, ok, reason = clinic.treat(state, method="compress", **actor(event=102))
        self.assertTrue(ok, reason)
        public = clinic.public_lines(state, 1).lower()
        for private in ("cold", "sprain", "fever", "assessinghealer",
                        "treatment: compress", "used compress", "less suited", "event 101", "event 102"):
            with self.subTest(private=private):
                self.assertNotIn(private, public)
        self.assertIn("visiting patient", public)
        self.assertIn("care", public)
        archived = clinic.refresh(state, 2)
        posted = clinic.public_lines(archived, 2).lower()
        self.assertNotIn("last archived patient", posted)
        self.assertNotIn("cold", posted)
        self.assertNotIn("assessinghealer", posted)

    def test_profession_alone_cannot_read_records_without_patient_permission(self):
        state, ok, reason = clinic.assess(None, **actor())
        self.assertTrue(ok, reason)
        content = clinic.private_lines(state, 1, account_id=9, mask_id=90)
        self.assertIn("permission", content.lower())
        self.assertNotIn("cold", content.lower())
        for aid, mid in ((10, 100), (9, 999)):
            content = clinic.private_lines(state, 1, account_id=aid, mask_id=mid)
            self.assertNotIn("cold", content.lower())

    def test_permission_is_signed_patient_specific_and_actor_specific(self):
        state, ok, reason = clinic.assess(None, **actor())
        self.assertTrue(ok, reason)
        allowed, ok, reason = clinic.grant_records_permission(state, **actor(event=103))
        self.assertTrue(ok, reason)
        self.assertEqual(allowed["records_permission"]["account_id"], 9)
        self.assertEqual(allowed["records_permission"]["mask_id"], 90)
        self.assertEqual(allowed["records_permission"]["event_id"], 103)
        authorized = clinic.private_lines(allowed, 1, account_id=9, mask_id=90)
        self.assertIn("cold", authorized.lower())
        self.assertIn("event 101", authorized.lower())
        other = clinic.private_lines(allowed, 1, account_id=17, mask_id=170)
        self.assertNotIn("cold", other.lower())
        self.assertNotIn("assessinghealer", other.lower())
        wrong_character_same_account = clinic.private_lines(
            allowed, 1, account_id=9, mask_id=999)
        self.assertNotIn("cold", wrong_character_same_account.lower())
        again, ok, reason = clinic.grant_records_permission(
            allowed, **actor(event=104))
        self.assertFalse(ok)
        self.assertEqual(again, allowed)

    def test_permission_requires_real_assessment_not_a_profession_title(self):
        empty, ok, reason = clinic.grant_records_permission(
            None, **actor(event=130))
        self.assertFalse(ok)
        self.assertIn("assessment", reason.lower())
        self.assertIsNone(empty["records_permission"])
        state, ok, reason = clinic.assess(None, **actor())
        self.assertTrue(ok, reason)
        candidate, ok, reason = clinic.grant_records_permission(
            state, **actor(event=131, aid=90, mid=900, mask="OtherHealer"))
        self.assertFalse(ok)
        self.assertIsNone(candidate["records_permission"])
        self.assertEqual(candidate, state)

    def test_day_change_expiry_and_history_no_private_consent_spill(self):
        state, ok, _ = clinic.assess(None, **actor())
        state, ok, _ = clinic.grant_records_permission(state, **actor(event=103))
        self.assertTrue(ok)
        tomorrow = clinic.refresh(state, 2)
        self.assertIsNone(tomorrow["records_permission"])
        notes = clinic.private_lines(tomorrow, 2, account_id=9, mask_id=90)
        self.assertNotIn("cold", notes.lower())
        self.assertNotIn("assessinghealer", notes.lower())
        original = copy.deepcopy(state)
        tomorrow["history"].append({"bad": True})
        self.assertEqual(state, original)

    def test_reject_invalid_or_forged_patient_permission_ids(self):
        state, ok, _ = clinic.assess(None, **actor())
        for aid, mid, event in ((True, 90, 106), (9, False, 107), (9, 90, -1),
                                (9, 90, "not-an-event")):
            signed, ok, error = clinic.grant_records_permission(
                state, **actor(event=event, aid=aid, mid=mid))
            self.assertFalse(ok)
            self.assertEqual(signed, state)
            self.assertTrue(error)


if __name__ == "__main__":
    unittest.main()
