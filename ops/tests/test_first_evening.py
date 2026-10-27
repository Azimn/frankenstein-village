"""Pure, no-model acceptance checks for state-aware Square guidance."""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "spike" / "fvillage"))
from world.first_evening import render_square


class FirstEveningTests(unittest.TestCase):
    def guide(self, **updates):
        state = dict(
            wood_remaining=3,
            hearth_reserve=0,
            hearth_limit=6,
            carrying_firewood=False,
            active_profession=None,
            unreported_sites=("St. Lazarus Churchyard", "Market Lane"),
            lamp_status="A Smith can use repair diagnose north-square gas lamp. "
                        "Use commons post need = The lamp needs help.",
        )
        state.update(updates)
        return render_square(**state)

    def test_newcomer_has_three_concrete_grounded_opportunities(self):
        text = self.guide()
        self.assertIn("Everyday life", text)
        self.assertIn("Choose a profession", text)
        self.assertIn("Follow a mystery", text)
        self.assertIn("hearth gather", text)
        self.assertIn("hearth deliver", text)
        self.assertIn("calling choose", text)
        self.assertIn("survey report", text)
        self.assertIn("repair diagnose", text)

    def test_empty_woodpile_does_not_offer_nonexistent_delivery(self):
        text = self.guide(wood_remaining=0)
        self.assertNotIn("hearth gather", text)
        self.assertNotIn("hearth deliver", text)
        self.assertIn("stock or rack capacity is unavailable", text)
        self.assertIn("survey report", text)

    def test_full_rack_does_not_offer_unfulfillable_delivery(self):
        text = self.guide(hearth_reserve=6)
        self.assertNotIn("hearth gather", text)
        self.assertNotIn("hearth deliver", text)

    def test_carried_bundle_only_offers_real_delivery(self):
        text = self.guide(wood_remaining=0, carrying_firewood=True)
        self.assertIn("hearth deliver", text)
        self.assertNotIn("|whearth gather|n", text)
        self.assertIn("already carry", text)

    def test_carried_bundle_with_full_rack_cannot_deliver(self):
        text = self.guide(carrying_firewood=True, hearth_reserve=6)
        self.assertNotIn("|whearth deliver|n", text)
        self.assertNotIn("|whearth gather|n", text)

    def test_finished_survey_does_not_request_duplicate_reports(self):
        text = self.guide(unreported_sites=())
        self.assertNotIn("survey report", text)
        self.assertIn("mystery bridge", text)

    def test_missing_surveys_do_not_invent_checkpoint(self):
        text = self.guide(unreported_sites=None)
        self.assertNotIn("survey report", text)
        self.assertIn("Old Stone Bridge", text)

    def test_existing_profession_not_reselected(self):
        text = self.guide(active_profession="smith")
        self.assertIn("Your profession", text)
        self.assertIn("current Calling is Smith", text)
        self.assertIn("calling work", text)
        self.assertNotIn("Choose a profession", text)
        self.assertNotIn("calling choose", text)

    def test_closed_lamp_not_advertised_as_open(self):
        text = self.guide(lamp_status="The lamp is burning again. "
                          "This is no longer an open job.")
        self.assertIn("no longer an open job", text)
        self.assertNotIn("repair diagnose", text)
        self.assertNotIn("repair procure", text)

    def test_pure_renderer_does_not_modify_inputs(self):
        sites = ["Market Lane"]
        result = self.guide(unreported_sites=sites)
        self.assertEqual(sites, ["Market Lane"])
        self.assertIn("Market Lane", result)


if __name__ == "__main__":
    unittest.main()
