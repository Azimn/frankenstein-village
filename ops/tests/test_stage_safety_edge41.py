"""GDD-EDGE-41: independent Hound warning and Performer decision rules.

These pure tests cover state and negative cases. The live ledger and physical
source adapter require separate authenticated Evennia integration testing.
"""
import json
import copy
import ast
from collections.abc import Mapping
from collections import UserDict
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "spike/fvillage"))
from world import stage_state as stage


def who(account=11, mask=111, event=100, day=1, hour=20, name="Player"):
    return {"day": day, "hour": hour, "account_id": account,
            "mask_id": mask, "mask": name, "event_id": event}


def warning(raw=None, **overrides):
    args = who()
    args.update(overrides)
    return stage.warn(raw, source_event_id=90, cord_id=777, **args)


def decision(raw, choice="indoor", **overrides):
    args = who(account=22, mask=222, event=101, name="Performer")
    args.update(overrides)
    return stage.adapt(raw, choice=choice, **args)


class StageSafetyTests(unittest.TestCase):
    def test_signed_warning_requires_independent_performer_choice(self):
        state, ok, why = warning()
        self.assertTrue(ok, why)
        state, ok, why = stage.rehearse(state, tune="ballad", **who(account=22, mask=222, event=102))
        self.assertTrue(ok, why)
        before = stage.normalize(state)
        blocked, ok, why = stage.perform(state, tune="ballad", **who(account=22, mask=222, event=103))
        self.assertFalse(ok)
        self.assertIn("requires a Performer decision", why)
        self.assertEqual(blocked, before)
        state, ok, why = decision(state)
        self.assertTrue(ok, why)
        state, ok, why = stage.perform(state, tune="ballad", **who(account=22, mask=222, event=104))
        self.assertTrue(ok, why)
        self.assertEqual(state["performance"]["safety_mode"], "indoor")
        self.assertEqual(state["performance"]["safety_decision_event_id"], 101)
        self.assertEqual(state["safety_decision"]["warning_event_id"], 100)

    def test_cancel_blocks_show_and_retains_restart_history(self):
        state, ok, why = warning()
        self.assertTrue(ok, why)
        state, ok, why = decision(state, "cancel")
        self.assertTrue(ok, why)
        state, ok, why = stage.rehearse(state, tune="reel", **who(account=22, mask=222, event=102))
        self.assertTrue(ok, why)
        _, ok, why = stage.perform(state, tune="reel", **who(account=22, mask=222, event=103))
        self.assertFalse(ok)
        self.assertIn("cancelled", why)
        restored = json.loads(json.dumps(state))
        self.assertEqual(stage.normalize(restored)["safety_decision"]["choice"], "cancel")
        next_day = stage.refresh(restored, 2)
        self.assertIsNone(next_day["safety_decision"])
        self.assertIsNone(next_day["safety_warning"])
        self.assertEqual(next_day["history"][-1]["safety_decision"]["choice"], "cancel")
        self.assertIn("Previous stage decision", stage.public_lines(next_day, 2))

    def test_no_warning_no_adaptation(self):
        before = stage.normalize(None)
        after, ok, why = decision(None)
        self.assertFalse(ok)
        self.assertIn("warning", why)
        self.assertEqual(before, after)

    def test_same_account_role_switch_denied(self):
        state, ok, _ = warning()
        self.assertTrue(ok)
        _, ok, why = decision(state, account_id=11, mask_id=333)
        self.assertFalse(ok)
        self.assertIn("Hound", why)

    def test_duplicates_are_denied(self):
        state, ok, _ = warning()
        self.assertTrue(ok)
        _, ok, why = warning(state, event_id=120)
        self.assertFalse(ok)
        self.assertIn("already signed", why)
        state, ok, _ = decision(state)
        self.assertTrue(ok)
        _, ok, why = decision(state, event_id=130, choice="cancel")
        self.assertFalse(ok)
        self.assertIn("already signed", why)

    def test_retroactive_warning_and_adaptation_denied(self):
        state, ok, _ = stage.rehearse(None, tune="ballad", **who(account=22, mask=222))
        self.assertTrue(ok)
        state, ok, _ = stage.perform(state, tune="ballad", **who(account=22, mask=222, event=101))
        self.assertTrue(ok)
        _, ok, why = warning(state)
        self.assertFalse(ok)
        self.assertIn("retroactively", why)

    def test_bad_ids_time_and_choices_fail_closed(self):
        for overrides in ({"account_id": True}, {"mask_id": 0},
                          {"event_id": "bad"}, {"day": 0},
                          {"hour": 24}, {"hour": -1}):
            with self.subTest(overrides=overrides):
                _, ok, _ = warning(**overrides)
                self.assertFalse(ok)
        state, ok, _ = warning()
        self.assertTrue(ok)
        for choice in ("teleport", "", None):
            _, ok, why = decision(state, choice)
            self.assertFalse(ok)
            self.assertIn("Choose", why)
        _, ok, why = decision(state, day=0)
        self.assertFalse(ok)
        self.assertIn("rewound", why)

    def test_fractional_signed_ids_and_hours_fail_closed(self):
        # Signed event, actor and time fields must never be truncated from
        # floats or fractional strings into valid-looking stage evidence.
        for invalid in (11.5, 11.0, "11.5", True):
            for field in ("account_id", "mask_id", "event_id"):
                with self.subTest(field=field, invalid=invalid):
                    _, ok, _ = warning(**{field: invalid})
                    self.assertFalse(ok)
        for invalid in (90.5, 90.0, "90.5", True):
            with self.subTest(source_event_id=invalid):
                _, ok, _ = stage.warn(
                    None, source_event_id=invalid, cord_id=777, **who()
                )
                self.assertFalse(ok)
        for invalid in (20.5, 20.0, "20.5", True):
            with self.subTest(hour=invalid):
                _, ok, _ = warning(hour=invalid)
                self.assertFalse(ok)
        state, ok, why = warning()
        self.assertTrue(ok, why)
        for invalid in (22.5, 22.0, "22.5", True):
            with self.subTest(performer_account=invalid):
                _, ok, _ = decision(state, account_id=invalid)
                self.assertFalse(ok)
        corrupted = copy.deepcopy(state)
        corrupted["safety_warning"]["source_event_id"] = 90.5
        self.assertIsNone(stage.normalize(corrupted)["safety_warning"])
        corrupted = copy.deepcopy(state)
        corrupted["safety_warning"]["hour"] = 20.5
        self.assertIsNone(stage.normalize(corrupted)["safety_warning"])
        corrupted = copy.deepcopy(state)
        corrupted["day"] = 1.5
        self.assertIsNone(stage.normalize(corrupted)["safety_warning"])
        # Legitimate decimal-string IDs and hours remain accepted.
        valid, ok, why = stage.warn(
            None, source_event_id="90", cord_id="777",
            **who(account="11", mask="111", event="100", hour="20")
        )
        self.assertTrue(ok, why)
        self.assertEqual(valid["safety_warning"]["source_event_id"], 90)

    def test_day_rollover_cannot_reuse_old_warning(self):
        state, ok, _ = warning()
        self.assertTrue(ok)
        tomorrow = stage.refresh(state, 2)
        _, ok, why = decision(tomorrow, day=2, hour=10)
        self.assertFalse(ok)
        self.assertIn("warning", why)

    def test_corrupt_warning_and_same_account_persisted_decision_ignored(self):
        state, ok, _ = warning()
        self.assertTrue(ok)
        state["safety_decision"] = {"account_id": 11, "mask_id": 333,
                                    "event_id": 200, "warning_event_id": 100,
                                    "hour": 20, "choice": "indoor"}
        self.assertIsNone(stage.normalize(state)["safety_decision"])
        state["safety_warning"]["source_event_id"] = False
        self.assertIsNone(stage.normalize(state)["safety_warning"])

    def test_verified_hound_source_requires_completed_ledger_and_original_cord(self):
        route = {"day": 1, "field_decisions": {
            "hound": {"account_id": 11, "event_id": 90}}}
        marker = {"account_id": 11, "event_id": 90, "day": 1}
        event = {
            "id": 90, "kind": "village.route_protected", "status": "complete",
            "actor": {"account_id": 11, "mask_id": 111},
            "payload": {"site": "red_cord", "role": "hound",
                        "action": "protect", "location": "Northern Treeline",
                        "day": 1, "hour": 19},
            "consequence": {"cord_object_id": 777, "square_room_id": 88,
                            "role": "hound", "action": "protect",
                            "day": 1, "caution_marked": True},
        }
        kwargs = dict(account_id=11, mask_id=111, source_event_id=90,
                      cord_id=777, square_id=88, day=1, hour=20,
                      room_name="Northern Treeline")
        check = stage.verified_hound_source
        self.assertTrue(check(route, event, marker, **kwargs))
        # Evennia persistence can return mapping wrappers rather than plain
        # dicts. Valid completed evidence must remain usable after reload.
        wrapped_route = UserDict({
            **route,
            "field_decisions": UserDict({
                "hound": UserDict(route["field_decisions"]["hound"]),
            }),
        })
        wrapped_event = UserDict({
            **event,
            "actor": UserDict(event["actor"]),
            "payload": UserDict(event["payload"]),
            "consequence": UserDict(event["consequence"]),
        })
        self.assertTrue(check(
            wrapped_route, wrapped_event, UserDict(marker), **kwargs,
        ))
        for path, invalid in (
            (("status",), "consequence_failed"),
            (("kind",), "village.route_passability_observed"),
            (("id",), 999),
            (("actor", "account_id"), 22),
            (("actor", "mask_id"), 333),
            (("payload", "site"), "market_scale"),
            (("payload", "role"), "wanderer"),
            (("payload", "day"), 2),
            (("payload", "hour"), 21),
            (("payload", "hour"), True),
            (("consequence", "cord_object_id"), 999),
            (("consequence", "square_room_id"), 999),
            (("consequence", "caution_marked"), False),
        ):
            with self.subTest(path=path):
                forged = copy.deepcopy(event)
                node = forged
                for key in path[:-1]:
                    node = node[key]
                node[path[-1]] = invalid
                self.assertFalse(check(route, forged, marker, **kwargs))
        self.assertFalse(check(route, None, marker, **kwargs))
        self.assertFalse(check(route, event, {**marker, "event_id": 999}, **kwargs))
        self.assertFalse(check({**route, "day": 2}, event, marker, **kwargs))
        self.assertFalse(check(route, event, marker, **{**kwargs, "hour": 18}))

    def test_malformed_nested_hound_evidence_fails_closed(self):
        # Persisted ledger or route structures can be malformed after a bad
        # import or partial restore. They must not crash the stage command or
        # count as evidence that the Hound physically protected the cord.
        route = {"day": 1, "field_decisions": {
            "hound": {"account_id": 11, "event_id": 90}}}
        marker = {"account_id": 11, "event_id": 90, "day": 1}
        event = {
            "id": 90, "kind": "village.route_protected", "status": "complete",
            "actor": {"account_id": 11, "mask_id": 111},
            "payload": {"site": "red_cord", "role": "hound",
                        "action": "protect", "location": "Northern Treeline",
                        "day": 1, "hour": 19},
            "consequence": {"cord_object_id": 777, "square_room_id": 88,
                            "role": "hound", "action": "protect",
                            "day": 1, "caution_marked": True},
        }
        args = dict(account_id=11, mask_id=111, source_event_id=90,
                    cord_id=777, square_id=88, day=1, hour=20,
                    room_name="Northern Treeline")
        verify = stage.verified_hound_source
        self.assertTrue(verify(route, event, marker, **args))
        for field in ("actor", "payload", "consequence"):
            for malformed in (["bad"], "bad", 17, None):
                with self.subTest(field=field, malformed=malformed):
                    broken = copy.deepcopy(event)
                    broken[field] = malformed
                    self.assertFalse(verify(route, broken, marker, **args))
        for malformed in (["bad"], "bad", 17, None):
            with self.subTest(route_decisions=malformed):
                broken_route = {**route, "field_decisions": malformed}
                self.assertFalse(verify(broken_route, event, marker, **args))
            with self.subTest(hound_entry=malformed):
                broken_route = {**route, "field_decisions": {"hound": malformed}}
                self.assertFalse(verify(broken_route, event, marker, **args))

    def test_persisted_performer_decision_cannot_predate_hound_warning(self):
        state, ok, why = warning(hour=21)
        self.assertTrue(ok, why)
        state, ok, why = decision(state, hour=21)
        self.assertTrue(ok, why)
        forged = copy.deepcopy(state)
        forged["safety_decision"]["hour"] = 20
        normalized = stage.normalize(forged)
        self.assertIsNotNone(normalized["safety_warning"])
        self.assertIsNone(normalized["safety_decision"])
        # A missing valid decision never silently authorizes a show.
        state, ok, why = stage.rehearse(
            normalized, tune="ballad",
            **who(account=22, mask=222, event=202, hour=21))
        self.assertTrue(ok, why)
        _, ok, why = stage.perform(
            state, tune="ballad",
            **who(account=22, mask=222, event=203, hour=21))
        self.assertFalse(ok)
        self.assertIn("requires a Performer decision", why)

    def test_rehearsal_cannot_follow_performance_after_clock_rewind(self):
        # A real rehearsal at hour 21 cannot authorize an hour-20 show,
        # even if the village clock or a persisted stage record is rewound.
        state, ok, why = stage.rehearse(
            None, tune="ballad",
            **who(account=22, mask=222, event=200, hour=21))
        self.assertTrue(ok, why)
        before = stage.normalize(state)
        unchanged, ok, why = stage.perform(
            state, tune="ballad",
            **who(account=22, mask=222, event=201, hour=20))
        self.assertFalse(ok)
        self.assertIn("rehearsal cannot occur after", why)
        self.assertEqual(unchanged, before)
        self.assertIsNone(unchanged["performance"])
        state, ok, why = stage.perform(
            state, tune="ballad",
            **who(account=22, mask=222, event=202, hour=21))
        self.assertTrue(ok, why)
        self.assertEqual(state["performance"]["rehearsal_event_id"], 200)

    def test_warning_and_decision_chronology_cannot_be_reversed(self):
        state, ok, _ = warning(hour=20)
        self.assertTrue(ok)
        _, ok, why = decision(state, hour=19)
        self.assertFalse(ok)
        self.assertIn("not happened yet", why)
        state, ok, _ = decision(state, hour=21)
        self.assertTrue(ok)
        state, ok, _ = stage.rehearse(state, tune="ballad", **who(
            account=22, mask=222, event=102, hour=21))
        self.assertTrue(ok)
        _, ok, why = stage.perform(state, tune="ballad", **who(
            account=22, mask=222, event=103, hour=20))
        self.assertFalse(ok)
        self.assertIn("after this performance", why)

    def test_adapter_public_status_rejects_forged_stage_projection(self):
        # Execute the real pure adapter helper without importing Django or
        # Evennia. The authenticated client/restart gate remains separate.
        source = (Path(__file__).resolve().parents[2]
                  / "spike/fvillage/world/stage_work.py").read_text()
        tree = ast.parse(source)
        helper = next(node for node in tree.body
                      if isinstance(node, ast.FunctionDef)
                      and node.name == "_verified_public_status")
        gates = {"warning": False, "decision": False}
        seen = []
        def verify_warning(raw, day, hour):
            seen.append(("warning", day, hour))
            return gates["warning"]
        def verify_decision(raw, day, hour):
            seen.append(("decision", day, hour))
            return gates["decision"]
        scope = {
            "stage_state": stage, "Mapping": Mapping,
            "_verified_warning": verify_warning,
            "_verified_decision": verify_decision,
        }
        exec(compile(ast.Module(body=[helper], type_ignores=[]),
                     "<actual-stage-status-adapter>", "exec"), scope)
        public = scope["_verified_public_status"]

        original, ok, why = warning()
        self.assertTrue(ok, why)
        original, ok, why = decision(original)
        self.assertTrue(ok, why)
        saved = copy.deepcopy(original)
        forged = public(original, 1, 21)
        self.assertNotIn("A Hound signed", forged)
        self.assertNotIn("A Performer chose", forged)
        self.assertIn("could not be verified", forged)
        self.assertEqual(seen, [("warning", 1, 21)])
        self.assertEqual(original, saved)  # Never mutate persistent evidence.

        gates["warning"] = True
        seen.clear()
        partial = public(original, 1, 21)
        self.assertIn("A Hound signed", partial)
        self.assertNotIn("A Performer chose", partial)
        self.assertIn("could not be verified", partial)
        self.assertEqual(seen, [("warning", 1, 21), ("decision", 1, 21)])

        gates["decision"] = True
        verified = public(original, 1, 21)
        self.assertIn("A Hound signed", verified)
        self.assertIn("A Performer chose indoor", verified)
        self.assertNotIn("could not be verified", verified)

        later = stage.refresh(original, 2)
        historical = public(later, 2, 9)
        self.assertNotIn("Previous stage decision:", historical)
        self.assertIn("Earlier stage safety choices require", historical)
        self.assertEqual(later["history"][-1]["safety_decision"]["choice"], "indoor")

        scope["_verified_warning"] = lambda *_: (_ for _ in ()).throw(KeyError("ledger"))
        # The helper's global namespace is scope, so a missing ledger
        # cannot turn a mutable warning into a signed public claim.
        broken = public(original, 1, 21)
        self.assertNotIn("A Hound signed", broken)
        self.assertNotIn("A Performer chose", broken)
        self.assertIn("could not be verified", broken)

    def test_public_status_does_not_invent_crowd(self):
        state, ok, _ = warning()
        self.assertTrue(ok)
        state, ok, _ = decision(state)
        self.assertTrue(ok)
        lines = stage.public_lines(state, 1)
        self.assertIn("Hound signed", lines)
        self.assertIn("Performer chose indoor", lines)
        self.assertIn("No public performance", lines)
        self.assertNotIn("attended", lines)


if __name__ == "__main__":
    unittest.main()
