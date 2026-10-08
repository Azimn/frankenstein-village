"""Assertions run after the player telnet pass and a real server restart."""

import hashlib

from evennia.scripts.models import ScriptDB
from evennia.utils import search

from world.callings import (
    RANK_APPRENTICE,
    active_calling,
    active_rank,
    calling_record,
    calling_state,
)
from world.object_properties import (
    hidden_mechanical_properties,
    hidden_property_knowledge,
    mechanical_properties,
    perception_notes,
)
from world.residents import facts_known_by_player, resident_state
from world.situations import (
    TITHE_ID,
    TORN_CHRONICLE_ID,
    WELL_MUSHROOM_WARNING_ID,
    TAVERN_COLD_CARE_ID,
    LAMP_REPAIR_ID,
    get_situation,
    situation_status_for_player,
)
from world.publications import (
    chronicle_disagreement_for_rumor,
    chronicle_entries,
    depositions_for_rumor,
    edition_stories,
    get_story,
    latest_edition,
)
from world.harbinger_content import (
    correction_disputes_for_story,
    harbinger_conflicts,
    harbinger_obituary_cases,
)
from world.timed_incidents import (
    WELL_BOILS_ID,
    advance_timed_incidents,
    get_timed_incident,
    status_for_player as timed_status_for_player,
)
from world.random_incidents import (
    EXTINGUISHED_LAMP_ID,
    current_random_incident,
    recent_random_incidents,
)
from world.seasonal_frameworks import (
    LONG_SHADOWS_ID,
    OVERLAY_KEY as SEASONAL_OVERLAY_KEY,
    current_chapter,
    get_seasonal_framework_registry,
)
from world.scheduled_events import (
    HARBINGER_PUBLICATION_ID,
    MARKET_MORNING_ID,
    SUNDAY_SERVICE_ID,
    get_scheduled_event_registry,
)
from world.server_events import (
    LONG_BLACKOUT_ID,
    get_server_event,
    get_server_event_registry,
)
from world.public_mysteries import (
    MANOR_LIGHTS_ID,
    get_public_mystery,
    get_public_mystery_registry,
)
from world.private_mysteries import (
    HOUNDS_INVITATION_ID,
    get_private_mystery_registry,
    records_for as private_records_for,
)
from world.rumors import get_rumor_registry


def one(key):
    found = [obj for obj in search.search_object(key) if obj.key == key]
    assert len(found) == 1, (key, len(found))
    return found[0]


miklos = one("Miklós Farkas")
smoke = one("SmokeTester")
healer_tester = one("HealerTester")
innkeep_tester = one("InnkeepTester")
smith_tester = one("SmithTester")
merchant_tester = one("MerchantTester")
state = resident_state(miklos)
relation = (state.get("relationships") or {}).get(str(smoke.id))
assert relation, "telnet interactions did not persist a Miklós relationship"
assert relation["familiarity"] >= 8
assert state["character_depth"] in {"C", "B", "A"}
assert state["simulation_resolution"] in {"reactive", "engaged", "focused"}
assert state["facts"], "history question did not persist progressive characterization"
known = facts_known_by_player(miklos, smoke)
assert known, "revealed fact was not recorded for the player mask"

# Calling identity and work history belong to the mask and survive a real
# server restart. Respecialization did not erase the earlier Chronicler record.
assert active_calling(smoke) == "chronicler"
assert active_rank(smoke) == RANK_APPRENTICE
smoke_chronicler = calling_record(smoke, "chronicler")
assert smoke_chronicler["participation"]["evidence_revisions"] == 1
assert smoke_chronicler["participation"]["signed_accounts"] == 1
assert smoke_chronicler["participation"]["public_health_records"] == 1
assert calling_record(smoke, "performer") is None
smoke_calling_history = calling_state(smoke)["history"]
assert any(
    item.get("action") == "joined_calling"
    and item.get("calling") == "chronicler"
    for item in smoke_calling_history
)
assert not any(
    item.get("action") == "respecialized"
    for item in smoke_calling_history
), "player command bypassed authored respecialization before restart"

# The specialized Healer capability survives the same process boundary.
assert active_calling(healer_tester) == "healer"
assert active_rank(healer_tester) == RANK_APPRENTICE
healer_record = calling_record(healer_tester, "healer")
assert healer_record["participation"]["assessments"] == 1
assert healer_record["participation"]["public_health_findings"] == 1
assert healer_record["participation"]["resident_assessments"] == 1
assert not getattr(healer_tester.db, "queasy", 0), (
    "safe Healer assessment unexpectedly applied the toxin effect"
)

assert active_calling(innkeep_tester) == "innkeep"
assert active_rank(innkeep_tester) == RANK_APPRENTICE
innkeep_record = calling_record(innkeep_tester, "innkeep")
assert innkeep_record["participation"]["recovery_hospitality"] == 1

population = list(search.search_tag("resident", category="system"))
assert len(population) == 36, "resident population changed across restart"

# Systemic object definitions survive the process boundary. During the live
# server pass Bram's routine legitimately restocks the bread after the player
# buys a serving, so the post-restart count should be the configured uses
# capacity rather than the pre-restock count.
bread = one("a loaf of bread")
water = one("a cup of water")
mushrooms = one("a cluster of mushrooms")
assert mechanical_properties(bread) == {"uses": 6, "worth": 4}
assert mechanical_properties(water) == {"worth": 0}
assert mechanical_properties(mushrooms) == {}
assert hidden_mechanical_properties(mushrooms) == {"toxin": 25}
assert bread.db.servings == mechanical_properties(bread)["uses"]
assert "toxic" not in dict(mushrooms.db.consume or {})
mushroom_knowledge = hidden_property_knowledge(smoke, mushrooms)
assert mushroom_knowledge["toxin"]["value"] == 25
assert mushroom_knowledge["toxin"]["source"] == "direct_effect"
assert mushroom_knowledge["toxin"]["object_key"] == "a cluster of mushrooms"
assert any(
    "can be toxic" in note.lower()
    and "direct effect" in note.lower()
    for note in perception_notes(smoke, mushrooms)
)

healer_mushroom_knowledge = hidden_property_knowledge(
    healer_tester,
    mushrooms,
)
assert healer_mushroom_knowledge["toxin"]["value"] == 25
assert healer_mushroom_knowledge["toxin"]["source"] == "healer_assessment"
assert healer_mushroom_knowledge["toxin"]["object_key"] == (
    "a cluster of mushrooms"
)
assert any(
    "can be toxic" in note.lower()
    and "healer assessment" in note.lower()
    for note in perception_notes(healer_tester, mushrooms)
)

edition = latest_edition()
assert edition and edition["special"], "Room Six special edition did not survive restart"
stories = edition_stories(edition)
assert any("Folded Note" in story["headline"] for story in stories)

entries = chronicle_entries()
assert any(
    entry["entry_type"] == "objective_record"
    and "Folded Note" in entry["title"]
    for entry in entries
), "objective Room Six Chronicle entry did not survive restart"
assert any(
    entry["entry_type"] == "deposition"
    and entry.get("source_mask_id") == smoke.id
    and entry.get("claim_status") == "reported_account"
    for entry in entries
), "player Chronicle deposition did not survive restart"

# Cross-calling public-health work survives restart as one shared situation.
# The Healer finding and Chronicler publication remain separately attributed,
# while public prose does not expose the internal toxin magnitude.
warning_case = get_situation(WELL_MUSHROOM_WARNING_ID)
assert warning_case["state"] == "aftermath"
assert warning_case["branch"] == "public_warning"
warning_mutations = dict(warning_case["objective_mutations"])
warning_finding = dict(warning_mutations["healer_finding"])
warning_record = dict(warning_mutations["chronicler_record"])
assert warning_finding["mask_id"] == healer_tester.id
assert warning_finding["mask"] == "HealerTester"
assert warning_finding["property"] == "toxin"
assert warning_finding["value"] == 25
assert warning_record["mask_id"] == smoke.id
assert warning_record["mask"] == "SmokeTester"

warning_entry = next(
    entry
    for entry in entries
    if entry["id"] == warning_record["chronicle_entry_id"]
)
assert warning_entry["claim_status"] == "verified_event"
assert "health warning issued for well mushrooms" in warning_entry["title"].lower()
assert "healertester" in warning_entry["text"].lower()
assert "can be toxic" in warning_entry["text"].lower()
assert "other mushrooms as safe" in warning_entry["text"].lower()
assert "25" not in warning_entry["text"]

warning_story = get_story(warning_record["harbinger_story_id"])
assert warning_story
assert "health warning issued for well mushrooms" in warning_story["headline"].lower()
assert "healertester" in warning_story["body"].lower()
assert "can be toxic" in warning_story["body"].lower()
assert "25" not in warning_story["body"]
assert warning_story["status"] in {"pending", "published"}

warning_ledger = ScriptDB.objects.get(db_key="world_event_ledger")
finding_event = warning_ledger.get_event(warning_finding["event_id"])
warning_event = warning_ledger.get_event(warning_record["event_id"])
assert finding_event["kind"] == "professional.healer_finding_submitted"
assert finding_event["payload"]["mechanical_value"] == 25
assert finding_event["payload"]["harbinger"] is False
assert finding_event["payload"]["chronicle_eligible"] is False
assert warning_event["kind"] == "professional.public_health_warning"
assert warning_event["payload"]["source_healer_mask_id"] == healer_tester.id
assert warning_event["publications"]["chronicle_entry_id"] == warning_entry["id"]
assert warning_event["publications"]["harbinger_story_id"] == warning_story["id"]
assert hidden_mechanical_properties(mushrooms) == {"toxin": 25}
assert mechanical_properties(mushrooms) == {}

# Resident care interdependence survives restart as Resident Life state plus a
# provenance record. The current stew stock may have been restocked by Bram,
# so the authoritative consumption proof is the care event's before/after pair.
cold_case = get_situation(TAVERN_COLD_CARE_ID)
assert cold_case["state"] == "aftermath"
assert cold_case["branch"] == "cared_for"
cold_mutations = dict(cold_case["objective_mutations"])
cold_init = dict(cold_mutations["patient_initialized"])
cold_assessment = dict(cold_mutations["healer_assessment"])
cold_hospitality = dict(cold_mutations["innkeep_care"])
assert cold_init["resident_id"] == "silas_crowe"
assert cold_assessment["mask_id"] == healer_tester.id
assert cold_assessment["mask"] == "HealerTester"
assert cold_hospitality["mask_id"] == innkeep_tester.id
assert cold_hospitality["mask"] == "InnkeepTester"
assert cold_hospitality["resource_object_key"] == "a bowl of stew"
assert cold_hospitality["servings_before"] - cold_hospitality["servings_after"] == 1
assert cold_hospitality["source_healer_event_id"] == cold_assessment["event_id"]

silas = one("Silas Crowe")
silas_life = resident_state(silas)["life"]
silas_body = dict(silas_life["body"])
assert silas_body["cold"] <= 15
assert silas_body["wet"] <= 10
assert silas_body["discomfort"] <= 10
assert any(
    item.get("key") == "warm_after_hunt"
    and item.get("status") == "fulfilled"
    for item in silas_life.get("commitments") or []
)
assert any(
    "hot stew" in str(item.get("summary") or "").lower()
    for item in silas_life.get("perceptions") or []
)

cold_ledger = ScriptDB.objects.get(db_key="world_event_ledger")
assessment_event = cold_ledger.get_event(cold_assessment["event_id"])
hospitality_event = cold_ledger.get_event(cold_hospitality["event_id"])
assert assessment_event["kind"] == "professional.healer_cold_assessment"
assert hospitality_event["kind"] == "professional.innkeep_recovery_care"
assert hospitality_event["payload"]["source_healer_event_id"] == (
    assessment_event["id"]
)
assert hospitality_event["payload"]["servings_before"] - (
    hospitality_event["payload"]["servings_after"]
) == 1

# Smith and Merchant repair work survives restart as professional history,
# finite stock depletion, linked provenance, and transformed object state.
assert active_calling(smith_tester) == "smith"
assert active_rank(smith_tester) == RANK_APPRENTICE
assert calling_record(smith_tester, "smith")["participation"]["repair_diagnoses"] == 1
assert calling_record(smith_tester, "smith")["participation"]["repair_completions"] == 1
assert active_calling(merchant_tester) == "merchant"
assert active_rank(merchant_tester) == RANK_APPRENTICE
assert calling_record(merchant_tester, "merchant")["participation"]["repair_procurements"] == 1

lamp_repair_case = get_situation(LAMP_REPAIR_ID)
assert lamp_repair_case["state"] == "aftermath"
assert lamp_repair_case["branch"] == "repaired"
lamp_mutations = dict(lamp_repair_case["objective_mutations"])
lamp_diagnosis = dict(lamp_mutations["smith_diagnosis"])
lamp_procurement = dict(lamp_mutations["merchant_procurement"])
lamp_completion = dict(lamp_mutations["smith_repair"])
assert lamp_diagnosis["mask_id"] == smith_tester.id
assert lamp_procurement["mask_id"] == merchant_tester.id
assert lamp_completion["mask_id"] == smith_tester.id
assert lamp_procurement["units_before"] - lamp_procurement["units_after"] == 1
assert lamp_procurement["source_smith_event_id"] == lamp_diagnosis["event_id"]
assert lamp_completion["source_smith_diagnosis_event_id"] == lamp_diagnosis["event_id"]
assert lamp_completion["source_merchant_event_id"] == lamp_procurement["event_id"]

north_square_lamp = one("north-square gas lamp")
repair_stock = one("a tray of brass mantle collars")
assert north_square_lamp.db.repair_state == "working"
assert north_square_lamp.db.repair_fault is None
assert "steady yellow flame" in (north_square_lamp.db.desc or "").lower()
assert repair_stock.db.units == lamp_procurement["units_after"]
assert mechanical_properties(repair_stock) == {"uses": 4, "worth": 7}

repair_ledger = ScriptDB.objects.get(db_key="world_event_ledger")
diagnosis_event = repair_ledger.get_event(lamp_diagnosis["event_id"])
procurement_event = repair_ledger.get_event(lamp_procurement["event_id"])
completion_event = repair_ledger.get_event(lamp_completion["event_id"])
assert diagnosis_event["kind"] == "professional.smith_lamp_diagnosis"
assert procurement_event["kind"] == "professional.merchant_repair_procurement"
assert completion_event["kind"] == "professional.smith_lamp_repair_completed"
assert procurement_event["payload"]["source_smith_event_id"] == diagnosis_event["id"]
assert completion_event["payload"]["source_merchant_event_id"] == procurement_event["id"]
assert completion_event["consequence"]["repair_state"] == "working"

# Harbinger The Correction must survive restart as an archive discrepancy.
# The old story body remains the surviving copy; the claimant's alleged wording
# and the follow-up response are separate persistent records.
public_records_for_correction = ScriptDB.objects.get(db_key="public_records")
smoke_correction_disputes = [
    dict(dispute)
    for dispute in (
        public_records_for_correction.db.harbinger_correction_disputes or []
    )
    if dispute.get("claimed_by_mask_id") == smoke.id
]
assert len(smoke_correction_disputes) == 1
smoke_correction_dispute = smoke_correction_disputes[0]
assert smoke_correction_dispute["status"] == "archive_discrepancy"
original_correction_story = get_story(smoke_correction_dispute["story_id"])
assert original_correction_story
assert smoke_correction_dispute["claimed_text"] not in (
    original_correction_story["body"]
)
assert hashlib.sha256(
    (
        original_correction_story["headline"]
        + "\n"
        + original_correction_story["body"]
    ).encode("utf-8")
).hexdigest() == smoke_correction_dispute["surviving_copy_hash"]
story_disputes = correction_disputes_for_story(
    smoke_correction_dispute["story_id"]
)
assert len([
    dispute
    for dispute in story_disputes
    if dispute.get("claimed_by_mask_id") == smoke.id
]) == 1
assert original_correction_story["correction_disputes"][-1][
    "id"
] == smoke_correction_dispute["id"]
correction_response_story = get_story(
    smoke_correction_dispute["response_story_id"]
)
assert correction_response_story
assert correction_response_story["basis"] == "correction_dispute"
assert correction_response_story["disputes_story_id"] == (
    original_correction_story["id"]
)
assert correction_response_story["surviving_copy_hash"] == (
    smoke_correction_dispute["surviving_copy_hash"]
)
assert correction_response_story["status"] == "published"
response_edition = next(
    dict(item)
    for item in (public_records_for_correction.db.harbinger_editions or [])
    if item.get("id") == correction_response_story["published_edition_id"]
)
assert correction_response_story["id"] in response_edition["story_ids"]

# Tomorrow's Obituary must survive restart as an editorial decision while the
# subject remains alive. The investigation story may be pending or already
# printed depending on the publication boundary reached later in the playtest.
smoke_obituary_cases = [
    case
    for case in harbinger_obituary_cases()
    if (
        case.get("submitted_by_mask_id") == smoke.id
        and case.get("subject_resident_id") == "miklos_farkas"
    )
]
assert len(smoke_obituary_cases) == 1
smoke_obituary = smoke_obituary_cases[0]
assert smoke_obituary["status"] == "closed"
assert smoke_obituary["decision"] == "investigate"
assert smoke_obituary["lifecycle_at_submission"] == "active"
assert smoke_obituary["lifecycle_at_decision"] == "active"
assert smoke_obituary["story_id"]
obituary_story = get_story(smoke_obituary["story_id"])
assert obituary_story
assert obituary_story["basis"] == "obituary_investigation"
assert obituary_story["obituary_case_id"] == smoke_obituary["id"]
assert obituary_story["obituary_subject_resident_id"] == "miklos_farkas"
assert "found alive" in obituary_story["headline"].lower()
assert obituary_story["status"] in {"pending", "published"}
assert (resident_state(miklos).get("lifecycle") or {}).get("status") == "active"
obituary_flag = resident_state(miklos)["event_flags"].get(
    str(smoke_obituary["event_id"])
)
assert obituary_flag
assert obituary_flag["payload"]["decision"] == "investigate"
assert obituary_flag["payload"]["reaction"] == (
    "relieved_by_obituary_investigation"
)
obituary_event = ScriptDB.objects.get(db_key="world_event_ledger").get_event(
    smoke_obituary["event_id"]
)
assert obituary_event["kind"] == "harbinger.tomorrows_obituary_decision"
assert obituary_event["payload"]["chronicle_eligible"] is False
assert obituary_event["payload"]["lifecycle_status"] == "active"

# Revision by Evidence must survive a real process restart without rewriting
# the original Chronicle claim status. The telnet player cited documentary
# strongbox evidence through the public command path.
strongbox_entry = next(
    entry
    for entry in entries
    if entry.get("title") == "Church Strongbox Loss Made Public"
)
assert strongbox_entry["claim_status"] == "verified_event"
evidence_annotations = [
    annotation
    for annotation in strongbox_entry.get("annotations") or []
    if annotation.get("annotation_type") == "evidence_revision"
    and annotation.get("source_mask_id") == smoke.id
]
assert len(evidence_annotations) == 1
evidence_annotation = evidence_annotations[0]
assert evidence_annotation["source_mask"] == "SmokeTester"
assert evidence_annotation["source_evidence_refs"] == [{
    "situation_id": TITHE_ID,
    "evidence_id": "roll",
    "label": "the tithe roll",
    "provenance": "documentary",
    "summary": (
        "The tithe roll was balanced the previous evening and records enough "
        "coin that the present lightness cannot be bookkeeping."
    ),
}]
assert "original entry and its prior claim status remain unchanged" in (
    evidence_annotation["text"].lower()
)

# The Refused Entry must survive restart as an institutional decision, not as
# a promoted rumor. Its social reaction also survives on residents who carried
# the claim strongly enough to be affected by the refusal.
public_records_for_refusal = ScriptDB.objects.get(db_key="public_records")
smoke_refusals = [
    dict(refusal)
    for refusal in (public_records_for_refusal.db.chronicle_refusals or [])
    if refusal.get("petitioned_by_mask_id") == smoke.id
]
assert len(smoke_refusals) == 1
smoke_refusal = smoke_refusals[0]
assert smoke_refusal["status"] == "refused"
assert smoke_refusal["supporter_count"] >= 3
assert len(smoke_refusal["supporter_resident_ids"]) == (
    smoke_refusal["supporter_count"]
)
refusal_entry = next(
    entry
    for entry in entries
    if entry.get("id") == smoke_refusal["chronicle_entry_id"]
)
assert refusal_entry["entry_type"] == "refusal_record"
assert refusal_entry["claim_status"] == "refused_canonization"
assert refusal_entry["source_rumor_ids"] == [smoke_refusal["rumor_id"]]
assert "does not certify the rumor as true or false" in refusal_entry["text"]
assert all(
    not (
        entry.get("claim_status") == "verified_event"
        and smoke_refusal["rumor_id"] in (entry.get("source_rumor_ids") or [])
    )
    for entry in entries
)
refusal_story = get_story(smoke_refusal["harbinger_story_id"])
assert refusal_story
assert "Chronicle Refuses Popular Rumor" in refusal_story["headline"]
supporter_id = smoke_refusal["supporter_resident_ids"][0]
supporter = next(
    npc for npc in population
    if npc.db.resident_id == supporter_id
)
supporter_flag = resident_state(supporter)["event_flags"].get(
    str(smoke_refusal["event_id"])
)
assert supporter_flag
assert supporter_flag["payload"]["reaction"] == "angered_by_refusal"

# The Chronicler preserves incompatible signed versions without promoting
# either one to verified history. This fixture was created through the same
# submission API before the real telnet pass and must survive a process restart.
chronicle_rumors = get_rumor_registry()
well_root = next(
    dict(rumor)
    for rumor in (chronicle_rumors.db.rumors or [])
    if rumor.get("canonical_seed_id") == 201
)
well_depositions = depositions_for_rumor(well_root["id"])
assert len({
    deposition.get("claim")
    for deposition in well_depositions
}) >= 3
well_disagreement = chronicle_disagreement_for_rumor(well_root["id"])
assert well_disagreement
assert well_disagreement["claim_status"] == "documented_disagreement"
assert len(well_disagreement.get("version_claims") or []) >= 3
assert len(well_disagreement.get("annotations") or []) >= 1
assert "does not choose" in well_disagreement["text"].lower()
assert all(
    entry.get("claim_status") != "verified_event"
    for entry in [
        item for item in entries
        if item.get("id") == well_disagreement["id"]
    ]
)

# The telnet copy-desk choice must survive a real process restart. It remains
# an attributed Harbinger interpretation and never upgrades the underlying
# disputed rumor to verified Chronicle history.
well_press = [
    conflict
    for conflict in harbinger_conflicts()
    if conflict.get("rumor_id") == well_root["id"]
]
assert len(well_press) == 1
well_press = well_press[0]
assert well_press["status"] == "selected"
assert well_press["resolution"] == "selected_account"
assert well_press["decided_by_mask"] == "SmokeTester"
assert well_press["story_id"]
well_press_story = get_story(well_press["story_id"])
assert well_press_story
assert well_press_story["basis"] == "contested_report"
assert well_press_story["source_rumor_id"] == well_root["id"]
assert well_press_story["source_deposition_id"] == (
    well_press["decision_deposition_id"]
)
assert "does not certify the claim as fact" in well_press_story["body"]

incident = get_situation(TITHE_ID)
assert incident["state"] == "aftermath"
assert incident["branch"] == "openly"
status = situation_status_for_player(smoke, TITHE_ID)
assert status
assert {entry["id"] for entry in status["evidence"]} == {
    "lock", "roll"
}
church = one("St. Lazarus Church")
assert church.db.tithe_strongbox_policy == "two_key"
assert church.db.tithe_confidence == "divided"

torn = get_situation(TORN_CHRONICLE_ID)
assert torn["state"] == "aftermath"
assert torn["branch"] == "reconstruct"
torn_status = situation_status_for_player(smoke, TORN_CHRONICLE_ID)
assert torn_status
assert {entry["id"] for entry in torn_status["evidence"]} == {
    "gap", "harbinger_archive"
}
from world.publications import get_public_record_registry
public_records = get_public_record_registry()
assert public_records.db.chronicle_gap_policy == "reconstructed_from_harbinger"
assert public_records.db.chronicle_gap_source == "Harbinger archive"

# A real restart must preserve the timed window and the exact evidence quality
# earned by the player. If enough wall-clock time elapsed during CI, direct
# catch-up may resolve the window, but it must never downgrade firsthand proof.
advance_timed_incidents()
timed = get_timed_incident(WELL_BOILS_ID)
assert timed["state"] in {"active", "aftermath"}
timed_status = timed_status_for_player(smoke, WELL_BOILS_ID)
assert timed_status, "telnet well observation did not survive restart"
assert timed_status["observation"]["quality"] == "firsthand"
assert "rope trembled" in timed_status["observation"]["summary"].lower()
assert timed["occurrence_count"] == 1
if timed["state"] == "aftermath":
    assert timed["current"]["aftermath_event_id"]
    assert timed["current"]["rumor_id"]
    assert timed["current"]["publications"]["harbinger_story_id"]
    assert timed["current"]["publications"].get("chronicle_entry_id") is None

# Random texture persists independently of the timed-window and quest layers.
# If a clock boundary happened during CI, it may already be archived; either
# way the same occurrence must survive and remain private.
random_current = current_random_incident()
random_records = (
    [random_current]
    if random_current and random_current.get("id") == EXTINGUISHED_LAMP_ID
    else [
        record for record in recent_random_incidents(5)
        if record.get("id") == EXTINGUISHED_LAMP_ID
    ]
)
assert random_records, "telnet random incident did not survive restart"
random_record = random_records[-1]
assert random_record["tone"] == "odd"
assert random_record["location"] == "Village Square"

# The player-facing blackout contribution is shared server state and must
# survive a real process restart independently of the player's own journal.
blackout = get_server_event(LONG_BLACKOUT_ID)
assert blackout["state"] in {"active", "aftermath"}
blackout_current = blackout["current"]
assert "lamps" in (blackout_current.get("responses") or {})
lamp_response = blackout_current["responses"]["lamps"]
assert lamp_response["result"] == "street lamps stabilized"
assert any(
    helper.get("mask_id") == smoke.id
    for helper in lamp_response.get("helpers") or []
), "telnet blackout contribution did not survive restart"

server_events = get_server_event_registry()
assert ScriptDB.objects.filter(db_key="server_event_registry").count() == 1
assert set((server_events.db.events or {}).keys()) == {LONG_BLACKOUT_ID}
assert set((server_events.db.metrics or {}).keys()).issuperset({
    "checks", "starts", "contributions", "resolutions", "aftermath_clears",
})

# Public observations and theories are shared persistent records, but theory
# truth status must remain deliberately unset after restart.
manor_mystery = get_public_mystery(MANOR_LIGHTS_ID)
assert manor_mystery["status"] == "open"
assert any(
    any(witness.get("mask_id") == smoke.id for witness in obs.get("witnesses") or [])
    for obs in manor_mystery.get("observations") or []
), "telnet Manor observation did not survive restart"
smoke_theories = [
    theory
    for theory in manor_mystery.get("theories") or []
    if (theory.get("author") or {}).get("mask_id") == smoke.id
]
assert smoke_theories, "telnet public theory did not survive restart"
assert all(theory.get("truth_status") is None for theory in smoke_theories)
assert any(
    "maintenance schedule" in theory.get("text", "").lower()
    for theory in smoke_theories
)
public_mysteries = get_public_mystery_registry()
assert ScriptDB.objects.filter(db_key="public_mystery_registry").count() == 1
assert set((public_mysteries.db.mysteries or {}).keys()) == {MANOR_LIGHTS_ID}

# Private mystery ownership and deliberate disclosure survive independently.
private_registry = get_private_mystery_registry()
assert ScriptDB.objects.filter(db_key="private_mystery_registry").count() == 1
private_records = private_records_for(smoke)
assert len(private_records) == 1
private_record = private_records[0]
assert private_record["id"] == HOUNDS_INVITATION_ID
assert private_record["status"] == "opened"
assert private_record["invitation_rumor_id"]
assert private_record["followup_rumor_id"]
assert any(
    (entry.get("target") or {}).get("mask") == "Bram"
    for entry in private_record.get("disclosures") or []
), "private disclosure to Bram did not survive restart"

private_rumors = get_rumor_registry()
followup_id = private_record["followup_rumor_id"]
followup_root = private_rumors.get_rumor(followup_id)
assert followup_root["privacy"] == "private"
assert private_rumors.belief_for(smoke, followup_id)
bram = one("Bram")
assert private_rumors.belief_for(bram, followup_id), (
    "explicitly retold private rumor did not remain known to Bram"
)
tavern = one("The Blood of the Vine")
assert followup_id not in (tavern.db.public_rumor_ids or []), (
    "private disclosure became public tavern knowledge"
)

print("POST_RESTART_RESIDENT_ASSERTIONS_GREEN")
print("POST_RESTART_PUBLIC_RECORD_ASSERTIONS_GREEN")
print("POST_RESTART_SITUATION_ASSERTIONS_GREEN")
scheduled = get_scheduled_event_registry()
assert set((scheduled.db.events or {}).keys()) == {
    HARBINGER_PUBLICATION_ID,
    MARKET_MORNING_ID,
    SUNDAY_SERVICE_ID,
}
assert ScriptDB.objects.filter(db_key="scheduled_event_registry").count() == 1
assert set((scheduled.db.metrics or {}).keys()).issuperset({
    "checks", "starts", "ends", "pulses",
})

print("POST_RESTART_INCIDENT_FEED_ASSERTIONS_GREEN")
print("POST_RESTART_TIMED_INCIDENT_ASSERTIONS_GREEN")
seasonal_registry = get_seasonal_framework_registry()
assert seasonal_registry.db.active_id == LONG_SHADOWS_ID
assert current_chapter()["id"] == LONG_SHADOWS_ID
square = one("Village Square")
assert SEASONAL_OVERLAY_KEY in (square.db.scheduled_overlays or {})
assert "long shadows" in (
    square.db.scheduled_overlays or {}
)[SEASONAL_OVERLAY_KEY].lower()

print("POST_RESTART_RANDOM_INCIDENT_ASSERTIONS_GREEN")
print("POST_RESTART_SEASONAL_ASSERTIONS_GREEN")
print("POST_RESTART_SERVER_EVENT_ASSERTIONS_GREEN")
print("POST_RESTART_PUBLIC_MYSTERY_ASSERTIONS_GREEN")
print("POST_RESTART_PRIVATE_MYSTERY_ASSERTIONS_GREEN")
print("POST_RESTART_SCHEDULED_EVENT_ASSERTIONS_GREEN")

# An asynchronous public commons survives Evennia stop/start.
from world import commons, commons_state
commons_after_restart = commons.current()
first_notice = commons_state.get_notice(commons_after_restart, 1)
second_notice = commons_state.get_notice(commons_after_restart, 2)
assert first_notice and first_notice["status"] == "closed"
assert first_notice["author"]["mask"] == "SmithTester"
assert any(reply["by"]["mask"] == "MerchantTester" for reply in first_notice["replies"])
assert first_notice["resolution"]["body"].startswith("We spoke")
assert second_notice and second_notice["status"] == "open"
assert second_notice["author"]["mask"] == "MerchantTester"
assert second_notice["body"].startswith("I can carry parcels")
print("POST_RESTART_COMMONS_ASSERTIONS_GREEN")
