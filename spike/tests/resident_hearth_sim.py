#!/usr/bin/env python3
"""Pure regression for hearth observation, memory and conditional location choice."""
from __future__ import annotations

import copy
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "fvillage"))
from world import resident_data, resident_hearth, resident_life


def main():
    mara = resident_data.RESIDENT_BY_ID["mara_crowe"]
    life = resident_life.fresh_life_state(mara)
    resident_life.apply_body_delta(life, cold=80)
    prior = copy.deepcopy(life)
    no_witness = resident_hearth.observe(
        life, present=False, warm=True, source_event_id=40, day=1, hour=21
    )
    assert no_witness is None and life == prior, "Offstage omniscience"
    no_fire = resident_hearth.observe(
        life, present=True, warm=False, source_event_id=40, day=1, hour=21
    )
    assert no_fire is None and life == prior
    no_source = resident_hearth.observe(
        life, present=True, warm=True, source_event_id=None, day=1, hour=21
    )
    assert no_source is None and life == prior
    witnessed = resident_hearth.observe(
        life, present=True, warm=True, source_event_id=40, day=1, hour=21
    )
    assert witnessed and witnessed["source_id"] == 40
    assert witnessed["summary"].startswith("I ")
    assert life["body"]["cold"] == 68
    assert life["last_witnessed_hearth_event_id"] == 40
    assert len(life["perceptions"]) == 1
    assert life["resident_relationships"] == {}, (
        "Environmental heat invented a social relationship"
    )
    again = resident_hearth.observe(
        life, present=True, warm=True, source_event_id=40, day=1, hour=22
    )
    assert again is None and life["body"]["cold"] == 68
    assert len(life["perceptions"]) == 1
    assert resident_hearth.observe(
        life, present=True, warm=True, source_event_id=39, day=1, hour=22
    ) is None
    assert len(life["perceptions"]) == 1, "Replayed a stale tending event"
    recovered = json.loads(json.dumps(life))
    assert resident_hearth.first_person_account(recovered).startswith("I was there")
    assert resident_hearth.observe(
        recovered, present=True, warm=True, source_event_id=40, day=2, hour=1
    ) is None

    candidate = resident_data.resolve_schedule(mara, hour=22, day=1)
    assert candidate["logical_location"] == mara["home_id"]
    assert resident_data.schedule_block(
        mara, hour=21, day=1
    )["desired_location"] == "tavern"
    safe_needs = {"fatigue": 20, "safety": 80, "hunger": 30}
    options = {
        "physical_location": "The Blood of the Vine",
        "previous_hour_location": "tavern",
        "active_heat": True, "hour": 22, "needs": safe_needs,
    }
    chosen = resident_hearth.maybe_linger(life, mara, candidate, **options)
    assert chosen and chosen["source"] == "hearth_preference"
    assert chosen["logical_location"] == "tavern"
    assert chosen["desired_location"] == mara["home_id"]
    for field, changed in [
        ("physical_location", "Village Square"),
        ("previous_hour_location", "offstage"),
        ("active_heat", False),
        ("hour", 23),
        ("needs", {"fatigue": 97, "safety": 80}),
        ("needs", {"fatigue": 20, "safety": 15}),
    ]:
        kwargs = dict(options)
        kwargs[field] = changed
        assert resident_hearth.maybe_linger(
            life, mara, candidate, **kwargs
        ) is None, (field, changed)
    wrong_goal = dict(candidate, source="life_goal_override")
    assert resident_hearth.maybe_linger(
        life, mara, wrong_goal, **options
    ) is None
    less_cold = copy.deepcopy(life)
    less_cold["body"]["cold"] = 48
    assert resident_hearth.maybe_linger(
        less_cold, mara, candidate, **options
    ) is None

    locked = resident_life.fresh_life_state(
        resident_data.RESIDENT_BY_ID["father_andrei"]
    )
    old = copy.deepcopy(locked)
    assert not resident_hearth.observe(
        locked, present=True, warm=True, source_event_id=40, day=1, hour=21
    )
    assert resident_hearth.maybe_linger(
        locked, resident_data.RESIDENT_BY_ID["father_andrei"],
        candidate, **options
    ) is None
    assert locked == old
    assert resident_hearth.first_person_account(locked) is None

    # New fuel -> new opportunity to perceive, not an unlimited heat machine.
    again = resident_hearth.observe(
        recovered, present=True, warm=True, source_event_id=41, day=2, hour=5
    )
    assert again and recovered["body"]["cold"] == 56
    assert len(recovered["perceptions"]) == 2
    assert len(recovered["perceptions"]) <= resident_life.MAX_PERCEPTIONS

    print("RESIDENT_HEARTH_SIM_GREEN")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
