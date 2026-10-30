"""Structural contract for the all-Calling design reference.

This checks documentation completeness only. It cannot certify implementation
or decide canon, and must never reinterpret a proposal as shipped gameplay.
"""
import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DOC = ROOT / "docs" / "TEN_CALLINGS_INTERDEPENDENCE_GAME_DESIGN_V1.md"
ROLES = ("Innkeep", "Chronicler", "Smith", "Healer", "Merchant",
         "Wanderer", "Performer", "Detective", "Hound", "Mystic")


class TenCallingDesignTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.text = DOC.read_text(encoding="utf-8")

    def test_all_ten_role_sections_exist_exactly_once(self):
        sections = re.findall(r"^### 3\.\d+ (.+)$", self.text, flags=re.M)
        self.assertEqual(sections, list(ROLES))

    def test_all_45_unique_pair_overlaps_are_written(self):
        pairs = re.findall(r"^### (\d{2})\. (\w+) ↔ (\w+) — ([VSCD]) \(", self.text, re.M)
        self.assertEqual(len(pairs), 45)
        self.assertEqual([int(x[0]) for x in pairs], list(range(1, 46)))
        real = set()
        for number, a, b, status in pairs:
            self.assertIn(a, ROLES)
            self.assertIn(b, ROLES)
            self.assertLess(ROLES.index(a), ROLES.index(b))
            self.assertIn(status, "VSCD")
            real.add((a, b))
        self.assertEqual(len(real), 45)
        self.assertEqual(real, {(ROLES[a], ROLES[b])
                                for a in range(10) for b in range(a + 1, 10)})

    def test_matrix_is_symmetric_and_points_to_pair_entries(self):
        section = self.text.split("## 4. Complete 10 × 10 overlap map", 1)[1]
        section = section.split("## 5. All 45 pairwise collaborations", 1)[0]
        rows = {}
        for line in section.splitlines():
            values = [v.strip() for v in line.strip().split("|")[1:-1]]
            if values and values[0] in ROLES:
                rows[values[0]] = values[1:]
        self.assertEqual(set(rows), set(ROLES))
        for i, a in enumerate(ROLES):
            self.assertEqual(len(rows[a]), 10)
            for j, b in enumerate(ROLES):
                cell = rows[a][j]
                if i == j:
                    self.assertEqual(cell, "—")
                    continue
                self.assertRegex(cell, r"^[VSCD](?:[1-9]|[1-3][0-9]|4[0-5])$")
                self.assertEqual(cell, rows[b][i])

    def test_design_preserves_world_authority_and_canon_blocks(self):
        for phrase in (
            "one active Calling", "Apprentice/Master", "world event ledger",
            "existing", "45 unique pairs", "do NOT interpret as resolved",
            "Guild of Mystics", "truth-value", "venue/location",
            "failed ritual", "not implemented", "host",
        ):
            with self.subTest(phrase=phrase):
                self.assertIn(phrase.lower(), self.text.lower())

    def test_document_does_not_claim_missing_systems_shipped(self):
        self.assertIn("**Status:** REVIEW DRAFT", self.text)
        self.assertIn("proposal", self.text.lower())
        self.assertIn("V (existing scripted cross-Calling chain)", self.text)
        self.assertIn("S (shared live system; distinct joint loop unverified)", self.text)
        self.assertIn("D (designed, not implemented)", self.text)
        self.assertIn("C (design overlap with canon-blocked capability)", self.text)


if __name__ == "__main__":
    unittest.main()
