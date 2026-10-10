#!/usr/bin/env python3
"""Portable deterministic civic warmth tests with no Evennia."""
from __future__ import annotations

import importlib.util
import json
from pathlib import Path

path = Path(__file__).resolve().parents[1] / "fvillage" / "world" / "hearth_state.py"
spec = importlib.util.spec_from_file_location("hearth_state", path)
rules = importlib.util.module_from_spec(spec)
spec.loader.exec_module(rules)


def main():
    source = rules.source(None, 1)
    assert source == {"day": 1, "remaining": 3}
    for remaining in [2, 1, 0]:
        source, ok = rules.take(source, 1)
        assert ok and source["remaining"] == remaining
    unchanged, ok = rules.take(source, 1)
    assert not ok and unchanged == source
    assert rules.source(source, 1)["remaining"] == 0
    assert rules.source(source, 2) == {"day": 2, "remaining": 3}
    assert rules.source({"day": 3, "remaining": 0}, 2)["remaining"] == 0, (
        "Rewound clock minted free wood"
    )

    state = rules.hearth(None)
    for remaining in range(1, rules.MAX_RESERVE + 1):
        state, ok = rules.deliver(state)
        assert ok and state["reserve"] == remaining
    full, ok = rules.deliver(state)
    assert not ok and full == state, "Overflow destroyed wood or grew storage"

    actor = {"mask_id": 22, "mask": "InnkeepTester"}
    warm, ok = rules.stoke(state, 1, 21, actor=actor, source_event_id=40)
    assert ok and warm["reserve"] == rules.MAX_RESERVE - 1
    assert warm["warm_until"] == rules.absolute_hour(1, 21) + 8
    assert rules.active(warm, 1, 21) and rules.active(warm, 2, 4)
    assert not rules.active(warm, 2, 5)
    rejected, ok = rules.stoke(warm, 1, 22, actor=actor, source_event_id=41)
    assert not ok and rejected == warm
    second, ok = rules.stoke(warm, 2, 5, actor=actor, source_event_id=42)
    assert ok and second["reserve"] == rules.MAX_RESERVE - 2
    assert second["history"][-1]["event_id"] == 42
    assert len(second["history"]) == 2

    recovered = json.loads(json.dumps(second))
    assert rules.hearth(recovered) == second
    for i in range(25):
        # No disconnected unlimited refill: use real reserve units.
        recovered, supplied = rules.deliver(recovered)
        if not supplied:
            pass
        now = rules.absolute_hour(3+i, 6)
        recovered, success = rules.stoke(
            recovered, 3+i, 6, actor=actor, source_event_id=100+i
        )
        assert success
    assert len(recovered["history"]) == rules.MAX_HISTORY
    assert recovered["history"][-1]["event_id"] == 124
    assert 0 <= recovered["reserve"] <= rules.MAX_RESERVE
    print("COMMUNITY_HEARTH_SIM_GREEN")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
