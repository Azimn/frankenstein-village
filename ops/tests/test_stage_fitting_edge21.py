"""GDD-EDGE-21: finite rail, independent Smith/Performer and restart-safe rules."""
import json
import sys
import unittest
from collections import UserDict, UserList
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "spike/fvillage"))
from world import stage_fitting_edge21 as rail


def fit(raw=None, **overrides):
    p = dict(day=4, hour=10, event_id=102, account_id=7, mask_id=70,
             item_id=800, forge_event_id=101, workshop_id=90, tavern_id=91)
    p.update(overrides)
    return rail.fit(raw, **p)


def check(raw, **overrides):
    p = dict(day=4, hour=11, event_id=103, account_id=8, mask_id=80)
    p.update(overrides)
    return rail.soundcheck(raw, **p)


def play(raw, **overrides):
    p = dict(day=4, hour=12, event_id=104, account_id=8, mask_id=80, tune="reel")
    p.update(overrides)
    return rail.acoustic(raw, **p)


class StageRailTests(unittest.TestCase):
    def test_two_independent_accounts_change_real_rail_state(self):
        a, ok, why = fit()
        self.assertTrue(ok, why)
        self.assertEqual(a["condition"], "fitted")
        self.assertEqual(a["fitting"]["item_id"], 800)
        b, ok, why = check(a)
        self.assertTrue(ok, why)
        self.assertEqual(b["condition"], "ready")
        c, ok, why = play(b)
        self.assertTrue(ok, why)
        self.assertEqual(c["remaining"], 2)
        self.assertEqual(c["plays"][0]["soundcheck_event_id"], 103)
        self.assertEqual(rail.normalize(json.loads(json.dumps(c))), c)

    def test_smith_cannot_certify_own_work(self):
        a, _, _ = fit()
        for kw in (dict(account_id=7), dict(mask_id=70)):
            _state, ok, why = check(a, **kw)
            self.assertFalse(ok)
            self.assertIn("different", why)

    def test_no_play_without_real_fit_and_soundcheck(self):
        for raw in (None, rail.fresh()):
            _state, ok, why = play(raw)
            self.assertFalse(ok)
        a, _, _ = fit()
        _state, ok, why = play(a)
        self.assertFalse(ok)
        self.assertIn("soundchecked", why)

    def test_one_signed_set_per_day_and_three_use_material_limit(self):
        a, _, _ = fit()
        for day in (4, 5, 6):
            a, ok, why = check(a, day=day, hour=11, event_id=day * 10)
            self.assertTrue(ok, why)
            a, ok, why = play(a, day=day, hour=12, event_id=day * 10 + 1)
            self.assertTrue(ok, why)
            _duplicate, ok, why = play(a, day=day, hour=13, event_id=day * 10 + 2)
            self.assertFalse(ok)
        self.assertEqual(a["remaining"], 0)
        self.assertEqual(a["condition"], "spent")
        _state, ok, why = check(a, day=7, hour=10, event_id=70)
        self.assertFalse(ok)
        _state, ok, why = fit(a, day=7, event_id=71)
        self.assertFalse(ok)

    def test_replay_cannot_reopen_prior_day(self):
        a, _, _ = fit()
        a, _, _ = check(a)
        a, _, _ = play(a)
        _state, ok, why = check(a, day=4, hour=15, event_id=200)
        self.assertFalse(ok)
        _state, ok, why = play(a, day=5, hour=10, event_id=201)
        self.assertFalse(ok)
        self.assertIn("current day", why)

    def test_late_and_wrong_account_actions_denied(self):
        a, _, _ = fit()
        for kw in (dict(day=3), dict(day=4, hour=9), dict(day=True), dict(hour=24)):
            _state, ok, _why = check(a, **kw)
            self.assertFalse(ok)
        a, _, _ = check(a)
        for kw in (dict(account_id=9), dict(mask_id=81), dict(hour=10),
                   dict(day=5), dict(tune="unheard")):
            _state, ok, _why = play(a, **kw)
            self.assertFalse(ok)

    def test_signed_ids_and_invalid_persistence_fail_closed(self):
        for kw in (dict(event_id=True), dict(item_id=0), dict(forge_event_id=-1),
                   dict(tavern_id="91"), dict(hour=-1)):
            _state, ok, _why = fit(**kw)
            self.assertFalse(ok)
        a, _, _ = fit()
        a, _, _ = check(a)
        a, _, _ = play(a)
        for broken in (
            dict(a, remaining=3),
            dict(a, condition="spent"),
            dict(a, fitting=dict(a["fitting"], event_id=0)),
            dict(a, soundcheck=dict(a["soundcheck"], account_id=7)),
            dict(a, plays=[dict(a["plays"][0], tune="ghost")]),
            dict(a, plays="fake"),
            dict(condition="worn", fitting=None, soundcheck=None,
                 plays=a["plays"], remaining=0),
        ):
            self.assertEqual(rail.normalize(broken)["condition"], "invalid")
            _state, ok, _why = play(broken, day=5)
            self.assertFalse(ok)

    def test_persisted_current_day_set_must_match_latest_soundcheck(self):
        state, ok, why = fit()
        self.assertTrue(ok, why)
        state, ok, why = check(state)
        self.assertTrue(ok, why)
        state, ok, why = play(state)
        self.assertTrue(ok, why)
        # A shape-valid Attribute must not turn a forged same-day play into
        # a public claim about remaining physical stage-rail capacity.
        for field, forged in (
            ("soundcheck_event_id", 999),
            ("account_id", 999),
            ("mask_id", 999),
            ("day", 5),
            ("hour", 10),
            ("event_id", state["soundcheck"]["event_id"]),
            ("event_id", state["fitting"]["event_id"]),
        ):
            with self.subTest(field=field, forged=forged):
                broken = json.loads(json.dumps(state))
                broken["plays"][0][field] = forged
                self.assertEqual(rail.normalize(broken)["condition"], "invalid")
                self.assertIn("inconsistent", rail.public_lines(broken))
                _result, allowed, _reason = play(broken, day=5)
                self.assertFalse(allowed)
        # Older sets legitimately reference earlier soundchecks, while the
        # physical record stores only the newest check. Do not reject them.
        renewed, ok, why = check(state, day=5, hour=11, event_id=205)
        self.assertTrue(ok, why)
        self.assertEqual(rail.normalize(json.loads(json.dumps(renewed))), renewed)
        played, ok, why = play(renewed, day=5, hour=12, event_id=206)
        self.assertTrue(ok, why)
        self.assertEqual(rail.normalize(json.loads(json.dumps(played))), played)

    def test_evennia_style_persistence_wrappers_and_json_restart(self):
        a, _, _ = fit()
        a, _, _ = check(a)
        a, _, _ = play(a)
        wrapped = UserDict(a)
        wrapped["fitting"] = UserDict(a["fitting"])
        wrapped["soundcheck"] = UserDict(a["soundcheck"])
        wrapped["plays"] = UserList([UserDict(p) for p in a["plays"]])
        self.assertEqual(rail.normalize(wrapped), a)
        self.assertEqual(rail.normalize(json.loads(json.dumps(a))), a)

    def test_signed_event_ids_cannot_alias_their_own_sources(self):
        _state, ok, _why = fit(forge_event_id=102)
        self.assertFalse(ok)
        state, ok, why = fit()
        self.assertTrue(ok, why)
        for event_id in (101, 102):
            with self.subTest(action="soundcheck", event_id=event_id):
                _state, ok, _why = check(state, event_id=event_id)
                self.assertFalse(ok)
        state, ok, why = check(state)
        self.assertTrue(ok, why)
        for event_id in (101, 102, 103):
            with self.subTest(action="acoustic", event_id=event_id):
                _state, ok, _why = play(state, event_id=event_id)
                self.assertFalse(ok)
        state, ok, why = play(state)
        self.assertTrue(ok, why)
        for event_id in (101, 102, 103, 104):
            with self.subTest(action="renew", event_id=event_id):
                _state, ok, _why = check(state, day=5, event_id=event_id)
                self.assertFalse(ok)
        renewed, ok, why = check(state, day=5, event_id=205)
        self.assertTrue(ok, why)
        for event_id in (101, 102, 103, 104, 205):
            with self.subTest(action="second_set", event_id=event_id):
                _state, ok, _why = play(renewed, day=5, event_id=event_id)
                self.assertFalse(ok)
        second, ok, why = play(renewed, day=5, event_id=206)
        self.assertTrue(ok, why)
        self.assertEqual(rail.normalize(json.loads(json.dumps(second))), second)

    def test_persisted_source_id_aliases_fail_closed_in_public_status(self):
        state, _, _ = fit()
        state, _, _ = check(state)
        state, _, _ = play(state)
        state, _, _ = check(state, day=5, event_id=205)
        state, _, _ = play(state, day=5, event_id=206)
        for group, field, alias in (
            ("fitting", "forge_event_id", 102),
            ("soundcheck", "event_id", 101),
            ("soundcheck", "event_id", 104),
            ("plays", "event_id", 103),
        ):
            with self.subTest(group=group, field=field, alias=alias):
                forged = json.loads(json.dumps(state))
                if group == "plays":
                    forged["plays"][1][field] = alias
                else:
                    forged[group][field] = alias
                self.assertEqual(rail.normalize(forged)["condition"], "invalid")
                self.assertIn("inconsistent", rail.public_lines(forged))
        self.assertEqual(rail.normalize(json.loads(json.dumps(state))), state)

    def test_existing_stage_solo_rehearsal_not_replaced(self):
        from world import stage_state
        s, ok, why = stage_state.rehearse(
            None, day=4, hour=10, account_id=8, mask_id=80,
            mask="Performer", tune="ballad", event_id=44)
        self.assertTrue(ok, why)
        s, ok, why = stage_state.perform(
            s, day=4, hour=11, account_id=8, mask_id=80,
            mask="Performer", tune="ballad", event_id=45)
        self.assertTrue(ok, why)
        self.assertEqual(s["performance"]["event_id"], 45)


if __name__ == "__main__":
    unittest.main()
