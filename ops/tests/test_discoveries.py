"""Deterministic, Evennia-free player field notebook contract tests."""
import importlib.util
from pathlib import Path
import sys
import unittest

PATH = (Path(__file__).resolve().parents[2]
        / "spike/fvillage/world/discoveries.py")
spec = importlib.util.spec_from_file_location("discovery_rules_test", PATH)
rules = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = rules
spec.loader.exec_module(rules)


class DiscoveryRulesTests(unittest.TestCase):
    def test_bounded_idempotent_firsthand_records(self):
        rows, added = rules.record(None, "red_cord", 3, 14)
        self.assertTrue(added)
        self.assertEqual(rows, [{"id": "red_cord", "day": 3, "hour": 14}])
        rows, added = rules.record(rows, "red_cord", 15, 20)
        self.assertFalse(added)
        self.assertEqual(rows[0]["day"], 3)
        rows, added = rules.record(rows, "secret_hidden_case", 3, 15)
        self.assertFalse(added)
        self.assertEqual(len(rows), 1)
        self.assertEqual(len(rules.LANDMARKS), 4)

    def test_malformed_saved_data_does_not_leak_or_grow(self):
        raw = [
            {"id": "market_scale", "day": 1, "hour": 12},
            {"id": "market_scale", "day": 2, "hour": 12},
            {"id": "river_gauge", "day": -1, "hour": 80},
            {"id": "administrator_note", "day": 1, "hour": 3},
            {"id": "grave_marker", "day": "2", "hour": "14"},
        ]
        self.assertEqual(rules.normalize(101), [])
        self.assertEqual(rules.normalize([{"id": [], "day": 2, "hour": 1}]), [])
        rows = rules.normalize(raw)
        self.assertEqual([r["id"] for r in rows],
                         ["market_scale", "grave_marker"])
        text = "\n".join(rules.journal_lines(rows))
        self.assertIn("crooked market scale", text)
        self.assertIn("weathered grave marker", text)
        self.assertNotIn("administrator_note", text)
        self.assertNotIn("river gauge", text)

    def test_invalid_clock_cannot_create_discovery(self):
        for day, hour in ((0, 10), (2, 24), (2, -1), ("bogus", 1)):
            row, changed = rules.record(None, "river_gauge", day, hour)
            self.assertFalse(changed)
            self.assertEqual(row, [])
        empty = "\n".join(rules.journal_lines([]))
        self.assertIn("not personally inspected", empty)

    def test_view_is_copy_and_no_secret_invented(self):
        raw = [{"id": "red_cord", "day": 4, "hour": 10}]
        sanitized = rules.normalize(raw)
        sanitized[0]["day"] = 33
        self.assertEqual(raw[0]["day"], 4)
        for row in rules.LANDMARKS.values():
            self.assertIn("room", row)
            self.assertNotIn("culprit", row["summary"].lower())


if __name__ == "__main__":
    unittest.main()
