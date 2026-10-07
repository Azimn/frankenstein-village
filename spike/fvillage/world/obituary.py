"""Compatibility facade for DM-Q-0017, Tomorrow's Obituary.

The production mechanic is owned by `world.harbinger_content`.  Keeping this
module as a thin facade prevents the earlier prototype from becoming a second
source of obituary state or importing nonexistent situation base classes.
"""

from __future__ import annotations

from world.harbinger_content import (
    OBITUARY_ACTIONS,
    decide_tomorrows_obituary,
    get_harbinger_obituary_case,
    harbinger_obituary_cases,
    open_harbinger_obituary_cases,
    resolve_due_obituary_cases,
    submit_tomorrows_obituary,
)


OBT_ID = "DM-Q-0017-OBTUARY"


def submit(player, subject):
    """Open the canonical Harbinger obituary case."""
    return submit_tomorrows_obituary(player, subject)


def decide(player, case_id, action):
    """Resolve a canonical Harbinger obituary case."""
    return decide_tomorrows_obituary(player, case_id, action)


def status(case_id):
    """Return one canonical Harbinger obituary case."""
    return get_harbinger_obituary_case(case_id)
