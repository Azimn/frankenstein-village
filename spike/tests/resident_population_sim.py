#!/usr/bin/env python3
"""Pure-stdlib long-run simulation for production resident schedules."""

from __future__ import annotations

import importlib.util
from pathlib import Path
import time


DATA_PATH = (
    Path(__file__).resolve().parents[1]
    / "fvillage"
    / "world"
    / "resident_data.py"
)

spec = importlib.util.spec_from_file_location("resident_data_under_test", DATA_PATH)
resident_data = importlib.util.module_from_spec(spec)
assert spec.loader is not None
spec.loader.exec_module(resident_data)


def main():
    residents = list(resident_data.RESIDENTS)
    assert 30 <= len(residents) <= 50, len(residents)

    ids = [resident["stable_id"] for resident in residents]
    assert len(ids) == len(set(ids)), "resident stable IDs must be unique"

    for resident in residents:
        for kin_id in resident.get("kin") or ():
            assert kin_id in resident_data.RESIDENT_BY_ID, (
                resident["stable_id"],
                kin_id,
            )
        employer_id = resident.get("employer_id")
        if employer_id:
            assert employer_id in resident_data.RESIDENT_BY_ID, (
                resident["stable_id"],
                employer_id,
            )
        for linked_id in resident.get("social_links") or ():
            assert linked_id in resident_data.RESIDENT_BY_ID, (
                resident["stable_id"],
                linked_id,
            )

    assert resident_data.RESIDENT_BY_ID["rada_petrescu"]["employer_id"] == "otto_kessler"
    population = [
        resident
        for resident in residents
        if resident.get("schedule_engine") == "population"
    ]
    assert population, "no production-scheduled residents"

    definitions_before = repr(resident_data.RESIDENTS)
    availability = {}
    resolutions = 0
    start = time.perf_counter()

    for day in range(1, 181):
        if day == 30:
            availability["schoolhouse"] = {
                "available": False,
                "reason": "school_destroyed",
            }
        if day == 33:
            availability["schoolhouse"] = {
                "available": True,
                "reason": None,
            }
        for hour in range(24):
            for resident in population:
                resolved = resident_data.resolve_schedule(
                    resident,
                    hour,
                    availability=availability,
                    day=day,
                )
                assert resolved["logical_location"]
                assert resolved["activity"]
                resolutions += 1

                if (
                    resident["stable_id"] == "wren_vessey"
                    and day in {30, 31, 32}
                    and hour == 10
                ):
                    assert resolved["logical_location"] == resident["home_id"]
                    assert resolved["source"] == "fallback"
                    assert resolved["reason"] == "school_destroyed"

                if (
                    resident["stable_id"] == "wren_vessey"
                    and day == 33
                    and hour == 10
                ):
                    assert resolved["logical_location"] == "schoolhouse"
                    assert resolved["source"] == "schedule"

    elapsed = time.perf_counter() - start
    assert definitions_before == repr(resident_data.RESIDENTS), (
        "schedule resolution mutated process-wide definitions"
    )

    wren = resident_data.RESIDENT_BY_ID["wren_vessey"]
    sunday = resident_data.resolve_schedule(wren, 12, day=1)
    monday = resident_data.resolve_schedule(wren, 10, day=2)
    assert sunday["logical_location"] == wren["home_id"]
    assert monday["logical_location"] == "schoolhouse"

    butcher = resident_data.RESIDENT_BY_ID["otto_kessler"]
    at_work = resident_data.resolve_schedule(butcher, 10)
    at_night = resident_data.resolve_schedule(butcher, 22)
    assert at_work["logical_location"] == "butcher_shop"
    assert at_night["logical_location"] == butcher["home_id"]

    # Newly traversable districts must actually participate in ordinary
    # resident life rather than remaining empty scenery. Physical projections
    # keep unbuilt private homes, school and nurseries inaccessible.
    expected_public = {
        "woods": "The Northern Treeline",
        "night_watch_post": "The Old Stone Bridge",
        "bakery": "Market Lane",
        "butcher_shop": "Market Lane",
        "forge": "Market Lane",
        "harbinger_office": "Market Lane",
        "carpenter_shop": "Market Lane",
    }
    for logical, physical in expected_public.items():
        assert resident_data.projection_for(logical) == physical
    for private in ("schoolhouse", "vessey_nursery", "home:kessler"):
        assert resident_data.projection_for(private) == "Offstage"

    def physical_at(stable_id, hour, day=2):
        resident = resident_data.RESIDENT_BY_ID[stable_id]
        schedule = resident_data.resolve_schedule(resident, hour, day=day)
        return resident_data.projection_for(schedule["logical_location"])

    assert physical_at("otto_kessler", 10) == "Market Lane"
    assert physical_at("sorin_dragomir", 23) == "The Old Stone Bridge"
    assert physical_at("sorin_dragomir", 10) == "Offstage"
    assert physical_at("silas_crowe", 10) == "The Northern Treeline"
    assert physical_at("silas_crowe", 20) == "The Blood of the Vine"
    assert physical_at("ilona_szabo", 10) == "Market Lane"
    # Market workers must leave their work frontage at their real closing
    # times rather than persist indefinitely as static ambient props.
    assert physical_at("otto_kessler", 22) == "Offstage"
    assert physical_at("ilona_szabo", 20) == "The Blood of the Vine"
    print("RESIDENT_OPEN_DISTRICT_SCHEDULES_GREEN")

    # Catch-up is direct. We do not replay 15 skipped hours.
    skipped = resident_data.resolve_schedule(
        butcher,
        22,
        current_location="butcher_shop",
    )
    assert skipped["logical_location"] == butcher["home_id"]

    night_worker = resident_data.RESIDENT_BY_ID["sorin_dragomir"]
    assert (
        resident_data.resolve_schedule(night_worker, 23)["logical_location"]
        == "night_watch_post"
    )
    assert (
        resident_data.resolve_schedule(night_worker, 10)["logical_location"]
        == night_worker["home_id"]
    )

    # This is intentionally generous for shared CI. The important observation
    # is that hundreds of thousands of routine resolutions are cheap and do
    # not scale with elapsed in-world history.
    assert elapsed < 5.0, f"schedule simulation too slow: {elapsed:.3f}s"
    rate = resolutions / max(elapsed, 1e-9)
    print(
        "RESIDENT_POPULATION_SIM_GREEN "
        f"population={len(residents)} scheduled={len(population)} "
        f"days=180 resolutions={resolutions} "
        f"seconds={elapsed:.4f} rate={rate:.0f}/s"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
