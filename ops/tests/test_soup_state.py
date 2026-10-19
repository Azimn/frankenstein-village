"""Finite and shareable soup production rules, tested without Evennia."""
import sys
import unittest
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "spike/fvillage"))

from world import soup_state as soup


class SoupKitchenRules(unittest.TestCase):
    def test_real_daily_stock_and_no_duplicate_refill(self):
        initial = soup.pantry(None, 1)
        self.assertEqual(initial["stock"]["turnip"], 3)
        state, ok, err = soup.reserve(initial, 1, "turnip", "thyme")
        self.assertTrue(ok, err)
        self.assertEqual(state["stock"]["turnip"], 2)
        self.assertEqual(state["stock"]["thyme"], 1)
        self.assertEqual(soup.pantry(state, 1)["stock"], state["stock"])
        self.assertEqual(soup.pantry(state, 0)["stock"], state["stock"])
        restored = soup.pantry(state, 2)
        self.assertEqual(restored["stock"]["turnip"], 3)
        self.assertEqual(soup.pantry(restored, 1)["day"], 2)
        self.assertEqual(soup.pantry(restored, 1)["stock"], restored["stock"])

    def test_rejects_invalid_or_unavailable_ingredients(self):
        state, ok, reason = soup.reserve(None, 1, "vampire", "blood")
        self.assertFalse(ok)
        self.assertEqual(state["stock"], soup.BASE_STOCK)
        self.assertIn("Choose", reason)
        state, ok, reason = soup.reserve(None, 1, "turnip", "pepper")
        self.assertTrue(ok, reason)
        state, ok, reason = soup.reserve(state, 1, "barley", "pepper")
        self.assertFalse(ok)
        self.assertIn("lacks", reason)
        state, ok, reason = soup.reserve(state, 1, "turnip", "salt")
        self.assertTrue(ok, reason)
        rewound, ok, reason = soup.reserve(state, 0, "turnip", "salt")
        self.assertFalse(ok)

    def test_real_food_differences_without_arbitrary_rerolling(self):
        plain = soup.produce("turnip", "thyme", warmed=False)
        warm = soup.produce("turnip", "thyme", warmed=True)
        another = soup.produce("barley", "pepper", warmed=True)
        self.assertEqual(warm["quality"] - plain["quality"], 5)
        self.assertEqual(plain["quality"], plain["nourish"])
        self.assertNotEqual(warm["flavor"], another["flavor"])
        self.assertTrue(another["warmed"])
        self.assertIsNone(soup.produce("mushrooms", "salt", warmed=True))

    def test_merchant_delivery_is_bounded_and_no_clock_rewind_exploit(self):
        source = soup.market_source(None, 1)
        self.assertEqual(source["remaining"], 2)
        used, okay = soup.issue_crate(source, 1)
        self.assertTrue(okay)
        used2, okay = soup.issue_crate(used, 1)
        self.assertTrue(okay)
        _, okay = soup.issue_crate(used2, 1)
        self.assertFalse(okay)
        self.assertFalse(soup.issue_crate(used2, 0)[1])
        self.assertEqual(soup.market_source(used2, 2)["remaining"], 2)
        state, okay = soup.deliver(None, 1)
        self.assertTrue(okay)
        self.assertEqual(state["stock"]["turnip"], 5)
        state, okay = soup.deliver(state, 1)
        self.assertTrue(okay)
        self.assertEqual(state["stock"]["turnip"], 7)
        duplicate, okay = soup.deliver(state, 1)
        self.assertFalse(okay)
        self.assertEqual(duplicate["stock"]["turnip"], 7)

    def test_signed_public_history_and_personal_book_are_bounded(self):
        state = None
        for event_id in range(1, 50):
            state = soup.archive(
                state, 1, maker_id=12, maker="Cook",
                source_event_id=2 * event_id, cook_event_id=event_id,
                recipe=soup.produce("barley", "thyme", warmed=False),
            )
        self.assertEqual(len(state["history"]), soup.HISTORY_MAX)
        self.assertEqual(state["history"][-1]["cook_event_id"], 49)
        self.assertEqual(state["history"][-1]["maker_id"], 12)
        book = []
        for n in range(30):
            entry = dict(state["history"][-1], cook_event_id=n)
            book = soup.notebook(book, entry)
        self.assertEqual(len(book), soup.NOTEBOOK_MAX)
        self.assertEqual(book[-1]["cook_event_id"], 29)
        self.assertEqual(soup.notebook(book, book[-1]), book)


if __name__ == "__main__":
    unittest.main()
