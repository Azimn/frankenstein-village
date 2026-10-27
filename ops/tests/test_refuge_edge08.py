"""EDGE-08 pure provenance, scarcity, negative and restart-survival tests."""
import copy
import json
import sys
import unittest
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "spike/fvillage"))

from world import refuge_state as r, soup_state


def fixture():
    protection = {
        "id": 41, "kind": "village.route_protected", "status": "complete",
        "actor": {"account_id": 101, "mask_id": 201, "mask": "HoundTester"},
        "payload": {"site": "red_cord", "role": "hound", "action": "protect",
                    "location": r.TREELINE, "day": 3, "hour": 10},
        "consequence": {"cord_object_id": 301, "day": 3,
                        "caution_marked": True},
    }
    marker = {"event_id": 41, "account_id": 101,
              "mask": "HoundTester", "day": 3}
    dispatch = {
        "id": 42, "kind": "professional.hound_refuge_dispatch",
        "status": "complete",
        "actor": {"account_id": 101, "mask_id": 201, "mask": "HoundTester"},
        "payload": {"day": 3, "hour": 11, "cord_id": 301,
                    "source_protect_event_id": 41,
                    "professional_calling": "hound",
                    "location": r.TREELINE},
        "consequence": {"item_id": 401, "cord_id": 301,
                        "source_protect_event_id": 41},
    }
    token = {"dispatch_event_id": 42, "source_protect_event_id": 41,
             "hound_account_id": 101, "hound_mask_id": 201,
             "cord_id": 301, "day": 3, "hour": 11}
    return protection, marker, dispatch, token


def serve(**changes):
    source, marker, event, token = fixture()
    args = dict(raw=None, pantry_raw=None, day=3, hour=12,
                innkeep_account_id=102, innkeep_mask_id=202,
                hound_account_id=101, hound_mask_id=201,
                token=token, token_id=401, dispatch_event=event,
                protection=source, marker=marker, cord_id=301,
                tavern_id=501, event_id=43)
    args.update(changes)
    return r.accept(**args)


class RefugeRules(unittest.TestCase):
    def test_real_two_account_arrival_spends_finite_food(self):
        history, food, ok, reason = serve()
        self.assertTrue(ok, reason)
        self.assertEqual(food["stock"]["turnip"], 2)
        self.assertEqual(food["stock"]["salt"], 3)
        self.assertEqual(history["history"][0]["dispatch_event_id"], 42)
        self.assertEqual(history["history"][0]["hound_account_id"], 101)
        self.assertEqual(history["history"][0]["innkeep_account_id"], 102)

    def test_signed_original_cord_required(self):
        source, marker, _, _ = fixture()
        self.assertTrue(r.protection_valid(source, marker, 301))
        self.assertFalse(r.protection_valid(source, marker, 302))
        for field, value in (("status", "consequence_failed"),
                             ("kind", "village.route_inspected")):
            bad = copy.deepcopy(source)
            bad[field] = value
            self.assertFalse(r.protection_valid(bad, marker, 301))
        bad = copy.deepcopy(source)
        bad["consequence"]["caution_marked"] = False
        self.assertFalse(r.protection_valid(bad, marker, 301))
        bad = copy.deepcopy(source)
        bad["actor"]["account_id"] = 999
        self.assertFalse(r.protection_valid(bad, marker, 301))

    def test_dispatch_one_per_day_and_clock_rewind(self):
        source, marker, _, _ = fixture()
        args = dict(cord_id=301, day=3, hour=11,
                    hound_account_id=101, hound_mask_id=201)
        self.assertTrue(r.can_dispatch(None, source, marker, **args)[0])
        self.assertFalse(r.can_dispatch({"day": 3}, source, marker, **args)[0])
        self.assertFalse(r.can_dispatch({"day": 4}, source, marker, **args)[0])
        self.assertFalse(r.can_dispatch(None, source, marker,
                         **dict(args, day=2))[0])
        self.assertTrue(r.can_dispatch({"day": 3}, source, marker,
                        **dict(args, day=4))[0])

    def test_forged_dispatch_source_or_item_rejected(self):
        source, marker, event, token = fixture()
        self.assertTrue(r.dispatch_valid(event, token, source, marker, 301, 401))
        for change in ({"status": "consequence_failed"},
                       {"kind": "village.route_inspected"}):
            self.assertFalse(serve(dispatch_event=dict(event, **change))[2])
        bad = copy.deepcopy(event)
        bad["actor"]["account_id"] = 999
        self.assertFalse(serve(dispatch_event=bad)[2])
        bad = copy.deepcopy(event)
        bad["consequence"]["item_id"] = 999
        self.assertFalse(serve(dispatch_event=bad)[2])
        self.assertFalse(serve(token_id=402)[2])
        self.assertFalse(serve(token=dict(token, source_protect_event_id=999))[2])
        self.assertFalse(serve(protection=dict(source, id=999))[2])

    def test_same_account_role_switch_and_wrong_carrier(self):
        self.assertFalse(serve(innkeep_account_id=101)[2])
        self.assertFalse(serve(hound_account_id=999)[2])
        self.assertFalse(serve(hound_mask_id=999)[2])
        self.assertFalse(serve(innkeep_mask_id=True)[2])

    def test_duplicate_dispatch_rejected(self):
        history, food, ok, _ = serve()
        self.assertTrue(ok)
        self.assertFalse(serve(raw=history, pantry_raw=food, event_id=44)[2])

    def test_late_arrival_future_and_clock_rewind(self):
        self.assertTrue(serve(day=4, hour=11)[2])
        self.assertFalse(serve(day=4, hour=12)[2])
        self.assertFalse(serve(day=3, hour=10)[2])
        self.assertFalse(serve(day=0, hour=12)[2])
        self.assertFalse(serve(day=3, hour=True)[2])
        self.assertFalse(serve(day=3, hour=24)[2])

    def test_depleted_pantry_and_solo_fallback(self):
        pantry = soup_state.pantry(None, 3)
        pantry["stock"]["turnip"] = 0
        self.assertFalse(serve(pantry_raw=pantry)[2])
        self.assertEqual(soup_state.pantry(None, 3)["stock"]["turnip"], 3)
        self.assertTrue(soup_state.reserve(None, 3, "barley", "thyme")[1])

    def test_restart_json_roundtrip(self):
        history, food, ok, _ = serve()
        self.assertTrue(ok)
        history = json.loads(json.dumps(history))
        food = json.loads(json.dumps(food))
        self.assertFalse(serve(raw=history, pantry_raw=food, event_id=44)[2])
        self.assertIn("1 signed Hound arrival", r.public_lines(history))
        self.assertIn("No witnessed", r.public_lines(None))

    def test_corrupt_persisted_history_fails_closed(self):
        self.assertFalse(serve(raw={"history": [{"event_id": True}]})[2])
        self.assertFalse(serve(raw={"history": "forged"})[2])
        self.assertFalse(serve(raw="forged")[2])
        self.assertIn("requires inspection",
                      r.public_lines({"history": [{"event_id": True}]}))


if __name__ == "__main__":
    unittest.main()
