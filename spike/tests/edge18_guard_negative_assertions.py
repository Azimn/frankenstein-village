"""EDGE-18 adversarial post-authentication source-gate isolation.

The real authenticated role and patient commands are tested separately by
telnet_edge18_day2_supported.py. Here a narrow mock bypasses ONLY the
login/location precondition so the downstream provenance checks can be
tested in the stopped-server disposable QA database. This is not an
authenticated player test and never signs an event. All mutations revert.
"""
from copy import deepcopy
from types import SimpleNamespace
from unittest.mock import patch
from evennia.scripts.models import ScriptDB
from evennia.utils import search
from world import clinic_cot_work, clinic_cot_edge18, clinic_state


def one(key):
    matches = [o for o in search.search_object(key) if o.key == key]
    assert len(matches) == 1, (key, len(matches))
    return matches[0]


church = one("St. Lazarus Church")
cot = one("a clinic treatment cot")
healer = one("HealerTester")
clock = ScriptDB.objects.get(db_key="village_time")
ledger = ScriptDB.objects.get(db_key="world_event_ledger")
original_clock = (int(clock.db.day), int(clock.db.hour))
original_clinic = deepcopy(dict(church.db.village_clinic))
original_equipment = deepcopy(dict(cot.db.clinic_equipment))
original_events = deepcopy(list(ledger.db.events or []))


def downstream_ready():
    # Offline characters have no active account. Bypass ONLY the outer
    # authenticated room/Calling guard, already tested through live telnet.
    # All actual cot, ledger, clock and assessment checks remain in force.
    with patch.object(clinic_cot_work, "_guard", return_value=(cot, None)):
        return clinic_cot_work.supported_rest_ready(healer)


assert original_clock[0] == 2 and 0 <= original_clock[1] <= 23, original_clock
assert clinic_cot_edge18.normalize(original_equipment)["condition"] == "certified"
assert clinic_state.normalize(original_clinic)["treatment"]["method"] == "supported"
try:
    # Even a valid signed cot must not be usable before its signed work.
    clock.db.day = 1
    clock.db.hour = 20
    ready, reason = downstream_ready()
    assert not ready and "still in the future" in reason.lower(), reason

    # Inspect the authentic consumed hinge's immutable forge receipt with
    # a read-only item proxy. Its signed hour is later than the rewound
    # 20:00 clock, so installation must fail before any player action.
    brace = original_equipment["brace"]
    forge_event = ledger.get_event(brace["forge_event_id"])
    proxy = SimpleNamespace(
        id=brace["item_id"],
        db=SimpleNamespace(forged_market_part={
            "source_event_id": brace["forge_event_id"],
            "issued_day": forge_event["payload"]["day"],
            "source_room_id": brace["workshop_id"],
            "smith_account_id": forge_event["actor"]["account_id"],
        }),
    )
    source, error = clinic_cot_work._forge(proxy)
    assert source is None and "future workshop date" in error.lower(), error
    clock.db.day, clock.db.hour = original_clock

    # The next patient must have an actual signed examination, not an
    # invented event ID copied into the original clinic Attribute.
    forged = deepcopy(original_clinic)
    forged["assessment"]["event_id"] = 99999999
    church.db.village_clinic = forged
    ready, reason = downstream_ready()
    assert not ready and "lacks a signed healer event" in reason.lower(), reason

    # Reusing the real event ID under a different account is also denied.
    forged = deepcopy(original_clinic)
    forged["assessment"]["account_id"] += 9999
    church.db.village_clinic = forged
    ready, reason = downstream_ready()
    assert not ready and "lacks a signed healer event" in reason.lower(), reason
    church.db.village_clinic = deepcopy(original_clinic)

    # The signed assessment hour, not the mutable clinic Attribute, governs
    # certification. A backdated row must fail even when the Healer account,
    # mask, patient and source event ID are otherwise genuine.
    signed_assessment = original_clinic["assessment"]
    forged = deepcopy(original_clinic)
    forged_hour = signed_assessment["hour"] - 1 if signed_assessment["hour"] > 0 else 1
    forged["assessment"]["hour"] = forged_hour
    church.db.village_clinic = forged
    examiner = SimpleNamespace(
        id=signed_assessment["mask_id"],
        account=SimpleNamespace(id=signed_assessment["account_id"]),
    )
    assessment, reason = clinic_cot_work._assessment(
        cot, examiner, original_clock[0], original_clock[1])
    assert assessment is None and "lacks an authentic healer event" in reason.lower(), reason
    # When possible, rewind to the forged hour: the receipt is still later.
    if signed_assessment["hour"] > 0:
        clock.db.hour = forged_hour
        assessment, reason = clinic_cot_work._assessment(
            cot, examiner, original_clock[0], forged_hour)
        assert assessment is None and "lacks an authentic healer event" in reason.lower(), reason
    clock.db.day, clock.db.hour = original_clock
    church.db.village_clinic = deepcopy(original_clinic)

    # Moving the certification timestamp into the future must not grant
    # access, regardless of the original signed event's existence.
    forged_equipment = deepcopy(original_equipment)
    forged_equipment["certification"]["day"] = original_clock[0] + 1
    forged_equipment["certification"]["hour"] = 0
    cot.db.clinic_equipment = forged_equipment
    ready, reason = downstream_ready()
    assert not ready and "still in the future" in reason.lower(), reason

    # A forged but already elapsed certification timestamp also fails.
    # Comparing only the clock to the mutable Attribute is insufficient.
    forged_equipment = deepcopy(original_equipment)
    forged_equipment["certification"]["day"] = original_clock[0]
    forged_equipment["certification"]["hour"] = 0
    cot.db.clinic_equipment = forged_equipment
    ready, reason = downstream_ready()
    assert not ready and "lacks a completed signed event" in reason.lower(), reason
finally:
    clock.db.day, clock.db.hour = original_clock
    church.db.village_clinic = original_clinic
    cot.db.clinic_equipment = original_equipment

assert list(ledger.db.events or []) == original_events, "Guard signed an event"
assert clinic_state.normalize(church.db.village_clinic)["treatment"]["method"] == "supported"
assert clinic_cot_edge18.normalize(cot.db.clinic_equipment)["condition"] == "certified"
print("GDD_EDGE18_REWIND_AND_FORGED_ASSESSMENT_GUARDS_GREEN")
