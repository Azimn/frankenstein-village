import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "spike" / "fvillage"))
from world.return_agenda import clean_note, summary


class ReturnAgendaTests(unittest.TestCase):
    def test_note_is_single_line_sanitized_bounded(self):
        self.assertEqual(clean_note("Finish chapter\n|rthen sleep\x1b"), "Finish chapter  rthen sleep")
        self.assertIsNone(clean_note(" " * 10))
        self.assertIsNone(clean_note("x" * 201))
        self.assertEqual(len(clean_note("x" * 200)), 200)

    def test_hidden_notice_does_not_reveal_cached_content(self):
        result = summary(
            note="Remember the tree.",
            followed=[{"id": 31, "available": False,
                       "from": "PROTECTED NAME",
                       "body": "SECRET BODY",
                       "new_replies": 9}],
            day=7,
            location="Village Square",
        )
        self.assertIn("Commons #31: no longer publicly available", result)
        self.assertNotIn("SECRET BODY", result)
        self.assertNotIn("PROTECTED NAME", result)
        self.assertNotIn("9 unread", result)

    def test_unread_replies_and_closure_are_distinct(self):
        result = summary(
            note=None, day=2, location="The Blood of the Vine",
            followed=[{"id": 1, "available": True, "status": "closed",
                       "new_replies": 2, "new_closure": True}],
        )
        self.assertIn("2 unread signed replies", result)
        self.assertIn("new closing account", result)
        self.assertIn("commons check 1", result)
        self.assertIn("private reminder: none yet", result)

    def test_empty_followed_has_discovery_route(self):
        result = summary(note="I will be back", followed=[], day=1,
                         location="Inn Common Room")
        self.assertIn("agenda note =", result)
        self.assertIn("commons follow", result)
        self.assertIn("I will be back", result)


if __name__ == "__main__":
    unittest.main()
