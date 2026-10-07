#!/usr/bin/env python3
"""Pure-stdlib regression for Resident Life v2.

This test intentionally runs without Evennia. It proves the population life
layer is portable, bounded, first-person at its subjective boundary, and a
strict no-op for authored-locked residents.
"""

from __future__ import annotations

import importlib.util
from pathlib import Path
import time


ROOT = Path(__file__).resolve().parents[1] / "fvillage" / "world"


def load(name):
    path = ROOT / f"{name}.py"
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


resident_data = load("resident_data")
resident_life = load("resident_life")


def by_id(stable_id):
    return resident_data.RESIDENT_BY_ID[stable_id]


def main():
    father = resident_life.fresh_life_state(by_id("father_andrei"))
    ilona = resident_life.fresh_life_state(by_id("ilona_szabo"))
    assert not father["enabled"]
    assert father["profile"] == resident_life.PROFILE_AUTHORED_LOCKED
    assert not ilona["enabled"], "authored Chronicle resident was not protected"

    miklos_def = by_id("miklos_farkas")
    life = resident_life.fresh_life_state(miklos_def)
    assert life["enabled"]
    assert life["profile"] == resident_life.PROFILE_POPULATION

    resident_life.apply_body_delta(life, pain=72, cold=48, injury=30)
    assert life["body"]["pain"] == 72
    assert life["body"]["cold"] == 48

    affect = resident_life.add_affect_episode(
        life,
        "fear",
        80,
        cause="the noise behind me",
        target_id="unknown_noise",
        day=4,
        hour=21,
        half_life_hours=6,
    )
    assert affect and affect["kind"] == "fear"

    perception = resident_life.record_perception(
        life,
        kind="sound",
        summary="I heard something scrape behind me.",
        source_id="room:street",
        confidence=0.8,
        salience=0.9,
        day=4,
        hour=21,
    )
    assert perception["summary"].startswith("I ")

    commitment = resident_life.add_commitment(
        life,
        "return_lantern",
        "return the borrowed lantern",
        target_id="rada_petrescu",
        logical_location="village_square",
        due_day=4,
        due_hour=21,
        priority=0.9,
        day=4,
        hour=16,
    )
    assert commitment["status"] == "open"

    relation = resident_life.record_social_event(
        life,
        "rada_petrescu",
        kind="help",
        day=4,
        valence=6,
        familiarity=3,
        trust=4,
        respect=2,
        debt=5,
    )
    assert relation["familiarity"] == 3
    assert relation["trust"] == 4
    assert resident_life.social_weight(life, "rada_petrescu") > 1.0

    needs = {
        "fatigue": 30,
        "hunger": 25,
        "safety": 80,
        "affiliation": 45,
        "duty": 30,
    }
    override = resident_life.schedule_override(
        life,
        needs,
        miklos_def,
        day=4,
        hour=21,
        availability={"village_square": {"available": True}},
    )
    # Pain is severe enough to protect the body and takes precedence over the
    # social commitment, so the first actionable goal is home.
    assert override
    assert override["logical_location"] == miklos_def["home_id"]

    thoughts = resident_life.first_person_thoughts(
        life,
        needs,
        day=4,
        hour=21,
        limit=6,
    )
    assert thoughts
    assert all(
        thought.startswith(("I ", "I'm ", "I've ", "My "))
        for thought in thoughts
    ), thoughts

    assert resident_life.resolve_commitment(
        life,
        "return_lantern",
        "fulfilled",
        day=4,
        hour=22,
    )
    assert not resident_life.open_commitments(life)

    before = len(life["affect"])
    resident_life.decay_life_state(life, 5, 21)
    assert len(life["affect"]) <= before
    assert life["body"]["cold"] < 48

    # Authored lock is a hard boundary, not a soft convention.
    locked = resident_life.fresh_life_state(by_id("father_andrei"))
    assert resident_life.apply_body_delta(locked, pain=100) == locked
    assert resident_life.add_affect_episode(
        locked,
        "fear",
        100,
        cause="QA",
        day=1,
        hour=1,
    ) is None
    assert resident_life.add_commitment(
        locked,
        "qa",
        "do something",
        day=1,
        hour=1,
    ) is None
    assert resident_life.record_social_event(
        locked,
        "miklos_farkas",
        kind="qa",
        day=1,
    ) is None
    assert resident_life.first_person_thoughts(locked, {}) == []

    # Long-run cost must remain proportional to resident count and current
    # time, never elapsed hidden cognition.
    states = {
        definition["stable_id"]: resident_life.fresh_life_state(definition)
        for definition in resident_data.RESIDENTS
    }
    start = time.perf_counter()
    steps = 0
    for day in range(1, 181):
        for hour in range(24):
            for definition in resident_data.RESIDENTS:
                state = states[definition["stable_id"]]
                resident_life.decay_life_state(state, day, hour)
                if state.get("enabled"):
                    resident_life.derive_goals(
                        state,
                        {
                            "fatigue": 20,
                            "hunger": 25,
                            "safety": 80,
                            "affiliation": 45,
                            "duty": 30,
                        },
                        day=day,
                        hour=hour,
                    )
                steps += 1
    elapsed = time.perf_counter() - start
    assert elapsed < 5.0, f"resident life simulation too slow: {elapsed:.3f}s"

    enabled_count = sum(
        bool(state.get("enabled"))
        for state in states.values()
    )
    locked_count = len(states) - enabled_count
    print(
        "RESIDENT_LIFE_SIM_GREEN "
        f"population={len(states)} enabled={enabled_count} locked={locked_count} "
        f"steps={steps} seconds={elapsed:.4f}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
