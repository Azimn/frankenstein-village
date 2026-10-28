"""EDGE-16: actual publication adapter rechecks physical and ledger authority."""
from contextlib import nullcontext
import importlib.util
import json
from pathlib import Path
import sys
import types
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "spike/fvillage"))
from world import route_surveys


class CautionAdapterTests(unittest.TestCase):
    def setUp(self):
        self.day, self.hour = 4, 12
        self.square = types.SimpleNamespace(
            id=500, key="Village Square", location=None,
            db=types.SimpleNamespace(daily_route_survey=None))
        self.treeline = types.SimpleNamespace(
            key="The Northern Treeline", location=None, contents=[])
        self.cord = types.SimpleNamespace(
            id=700, key="a frayed red cord", location=self.treeline,
            db=types.SimpleNamespace(
                landmark_id="red_cord",
                route_caution={"day": 4, "event_id": 40, "account_id": 11}))
        self.treeline.contents.append(self.cord)
        self.treeline.tags = types.SimpleNamespace(has=lambda *_a, **_kw: True)
        self.cord.access = lambda *_a, **_kw: True
        self.cord.db.route_caution_history = None
        state, ok, why = route_surveys.field_decision(
            None, 4, "red_cord", "hound", "protect", False, 11, "Hound", 40)
        self.assertTrue(ok, why)
        self.square.db.daily_route_survey = state
        self.account = types.SimpleNamespace(
            id=22, sessions=types.SimpleNamespace(all=lambda: [object()]))
        self.mask = types.SimpleNamespace(
            id=222, key="Chronicler", account=self.account,
            location=self.square, role="chronicler",
            db=types.SimpleNamespace(
                landmark_discoveries=[{"id": "red_cord"}],
                landmark_latest_view={"red_cord": {"day": 4, "hour": 11}}))
        self.hound_event = {
            "id": 40, "kind": "village.route_protected", "status": "complete",
            "actor": {"account_id": 11, "mask_id": 111, "mask": "Hound"},
            "payload": {"site": "red_cord", "day": 4, "hour": 10,
                        "role": "hound", "action": "protect",
                        "location": "The Northern Treeline"},
            "consequence": {
                "cord_object_id": 700, "square_room_id": 500,
                "site": "red_cord", "day": 4, "role": "hound",
                "action": "protect", "caution_marked": True},
        }
        self.events = {40: self.hound_event}
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
        utils.search = types.SimpleNamespace(search_object=lambda key:
            [self.treeline] if key == "The Northern Treeline" else [])
        callings = types.ModuleType("world.callings")
        callings.active_calling = lambda m: m.role
        callings.record_participation = lambda *_a, **_kw: None
        discoveries = types.ModuleType("world.discoveries")
        discoveries.LANDMARKS = {
            "red_cord": {"room": "The Northern Treeline",
                         "key": "a frayed red cord"}}
        discoveries.normalize = lambda raw: []
        events = types.ModuleType("world.events")
        events.get_event_ledger = lambda: types.SimpleNamespace(
            get_event=lambda ident: self.events.get(ident))
        events.publish_world_event = lambda *_a, **_kw: None
        stubs = {
            "django": django, "django.db": db, "evennia": evennia,
            "evennia.scripts": scripts, "evennia.scripts.models": models,
            "evennia.utils": utils, "world.callings": callings,
            "world.discoveries": discoveries, "world.events": events,
        }
        path = ROOT / "spike/fvillage/world/route_work.py"
        spec = importlib.util.spec_from_file_location(
            "edge16_route_work_under_test", path)
        self.work = importlib.util.module_from_spec(spec)
        with patch.dict(sys.modules, stubs):
            spec.loader.exec_module(self.work)
        self.work._square = lambda: self.square
        self.work._day_hour = lambda: (self.day, self.hour)
        self.work.active_calling = lambda m: m.role
        self.work.record_participation = lambda *_a, **_kw: None
        self.work.get_event_ledger = events.get_event_ledger
        self.work.search = utils.search
        self.work.known_landmarks = lambda raw: raw or []

        def publish(kind, *, actor, payload, consequence):
            self.mutate()
            effect = consequence({"id": 41})
            self.events[41] = {
                "id": 41, "kind": kind, "status": "complete",
                "actor": {"account_id": actor.account.id, "mask_id": actor.id,
                          "mask": actor.key},
                "payload": payload, "consequence": effect,
            }
            self.published.append(kind)
            return {"id": 41}
        self.work.publish_world_event = publish

    def _prepare_report_landmarks(self):
        # The adapter's route lookup iterates all four canonical landmarks.
        # Supply the other three nonmatching rooms in this isolated fixture.
        self.work.LANDMARKS = {
            **{site: {"room": site, "key": site}
               for site in route_surveys.SITES if site != "red_cord"},
            "red_cord": {"room": "The Northern Treeline",
                         "key": "a frayed red cord"},
        }

    def test_signed_public_route_report_requires_same_account_clock_and_inspection(self):
        # Exercise the real report adapter, not only the pure state machine.
        for label, change in (
            ("account", lambda actor: setattr(
                actor, "account", types.SimpleNamespace(id=33))),
            ("clock", lambda actor: setattr(self, "hour", 12)),
            ("inspection", lambda actor: actor.db.landmark_latest_view[
                "red_cord"].update(day=4)),
            ("landmark", lambda actor: setattr(
                self.cord.db, "landmark_id", "replaced")),
            ("location", lambda actor: setattr(actor, "location", self.square)),
        ):
            with self.subTest(race=label):
                self.setUp()
                self._prepare_report_landmarks()
                actor = self._hound_renewal_actor()
                self.mutate = lambda: change(actor)
                with self.assertRaises(RuntimeError):
                    self.work.report(actor)
                self.assertEqual(
                    route_surveys.normalize(self.square.db.daily_route_survey)[
                        "reports"], {})
                self.assertEqual(self.published, [])

    def test_signed_public_route_report_commits_legitimate_firsthand_observation(self):
        self._prepare_report_landmarks()
        actor = self._hound_renewal_actor()
        result, error = self.work.report(actor)
        self.assertIsNone(error)
        self.assertEqual(result["count"], 1)
        self.assertEqual(self.published, ["village.route_inspected"])
        signed = self.events[result["event_id"]]
        self.assertEqual(signed["actor"]["account_id"], 11)
        restored = json.loads(json.dumps(self.square.db.daily_route_survey))
        self.assertEqual(restored["reports"]["red_cord"]["account_id"], 11)

    def test_independent_publication_has_verified_source_and_restart(self):
        result, error = self.work.publish_caution(self.mask)
        self.assertIsNone(error)
        self.assertEqual(result["source_event_id"], 40)
        self.assertEqual(self.published, ["village.route_caution_published"])
        state = json.loads(json.dumps(self.square.db.daily_route_survey))
        self.assertEqual(state["caution_notice"]["account_id"], 22)
        self.assertTrue(self.work._verified_notice(self.square, state, 4))

    def test_chronicler_must_independently_inspect_original_cord_today(self):
        # A signed Hound source alone must not let a remote editor publish.
        for change in (
            lambda: setattr(self.mask.db, "landmark_discoveries", []),
            lambda: setattr(self.mask.db, "landmark_latest_view", {}),
            lambda: setattr(self.mask.db, "landmark_latest_view",
                            {"red_cord": {"day": 3, "hour": 11}}),
            lambda: setattr(self.mask.db, "landmark_latest_view",
                            {"red_cord": {"day": 4, "hour": 9}}),
            lambda: setattr(self.mask.db, "landmark_latest_view",
                            {"red_cord": {"day": 4, "hour": "11"}}),
        ):
            with self.subTest(change=change):
                self.setUp()
                change()
                result, error = self.work.publish_caution(self.mask)
                self.assertIsNone(result)
                self.assertIn("Examine the real red cord", error)
                self.assertEqual(self.published, [])

    def test_chronicler_inspection_revoked_before_event_consequence(self):
        self.mutate = lambda: self.mask.db.landmark_latest_view.clear()
        with self.assertRaisesRegex(RuntimeError, "firsthand cord inspection changed"):
            self.work.publish_caution(self.mask)
        self.assertIsNone(self.square.db.daily_route_survey["caution_notice"])
        self.assertEqual(self.published, [])

    def test_missing_or_failed_hound_source_rejected_without_event(self):
        for change in (
            lambda: self.events[40].update(status="consequence_failed"),
            lambda: self.cord.db.route_caution.update(event_id=99),
            lambda: self.events[40]["actor"].update(account_id=33),
            lambda: self.events[40]["consequence"].update(cord_object_id=999),
        ):
            with self.subTest(change=change):
                self.setUp()
                change()
                result, error = self.work.publish_caution(self.mask)
                self.assertIsNone(result)
                self.assertIn("completed Hound protection", error)
                self.assertEqual(self.published, [])

    def test_wrong_role_room_and_same_account_denied(self):
        for attr, value in (
            ("role", "hound"), ("location", self.treeline),
            ("account", types.SimpleNamespace(
                id=11, sessions=types.SimpleNamespace(all=lambda: [object()]))),
        ):
            with self.subTest(attr=attr):
                self.setUp()
                setattr(self.mask, attr, value)
                result, error = self.work.publish_caution(self.mask)
                self.assertIsNone(result)
                self.assertTrue(error)
                self.assertEqual(self.published, [])

    def test_source_marker_changed_after_preview_fails_closed(self):
        self.mutate = lambda: self.cord.db.route_caution.update(event_id=99)
        with self.assertRaisesRegex(RuntimeError, "physical Hound source changed"):
            self.work.publish_caution(self.mask)
        self.assertIsNone(self.square.db.daily_route_survey["caution_notice"])
        self.assertEqual(self.published, [])

    def test_account_or_calling_switch_after_preview_fails_closed(self):
        for change in (
            lambda: setattr(self.mask, "role", "hound"),
            lambda: setattr(self.mask, "account", types.SimpleNamespace(
                id=33, sessions=types.SimpleNamespace(all=lambda: [object()]))),
            lambda: setattr(self.mask, "location", self.treeline),
        ):
            with self.subTest(change=change):
                self.setUp()
                self.mutate = change
                with self.assertRaisesRegex(RuntimeError, "changed account"):
                    self.work.publish_caution(self.mask)
                self.assertIsNone(self.square.db.daily_route_survey["caution_notice"])
                self.assertEqual(self.published, [])

    def test_disconnect_and_clock_race_fail_closed(self):
        for change in (
            lambda: setattr(self.account.sessions, "all", lambda: []),
            lambda: setattr(self, "hour", 13),
        ):
            with self.subTest(change=change):
                self.setUp()
                self.mutate = change
                with self.assertRaises(RuntimeError):
                    self.work.publish_caution(self.mask)
                self.assertIsNone(self.square.db.daily_route_survey["caution_notice"])
                self.assertEqual(self.published, [])

    def test_later_publication_rejected_without_duplicate_ledger(self):
        result, error = self.work.publish_caution(self.mask)
        self.assertIsNone(error)
        result, error = self.work.publish_caution(self.mask)
        self.assertIsNone(result)
        self.assertIn("already published", error)
        self.assertEqual(len(self.published), 1)


    def test_damaged_notice_cannot_create_second_signed_publication(self):
        result, error = self.work.publish_caution(self.mask)
        self.assertIsNone(error)
        self.assertEqual(result["event_id"], 41)
        damaged = json.loads(json.dumps(self.square.db.daily_route_survey))
        damaged["caution_notice"]["source_event_id"] = 999
        self.square.db.daily_route_survey = damaged
        self.assertFalse(self.work._verified_notice(
            self.square, route_surveys.normalize(damaged), 4))
        result, error = self.work.publish_caution(self.mask)
        self.assertIsNone(result)
        self.assertIn("already published", error)
        self.assertEqual(self.published, ["village.route_caution_published"])

    def _hound_renewal_actor(self):
        self.day, self.hour = 5, 11
        self.square.db.daily_route_survey = route_surveys.refresh(
            self.square.db.daily_route_survey, 5)
        return types.SimpleNamespace(
            id=111, key="Hound", role="hound", location=self.treeline,
            account=types.SimpleNamespace(
                id=11, sessions=types.SimpleNamespace(all=lambda: [object()])),
            db=types.SimpleNamespace(
                landmark_discoveries=[{"id": "red_cord"}],
                landmark_latest_view={"red_cord": {"day": 5}}),
        )

    def test_real_route_adapter_renews_verified_previous_day_cord(self):
        hound = self._hound_renewal_actor()
        result, error = self.work.field_action(hound, "protect")
        self.assertIsNone(error)
        self.assertEqual(result["event_id"], 41)
        self.assertEqual(self.cord.db.route_caution["prior_caution_event_id"], 40)
        self.assertEqual(self.cord.db.route_caution["day"], 5)
        self.assertEqual(self.cord.db.route_caution_history[0]["event_id"], 40)
        self.assertTrue(self.square.db.daily_route_survey[
            "field_decisions"]["hound"]["retied_previous_day"])

    def test_renewal_rejects_role_and_account_drift_before_consequence(self):
        for change in (
            lambda h: setattr(h, "role", "merchant"),
            lambda h: setattr(h, "account", types.SimpleNamespace(id=33)),
            lambda h: setattr(h, "location", self.square),
        ):
            with self.subTest(change=change):
                self.setUp()
                hound = self._hound_renewal_actor()
                self.mutate = lambda: change(hound)
                with self.assertRaisesRegex(RuntimeError, "changed account"):
                    self.work.field_action(hound, "protect")
                self.assertEqual(self.cord.db.route_caution["event_id"], 40)
                self.assertEqual(self.published, [])

    def test_renewal_rejects_forged_prior_physical_event(self):
        hound = self._hound_renewal_actor()
        self.events[40]["status"] = "consequence_failed"
        result, error = self.work.field_action(hound, "protect")
        self.assertIsNone(result)
        self.assertIn("older cord warning", error)
        self.assertEqual(self.cord.db.route_caution["event_id"], 40)

    def test_public_names_must_match_canonical_signed_actor_names(self):
        result, error = self.work.publish_caution(self.mask)
        self.assertIsNone(error)
        signed = self.square.db.daily_route_survey
        self.assertTrue(self.work._verified_notice(self.square, signed, 4))
        # A corrupted Square record cannot attribute a real Hound's act
        # to another person while preserving valid event and account IDs.
        forged_source = json.loads(json.dumps(signed))
        forged_source["field_decisions"]["hound"]["mask"] = "Another Hound"
        self.assertIsNone(self.work._signed_hound_source(
            types.SimpleNamespace(id=500, db=types.SimpleNamespace(
                daily_route_survey=forged_source)), 4, 23))
        # The public Chronicler label is likewise bound to the event actor.
        forged_notice = json.loads(json.dumps(signed))
        forged_notice["caution_notice"]["mask"] = "Another Chronicler"
        self.assertFalse(self.work._verified_notice(
            self.square, forged_notice, 4))
        # Even an intact Square record is not enough if the canonical
        # publication actor name no longer matches its signed provenance.
        self.events[41]["actor"]["mask"] = "Another Chronicler"
        self.assertFalse(self.work._verified_notice(self.square, signed, 4))

    def test_public_board_hides_forged_hound_name_without_erasing_record(self):
        result, error = self.work.publish_caution(self.mask)
        self.assertIsNone(error)
        state = json.loads(json.dumps(self.square.db.daily_route_survey))
        state["field_decisions"]["hound"]["mask"] = "Impersonated Hound"
        self.square.db.daily_route_survey = state
        # The full public board, not just the verified-notice helper, must
        # suppress the false attribution and any notice relying on it.
        self.work.LANDMARKS = {
            **self.work.LANDMARKS,
            **{site: {"room": site, "key": site}
               for site in route_surveys.SITES if site != "red_cord"},
        }
        display = self.work.status_lines()
        self.assertNotIn("Impersonated Hound", display)
        self.assertNotIn("published a Chronicler caution notice", display)
        self.assertEqual(
            self.square.db.daily_route_survey["field_decisions"]["hound"]["mask"],
            "Impersonated Hound",
        )  # projection is read-only; no invented state repair

    def test_tampered_published_event_is_not_displayable(self):
        result, error = self.work.publish_caution(self.mask)
        self.assertIsNone(error)
        self.events[41]["consequence"]["source_event_id"] = 999
        self.assertFalse(self.work._verified_notice(
            self.square, self.square.db.daily_route_survey, 4))


if __name__ == "__main__":
    unittest.main()
