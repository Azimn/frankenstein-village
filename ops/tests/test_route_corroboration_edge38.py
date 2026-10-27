"""EDGE-38: independent, source-bound Hound/Wanderer route work."""
import copy
import json
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "spike/fvillage"))
from world import route_surveys as r


def prepared():
    state, ok, error = r.field_decision(
        None, 4, "red_cord", "wanderer", "passability",
        False, 31, "Wanderer", 101,
    )
    assert ok, error
    state, ok, error = r.field_decision(
        state, 4, "red_cord", "hound", "protect",
        False, 32, "Hound", 102,
    )
    assert ok, error
    return state, {"day": 4, "event_id": 102, "account_id": 32, "mask": "Hound"}


def signed(role):
    is_hound = role == "hound"
    return {
        "id": 102 if is_hound else 101,
        "kind": "village.route_protected" if is_hound else "village.route_passability_observed",
        "status": "complete",
        "actor": {"account_id": 32 if is_hound else 31,
                  "mask": "Hound" if is_hound else "Wanderer"},
        "payload": {"site": "red_cord", "day": 4, "hour": 12,
                    "role": role, "action": "protect" if is_hound else "passability",
                    "location": "The Northern Treeline"},
        "consequence": {"site": "red_cord", "day": 4,
                        "role": role, "action": "protect" if is_hound else "passability",
                        "cord_object_id": 6, "square_room_id": 7,
                        "caution_marked": is_hound,
                        "interpretation": None if is_hound else "unmarked"},
    }


class Edge38Tests(unittest.TestCase):
    def test_two_distinct_accounts_create_a_causal_link_without_rewriting_history(self):
        state, marker = prepared()
        old = copy.deepcopy(state)
        result, ok, error = r.corroborate(state, 4, "red_cord", 102, 31, "Wanderer", 103)
        self.assertTrue(ok, error)
        self.assertEqual(result["field_decisions"]["wanderer"]["observation"], "unmarked")
        self.assertEqual(result["field_decisions"]["wanderer"]["corroboration"]["hound_event_id"], 102)
        self.assertEqual(old["field_decisions"]["wanderer"]["observation"], "unmarked")
        self.assertNotIn("corroboration", old["field_decisions"]["wanderer"])
        self.assertTrue(any("not that the route is safe" in s for s in r.field_lines(result)))

    def test_duplicate_and_account_switch_are_rejected(self):
        state, marker = prepared()
        result, ok, _ = r.corroborate(state, 4, "red_cord", 102, 31, "W", 103)
        self.assertTrue(ok)
        for aid, event in ((31, 104), (32, 104), (33, 104)):
            after, ok, error = r.corroborate(result, 4, "red_cord", 102, aid, "X", event)
            self.assertFalse(ok, error)
            self.assertEqual(after, result)
        after, ok, error = r.corroborate(state, 4, "red_cord", 102, 32, "H", 103)
        self.assertFalse(ok)
        self.assertIn("separate", error)
        after, ok, error = r.corroborate(state, 4, "red_cord", 102, 31, "Imposter", 103)
        self.assertFalse(ok)
        self.assertIn("original Wanderer", error)

    def test_missing_hound_or_wanderer_or_wrong_marker_fails_closed(self):
        for role in ("hound", "wanderer"):
            state, marker = prepared()
            del state["field_decisions"][role]
            after, ok, _ = r.corroborate(state, 4, "red_cord", 102, 31, "W", 103)
            self.assertFalse(ok)
            self.assertNotIn("corroboration", after["field_decisions"].get("wanderer", {}))
        state, marker = prepared()
        for site, source in (("river_gauge", 102), ("red_cord", 999)):
            after, ok, _ = r.corroborate(state, 4, site, source, 31, "W", 103)
            self.assertFalse(ok)
            self.assertEqual(after, state)

    def test_bad_ids_clock_rewind_and_same_event_fail_closed(self):
        state, _ = prepared()
        for source, aid, event in ((True, 31, 103), (102, 0, 103),
                                   (102, 31, -1), (102, 31, 102),
                                   (102, 31, 101)):
            after, ok, _ = r.corroborate(state, 4, "red_cord", source, aid, "W", event)
            self.assertFalse(ok)
            self.assertEqual(after, state)
        after, ok, reason = r.corroborate(state, 3, "red_cord", 102, 31, "W", 103)
        self.assertFalse(ok)
        self.assertIn("later village day", reason)

    def test_marker_source_rejects_stale_and_forged(self):
        state, marker = prepared()
        hound = state["field_decisions"]["hound"]
        self.assertTrue(r.verify_caution_marker(marker, hound, 4))
        for key, bad in (("day", 3), ("event_id", 999), ("account_id", 31),
                         ("mask", "Another"), ("event_id", True)):
            forged = dict(marker, **{key: bad})
            self.assertFalse(r.verify_caution_marker(forged, hound, 4))

    def test_completed_source_verification_rejects_forgery(self):
        state, _ = prepared()
        for role in ("hound", "wanderer"):
            entry = state["field_decisions"][role]
            original = signed(role)
            self.assertTrue(r.verify_signed_field_source(
                original, entry, role, 4, 13, 6, 7
            ))
            for section, key, bad in (
                ("root", "status", "consequence_failed"),
                ("root", "kind", "village.route_inspected"),
                ("actor", "account_id", 999),
                ("actor", "mask", "Forged"),
                ("payload", "day", 5),
                ("payload", "hour", 14),
                ("payload", "location", "Village Square"),
                ("payload", "role", "merchant"),
                ("consequence", "cord_object_id", 999),
                ("consequence", "square_room_id", 999),
                ("consequence", "day", 3),
            ):
                forged = copy.deepcopy(original)
                target = forged if section == "root" else forged[section]
                target[key] = bad
                self.assertFalse(r.verify_signed_field_source(
                    forged, entry, role, 4, 13, 6, 7
                ), (role, section, key))

    def test_json_restart_and_day_rollover_preserve_link(self):
        state, _ = prepared()
        linked, ok, _ = r.corroborate(state, 4, "red_cord", 102, 31, "W", 103)
        self.assertTrue(ok)
        restored = r.normalize(json.loads(json.dumps(linked)))
        self.assertEqual(restored, linked)
        later = r.refresh(restored, 5)
        self.assertEqual(later["field_decisions"], {})
        self.assertEqual(later["history"][-1]["field_decisions"]["wanderer"]["corroboration"]["event_id"], 103)

    def test_unverified_joint_metadata_does_not_survive_normalization(self):
        state, _ = prepared()
        state["field_decisions"]["wanderer"]["corroboration"] = {
            "event_id": 103, "hound_event_id": 999, "account_id": 31,
            "mask": "Wanderer", "observation": "marked_caution",
        }
        restored = r.normalize(state)
        self.assertNotIn("corroboration", restored["field_decisions"]["wanderer"])


if __name__ == "__main__":
    unittest.main()
