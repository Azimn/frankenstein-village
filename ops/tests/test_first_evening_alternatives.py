"""Red-first behavior checks for authoritative alternate Square leads.

No quest acceptance, resource mutation, or interpretation of narrative copy
as physical truth is permitted. All eligibility is supplied as state.
"""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "spike" / "fvillage"))
from world.first_evening import render_square


class AlternativeLeadsTests(unittest.TestCase):
    def guide(self, **overrides):
        state = {
            "wood_remaining": 0,
            "hearth_reserve": 0,
            "hearth_limit": 6,
            "carrying_firewood": False,
            "active_profession": None,
            "unreported_sites": ("Market Lane",),
            "lamp_status": "The lamp is burning again. This is no longer an open job.",
            "lamp_case_state": "aftermath",
        }
        state.update(overrides)
        return render_square(**state)

    def test_depleted_stock_offers_unsigned_survey_instead(self):
        output = self.guide(lamp_case_state="active")
        self.assertIn("Alternative available now", output)
        self.assertIn("Market Lane", output)
        self.assertIn("survey report", output)
        self.assertNotIn("hearth gather", output)

    def test_completed_one_time_case_offers_real_renewable_stock(self):
        output = self.guide(wood_remaining=3, unreported_sites=())
        self.assertIn("no longer an open job", output)
        self.assertIn("Alternative available now", output)
        self.assertIn("hearth gather", output)
        self.assertNotIn("repair diagnose", output)

    def test_complete_case_and_empty_stock_use_remaining_survey(self):
        output = self.guide()
        self.assertIn("Alternative available now", output)
        self.assertIn("Market Lane", output)
        self.assertNotIn("repair procure", output)
        self.assertNotIn("hearth gather", output)

    def test_no_verified_work_gives_truthful_actionable_fallback(self):
        output = self.guide(unreported_sites=())
        self.assertIn("No verified open work", output)
        self.assertIn("commons", output)
        self.assertIn("calendar", output)
        self.assertNotIn("hearth gather", output)
        self.assertNotIn("survey report", output)
        self.assertNotIn("repair diagnose", output)

    def test_missing_survey_state_does_not_create_survey_job(self):
        output = self.guide(unreported_sites=None)
        self.assertIn("No verified open work", output)
        self.assertNotIn("survey report", output)

    def test_full_rack_even_with_stock_chooses_survey(self):
        output = self.guide(wood_remaining=3, hearth_reserve=6)
        self.assertIn("survey report", output)
        self.assertNotIn("hearth gather", output)

    def test_carried_firewood_with_space_is_a_real_alternative(self):
        output = self.guide(carrying_firewood=True, hearth_reserve=0)
        self.assertIn("Alternative available now", output)
        self.assertIn("hearth deliver", output)
        self.assertNotIn("hearth gather", output)

    def test_not_triggered_when_all_primary_work_is_available(self):
        output = self.guide(
            wood_remaining=3,
            lamp_case_state="active",
        )
        self.assertNotIn("No verified open work", output)
        self.assertNotIn("Alternative available now", output)


if __name__ == "__main__":
    unittest.main()
