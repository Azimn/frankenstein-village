"""Read-only EDGE-18 verification after a second actual Evennia restart.

The T-13 QA scene begins on day two but the live clock may advance during
additional authenticated negative tests and genuine process restarts.
Validate the actual signed later-day patient instead of rewinding the clock.
"""
from copy import deepcopy

from evennia.accounts.models import AccountDB
from evennia.scripts.models import ScriptDB
from evennia.utils import search
from world import clinic_state, clinic_cot_edge18, clinic_cot_work


def one(key):
    found = [obj for obj in search.search_object(key) if obj.key == key]
    assert len(found) == 1, (key, len(found))
    return found[0]


clock = ScriptDB.objects.get(db_key="village_time")
assert int(clock.db.day) >= 2, "Original day-two QA setup was not reached"
church = one("St. Lazarus Church")
cot = one("a clinic treatment cot")
assert cot.location == church
healer = AccountDB.objects.get(username="qa_healer_assessor")
smith = AccountDB.objects.get(username="qa_smith_repair")
assert healer.id != smith.id
assert not healer.is_connected and not smith.is_connected

clinic = clinic_state.normalize(church.db.village_clinic)
patient_day = clinic["day"]
assert 2 <= patient_day <= int(clock.db.day), "Later-day treatment chronology is invalid"
assert clinic["condition"] == clinic_state.CONDITIONS[
    (patient_day - 1) % len(clinic_state.CONDITIONS)
]
assessment = clinic["assessment"]
treatment = clinic["treatment"]
assert assessment and treatment
assert assessment["account_id"] == treatment["account_id"] == healer.id
assert treatment["method"] == "supported"
assert treatment["improvement"] == 30
assert treatment["assessment_event_id"] == assessment["event_id"]
assert assessment["day"] == treatment["day"] == patient_day
assert len([row for row in clinic["history"] if row["day"] == 1]) == 1
day_one = next(row for row in clinic["history"] if row["day"] == 1)
assert day_one["treatment"]["method"] == "compress"
assert day_one["assessment"]["event_id"] != assessment["event_id"]
assert clinic["records_permission"] is None, (
    "Day-one consent leaked into the next patient's case"
)

equipment = clinic_cot_edge18.normalize(cot.db.clinic_equipment)
assert equipment["condition"] == "certified"
brace = equipment["brace"]
cert = equipment["certification"]
assert brace["account_id"] != cert["account_id"] == healer.id
assert brace["day"] == cert["day"] == 1
assert cert["assessment_event_id"] == day_one["assessment"]["event_id"]
assert "clinically approved" in cot.get_display_desc().lower()
public = clinic_state.public_lines(church.db.village_clinic, patient_day).lower()
assert "care has been provided" in public
assert clinic["condition"] not in public and "healertester" not in public
assert clinic["condition"] not in clinic_state.private_lines(
    church.db.village_clinic, patient_day, account_id=smith.id,
    mask_id=one("SmithTester").id
).lower()

ledger = ScriptDB.objects.get(db_key="world_event_ledger")
assess_event = ledger.get_event(assessment["event_id"])
treat_event = ledger.get_event(treatment["event_id"])
cert_event = ledger.get_event(cert["event_id"])
brace_event = ledger.get_event(brace["event_id"])
assert assess_event["kind"] == "village.clinic_assess"
assert treat_event["kind"] == "village.clinic_treat"
assert cert_event["kind"] == "professional.clinic_cot_certified"
assert brace_event["kind"] == "professional.clinic_cot_braced"
assert all(row["status"] == "complete" for row in (
    assess_event, treat_event, cert_event, brace_event
))
assert assess_event["actor"]["account_id"] == healer.id
assert treat_event["actor"]["account_id"] == healer.id
assert treat_event["payload"]["method"] == "supported"
assert treat_event["payload"]["day"] == patient_day
assert treat_event["consequence"]["improvement"] == 30
assert treat_event["consequence"]["assessment_event_id"] == assessment["event_id"]
assert treat_event["consequence"]["room_id"] == church.id
assert len([row for row in ledger.db.events
            if row.get("kind") == "village.clinic_treat"
            and row.get("payload", {}).get("day") == patient_day]) == 1
# Signed physical history must survive mutable Attribute rollback, and
# public readback must never endorse forged brace or approval event IDs.
saved_equipment = deepcopy(dict(cot.db.clinic_equipment))
try:
    assert "clinically approved" in clinic_cot_work.public_status(cot).lower()
    cot.db.clinic_equipment = clinic_cot_edge18.fresh()
    prior, reason = clinic_cot_work._prior_completed_brace(cot)
    assert prior and "already" in reason.lower(), reason
    assert "inconsistent physical history" in clinic_cot_work.public_status(cot).lower()

    forged_brace = deepcopy(saved_equipment)
    forged_brace["brace"]["event_id"] += 1000000
    cot.db.clinic_equipment = forged_brace
    assert "unverified smith fitting" in clinic_cot_work.public_status(cot).lower()

    forged_approval = deepcopy(saved_equipment)
    forged_approval["certification"]["event_id"] += 1000000
    cot.db.clinic_equipment = forged_approval
    assert "unverified clinical approval" in clinic_cot_work.public_status(cot).lower()
finally:
    cot.db.clinic_equipment = saved_equipment
assert "clinically approved" in clinic_cot_work.public_status(cot).lower()
print("POST_SECOND_RESTART_GDD_EDGE18_COT_ROLLBACK_AND_FORGERY_REJECTED_GREEN")

print(f"POST_SECOND_RESTART_GDD_EDGE18_LATER_DAY_SUPPORTED_CARE_GREEN day={patient_day}")
if patient_day == 2:
    print("POST_SECOND_RESTART_GDD_EDGE18_DAY_TWO_SUPPORTED_CARE_GREEN")
