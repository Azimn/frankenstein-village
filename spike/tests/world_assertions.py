"""Runtime assertions executed through evennia shell after a second build."""

from evennia import create_script
from evennia.accounts.models import AccountDB
from evennia.scripts.models import ScriptDB
from evennia.utils import search

from commands.account_cmds import _world_entry_allowed
from commands.village_cmds import PLAYABLE_RUMOR_IDS, load_rumor_seeds


def exact_objects(key):
    return [obj for obj in search.search_object(key) if obj.key == key]


def one(key):
    found = exact_objects(key)
    assert len(found) == 1, f"{key!r}: expected exactly one object, found {len(found)}"
    return found[0]


for room_key in (
    "Inn Common Room",
    "Inn Hallway",
    "Village Square",
    "The Blood of the Vine",
    "Tavern Back Hall",
    "The Lamp Shop",
    "St. Lazarus Church",
):
    one(room_key)

for script_key in (
    "world_event_ledger",
    "rumor_registry",
    "resident_population",
    "public_records",
    "public_mystery_registry",
    "private_mystery_registry",
    "situation_registry",
    "seasonal_framework_registry",
    "scheduled_event_registry",
    "server_event_registry",
    "random_incident_registry",
    "timed_incident_registry",
    "room_six",
    "moderation_queue",
    "ambient_life",
    "village_time",
):
    count = ScriptDB.objects.filter(db_key=script_key).count()
    assert count == 1, f"{script_key!r}: expected one script, found {count}"

bram = one("Bram")
assert bram.db.till_kr == 37, "rebuild reset Bram's live till"
assert "bram" in (bram.aliases.all() or []), "Bram alias did not converge"

bread = one("a loaf of bread")
assert bread.db.servings == 2, "rebuild reset live sideboard servings"

well = one("well")
assert well.typeclass_path == "typeclasses.objects.VillageWell"
assert "straight" in (well.db.desc or "").lower(), "well rumor has no inspectable evidence"

confessional = one("a confessional box")
assert "lavender" in (confessional.db.desc or "").lower(), (
    "confessional rumor has no inspectable evidence"
)

strongbox = one("tithe strongbox")
tithe_roll = one("tithe roll")
assert strongbox.typeclass_path == "typeclasses.objects.TitheStrongbox"
assert tithe_roll.typeclass_path == "typeclasses.objects.TitheRoll"

register = one("register")
register_desc = (register.db.desc or "").lower()
assert "last michaelmas" in register_desc and "crossed out" in register_desc, (
    "register rumor has no inspectable evidence"
)

playable = load_rumor_seeds()
ids = {int(num) for num, _body in playable}
assert ids == set(PLAYABLE_RUMOR_IDS) == {151, 201, 236}, ids
assert len(load_rumor_seeds(playable_only=False)) == 250, "canon rumor corpus changed"

# Production resident population: identity, schedules, fallback, persistence,
# progressive depth, fact claims, isolation, event wakeups, and cheap demotion.
import copy
from collections import Counter
from types import SimpleNamespace

from world.resident_data import FACT_BY_ID, RESIDENTS
from world.residents import (
    advance_population,
    all_residents,
    assign_fact,
    decay_resident_engagement,
    expose_fact_as_rumor,
    facts_known_by_player,
    gather_population_for_mass,
    generic_ask_line,
    get_population_registry,
    record_player_interaction,
    resident_definition,
    resident_state,
    save_state,
    set_lifecycle,
    set_location_availability,
)

population = all_residents()
assert len(population) == len(RESIDENTS) == 36, len(population)
resident_ids = [npc.db.resident_id for npc in population]
assert len(resident_ids) == len(set(resident_ids)), "duplicate resident stable id"
assert sum(
    npc.typeclass_path == "typeclasses.characters.ResidentNPC"
    for npc in population
) == 30
assert not one("M.").tags.has("resident", category="system"), (
    "M. is the dual-ontology Inn exception, not an IC population resident"
)

by_resident_id = {
    npc.db.resident_id: npc
    for npc in population
}
for stable_id, npc in by_resident_id.items():
    state = resident_state(npc)
    assert state["schema_version"] == 1
    assert state["stable_id"] == stable_id
    assert state["simulation_resolution"] in {
        "automaton", "reactive", "engaged", "focused"
    }
    assert state["character_depth"] in {"D", "C", "B", "A"}
    assert set(state["needs"]) == {
        "fatigue", "hunger", "safety", "affiliation", "duty"
    }

population_registry = get_population_registry()
rumor_registry = ScriptDB.objects.get(db_key="rumor_registry")
assert population_registry.db.metrics["population_size"] == 36

# The clean-checkout runner assigned a fact and closed the school before this
# second build. Both must survive the idempotent rebuild.
lark = by_resident_id["lark_vessey"]
qa_fact_id = lark.db.qa_fact_id
assert qa_fact_id, "resident persistence sentinel was not created"
assert any(
    fact["fact_id"] == qa_fact_id
    for fact in resident_state(lark)["facts"]
), "resident fact was erased by rebuild"
assert "lark_vessey" in (
    (population_registry.db.fact_claims or {}).get(qa_fact_id) or []
), "global fact claim was erased by rebuild"
school_state = (population_registry.db.location_states or {}).get("schoolhouse")
assert school_state and not school_state["available"]
assert school_state["reason"] == "school_destroyed"

state_snapshot = {
    stable_id: copy.deepcopy(npc.db.resident_state)
    for stable_id, npc in by_resident_id.items()
}
claims_snapshot = copy.deepcopy(dict(population_registry.db.fact_claims or {}))
locations_snapshot = copy.deepcopy(
    dict(population_registry.db.location_states or {})
)
public_records = ScriptDB.objects.get(db_key="public_records")
timed_registry = ScriptDB.objects.get(db_key="timed_incident_registry")
timed_incident_snapshot = copy.deepcopy(
    dict(timed_registry.db.incidents or {})
)
timed_metrics_snapshot = copy.deepcopy(
    dict(timed_registry.db.metrics or {})
)
public_records_snapshot = {
    "harbinger_drafts": copy.deepcopy(list(public_records.db.harbinger_drafts or [])),
    "harbinger_editions": copy.deepcopy(list(public_records.db.harbinger_editions or [])),
    "chronicle_entries": copy.deepcopy(list(public_records.db.chronicle_entries or [])),
    "depositions": copy.deepcopy(list(public_records.db.depositions or [])),
    "chronicle_refusals": copy.deepcopy(
        list(public_records.db.chronicle_refusals or [])
    ),
    "next_chronicle_refusal_id": public_records.db.next_chronicle_refusal_id,
    "harbinger_correction_disputes": copy.deepcopy(
        list(public_records.db.harbinger_correction_disputes or [])
    ),
    "next_harbinger_correction_dispute_id": (
        public_records.db.next_harbinger_correction_dispute_id
    ),
    "harbinger_obituary_cases": copy.deepcopy(
        list(public_records.db.harbinger_obituary_cases or [])
    ),
    "next_harbinger_obituary_case_id": (
        public_records.db.next_harbinger_obituary_case_id
    ),
    "next_story_id": public_records.db.next_story_id,
    "next_edition_id": public_records.db.next_edition_id,
    "next_chronicle_id": public_records.db.next_chronicle_id,
    "next_deposition_id": public_records.db.next_deposition_id,
    "last_harbinger_day": public_records.db.last_harbinger_day,
    "chronicle_gap_policy": public_records.db.chronicle_gap_policy,
    "chronicle_gap_source": public_records.db.chronicle_gap_source,
}
rumor_snapshot = {
    "rumors": copy.deepcopy(list(rumor_registry.db.rumors or [])),
    "transmissions": copy.deepcopy(list(rumor_registry.db.transmissions or [])),
    "next_rumor_id": rumor_registry.db.next_rumor_id,
    "next_transmission_id": rumor_registry.db.next_transmission_id,
}
rumor_belief_snapshot = {
    npc.id: copy.deepcopy(dict(npc.db.rumor_beliefs or {}))
    for npc in population
}
tavern_for_snapshot = one("The Blood of the Vine")
tavern_public_ids_snapshot = copy.deepcopy(
    list(tavern_for_snapshot.db.public_rumor_ids or [])
)
tavern_player_rumors_snapshot = copy.deepcopy(
    list(tavern_for_snapshot.db.player_rumors or [])
)

# Acceptance scenario: Wren follows school without cognition when the routine
# is valid, falls back home with an attributable cause when the school is
# destroyed, and resumes after restoration.
wren = by_resident_id["wren_vessey"]
wstate = resident_state(wren)
wstate["wake_reasons"] = []
wstate["engagement"] = 0.0
wstate["engagement_tier"] = "D"
wstate["simulation_resolution"] = "automaton"
wstate["metrics"]["decision_evaluations"] = 0
save_state(wren, wstate)
set_location_availability("schoolhouse", True)
advance_population(day=2, hour=10, emit=False)
wstate = resident_state(wren)
assert wstate["routine"]["logical_location"] == "schoolhouse"
assert wstate["routine"]["source"] == "schedule"
assert wstate["metrics"]["decision_evaluations"] == 0, (
    "successful automaton routine performed unnecessary cognition"
)

from world.events import publish_world_event
ledger = ScriptDB.objects.get(db_key="world_event_ledger")
ledger_events_snapshot = copy.deepcopy(list(ledger.db.events or []))
school_destroyed = publish_world_event(
    "building_destroyed",
    payload={"location_id": "schoolhouse", "cause": "school_destroyed"},
)
advance_population(day=2, hour=10, emit=False)
wstate = resident_state(wren)
assert wstate["routine"]["logical_location"] == RESIDENTS[
    next(
        i for i, resident in enumerate(RESIDENTS)
        if resident["stable_id"] == "wren_vessey"
    )
]["home_id"]
assert wstate["routine"]["source"] == "fallback"
assert wstate["routine"]["reason"] == "school_destroyed"
assert str(school_destroyed["id"]) in wstate["event_flags"]

school_restored = publish_world_event(
    "building_restored",
    payload={"location_id": "schoolhouse", "cause": "repairs_complete"},
)
advance_population(day=2, hour=10, emit=False)
assert resident_state(wren)["routine"]["logical_location"] == "schoolhouse"

# Public-record bridge: objective destruction creates a special Harbinger
# edition and a verified Chronicle entry. Restoration waits for the fixed
# morning issue. Corrections and Chronicle annotations append without erasing.
from world.publications import (
    annotate_chronicle,
    chronicle_disagreement_for_rumor,
    correct_harbinger_story,
    depositions_for_rumor,
    get_chronicle_entry,
    get_story,
    latest_edition,
    publish_due_harbinger,
    reconcile_chronicle_disagreement,
    reconcile_chronicle_disagreements,
    submit_deposition,
)
from world.harbinger_content import (
    correction_disputes_for_story,
    decide_tomorrows_obituary,
    ensure_harbinger_conflict,
    get_harbinger_conflict,
    get_harbinger_obituary_case,
    harbinger_obituary_cases,
    resolve_due_harbinger_conflicts,
    resolve_due_obituary_cases,
    submit_correction_dispute,
    submit_tomorrows_obituary,
)
destroy_refs = school_destroyed.get("publications") or {}
assert destroy_refs["harbinger_story_id"]
assert destroy_refs["chronicle_entry_id"]
assert destroy_refs["special_edition_id"]
destroy_story = get_story(destroy_refs["harbinger_story_id"])
assert destroy_story["basis"] == "objective"
assert destroy_story["status"] == "published"
assert "schoolhouse" in destroy_story["body"].lower()
destroy_entry = get_chronicle_entry(destroy_refs["chronicle_entry_id"])
original_chronicle_text = destroy_entry["text"]
annotated = annotate_chronicle(
    destroy_entry["id"],
    "Repairs began after the closure; this note does not alter the original entry.",
    source_event_ids=[school_restored["id"]],
    author="QA Chronicler",
)
assert annotated["text"] == original_chronicle_text
assert len(annotated["annotations"]) == 1

original_story_body = destroy_story["body"]
correction = correct_harbinger_story(
    destroy_story["id"],
    "Correction: the closure was confirmed before the cause was fully understood.",
    source_event_id=school_restored["id"],
)
assert correction and correction["basis"] == "correction"
assert get_story(destroy_story["id"])["body"] == original_story_body

morning = publish_due_harbinger(2, 8)
assert morning and not morning["special"]
assert correction["id"] in morning["story_ids"]
assert publish_due_harbinger(2, 8) is None, (
    "fixed Harbinger cadence printed twice on one game day"
)

# Harbinger Section 3.22, The Correction: a claimant says an older issue
# contained wording absent from every surviving copy. Preserve the discrepancy
# without rewriting the old story or upgrading the claim into accepted fact.
claimed_missing_text = "The schoolhouse burned before dawn."
correction_dispute_result, correction_dispute_error = submit_correction_dispute(
    wren,
    destroy_story["id"],
    claimed_missing_text,
)
assert correction_dispute_error is None
assert correction_dispute_result["created"]
correction_dispute = correction_dispute_result["dispute"]
dispute_story = correction_dispute_result["response_story"]
assert correction_dispute["story_id"] == destroy_story["id"]
assert correction_dispute["published_edition_id"] == (
    destroy_story["published_edition_id"]
)
assert correction_dispute["claimed_text"] == claimed_missing_text
assert len(correction_dispute["surviving_copy_hash"]) == 64
assert dispute_story["basis"] == "correction_dispute"
assert dispute_story["status"] == "pending"
assert dispute_story["disputes_story_id"] == destroy_story["id"]
assert dispute_story["surviving_copy_hash"] == (
    correction_dispute["surviving_copy_hash"]
)
assert get_story(destroy_story["id"])["body"] == original_story_body
assert get_story(destroy_story["id"])["correction_disputes"][-1][
    "claimed_text"
] == claimed_missing_text
assert correction_disputes_for_story(destroy_story["id"])[0]["id"] == (
    correction_dispute["id"]
)

repeat_dispute, repeat_dispute_error = submit_correction_dispute(
    wren,
    destroy_story["id"],
    claimed_missing_text,
)
assert repeat_dispute_error is None
assert not repeat_dispute["created"]
assert repeat_dispute["dispute"]["id"] == correction_dispute["id"]

present_wording, present_wording_error = submit_correction_dispute(
    wren,
    destroy_story["id"],
    "schoolhouse",
)
assert present_wording is None
assert "surviving copy already contains" in present_wording_error.lower()
assert get_story(destroy_story["id"])["body"] == original_story_body

# Harbinger Section 3.22, Tomorrow's Obituary: a submitted death notice for a
# living resident is an editorial dilemma, not an authority over lifecycle.
# Exercise all four choices and prove that none of them kills the subject.
obituary_targets = {
    "print": by_resident_id["wren_vessey"],
    "investigate": by_resident_id["lark_vessey"],
    "suppress": by_resident_id["miklos_farkas"],
    "mock": by_resident_id["old_vasile"],
}
obituary_results = {}
for action, subject in obituary_targets.items():
    before_lifecycle = (resident_state(subject).get("lifecycle") or {}).get("status")
    assert before_lifecycle == "active"
    opened, obituary_error = submit_tomorrows_obituary(
        wren,
        subject.db.resident_id,
    )
    assert obituary_error is None
    assert opened["created"]
    obituary_case = opened["case"]
    assert obituary_case["status"] == "open"
    assert obituary_case["lifecycle_at_submission"] == "active"

    closed, obituary_story, obituary_error = decide_tomorrows_obituary(
        wren,
        obituary_case["id"],
        action,
    )
    assert obituary_error is None
    assert closed["status"] == "closed"
    assert closed["decision"] == action
    assert closed["lifecycle_at_decision"] == "active"
    assert (resident_state(subject).get("lifecycle") or {}).get("status") == "active"

    decision_event = ledger.get_event(closed["event_id"])
    assert decision_event["kind"] == "harbinger.tomorrows_obituary_decision"
    assert decision_event["payload"]["chronicle_eligible"] is False
    assert decision_event["payload"]["harbinger"] is False
    assert decision_event["payload"]["decision"] == action
    assert decision_event["payload"]["lifecycle_status"] == "active"
    assert not (decision_event.get("publications") or {}).get("chronicle_entry_id")

    if action == "suppress":
        assert obituary_story is None
        assert closed["story_id"] is None
        assert not decision_event["payload"].get("resident_ids")
    else:
        assert obituary_story
        assert obituary_story["status"] == "pending"
        assert obituary_story["source_event_id"] == decision_event["id"]
        assert obituary_story["obituary_case_id"] == obituary_case["id"]
        assert obituary_story["obituary_subject_resident_id"] == (
            subject.db.resident_id
        )
        subject_flag = resident_state(subject)["event_flags"].get(
            str(decision_event["id"])
        )
        assert subject_flag
        assert subject_flag["payload"]["reaction"] == {
            "print": "angered_by_premature_obituary",
            "investigate": "relieved_by_obituary_investigation",
            "mock": "embarrassed_by_obituary_mockery",
        }[action]

    obituary_results[action] = {
        "case": closed,
        "story": obituary_story,
    }

assert obituary_results["print"]["story"]["basis"] == "premature_obituary"
assert "not as a certified death record" in (
    obituary_results["print"]["story"]["body"].lower()
)
assert obituary_results["investigate"]["story"]["basis"] == (
    "obituary_investigation"
)
assert "found" in obituary_results["investigate"]["story"]["headline"].lower()
assert obituary_results["mock"]["story"]["basis"] == "editorial_mockery"
assert "not a death" in obituary_results["mock"]["story"]["body"].lower()

duplicate_obituary, duplicate_obituary_error = submit_tomorrows_obituary(
    wren,
    "wren_vessey",
)
assert duplicate_obituary_error is None
assert not duplicate_obituary["created"]
assert duplicate_obituary["case"]["id"] == (
    obituary_results["print"]["case"]["id"]
)
assert len(harbinger_obituary_cases()) == 4
assert get_harbinger_obituary_case(
    obituary_results["investigate"]["case"]["id"]
)["decision"] == "investigate"

# If nobody chooses before press time, the safe default is suppression. The
# deadline must never auto-print an unverified death notice.
deadline_subject = by_resident_id["father_andrei"]
deadline_opened, deadline_error = submit_tomorrows_obituary(
    wren,
    deadline_subject.db.resident_id,
)
assert deadline_error is None and deadline_opened["created"]
deadline_case = deadline_opened["case"]
deadline_resolved = resolve_due_obituary_cases(
    deadline_case["deadline_day"],
    deadline_case["deadline_hour"],
)
assert deadline_resolved == [{
    "case_id": deadline_case["id"],
    "resolution": "deadline_suppressed",
    "story_id": None,
}]
deadline_closed = get_harbinger_obituary_case(deadline_case["id"])
assert deadline_closed["status"] == "closed"
assert deadline_closed["decision"] == "suppress"
assert deadline_closed["resolution"] == "deadline_suppressed"
assert deadline_closed["story_id"] is None
assert (resident_state(deadline_subject).get("lifecycle") or {}).get(
    "status"
) == "active"
assert len(harbinger_obituary_cases()) == 5

# A rumor may be news without becoming Chronicle truth.
reported = publish_world_event(
    "qa_reported_only",
    actor=magda if "magda" in globals() else None,
    payload={"harbinger": True},
    rumor="Someone claims a bell rang under the well.",
)
reported_refs = reported.get("publications") or {}
assert reported_refs["harbinger_story_id"]
assert reported_refs["chronicle_entry_id"] is None
assert get_story(reported_refs["harbinger_story_id"])["basis"] == "reported"

# Sealed/private events are never promoted into public records even when a
# content-free social rumor exists around the event.
private_event = publish_world_event(
    "confession",
    payload={"sealed": True},
    rumor="Someone was a long time in the box today.",
)
assert not private_event.get("publications")

# Chronicler Section 3.23, The Refused Entry: popularity is not archival
# evidence. Pick the most-carried canon rumor, petition it through a resident
# who currently believes it, and verify that the Chronicle canonizes only the
# institutional refusal while the Harbinger reports the social dispute.
from world.chronicle_content import (
    REFUSAL_CONFIDENCE_FLOOR,
    chronicle_refusal_for_rumor,
    petition_refused_entry,
)

canon_roots = [
    dict(root)
    for root in (rumor_registry.db.rumors or [])
    if root.get("canonical_seed_id") in PLAYABLE_RUMOR_IDS
]
support_by_root = {}
for root in canon_roots:
    support_by_root[root["id"]] = [
        npc
        for npc in population
        if (
            (rumor_registry.belief_for(npc, root["id"]) or {}).get("confidence", 0)
            >= REFUSAL_CONFIDENCE_FLOOR
        )
    ]
refusal_root = max(
    canon_roots,
    key=lambda root: len(support_by_root[root["id"]]),
)
refusal_supporters = support_by_root[refusal_root["id"]]
assert len(refusal_supporters) >= 3, (
    "canon rumor seeding no longer supplies a popular Refused Entry case"
)
refusal_ledger_count = len(ledger.db.events or [])
refusal_result, refusal_error = petition_refused_entry(
    refusal_supporters[0],
    refusal_root["id"],
)
assert refusal_error is None
assert refusal_result["created"]
refusal = refusal_result["refusal"]
refusal_entry = refusal_result["entry"]
assert refusal_entry["claim_status"] == "refused_canonization"
assert refusal_entry["source_rumor_ids"] == [refusal_root["id"]]
assert refusal_root["claim"] in refusal_entry["text"]
assert "does not certify the rumor as true or false" in refusal_entry["text"]
assert chronicle_refusal_for_rumor(refusal_root["id"])["id"] == refusal["id"]
refusal_event = ledger.get_event(refusal["event_id"])
assert refusal_event["kind"] == "chronicle.refused_entry"
assert refusal_event["payload"]["chronicle_eligible"] is False
assert refusal_event["payload"]["reaction"] == "angered_by_refusal"
assert refusal_event["publications"]["harbinger_story_id"]
assert refusal_event["publications"]["chronicle_entry_id"] is None
assert get_story(
    refusal_event["publications"]["harbinger_story_id"]
)["status"] == "pending"
for npc in refusal_supporters:
    event_flag = resident_state(npc)["event_flags"].get(str(refusal["event_id"]))
    assert event_flag
    assert event_flag["payload"]["reaction"] == "angered_by_refusal"

# A repeated petition preserves the first institutional decision rather than
# manufacturing another event or pretending repeated pressure is new evidence.
repeat_refusal, repeat_error = petition_refused_entry(
    refusal_supporters[0],
    refusal_root["id"],
)
assert repeat_error is None
assert not repeat_refusal["created"]
assert repeat_refusal["refusal"]["id"] == refusal["id"]
assert len(ledger.db.events or []) == refusal_ledger_count + 1

# Popularity must not be able to downgrade an already event-backed fact into a
# refused-rumor case. Build a synthetic public telling of the verified school
# destruction and give it more than enough supporters; the Chronicle must
# still point to its existing objective authority.
verified_rumor = rumor_registry.ensure_rumor(
    subject="qa:verified-school-destruction",
    claim="The schoolhouse was destroyed.",
    source_actor="QA witness",
    source_type="qa",
    original_event_id=school_destroyed["id"],
    origin_location="Village Square",
    confidence=0.90,
    emotional_charge=0.20,
    privacy="public",
    variants=[],
    family="qa:verified-school-destruction",
)
for npc in population[:4]:
    rumor_registry.hear_direct(
        verified_rumor["id"],
        npc,
        source_label="QA witness",
        source_type="qa",
        location="Village Square",
    )
verified_petition, verified_petition_error = petition_refused_entry(
    population[0],
    verified_rumor["id"],
)
assert verified_petition is None
assert "already has event-backed authority" in verified_petition_error.lower()
assert chronicle_refusal_for_rumor(verified_rumor["id"]) is None

# Printed stories feed public knowledge back into residents with explicit
# Harbinger provenance. Ilona reads institutional news deterministically.
harbinger_roots = [
    dict(root)
    for root in (rumor_registry.db.rumors or [])
    if root.get("source_type") == "harbinger"
    and root.get("original_event_id") == school_destroyed["id"]
]
assert len(harbinger_roots) == 1
ilona = by_resident_id["ilona_szabo"]
assert rumor_registry.belief_for(ilona, harbinger_roots[0]["id"]), (
    "printed Harbinger story did not feed knowledge back into the Chronicler"
)

# Shared situation engine and incident feed: one canonical world state,
# separate per-mask evidence, deterministic surfacing, and autonomous aftermath.
from world.situations import (
    TITHE_ID,
    TORN_CHRONICLE_ID,
    TEMPLATES,
    advance_situations,
    choose,
    chronicle_gap_description,
    discover_evidence,
    get_situation,
    get_situation_registry,
    harbinger_archive_evidence,
    incident_feed_candidates,
    resident_situation_ask,
    situation_status_for_player,
)

situation_registry = get_situation_registry()
assert set((situation_registry.db.situations or {}).keys()) == {
    TITHE_ID,
    TORN_CHRONICLE_ID,
}
situation_original = copy.deepcopy(dict(situation_registry.db.situations or {}))
situation_metrics_original = copy.deepcopy(dict(situation_registry.db.metrics or {}))
church = one("St. Lazarus Church")
church_state_original = {
    "tithe_strongbox_policy": church.db.tithe_strongbox_policy,
    "tithe_confidence": church.db.tithe_confidence,
    "roof_repair_delay_winters": church.db.roof_repair_delay_winters,
}

inc_alice = SimpleNamespace(id=910001, key="incident_alice", has_account=True)
inc_bob = SimpleNamespace(id=910002, key="incident_bob", has_account=True)

assert get_situation(TITHE_ID)["state"] == "surfaced"
assert get_situation(TORN_CHRONICLE_ID)["state"] == "dormant"
assert incident_feed_candidates() == [], (
    "dependent incident surfaced before its prerequisite aftermath"
)

discover_evidence(inc_alice, "lock", TITHE_ID)
discover_evidence(inc_bob, "roll", TITHE_ID)
alice_status = situation_status_for_player(inc_alice, TITHE_ID)
bob_status = situation_status_for_player(inc_bob, TITHE_ID)
assert [entry["id"] for entry in alice_status["evidence"]] == ["lock"]
assert [entry["id"] for entry in bob_status["evidence"]] == ["roll"]
assert "roll" not in {entry["id"] for entry in alice_status["evidence"]}
assert "lock" not in {entry["id"] for entry in bob_status["evidence"]}

# The authored witness is useful when available but never load-bearing.
andrei = one("Father Andrei")
andrei_line = andrei.ask_about(inc_bob, "strongbox")
assert "key was hanging where it belongs" in andrei_line.lower()
bob_after_witness = situation_status_for_player(inc_bob, TITHE_ID)
assert {entry["id"] for entry in bob_after_witness["evidence"]} == {
    "roll", "andrei"
}

failed_choice, choice_error = choose(inc_alice, "openly", TITHE_ID)
assert failed_choice is None and "at least 2" in choice_error

# Quiet branch occupies the only active feed slot until its timer resolves.
discover_evidence(inc_alice, "roll", TITHE_ID)
quiet, choice_error = choose(inc_alice, "quietly", TITHE_ID)
assert not choice_error
assert quiet["state"] == "changing"
assert quiet["branch"] == "quietly"
assert get_situation(TORN_CHRONICLE_ID)["state"] == "dormant"
quiet_event = ledger.get_event(quiet["event_ids"][-1])
assert quiet_event["kind"] == "incident.tithe_strongbox.quiet_inquiry"
assert not quiet_event.get("publications"), (
    "private inquiry leaked into the public-record pipeline"
)
assert advance_situations(
    day=quiet["deadline_day"],
    hour=quiet["deadline_hour"],
) == 1
quiet_done = get_situation(TITHE_ID)
assert quiet_done["state"] == "aftermath"
assert quiet_done["branch"] == "quietly"
assert church.db.tithe_strongbox_policy == "two_key"
assert church.db.tithe_confidence == "guarded"
assert get_situation(TORN_CHRONICLE_ID)["state"] == "surfaced", (
    "incident feed did not fill the newly available slot"
)
late_choice, late_error = choose(inc_bob, "openly", TITHE_ID)
assert late_choice is None and "door has already closed" in late_error

# Reset for the public branch.
situation_registry.db.situations = copy.deepcopy(situation_original)
situation_registry.db.metrics = copy.deepcopy(situation_metrics_original)
church.db.tithe_strongbox_policy = church_state_original["tithe_strongbox_policy"]
church.db.tithe_confidence = church_state_original["tithe_confidence"]
church.db.roof_repair_delay_winters = church_state_original[
    "roof_repair_delay_winters"
]
public_records.db.chronicle_gap_policy = public_records_snapshot[
    "chronicle_gap_policy"
]
public_records.db.chronicle_gap_source = public_records_snapshot[
    "chronicle_gap_source"
]

# Open branch is immediate, public, provenance-bearing, and releases the feed slot.
discover_evidence(inc_alice, "lock", TITHE_ID)
discover_evidence(inc_alice, "roll", TITHE_ID)
opened, choice_error = choose(inc_alice, "openly", TITHE_ID)
assert not choice_error
assert opened["state"] == "aftermath"
assert opened["branch"] == "openly"
assert church.db.tithe_strongbox_policy == "two_key"
assert church.db.tithe_confidence == "divided"
open_event = ledger.get_event(opened["event_ids"][-1])
assert open_event["kind"] == "incident.tithe_strongbox.open_accusation"
assert open_event["rumor"]["rumor_id"] in opened["rumor_ids"]
assert open_event["publications"]["harbinger_story_id"]
assert open_event["publications"]["chronicle_entry_id"]
assert open_event["publications"]["special_edition_id"]
assert get_story(
    open_event["publications"]["harbinger_story_id"]
)["status"] == "published"
torn = get_situation(TORN_CHRONICLE_ID)
assert torn["state"] == "surfaced"
assert public_records.db.chronicle_gap_policy == "open_gap"

# Chronicler Section 3.23, Revision by Evidence: a mask may append evidence it
# actually discovered to an older Chronicle entry. The original text and claim
# status remain immutable, duplicate provenance is rejected, and another mask
# cannot cite evidence it has not discovered.
from world.chronicle_content import (
    revision_evidence_for_player,
    submit_evidence_revision,
)
open_entry_id = open_event["publications"]["chronicle_entry_id"]
open_entry_before = get_chronicle_entry(open_entry_id)
original_open_text = open_entry_before["text"]
original_open_status = open_entry_before["claim_status"]
revision_refs = revision_evidence_for_player(inc_alice)
assert {
    (ref["situation_id"], ref["evidence_id"])
    for ref in revision_refs
} >= {
    (TITHE_ID, "lock"),
    (TITHE_ID, "roll"),
}
revised_entry, revision_error = submit_evidence_revision(
    inc_alice,
    open_entry_id,
    "strongbox",
    "roll",
)
assert revision_error is None
assert revised_entry["text"] == original_open_text
assert revised_entry["claim_status"] == original_open_status
revision_annotation = revised_entry["annotations"][-1]
assert revision_annotation["annotation_type"] == "evidence_revision"
assert revision_annotation["source_mask"] == inc_alice.key
assert revision_annotation["source_evidence_refs"] == [{
    "situation_id": TITHE_ID,
    "evidence_id": "roll",
    "label": "the tithe roll",
    "provenance": "documentary",
    "summary": TEMPLATES[TITHE_ID]["evidence"]["roll"]["summary"],
}]
assert "original entry and its prior claim status remain unchanged" in (
    revision_annotation["text"].lower()
)
duplicate_revision, duplicate_error = submit_evidence_revision(
    inc_alice,
    open_entry_id,
    "strongbox",
    "roll",
)
assert duplicate_revision is None and "already cited" in duplicate_error.lower()
unrelated_revision, unrelated_error = submit_evidence_revision(
    inc_alice,
    destroy_entry["id"],
    "strongbox",
    "lock",
)
assert unrelated_revision is None
assert "no situation-linked event provenance" in unrelated_error.lower()
unseen_revision, unseen_error = submit_evidence_revision(
    inc_bob,
    open_entry_id,
    "strongbox",
    "lock",
)
assert unseen_revision is None
assert "has not discovered" in unseen_error.lower()

# Save the feed-surfaced world as the common starting point for the second
# incident's three outcome branches.
feed_surface_snapshot = copy.deepcopy(
    dict(situation_registry.db.situations or {})
)

# Different masks may discover different archive evidence.
gap_text = chronicle_gap_description(inc_alice)
assert "cut out cleanly" in gap_text
archive_text = harbinger_archive_evidence(inc_bob)
assert "newspaper records" in archive_text
alice_torn = situation_status_for_player(inc_alice, TORN_CHRONICLE_ID)
bob_torn = situation_status_for_player(inc_bob, TORN_CHRONICLE_ID)
assert {entry["id"] for entry in alice_torn["evidence"]} == {"gap"}
assert {entry["id"] for entry in bob_torn["evidence"]} == {
    "harbinger_archive"
}

# Ilona is a third optional witness channel, not a survival dependency.
ilona = by_resident_id["ilona_szabo"]
ilona_line = resident_situation_ask(ilona, inc_bob, "missing Chronicle pages")
assert ilona_line and "newspaper copy" in ilona_line.lower()
assert {entry["id"] for entry in situation_status_for_player(
    inc_bob, TORN_CHRONICLE_ID
)["evidence"]} == {"harbinger_archive", "ilona"}

# Reconstruction requires two channels and visibly remains press-derived.
failed_torn, torn_error = choose(
    inc_alice,
    "reconstruct",
    TORN_CHRONICLE_ID,
)
assert failed_torn is None and "at least 2" in torn_error
harbinger_archive_evidence(inc_alice)
reconstructed, torn_error = choose(
    inc_alice,
    "reconstruct",
    TORN_CHRONICLE_ID,
)
assert not torn_error
assert reconstructed["state"] == "aftermath"
assert reconstructed["branch"] == "reconstruct"
assert public_records.db.chronicle_gap_policy == "reconstructed_from_harbinger"
assert public_records.db.chronicle_gap_source == "Harbinger archive"
reconstruct_event = ledger.get_event(reconstructed["event_ids"][-1])
assert reconstruct_event["kind"] == "incident.torn_chronicle.reconstructed"
assert reconstruct_event["publications"]["harbinger_story_id"]
assert reconstruct_event["publications"]["chronicle_entry_id"]
assert reconstruct_event["publications"]["special_edition_id"]
assert "press-derived" in chronicle_gap_description(inc_alice).lower()
late_torn, late_torn_error = choose(
    inc_bob,
    "preserve",
    TORN_CHRONICLE_ID,
)
assert late_torn is None and "door has already closed" in late_torn_error

# Preserve branch starts from the same surfaced state and keeps the gap honest.
situation_registry.db.situations = copy.deepcopy(feed_surface_snapshot)
public_records.db.chronicle_gap_policy = "open_gap"
public_records.db.chronicle_gap_source = None
chronicle_gap_description(inc_alice)
harbinger_archive_evidence(inc_alice)
preserved, preserve_error = choose(
    inc_alice,
    "preserve",
    TORN_CHRONICLE_ID,
)
assert not preserve_error
assert preserved["state"] == "aftermath"
assert preserved["branch"] == "preserve"
assert public_records.db.chronicle_gap_policy == "preserved_gap"
assert "left unreconstructed" in chronicle_gap_description(inc_alice).lower()

# Left alone is authored continuation, not frozen content.
situation_registry.db.situations = copy.deepcopy(feed_surface_snapshot)
public_records.db.chronicle_gap_policy = "open_gap"
public_records.db.chronicle_gap_source = None
untouched_torn = get_situation(TORN_CHRONICLE_ID)
assert advance_situations(
    day=untouched_torn["deadline_day"],
    hour=untouched_torn["deadline_hour"],
) == 1
famous_gap = get_situation(TORN_CHRONICLE_ID)
assert famous_gap["state"] == "aftermath"
assert famous_gap["branch"] == "left_alone"
assert public_records.db.chronicle_gap_policy == "famous_gap"

# Reset again and prove the first incident also progresses when nobody acts.
situation_registry.db.situations = copy.deepcopy(situation_original)
situation_registry.db.metrics = copy.deepcopy(situation_metrics_original)
church.db.tithe_strongbox_policy = church_state_original["tithe_strongbox_policy"]
church.db.tithe_confidence = church_state_original["tithe_confidence"]
church.db.roof_repair_delay_winters = church_state_original[
    "roof_repair_delay_winters"
]
public_records.db.chronicle_gap_policy = public_records_snapshot[
    "chronicle_gap_policy"
]
public_records.db.chronicle_gap_source = public_records_snapshot[
    "chronicle_gap_source"
]
untouched = get_situation(TITHE_ID)
assert advance_situations(
    day=untouched["deadline_day"],
    hour=untouched["deadline_hour"],
) == 1
left_alone = get_situation(TITHE_ID)
assert left_alone["state"] == "aftermath"
assert left_alone["branch"] == "left_alone"
assert church.db.tithe_strongbox_policy == "two_key"
assert church.db.tithe_confidence == "low"
assert int(church.db.roof_repair_delay_winters or 0) >= 1
assert get_situation(TORN_CHRONICLE_ID)["state"] == "surfaced"

# QA branches must leave the actual playtest world in the untouched initial
# state. Restore canonical event/publication/rumor registries and readership.
situation_registry.db.situations = copy.deepcopy(situation_original)
situation_registry.db.metrics = copy.deepcopy(situation_metrics_original)
church.db.tithe_strongbox_policy = church_state_original["tithe_strongbox_policy"]
church.db.tithe_confidence = church_state_original["tithe_confidence"]
church.db.roof_repair_delay_winters = church_state_original[
    "roof_repair_delay_winters"
]
ledger.db.events = copy.deepcopy(ledger_events_snapshot)
# Synthetic school and situation events above are deliberately erased from the
# canonical ledger before later isolation tests. Erase their resident-side
# flags too so a reused QA identifier cannot masquerade as a new exposure.
_baseline_event_ids = {
    str(event["id"]) for event in ledger_events_snapshot
}
for npc in population:
    _state = resident_state(npc)
    _state["event_flags"] = {
        key: value
        for key, value in (_state.get("event_flags") or {}).items()
        if str(key) in _baseline_event_ids
    }
    save_state(npc, _state)
for key, value in public_records_snapshot.items():
    setattr(public_records.db, key, copy.deepcopy(value))
rumor_registry.db.rumors = copy.deepcopy(rumor_snapshot["rumors"])
rumor_registry.db.transmissions = copy.deepcopy(rumor_snapshot["transmissions"])
rumor_registry.db.next_rumor_id = rumor_snapshot["next_rumor_id"]
rumor_registry.db.next_transmission_id = rumor_snapshot["next_transmission_id"]
for npc in population:
    npc.db.rumor_beliefs = copy.deepcopy(
        rumor_belief_snapshot.get(npc.id, {})
    )
tavern_for_snapshot.db.public_rumor_ids = copy.deepcopy(
    tavern_public_ids_snapshot
)
tavern_for_snapshot.db.player_rumors = copy.deepcopy(
    tavern_player_rumors_snapshot
)

# Timed incident windows reward presence without erasing content for absence.
# They are independent of the major situation feed and use direct current-time
# expiry rather than replaying every elapsed tick.
from world.timed_incidents import (
    WELL_BOILS_ID,
    advance_timed_incidents,
    get_timed_incident,
    maybe_start_timed_incidents,
    record_observation,
    start_timed_incident,
    status_for_player as timed_status_for_player,
)

assert set((timed_registry.db.incidents or {}).keys()) == {WELL_BOILS_ID}
assert get_timed_incident(WELL_BOILS_ID)["state"] == "dormant"

timed_alice = SimpleNamespace(id=920001, key="timed_alice", has_account=True)
timed_bob = SimpleNamespace(id=920002, key="timed_bob", has_account=True)

started = start_timed_incident(
    WELL_BOILS_ID,
    day=1,
    hour=22,
    now=1000.0,
    force=True,
)
assert started["state"] == "active"
assert started["current"]["expires_at"] == 1600.0
start_event = ledger.get_event(started["current"]["start_event_id"])
assert start_event["kind"] == "timed.well_boils.started"
assert not start_event.get("publications"), (
    "private live window was prematurely published"
)

firsthand = record_observation(
    timed_alice,
    WELL_BOILS_ID,
    source="qa_live_window",
)
assert firsthand["quality"] == "firsthand"
assert "rope trembled" in firsthand["summary"].lower()
assert timed_status_for_player(timed_bob, WELL_BOILS_ID) is None

assert advance_timed_incidents(now=1599.0) == 0
assert advance_timed_incidents(now=1601.0) == 1
resolved = get_timed_incident(WELL_BOILS_ID)
assert resolved["state"] == "aftermath"
aftermath_event = ledger.get_event(resolved["current"]["aftermath_event_id"])
assert aftermath_event["kind"] == "timed.well_boils.aftermath"
assert aftermath_event["rumor"]["rumor_id"] == resolved["current"]["rumor_id"]
assert aftermath_event["publications"]["harbinger_story_id"]
assert aftermath_event["publications"]["chronicle_entry_id"] is None, (
    "brief well disturbance was promoted into Chronicle truth"
)

late = record_observation(
    timed_bob,
    WELL_BOILS_ID,
    source="qa_after_window",
)
assert late["quality"] == "aftermath"
assert "mineral ring" in late["summary"].lower()
record_observation(
    timed_alice,
    WELL_BOILS_ID,
    source="qa_return_visit",
)
assert timed_status_for_player(
    timed_alice,
    WELL_BOILS_ID,
)["observation"]["quality"] == "firsthand", (
    "later residue downgraded retained firsthand evidence"
)

# A fully unwitnessed occurrence still resolves into traces, rumor, and press.
unwitnessed = start_timed_incident(
    WELL_BOILS_ID,
    day=2,
    hour=3,
    now=2000.0,
    force=True,
)
assert unwitnessed["state"] == "active"
assert not unwitnessed["current"]["player_observations"]
assert advance_timed_incidents(now=2601.0) == 1
unwitnessed_done = get_timed_incident(WELL_BOILS_ID)
assert unwitnessed_done["state"] == "aftermath"
assert unwitnessed_done["current"]["rumor_id"]
assert unwitnessed_done["current"]["publications"]["harbinger_story_id"]

# Recurrence obeys the authored weekly cadence and archives bounded history.
assert maybe_start_timed_incidents(
    day=8,
    hour=22,
    now=3000.0,
) == [], "cooldown allowed the well window back too early"
scheduled = maybe_start_timed_incidents(
    day=15,
    hour=22,
    now=3000.0,
)
assert scheduled == [WELL_BOILS_ID]
recurred = get_timed_incident(WELL_BOILS_ID)
assert recurred["state"] == "active"
assert recurred["occurrence_count"] == 3
assert len(recurred["history"]) == 2
assert len(recurred["history"]) <= 12

# Remove synthetic timed-window effects before the remainder of regression.
timed_registry.db.incidents = copy.deepcopy(timed_incident_snapshot)
timed_registry.db.metrics = copy.deepcopy(timed_metrics_snapshot)
ledger.db.events = copy.deepcopy(ledger_events_snapshot)
for npc in population:
    _state = resident_state(npc)
    _state["event_flags"] = {
        key: value
        for key, value in (_state.get("event_flags") or {}).items()
        if str(key) in _baseline_event_ids
    }
    save_state(npc, _state)
for key, value in public_records_snapshot.items():
    setattr(public_records.db, key, copy.deepcopy(value))
rumor_registry.db.rumors = copy.deepcopy(rumor_snapshot["rumors"])
rumor_registry.db.transmissions = copy.deepcopy(rumor_snapshot["transmissions"])
rumor_registry.db.next_rumor_id = rumor_snapshot["next_rumor_id"]
rumor_registry.db.next_transmission_id = rumor_snapshot["next_transmission_id"]
for npc in population:
    npc.db.rumor_beliefs = copy.deepcopy(
        rumor_belief_snapshot.get(npc.id, {})
    )
tavern_for_snapshot.db.public_rumor_ids = copy.deepcopy(
    tavern_public_ids_snapshot
)
tavern_for_snapshot.db.player_rumors = copy.deepcopy(
    tavern_player_rumors_snapshot
)

# Seasonal chapters modify the existing world instead of replacing it.
from world.seasonal_frameworks import (
    DEFINITIONS as SEASONAL_DEFINITIONS,
    EMPTY_PLACES_ID,
    FROZEN_ROADS_ID,
    LONG_SHADOWS_ID,
    RECKONING_ID,
    THAW_BELOW_ID,
    VISITORS_ID,
    OVERLAY_KEY as SEASONAL_OVERLAY_KEY,
    advance_seasonal_framework,
    apply_resident_target,
    calendar_line as seasonal_calendar_line,
    chapter_history,
    content_tags as seasonal_content_tags,
    current_chapter,
    economy_modifiers,
    get_seasonal_framework_registry,
    random_incident_bonus,
    weather_weights,
)

seasonal_registry = get_seasonal_framework_registry()
seasonal_snapshot = {
    "active_id": seasonal_registry.db.active_id,
    "started_day": seasonal_registry.db.started_day,
    "cycle_started_day": seasonal_registry.db.cycle_started_day,
    "history": copy.deepcopy(list(seasonal_registry.db.history or [])),
    "metrics": copy.deepcopy(dict(seasonal_registry.db.metrics or {})),
}
seasonal_square = one("Village Square")
seasonal_overlay_snapshot = copy.deepcopy(
    dict(seasonal_square.db.scheduled_overlays or {})
)

assert current_chapter()["id"] == LONG_SHADOWS_ID
assert sum(
    int(SEASONAL_DEFINITIONS[stable_id]["duration_days"])
    for stable_id in (
        LONG_SHADOWS_ID,
        RECKONING_ID,
        EMPTY_PLACES_ID,
        FROZEN_ROADS_ID,
        THAW_BELOW_ID,
        VISITORS_ID,
    )
) == 365
assert "fog" in seasonal_content_tags()
assert weather_weights()["fog"] > weather_weights()["clear"]
assert SEASONAL_OVERLAY_KEY in (
    seasonal_square.db.scheduled_overlays or {}
)
assert "long shadows" in (
    seasonal_square.db.scheduled_overlays or {}
)[SEASONAL_OVERLAY_KEY].lower()
assert "The Weeks of Long Shadows" in seasonal_calendar_line(1)

# Optional evening public routines close earlier, while essential night roles
# remain exempt. This is schedule pressure, not a second scheduling engine.
ilona_definition = resident_definition(by_resident_id["ilona_szabo"])
ilona_target = {
    "desired_location": "tavern",
    "logical_location": "tavern",
    "activity": "listens more than she speaks",
    "source": "schedule",
    "reason": None,
}
seasonal_ilona = apply_resident_target(
    ilona_definition,
    ilona_target,
    day=1,
    hour=21,
)
assert seasonal_ilona["logical_location"] == ilona_definition["home_id"]
assert seasonal_ilona["source"] == "seasonal"

miklos_definition = resident_definition(by_resident_id["miklos_farkas"])
night_target = {
    "desired_location": "village_square",
    "logical_location": "village_square",
    "activity": "tends the lamps",
    "source": "schedule",
    "reason": None,
}
assert apply_resident_target(
    miklos_definition,
    night_target,
    day=1,
    hour=21,
)["logical_location"] == "village_square"

# Long Shadows raises odd evening texture without making it dominant.
lamp_definition = {
    "tone": "odd",
}
assert random_incident_bonus(
    "RANDOM-EXTINGUISHED-LAMP",
    lamp_definition,
    day=1,
    hour=21,
    weather="fog",
) > random_incident_bonus(
    "RANDOM-EXTINGUISHED-LAMP",
    lamp_definition,
    day=1,
    hour=12,
    weather="fog",
)

# Direct catch-up crosses chapter boundaries without replaying each day.
transitions = advance_seasonal_framework(day=92, hour=0, emit=False)
assert [item["to"] for item in transitions] == [
    RECKONING_ID,
    EMPTY_PLACES_ID,
    FROZEN_ROADS_ID,
]
assert current_chapter(day=92)["id"] == FROZEN_ROADS_ID
assert economy_modifiers()["travel_cost"] == 1.50
assert len(chapter_history()) == 3

# A real boundary writes durable public history with provenance. Restore it
# afterward so synthetic season QA cannot leak into later network playtests.
seasonal_ilona_state = copy.deepcopy(
    by_resident_id["ilona_szabo"].db.resident_state
)
seasonal_registry.db.active_id = LONG_SHADOWS_ID
seasonal_registry.db.started_day = 1
seasonal_registry.db.cycle_started_day = 1
seasonal_registry.db.history = []
transition = advance_seasonal_framework(day=31, hour=0, emit=True)
assert len(transition) == 1
assert transition[0]["to"] == RECKONING_ID
season_events = [
    event for event in (ledger.db.events or [])
    if event.get("kind") == "seasonal.chapter_changed"
]
assert season_events
season_event = season_events[-1]
assert season_event["publications"]["harbinger_story_id"]
assert season_event["publications"]["chronicle_entry_id"]
assert "debts" in seasonal_content_tags()
assert economy_modifiers()["debt_pressure"] == 1.35

# Restore the actual chapter and all synthetic public history.
seasonal_registry.db.active_id = seasonal_snapshot["active_id"]
seasonal_registry.db.started_day = seasonal_snapshot["started_day"]
seasonal_registry.db.cycle_started_day = seasonal_snapshot["cycle_started_day"]
seasonal_registry.db.history = copy.deepcopy(seasonal_snapshot["history"])
seasonal_registry.db.metrics = copy.deepcopy(seasonal_snapshot["metrics"])
seasonal_square.db.scheduled_overlays = copy.deepcopy(
    seasonal_overlay_snapshot
)
by_resident_id["ilona_szabo"].db.resident_state = copy.deepcopy(
    seasonal_ilona_state
)
ledger.db.events = copy.deepcopy(ledger_events_snapshot)
for key, value in public_records_snapshot.items():
    setattr(public_records.db, key, copy.deepcopy(value))
rumor_registry.db.rumors = copy.deepcopy(rumor_snapshot["rumors"])
rumor_registry.db.transmissions = copy.deepcopy(rumor_snapshot["transmissions"])
rumor_registry.db.next_rumor_id = rumor_snapshot["next_rumor_id"]
rumor_registry.db.next_transmission_id = rumor_snapshot["next_transmission_id"]

# Recurring scheduled events share one persistent calendar registry. This
# section proves three different behaviors: a publication pulse, a civic
# activity window, and a social convergence window.
from world.scheduled_events import (
    HARBINGER_PUBLICATION_ID,
    MARKET_MORNING_ID,
    SUNDAY_SERVICE_ID,
    advance_scheduled_events,
    calendar_lines,
    day_name,
    get_scheduled_event,
)

scheduled_registry = ScriptDB.objects.get(db_key="scheduled_event_registry")
assert set((scheduled_registry.db.events or {}).keys()) == {
    HARBINGER_PUBLICATION_ID,
    MARKET_MORNING_ID,
    SUNDAY_SERVICE_ID,
}
for _scheduled_id in (
    HARBINGER_PUBLICATION_ID,
    MARKET_MORNING_ID,
    SUNDAY_SERVICE_ID,
):
    assert get_scheduled_event(_scheduled_id)["state"] == "idle"

scheduled_registry_snapshot = copy.deepcopy(
    dict(scheduled_registry.db.events or {})
)
scheduled_metrics_snapshot = copy.deepcopy(
    dict(scheduled_registry.db.metrics or {})
)
scheduled_resident_states = {
    npc.db.resident_id: copy.deepcopy(npc.db.resident_state)
    for npc in population
}
scheduled_resident_locations = {
    npc.db.resident_id: npc.location
    for npc in population
}
scheduled_resident_blessings = {
    npc.db.resident_id: npc.db.blessed_day
    for npc in population
}
scheduled_regulars = {
    obj.key: {
        "object": obj,
        "location": obj.location,
        "override": copy.deepcopy(obj.db.routine_override),
        "blessed_day": obj.db.blessed_day,
    }
    for obj in (
        one("Father Andrei"),
        one("Magda"),
        one("Old Vasile"),
    )
}
square = one("Village Square")
church_room = one("St. Lazarus Church")
square_overlays_snapshot = copy.deepcopy(
    dict(square.db.scheduled_overlays or {})
)
church_overlays_snapshot = copy.deepcopy(
    dict(church_room.db.scheduled_overlays or {})
)
routine_script = ScriptDB.objects.get(db_key="village_routine")
last_mass_snapshot = routine_script.db.last_mass_day
scheduled_ledger_snapshot = copy.deepcopy(list(ledger.db.events or []))
scheduled_public_snapshot = {
    key: copy.deepcopy(value)
    for key, value in public_records_snapshot.items()
}
scheduled_rumor_snapshot = {
    "rumors": copy.deepcopy(list(rumor_registry.db.rumors or [])),
    "transmissions": copy.deepcopy(list(rumor_registry.db.transmissions or [])),
    "next_rumor_id": rumor_registry.db.next_rumor_id,
    "next_transmission_id": rumor_registry.db.next_transmission_id,
}
scheduled_belief_snapshot = {
    npc.id: copy.deepcopy(dict(npc.db.rumor_beliefs or {}))
    for npc in population
}

assert day_name(7) == "Saturday"
assert day_name(8) == "Sunday"

# Daily Harbinger publication is now a calendar pulse rather than hard-coded
# clock logic. One pending article prints exactly once at the 08:00 boundary.
calendar_notice = publish_world_event(
    "qa_scheduled_notice",
    payload={
        "headline": "QA Calendar Notice",
        "public_summary": "A harmless notice exists only to test the calendar press pulse.",
    },
    rumor="A harmless QA notice is waiting for the morning paper.",
)
pending_story_id = calendar_notice["publications"]["harbinger_story_id"]
assert pending_story_id
edition_count_before = len(public_records.db.harbinger_editions or [])
pulse = advance_scheduled_events(day=3, hour=8)
assert pulse["pulsed"] == [HARBINGER_PUBLICATION_ID]
paper_event = get_scheduled_event(HARBINGER_PUBLICATION_ID)
assert paper_event["run_count"] == 1
assert paper_event["history"][-1]["result"]["published"]
assert public_records.db.last_harbinger_day == 3
assert len(public_records.db.harbinger_editions or []) == edition_count_before + 1
duplicate_pulse = advance_scheduled_events(day=3, hour=8)
assert duplicate_pulse["pulsed"] == []
assert get_scheduled_event(HARBINGER_PUBLICATION_ID)["run_count"] == 1
assert len(public_records.db.harbinger_editions or []) == edition_count_before + 1

# Saturday market morning temporarily concentrates useful professions in the
# square. It is a routine civic event, so it does not generate a world-event
# ledger entry merely for happening.
ledger_count_before_market = len(ledger.db.events or [])
market_start = advance_scheduled_events(day=7, hour=7)
assert market_start["started"] == [MARKET_MORNING_ID]
market_event = get_scheduled_event(MARKET_MORNING_ID)
assert market_event["state"] == "active"
market_ids = market_event["current"]["result"]["participant_ids"]
assert len(market_ids) >= 6
assert "Market morning fills the square" in (
    square.db.scheduled_overlays or {}
)[MARKET_MORNING_ID]
for stable_id in market_ids:
    market_state = resident_state(by_resident_id[stable_id])
    assert market_state["routine"]["logical_location"] == "square"
    assert market_state["routine"]["source"] == "deviation"
assert len(ledger.db.events or []) == ledger_count_before_market, (
    "ordinary market recurrence polluted the canonical event ledger"
)
calendar_now = "\n".join(calendar_lines(7, 7))
assert "Underway now: Market Morning." in calendar_now
assert "Next Sunday Mass: day 8 at 10:00." in calendar_now
duplicate_market = advance_scheduled_events(day=7, hour=7)
assert duplicate_market["started"] == []
assert get_scheduled_event(MARKET_MORNING_ID)["run_count"] == 1
market_end = advance_scheduled_events(day=7, hour=12)
assert market_end["ended"] == [MARKET_MORNING_ID]
assert MARKET_MORNING_ID not in (square.db.scheduled_overlays or {})
for stable_id in market_ids:
    market_state = resident_state(by_resident_id[stable_id])
    assert (market_state.get("routine_override") or {}).get("reason") != (
        "Saturday market morning"
    )
assert len(get_scheduled_event(MARKET_MORNING_ID)["history"]) == 1

# Sunday service is now started and ended by the same calendar. The existing
# liturgical Mass implementation remains the behavior engine.
routine_script.db.last_mass_day = None
service_start = advance_scheduled_events(day=8, hour=10)
assert service_start["started"] == [SUNDAY_SERVICE_ID]
service_event = get_scheduled_event(SUNDAY_SERVICE_ID)
assert service_event["state"] == "active"
assert service_event["current"]["result"]["attendee_count"] >= 5
assert "Sunday Mass is underway" in (
    church_room.db.scheduled_overlays or {}
)[SUNDAY_SERVICE_ID]
assert resident_state(wren)["routine"]["logical_location"] == "church"
mass_events = [
    event for event in (ledger.db.events or [])
    if event.get("kind") == "mass"
    and (event.get("payload") or {}).get("day") == 8
]
assert len(mass_events) == 1
duplicate_service = advance_scheduled_events(day=8, hour=10)
assert duplicate_service["started"] == []
assert get_scheduled_event(SUNDAY_SERVICE_ID)["run_count"] == 1
service_end = advance_scheduled_events(day=8, hour=11)
assert service_end["ended"] == [SUNDAY_SERVICE_ID]
assert SUNDAY_SERVICE_ID not in (church_room.db.scheduled_overlays or {})
assert (resident_state(wren).get("routine_override") or {}).get("reason") != (
    "Sunday mass"
)
assert len(get_scheduled_event(SUNDAY_SERVICE_ID)["history"]) == 1

# Restore the test world before lifecycle, relationship, and telnet scenarios.
scheduled_registry.db.events = copy.deepcopy(scheduled_registry_snapshot)
scheduled_registry.db.metrics = copy.deepcopy(scheduled_metrics_snapshot)
square.db.scheduled_overlays = copy.deepcopy(square_overlays_snapshot)
church_room.db.scheduled_overlays = copy.deepcopy(church_overlays_snapshot)
routine_script.db.last_mass_day = last_mass_snapshot
for stable_id, old_state in scheduled_resident_states.items():
    npc = by_resident_id[stable_id]
    npc.db.resident_state = copy.deepcopy(old_state)
    npc.db.blessed_day = scheduled_resident_blessings[stable_id]
    old_location = scheduled_resident_locations[stable_id]
    if old_location and npc.location != old_location:
        npc.move_to(old_location, quiet=True)
for data in scheduled_regulars.values():
    obj = data["object"]
    obj.db.routine_override = copy.deepcopy(data["override"])
    obj.db.blessed_day = data["blessed_day"]
    if data["location"] and obj.location != data["location"]:
        obj.move_to(data["location"], quiet=True)
ledger.db.events = copy.deepcopy(scheduled_ledger_snapshot)
for key, value in scheduled_public_snapshot.items():
    setattr(public_records.db, key, copy.deepcopy(value))
rumor_registry.db.rumors = copy.deepcopy(scheduled_rumor_snapshot["rumors"])
rumor_registry.db.transmissions = copy.deepcopy(
    scheduled_rumor_snapshot["transmissions"]
)
rumor_registry.db.next_rumor_id = scheduled_rumor_snapshot["next_rumor_id"]
rumor_registry.db.next_transmission_id = scheduled_rumor_snapshot[
    "next_transmission_id"
]
for npc in population:
    npc.db.rumor_beliefs = copy.deepcopy(
        scheduled_belief_snapshot.get(npc.id, {})
    )
tavern_for_snapshot.db.public_rumor_ids = copy.deepcopy(
    tavern_public_ids_snapshot
)
tavern_for_snapshot.db.player_rumors = copy.deepcopy(
    tavern_player_rumors_snapshot
)

# Random world incidents reuse the village clock and generic room overlays.
# Most texture must remain mundane; odd incidents are rarer and gain weight
# from appropriate environmental context rather than genre privilege.
from world.random_incidents import (
    EXTINGUISHED_LAMP_ID,
    PUBLIC_SNEEZE_ID,
    advance_random_incidents,
    candidate_table,
    current_random_incident,
    get_random_incident_registry,
    recent_random_incidents,
    reconcile_random_incident_overlay,
)

random_registry = get_random_incident_registry()
random_snapshot = {
    "current": copy.deepcopy(random_registry.db.current),
    "history": copy.deepcopy(list(random_registry.db.history or [])),
    "last_check_key": random_registry.db.last_check_key,
    "last_runs": copy.deepcopy(dict(random_registry.db.last_runs or {})),
    "metrics": copy.deepcopy(dict(random_registry.db.metrics or {})),
}
random_square_overlays = copy.deepcopy(dict(square.db.scheduled_overlays or {}))
weather_script = ScriptDB.objects.get(db_key="village_weather")
weather_snapshot = weather_script.db.state
random_ledger_snapshot = copy.deepcopy(list(ledger.db.events or []))
random_public_snapshot = {
    key: copy.deepcopy(value)
    for key, value in public_records_snapshot.items()
}
random_rumor_snapshot = {
    "rumors": copy.deepcopy(list(rumor_registry.db.rumors or [])),
    "transmissions": copy.deepcopy(list(rumor_registry.db.transmissions or [])),
    "next_rumor_id": rumor_registry.db.next_rumor_id,
    "next_transmission_id": rumor_registry.db.next_transmission_id,
}

# Market Morning changes the current world state by concentrating residents.
# Prove the random layer consumes that state rather than assuming a fixed crowd.
pre_market_candidates = {
    row["id"]: row for row in candidate_table(day=14, hour=8)
}
pre_market_square_density = 0
if PUBLIC_SNEEZE_ID in pre_market_candidates:
    pre_market_square_density = next(
        (
            loc["resident_count"]
            for loc in pre_market_candidates[PUBLIC_SNEEZE_ID]["locations"]
            if loc["key"] == "Village Square"
        ),
        0,
    )

advance_scheduled_events(day=14, hour=7)
market_candidates = candidate_table(day=14, hour=8)
market_by_id = {row["id"]: row for row in market_candidates}
assert PUBLIC_SNEEZE_ID in market_by_id
assert market_by_id[PUBLIC_SNEEZE_ID]["tone"] == "mundane"
market_square_density = next(
    (
        loc["resident_count"]
        for loc in market_by_id[PUBLIC_SNEEZE_ID]["locations"]
        if loc["key"] == "Village Square"
    ),
    0,
)
assert market_square_density > pre_market_square_density, (
    pre_market_square_density,
    market_square_density,
)

# Time and weather affect the odd environmental incident mechanically.
weather_script.db.state = "clear"
clear_rows = {row["id"]: row for row in candidate_table(day=14, hour=21)}
weather_script.db.state = "fog"
fog_rows = {row["id"]: row for row in candidate_table(day=14, hour=21)}
assert EXTINGUISHED_LAMP_ID in clear_rows
assert EXTINGUISHED_LAMP_ID in fog_rows
assert fog_rows[EXTINGUISHED_LAMP_ID]["weight"] > clear_rows[
    EXTINGUISHED_LAMP_ID
]["weight"]
assert fog_rows[PUBLIC_SNEEZE_ID]["weight"] > fog_rows[
    EXTINGUISHED_LAMP_ID
]["weight"], "odd texture became more common than mundane life by default"

# Force the accepted mundane template only to test execution deterministically.
mundane = advance_random_incidents(
    day=14,
    hour=8,
    force_id=PUBLIC_SNEEZE_ID,
)
assert mundane["started"] == PUBLIC_SNEEZE_ID
current = current_random_incident()
assert current["tone"] == "mundane"
assert current["subject"]["resident_id"]
assert current["location"] in {"Village Square", "The Blood of the Vine"}
mundane_room = one(current["location"])
assert PUBLIC_SNEEZE_ID in (mundane_room.db.scheduled_overlays or {})
mundane_event = ledger.get_event(current["event_id"])
assert mundane_event["kind"] == "random.random-public-sneeze"
assert not mundane_event.get("publications")
assert not mundane_event.get("rumor")

# One game hour later the overlay clears and history records the occurrence.
ended = advance_random_incidents(
    day=14,
    hour=9,
    force_id="NO-SUCH-RANDOM-INCIDENT",
)
assert ended["ended"] == PUBLIC_SNEEZE_ID
assert current_random_incident() is None
assert PUBLIC_SNEEZE_ID not in (mundane_room.db.scheduled_overlays or {})
assert recent_random_incidents(1)[0]["id"] == PUBLIC_SNEEZE_ID

# The odd template is separately executable and still remains private texture.
weather_script.db.state = "fog"
odd = advance_random_incidents(
    day=15,
    hour=21,
    force_id=EXTINGUISHED_LAMP_ID,
)
assert odd["started"] == EXTINGUISHED_LAMP_ID
lamp = current_random_incident()
assert lamp["tone"] == "odd"
assert lamp["location"] == "Village Square"
assert "neighboring lamps burn steadily" in (
    square.db.scheduled_overlays or {}
)[EXTINGUISHED_LAMP_ID]

# The persistent registry is canonical. If the visible projection disappears
# across a process boundary, reconciliation must restore it.
_random_projection = copy.deepcopy(dict(square.db.scheduled_overlays or {}))
_random_projection.pop(EXTINGUISHED_LAMP_ID, None)
square.db.scheduled_overlays = _random_projection
assert EXTINGUISHED_LAMP_ID not in (square.db.scheduled_overlays or {})
assert reconcile_random_incident_overlay()
assert EXTINGUISHED_LAMP_ID in (square.db.scheduled_overlays or {})

lamp_event = ledger.get_event(lamp["event_id"])
assert not lamp_event.get("publications")
assert not lamp_event.get("rumor")
# The lamp template lasts two game hours because its authored premise is a
# repeatedly failing lamp, not an instantaneous flicker.
assert current_random_incident()["id"] == EXTINGUISHED_LAMP_ID
advance_random_incidents(
    day=15,
    hour=23,
    force_id="NO-SUCH-RANDOM-INCIDENT",
)
assert EXTINGUISHED_LAMP_ID not in (square.db.scheduled_overlays or {})

# History is bounded. Texture cannot become an unbounded event log.
random_registry.db.history = [
    {"id": f"qa-{index}", "state": "ended"}
    for index in range(30)
]
weather_script.db.state = "fog"
advance_random_incidents(
    day=17,
    hour=21,
    force_id=EXTINGUISHED_LAMP_ID,
)
advance_random_incidents(
    day=17,
    hour=23,
    force_id="NO-SUCH-RANDOM-INCIDENT",
)
assert len(random_registry.db.history or []) == 24

# Restore random and scheduled QA effects before the remaining regression.
random_registry.db.current = copy.deepcopy(random_snapshot["current"])
random_registry.db.history = copy.deepcopy(random_snapshot["history"])
random_registry.db.last_check_key = random_snapshot["last_check_key"]
random_registry.db.last_runs = copy.deepcopy(random_snapshot["last_runs"])
random_registry.db.metrics = copy.deepcopy(random_snapshot["metrics"])
square.db.scheduled_overlays = copy.deepcopy(random_square_overlays)
weather_script.db.state = weather_snapshot
ledger.db.events = copy.deepcopy(random_ledger_snapshot)
for key, value in random_public_snapshot.items():
    setattr(public_records.db, key, copy.deepcopy(value))
rumor_registry.db.rumors = copy.deepcopy(random_rumor_snapshot["rumors"])
rumor_registry.db.transmissions = copy.deepcopy(
    random_rumor_snapshot["transmissions"]
)
rumor_registry.db.next_rumor_id = random_rumor_snapshot["next_rumor_id"]
rumor_registry.db.next_transmission_id = random_rumor_snapshot[
    "next_transmission_id"
]
# End the synthetic market if it was not already restored above.
scheduled_registry.db.events = copy.deepcopy(scheduled_registry_snapshot)
scheduled_registry.db.metrics = copy.deepcopy(scheduled_metrics_snapshot)
square.db.scheduled_overlays = copy.deepcopy(random_square_overlays)
for stable_id, old_state in scheduled_resident_states.items():
    npc = by_resident_id[stable_id]
    npc.db.resident_state = copy.deepcopy(old_state)
    old_location = scheduled_resident_locations[stable_id]
    if old_location and npc.location != old_location:
        npc.move_to(old_location, quiet=True)

# Server-wide events are broad conditions with independent local responses,
# not accepted quests. The Long Blackout is the first production framework.
from world.server_events import (
    LONG_BLACKOUT_ID,
    advance_server_events,
    contribute as contribute_server_event,
    get_server_event,
    get_server_event_registry,
    reconcile_server_event_overlays,
    start_server_event,
    status_lines as server_event_status_lines,
)

server_registry = get_server_event_registry()
assert set((server_registry.db.events or {}).keys()) == {LONG_BLACKOUT_ID}
server_snapshot = {
    "events": copy.deepcopy(dict(server_registry.db.events or {})),
    "metrics": copy.deepcopy(dict(server_registry.db.metrics or {})),
}
server_rooms = {
    key: one(key)
    for key in (
        "Village Square",
        "The Blood of the Vine",
        "St. Lazarus Church",
        "The Lamp Shop",
    )
}
server_overlay_snapshot = {
    key: copy.deepcopy(dict(room.db.scheduled_overlays or {}))
    for key, room in server_rooms.items()
}
server_ledger_snapshot = copy.deepcopy(list(ledger.db.events or []))
server_public_snapshot = {
    key: copy.deepcopy(getattr(public_records.db, key))
    for key in public_records_snapshot
}
server_rumor_snapshot = {
    "rumors": copy.deepcopy(list(rumor_registry.db.rumors or [])),
    "transmissions": copy.deepcopy(list(rumor_registry.db.transmissions or [])),
    "next_rumor_id": rumor_registry.db.next_rumor_id,
    "next_transmission_id": rumor_registry.db.next_transmission_id,
}
server_belief_snapshot = {
    npc.id: copy.deepcopy(dict(npc.db.rumor_beliefs or {}))
    for npc in population
}
server_resident_snapshot = {
    npc.db.resident_id: copy.deepcopy(npc.db.resident_state)
    for npc in population
}
server_tavern_public = copy.deepcopy(
    list(tavern_for_snapshot.db.public_rumor_ids or [])
)
server_tavern_player = copy.deepcopy(
    list(tavern_for_snapshot.db.player_rumors or [])
)

# The framework starts only at its hidden authored boundary unless forced.
assert advance_server_events(day=10, hour=18)["started"] == []
autostart = advance_server_events(day=10, hour=19)
assert autostart["started"] == [LONG_BLACKOUT_ID]
blackout = get_server_event(LONG_BLACKOUT_ID)
assert blackout["state"] == "active"
assert blackout["current"]["end_day"] == 11
assert blackout["current"]["end_hour"] == 7
assert not blackout["current"]["responses"]

active_overlay_id = f"{LONG_BLACKOUT_ID}:active"
for room_key, room in server_rooms.items():
    assert active_overlay_id in (room.db.scheduled_overlays or {}), room_key

start_event = ledger.get_event(blackout["current"]["start_event_id"])
assert start_event["kind"] == "server.long_blackout.started"
assert start_event["rumor"]["rumor_id"] == blackout["current"]["start_rumor_id"]
assert start_event["publications"]["harbinger_story_id"]
assert start_event["publications"]["chronicle_entry_id"] is None

# Relevant residents are woken from explicit structured IDs rather than prose.
for stable_id in (
    "miklos_farkas",
    "lucian_deville",
    "bram_v",
    "father_andrei",
    "sorin_dragomir",
):
    npc = by_resident_id[stable_id]
    flags = resident_state(npc).get("event_flags") or {}
    assert str(start_event["id"]) in flags, stable_id

# The registry, not room prose, is canonical across process boundaries.
square_server_overlays = copy.deepcopy(dict(square.db.scheduled_overlays or {}))
square_server_overlays.pop(active_overlay_id, None)
square.db.scheduled_overlays = square_server_overlays
assert active_overlay_id not in (square.db.scheduled_overlays or {})
assert reconcile_server_event_overlays()
assert active_overlay_id in (square.db.scheduled_overlays or {})

qa_square = SimpleNamespace(
    id=930001, key="qa_square", location=server_rooms["Village Square"],
    has_account=True, account=None,
)
qa_tavern = SimpleNamespace(
    id=930002, key="qa_tavern", location=server_rooms["The Blood of the Vine"],
    has_account=True, account=None,
)
qa_church = SimpleNamespace(
    id=930003, key="qa_church", location=server_rooms["St. Lazarus Church"],
    has_account=True, account=None,
)
qa_shop = SimpleNamespace(
    id=930004, key="qa_shop", location=server_rooms["The Lamp Shop"],
    has_account=True, account=None,
)

wrong, error = contribute_server_event(qa_square, "supplies")
assert wrong is None and "Lamp Shop" in error

for actor, action in (
    (qa_square, "lamps"),
    (qa_tavern, "shelter"),
    (qa_church, "candles"),
    (qa_shop, "supplies"),
):
    result, error = contribute_server_event(actor, action)
    assert result and error is None
    assert result["first_completion"]

duplicate, error = contribute_server_event(qa_square, "lamps")
assert duplicate is None and "already done" in error.lower()

blackout = get_server_event(LONG_BLACKOUT_ID)
assert set(blackout["current"]["responses"]) == {
    "lamps", "shelter", "candles", "supplies"
}
status_text = "\n".join(server_event_status_lines(qa_square))
assert "4 of 4" in status_text
assert "street lamps stabilized" in status_text

# It does not freeze offline and does not resolve early.
assert advance_server_events(day=11, hour=6)["resolved"] == []
resolved_result = advance_server_events(day=11, hour=7)
assert resolved_result["resolved"] == [LONG_BLACKOUT_ID]
blackout = get_server_event(LONG_BLACKOUT_ID)
assert blackout["state"] == "aftermath"
assert blackout["current"]["outcome"]["quality"] == "coordinated"
assert blackout["current"]["outcome"]["completed_response_count"] == 4

end_event = ledger.get_event(blackout["current"]["end_event_id"])
assert end_event["kind"] == "server.long_blackout.ended"
assert end_event["publications"]["harbinger_story_id"]
assert end_event["publications"]["chronicle_entry_id"]
assert blackout["current"]["end_rumor_id"]

aftermath_overlay_id = f"{LONG_BLACKOUT_ID}:aftermath"
for room_key, room in server_rooms.items():
    assert active_overlay_id not in (room.db.scheduled_overlays or {}), room_key
    assert aftermath_overlay_id in (room.db.scheduled_overlays or {}), room_key

# Aftermath is playable but finite, then the framework returns to dormancy.
assert advance_server_events(day=11, hour=12)["cleared"] == []
cleared_result = advance_server_events(day=11, hour=13)
assert cleared_result["cleared"] == [LONG_BLACKOUT_ID]
blackout = get_server_event(LONG_BLACKOUT_ID)
assert blackout["state"] == "dormant"
assert blackout["current"] is None
assert len(blackout["history"]) == 1

# No-intervention is also authored content, not a frozen or failed quest.
unanswered = start_server_event(
    LONG_BLACKOUT_ID,
    day=20,
    hour=19,
    force=True,
)
assert unanswered and unanswered["state"] == "active"
advance_server_events(day=21, hour=7)
unanswered = get_server_event(LONG_BLACKOUT_ID)
assert unanswered["state"] == "aftermath"
assert unanswered["current"]["outcome"]["quality"] == "rough"
assert unanswered["current"]["outcome"]["completed_response_count"] == 0
assert "without organized player help" in (
    unanswered["current"]["outcome"]["summary"]
)

# Restore all QA mutations before lifecycle and telnet scenarios.
server_registry.db.events = copy.deepcopy(server_snapshot["events"])
server_registry.db.metrics = copy.deepcopy(server_snapshot["metrics"])
for room_key, room in server_rooms.items():
    room.db.scheduled_overlays = copy.deepcopy(
        server_overlay_snapshot[room_key]
    )
ledger.db.events = copy.deepcopy(server_ledger_snapshot)
for key, value in server_public_snapshot.items():
    setattr(public_records.db, key, copy.deepcopy(value))
rumor_registry.db.rumors = copy.deepcopy(server_rumor_snapshot["rumors"])
rumor_registry.db.transmissions = copy.deepcopy(
    server_rumor_snapshot["transmissions"]
)
rumor_registry.db.next_rumor_id = server_rumor_snapshot["next_rumor_id"]
rumor_registry.db.next_transmission_id = server_rumor_snapshot[
    "next_transmission_id"
]
for npc in population:
    npc.db.rumor_beliefs = copy.deepcopy(
        server_belief_snapshot.get(npc.id, {})
    )
    old_state = server_resident_snapshot.get(npc.db.resident_id)
    if old_state is not None:
        npc.db.resident_state = copy.deepcopy(old_state)
tavern_for_snapshot.db.public_rumor_ids = copy.deepcopy(server_tavern_public)
tavern_for_snapshot.db.player_rumors = copy.deepcopy(server_tavern_player)

# Public mysteries preserve the distinction between observation and theory.
from world.public_mysteries import (
    MANOR_LIGHTS_ID,
    get_public_mystery,
    get_public_mystery_registry,
    manor_light_state,
    mystery_lines,
    observe_manor,
    submit_theory,
)

manor = one("the manor on the hill")
assert manor.typeclass_path == "typeclasses.objects.ManorView"
public_mystery_registry = get_public_mystery_registry()
assert set((public_mystery_registry.db.mysteries or {}).keys()) == {
    MANOR_LIGHTS_ID
}
public_mystery_snapshot = {
    "mysteries": copy.deepcopy(
        dict(public_mystery_registry.db.mysteries or {})
    ),
    "metrics": copy.deepcopy(dict(public_mystery_registry.db.metrics or {})),
}
mystery_ledger_snapshot = copy.deepcopy(list(ledger.db.events or []))
mystery_public_snapshot = {
    key: copy.deepcopy(getattr(public_records.db, key))
    for key in public_records_snapshot
}
mystery_rumor_snapshot = {
    "rumors": copy.deepcopy(list(rumor_registry.db.rumors or [])),
    "transmissions": copy.deepcopy(list(rumor_registry.db.transmissions or [])),
    "next_rumor_id": rumor_registry.db.next_rumor_id,
    "next_transmission_id": rumor_registry.db.next_transmission_id,
}
mystery_belief_snapshot = {
    npc.id: copy.deepcopy(dict(npc.db.rumor_beliefs or {}))
    for npc in population
}
mystery_tavern_public = copy.deepcopy(
    list(tavern_for_snapshot.db.public_rumor_ids or [])
)
mystery_tavern_player = copy.deepcopy(
    list(tavern_for_snapshot.db.player_rumors or [])
)

# Find one deterministic visible-light state without hard-coding a lucky hour.
lit_sample = None
dark_sample = None
for _day in range(1, 8):
    for _hour in (18, 19, 20, 21, 22, 23, 0, 1, 2, 3, 4, 5):
        for _weather in ("clear", "fog", "rain"):
            _state = manor_light_state(_day, _hour, _weather)
            if _state["lit"] and lit_sample is None:
                lit_sample = (_day, _hour, _weather, _state)
            if not _state["lit"] and dark_sample is None:
                dark_sample = (_day, _hour, _weather, _state)
assert lit_sample and dark_sample

qa_manor_a = SimpleNamespace(
    id=940001, key="qa_manor_a", location=square,
    has_account=True, account=None,
)
qa_manor_b = SimpleNamespace(
    id=940002, key="qa_manor_b", location=square,
    has_account=True, account=None,
)

_day, _hour, _weather, _state = lit_sample
first_obs = observe_manor(
    qa_manor_a,
    day=_day,
    hour=_hour,
    weather=_weather,
)
assert first_obs["lit"]
assert first_obs["pattern"] == _state["pattern"]
mystery = get_public_mystery(MANOR_LIGHTS_ID)
assert len(mystery["observations"]) == 1
assert len(mystery["observations"][0]["witnesses"]) == 1
assert mystery["first_signal_event_id"]
assert mystery["first_signal_rumor_id"]
assert mystery["first_signal_publications"]["harbinger_story_id"]
assert not mystery["first_signal_publications"].get("chronicle_entry_id")

signal_event = ledger.get_event(mystery["first_signal_event_id"])
assert signal_event["kind"] == "public_mystery.manor_lights.observed"
assert signal_event["rumor"]["rumor_id"] == mystery["first_signal_rumor_id"]

# A second witness to the same objective state attaches provenance rather than
# creating a duplicate "fact".
second_obs = observe_manor(
    qa_manor_b,
    day=_day,
    hour=_hour,
    weather=_weather,
)
assert second_obs["key"] == first_obs["key"]
mystery = get_public_mystery(MANOR_LIGHTS_ID)
assert len(mystery["observations"]) == 1
assert {
    witness["mask_id"]
    for witness in mystery["observations"][0]["witnesses"]
} == {qa_manor_a.id, qa_manor_b.id}

observe_manor(
    qa_manor_a,
    day=_day,
    hour=_hour,
    weather=_weather,
)
mystery = get_public_mystery(MANOR_LIGHTS_ID)
assert len(mystery["observations"][0]["witnesses"]) == 2

# A dark observation is equally valid evidence. Absence is measurable too.
_dark_day, _dark_hour, _dark_weather, _dark_state = dark_sample
dark_obs = observe_manor(
    qa_manor_a,
    day=_dark_day,
    hour=_dark_hour,
    weather=_dark_weather,
)
assert not dark_obs["lit"]
mystery = get_public_mystery(MANOR_LIGHTS_ID)
assert len(mystery["observations"]) == 2

theory, error = submit_theory(
    qa_manor_a,
    "The lights follow a maintenance routine the village has forgotten.",
)
assert theory and error is None
assert theory["status"] == "proposed"
assert theory["truth_status"] is None
mystery = get_public_mystery(MANOR_LIGHTS_ID)
assert len(mystery["theories"]) == 1
assert mystery["theories"][0]["truth_status"] is None
mystery_text = "\n".join(mystery_lines(qa_manor_a))
assert "Shared observations: 2" in mystery_text
assert "Provisional theories:" in mystery_text
assert "No metaphysical explanation is certified." in mystery_text

# Restore QA evidence and its publication side effects before later scenarios.
public_mystery_registry.db.mysteries = copy.deepcopy(
    public_mystery_snapshot["mysteries"]
)
public_mystery_registry.db.metrics = copy.deepcopy(
    public_mystery_snapshot["metrics"]
)
ledger.db.events = copy.deepcopy(mystery_ledger_snapshot)
for key, value in mystery_public_snapshot.items():
    setattr(public_records.db, key, copy.deepcopy(value))
rumor_registry.db.rumors = copy.deepcopy(mystery_rumor_snapshot["rumors"])
rumor_registry.db.transmissions = copy.deepcopy(
    mystery_rumor_snapshot["transmissions"]
)
rumor_registry.db.next_rumor_id = mystery_rumor_snapshot["next_rumor_id"]
rumor_registry.db.next_transmission_id = mystery_rumor_snapshot[
    "next_transmission_id"
]
for npc in population:
    npc.db.rumor_beliefs = copy.deepcopy(
        mystery_belief_snapshot.get(npc.id, {})
    )
tavern_for_snapshot.db.public_rumor_ids = copy.deepcopy(mystery_tavern_public)
tavern_for_snapshot.db.player_rumors = copy.deepcopy(mystery_tavern_player)

# Private mysteries create mask-specific information asymmetry. The thread
# belongs to the invited mask; deliberate disclosure shares knowledge without
# cloning ownership or becoming server-wide progress.
from evennia.utils import create as evennia_create
from world.private_mysteries import (
    HOUNDS_INVITATION_ID,
    deliver_hounds_invitation,
    get_private_mystery_registry,
    note_disclosure,
    open_hounds_followup,
    private_lines,
    private_mystery_answer,
    records_for,
)

private_registry = get_private_mystery_registry()
private_snapshot = {
    "records": copy.deepcopy(dict(private_registry.db.records or {})),
    "metrics": copy.deepcopy(dict(private_registry.db.metrics or {})),
}
private_rumor_snapshot = {
    "rumors": copy.deepcopy(list(rumor_registry.db.rumors or [])),
    "transmissions": copy.deepcopy(list(rumor_registry.db.transmissions or [])),
    "next_rumor_id": rumor_registry.db.next_rumor_id,
    "next_transmission_id": rumor_registry.db.next_transmission_id,
}
private_tavern_public = copy.deepcopy(
    list(tavern_for_snapshot.db.public_rumor_ids or [])
)
private_tavern_player = copy.deepcopy(
    list(tavern_for_snapshot.db.player_rumors or [])
)
private_ledger_count = len(ledger.db.events or [])
private_harbinger_count = len(public_records.db.harbinger_drafts or [])
private_chronicle_count = len(public_records.db.chronicle_entries or [])

qa_private_a = evennia_create.create_object(
    "typeclasses.characters.Character",
    key="qa_private_a",
    location=tavern_for_snapshot,
)
qa_private_b = evennia_create.create_object(
    "typeclasses.characters.Character",
    key="qa_private_b",
    location=tavern_for_snapshot,
)
janos = one("János")

try:
    assert records_for(qa_private_a) == []
    assert records_for(qa_private_b) == []

    refused = private_mystery_answer(
        janos,
        qa_private_b,
        "east patrol",
    )
    assert "not a conversation" in refused.lower()
    assert records_for(qa_private_b) == []

    invitation = deliver_hounds_invitation(janos, qa_private_a)
    assert invitation["status"] == "invited"
    invitation_id = invitation["invitation_rumor_id"]
    assert records_for(qa_private_a)[0]["id"] == HOUNDS_INVITATION_ID
    assert records_for(qa_private_b) == []

    invitation_root = rumor_registry.get_rumor(invitation_id)
    assert invitation_root["privacy"] == "private"
    assert rumor_registry.belief_for(qa_private_a, invitation_id)
    assert rumor_registry.belief_for(qa_private_b, invitation_id) is None
    assert invitation_id not in (
        tavern_for_snapshot.db.public_rumor_ids or []
    )

    rumor_count = len(rumor_registry.db.rumors or [])
    duplicate = deliver_hounds_invitation(janos, qa_private_a)
    assert duplicate["invitation_rumor_id"] == invitation_id
    assert len(rumor_registry.db.rumors or []) == rumor_count

    followup = open_hounds_followup(janos, qa_private_a)
    assert followup["status"] == "opened"
    followup_id = followup["followup_rumor_id"]
    followup_root = rumor_registry.get_rumor(followup_id)
    assert followup_root["privacy"] == "private"
    assert "chalk ring" in followup_root["claim"].lower()
    assert open_hounds_followup(janos, qa_private_b) is None
    assert followup_id not in (
        tavern_for_snapshot.db.public_rumor_ids or []
    )

    # Private existence alone never creates public history.
    assert len(ledger.db.events or []) == private_ledger_count
    assert len(public_records.db.harbinger_drafts or []) == private_harbinger_count
    assert len(public_records.db.chronicle_entries or []) == private_chronicle_count

    # Explicit retelling shares the rumor but does not clone the private thread.
    shared = rumor_registry.transmit(
        followup_id,
        qa_private_a,
        qa_private_b,
        location=tavern_for_snapshot.key,
        force_accept=True,
        allow_private=True,
    )
    assert shared and shared["accepted"]
    assert rumor_registry.belief_for(qa_private_b, followup_id)
    note_disclosure(qa_private_a, qa_private_b, followup_id)
    assert records_for(qa_private_b) == []

    owner_record = records_for(qa_private_a)[0]
    assert owner_record["disclosures"]
    assert owner_record["disclosures"][-1]["target"]["mask"] == "qa_private_b"
    owner_text = "\n".join(private_lines(qa_private_a))
    assert "qa_private_b" in owner_text
    assert "server-wide requirement" in owner_text
finally:
    qa_private_a.delete()
    qa_private_b.delete()
    private_registry.db.records = copy.deepcopy(private_snapshot["records"])
    private_registry.db.metrics = copy.deepcopy(private_snapshot["metrics"])
    rumor_registry.db.rumors = copy.deepcopy(private_rumor_snapshot["rumors"])
    rumor_registry.db.transmissions = copy.deepcopy(
        private_rumor_snapshot["transmissions"]
    )
    rumor_registry.db.next_rumor_id = private_rumor_snapshot["next_rumor_id"]
    rumor_registry.db.next_transmission_id = private_rumor_snapshot[
        "next_transmission_id"
    ]
    tavern_for_snapshot.db.public_rumor_ids = copy.deepcopy(
        private_tavern_public
    )
    tavern_for_snapshot.db.player_rumors = copy.deepcopy(
        private_tavern_player
    )

# The butcher resolves directly to the correct current state. Skipped hours
# are not replayed, and a dead resident stops following schedules.
otto = by_resident_id["otto_kessler"]
ostate = resident_state(otto)
ostate["wake_reasons"] = []
ostate["engagement"] = 0.0
ostate["engagement_tier"] = "D"
ostate["simulation_resolution"] = "automaton"
ostate["lifecycle"] = {"status": "active", "reason": None, "changed_day": None}
save_state(otto, ostate)
advance_population(day=2, hour=10, emit=False)
assert resident_state(otto)["routine"]["logical_location"] == "butcher_shop"
before_resolutions = resident_state(otto)["metrics"]["routine_resolutions"]
advance_population(day=2, hour=22, emit=False)
ostate = resident_state(otto)
assert ostate["routine"]["logical_location"].startswith("home:")
assert ostate["metrics"]["routine_resolutions"] == before_resolutions + 1
night_routine = copy.deepcopy(ostate["routine"])
set_lifecycle(otto, "dead", reason="qa lifecycle")
advance_population(day=3, hour=10, emit=False)
assert resident_state(otto)["routine"] == night_routine, (
    "dead resident continued following a schedule"
)

# Social graph edges are consequential. An event targeting the butcher reaches
# his assistant through the explicit employer relation without becoming global.
rada = by_resident_id["rada_petrescu"]
employment_event = publish_world_event(
    "qa_employer_incident",
    payload={"target_resident_id": "otto_kessler", "cause": "shop_accident"},
)
assert str(employment_event["id"]) in resident_state(rada)["event_flags"]
assert str(employment_event["id"]) not in resident_state(
    by_resident_id["wren_vessey"]
)["event_flags"]

# Sunday Mass gathers a deterministic subset of background households and
# releases them back into their routines afterward. A structured incident can
# mark only the explicit witnesses without simulating everyone present.
mass_ids = gather_population_for_mass(8)
assert len(mass_ids) >= 5
assert "wren_vessey" in mass_ids
assert resident_state(wren)["routine"]["logical_location"] == "church"
mass_witnesses = mass_ids[:3]
mass_event = publish_world_event(
    "qa_mass_incident",
    payload={"resident_ids": mass_witnesses},
)
for stable_id in mass_witnesses:
    assert str(mass_event["id"]) in resident_state(
        by_resident_id[stable_id]
    )["event_flags"]
non_witness = next(
    stable_id for stable_id in mass_ids if stable_id not in mass_witnesses
)
assert str(mass_event["id"]) not in resident_state(
    by_resident_id[non_witness]
)["event_flags"]
advance_population(day=8, hour=12, emit=False)
for stable_id in mass_ids:
    assert resident_state(
        by_resident_id[stable_id]
    )["routine"]["logical_location"] != "church", (
        stable_id,
        "resident trapped at church after Mass",
    )

# Attention can deepen an ordinary background resident without making
# narrative importance or active compute the same thing. A second player gets
# a separate relationship view of the same global person and facts.
marta = by_resident_id["marta_kovacs"]
mstate = resident_state(marta)
mstate["relationships"] = {}
mstate["facts"] = []
mstate["engagement"] = 0.0
mstate["engagement_floor"] = 0.0
mstate["engagement_tier"] = "D"
mstate["simulation_resolution"] = "automaton"
mstate["character_depth"] = "D"
mstate["narrative_importance"] = 0
mstate["last_decay_day"] = 1
save_state(marta, mstate)
alice = SimpleNamespace(id=900001, key="qa_alice", has_account=True)
bob = SimpleNamespace(id=900002, key="qa_bob", has_account=True)
for _ in range(41):
    record_player_interaction(marta, alice, kind="talk")
mstate = resident_state(marta)
assert mstate["engagement_tier"] == "A"
assert mstate["character_depth"] == "A"
assert mstate["simulation_resolution"] == "focused"
assert mstate["narrative_importance"] == 0, (
    "player attention incorrectly became narrative importance"
)
assert resident_state(otto)["relationships"] == state_snapshot[
    "otto_kessler"
]["relationships"], "resident relationship state leaked between NPCs"

secret_line = generic_ask_line(marta, alice, "your secret")
assert secret_line and "Keep this where I put it" in secret_line
alice_facts = facts_known_by_player(marta, alice)
bob_facts = facts_known_by_player(marta, bob)
assert len(alice_facts) == 1
assert bob_facts == [], "second player inherited another player's revelation"
shared_fact_id = alice_facts[0]["fact_id"]
assert any(
    fact["fact_id"] == shared_fact_id
    for fact in resident_state(marta)["facts"]
), "revealed fact was not resident-global canon"

decay_resident_engagement(marta, 120)
mstate = resident_state(marta)
assert mstate["engagement_tier"] == "D"
assert mstate["simulation_resolution"] == "automaton"
assert mstate["character_depth"] == "A", (
    "demotion erased accumulated character depth"
)
assert any(
    fact["fact_id"] == shared_fact_id for fact in mstate["facts"]
), "demotion erased persistent facts"
assert str(alice.id) in mstate["relationships"], (
    "demotion erased player relationship history"
)

# Generate facts across many residents. Ordinary irregularities must dominate,
# forced Gothic assignments must remain unique, and assignment alone must not
# magically publish a rumor.
sample_ids = [
    "marta_kovacs", "otto_kessler", "rada_petrescu", "petru_ionescu",
    "ana_ionescu", "miklos_farkas", "elias_dorn", "ilona_szabo",
    "klara_weiss", "pavel_orban", "milena_varga", "sorin_dragomir",
]
classes = Counter()
for stable_id in sample_ids:
    fact = assign_fact(by_resident_id[stable_id])
    assert fact
    classes[fact["class"]] += 1
assert classes["ordinary"] > classes["serious"] + classes["gothic"], classes

gothic_ids = []
for stable_id in (
    "petru_ionescu", "ana_ionescu", "miklos_farkas",
    "elias_dorn", "ilona_szabo", "klara_weiss",
):
    fact = assign_fact(by_resident_id[stable_id], class_hint="gothic")
    assert fact
    if fact["class"] == "gothic":
        gothic_ids.append(fact["fact_id"])
assert gothic_ids, "forced Gothic pool produced no Gothic assignment"
assert len(gothic_ids) == len(set(gothic_ids)), (
    "unique Gothic secret was assigned to multiple residents"
)
for fact_id in gothic_ids:
    assert FACT_BY_ID[fact_id]["claim"] == "unique"
    assert len((population_registry.db.fact_claims or {}).get(fact_id) or []) == 1

rumor_roots_before = {
    rumor["id"]
    for rumor in (rumor_registry.db.rumors or [])
    if str(rumor.get("subject") or "").startswith("resident_fact:")
}
assert not rumor_roots_before
exposed = expose_fact_as_rumor(
    marta,
    shared_fact_id,
    source_actor="qa witness",
)
assert exposed and exposed["published"]
exposed_id = exposed["rumor_id"]
exposed_root = rumor_registry.get_rumor(exposed_id)
assert exposed_root["subject"] == f"resident_fact:{shared_fact_id}"

# Remove QA-only world events and the explicitly exposed QA rumor, then restore
# resident state so the player-facing telnet pass starts from a normal village.
qa_event_ids = {
    school_destroyed["id"],
    school_restored["id"],
    reported["id"],
    private_event["id"],
    employment_event["id"],
    mass_event["id"],
}
ledger.db.events = [
    event for event in (ledger.db.events or [])
    if event.get("id") not in qa_event_ids
]
rumor_registry.db.rumors = [
    rumor for rumor in (rumor_registry.db.rumors or [])
    if rumor.get("id") != exposed_id
]
rumor_registry.db.transmissions = [
    transmission for transmission in (rumor_registry.db.transmissions or [])
    if transmission.get("rumor_id") != exposed_id
]
tavern = one("The Blood of the Vine")
tavern.db.public_rumor_ids = [
    rid for rid in (tavern.db.public_rumor_ids or [])
    if rid != exposed_id
]
if exposed_root:
    tavern.db.player_rumors = [
        body for body in (tavern.db.player_rumors or [])
        if body != exposed_root["claim"]
    ]
for npc in population:
    beliefs = dict(npc.db.rumor_beliefs or {})
    beliefs.pop(str(exposed_id), None)
    npc.db.rumor_beliefs = beliefs

# Restore all publication and rumor state changed by synthetic population QA.
# This prevents special editions, confession chatter, corrections, and article
# readership from leaking into the real telnet transcript that follows.
for key, value in public_records_snapshot.items():
    setattr(public_records.db, key, copy.deepcopy(value))
rumor_registry.db.rumors = copy.deepcopy(rumor_snapshot["rumors"])
rumor_registry.db.transmissions = copy.deepcopy(rumor_snapshot["transmissions"])
rumor_registry.db.next_rumor_id = rumor_snapshot["next_rumor_id"]
rumor_registry.db.next_transmission_id = rumor_snapshot["next_transmission_id"]
for npc in population:
    npc.db.rumor_beliefs = copy.deepcopy(
        rumor_belief_snapshot.get(npc.id, {})
    )
tavern_for_snapshot.db.public_rumor_ids = copy.deepcopy(
    tavern_public_ids_snapshot
)
tavern_for_snapshot.db.player_rumors = copy.deepcopy(
    tavern_player_rumors_snapshot
)

for stable_id, old_state in state_snapshot.items():
    by_resident_id[stable_id].db.resident_state = old_state
population_registry.db.fact_claims = claims_snapshot
set_location_availability("schoolhouse", True)

# Resynchronize physical projection to the actual clock after synthetic time
# travel in the assertions above.
clock = ScriptDB.objects.get(db_key="village_time")
advance_population(
    day=clock.db.day or 1,
    hour=clock.db.hour if clock.db.hour is not None else 21,
    emit=False,
)

# Rumors are structured belief objects with immutable roots and append-only
# transmission provenance. The three live canon hooks seed real NPC beliefs.
rumor_registry = ScriptDB.objects.get(db_key="rumor_registry")
canon_roots = [
    dict(rumor)
    for rumor in (rumor_registry.db.rumors or [])
    if rumor.get("canonical_seed_id") is not None
]
assert {r["canonical_seed_id"] for r in canon_roots} == {151, 201, 236}
assert len(canon_roots) == 3, "rebuild duplicated canonical rumor roots"
for root in canon_roots:
    assert root.get("source_actor"), root
    assert root.get("source_type") == "canon_teller", root
    assert root.get("privacy") == "public", root
    assert len(root.get("variants") or []) == 3, root

magda = one("Magda")
vasile = one("Old Vasile")
janos = one("János")
m = one("M.")
assert magda.tags.has("participant", category="rumor")
assert vasile.tags.has("participant", category="rumor")
assert janos.tags.has("participant", category="rumor")
assert not m.tags.has("participant", category="rumor"), (
    "OOC innkeeper must not participate in IC rumor simulation"
)

root = next(r for r in canon_roots if r["canonical_seed_id"] == 201)
root_before = dict(root)
magda_belief = rumor_registry.belief_for(magda, root["id"])
assert magda_belief, "seeded NPC lacks canon rumor belief"

# Tavern life may already have changed Magda's current version before this
# assertion shell starts. Reset only her current belief to a new direct hearing
# so the controlled provenance chain below has a deterministic three links.
rumor_registry.hear_direct(
    root["id"],
    magda,
    source_label=root["source_actor"],
    source_type=root["source_type"],
    location="The Blood of the Vine",
    force_new=True,
)

first = rumor_registry.transmit(
    root["id"],
    magda,
    vasile,
    location="The Blood of the Vine",
    force_accept=True,
    force_variant_index=0,
)
assert first and first["accepted"]
second = rumor_registry.transmit(
    root["id"],
    vasile,
    janos,
    location="The Blood of the Vine",
    force_accept=True,
    force_variant_index=1,
)
assert second and second["accepted"]
assert rumor_registry.get_rumor(root["id"]) == root_before, (
    "retelling mutated the immutable rumor root"
)
chain = rumor_registry.provenance(second["id"])
assert len(chain) == 3, chain
assert chain[0]["parent_id"] is None
assert chain[1]["parent_id"] == chain[0]["id"]
assert chain[2]["parent_id"] == chain[1]["id"]
assert chain[2]["distortion_generation"] == 2
assert chain[2]["claim"] == root["variants"][1]
known = rumor_registry.known_by(root["id"])
known_ids = {entry.get("id") for entry in known}
assert {magda.id, vasile.id, janos.id}.issubset(known_ids)
assert len(rumor_registry.current_claims(root["id"])) >= 2

# Chronicler content: incompatible signed accounts remain distinct public
# records. The archive acknowledges disagreement without selecting a winner.
vasile_entry, error = submit_deposition(vasile, root["id"])
assert error is None and vasile_entry["entry_type"] == "deposition"
assert chronicle_disagreement_for_rumor(root["id"]) is None

janos_entry, error = submit_deposition(janos, root["id"])
assert error is None and janos_entry["entry_type"] == "deposition"
disagreement = chronicle_disagreement_for_rumor(root["id"])
assert disagreement
assert disagreement["entry_type"] == "disagreement_record"
assert disagreement["claim_status"] == "documented_disagreement"
assert set(disagreement["source_deposition_ids"]) == {
    vasile_entry["deposition_id"],
    janos_entry["deposition_id"],
}
assert len(disagreement["version_claims"]) == 2
assert {
    item["claim"] for item in disagreement["version_claims"]
} == {
    rumor_registry.belief_for(vasile, root["id"])["claim"],
    rumor_registry.belief_for(janos, root["id"])["claim"],
}
assert "does not choose" in disagreement["text"].lower()
assert "verified fact" in disagreement["text"].lower()

# A third distinct account is appended as an annotation. The original
# disagreement text remains immutable, and repeating a represented version
# does not create a second disagreement record.
initial_disagreement_text = disagreement["text"]
magda_entry, error = submit_deposition(magda, root["id"])
assert error is None and magda_entry["entry_type"] == "deposition"
expanded = chronicle_disagreement_for_rumor(root["id"])
assert expanded["text"] == initial_disagreement_text
assert len(expanded["version_claims"]) == 3
assert len(expanded["annotations"]) == 1
assert expanded["annotations"][0]["source_deposition_ids"] == [
    magda_entry["deposition_id"]
]
assert "not truth" in expanded["annotations"][0]["text"].lower()
assert len([
    entry
    for entry in (public_records.db.chronicle_entries or [])
    if entry.get("entry_type") == "disagreement_record"
    and root["id"] in list(entry.get("source_rumor_ids") or [])
]) == 1
assert len(depositions_for_rumor(root["id"])) == 3

# Harbinger Section 3.22, Stop the Press: incompatible signed accounts can
# become a copy-desk decision without making the newspaper omniscient. The
# no-player path is equally important: if press time arrives first, the paper
# prints the disagreement rather than silently picking a winner.
_stop_press_conflicts = copy.deepcopy(
    list(public_records.db.harbinger_conflicts or [])
)
_stop_press_next = public_records.db.next_harbinger_conflict_id
_stop_press_drafts = copy.deepcopy(list(public_records.db.harbinger_drafts or []))
_stop_press_next_story = public_records.db.next_story_id

stop_press, error = ensure_harbinger_conflict(root["id"])
assert error is None and stop_press["status"] == "open"
assert len(stop_press["accounts"]) == 3
assert {
    account["deposition_id"] for account in stop_press["accounts"]
} == {
    vasile_entry["deposition_id"],
    janos_entry["deposition_id"],
    magda_entry["deposition_id"],
}
resolved_press = resolve_due_harbinger_conflicts(
    stop_press["deadline_day"],
    stop_press["deadline_hour"],
)
assert len(resolved_press) == 1
assert resolved_press[0]["conflict_id"] == stop_press["id"]
assert resolved_press[0]["story_id"]
closed_press = get_harbinger_conflict(stop_press["id"])
assert closed_press["status"] == "deadline_neutral"
assert closed_press["resolution"] == "printed_disagreement"
neutral_story = get_story(closed_press["story_id"])
assert neutral_story["basis"] == "disputed_report"
assert neutral_story["source_rumor_id"] == root["id"]
assert neutral_story["source_deposition_id"] is None
assert "without selecting any version as settled fact" in neutral_story["body"]

# Restore only the synthetic editorial layer. The signed accounts themselves
# are intentional shared state used by the later real telnet playthrough.
public_records.db.harbinger_conflicts = _stop_press_conflicts
public_records.db.next_harbinger_conflict_id = _stop_press_next
public_records.db.harbinger_drafts = _stop_press_drafts
public_records.db.next_story_id = _stop_press_next_story

# Migration path: an upgraded persistent world may already contain these
# depositions but no disagreement entry. Removing only the derived record
# simulates that pre-feature state. Reconciliation must restore the public
# archive immediately and remain idempotent.
public_records.db.chronicle_entries = [
    entry
    for entry in (public_records.db.chronicle_entries or [])
    if not (
        entry.get("entry_type") == "disagreement_record"
        and root["id"] in list(entry.get("source_rumor_ids") or [])
    )
]
assert chronicle_disagreement_for_rumor(root["id"]) is None
migration = reconcile_chronicle_disagreements()
backfilled = chronicle_disagreement_for_rumor(root["id"])
assert backfilled
assert backfilled["id"] in migration["disagreement_ids"]
assert len(backfilled["version_claims"]) == 3
assert len(backfilled["annotations"]) == 1
backfill_id = backfilled["id"]
again = reconcile_chronicle_disagreements()
assert chronicle_disagreement_for_rumor(root["id"])["id"] == backfill_id
assert again["disagreement_ids"].count(backfill_id) == 1
assert len([
    entry
    for entry in (public_records.db.chronicle_entries or [])
    if entry.get("entry_type") == "disagreement_record"
    and root["id"] in list(entry.get("source_rumor_ids") or [])
]) == 1

# Player-facing lazy recovery is deliberately scoped to one requested rumor.
# Remove the derived record a second time and prove the single-root path can
# restore it without invoking the global migration.
public_records.db.chronicle_entries = [
    entry
    for entry in (public_records.db.chronicle_entries or [])
    if not (
        entry.get("entry_type") == "disagreement_record"
        and root["id"] in list(entry.get("source_rumor_ids") or [])
    )
]
assert chronicle_disagreement_for_rumor(root["id"]) is None
lazy_backfill = reconcile_chronicle_disagreement(root["id"])
assert lazy_backfill
assert lazy_backfill["claim_status"] == "documented_disagreement"
assert len(lazy_backfill["version_claims"]) == 3
assert len(lazy_backfill["annotations"]) == 1
assert chronicle_disagreement_for_rumor(root["id"])["id"] == lazy_backfill["id"]

from world.rumors import propagate_colocated_npcs
autonomous = propagate_colocated_npcs(announce=False, max_per_room=1)
assert autonomous, "routine-scale NPC rumor propagation produced no retelling"

# Event-generated rumors enter the same registry and retain their event link.
from world.events import publish_world_event
qa_public_snapshot = {
    "harbinger_drafts": copy.deepcopy(list(public_records.db.harbinger_drafts or [])),
    "harbinger_editions": copy.deepcopy(list(public_records.db.harbinger_editions or [])),
    "chronicle_entries": copy.deepcopy(list(public_records.db.chronicle_entries or [])),
    "depositions": copy.deepcopy(list(public_records.db.depositions or [])),
    "next_story_id": public_records.db.next_story_id,
    "next_edition_id": public_records.db.next_edition_id,
    "next_chronicle_id": public_records.db.next_chronicle_id,
    "next_deposition_id": public_records.db.next_deposition_id,
    "last_harbinger_day": public_records.db.last_harbinger_day,
}
qa_event = publish_world_event(
    "qa_rumor",
    actor=magda,
    payload={"proof": True},
    rumor="The QA bell rang twice.",
)
assert qa_event["status"] == "complete"
qa_rumor_id = qa_event["rumor"]["rumor_id"]
qa_root = rumor_registry.get_rumor(qa_rumor_id)
assert qa_root["original_event_id"] == qa_event["id"]
assert qa_root["source_actor"] == "Magda"
assert qa_root["source_type"] == "npc"
assert qa_root["claim"] == "The QA bell rang twice."

# Remove the synthetic event from the same temporary world used by the telnet
# pass. The assertion proves integration without making QA chatter player-facing.
ledger = ScriptDB.objects.get(db_key="world_event_ledger")
ledger.db.events = [
    event for event in (ledger.db.events or [])
    if event.get("id") != qa_event["id"]
]
rumor_registry.db.rumors = [
    rumor for rumor in (rumor_registry.db.rumors or [])
    if rumor.get("id") != qa_rumor_id
]
rumor_registry.db.transmissions = [
    transmission for transmission in (rumor_registry.db.transmissions or [])
    if transmission.get("rumor_id") != qa_rumor_id
]
tavern = one("The Blood of the Vine")
tavern.db.public_rumor_ids = [
    rid for rid in (tavern.db.public_rumor_ids or [])
    if rid != qa_rumor_id
]
tavern.db.player_rumors = [
    body for body in (tavern.db.player_rumors or [])
    if body != "The QA bell rang twice."
]
for npc in search.search_tag("participant", category="rumor"):
    beliefs = dict(npc.db.rumor_beliefs or {})
    beliefs.pop(str(qa_rumor_id), None)
    npc.db.rumor_beliefs = beliefs
for key, value in qa_public_snapshot.items():
    setattr(public_records.db, key, copy.deepcopy(value))

# Moderation lifecycle is tested on an isolated temporary script so running
# these assertions against a real development world cannot pollute its queue.
moderation = create_script(
    "typeclasses.scripts.ModerationQueue",
    key="qa_moderation_queue",
    persistent=False,
)
target = AccountDB.objects.order_by("id").first()
assert target is not None, "bootstrap did not create an account"
old_warnings = list(target.db.compact_warning_actions or [])
old_bans = list(target.db.compact_ban_actions or [])
old_notices = list(target.db.moderation_notices or [])
try:
    target.db.compact_warning_actions = []
    target.db.compact_ban_actions = []
    target.db.moderation_notices = []

    first = moderation.submit({
        "reporter_mask": "qa-reporter",
        "target": target.key,
        "target_account_id": target.id,
        "reason": "first reviewed allegation",
    })
    assert _world_entry_allowed(target), "a raw report must never suspend entry"

    denied, error = moderation.ban_report(first["id"], target, note="too soon")
    assert denied is None and "warning" in error.lower(), (
        "ban was allowed before a human-issued warning"
    )
    assert _world_entry_allowed(target), "failed ban attempt changed entry state"

    warning, error = moderation.warn_report(
        first["id"], target, note="human warning test"
    )
    assert warning and error is None and warning["kind"] == "warning"
    assert warning["id"] in (target.db.compact_warning_actions or [])
    assert _world_entry_allowed(target), "warning incorrectly suspended world entry"

    second = moderation.submit({
        "reporter_mask": "qa-reporter",
        "target": target.key,
        "target_account_id": target.id,
        "reason": "second reviewed allegation",
    })
    ban, error = moderation.ban_report(
        second["id"], target, note="human suspension test"
    )
    assert ban and error is None and ban["kind"] == "ban"
    assert ban["id"] in (target.db.compact_ban_actions or [])
    assert not _world_entry_allowed(target), "reviewed ban did not suspend world entry"

    appeal, error = moderation.submit_appeal(
        target, ban["id"], "please review the suspension"
    )
    assert appeal and error is None and appeal["status"] == "open"
    resolved, error = moderation.resolve_appeal(
        appeal["id"], target, "overturn", note="qa reversal"
    )
    assert resolved and error is None and resolved["outcome"] == "overturn"
    assert ban["id"] not in (target.db.compact_ban_actions or [])
    assert _world_entry_allowed(target), "successful appeal did not restore entry"

    warning_appeal, error = moderation.submit_appeal(
        target, warning["id"], "please review the warning"
    )
    assert warning_appeal and error is None
    resolved, error = moderation.resolve_appeal(
        warning_appeal["id"], target, "overturn", note="qa reversal"
    )
    assert resolved and error is None
    assert warning["id"] not in (target.db.compact_warning_actions or [])

    kinds = [action["kind"] for action in moderation.audit_actions(limit=20)]
    assert "warning" in kinds and "ban" in kinds
    assert kinds.count("appeal_overturn") == 2
finally:
    target.db.compact_warning_actions = old_warnings
    target.db.compact_ban_actions = old_bans
    target.db.moderation_notices = old_notices
    moderation.delete()

# Leave one fresh real window active for the network playtest. The start event
# is intentionally private; the telnet player must earn firsthand evidence by
# entering the square and observing the well while the window is still open.
import time as _time
_telnet_clock = ScriptDB.objects.get(db_key="village_time")
_telnet_window = start_timed_incident(
    WELL_BOILS_ID,
    day=_telnet_clock.db.day or 1,
    hour=(
        _telnet_clock.db.hour
        if _telnet_clock.db.hour is not None
        else 21
    ),
    now=_time.time(),
    force=True,
)
assert _telnet_window and _telnet_window["state"] == "active"
assert not _telnet_window["current"]["player_observations"]

# Leave one ordinary random incident active too. This proves that stochastic
# texture reaches the same room-description overlay path as scheduled events,
# without becoming a quest or public record automatically.
_existing_random = current_random_incident()
if _existing_random:
    advance_random_incidents(
        day=_existing_random["end_day"],
        hour=_existing_random["end_hour"],
        force_id="NO-SUCH-RANDOM-INCIDENT",
    )
# Fixture-only normalization: preserve production cooldown behavior, but clear
# this template's prior run so the network test can deterministically exercise
# the accepted Extinguished Lamp example.
_telnet_last_runs = copy.deepcopy(dict(random_registry.db.last_runs or {}))
_telnet_last_runs.pop(EXTINGUISHED_LAMP_ID, None)
random_registry.db.last_runs = _telnet_last_runs
_telnet_random = advance_random_incidents(
    day=_telnet_clock.db.day or 1,
    hour=21,
    force_id=EXTINGUISHED_LAMP_ID,
)
assert _telnet_random["started"] == EXTINGUISHED_LAMP_ID, _telnet_random

# Keep this QA occurrence alive across server bootstrap hooks. Production
# lifetimes remain template-owned; this only makes the real network rendering
# check independent of how many immediate clock callbacks Evennia performs
# while starting a fresh server process.
_telnet_random_record = copy.deepcopy(dict(random_registry.db.current or {}))
_telnet_random_record["end_day"] = int(_telnet_clock.db.day or 1) + 1
_telnet_random_record["end_hour"] = 21
random_registry.db.current = _telnet_random_record
assert reconcile_random_incident_overlay()
assert EXTINGUISHED_LAMP_ID in (
    one("Village Square").db.scheduled_overlays or {}
)

# Leave one server-wide condition active for the real network playtest.
_telnet_server = start_server_event(
    LONG_BLACKOUT_ID,
    day=_telnet_clock.db.day or 1,
    hour=(
        _telnet_clock.db.hour
        if _telnet_clock.db.hour is not None
        else 21
    ),
    force=True,
)
assert _telnet_server and _telnet_server["state"] == "active"
_telnet_server_record = copy.deepcopy(
    dict(server_registry.db.events[LONG_BLACKOUT_ID])
)
_telnet_server_current = copy.deepcopy(
    dict(_telnet_server_record["current"])
)
_telnet_server_current["end_day"] = int(_telnet_clock.db.day or 1) + 1
_telnet_server_current["end_hour"] = int(
    _telnet_clock.db.hour
    if _telnet_clock.db.hour is not None
    else 21
)
_telnet_server_record["current"] = _telnet_server_current
_telnet_server_record["state"] = "active"
_telnet_events = copy.deepcopy(dict(server_registry.db.events or {}))
_telnet_events[LONG_BLACKOUT_ID] = _telnet_server_record
server_registry.db.events = _telnet_events
assert reconcile_server_event_overlays()
assert f"{LONG_BLACKOUT_ID}:active" in (
    one("Village Square").db.scheduled_overlays or {}
)

print("WORLD_ASSERTIONS_GREEN")
