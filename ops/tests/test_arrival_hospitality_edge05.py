"""GDD-EDGE-05: independent source-verified Wanderer and Innkeep arrival."""
import copy
import json
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "spike/fvillage"))
from world import arrival_hospitality as arrival, soup_state


def fixture():
    state = soup_state.archive(
        None, 1, maker_id=21, maker="InnkeepTester",
        source_event_id=60, cook_event_id=61,
        recipe=soup_state.produce("barley", "salt", warmed=False),
    )
    route = {
        "id": 80, "kind": "village.route_passability_observed",
        "status": "complete",
        "actor": {"account_id": 31, "mask_id": 32, "mask": "WandererTester"},
        "payload": {"site": "red_cord", "role": "wanderer",
                    "action": "passability", "location": "The Northern Treeline",
                    "day": 1, "hour": 21},
        "consequence": {"site": "red_cord", "role": "wanderer",
                        "action": "passability", "day": 1,
                        "square_room_id": 2, "cord_object_id": 9,
                        "interpretation": "unmarked", "caution_marked": False},
    }
    cooked = {
        "id": 61, "kind": "professional.innkeep_soup_cooked",
        "status": "complete",
        "actor": {"account_id": 20, "mask_id": 21, "mask": "InnkeepTester"},
        "payload": {"day": 1, "hour": 21, "base": "barley",
                    "seasoning": "salt", "prep_event_id": 60,
                    "packet_id": 10},
        "consequence": {"bowl_id": 77, "pantry_room_id": 3,
                        "source_event_id": 60},
    }
    kw = {
        "day": 1, "hour": 21,
        "innkeep_account_id": 20, "innkeep_mask_id": 21,
        "wanderer_account_id": 31, "wanderer_mask_id": 32,
        "wanderer_mask": "WandererTester",
        "route_entry": {"event_id": 80, "account_id": 31,
                        "mask": "WandererTester", "site": "red_cord",
                        "action": "passability", "observation": "unmarked"},
        "route_event": route, "bowl_event": cooked,
        "bowl_id": 77, "square_room_id": 2, "tavern_room_id": 3,
        "event_id": 90,
    }
    return state, kw


class ArrivalHospitalityTests(unittest.TestCase):
    def test_two_accounts_transfer_signed_meal_and_survive_json_restart(self):
        state, kw = fixture()
        result, ok, reason = arrival.welcome(state, **kw)
        self.assertTrue(ok, reason)
        self.assertEqual(state["history"][0].get("arrival_welcome"), None)
        receipt = result["history"][0]["arrival_welcome"]
        self.assertEqual(receipt["route_event_id"], 80)
        self.assertEqual(receipt["cook_event_id"], 61)
        self.assertEqual(receipt["service"], "physical_bowl_transferred")
        persisted = json.loads(json.dumps(result))
        self.assertEqual(
            soup_state.pantry(persisted, 2)["history"][0]["arrival_welcome"],
            receipt,
        )
        _, accepted, reason = arrival.welcome(persisted, **kw)
        self.assertFalse(accepted)
        self.assertIn("already", reason)

    def test_same_account_and_invalid_id_rejected(self):
        state, kw = fixture()
        kw["wanderer_account_id"] = 20
        self.assertFalse(arrival.welcome(state, **kw)[1])
        state, kw = fixture()
        kw["bowl_id"] = True
        self.assertFalse(arrival.welcome(state, **kw)[1])

    def test_forged_route_and_wrong_profession_rejected(self):
        for key, value in (("kind", "village.route_protected"),
                           ("status", "consequence_failed")):
            state, kw = fixture()
            kw["route_event"][key] = value
            self.assertFalse(arrival.welcome(state, **kw)[1])
        state, kw = fixture()
        kw["route_event"]["payload"]["role"] = "hound"
        self.assertFalse(arrival.welcome(state, **kw)[1])

    def test_mismatched_route_actor_mask_and_square_rejected(self):
        for field, value in (("account_id", 99), ("mask_id", 99),
                             ("mask", "Forged")):
            state, kw = fixture()
            kw["route_event"]["actor"][field] = value
            self.assertFalse(arrival.welcome(state, **kw)[1])
        state, kw = fixture()
        kw["route_event"]["consequence"]["square_room_id"] = 99
        self.assertFalse(arrival.welcome(state, **kw)[1])

    def test_stale_future_route_and_clock_rewind_rejected(self):
        state, kw = fixture()
        kw["route_event"]["payload"]["hour"] = 22
        self.assertFalse(arrival.welcome(state, **kw)[1])
        state, kw = fixture()
        kw["day"] = 2
        self.assertFalse(arrival.welcome(state, **kw)[1])
        state, kw = fixture()
        kw["hour"] = -1
        self.assertFalse(arrival.welcome(state, **kw)[1])

    def test_forged_bowl_and_failed_cook_rejected(self):
        for key, value in (("kind", "village.stage_perform"),
                           ("status", "consequence_failed")):
            state, kw = fixture()
            kw["bowl_event"][key] = value
            self.assertFalse(arrival.welcome(state, **kw)[1])
        state, kw = fixture()
        kw["bowl_event"]["consequence"]["bowl_id"] = 999
        self.assertFalse(arrival.welcome(state, **kw)[1])

    def test_wrong_innkeep_and_wrong_cooked_batch_rejected(self):
        state, kw = fixture()
        kw["bowl_event"]["actor"]["account_id"] = 99
        self.assertFalse(arrival.welcome(state, **kw)[1])
        state, kw = fixture()
        kw["bowl_event"]["payload"]["prep_event_id"] = 99
        self.assertFalse(arrival.welcome(state, **kw)[1])

    def test_original_observation_must_match_signed_route_consequence(self):
        # A mutable Square projection must not rewrite the actual witnessed
        # cord condition recorded in the completed canonical world event.
        state, kw = fixture()
        kw["route_entry"]["observation"] = "marked_caution"
        self.assertFalse(arrival.welcome(state, **kw)[1])
        self.assertNotIn("arrival_welcome", state["history"][0])

        state, kw = fixture()
        kw["route_event"]["consequence"]["interpretation"] = "marked_caution"
        self.assertFalse(arrival.welcome(state, **kw)[1])

        state, kw = fixture()
        kw["route_event"]["consequence"]["caution_marked"] = True
        self.assertFalse(arrival.welcome(state, **kw)[1])

        # A legitimate observed marker remains a valid distinct account path.
        state, kw = fixture()
        kw["route_entry"]["observation"] = "marked_caution"
        kw["route_event"]["consequence"]["interpretation"] = "marked_caution"
        kw["route_event"]["consequence"]["caution_marked"] = True
        result, ok, reason = arrival.welcome(state, **kw)
        self.assertTrue(ok, reason)
        self.assertEqual(result["history"][0]["arrival_welcome"]["route_observation"],
                         "marked_caution")

    def test_signed_identity_types_and_days_cannot_be_substituted(self):
        # Python bool/float equality must not turn a malformed source into
        # an authenticated account, object, world event or clock day.
        mutations = (
            ("route_event", "actor", "account_id", 31.0),
            ("route_event", "actor", "mask_id", 32.0),
            ("route_event", "payload", "day", True),
            ("route_event", "consequence", "day", 1.0),
            ("route_event", "consequence", "square_room_id", 2.0),
            ("route_event", "consequence", "cord_object_id", True),
            ("bowl_event", "actor", "account_id", 20.0),
            ("bowl_event", "actor", "mask_id", 21.0),
            ("bowl_event", "payload", "day", True),
            ("bowl_event", "consequence", "bowl_id", 77.0),
            ("bowl_event", "consequence", "pantry_room_id", 3.0),
        )
        for root, part, key, bad in mutations:
            with self.subTest(root=root, part=part, key=key, bad=bad):
                state, kw = fixture()
                kw[root][part][key] = bad
                changed, ok, _reason = arrival.welcome(state, **kw)
                self.assertFalse(ok)
                self.assertEqual(changed["history"], state["history"])

        for key, bad in (("event_id", 80.0), ("account_id", 31.0)):
            with self.subTest(route_entry=key):
                state, kw = fixture()
                kw["route_entry"][key] = bad
                self.assertFalse(arrival.welcome(state, **kw)[1])

    def test_malformed_persisted_cooking_receipt_is_not_proof(self):
        for key, bad in (("cook_event_id", 61.0),
                         ("prep_event_id", 60.0),
                         ("maker_id", 21.0)):
            with self.subTest(receipt=key):
                state, kw = fixture()
                state["history"][0][key] = bad
                self.assertFalse(arrival.welcome(state, **kw)[1])

    def test_one_route_cannot_buy_multiple_meals(self):
        state, kw = fixture()
        first, ok, why = arrival.welcome(state, **kw)
        self.assertTrue(ok, why)
        next_state = soup_state.archive(
            first, 1, maker_id=21, maker="InnkeepTester",
            source_event_id=100, cook_event_id=101,
            recipe=soup_state.produce("barley", "salt", warmed=False),
        )
        second = copy.deepcopy(kw)
        second["event_id"] = 102
        second["bowl_id"] = 103
        second["bowl_event"]["id"] = 101
        second["bowl_event"]["payload"]["prep_event_id"] = 100
        second["bowl_event"]["consequence"]["source_event_id"] = 100
        second["bowl_event"]["consequence"]["bowl_id"] = 103
        self.assertFalse(arrival.welcome(next_state, **second)[1])


    def test_public_pot_history_requires_original_completed_source_chain(self):
        state, kw = fixture()
        committed, ok, reason = arrival.welcome(state, **kw)
        self.assertTrue(ok, reason)
        signed_welcome = {
            "id": 90,
            "kind": "professional.innkeep_wanderer_arrival_welcome",
            "status": "complete",
            "actor": {"account_id": 20, "mask_id": 21, "mask": "InnkeepTester"},
            "payload": {
                "day": 1, "hour": 21, "tavern_room_id": 3,
                "guest_mask_id": 32, "guest_account_id": 31,
                "route_event_id": 80, "cook_event_id": 61, "bowl_id": 77,
            },
            "consequence": {
                "tavern_room_id": 3, "bowl_id": 77, "route_event_id": 80,
                "cook_event_id": 61, "wanderer_account_id": 31,
                "innkeep_account_id": 20,
                "service": "physical_bowl_transferred",
            },
        }
        events = {80: kw["route_event"], 61: kw["bowl_event"],
                  90: signed_welcome}
        line = arrival.verified_public_welcome(
            json.loads(json.dumps(committed))["history"], events.get
        )
        self.assertIn("signed returning-traveler hospitality", line.lower())
        self.assertIn("route event 80", line)
        self.assertIn("welcome event 90", line)
        self.assertIn("does not certify route safety", line)

        # Mutable pantry records cannot create public claims by themselves.
        for field, bad in (("event_id", 90.0),
                           ("route_event_id", 80.0),
                           ("wanderer_account_id", 20),
                           ("bowl_id", 77.0),
                           ("service", "free_ration")):
            with self.subTest(receipt_field=field):
                changed = copy.deepcopy(committed)
                changed["history"][0]["arrival_welcome"][field] = bad
                self.assertEqual(
                    arrival.verified_public_welcome(changed["history"], events.get),
                    "",
                )

        for event_id, part, field, bad in (
            (90, "", "status", "consequence_failed"),
            (90, "actor", "account_id", 99),
            (90, "payload", "route_event_id", 999),
            (90, "consequence", "service", "imagined"),
            (80, "actor", "mask_id", 999),
            (80, "consequence", "interpretation", "marked_caution"),
            (61, "actor", "account_id", 999),
            (61, "consequence", "bowl_id", 999),
        ):
            with self.subTest(event_id=event_id, field=field):
                changed = copy.deepcopy(events)
                target = changed[event_id] if not part else changed[event_id][part]
                target[field] = bad
                self.assertEqual(
                    arrival.verified_public_welcome(
                        committed["history"], changed.get
                    ), "",
                )
        self.assertEqual(
            arrival.verified_public_welcome(
                committed["history"], lambda event_id: None
            ), "",
        )
        self.assertEqual(
            arrival.verified_public_welcome([], events.get), "",
        )



if __name__ == "__main__":
    unittest.main()
