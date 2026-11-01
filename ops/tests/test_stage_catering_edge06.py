"""GDD-EDGE-06: a Performer show and Innkeep's finite physical food service."""
import copy
import json
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "spike/fvillage"))
from world import stage_state as stage


def args(aid, event, *, day=3, hour=19, mid=None, mask=None):
    return {
        "day": day, "hour": hour, "account_id": aid,
        "mask_id": mid or aid * 10, "mask": mask or f"Mask{aid}",
        "event_id": event,
    }


def witnessed_show():
    state, ok, why = stage.rehearse(
        None, tune="ballad", **args(7, 101))
    assert ok, why
    state, ok, why = stage.perform(
        state, tune="ballad", audience_account_ids=[8],
        **args(7, 102))
    assert ok, why
    state, ok, why = stage.witness(state, **args(8, 103))
    assert ok, why
    return state


def cater(state, aid=8, event=105, bowl=201, cooked=104, hour=19, day=3):
    return stage.cater(
        state, bowl_id=bowl, cook_event_id=cooked,
        **args(aid, event, day=day, hour=hour),
    )


class InnkeepPerformerCateringTests(unittest.TestCase):
    def test_two_independent_accounts_and_actual_bowl_receipt(self):
        source = witnessed_show()
        before = copy.deepcopy(source)
        updated, ok, reason = cater(source)
        self.assertTrue(ok, reason)
        self.assertIsNone(before["service"])
        self.assertIsNone(source["service"], "Pure function must not mutate input")
        service = updated["service"]
        self.assertEqual(service["account_id"], 8)
        self.assertEqual(service["performance_event_id"], 102)
        self.assertEqual(service["witness_event_id"], 103)
        self.assertEqual(service["cook_event_id"], 104)
        self.assertEqual(service["bowl_id"], 201)
        self.assertEqual(service["witness_count"], 1)
        self.assertIn("one real cooked soup bowl", stage.public_lines(updated, 3))

    def test_no_show_or_audience_does_not_invent_demand(self):
        _, ok, reason = cater(None)
        self.assertFalse(ok)
        self.assertIn("No real Performer show", reason)
        state, ok, _ = stage.rehearse(None, tune="ballad", **args(7, 101))
        self.assertTrue(ok)
        state, ok, _ = stage.perform(
            state, tune="ballad", audience_account_ids=[8], **args(7, 102))
        self.assertTrue(ok)
        result, ok, reason = cater(state)
        self.assertFalse(ok)
        self.assertIn("No audience member", reason)
        self.assertIsNone(result["service"])

    def test_performer_cannot_supply_own_pairwise_service(self):
        state = witnessed_show()
        result, ok, reason = cater(state, aid=7)
        self.assertFalse(ok)
        self.assertIn("independent Innkeep", reason)
        self.assertIsNone(result["service"])

    def test_missing_bowl_and_forged_identifiers_fail_closed(self):
        state = witnessed_show()
        for changes in (
            {"bowl": 0}, {"bowl": True}, {"cooked": False},
            {"cooked": -2}, {"event": 0}, {"aid": True},
            {"event": 102}, {"event": 104},
        ):
            result, ok, reason = cater(state, **changes)
            self.assertFalse(ok, reason)
            self.assertIsNone(result["service"])

    def test_duplicate_and_late_service_do_not_change_world(self):
        state = witnessed_show()
        late, ok, reason = cater(state, hour=20)
        self.assertFalse(ok)
        self.assertIn("audience has left", reason)
        self.assertIsNone(late["service"])
        served, ok, reason = cater(state)
        self.assertTrue(ok, reason)
        original = copy.deepcopy(served)
        duplicate, ok, reason = cater(served, event=106, bowl=202, cooked=107)
        self.assertFalse(ok)
        self.assertIn("already received", reason)
        self.assertEqual(duplicate, original)

    def test_later_witness_does_not_rewrite_service_attendance(self):
        state, ok, why = stage.rehearse(
            None, tune="ballad", **args(7, 101))
        self.assertTrue(ok, why)
        state, ok, why = stage.perform(
            state, tune="ballad", audience_account_ids=[8, 9],
            **args(7, 102))
        self.assertTrue(ok, why)
        state, ok, why = stage.witness(state, **args(8, 103))
        self.assertTrue(ok, why)
        served, ok, why = cater(state)
        self.assertTrue(ok, why)
        after, ok, why = stage.witness(served, **args(9, 106))
        self.assertTrue(ok, why)
        self.assertEqual(len(after["witnesses"]), 2)
        self.assertEqual(after["service"]["witness_count"], 1)
        self.assertEqual(stage.normalize(after)["service"]["witness_count"], 1)

    def test_json_restart_and_rollover_preserve_signed_causality(self):
        state, ok, reason = cater(witnessed_show())
        self.assertTrue(ok, reason)
        loaded = stage.normalize(json.loads(json.dumps(state)))
        self.assertEqual(loaded["service"], state["service"])
        tomorrow = stage.refresh(loaded, 4)
        self.assertIsNone(tomorrow["service"])
        self.assertEqual(tomorrow["history"][-1]["service"], state["service"])
        stale, ok, reason = cater(tomorrow, day=3)
        self.assertFalse(ok)
        self.assertIn("rewound", reason)
        self.assertIsNone(stale["service"])

    def test_corrupt_stored_service_never_becomes_valid(self):
        state, ok, reason = cater(witnessed_show())
        self.assertTrue(ok, reason)
        for field, value in (
            ("account_id", 7), ("account_id", "7"), ("bowl_id", False),
            ("performance_event_id", 999),
            ("witness_event_id", 999), ("hour", 21),
            ("event_id", 102), ("event_id", "invalid"),
            ("cook_event_id", "invalid"), ("witness_count", False),
            ("witness_count", 9),
        ):
            forged = copy.deepcopy(state)
            forged["service"][field] = value
            self.assertIsNone(stage.normalize(forged)["service"], field)


def signed_catering_adapter():
    """Load the actual pure source predicate without a running Evennia server."""
    import importlib.util
    import types
    from unittest import mock

    names = ("django", "django.db", "evennia", "evennia.scripts",
             "evennia.scripts.models", "evennia.utils",
             "evennia.utils.search", "world.callings", "world.events")
    fake = {name: types.ModuleType(name) for name in names}
    for name in ("django", "evennia", "evennia.scripts", "evennia.utils"):
        fake[name].__path__ = []
    fake["django"].db = fake["django.db"]
    fake["django.db"].transaction = types.SimpleNamespace(atomic=lambda: None)
    fake["evennia"].scripts = fake["evennia.scripts"]
    fake["evennia.scripts"].models = fake["evennia.scripts.models"]
    fake["evennia.scripts.models"].ScriptDB = type("ScriptDB", (), {})
    fake["evennia"].utils = fake["evennia.utils"]
    fake["evennia.utils"].search = fake["evennia.utils.search"]
    fake["evennia.utils.search"].search_object = lambda *a, **kw: []
    fake["world.callings"].active_calling = lambda mask: None
    fake["world.callings"].record_participation = lambda *a, **kw: None
    fake["world.events"].get_event_ledger = lambda: None
    fake["world.events"].publish_world_event = lambda *a, **kw: None
    path = Path(__file__).resolve().parents[2] / "spike/fvillage/world/stage_work.py"
    spec = importlib.util.spec_from_file_location("edge06_stage_work_probe", path)
    module = importlib.util.module_from_spec(spec)
    with mock.patch.dict(sys.modules, fake):
        spec.loader.exec_module(module)
    return module._catering_sources_match


def signed_catering_events():
    """Actual production event payload/consequence shapes for one witnessed show."""
    return {
        "cook": {
            "id": 104, "status": "complete",
            "kind": "professional.innkeep_soup_cooked",
            "actor": {"account_id": 8, "mask_id": 80, "mask": "Mask8"},
            "payload": {"day": 3, "hour": 19},
            "consequence": {"bowl_id": 201, "pantry_room_id": 500},
        },
        "show": {
            "id": 102, "status": "complete", "kind": "village.stage_perform",
            "actor": {"account_id": 7, "mask_id": 70, "mask": "Mask7"},
            "payload": {"day": 3, "hour": 19, "tune": "ballad"},
            "consequence": {
                "day": 3, "hour": 19, "tune": "ballad",
                "tavern_room_id": 500, "performance_event_id": 102,
            },
        },
        "witness": {
            "id": 103, "status": "complete", "kind": "village.stage_witness",
            "actor": {"account_id": 8, "mask_id": 80, "mask": "Mask8"},
            "payload": {"day": 3, "hour": 19, "tune": None},
            "consequence": {
                "day": 3, "hour": 19, "tavern_room_id": 500,
                "performance_event_id": 102,
            },
        },
    }


class SignedCateringSourceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.match = staticmethod(signed_catering_adapter())

    def valid(self, state, events):
        return self.match(
            state, events["cook"], events["show"], events["witness"],
            tavern_id=500, bowl_id=201, cook_event_id=104,
        )

    def test_real_independent_witness_and_tavern_bowl_source(self):
        state = witnessed_show()
        events = signed_catering_events()
        self.assertTrue(self.valid(state, events))
        self.assertTrue(self.valid(
            stage.normalize(json.loads(json.dumps(state))),
            json.loads(json.dumps(events)),
        ))

    def test_other_completed_show_witness_does_not_authorize_catering(self):
        state = witnessed_show()
        forged = copy.deepcopy(state)
        forged["witnesses"][0]["event_id"] = 205
        # Shape-only stage state still accepts this plausible persisted ID.
        _, shape_ok, reason = cater(forged, event=206)
        self.assertTrue(shape_ok, reason)
        events = signed_catering_events()
        events["witness"]["id"] = 205
        events["witness"]["consequence"]["performance_event_id"] = 99
        self.assertFalse(self.valid(forged, events))
        self.assertIsNone(state["service"])
        self.assertIsNone(forged["service"])

    def test_signed_actor_time_show_room_and_cook_locality_fail_closed(self):
        original = signed_catering_events()
        state = witnessed_show()
        cases = (
            ("witness", "actor", "account_id", 7),
            ("witness", "actor", "mask_id", 999),
            ("witness", "payload", "day", 2),
            ("witness", "payload", "hour", 18),
            ("witness", "consequence", "performance_event_id", 999),
            ("witness", "consequence", "tavern_room_id", 501),
            ("show", "actor", "account_id", 8),
            ("show", "payload", "day", 2),
            ("show", "payload", "hour", 18),
            ("show", "payload", "tune", "reel"),
            ("show", "consequence", "tavern_room_id", 501),
            ("show", "consequence", "performance_event_id", 999),
            ("cook", "consequence", "pantry_room_id", 501),
            ("cook", "consequence", "bowl_id", 202),
            ("cook", "payload", "day", 4),
            ("cook", "payload", "hour", 20),
        )
        for event, section, key, value in cases:
            with self.subTest(event=event, section=section, key=key):
                corrupted = copy.deepcopy(original)
                corrupted[event][section][key] = value
                self.assertFalse(self.valid(state, corrupted))
                self.assertIsNone(state["service"])
        for missing in ("cook", "show", "witness"):
            with self.subTest(missing=missing):
                corrupted = copy.deepcopy(original)
                corrupted[missing] = None
                self.assertFalse(self.valid(state, corrupted))
        self.assertTrue(self.valid(state, original))



if __name__ == "__main__":
    unittest.main()
