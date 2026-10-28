"""EDGE-18 disposable QA fixture for a real authenticated forged-source refusal.

Only the stopped test server may install or remove the forged assessment.
The client must attempt ordinary clinic treatment over an authenticated socket.
No source is invented in production and no signed event is created here.
"""
import os
from copy import deepcopy
from evennia.scripts.models import ScriptDB
from evennia.utils import search
from world import clinic_state, clinic_cot_edge18


def one(key):
    found = [o for o in search.search_object(key) if o.key == key]
    assert len(found) == 1, (key, len(found))
    return found[0]


church = one("St. Lazarus Church")
cot = one("a clinic treatment cot")
healer = one("HealerTester")
clock = ScriptDB.objects.get(db_key="village_time")
ledger = ScriptDB.objects.get(db_key="world_event_ledger")
day, hour = int(clock.db.day), int(clock.db.hour)
assert day == 2 and 0 <= hour <= 23, (day, hour)
assert clinic_cot_edge18.normalize(cot.db.clinic_equipment)["condition"] == "certified"


def treatment_ids():
    return sorted(
        event["id"] for event in list(ledger.db.events or [])
        if event.get("kind") == "village.clinic_treat"
        and event.get("status") == "complete"
    )


phase = os.environ.get("FV_EDGE18_AUTH_NEGATIVE_PHASE")
if phase == "stage":
    assert church.db.qa_edge18_negative_snapshot is None, "Fixture already staged"
    original = deepcopy(dict(church.db.village_clinic))
    next_day = clinic_state.refresh(original, day)
    assert next_day["assessment"] is None and next_day["treatment"] is None
    prior = original.get("assessment")
    assert prior and prior["day"] < day and prior["mask_id"] == healer.id
    assert prior["event_id"] > 0 and ledger.get_event(prior["event_id"])
    # Reuse an ACTUAL day-one assessment receipt but lie about its day/hour.
    # This passes the shape checks, so only ledger provenance can reject it.
    forged = deepcopy(next_day)
    forged["assessment"] = dict(
        prior, day=day, hour=hour, finding=next_day["condition"]
    )
    assert clinic_state.normalize(forged)["assessment"] is not None
    church.db.qa_edge18_negative_snapshot = {
        "clinic": original, "treatment_ids": treatment_ids(),
        "cot": deepcopy(dict(cot.db.clinic_equipment)),
        "day": day, "hour": hour,
    }
    church.db.village_clinic = forged
    print("EDGE18_AUTHENTICATED_FORGED_SOURCE_STAGED")
elif phase == "restore":
    saved = church.db.qa_edge18_negative_snapshot
    assert saved is not None, "No staged fixture"
    try:
        assert (day, hour) == (saved["day"], saved["hour"]), "Clock moved during refusal"
        assert treatment_ids() == saved["treatment_ids"], "Forged source caused signed treatment"
        assert clinic_state.normalize(church.db.village_clinic)["treatment"] is None
        assert clinic_cot_edge18.normalize(cot.db.clinic_equipment)["condition"] == "certified"
        assert dict(cot.db.clinic_equipment) == saved["cot"], "Cot changed on refusal"
        print("EDGE18_AUTHENTICATED_FORGED_SOURCE_NO_SIGNED_TREATMENT_GREEN")
    finally:
        church.db.village_clinic = deepcopy(saved["clinic"])
        church.attributes.remove("qa_edge18_negative_snapshot")
    assert church.db.qa_edge18_negative_snapshot is None
else:
    raise RuntimeError("Set FV_EDGE18_AUTH_NEGATIVE_PHASE to stage or restore")
