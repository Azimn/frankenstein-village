"""B08 EDGE-20/23: finite physical fittings and original source-chain proof."""
import copy
import json
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "spike/fvillage"))
from world import route_fittings as f


def fixture(kind="span"):
    target_id = 400 if kind == "span" else 401
    room_id = 400 if kind == "span" else 402
    source_object_id = 501 if kind == "span" else 502
    source_room_id = 503 if kind == "span" else 504
    state = {
        "kind": kind, "install_event_id": 30, "source_event_id": 10,
        "forge_event_id": 20, "item_id": 600,
        "source_object_id": source_object_id,
        "source_room_id": source_room_id,
        "target_id": target_id, "target_room_id": room_id,
        "day": 4, "hour": 14, "smith_account_id": 7,
        "source_account_id": 8,
    }
    source = {
        "id": 10, "status": "complete", "kind": f.SOURCES[kind],
        "actor": {"account_id": 8, "mask_id": 80, "mask": "Scout"},
        "payload": {"day": 4, "hour": 11},
        "consequence": {},
    }
    if kind == "span":
        source["payload"].update(
            calling="wanderer", location="Riverside Path",
            object_id=501, room_id=503)
        source["consequence"].update(
            gauge_object_id=501, room_id=503, account_id=8,
            witness_event_id=10)
    else:
        source["payload"].update(
            role="hound", action="protect", site="red_cord",
            location="The Northern Treeline")
        source["consequence"].update(
            cord_object_id=502, square_room_id=504,
            site="red_cord", role="hound", action="protect",
            caution_marked=True)
    forge = {
        "id": 20, "status": "complete",
        "kind": "village.route_fitting_forged",
        "actor": {"account_id": 7, "mask_id": 70, "mask": "Smith"},
        "payload": {"calling": "smith", "kind": kind,
                    "location": "Market Lane", "day": 4,
                    "hour": 12, "table_id": 900},
        "consequence": {"item_id": 600, "table_id": 900,
                        "kind": kind, "remaining": 1},
    }
    install = {
        "id": 30, "status": "complete",
        "kind": "village.route_fitting_installed",
        "actor": {"account_id": 7, "mask_id": 70, "mask": "Smith"},
        "payload": {
            "calling": "smith", "kind": kind,
            "location": f.ROOMS[kind], "day": 4, "hour": 14,
            "target_id": target_id, "target_room_id": room_id,
            "source_event_id": 10, "forge_event_id": 20, "item_id": 600,
        },
        "consequence": {
            "installed": True, "target_id": target_id,
            "target_room_id": room_id, "source_event_id": 10,
            "forge_event_id": 20, "consumed_item_id": 600,
        },
    }
    return state, {10: source, 20: forge, 30: install}


def verify(state, events):
    return f.verified_install(
        state, events.get, kind=state.get("kind"),
        target_id=state.get("target_id"),
        room_id=state.get("target_room_id"), table_id=900, day=4)


class RouteFittingProofTests(unittest.TestCase):
    def test_both_independent_physical_routes_survive_json_restart(self):
        for kind in f.KINDS:
            with self.subTest(kind=kind):
                state, events = fixture(kind)
                state = json.loads(json.dumps(state))
                events = {int(k): v for k, v in
                          json.loads(json.dumps(events)).items()}
                self.assertTrue(verify(state, events))
                self.assertTrue(f.verified_forge(
                    {"item_id": 600, "forge_event_id": 20,
                     "forge_day": 4}, events.get,
                    kind=kind, table_id=900, day=4))
                self.assertFalse(f.verified_install(
                    state, events.get, kind=kind,
                    target_id=state["target_id"] + 1,
                    room_id=state["target_room_id"],
                    table_id=900, day=4))

    def test_forged_failed_wrong_role_account_and_physical_source_refused(self):
        for kind in f.KINDS:
            state, events = fixture(kind)
            cases = [
                (10, None, "status", "consequence_failed"),
                (10, None, "kind", "village.unrelated"),
                (10, "actor", "account_id", 7),
                (10, "actor", "mask_id", 70),
                (10, "actor", "mask", ""),
                (10, "payload", "day", 5),
                (10, "payload", "hour", 15),
                (20, None, "status", "consequence_failed"),
                (20, "payload", "calling", "merchant"),
                (20, "actor", "mask", ""),
                (20, "payload", "table_id", 901),
                (20, "consequence", "item_id", 601),
                (30, None, "status", "consequence_failed"),
                (30, "actor", "account_id", 8),
                (30, "payload", "target_id", 401 if kind == "span" else 400),
                (30, "consequence", "consumed_item_id", 601),
            ]
            for event_id, group, key, value in cases:
                with self.subTest(kind=kind, event=event_id, field=key):
                    forged = copy.deepcopy(events)
                    target = forged[event_id] if group is None else forged[event_id][group]
                    target[key] = value
                    self.assertFalse(verify(state, forged))
            for field, value in (
                ("smith_account_id", 8), ("source_event_id", 20),
                ("item_id", False), ("day", 5), ("hour", True),
                ("target_id", 999), ("source_object_id", 999),
            ):
                with self.subTest(kind=kind, field=field):
                    changed = dict(state, **{field: value})
                    self.assertFalse(verify(changed, events))

    def test_finite_stock_conserves_two_units_and_refuses_rewind(self):
        for kind in f.KINDS:
            state, error = f.withdraw(None, 4, kind)
            self.assertIsNone(error)
            self.assertEqual(state["remaining"][kind], 1)
            state, error = f.withdraw(state, 4, kind)
            self.assertIsNone(error)
            self.assertEqual(state["remaining"][kind], 0)
            exhausted, error = f.withdraw(state, 4, kind)
            self.assertIsNone(exhausted)
            self.assertIn("remain", error)
            rewind, error = f.withdraw(state, 3, kind)
            self.assertIsNone(rewind)
            self.assertIn("earlier", error)
            refreshed, error = f.withdraw(state, 5, kind)
            self.assertIsNone(error)
            self.assertEqual(refreshed["remaining"][kind], 1)
            corrupt, error = f.withdraw({"day": 5, "remaining": {kind: True}}, 5, kind)
            self.assertIsNone(corrupt)
            self.assertIn("review", error)

    def test_hound_must_reinspect_original_cord_after_smith_install(self):
        proof = dict(day=4, hour=14, route_fitting_install_event_id=30,
                     route_fitting_cord_id=401)
        kwargs = dict(day=4, hour=14, install_hour=14,
                      install_event_id=30, cord_id=401)
        self.assertTrue(f.verified_post_install_view(proof, **kwargs))
        for change in (
            {"route_fitting_install_event_id": None},
            {"route_fitting_install_event_id": 29},
            {"route_fitting_cord_id": 999},
            {"day": 3},
            {"hour": 13},
            {"hour": True},
        ):
            with self.subTest(change=change):
                self.assertFalse(f.verified_post_install_view(
                    dict(proof, **change), **kwargs))
        self.assertFalse(f.verified_post_install_view(
            {"day": 4, "hour": 14}, **kwargs))
        self.assertFalse(f.verified_post_install_view(True, **kwargs))

    def test_hound_post_install_test_requires_original_source_and_separate_account(self):
        state, events = fixture("cord")
        events[40] = {
            "id": 40, "status": "complete",
            "kind": "village.route_fitting_tested",
            "actor": {"account_id": 8, "mask_id": 80, "mask": "Hound"},
            "payload": {
                "calling": "hound", "kind": "cord",
                "location": "The Northern Treeline",
                "day": 4, "hour": 15, "target_id": 401,
                "target_room_id": 402, "install_event_id": 30,
            },
            "consequence": {
                "tested": True, "target_id": 401, "install_event_id": 30,
            },
        }
        row = {"event_id": 40, "install_event_id": 30}
        kwargs = dict(cord_id=401, room_id=402, table_id=900, day=4)
        self.assertTrue(f.verified_test(state, row, events.get, **kwargs))
        for event_id, group, key, value in (
            (40, None, "status", "consequence_failed"),
            (40, "actor", "account_id", 7),
            (40, "payload", "install_event_id", 99),
            (40, "payload", "target_id", 999),
            (40, "payload", "hour", 13),
            (40, "consequence", "tested", False),
        ):
            changed = copy.deepcopy(events)
            target = changed[event_id] if group is None else changed[event_id][group]
            target[key] = value
            self.assertFalse(f.verified_test(state, row, changed.get, **kwargs))


if __name__ == "__main__":
    unittest.main()
