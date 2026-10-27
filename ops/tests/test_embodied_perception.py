"""Tarn/emic sensory renderer must reflect state, not create another physiology."""
import sys
import unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[2]/"spike/fvillage"))
from world.embodied_perception import perception, deep_lines


class EmbodiedPerceptionTests(unittest.TestCase):
    def test_hunger_grades_and_real_attention(self):
        low=perception(hunger=20)
        middle=perception(hunger=70)
        high=perception(hunger=95)
        self.assertEqual(low["bands"]["hunger"],"sated")
        self.assertEqual(middle["bands"]["hunger"],"hungry")
        self.assertEqual(high["bands"]["hunger"],"famished")
        self.assertIn("hollow pressure",high["first_person"][0])
        self.assertNotIn("hollow pressure",low["first_person"][0])

    def test_warmth_state_changes_language_without_inventing_weather(self):
        cold=perception(warmth=0.12)
        warm=perception(warmth=0.92)
        self.assertEqual(cold["bands"]["warmth"],"freezing")
        self.assertEqual(warm["bands"]["warmth"],"warm")
        self.assertIn("cold",cold["first_person"][1].lower())
        self.assertNotIn("rain", " ".join(cold["first_person"]).lower())
        self.assertNotIn("shivering", " ".join(warm["first_person"]).lower())

    def test_queasiness_and_intoxication_are_separate_measured_states(self):
        upset=perception(queasy=5,drunkenness=64)
        settled=perception(queasy=0,drunkenness=0)
        self.assertEqual(upset["bands"]["stomach"],"unsettled")
        self.assertEqual(upset["bands"]["intoxication"],"drunk")
        self.assertNotIn("queasiness"," ".join(settled["first_person"]).lower())
        self.assertIn("balance", " ".join(upset["first_person"]).lower())

    def test_relief_is_qualified_by_place_and_actual_stock(self):
        hungry=perception(hunger=99,place="The Blood of the Vine")
        self.assertIn("serving that still exists", " ".join(hungry["possible_relief"]))
        away=perception(hunger=99,place="Village Square")
        self.assertIn("when its stock is available"," ".join(away["possible_relief"]))
        self.assertIn("not damaging"," ".join(away["possible_relief"]))

    def test_no_fake_needs_or_omniscient_hidden_truth(self):
        text=" ".join(deep_lines(perception(hunger=50,warmth=.9,drunkenness=0,queasy=0)))
        for forbidden in ("You are injured","You are thirsty","You are wet","You have a fever"):
            self.assertNotIn(forbidden,text)
        model=perception()
        self.assertEqual(model["body_model"],"represented_character_sensations_not_ai_biology")
        self.assertNotIn("hidden_hazard",model)

    def test_invalid_values_fail_closed_without_nan_or_overflow(self):
        x=perception(hunger=float("nan"),warmth=float("-inf"),drunkenness=True,queasy="unknown")
        self.assertEqual(x["bands"]["hunger"],"settled")
        self.assertEqual(x["bands"]["warmth"],"warm")
        self.assertEqual(x["bands"]["intoxication"],"clear")
        self.assertEqual(x["bands"]["stomach"],"settled")


if __name__=="__main__":
    unittest.main()
