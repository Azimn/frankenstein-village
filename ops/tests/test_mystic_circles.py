"""Mystic guild keeps genuine anomaly distinct from interpreted cause."""
import sys
from pathlib import Path
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "spike/fvillage"))
from world import mystic_circles as guild
from world import resident_data


class MysticCirclesTests(unittest.TestCase):
    def test_weekly_rare_objective_manifestation(self):
        self.assertTrue(guild.manifested(1, 21))
        self.assertTrue(guild.manifested(8, 22))
        self.assertFalse(guild.manifested(1, 20))
        self.assertFalse(guild.manifested(2, 21))
        self.assertFalse(guild.manifested(1, 23))
        self.assertFalse(guild.manifested(0, 21))
        self.assertIn("no hand or chisel", guild.manifestation_text(8, 22))
        self.assertEqual(guild.manifestation_text(2, 21), "")

    def test_signed_approaches_and_independent_player_limit(self):
        state, ok, reason = guild.record(
            None, "measure", day=1, account_id=6, mask_id=20,
            mask="Observer", event_id=100,
        )
        self.assertTrue(ok, reason)
        self.assertEqual(state["studies"][0]["method"], "measure")
        self.assertIn("signed measured study", " ".join(guild.public_lines(state)))
        again, ok, reason = guild.record(
            state, "vigil", day=1, account_id=6, mask_id=22,
            mask="AlternateMask", event_id=101,
        )
        self.assertFalse(ok)
        self.assertIn("already filed", reason)
        self.assertEqual(again, state)
        other, ok, reason = guild.record(
            state, "vigil", day=1, account_id=7, mask_id=23,
            mask="Other", event_id=102,
        )
        self.assertTrue(ok, reason)
        self.assertEqual([x["method"] for x in other["studies"]],
                         ["measure", "vigil"])
        self.assertEqual(state["studies"][0]["event_id"], 100)
        nextday, ok, reason = guild.record(
            other, "measure", day=8, account_id=6, mask_id=20,
            mask="Observer", event_id=103,
        )
        self.assertTrue(ok, reason)
        rewind, ok, reason = guild.record(
            nextday, "measure", day=2, account_id=8, mask_id=24,
            mask="Newcomer", event_id=104,
        )
        self.assertFalse(ok)
        self.assertEqual(rewind, nextday)

    def test_data_validation_does_not_mint_observers(self):
        state, ok, reason = guild.record(
            None, "vigil", day=1, account_id=True, mask_id=4,
            mask="Forged", event_id=3,
        )
        self.assertFalse(ok)
        self.assertEqual(state["studies"], [])
        state, ok, reason = guild.record(
            None, "summon", day=1, account_id=1, mask_id=4,
            mask="Forged", event_id=3,
        )
        self.assertFalse(ok)
        self.assertEqual(state["studies"], [])
        self.assertEqual(guild.normalize({"studies": [
            {"method": "measure", "day": 1, "account_id": False,
             "mask_id": 1, "event_id": 3}
        ]})["studies"], [])

    def test_two_unique_people_not_ethnic_or_exclusive_character_classes(self):
        self.assertEqual(len(guild.NPCS), 2)
        self.assertNotEqual(guild.dialogue("beatrice_harcourt", "methods"),
                            guild.dialogue("mirela_dobre", "methods"))
        self.assertIn("credit", guild.dialogue("beatrice_harcourt", "Mirela"))
        self.assertIn("clock", guild.dialogue("mirela_dobre", "Harcourt"))
        for rid in guild.NPCS:
            person = resident_data.RESIDENT_BY_ID[rid]
            self.assertEqual(person["faction"], "Guild of Mystics")
            self.assertEqual(person["schedule_engine"], "population")
            self.assertEqual(resident_data.projection_for("churchyard"),
                             "St. Lazarus Churchyard")
        self.assertEqual(
            resident_data.projection_for("market_lane"), "Market Lane"
        )


if __name__ == "__main__":
    unittest.main()
