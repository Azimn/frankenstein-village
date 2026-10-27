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
                        "square_room_id": 2, "cord_object_id": 9},
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


if __name__ == "__main__":
    unittest.main()
