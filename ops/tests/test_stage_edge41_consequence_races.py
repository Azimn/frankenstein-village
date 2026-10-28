"""EDGE-41: live stage authorization must survive the ledger boundary.

These tests load the real production adapter with minimal Evennia stand-ins.
They exercise a mutation *after* the preview but *before* the consequence,
rather than merely inspecting source text. The separate authenticated telnet
and real-restart suite remains the integration qualification.
"""
from contextlib import nullcontext
import importlib.util
from pathlib import Path
import sys
import types
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "spike/fvillage"))
from world import stage_state


class Account:
    def __init__(self, ident):
        self.id = ident
        self.sessions = types.SimpleNamespace(all=lambda: [object()])


class Mask:
    def __init__(self, account, role, tavern, name="Player"):
        self.id = account.id + 100
        self.account = account
        self.role = role
        self.location = tavern
        self.key = name


class StageConsequenceRaceTests(unittest.TestCase):
    def setUp(self):
        self.tavern = types.SimpleNamespace(
            db=types.SimpleNamespace(village_stage=stage_state.fresh(4)),
            contents=[],
            id=999,
        )
        self.actor = Mask(Account(11), "performer", self.tavern, "Musician")
        self.tavern.contents.append(self.actor)
        self.mutate = lambda: None
        self.published = []

        django = types.ModuleType("django")
        db = types.ModuleType("django.db")
        db.transaction = types.SimpleNamespace(atomic=nullcontext)
        evennia = types.ModuleType("evennia")
        scripts = types.ModuleType("evennia.scripts")
        models = types.ModuleType("evennia.scripts.models")
        models.ScriptDB = types.SimpleNamespace()
        utils = types.ModuleType("evennia.utils")
        utils.search = types.SimpleNamespace(search_object=lambda _key: [])
        callings = types.ModuleType("world.callings")
        callings.active_calling = lambda mask: mask.role
        callings.record_participation = lambda *_args, **_kwargs: None
        events = types.ModuleType("world.events")
        events.publish_world_event = lambda *_args, **_kwargs: None
        events.get_event_ledger = lambda: None
        stubs = {
            "django": django, "django.db": db,
            "evennia": evennia, "evennia.scripts": scripts,
            "evennia.scripts.models": models, "evennia.utils": utils,
            "world.callings": callings, "world.events": events,
        }
        module_path = ROOT / "spike/fvillage/world/stage_work.py"
        spec = importlib.util.spec_from_file_location(
            "edge41_stage_work_race_under_test", module_path)
        self.work = importlib.util.module_from_spec(spec)
        with patch.dict(sys.modules, stubs):
            spec.loader.exec_module(self.work)
        self.work._tavern = lambda: self.tavern
        self.work._clock = lambda: (4, 20)
        self.work.active_calling = lambda mask: mask.role
        self.work.record_participation = lambda *_args, **_kwargs: None

        def publish(kind, *, actor, payload, consequence):
            self.mutate()
            result = consequence({"id": 501})
            self.published.append((kind, result))
            return {"id": 501}

        self.work.publish_world_event = publish

    def _rehearsal(self):
        state, ok, why = stage_state.rehearse(
            None, day=4, hour=19, account_id=11, mask_id=self.actor.id,
            mask=self.actor.key, tune="ballad", event_id=490)
        self.assertTrue(ok, why)
        self.tavern.db.village_stage = state

    def _performance(self):
        self._rehearsal()
        state, ok, why = stage_state.perform(
            self.tavern.db.village_stage, day=4, hour=20,
            account_id=11, mask_id=self.actor.id, mask=self.actor.key,
            tune="ballad", event_id=491, audience_account_ids=[22])
        self.assertTrue(ok, why)
        self.tavern.db.village_stage = state

    def test_performer_cannot_rehearse_after_leaving_between_preview_and_commit(self):
        self.mutate = lambda: setattr(self.actor, "location", None)
        with self.assertRaisesRegex(RuntimeError, "left or changed account"):
            self.work.act(self.actor, "rehearse", "ballad")
        self.assertEqual(self.tavern.db.village_stage["rehearsals"], [])
        self.assertEqual(self.published, [])

    def test_performer_cannot_rehearse_after_changing_calling(self):
        self.mutate = lambda: setattr(self.actor, "role", "hound")
        with self.assertRaisesRegex(RuntimeError, "Calling changed"):
            self.work.act(self.actor, "rehearse", "ballad")
        self.assertEqual(self.tavern.db.village_stage["rehearsals"], [])
        self.assertEqual(self.published, [])

    def test_performer_cannot_commit_under_replaced_account(self):
        self.mutate = lambda: setattr(self.actor, "account", Account(44))
        with self.assertRaisesRegex(RuntimeError, "left or changed account"):
            self.work.act(self.actor, "rehearse", "ballad")
        self.assertEqual(self.tavern.db.village_stage["rehearsals"], [])
        self.assertEqual(self.published, [])

    def test_performer_cannot_perform_after_changing_calling(self):
        self._rehearsal()
        self.mutate = lambda: setattr(self.actor, "role", "hound")
        with self.assertRaisesRegex(RuntimeError, "Calling changed"):
            self.work.act(self.actor, "perform", "ballad")
        self.assertIsNone(self.tavern.db.village_stage["performance"])
        self.assertEqual(self.published, [])

    def test_witness_cannot_sign_after_leaving_or_disconnect(self):
        self._performance()
        listener = Mask(Account(22), "innkeep", self.tavern, "Listener")
        self.tavern.contents.append(listener)
        for mutation in (
            lambda: setattr(listener, "location", None),
            lambda: setattr(listener.account.sessions, "all", lambda: []),
        ):
            with self.subTest(mutation=mutation):
                listener.location = self.tavern
                listener.account.sessions.all = lambda: [object()]
                self.mutate = mutation
                with self.assertRaises(RuntimeError):
                    self.work.act(listener, "witness")
                self.assertEqual(self.tavern.db.village_stage["witnesses"], [])
                self.assertEqual(self.published, [])

    def test_valid_rehearsal_and_independent_live_witness_still_commit(self):
        result, error = self.work.act(self.actor, "rehearse", "ballad")
        self.assertIsNone(error)
        self.assertEqual(result["action"], "rehearse")
        self.assertEqual(len(self.tavern.db.village_stage["rehearsals"]), 1)
        state, ok, why = stage_state.perform(
            self.tavern.db.village_stage, day=4, hour=20,
            account_id=11, mask_id=self.actor.id, mask=self.actor.key,
            tune="ballad", event_id=491, audience_account_ids=[22])
        self.assertTrue(ok, why)
        self.tavern.db.village_stage = state
        listener = Mask(Account(22), "innkeep", self.tavern, "Listener")
        self.tavern.contents.append(listener)
        result, error = self.work.act(listener, "witness")
        self.assertIsNone(error)
        self.assertEqual(result["action"], "witness")
        self.assertEqual(len(self.tavern.db.village_stage["witnesses"]), 1)
        self.assertEqual(self.tavern.db.village_stage["witnesses"][0]["account_id"], 22)


if __name__ == "__main__":
    unittest.main()
