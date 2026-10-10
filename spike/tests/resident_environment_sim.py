#!/usr/bin/env python3
"""Matched causal contrasts: physical rainfall, actual warmth, and absence.

Pure resident-life test: no Evennia, no external model, no magic city-wide
knowledge. One real village hour = at most one physical exposure per resident.
"""
from __future__ import annotations

import copy
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "fvillage"))
from world import resident_data, resident_hearth, resident_life, resident_weather


def fresh(stable_id="tam_rook"):
    return resident_life.fresh_life_state(resident_data.RESIDENT_BY_ID[stable_id])


def expose(life, *, room="Village Square", weather="rain", day=2, hour=6):
    return resident_weather.observe(
        life, physical_room=room, weather=weather, day=day, hour=hour
    )


def main():
    exposed = fresh()
    distant = fresh()
    dry = fresh()
    indoors = fresh()
    authored = fresh("father_andrei")
    locked_before = copy.deepcopy(authored)
    assert not exposed["body"]["cold"]
    baseline = copy.deepcopy(exposed)
    assert expose(distant, room="Offstage") is None
    assert expose(indoors, room="The Blood of the Vine") is None
    assert expose(dry, weather="fog") is None
    assert expose(authored) is None
    assert (distant, dry, indoors) == (baseline, baseline, baseline)
    assert authored == locked_before
    assert resident_weather.first_person_account(authored) is None

    first = expose(exposed)
    assert first and first["kind"] == "weather"
    assert first["summary"].startswith("I ")
    assert first["target_id"] == resident_weather.RAIN_TARGET_ID
    assert exposed["body"]["cold"] == 10
    assert exposed["body"]["wet"] == 14
    assert len(exposed["perceptions"]) == 1
    assert resident_weather.first_person_account(exposed).startswith("I was caught")
    assert resident_weather.first_person_account(distant).startswith("I haven't")

    assert expose(exposed) is None
    assert expose(exposed, hour=5) is None
    assert exposed["body"]["cold"] == 10 and len(exposed["perceptions"]) == 1
    assert expose(exposed, hour=7)
    assert exposed["body"]["cold"] == 20
    assert exposed["body"]["wet"] == 28
    before_relief = copy.deepcopy(exposed)
    assert resident_hearth.observe(
        exposed, present=False, warm=True, source_event_id=91,
        day=2, hour=8,
    ) is None
    assert exposed == before_relief
    assert resident_hearth.observe(
        exposed, present=True, warm=True, source_event_id=91,
        day=2, hour=8,
    )
    assert exposed["body"]["cold"] == 8, (
        "Physically experienced hearth warmth did not relieve rain-driven cold"
    )
    assert exposed["body"]["wet"] == 28, (
        "The fire did not physically change the wet clothes"
    )
    assert exposed["resident_relationships"] == {}, (
        "Environment mechanically invented social affection"
    )
    assert resident_hearth.observe(
        exposed, present=True, warm=True, source_event_id=91,
        day=2, hour=8,
    ) is None

    # Even warm residents may witness the fire, but must not claim a
    # reduction from a physical cold condition which was already zero.
    already_warm = fresh()
    warm_event = resident_hearth.observe(
        already_warm, present=True, warm=True, source_event_id=91,
        day=2, hour=8,
    )
    assert warm_event and "already warm" in warm_event["summary"]
    assert "ease the cold" not in warm_event["summary"]
    assert already_warm["body"]["cold"] == 0
    assert resident_hearth.observe(
        already_warm, present=True, warm=True, source_event_id=91,
        day=2, hour=9,
    ) is None

    # Freeze and resume the two physical histories: no synthetic catch-up
    # or duplicate effect after a JSON/database persistence boundary.
    restored = json.loads(json.dumps(exposed))
    assert expose(restored, hour=7) is None
    assert restored["body"]["cold"] == 8
    assert resident_hearth.observe(
        restored, present=True, warm=True, source_event_id=91,
        day=2, hour=8,
    ) is None
    assert expose(restored, hour=9)
    assert restored["body"]["cold"] == 18

    # More than twelve hourly observations never grows infinite histories.
    for offset in range(35):
        assert expose(restored, day=3 + offset, hour=6)
    assert 0 <= restored["body"]["cold"] <= 100
    assert 0 <= restored["body"]["wet"] <= 100
    assert len(restored["perceptions"]) <= resident_life.MAX_PERCEPTIONS
    assert len(restored["resident_relationships"]) == 0
    assert len(distant["perceptions"]) == 0
    print("RESIDENT_ENVIRONMENT_CAUSAL_SIM_GREEN")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
