"""Deterministic exploration policy, including one-way and hidden paths."""
import unittest

from ops.agent_exploration import ExplorationPlanner


def state(room, **routes):
    return {"location": room, "side": "ic", "exits": sorted(routes),
            "exit_targets": routes}


class ExplorerTests(unittest.TestCase):
    def test_map_learned_incrementally_and_no_omniscient_shortcuts(self):
        p = ExplorationPlanner("Tavern")
        p.observe(state("Tavern", west="Square", east="River"))
        self.assertEqual(p.next_move("Tavern"), ["east"])
        self.assertIsNone(p.route("Tavern", "Bridge"))
        p.observe(state("River", west="Tavern", east="Bridge"))
        self.assertEqual(p.next_move("River"), ["east"])
        p.observe(state("Bridge", west="River"))
        self.assertEqual(p.next_move("Bridge"), ["west", "west", "west"])
        p.observe(state("Square", east="Tavern"))
        self.assertIsNone(p.next_move("Square"))
        self.assertEqual(p.route("Square", "Bridge"), ["east", "east", "east"])

    def test_never_cross_hidden_exits_or_private_ooc(self):
        p = ExplorationPlanner("Square")
        p.observe({"location": "Square", "side": "ic",
                   "exits": ["east", "north"],
                   "exit_targets": {"east": "Tavern", "north": "Offstage",
                                    "secret": "Forbidden"}})
        self.assertEqual(p.next_move("Square"), ["east"])
        self.assertNotIn("north", p.edges["Square"])
        self.assertNotIn("secret", p.edges["Square"])
        with self.assertRaises(ValueError):
            p.observe({"location": "Inn Common Room", "side": "ooc"})

    def test_blocked_route_does_not_loop(self):
        p = ExplorationPlanner("Tavern")
        p.observe(state("Tavern", east="River"))
        self.assertEqual(p.next_move("Tavern"), ["east"])
        p.block("Tavern", "east")
        self.assertIsNone(p.next_move("Tavern"))


if __name__ == "__main__":
    unittest.main()
