"""Regression for T13 movement responses interleaved with another player's give."""
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "spike" / "tests"))
from telnet_t13_race import move_and_verify


class FakeClient:
    def __init__(self, movement, late, observation):
        self.movement = movement
        self.late = late
        self.observation = observation
        self.commands = []
        self.reads = 0

    def command(self, command, *, wait=2.5):
        self.commands.append(command)
        return self.observation if command == "agent" else self.movement

    def read_quiet(self, *, max_wait, quiet):
        self.reads += 1
        return self.late


def room_observation(room):
    return 'FV_AGENT_JSON {"location":"' + room + '"}\n'


class AsyncMovementTests(unittest.TestCase):
    def test_delayed_room_after_give_broadcast(self):
        client = FakeClient(
            "SmithTester gives you a bundle of firewood.",
            "\nThe Blood of the Vine\n",
            room_observation("The Blood of the Vine"),
        )
        move_and_verify(client, "east", "The Blood of the Vine")
        self.assertEqual(client.commands, ["east", "agent"])
        self.assertEqual(client.reads, 1)

    def test_immediate_room_does_not_consume_unrelated_broadcast(self):
        client = FakeClient(
            "The Blood of the Vine",
            "unrelated broadcast",
            room_observation("The Blood of the Vine"),
        )
        move_and_verify(client, "east", "The Blood of the Vine")
        self.assertEqual(client.commands, ["east", "agent"])
        self.assertEqual(client.reads, 0)

    def test_missing_movement_confirmation_fails_closed(self):
        client = FakeClient(
            "SmithTester gives you a bundle of firewood.",
            "Another unrelated message",
            room_observation("The Blood of the Vine"),
        )
        with self.assertRaises(AssertionError):
            move_and_verify(client, "east", "The Blood of the Vine")
        self.assertEqual(client.commands, ["east"])

    def test_wrong_actual_room_fails_despite_positive_text(self):
        client = FakeClient(
            "The Blood of the Vine",
            "",
            room_observation("Village Square"),
        )
        with self.assertRaises(AssertionError):
            move_and_verify(client, "east", "The Blood of the Vine")
        self.assertEqual(client.commands, ["east", "agent"])


if __name__ == "__main__":
    unittest.main()
