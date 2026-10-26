import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "spike" / "fvillage"))
from world.return_agenda import clean_note, summary, reentry_lines, lamp_repair_work_lines


class ReturnAgendaTests(unittest.TestCase):
    def test_note_is_single_line_sanitized_bounded(self):
        self.assertEqual(clean_note("Finish chapter\n|rthen sleep\x1b"), "Finish chapter rthen sleep")
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


    def test_returning_mask_sees_own_goal_without_undisclosed_board_content(self):
        lines = reentry_lines(
            note="  Check the bridge |r tonight\n",
            following=[{"id": 42, "body": "SECRET MODERATED TEXT",
                        "sender": "HIDDEN NAME"}],
        )
        output = "\n".join(lines)
        self.assertIn("Your saved private intention: Check the bridge r tonight", output)
        self.assertIn("commons", output.lower())
        self.assertIn("agenda", output)
        self.assertNotIn("SECRET MODERATED TEXT", output)
        self.assertNotIn("HIDDEN NAME", output)
        self.assertNotIn("#42", output)

    def test_reentry_without_notes_offers_discoverable_first_step(self):
        lines = reentry_lines(note=None, following=[])
        self.assertIn("guide", " ".join(lines))
        self.assertIn("agenda", " ".join(lines))


    def test_current_work_is_displayed_without_exposing_other_player_orders(self):
        result = summary(
            note=None, followed=[], day=2, location="Village Square",
            work_lines=["Commission civic-2: your firewood pledge is pending."],
        )
        self.assertIn("Your current village work", result)
        self.assertIn("your firewood pledge is pending", result)
        other = summary(note=None, followed=[], day=2,
                        location="Village Square", work_lines=[])
        self.assertNotIn("Your current village work", other)



    def test_lamp_agenda_requires_this_exact_mask_not_another_account(self):
        case = {
            "state": "investigating",
            "objective_mutations": {
                "smith_diagnosis": {"mask_id": 7, "mask": "SmithTester",
                                    "event_id": "signed-1"},
            },
        }
        self.assertEqual(lamp_repair_work_lines(case, 8), [])
        self.assertEqual(lamp_repair_work_lines(case, None), [])
        self.assertEqual(lamp_repair_work_lines({}, 7), [])
        own = " ".join(lamp_repair_work_lines(case, 7))
        self.assertIn("your Smith diagnosis", own)
        self.assertIn("Merchant must procure", own)
        self.assertNotIn("signed-1", own)

    def test_lamp_agenda_advances_after_actual_merchant_procurement(self):
        case = {
            "state": "changing",
            "objective_mutations": {
                "smith_diagnosis": {"mask_id": 7},
                "merchant_procurement": {"mask_id": 8},
            },
        }
        smith = " ".join(lamp_repair_work_lines(case, 7))
        merchant = " ".join(lamp_repair_work_lines(case, 8))
        self.assertIn("Merchant has procured", smith)
        self.assertIn("repair finish north-square gas lamp", smith)
        self.assertIn("your Merchant procurement", merchant)
        self.assertIn("Smith must install", merchant)
        self.assertEqual(lamp_repair_work_lines(case, 9), [])

    def test_lamp_agenda_terminal_repair_or_deadline_is_not_open_work(self):
        case = {
            "state": "aftermath",
            "branch": "repaired",
            "objective_mutations": {
                "smith_diagnosis": {"mask_id": 7},
                "merchant_procurement": {"mask_id": 8},
                "smith_repair": {"mask_id": 7},
            },
        }
        for mask_id in (7, 8):
            out = " ".join(lamp_repair_work_lines(case, mask_id))
            self.assertIn("lamp is repaired", out)
            self.assertIn("no repeat repair", out)
            self.assertNotIn("must procure", out)
        case["branch"] = "left_dark"
        for mask_id in (7, 8):
            out = " ".join(lamp_repair_work_lines(case, mask_id))
            self.assertIn("repair window closed", out)
            self.assertIn("can no longer be finished", out)
        self.assertEqual(lamp_repair_work_lines(case, 12), [])

    def test_lamp_agenda_handles_untrusted_or_incomplete_mutations(self):
        self.assertEqual(lamp_repair_work_lines(None, 1), [])
        self.assertEqual(lamp_repair_work_lines({"objective_mutations": []}, 1), [])
        self.assertEqual(lamp_repair_work_lines(
            {"objective_mutations": {"smith_diagnosis": "invalid"}}, 1
        ), [])


if __name__ == "__main__":
    unittest.main()
