"""GDD-EDGE-11: source-bound, two-account public-health publication."""
import copy
import json
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "spike/fvillage"))
from world.warning_provenance import verify_healer_source
WELL_MUSHROOM_WARNING_ID = "CIV-HEALTH-0001-WELL-MUSHROOMS"


def signed():
    finding = dict(
        calling="healer", account_id=10, mask_id=100, mask="HealerTester",
        object_id=77, object_key="a cluster of mushrooms", property="toxin",
        value=25, assessment_source="healer_assessment",
        event_id=501, day=2, hour=12,
    )
    event = dict(
        id=501, kind="professional.healer_finding_submitted", status="complete",
        actor=dict(account_id=10, mask_id=100, mask="HealerTester"),
        payload=dict(
            situation_id=WELL_MUSHROOM_WARNING_ID,
            source_object_id=77, source_object_key="a cluster of mushrooms",
            mechanical_property="toxin", mechanical_value=25,
            professional_calling="healer", day=2, hour=12,
            publicity="private", harbinger=False, chronicle_eligible=False,
        ),
    )
    return finding, event


def verify(finding, event, **kwargs):
    return verify_healer_source(
        finding, event, chronicler_account_id=kwargs.get("account", 20),
        day=kwargs.get("day", 2), hour=kwargs.get("hour", 13),
        situation_id=WELL_MUSHROOM_WARNING_ID,
    )


class SignedHealthSourceTests(unittest.TestCase):
    def test_completed_source_accepts_independent_account(self):
        finding, event = signed()
        self.assertEqual(verify(finding, event), (True, None))
        self.assertEqual(verify(*json.loads(json.dumps([finding, event]))), (True, None))
        self.assertEqual(verify(finding, event, day=3, hour=0), (True, None))

    def test_same_account_switching_calling_is_not_cooperation(self):
        finding, event = signed()
        ok, reason = verify(finding, event, account=10)
        self.assertFalse(ok)
        self.assertIn("separate account", reason)

    def test_missing_failed_or_wrong_kind_source(self):
        finding, event = signed()
        self.assertFalse(verify(finding, None)[0])
        for key, value in (
            ("status", "consequence_failed"),
            ("status", "recorded"),
            ("kind", "professional.public_health_warning"),
            ("id", 502),
        ):
            forged = copy.deepcopy(event)
            forged[key] = value
            self.assertFalse(verify(finding, forged)[0], key)

    def test_actor_mask_and_account_must_match_signed_ledger(self):
        finding, event = signed()
        for key, value in (("account_id", 11), ("mask_id", 101), ("mask", "Impostor")):
            forged = copy.deepcopy(event)
            forged["actor"][key] = value
            self.assertFalse(verify(finding, forged)[0], key)
        finding["account_id"] = True
        self.assertFalse(verify(finding, event)[0])

    def test_source_payload_cannot_be_substituted(self):
        finding, event = signed()
        tampering = (
            ("situation_id", "different"),
            ("source_object_id", 78),
            ("source_object_key", "another mushroom"),
            ("mechanical_property", "safe"),
            ("mechanical_value", 0),
            ("professional_calling", "chronicler"),
            ("day", 3), ("hour", 14),
            ("publicity", "public"),
            ("harbinger", True), ("chronicle_eligible", True),
        )
        for key, value in tampering:
            forged = copy.deepcopy(event)
            forged["payload"][key] = value
            self.assertFalse(verify(finding, forged)[0], key)

    def test_finding_row_is_not_an_authority(self):
        finding, event = signed()
        for key, value in (
            ("event_id", 502), ("object_id", 78), ("object_key", "fake"),
            ("property", "safe"), ("value", 99), ("calling", "merchant"),
            ("mask_id", 200), ("day", 3), ("hour", 14),
        ):
            forged = copy.deepcopy(finding)
            forged[key] = value
            self.assertFalse(verify(forged, event)[0], key)

    def test_future_clock_and_invalid_identifiers_rejected(self):
        finding, event = signed()
        self.assertFalse(verify(finding, event, day=2, hour=11)[0])
        self.assertFalse(verify(finding, event, day=1, hour=23)[0])
        self.assertFalse(verify(finding, event, account=True)[0])
        self.assertFalse(verify(finding, event, hour=24)[0])
        self.assertFalse(verify(finding, event, day=0)[0])

    def test_validation_does_not_mutate_persisted_state(self):
        finding, event = signed()
        original = copy.deepcopy((finding, event))
        self.assertTrue(verify(finding, event)[0])
        self.assertEqual((finding, event), original)


if __name__ == "__main__":
    unittest.main()
