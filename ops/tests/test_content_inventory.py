"""Contract tests for the static gameplay inventory.

Counts intentionally reflect code declarations, not verified player reachability.
The checks must survive future content additions without freezing item quotas.
"""

from __future__ import annotations

import ast
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "ops"))

from content_inventory import (  # noqa: E402
    _mapping_keys,
    _rooms,
    _seed_ids,
    build_inventory,
    to_markdown,
)


class StaticInventoryTests(unittest.TestCase):
    def test_identifier_resolution_and_duplicate_rejection(self):
        tree = ast.parse(
            "ALPHA_ID = 'a'\nBETA_ID = 'b'\n"
            "DEFINITIONS = {ALPHA_ID: {}, BETA_ID: {}}\n"
        )
        self.assertEqual(_mapping_keys(tree, "DEFINITIONS"), ["a", "b"])
        repeated = ast.parse("DEFINITIONS = {'a': {}, 'a': {}}")
        with self.assertRaisesRegex(ValueError, "Repeated identifiers"):
            _mapping_keys(repeated, "DEFINITIONS")

    def test_room_scanner_does_not_count_function_declarations(self):
        tree = ast.parse(
            "def get_or_create_room(key):\n"
            "    return key\n"
            "square = get_or_create_room('Village Square', side='ic')\n"
            "get_or_create_room('Offstage', side='ic', place='offstage')\n"
        )
        rooms = _rooms(tree)
        self.assertEqual(len(rooms), 2)
        self.assertEqual(rooms[0]["name"], "Village Square")
        self.assertEqual(rooms[1]["place"], "offstage")

    def test_rumor_selection_is_explicit(self):
        tree = ast.parse("PLAYABLE_RUMOR_IDS = frozenset({236, 151, 201})")
        self.assertEqual(_seed_ids(tree), [151, 201, 236])

    def test_live_source_cross_references(self):
        data = build_inventory(ROOT)
        self.assertEqual(data["schema"], "fvillage.static_content_inventory.v1")
        self.assertGreaterEqual(data["rooms"]["ic_walkable_declared"], 5)
        self.assertGreaterEqual(data["rooms"]["ooc_walkable_declared"], 2)
        self.assertGreaterEqual(data["resident_definitions"], 36)
        self.assertEqual(data["calling_definitions"]["count"], 9)
        self.assertGreaterEqual(data["rumors"]["accepted_corpus_ids"], 250)
        self.assertGreaterEqual(data["rumors"]["selected_for_bootstrap"], 3)
        self.assertTrue(data["rumors"]["seed_function_called"])
        for category, entry in data["categories"].items():
            with self.subTest(category=category):
                self.assertGreaterEqual(entry["count"], 1)
                self.assertTrue(entry["bootstrap_initialization_called"])
                self.assertEqual(entry["interpretation"], "static_definition_only")

    def test_report_disclaims_quality_and_runtime_completeness(self):
        report = to_markdown(build_inventory(ROOT))
        self.assertIn("not proof of", report)
        self.assertIn("Invited-alpha scope is separately gated", report)
        self.assertIn("Selected initial canon rumors", report)


if __name__ == "__main__":
    unittest.main()
