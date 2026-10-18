"""Finite, physical Market Lane supplies for the missing-plaque investigation.

Stock replenishes only when the existing village clock advances. Inventory
objects are separate, transportable Evennia objects carrying event provenance.
A world rebuild does not mint supplies or erase remaining stock.
"""
from __future__ import annotations

CHOICES = ("preserve", "display")
DAILY_PER_KIND = 2
ITEM_NAMES = {
    "preserve": "a canvas preservation kit",
    "display": "a public inquiry board kit",
}
ITEM_DESCRIPTIONS = {
    "preserve": (
        "Canvas, cord and simple fitted brackets for protecting existing "
        "stonework. This kit came from the Market Lane civic supply table; "
        "it can be carried or given to another traveler."
    ),
    "display": (
        "A blank oak panel, chalk and mounting pins. This kit can support "
        "public witness notes without asserting that any theory is true. "
        "It came from the Market Lane civic supply table."
    ),
}


def normalize(raw, day):
    """Refresh bounded counters for a new day; never refill on clock rewind."""
    try:
        source = dict(raw or {})
    except (TypeError, ValueError):
        source = {}
    try:
        last = int(source.get("day") or 0)
    except (ValueError, TypeError, OverflowError):
        last = 0
    last = max(0, last)
    day = int(day)
    if day < 1:
        raise ValueError("Village day must be positive.")
    if last == 0 or day > last:
        return {"day": day, "remaining": {
            choice: DAILY_PER_KIND for choice in CHOICES
        }}
    old = dict(source.get("remaining") or {})
    remaining = {}
    for choice in CHOICES:
        try:
            quantity = int(old.get(choice, 0))
        except (TypeError, ValueError, OverflowError):
            quantity = 0
        remaining[choice] = max(0, min(DAILY_PER_KIND, quantity))
    return {"day": last, "remaining": remaining}


def withdraw(raw, day, choice):
    state = normalize(raw, day)
    if choice not in CHOICES:
        return state, False, "Choose preserve or display materials."
    if int(day) < state["day"]:
        return state, False, "The supply table cannot reopen an earlier day."
    if state["remaining"][choice] < 1:
        return state, False, "No more of those kits remain today."
    state["remaining"][choice] -= 1
    return state, True, None
