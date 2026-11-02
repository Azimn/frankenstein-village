"""B13: original completed-ledger proof for public bridge and finite kits."""
import copy
import json
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "spike/fvillage"))
from world import bridge_provenance as proof


def fixture():
    state = {
        "resolution": {"choice": "preserve", "account_id": 12,
                       "mask_id": 44, "mask": "Investigator",
                       "day": 2, "hour": 19, "event_id": 90},
        "checks": [{"account_id": 21, "mask_id": 60, "day": 2,
                    "event_id": 91}],
    }
    events = {
        81: {"id": 81, "kind": "village.bridge_material_collected",
             "status": "complete",
             "actor": {"account_id": 10, "mask_id": 40, "mask": "Carrier"},
             "payload": {"choice": "preserve", "location": "Market Lane",
                         "day": 2, "hour": 18},
             "consequence": {"item_id": 200, "choice": "preserve",
                             "market_table_id": 500, "remaining": 1}},
        90: {"id": 90, "kind": "village.bridge_response", "status": "complete",
             "actor": {"account_id": 12, "mask_id": 44, "mask": "Investigator"},
             "payload": {"choice": "preserve", "location": "The Old Stone Bridge",
                         "day": 2, "hour": 19},
             "consequence": {"choice": "preserve", "signed_upkeep": 0,
                             "consumed_item_id": 200, "source_event_id": 81,
                             "bridge_room_id": 300}},
        91: {"id": 91, "kind": "village.bridge_upkeep", "status": "complete",
             "actor": {"account_id": 21, "mask_id": 60, "mask": "Keeper"},
             "payload": {"choice": None, "location": "The Old Stone Bridge",
                         "day": 2, "hour": 20},
             "consequence": {"choice": "preserve", "signed_upkeep": 1}},
    }
    return state, events


def verify(state, events):
    return proof.verified_state(
        state, lambda event_id: events.get(event_id), bridge_room_id=300
    )


class BridgeProvenanceTests(unittest.TestCase):
    def test_real_two_account_response_and_upkeep_survive_json_restart(self):
        state, events = fixture()
        state = json.loads(json.dumps(state))
        events = {int(k): v for k, v in
                  json.loads(json.dumps(events)).items()}
        safe, valid = verify(state, events)
        self.assertTrue(valid)
        self.assertEqual(safe, state)
        self.assertIn("canvas cover", proof.public_line(
            state, lambda ident: events.get(ident), bridge_room_id=300))
        self.assertIn("1 signed upkeep", proof.public_line(
            state, lambda ident: events.get(ident), bridge_room_id=300))

    def test_response_cannot_be_signed_by_mutable_room_data(self):
        state, events = fixture()
        for event_id, group, key, value in (
            (90, None, "status", "consequence_failed"),
            (90, None, "kind", "village.bridge_other"),
            (90, "actor", "account_id", 999),
            (90, "actor", "mask_id", 999),
            (90, "actor", "mask", "Impostor"),
            (90, "payload", "location", "Village Square"),
            (90, "payload", "day", 3),
            (90, "payload", "hour", True),
            (90, "consequence", "bridge_room_id", 999),
            (90, "consequence", "consumed_item_id", 999),
            (90, "consequence", "source_event_id", 999),
            (81, None, "status", "consequence_failed"),
            (81, None, "kind", "village.fake_collection"),
            (81, "payload", "choice", "display"),
            (81, "payload", "location", "Village Square"),
            (81, "consequence", "item_id", 999),
            (81, "consequence", "market_table_id", False),
        ):
            with self.subTest(event=event_id, field=key):
                forged = copy.deepcopy(events)
                target = forged[event_id] if group is None else forged[event_id][group]
                target[key] = value
                safe, valid = verify(state, forged)
                self.assertFalse(valid)
                self.assertIsNone(safe["resolution"])
                self.assertNotIn("canvas cover", proof.public_line(
                    state, lambda ident: forged.get(ident),
                    bridge_room_id=300))

    def test_missing_events_invalid_ids_and_rewound_clock_fail_closed(self):
        state, events = fixture()
        for missing in (81, 90):
            forged = copy.deepcopy(events)
            del forged[missing]
            self.assertFalse(verify(state, forged)[1])
        for field in ("account_id", "mask_id", "day", "event_id"):
            for value in (True, 90.0, "90", 0, -1):
                with self.subTest(field=field, value=value):
                    forged = copy.deepcopy(state)
                    forged["resolution"][field] = value
                    self.assertFalse(verify(forged, events)[1])
        forged = copy.deepcopy(events)
        forged[81]["payload"]["day"] = 3
        self.assertFalse(verify(state, forged)[1])

    def test_invalid_upkeep_is_not_a_public_inspection_or_future_authority(self):
        state, events = fixture()
        for event_id, group, key, value in (
            (91, None, "status", "consequence_failed"),
            (91, None, "kind", "village.bridge_other"),
            (91, "actor", "account_id", 999),
            (91, "payload", "location", "Village Square"),
            (91, "payload", "day", 1),
            (91, "consequence", "choice", "display"),
        ):
            with self.subTest(field=key):
                forged = copy.deepcopy(events)
                target = forged[event_id] if group is None else forged[event_id][group]
                target[key] = value
                safe, valid = verify(state, forged)
                self.assertFalse(valid)
                self.assertIsNotNone(safe["resolution"])
                self.assertEqual(safe["checks"], [])
                self.assertNotIn("signed upkeep", proof.public_line(
                    state, lambda ident: forged.get(ident),
                    bridge_room_id=300))
        forged = copy.deepcopy(state)
        forged["checks"][0]["event_id"] = True
        self.assertFalse(verify(forged, events)[1])

    def test_corrupt_saved_upkeep_container_never_crashes_public_room(self):
        state, events = fixture()
        for malformed in (7, {"event_id": 91}, "not-a-list", True):
            with self.subTest(malformed=malformed):
                forged = copy.deepcopy(state)
                forged["checks"] = malformed
                safe, valid = verify(forged, events)
                self.assertFalse(valid)
                self.assertIsNotNone(safe["resolution"])
                self.assertEqual(safe["checks"], [])
                self.assertIn("cannot be verified", proof.public_line(
                    forged, lambda ident: events.get(ident),
                    bridge_room_id=300))

    def test_real_giftable_kit_requires_completed_physical_collection(self):
        _, events = fixture()
        kit = {"item_id": 200, "source_event_id": 81,
               "source_day": 2}
        self.assertTrue(proof.verified_kit(
            kit, lambda ident: events.get(ident), choice="preserve",
            market_table_id=500, current_day=2))
        self.assertTrue(proof.verified_kit(
            kit, lambda ident: events.get(ident), choice="preserve",
            market_table_id=500, current_day=3))
        for bad in (
            {"source_event_id": True},
            {"source_event_id": 81.0},
            {"source_event_id": 999},
            {"item_id": 201},
            {"source_day": 3},
        ):
            with self.subTest(bad=bad):
                self.assertFalse(proof.verified_kit(
                    {**kit, **bad}, lambda ident: events.get(ident),
                    choice="preserve", market_table_id=500, current_day=2))
        self.assertFalse(proof.verified_kit(
            kit, lambda ident: events.get(ident), choice="preserve",
            market_table_id=500, current_day=1))
        self.assertFalse(proof.verified_kit(
            kit, lambda ident: events.get(ident), choice="display",
            market_table_id=500, current_day=2))


if __name__ == "__main__":
    unittest.main()
