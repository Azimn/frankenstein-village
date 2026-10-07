"""Compatibility facade for DM-Q-0018, The Well Boils.

The live implementation is the shared timed-incident engine in
`world.timed_incidents`.  This module intentionally owns no mutable state and
contains no second quest engine.  It exists so older imports of
`world.well_boils` continue to resolve to the production implementation.
"""

from __future__ import annotations

import copy

from world.timed_incidents import (
    WELL_BOILS_ID,
    TEMPLATES,
    advance_timed_incidents,
    get_timed_incident,
    maybe_start_timed_incidents,
    record_observation,
    start_timed_incident,
    status_for_player,
    well_description,
)


WELL_ID = WELL_BOILS_ID


def definition():
    """Return a copy of the authoritative timed-incident definition."""
    return copy.deepcopy(TEMPLATES[WELL_BOILS_ID])


def start(*, day=None, hour=None, now=None, force=False):
    """Start the production Well Boils window through its canonical engine."""
    return start_timed_incident(
        WELL_BOILS_ID,
        day=day,
        hour=hour,
        now=now,
        force=force,
    )


def status(player=None):
    """Return objective state, or one player's earned observation state."""
    if player is None:
        return get_timed_incident(WELL_BOILS_ID)
    return status_for_player(player, WELL_BOILS_ID)
