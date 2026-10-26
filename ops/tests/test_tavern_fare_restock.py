"""T-09: exhausted physical Tavern fare has a bounded next-day replenishment."""
import sys
import unittest
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[2]/"spike/fvillage"))
from world.tavern_fare_restock import restock


class ExistingFareRestockTests(unittest.TestCase):
    def test_depleted_plate_remains_depleted_same_day(self):
        self.assertEqual(restock(0, 5, 5, 6),(0,5,False))
        self.assertEqual(restock(0, 5, 4, 6),(0,5,False))

    def test_next_day_restock_exactly_once_then_consumable_again(self):
        self.assertEqual(restock(0, 5, 6, 6),(6,6,True))
        self.assertEqual(restock(3, 6, 6, 6),(3,6,False))
        self.assertEqual(restock(0, 6, 7, 6),(6,7,True))

    def test_existing_legacy_servings_never_refilled_by_patch_or_rebuild(self):
        self.assertEqual(restock(2, None, 20, 6),(2,20,False))
        self.assertEqual(restock(2, 20, 20, 6),(2,20,False))
        self.assertEqual(restock(None, None, 20, 6),(6,20,False))

    def test_no_clock_rewind_or_beyond_capacity_inflation(self):
        self.assertEqual(restock(300, 15, 14, 6),(6,15,False))
        self.assertEqual(restock(-10, 15, 15, 6),(0,15,False))
        self.assertEqual(restock(2, 15, 16, 6),(6,16,True))

    def test_invalid_input_fails_closed(self):
        for args in ((0, 1, 0, 6),(0,1,2,0),(0,1,True,6),
                     (0,1,2,False),(0,"invalid",2,6),(False,1,2,6)):
            with self.subTest(args=args),self.assertRaises(ValueError):
                restock(*args)


if __name__=="__main__":
    unittest.main()
