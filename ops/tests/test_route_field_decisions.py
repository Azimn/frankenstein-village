"""GDD T-07: distinct Hound protection and Wanderer travel judgment.

This starts red on the unmodified shared route state. No new quest system.
"""
import copy
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "spike/fvillage"))
from world import route_surveys as r


class RoleFieldDecisions(unittest.TestCase):
    def test_same_site_supports_distinct_professional_decisions(self):
        # Wanderer describes actual access; Hound can change physical warning.
        before, ok, err = r.field_decision(
            None, 6, "red_cord", "wanderer", "passability", False, 21,
            "Wanderer", 101,
        )
        self.assertTrue(ok, err)
        self.assertEqual(before["field_decisions"]["wanderer"]["observation"],
                         "unmarked")
        after, ok, err = r.field_decision(
            before, 6, "red_cord", "hound", "protect", False, 22,
            "Hound", 102,
        )
        self.assertTrue(ok, err)
        self.assertEqual(after["field_decisions"]["hound"]["action"], "protect")
        self.assertEqual(after["field_decisions"]["wanderer"]["observation"],
                         "unmarked", "A later warning must not rewrite past testimony")
        self.assertEqual(after["field_decisions"]["hound"]["event_id"], 102)
        self.assertEqual(before["field_decisions"]["hound"] if "hound" in before["field_decisions"] else None, None)

    def test_protection_refuses_repeated_action_and_bad_role(self):
        state, ok, err = r.field_decision(
            None, 1, "red_cord", "hound", "protect", False, 4, "H", 5
        )
        self.assertTrue(ok, err)
        original = copy.deepcopy(state)
        retry, ok, err = r.field_decision(
            state, 1, "red_cord", "hound", "protect", True, 4, "H", 6
        )
        self.assertFalse(ok)
        self.assertEqual(original, retry)
        wrong, ok, err = r.field_decision(
            state, 1, "red_cord", "detective", "protect", True, 4, "D", 7
        )
        self.assertFalse(ok)
        self.assertEqual(original, wrong)

    def test_distinct_sources_and_firsthand_guards_fail_closed(self):
        for role, action in (("hound", "passability"), ("wanderer", "protect"),
                             ("hound", "protect")):
            site = "market_scale" if (role, action) == ("hound", "protect") else "red_cord"
            state, ok, error = r.field_decision(
                None, 1, site, role, action, False, 1, "Actor", 9
            )
            self.assertFalse(ok, error)
            self.assertEqual(state["field_decisions"], {})
        for aid, event in ((0, 5), (1, -1), (True, 5)):
            state, ok, err = r.field_decision(
                None, 1, "red_cord", "hound", "protect", False,
                aid, "Bad", event
            )
            self.assertFalse(ok)
            self.assertEqual(state["field_decisions"], {})

    def test_new_day_preserves_prior_signed_actions(self):
        old, ok, err = r.field_decision(
            None, 2, "red_cord", "hound", "protect", False, 13, "H", 14
        )
        self.assertTrue(ok, err)
        nxt = r.refresh(old, 3)
        self.assertEqual(nxt["field_decisions"], {})
        self.assertEqual(nxt["history"][-1]["field_decisions"]["hound"]["event_id"], 14)
        old_copy = copy.deepcopy(old)
        nxt["history"][-1]["field_decisions"]["hound"]["mask"] = "Changed"
        self.assertEqual(old, old_copy)
        prior, ok, err = r.field_decision(nxt, 2, "red_cord", "wanderer",
                                          "passability", True, 15, "W", 16)
        self.assertFalse(ok)
        self.assertEqual(prior, nxt)

    def test_wanderer_can_make_later_observation_without_overwriting_hound(self):
        protected, ok, err = r.field_decision(
            None, 2, "red_cord", "hound", "protect", False, 11, "H", 40
        )
        self.assertTrue(ok, err)
        observed, ok, err = r.field_decision(
            protected, 2, "red_cord", "wanderer", "passability", True,
            12, "W", 41,
        )
        self.assertTrue(ok, err)
        self.assertEqual(observed["field_decisions"]["wanderer"]["observation"],
                         "marked_caution")
        self.assertEqual(observed["field_decisions"]["hound"]["event_id"], 40)
        self.assertTrue(any("marked caution" in line for line in r.field_lines(observed)))


if __name__ == "__main__":
    unittest.main()
