"""Bounded non-omniscient room explorer for ordinary Frankenstein Village agents.

Navigation learns only the destination edges actually disclosed to a
particular player by the public 'agent' command. No full-world topology or
builder API is supplied to the player.
"""
from __future__ import annotations

from collections import deque


class ExplorationPlanner:
    def __init__(self, start: str):
        self.start = start
        self.visited = set()
        self.edges = {}
        self.blocked = set()

    def observe(self, state):
        if state.get("side") != "ic":
            raise ValueError("Autonomous in-character exploration left the village")
        room = state.get("location")
        if not isinstance(room, str) or not room:
            raise ValueError("Missing observable current room")
        visible = set(state.get("exits") or [])
        # Ignore private OOC return routes. This is public map knowledge,
        # not a hidden staff coordinate or unrestricted pathfinding.
        exits = {}
        for direction, destination in (state.get("exit_targets") or {}).items():
            if not isinstance(direction, str) or direction not in visible:
                continue
            if not isinstance(destination, str) or not destination:
                continue
            if destination in {"Inn Hallway", "Inn Common Room", "Offstage"}:
                continue
            if (room, direction) in self.blocked:
                continue
            exits[direction] = destination
        self.edges[room] = exits
        self.visited.add(room)
        return room

    def next_move(self, current):
        """Shortest known approach to an unvisited adjacent room, else None."""
        queue = deque([(current, [])])
        seen = {current}
        while queue:
            node, path = queue.popleft()
            edges = self.edges.get(node, {})
            for direction, destination in sorted(edges.items()):
                if destination not in self.visited:
                    return path + [direction]
            for direction, destination in sorted(edges.items()):
                if destination in self.visited and destination not in seen:
                    seen.add(destination)
                    queue.append((destination, path + [direction]))
        return None

    def route(self, current, target):
        """Return a route through observed traversable edges, never guess."""
        if current == target:
            return []
        queue = deque([(current, [])])
        seen = {current}
        while queue:
            node, path = queue.popleft()
            for direction, destination in sorted(self.edges.get(node, {}).items()):
                if destination == target:
                    return path + [direction]
                if destination not in seen and destination in self.visited:
                    seen.add(destination)
                    queue.append((destination, path + [direction]))
        return None

    def block(self, room, direction):
        self.blocked.add((room, direction))
        self.edges.get(room, {}).pop(direction, None)
