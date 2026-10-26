"""Pure daily refill logic for existing physical Tavern fare, not an economy.

Bram's existing sideboard is staffed by an NPC. A depleted plate stays empty
until a later village day, then receives precisely its declared finite stock.
A rebuild or repeat look on the same day never mints more servings.
"""
from __future__ import annotations


def restock(remaining, last_day, today, capacity):
    """Return (servings, recorded_day, restocked).

    On legacy unmarked items preserve their currently spent serving count.
    A real subsequent day may refill them once. Fail closed on bad days.
    """
    if any(isinstance(x, bool) for x in (today, capacity)):
        raise ValueError("Daily fare counts must be positive integers")
    try:
        day = int(today)
        maximum = int(capacity)
        previous = int(last_day) if last_day is not None else None
    except (ValueError, TypeError, OverflowError) as e:
        raise ValueError("Missing village day or serving capacity") from e
    if day < 1 or maximum < 1 or (previous is not None and previous < 1):
        raise ValueError("Missing village day or serving capacity")
    if remaining is None:
        remaining = maximum
    else:
        if isinstance(remaining, bool):
            raise ValueError("Invalid serving count")
        remaining = max(0, min(maximum, int(remaining)))
    if previous is None:
        return remaining, day, False
    if day > previous:
        return maximum, day, True
    return remaining, previous, False
