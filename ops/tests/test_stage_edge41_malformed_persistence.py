"""EDGE-41: malformed persisted stage containers must fail closed.

These are pure production-state tests. Authenticated two-account gameplay and
actual Evennia restart assertions remain in the clean-checkout regression.
"""
import sys
import unittest
from collections import UserDict, UserList
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "spike/fvillage"))
from world import stage_state as stage


class MalformedStagePersistenceTests(unittest.TestCase):
    def test_non_sequence_rehearsals_and_history_do_not_crash_or_grant_show(self):
        for malformed in (17, True, "not a record", {"fake": "row"}, object()):
            with self.subTest(value=type(malformed).__name__):
                raw = {"day": 4, "rehearsals": malformed,
                       "history": malformed, "witnesses": malformed}
                state = stage.normalize(raw)
                self.assertEqual(state["rehearsals"], [])
                self.assertEqual(state["history"], [])
                self.assertIsNone(state["performance"])
                self.assertIn("No public performance", stage.public_lines(raw, 4))
                _, allowed, reason = stage.perform(
                    raw, day=4, hour=20, account_id=11, mask_id=111,
                    mask="Performer", tune="ballad", event_id=99)
                self.assertFalse(allowed)
                self.assertIn("Rehearse", reason)

    def test_malformed_witnesses_do_not_create_phantom_audience(self):
        state, ok, reason = stage.rehearse(
            None, day=4, hour=19, account_id=11, mask_id=111,
            mask="Performer", tune="ballad", event_id=90)
        self.assertTrue(ok, reason)
        state, ok, reason = stage.perform(
            state, day=4, hour=20, account_id=11, mask_id=111,
            mask="Performer", tune="ballad", event_id=91,
            audience_account_ids=[22])
        self.assertTrue(ok, reason)
        for malformed in (23, "witness", {"account_id": 22}, True):
            with self.subTest(value=malformed):
                restored = {**state, "witnesses": malformed}
                self.assertEqual(stage.normalize(restored)["witnesses"], [])
                self.assertIn("0 other player account(s) witnessed",
                              stage.public_lines(restored, 4))

    def test_malformed_historical_nested_rows_are_not_public_claims(self):
        raw = {"day": 5, "history": [
            {"day": 4, "performance": "forged",
             "safety_decision": 7},
            UserDict({"day": 3, "performance": ["invalid"],
                      "safety_decision": "cancel"}),
        ]}
        lines = stage.public_lines(raw, 5)
        self.assertNotIn("Previous recorded show:", lines)
        self.assertNotIn("Previous stage decision:", lines)
        self.assertEqual(len(stage.normalize(raw)["history"]), 2)

    def test_valid_mapping_wrappers_and_real_history_still_render(self):
        raw = UserDict({"day": 5, "history": [
            UserDict({"day": 4, "performance": UserDict({
                "mask": "Actual Performer"}), "safety_decision": None}),
        ]})
        self.assertIn("Previous recorded show: Actual Performer, day 4",
                      stage.public_lines(raw, 5))


    def test_evennia_style_mutable_sequence_preserves_rehearsal_and_replay_guard(self):
        # Evennia wraps Attribute lists as _SaverList, a MutableSequence
        # rather than a builtin list. UserList reproduces this interface.
        state, ok, reason = stage.rehearse(
            None, day=4, hour=19, account_id=11, mask_id=111,
            mask="Performer", tune="ballad", event_id=90)
        self.assertTrue(ok, reason)
        wrapped = {**state, "rehearsals": UserList([
            UserDict(row) for row in state["rehearsals"]])}
        self.assertEqual(len(stage.normalize(wrapped)["rehearsals"]), 1)
        denied, ok, reason = stage.rehearse(
            wrapped, day=4, hour=20, account_id=11, mask_id=111,
            mask="Performer", tune="ballad", event_id=91)
        self.assertFalse(ok)
        self.assertIn("already rehearsed", reason)
        self.assertEqual(len(denied["rehearsals"]), 1)
        played, ok, reason = stage.perform(
            wrapped, day=4, hour=20, account_id=11, mask_id=111,
            mask="Performer", tune="ballad", event_id=92,
            audience_account_ids=[22])
        self.assertTrue(ok, reason)
        self.assertEqual(played["performance"]["rehearsal_event_id"], 90)

    def test_evennia_style_mutable_sequence_preserves_witnesses_and_history(self):
        state, ok, reason = stage.rehearse(
            None, day=4, hour=19, account_id=11, mask_id=111,
            mask="Performer", tune="reel", event_id=100)
        self.assertTrue(ok, reason)
        state, ok, reason = stage.perform(
            state, day=4, hour=20, account_id=11, mask_id=111,
            mask="Performer", tune="reel", event_id=101,
            audience_account_ids=[22])
        self.assertTrue(ok, reason)
        state["witnesses"] = UserList([
            UserDict({"account_id": 22, "event_id": 102})])
        state["history"] = UserList([
            UserDict({"day": 3, "performance": UserDict({
                "mask": "Prior Performer"}), "safety_decision": None})])
        restored = stage.normalize(state)
        self.assertEqual(len(restored["witnesses"]), 1)
        self.assertEqual(restored["witnesses"][0]["account_id"], 22)
        self.assertEqual(len(restored["history"]), 1)
        self.assertIn("Previous recorded show: Prior Performer, day 3",
                      stage.public_lines(state, 4))


    def test_corrupt_audience_eligibility_cannot_crash_or_create_witnesses(self):
        state, ok, reason = stage.rehearse(
            None, day=4, hour=19, account_id=11, mask_id=111,
            mask="Performer", tune="ballad", event_id=90)
        self.assertTrue(ok, reason)
        state, ok, reason = stage.perform(
            state, day=4, hour=20, account_id=11, mask_id=111,
            mask="Performer", tune="ballad", event_id=91,
            audience_account_ids=[22])
        self.assertTrue(ok, reason)
        for corrupt in (None, 22, True, "22", {"account": 22}, object()):
            with self.subTest(kind=type(corrupt).__name__):
                forged = {**state, "performance": {
                    **state["performance"], "eligible_audience_ids": corrupt,
                }, "witnesses": [{"account_id": 22, "event_id": 92}]}
                restored = stage.normalize(forged)
                self.assertEqual(
                    restored["performance"]["eligible_audience_ids"], [])
                self.assertEqual(restored["witnesses"], [])
                _, allowed, error = stage.witness(
                    forged, day=4, hour=20, account_id=22, mask_id=222,
                    mask="Listener", event_id=93)
                self.assertFalse(allowed)
                self.assertIn("present for the actual performance", error)
                self.assertIn(
                    "0 other player account(s) witnessed",
                    stage.public_lines(forged, 4))

    def test_persisted_audience_eligibility_is_bounded_and_independent(self):
        state, ok, reason = stage.rehearse(
            None, day=4, hour=19, account_id=11, mask_id=111,
            mask="Performer", tune="reel", event_id=100)
        self.assertTrue(ok, reason)
        state, ok, reason = stage.perform(
            state, day=4, hour=20, account_id=11, mask_id=111,
            mask="Performer", tune="reel", event_id=101,
            audience_account_ids=[22])
        self.assertTrue(ok, reason)
        wrapped = {**state, "performance": {
            **state["performance"],
            "eligible_audience_ids": UserList([22, 22, 11, True, "bad"]),
        }, "witnesses": UserList([
            UserDict({"account_id": 22, "event_id": 102}),
            UserDict({"account_id": 22, "event_id": 103}),
            UserDict({"account_id": 33, "event_id": 104}),
        ])}
        restored = stage.normalize(wrapped)
        self.assertEqual(
            restored["performance"]["eligible_audience_ids"], [22])
        self.assertEqual(len(restored["witnesses"]), 1)
        self.assertEqual(restored["witnesses"][0]["event_id"], 102)
        _, allowed, error = stage.witness(
            wrapped, day=4, hour=20, account_id=22, mask_id=222,
            mask="Listener", event_id=105)
        self.assertFalse(allowed)
        self.assertIn("already witnessed", error)

    def test_historical_day_strings_normalize_without_future_claims(self):
        state = {"day": 5, "history": UserList([
            UserDict({"day": "4", "performance": UserDict({
                "mask": "Earlier Performer"})}),
            UserDict({"day": 8, "performance": UserDict({
                "mask": "Future Forgery"})}),
            UserDict({"day": "invalid", "performance": UserDict({
                "mask": "Bad Date"})}),
        ])}
        restored = stage.normalize(state)
        self.assertEqual(len(restored["history"]), 1)
        self.assertEqual(restored["history"][0]["day"], 4)
        status = stage.public_lines(state, 5)
        self.assertIn("Previous recorded show: Earlier Performer, day 4", status)
        self.assertNotIn("Future Forgery", status)



    def test_player_facing_stage_help_avoids_evennia_color_pipe_sequences(self):
        # Evennia consumes a vertical bar as an inline markup introducer.
        # A help string such as "indoor|cancel" visibly becomes "indoorancel".
        status = stage.public_lines(stage.fresh(4), 4)
        self.assertIn("stage adapt indoor or stage adapt cancel", status)
        self.assertIn("stage rehearse ballad or stage rehearse reel", status)
        self.assertIn("stage perform ballad or stage perform reel", status)
        self.assertNotIn("|", status)

        command_source = (
            Path(__file__).resolve().parents[2]
            / "spike/fvillage/commands/stage_cmd.py"
        ).read_text(encoding="utf-8")
        self.assertIn(
            "stage adapt indoor or stage adapt cancel", command_source
        )
        self.assertNotIn("ballad|reel", command_source)
        self.assertNotIn("indoor|cancel", command_source)


    def test_persisted_numeric_string_rehearsal_and_show_are_canonical(self):
        state, ok, reason = stage.rehearse(
            None, day=4, hour=19, account_id=11, mask_id=111,
            mask="Performer", tune="ballad", event_id=90)
        self.assertTrue(ok, reason)
        restored = {**state, "rehearsals": [{
            **state["rehearsals"][0],
            "account_id": "11", "mask_id": "111",
            "event_id": "90", "hour": "19",
        }]}
        self.assertEqual(stage.normalize(restored)["rehearsals"][0]["hour"], 19)
        self.assertEqual(stage.normalize(restored)["rehearsals"][0]["account_id"], 11)
        _, ok, reason = stage.rehearse(
            restored, day=4, hour=20, account_id=11, mask_id=111,
            mask="Performer", tune="ballad", event_id=91)
        self.assertFalse(ok)
        self.assertIn("already rehearsed", reason)
        played, ok, reason = stage.perform(
            restored, day=4, hour=20, account_id=11, mask_id=111,
            mask="Performer", tune="ballad", event_id=92,
            audience_account_ids=[22])
        self.assertTrue(ok, reason)
        restored_show = {**played, "performance": {
            **played["performance"], "account_id": "11",
            "mask_id": "111", "event_id": "92", "hour": "20",
        }}
        self.assertEqual(stage.normalize(restored_show)["performance"]["hour"], 20)
        self.assertIn("hour 20", stage.public_lines(restored_show, 4))
        _, ok, reason = stage.perform(
            restored_show, day=4, hour=20, account_id=11, mask_id=111,
            mask="Performer", tune="ballad", event_id=93)
        self.assertFalse(ok)
        self.assertIn("already taken place", reason)
        witnessed, ok, reason = stage.witness(
            restored_show, day=4, hour=20, account_id=22, mask_id=222,
            mask="Witness", event_id=94)
        self.assertTrue(ok, reason)
        self.assertEqual(len(witnessed["witnesses"]), 1)

    def test_persisted_numeric_string_warning_and_decision_remain_consistent(self):
        state, ok, reason = stage.warn(
            None, day=4, hour=18, account_id=11, mask_id=111,
            mask="Hound", event_id=90, source_event_id=80, cord_id=777)
        self.assertTrue(ok, reason)
        state, ok, reason = stage.adapt(
            state, day=4, hour=19, account_id=22, mask_id=222,
            mask="Performer", event_id=91, choice="indoor")
        self.assertTrue(ok, reason)
        restored = {**state,
            "safety_warning": {**state["safety_warning"],
                "account_id": "11", "mask_id": "111",
                "event_id": "90", "source_event_id": "80",
                "cord_id": "777", "hour": "18"},
            "safety_decision": {**state["safety_decision"],
                "account_id": "22", "mask_id": "222",
                "event_id": "91", "warning_event_id": 90,
                "hour": "19"},
        }
        normalized = stage.normalize(restored)
        self.assertIsNotNone(normalized["safety_warning"])
        self.assertIsNotNone(normalized["safety_decision"])
        self.assertEqual(normalized["safety_warning"]["hour"], 18)
        self.assertEqual(normalized["safety_decision"]["hour"], 19)
        self.assertIn("A Hound signed", stage.public_lines(restored, 4))
        state, ok, reason = stage.rehearse(
            restored, day=4, hour=19, account_id=22, mask_id=222,
            mask="Performer", tune="reel", event_id=92)
        self.assertTrue(ok, reason)
        state, ok, reason = stage.perform(
            state, day=4, hour=20, account_id=22, mask_id=222,
            mask="Performer", tune="reel", event_id=93)
        self.assertTrue(ok, reason)
        self.assertEqual(state["performance"]["safety_mode"], "indoor")



if __name__ == "__main__":
    unittest.main()
