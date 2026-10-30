"""Assertions run after the player telnet pass and a real server restart."""

import hashlib

from evennia.scripts.models import ScriptDB
from evennia.accounts.models import AccountDB
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
    BRIDGE_PLAQUE_ID,
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
# GDD T-09: character sensations are projections of one existing body
# and persist across real restart without a second need ledger.
_emic = smoke.sensory_snapshot()
assert _emic["body_model"] == "represented_character_sensations_not_ai_biology"
assert _emic["bands"]["hunger"] in {"sated", "settled", "hungry", "famished"}
assert _emic["first_person"] and _emic["possible_relief"]
# The physical Tavern objects and their mutable serving counts persist
# through restart. Bram's ORIGINAL routine may legitimately refill a plate
# while he is actually at the Tavern. Assert conservation and identity, not
# a fabricated permanent depletion or exact refill day.
_bread = one("a loaf of bread")
_cheese = one("a wedge of cheese")
assert _bread.location.key == "The Blood of the Vine"
assert _cheese.location.key == "The Blood of the Vine"
assert 0 <= _bread.db.servings <= 6
assert 0 <= _cheese.db.servings <= 5
print("POST_RESTART_GDD_T09_REAL_FOOD_AND_FIRST_PERSON_STATE_GREEN")

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

# Recipe trials are physical work, carried ingredients and finished food,
# not an experience point allocation. Personal and public ledgers survive.
from world import soup_state
_tavern_soup = one("The Blood of the Vine")
_soup_log = soup_state.pantry(_tavern_soup.db.soup_pantry, 1)
assert _soup_log["history"], "The shared soup pot lost all batches"
_batch = _soup_log["history"][-1]
assert _batch["maker_id"] == innkeep_tester.id
assert _batch["base"] == "turnip" and _batch["seasoning"] == "thyme"
assert _batch["prep_event_id"] < _batch["cook_event_id"]
assert innkeep_record["participation"]["soup_preparations"] == 1
assert innkeep_record["participation"]["soup_batches_cooked"] == 1
assert len(list(innkeep_tester.db.soup_notebook or [])) == 1
assert list(innkeep_tester.db.soup_notebook)[-1]["cook_event_id"] == _batch["cook_event_id"]
assert calling_record(merchant_tester, "merchant")["participation"]["kitchen_procurements"] == 1
_soup_cooked = ScriptDB.objects.get(db_key="world_event_ledger").get_event(_batch["cook_event_id"])
assert _soup_cooked["kind"] == "professional.innkeep_soup_cooked"
assert _soup_cooked["status"] == "complete"
assert _soup_cooked["consequence"]["bowl_id"] > 0
assert _soup_cooked["payload"]["prep_event_id"] == _batch["prep_event_id"]
assert _soup_log["stock"]["turnip"] >= 2
assert not [obj for obj in innkeep_tester.contents if obj.key == "a packet of soup ingredients"]
_soup_bowl = one("a bowl of turnip and thyme soup")
assert _soup_bowl.location == innkeep_tester
assert _soup_bowl.db.servings == 0, "Consumed bowl refilled across restart"
assert one("a communal soup pot").location == _tavern_soup
# GDD-EDGE-04: the real Merchant crate was given to a different account,
# accepted exactly once, and the two canonical events survived restart.
_soup_ledger = ScriptDB.objects.get(db_key="world_event_ledger")
_edge04_receipts = [
    dict(row) for row in (_soup_ledger.db.events or [])
    if row.get("kind") == "professional.innkeep_kitchen_acceptance"
]
assert len(_edge04_receipts) == 1, "Kitchen receipt missing or duplicated"
_edge04 = _edge04_receipts[0]
_edge04_source = _soup_ledger.get_event(
    _edge04["payload"]["procurement_event_id"]
)
assert _edge04["status"] == "complete"
assert _edge04_source and _edge04_source["status"] == "complete"
assert _edge04_source["kind"] == "professional.merchant_kitchen_procurement"
assert _edge04_source["actor"]["mask_id"] == merchant_tester.id
assert _edge04["actor"]["mask_id"] == innkeep_tester.id
assert _edge04_source["actor"]["account_id"] != _edge04["actor"]["account_id"]
assert _edge04["consequence"]["merchant_account_id"] == (
    _edge04_source["actor"]["account_id"]
)
assert _edge04["consequence"]["receiving_account_id"] == (
    _edge04["actor"]["account_id"]
)
assert _edge04["consequence"]["procurement_event_id"] == _edge04_source["id"]
assert _edge04_source["consequence"]["crate_id"] == (
    _edge04["consequence"]["crate_id"]
)
assert _edge04["consequence"]["pantry_room_id"] == _tavern_soup.id
assert _edge04["consequence"]["turnip_stock"] >= 4
assert not [obj for obj in innkeep_tester.contents
            if obj.key == "a crate of kitchen roots"], (
    "Consumed Merchant crate survived a real server restart"
)
assert innkeep_record["participation"]["kitchen_acceptances"] == 1
print("POST_RESTART_GDD_EDGE04_SIGNED_TWO_ACCOUNT_KITCHEN_SUPPLY_GREEN")
print("POST_RESTART_SHARED_SOUP_WORKPLACE_GREEN")

# EDGE-01: the same physical batch and existing pantry history survive an
# actual Evennia stop/start with consent and independent publication intact.
from world import soup_receipts
_consent = dict(_batch.get("consent") or {})
_publication = dict(_batch.get("publication") or {})
assert _consent["cook_event_id"] == _batch["cook_event_id"]
assert _publication["cook_event_id"] == _batch["cook_event_id"]
assert _publication["consent_event_id"] == _consent["event_id"]
assert _consent["mask_id"] == innkeep_tester.id
assert _publication["mask_id"] == smoke.id
assert _consent["account_id"] != _publication["account_id"]
_receipt_ledger = ScriptDB.objects.get(db_key="world_event_ledger")
_disclosed = _receipt_ledger.get_event(_consent["event_id"])
_published = _receipt_ledger.get_event(_publication["event_id"])
assert _disclosed["status"] == _published["status"] == "complete"
assert _disclosed["kind"] == "professional.innkeep_house_receipt_disclosed"
assert _published["kind"] == "professional.chronicler_house_receipt_published"
assert _disclosed["actor"]["account_id"] == _consent["account_id"]
assert _published["actor"]["account_id"] == _publication["account_id"]
assert _disclosed["payload"]["cook_event_id"] == _batch["cook_event_id"]
assert _published["payload"]["consent_event_id"] == _consent["event_id"]
assert _published["consequence"]["scope"] == "public_kitchen_batch_only"
_public_receipts = soup_receipts.public_lines(_tavern_soup.db.soup_pantry, 2)
assert "Chronicler SmokeTester" in _public_receipts
assert "not a guest list" in _public_receipts
assert "guest_name" not in str(_batch)
print("POST_RESTART_GDD_EDGE01_CONSENTED_HOUSE_RECEIPT_GREEN")



population = list(search.search_tag("resident", category="system"))
from world.resident_data import RESIDENTS
assert len(population) == len(RESIDENTS) >= 36, "resident population changed across restart"

# Systemic object definitions survive the process boundary. During the live
# server pass Bram's routine legitimately restocks the bread after the player
# buys a serving, so the post-restart count should be the configured uses
# capacity rather than the pre-restock count.
bread = one("a loaf of bread")
water = one("a cup of water")
# A real restart may retain a legacy same-name cluster, original carried
# growth and new registered growth. Select the original signed physical
# specimen by its pre-rebuild ID, never by a global first-name match.
from world import clinic_inquiry_state as _well_rules
from commands.village_cmds import (
    _preferred_well_growth_pickup as _well_pickup,
    ensure_well_mushrooms as _ensure_well_growth,
)
_square = one("Village Square")
_wells = [o for o in _square.contents
          if o.key == "well"
          and o.is_typeclass("typeclasses.objects.VillageWell", exact=True)]
assert len(_wells) == 1, "canonical village well lost or duplicated"
_well = _wells[0]
_registered_before = tuple(_well_rules.well_growth_ids(
    getattr(_well.db, "well_mushroom_spawn_ids", None)))
assert _registered_before, "registered growth provenance did not survive restart"
_all_clusters = [o for o in search.search_object("a cluster of mushrooms")
                 if o.key == "a cluster of mushrooms"]
_original_id = getattr(_well.db, "qa_expected_growth_id", None)
_originals = [o for o in _all_clusters
              if o.id == _original_id
              and _well_rules.registered_well_growth(o.id, _registered_before)
              and getattr(o.db, "well_mushroom_source_id", None) == _well.id]
assert len(_originals) == 1, "original registered specimen lost across restart"
mushrooms = _originals[0]
_legacy = [o for o in _all_clusters
           if getattr(o.db, "qa_legacy_mushroom_decoy", False) is True]
assert len(_legacy) == 1, "hostile legacy coexistence fixture did not persist"
assert _legacy[0].location == _square
assert _legacy[0].id not in _registered_before
assert not _well_rules.registered_well_growth(
    _legacy[0].id, _registered_before)
assert getattr(_legacy[0].db, "well_mushroom_source_id", None) == _well.id
assert hidden_mechanical_properties(_legacy[0]) == {"toxin": 25}
_floor_growth = _well_pickup(
    [o for o in _square.contents if o.key == "a cluster of mushrooms"],
    _square,
)
assert _floor_growth is not None and _floor_growth.id in _registered_before
assert _well_pickup([_legacy[0], _floor_growth], _square) is _floor_growth
assert _well_pickup([_floor_growth, _legacy[0]], _square) is _floor_growth
assert _ensure_well_growth().id == _floor_growth.id, (
    "post-restart rebuild changed the physical registered well specimen")
assert tuple(_well.db.well_mushroom_spawn_ids or ()) == _registered_before, (
    "post-restart idempotent rebuild created or erased well provenance")
assert _legacy[0].id not in _well.db.well_mushroom_spawn_ids
print("POST_RESTART_GDD_EDGE28_MIGRATED_WELL_PROVENANCE_GREEN")
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
assert type(warning_finding["account_id"]) is int
assert warning_finding["mask"] == "HealerTester"
assert warning_finding["property"] == "toxin"
assert warning_finding["value"] == 25
assert warning_record["mask_id"] == smoke.id
assert type(warning_record["account_id"]) is int
assert warning_record["account_id"] != warning_finding["account_id"]
assert warning_record["source_healer_event_id"] == warning_finding["event_id"]
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
assert finding_event["status"] == "complete"
assert finding_event["actor"]["account_id"] == warning_finding["account_id"]
assert finding_event["actor"]["mask_id"] == healer_tester.id
assert finding_event["payload"]["day"] == warning_finding["day"]
assert finding_event["payload"]["hour"] == warning_finding["hour"]
assert finding_event["payload"]["mechanical_value"] == 25
assert finding_event["payload"]["harbinger"] is False
assert finding_event["payload"]["chronicle_eligible"] is False
assert warning_event["kind"] == "professional.public_health_warning"
assert warning_event["status"] == "complete"
assert warning_event["actor"]["account_id"] == warning_record["account_id"]
assert warning_event["payload"]["source_healer_account_id"] == warning_finding["account_id"]
assert warning_event["payload"]["source_healer_event_id"] == finding_event["id"]
assert warning_event["payload"]["source_healer_mask_id"] == healer_tester.id
assert warning_event["publications"]["chronicle_entry_id"] == warning_entry["id"]
assert warning_event["publications"]["harbinger_story_id"] == warning_story["id"]
assert hidden_mechanical_properties(mushrooms) == {"toxin": 25}
assert mechanical_properties(mushrooms) == {}
print("POST_RESTART_GDD_EDGE11_SIGNED_DISTINCT_HEALTH_WARNING_GREEN")

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

# GDD-EDGE-03: two actual accounts and an independently completed Healer
# event, not merely a situation row, survive the real Evennia restart.
assert assessment_event["status"] == "complete"
assert hospitality_event["status"] == "complete"
assert cold_assessment["account_id"] == assessment_event["actor"]["account_id"]
assert cold_hospitality["account_id"] == hospitality_event["actor"]["account_id"]
assert cold_assessment["account_id"] != cold_hospitality["account_id"]
assert cold_hospitality["source_healer_account_id"] == cold_assessment["account_id"]
assert cold_hospitality["source_healer_mask_id"] == cold_assessment["mask_id"]
assert hospitality_event["payload"]["source_healer_account_id"] == cold_assessment["account_id"]
assert hospitality_event["payload"]["source_healer_mask_id"] == cold_assessment["mask_id"]
assert assessment_event["actor"]["mask_id"] == cold_assessment["mask_id"]
assert assessment_event["payload"]["situation_id"] == TAVERN_COLD_CARE_ID
assert assessment_event["payload"]["resident_ids"] == ["silas_crowe"]
assert assessment_event["payload"]["professional_calling"] == "healer"
assert assessment_event["payload"]["day"] == cold_assessment["day"]
assert assessment_event["payload"]["hour"] == cold_assessment["hour"]
print("POST_RESTART_GDD_EDGE03_SIGNED_DISTINCT_CARE_GREEN")

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
from world.repair_provenance import verify_diagnosis, verify_procurement
assert verify_diagnosis(
    lamp_diagnosis, diagnosis_event, lamp_id=north_square_lamp.id,
    situation_id=LAMP_REPAIR_ID, part="brass mantle collar",
), "The Smith diagnosis has no matching completed signed source"
assert verify_procurement(
    lamp_procurement, procurement_event, lamp_diagnosis, diagnosis_event,
    stock_id=repair_stock.id, situation_id=LAMP_REPAIR_ID,
    part="brass mantle collar",
), "The Merchant procurement has no matching completed signed source"
assert diagnosis_event["actor"]["account_id"] != procurement_event["actor"]["account_id"]
assert completion_event["actor"]["account_id"] == diagnosis_event["actor"]["account_id"]
assert completion_event["consequence"]["source_smith_diagnosis_event_id"] == diagnosis_event["id"]
assert completion_event["consequence"]["source_merchant_event_id"] == procurement_event["id"]
print("POST_RESTART_GDD_EDGE19_SIGNED_REPAIR_GREEN")
# T-03: the authenticated Smith retried after an actual server restart.
# A truthful "already complete" response must not conceal a second signed
# completion, new part expenditure or replacement of the lamp's repair receipt.
lamp_completion_events = [
    event for event in (repair_ledger.db.events or [])
    if event.get("kind") == "professional.smith_lamp_repair_completed"
    and event.get("payload", {}).get("situation_id") == LAMP_REPAIR_ID
    and event.get("status") == "complete"
]
assert len(lamp_completion_events) == 1, lamp_completion_events
assert lamp_completion_events[0]["id"] == lamp_completion["event_id"]
assert north_square_lamp.db.repaired_by_event_id == lamp_completion["event_id"]
print("POST_RESTART_GDD_T03_SINGLE_REPAIR_EVENT_AND_STOCK_GREEN")

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
bridge_mystery = get_public_mystery(BRIDGE_PLAQUE_ID)
assert bridge_mystery and bridge_mystery["status"] == "open"
assert any(
    witness.get("mask") == "SmokeTester"
    for record in bridge_mystery.get("observations") or []
    for witness in record.get("witnesses") or []
), "The physical bridge observation did not survive restart"
assert any(
    "former ferry keeper" in theory.get("text", "")
    and theory.get("truth_status") is None
    for theory in bridge_mystery.get("theories") or []
), "The public bridge theory did not persist as an unresolved interpretation"
print("POST_RESTART_BRIDGE_MYSTERY_ASSERTIONS_GREEN")

assert set((public_mysteries.db.mysteries or {}).keys()) == {MANOR_LIGHTS_ID, BRIDGE_PLAQUE_ID}

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
# Public small-talk builds mask-specific social memory, not a shared
# account-level impression. Live player dialogue established the interests.
mask_memories = dict(bram.db.mask_memory or {})
smoke_memory = dict(mask_memories.get(str(smoke.id)) or {})
assert smoke_memory.get("first_talk") is True, (
    "Bram forgot this mask's first real conversation across server restart"
)
assert {"lamp", "silas", "work", "rumors"}.issubset(
    set(smoke_memory.get("interests") or [])
), "Bram lost the topics this individual mask chose to discuss"
healer_memory = dict(mask_memories.get(str(healer_tester.id)) or {})
assert {"lamp", "silas"}.issubset(
    set(healer_memory.get("interests") or [])
), "The Healer's direct inquiries did not survive restart"
returnee = bram._returnee_line(healer_tester, healer_memory, 0)
assert "that lamp you asked about" in returnee.lower(), (
    "Bram did not recall a mask's interest against changed public world state"
)
merchant_memory = dict(mask_memories.get(str(merchant_tester.id)) or {})
# The independently controlled AI merchant now also speaks to Bram in a
# real connection. That creates its OWN first-talk memory, not a leak of
# SmokeTester's earlier questions. Source the distinction from interests.
assert merchant_memory.get("first_talk") is True, (
    "Bram failed to remember the AI merchant's own first conversation"
)
assert str(smoke.id) != str(merchant_tester.id)
assert not {"lamp", "silas", "work", "rumors"}.intersection(
    set(merchant_memory.get("interests") or [])
), "Bram's private mask interests leaked to a different account"
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
assert len(second_notice["replies"]) == 2, (
    "Parallel Commons replies were lost or duplicated across server restart"
)
assert {reply["by"]["mask"] for reply in second_notice["replies"]} == {
    "SmithTester", "InnkeepTester",
}
assert len({reply["by"]["account_id"] for reply in second_notice["replies"]}) == 2, (
    "Simultaneous player updates were incorrectly attributed to one account"
)
print("POST_RESTART_CONCURRENT_COMMONS_ASSERTIONS_GREEN")

# Prospective interests belong to the active mask and survive real stop/start.
# The public board remains authoritative; mask bookmarks only store cursors.
from world import commons_follow
smith_follow = commons_follow.normalize(smith_tester.db.commons_following)
followed_ids = [w["id"] for w in smith_follow["items"]]
assert followed_ids == [1, 2], followed_ids
watched = commons_follow.summaries(smith_follow, commons_after_restart)
assert len(watched) == 2
assert watched[0]["status"] == "closed"
assert watched[0]["new_replies"] == 0
assert watched[0]["new_closure"] is False
assert watched[1]["status"] == "open"
assert watched[1]["new_replies"] == 0
assert not commons_follow.normalize(merchant_tester.db.commons_following)["items"], (
    "Smith's followed Commons correspondence leaked into a different mask"
)
# Physical finite-resource civic fire survives stop/start separately from
# closed authored cases. The warm period uses the one canonical village clock.
from world import hearth_state
source = one("a village woodpile")
actual_source = dict(source.db.civic_wood or {})
assert actual_source["remaining"] == 1, (
    "An idempotent rebuild or restart replenished previously taken wood"
)
tavern_hearth = hearth_state.hearth(tavern.db.civic_hearth)
assert tavern_hearth["reserve"] == 1, (
    "Delivered and spent fuel was not preserved"
)
assert tavern_hearth["warm_until"] > 0
assert len(tavern_hearth["history"]) == 1, (
    "The same Innkeep tending was replayed after restart"
)
last_tending = tavern_hearth["history"][0]
assert last_tending["mask_id"] == innkeep_tester.id
assert last_tending["mask"] == "InnkeepTester"
innkeep_stats = calling_record(innkeep_tester)
assert innkeep_stats["participation"].get("hearth_tendings") == 1
assert not any(
    o.key == "a bundle of firewood" and o.db.civic_firewood is True
    for o in smith_tester.contents
), "Consumed wood bundle reappeared in a player's inventory"
from world import civic_commissions
commissions = civic_commissions.normalize(tavern.db.civic_commission)
completed = commissions["commission"]
assert completed["status"] == "complete"
assert completed["supplier_account"] != completed["finisher_account"]
assert completed["bundle_id"] > 0
assert len(completed["event_ids"]) == 2
ledger = ScriptDB.objects.get(db_key="world_event_ledger")
assert ledger.get_event(completed["event_ids"][0])["status"] == "complete"
assert ledger.get_event(completed["event_ids"][1])["status"] == "complete"
assert ledger.get_event(completed["event_ids"][0])["actor"]["account_id"] == completed["supplier_account"]
assert ledger.get_event(completed["event_ids"][1])["actor"]["account_id"] == completed["finisher_account"]
assert not any(
    o.key == "a bundle of firewood" and o.db.civic_firewood is True
    for o in merchant_tester.contents
), "A claimed commission bundle was duplicated on restart"
print("POST_RESTART_COOPERATIVE_COMMISSION_ASSERTIONS_GREEN")
print("POST_RESTART_COMMUNITY_HEARTH_ASSERTIONS_GREEN")

# Resident response is based on actual physical witness of the completed
# Innkeep tending, not global knowledge of its ledger event. Test the
# persisted fire after a real restart and move residents by their NORMAL
# schedules (not teleporting their bodies or generating a second burn).
from world.residents import advance_population, generic_ask_line
mara = one("Mara Crowe")  # hunter schedule: Tavern 18-22, then home
marta = one("Marta Kovács")  # schoolteacher: home on day-one Sunday
father = one("Father Andrei")  # authored life state must remain locked
fire_event_id = last_tending["event_id"]
# The actual Long Shadows chapter overrides routine: public evening
# life closes early. That rule must win; a hearth may not force Mara into
# the Tavern and fabricate an experience she was never present for.
from world.seasonal_frameworks import (
    RECKONING_ID, get_seasonal_framework_registry,
)
chapter = get_seasonal_framework_registry()
assert chapter.db.active_id == LONG_SHADOWS_ID
advance_population(day=1, hour=21, emit=False)
assert mara.location != tavern, (
    "Hearth warmth bypassed Long Shadows' earlier evening closure"
)
assert not any(
    p.get("target_id") == "tavern_hearth"
    and p.get("source_id") == fire_event_id
    for p in resident_state(mara)["life"].get("perceptions") or []
), "Resident experienced a fire from home under Long Shadows"

# Counterfactual seasonal integration (no teleport): the same real persisted
# fire, physical Tavern, natural hunter route and population scheduler, but
# a chapter whose public evenings remain open. Restore season afterwards.
chapter.db.active_id = RECKONING_ID
advance_population(day=1, hour=21, emit=False)
assert mara.location == tavern, (
    "The ordinary hunter schedule did not bring Mara to the open Tavern"
)
mara_life = resident_state(mara)["life"]
perceptions = [
    p for p in mara_life.get("perceptions") or []
    if p.get("target_id") == "tavern_hearth"
    and p.get("source_id") == fire_event_id
]
assert len(perceptions) == 1, (
    "A real co-located resident failed to witness this tending exactly once"
)
assert perceptions[0]["summary"].startswith("I ")
assert mara_life["last_witnessed_hearth_event_id"] == fire_event_id
assert mara_life["body"]["cold"] <= 66.0, (
    "The cold-exposed witness got no measurable relief from actual warmth"
)
first_cold = mara_life["body"]["cold"]
prior_social = dict(mara_life.get("resident_relationships") or {})
first_count = len(perceptions)
advance_population(day=1, hour=21, emit=False)
mara_repeat = resident_state(mara)["life"]
assert mara_repeat["body"]["cold"] == first_cold, (
    "Running the same population hour gave free second warmth"
)
assert len([
    p for p in mara_repeat.get("perceptions") or []
    if p.get("target_id") == "tavern_hearth"
    and p.get("source_id") == fire_event_id
]) == first_count, "A duplicate first-person experience was minted"
assert "I was there" in generic_ask_line(
    mara, smith_tester, "hearth"
), "Resident cannot recall her own physically witnessed warmth"
assert not any(
    p.get("source_id") == fire_event_id
    and p.get("target_id") == "tavern_hearth"
    for p in resident_state(marta)["life"].get("perceptions") or []
), "Resident offstage learned of heat she never experienced"
assert not resident_state(father)["life"]["enabled"], (
    "Hearth observation illegally activated an authored-locked mind"
)

# At 22:00 the hunter ordinarily goes home. With enough remaining physical
# cold and an active fire, she elects to remain for one bounded hour instead;
# at 23:00 ordinary home schedule resumes. No social bond is inferred.
advance_population(day=1, hour=22, emit=False)
mara_shift = resident_state(mara)
assert mara_shift["routine"]["logical_location"] == "tavern"
assert mara_shift["routine"]["source"] == "hearth_preference"
assert mara.location == tavern
advance_population(day=1, hour=23, emit=False)
mara_departure = resident_state(mara)
assert mara_departure["routine"]["source"] == "schedule"
assert mara_departure["routine"]["logical_location"] != "tavern"
assert mara.location != tavern, "Hearth preference became an endless stay"
assert dict(mara_departure["life"].get("resident_relationships") or {}) == prior_social, (
    "A shared warmth event invented a private relationship"
)
chapter.db.active_id = LONG_SHADOWS_ID
assert chapter.db.active_id == LONG_SHADOWS_ID
print("POST_RESTART_RESIDENT_HEARTH_ASSERTIONS_GREEN")

# Real, scheduled residents encounter real public rain. This runs after the
# previous fire-scenario controls so their original contrasts remain sealed.
from world.residents import save_state as save_resident_state
from world.resident_weather import RAIN_TARGET_ID
import copy as _copy
weather = ScriptDB.objects.get(db_key="village_weather")
old_weather = weather.db.state
tam = one("Tam Rook")  # well keeper: Village Square, 04:00–09:00
weather.set_weather("fog")
advance_population(day=2, hour=5, emit=False)
assert tam.location == square, "The well keeper missed their normal dawn route"
tam_state = resident_state(tam)
assert tam_state["life"]["enabled"], "Resident weather incorrectly chose an authored lock"
tam_state["life"]["body"]["cold"] = 20.0
tam_state["life"]["body"]["wet"] = 10.0
save_resident_state(tam, tam_state)
before = _copy.deepcopy(resident_state(tam)["life"])
dry_witnesses = [
    p for p in before.get("perceptions") or []
    if p.get("target_id") == RAIN_TARGET_ID
]
weather.set_weather("rain")
advance_population(day=2, hour=6, emit=False)
assert tam.location == square, "The weather observer was not physically in the square"
after = resident_state(tam)["life"]
rain_witnesses = [
    p for p in after.get("perceptions") or []
    if p.get("target_id") == RAIN_TARGET_ID
]
assert len(rain_witnesses) == len(dry_witnesses) + 1, (
    "A truly co-located resident did not receive one new rain experience"
)
assert rain_witnesses[-1]["summary"].startswith("I ")
assert rain_witnesses[-1]["day"] == 2 and rain_witnesses[-1]["hour"] == 6
assert after["body"]["cold"] >= before["body"]["cold"] + 8, (
    "The physically exposed resident did not get measurably colder"
)
assert after["body"]["wet"] >= before["body"]["wet"] + 10, (
    "Real rain did not increase the exposed resident's wetness"
)
first_cold = after["body"]["cold"]
first_wet = after["body"]["wet"]
social_before = _copy.deepcopy(after.get("resident_relationships") or {})
advance_population(day=2, hour=6, emit=False)
repeat = resident_state(tam)["life"]
assert repeat["body"]["cold"] == first_cold
assert repeat["body"]["wet"] == first_wet
assert len([
    p for p in repeat.get("perceptions") or []
    if p.get("target_id") == RAIN_TARGET_ID
]) == len(rain_witnesses), "Same-hour rain was counted twice"
assert "I was caught in the rain" in generic_ask_line(
    tam, smith_tester, "rain"
), "A resident could not recall observed weather"
absent = resident_state(marta)["life"]
assert not any(
    p.get("target_id") == RAIN_TARGET_ID and
    p.get("day") == 2 and p.get("hour") == 6
    for p in absent.get("perceptions") or []
), "An absent schoolteacher was given physical rain experience"
assert marta.location != square
assert not resident_state(father)["life"]["enabled"]
weather.set_weather("fog")
advance_population(day=2, hour=7, emit=False)
dry_after = resident_state(tam)["life"]
assert len([
    p for p in dry_after.get("perceptions") or []
    if p.get("target_id") == RAIN_TARGET_ID
]) == len(rain_witnesses), "Fog was improperly treated as rain"
assert (dry_after.get("resident_relationships") or {}) == social_before
weather.set_weather(old_weather)
print("POST_RESTART_RESIDENT_WEATHER_CAUSAL_ASSERTIONS_GREEN")

# The return reminder belongs to the mask, survives a true restart, and
# cannot be read from another account's character record.
smoke_mask = one("SmokeTester")
healer_mask = one("HealerTester")
assert "speak with Bram about the river" in str(
    smoke_mask.db.player_return_note or ""
), "The personal next-step intention did not survive restart"
assert not healer_mask.db.player_return_note, (
    "Another player's mask acquired a private reminder"
)
print("POST_RESTART_PLAYER_AGENDA_ASSERTIONS_GREEN")

from world.discoveries import LANDMARKS, normalize as normalize_discoveries
field = normalize_discoveries(smoke.db.landmark_discoveries)
assert {item["id"] for item in field} == set(LANDMARKS), (
    "Not all firsthand district inspections survived an actual server restart"
)
assert not normalize_discoveries(healer_tester.db.landmark_discoveries), (
    "Another account inherited a private field notebook"
)
assert not normalize_discoveries(innkeep_tester.db.landmark_discoveries), (
    "A public conversation copied someone else's private discoveries"
)
for item in field:
    assert item["day"] >= 1 and 0 <= item["hour"] <= 23
print("POST_RESTART_FIRSTHAND_DISCOVERIES_GREEN")

from world import route_surveys as _daily_survey
route_board = _daily_survey.normalize(
    one("Village Square").db.daily_route_survey
)
assert _daily_survey.complete(route_board), (
    "Four legitimate in-person route reports did not survive restart"
)
assert set(route_board["reports"]) == set(_daily_survey.SITES)
assert {
    row["mask"] for row in route_board["reports"].values()
} == {"SmokeTester", "SmithTester"}
assert len({
    row["account_id"] for row in route_board["reports"].values()
}) == 2, "Separate contributors became one account"
for site, signed in route_board["reports"].items():
    incident = warning_ledger.get_event(signed["event_id"])
    assert incident["kind"] == "village.route_inspected"
    assert incident["payload"]["site"] == site
    assert incident["status"] == "complete"
_next_survey_day = _daily_survey.refresh(
    route_board, route_board["day"] + 1
)
assert not _next_survey_day["reports"]
assert _next_survey_day["history"][-1]["completed"] is True
assert len(_next_survey_day["history"][-1]["reports"]) == 4
assert calling_record(smoke, "chronicler")["participation"][
    "community_route_contributions"
] == 3, "Chronicler civic work participation was lost"
assert calling_record(smith_tester, "smith")["participation"][
    "community_route_contributions"
] == 1, "Smith civic work participation was lost"
print("POST_RESTART_DAILY_ROUTE_SURVEY_GREEN")
# GDD T-07: two ordinary accounts share the same real physical red cord,
# but only Hound changed its protection marker; Wanderer's earlier signed
# interpretation remains an accurate, time-scoped observation.
_treeline = one("The Northern Treeline")
_cords = [x for x in _treeline.contents if x.key == "a frayed red cord"]
assert len(_cords) == 1, "Treeline physical evidence missing or duplicated"
_cord = _cords[0]
_hound_protect = one("HoundTester")
_wanderer_field = one("WandererTester")
assert active_calling(_hound_protect) == "hound"
assert active_calling(_wanderer_field) == "wanderer"
assert _cord.db.route_caution["mask"] == "HoundTester"
assert _cord.db.route_caution["event_id"] > 0
assert "clear caution marker" in _cord.get_display_desc(looker=_wanderer_field)
_actions = route_board["field_decisions"]
assert set(_actions) == {"hound", "wanderer"}
assert _actions["hound"]["mask"] == "HoundTester"
assert _actions["wanderer"]["mask"] == "WandererTester"
assert _actions["wanderer"]["observation"] == "unmarked", (
    "Later protection overwrote the original Wanderer's observation"
)
assert _actions["hound"]["event_id"] == _cord.db.route_caution["event_id"]
for _role, _kind in (("hound", "village.route_protected"),
                     ("wanderer", "village.route_passability_observed")):
    _signed = warning_ledger.get_event(_actions[_role]["event_id"])
    assert _signed["kind"] == _kind
    assert _signed["status"] == "complete"
assert calling_record(_hound_protect, "hound")["participation"]["field_surveys"] == 1
assert calling_record(_wanderer_field, "wanderer")["participation"]["field_surveys"] == 1
assert set(_next_survey_day["history"][-1]["field_decisions"]) == {"hound", "wanderer"}
print("POST_RESTART_GDD_T07_SHARED_CORD_AND_DISTINCT_ACTIONS_GREEN")

# GDD-EDGE-13: the map is a persistent editorial snapshot with two
# independent real accounts and two completed, causally linked events.
_map = route_board["advisory"]
assert _map is not None, "Chronicler public map vanished after server restart"
assert _map["version"] == 1 and _map["source_day"] == route_board["day"]
assert _map["site"] == "red_cord"
assert _map["mask"] == "SmokeTester"
assert _map["source_mask"] == "WandererTester"
assert _map["source_event_id"] == _actions["wanderer"]["event_id"]
assert _map["source_account_id"] == _actions["wanderer"]["account_id"]
assert _map["account_id"] != _map["source_account_id"]
assert _map["observation"] == "unmarked", "A later warning rewrote the earlier map"
_published = warning_ledger.get_event(_map["event_id"])
assert _published["kind"] == "village.route_map_published"
assert _published["status"] == "complete"
assert _published["actor"]["account_id"] == _map["account_id"]
assert _published["payload"]["source_event_id"] == _map["source_event_id"]
assert _published["payload"]["source_account_id"] == _map["source_account_id"]
assert _next_survey_day["history"][-1]["advisory"] == _map
assert calling_record(smoke, "chronicler")["participation"]["route_advisories"] == 1
assert any("not a current safety guarantee" in text
           for text in _daily_survey.advisory_lines(route_board))
print("POST_RESTART_GDD_EDGE13_SIGNED_INDEPENDENT_MAP_GREEN")

from world.residents import (
    resident_state as _resident_state, relationship_for as _relationship_for
)
from world.resident_civic import (
    normalized_recognitions as _civic_notes,
    remembered_help as _civic_recalled,
)
_miklos = one("Miklós Farkas")
_civic = _civic_notes(_resident_state(_miklos).get("civic_recognitions"))
_personal = [
    row for row in _civic
    if row["mask_id"] == smoke.id and row["day"] == route_board["day"]
]
assert len(_personal) == 1, (
    "Repeated civic questions duplicated Miklós's credit for one signed day"
)
assert _personal[0]["site"] == "grave_marker"
assert _personal[0]["event_id"] == route_board["reports"][
    "grave_marker"
]["event_id"]
assert all(row["mask_id"] != merchant_tester.id for row in _civic), (
    "Another account received a private resident civic acknowledgment"
)
assert _relationship_for(_miklos, smoke)["trust"] > 0, (
    "Resident relationship did not persist after accepting public help"
)
assert "remember you helping" in _civic_recalled(
    _civic, mask_id=smoke.id, current_day=route_board["day"] + 1
)
print("POST_RESTART_RESIDENT_CIVIC_RECOGNITION_GREEN")


from world.market_standards import (
    normalize as _market_work_state, suspended as _market_suspended,
)
_market_live = _market_work_state(one("Market Lane").db.market_standards)
assert _market_live["review"] and _market_live["review"]["choice"] == "hold"
assert _market_live["calibration"] and _market_live["attestation"]
assert _market_live["audit"] and _market_live["audit"]["review_event_id"] == _market_live["review"]["event_id"]
assert _market_live["audit"]["review_choice"] == "hold"
assert _market_live["audit"]["mask_id"] == smoke.id
assert _market_live["audit"]["account_id"] != _market_live["review"]["account_id"]
assert _market_live["review"]["mask_id"] == merchant_tester.id
assert _market_live["calibration"]["mask_id"] == smith_tester.id
assert _market_live["attestation"]["mask_id"] == smoke.id
assert not _market_suspended(_market_live, _market_live["day"]), (
    "A Smith's completed physical correction left supplies blocked"
)
for _record, _event_kind in (
    ("review", "village.market_hold"),
    ("calibration", "village.market_calibrate"),
    ("attestation", "village.market_attest"),
    ("audit", "village.market_audit"),
):
    _event = warning_ledger.get_event(_market_live[_record]["event_id"])
    assert _event["kind"] == _event_kind
    assert _event["status"] == "complete"
    assert _event["actor"]["mask_id"] == _market_live[_record]["mask_id"]
assert calling_record(merchant_tester, "merchant")["participation"]["market_hold"] == 1
assert calling_record(smith_tester, "smith")["participation"]["market_calibrate"] == 1
assert calling_record(smoke, "chronicler")["participation"]["market_attest"] == 1
assert calling_record(smoke, "chronicler")["participation"]["market_audit"] == 1
from world.market_standards import verified_merchant_review as _verified_market_review
assert _verified_market_review(
    _market_live["review"], warning_ledger.get_event(_market_live["review"]["event_id"])
)
_market_audit_event = warning_ledger.get_event(_market_live["audit"]["event_id"])
assert _market_audit_event["consequence"]["audit_source_event_id"] == _market_live["review"]["event_id"]
assert _market_audit_event["actor"]["account_id"] != _market_live["review"]["account_id"]
print("POST_RESTART_GDD_EDGE12_DISTINCT_SIGNED_MARKET_AUDIT_GREEN")
from world.market_work import clock as _market_live_clock
_market_now, _market_hour = _market_live_clock()
_market_visible = one("Market Lane").get_display_desc(smoke).lower()
if _market_now == _market_live["day"]:
    assert "physically recalibrated" in _market_visible, (
        "A same-day calibrated market scale is invisible after restart",
        _market_now, _market_live["day"], _market_visible,
    )
elif _market_now > _market_live["day"]:
    assert "market" in _market_visible and "scale" in _market_visible, (
        "The market did not return to its ordinary daily state",
        _market_now, _market_live["day"], _market_visible,
    )
else:
    assert "later village record" in _market_visible, (
        "A backwards clock incorrectly restored earlier market duties",
        _market_now, _market_live["day"], _market_visible,
    )
from world.mystic_circles import normalize as _guild_studies
from world.resident_data import RESIDENT_BY_ID, projection_for
_churchyard = one("St. Lazarus Churchyard")
_guild = _guild_studies(_churchyard.db.mystic_studies)
assert len(_guild["studies"]) == 1, "The Mystic's actual study did not survive restart"
_signed_study = _guild["studies"][0]
assert _signed_study["method"] == "measure"
assert _signed_study["mask"] == "MysticTester"
_mystic_mask = one("MysticTester")
assert active_calling(_mystic_mask) == "mystic"
assert _signed_study["mask_id"] == _mystic_mask.id
assert calling_record(_mystic_mask, "mystic")["participation"]["mystic_grave_studies"] == 1
_mystic_event = warning_ledger.get_event(_signed_study["event_id"])
assert _mystic_event["kind"] == "village.mystic_grave_study"
assert _mystic_event["status"] == "complete"
assert _mystic_event["payload"]["observation_quality"] == "firsthand"
assert _mystic_event["actor"]["mask_id"] == _mystic_mask.id
assert _mystic_event["consequence"]["observed_grave_id"] > 0
for _resident_id in ("beatrice_harcourt", "mirela_dobre"):
    _resident = RESIDENT_BY_ID[_resident_id]
    assert _resident["faction"] == "Guild of Mystics"
    _matching = list(search.search_tag(_resident_id, category="resident_id"))
    assert len(_matching) == 1, "The Mystic guild resident is missing or duplicated"
    assert _matching[0].db.resident_id == _resident_id
assert projection_for("churchyard") == "St. Lazarus Churchyard"
print("POST_RESTART_MYSTIC_GUILD_AND_STUDY_GREEN")


# The real Tavern performance and actual audience survive process restart.
from world.stage_state import normalize as _stage_normalize, public_lines as _stage_lines
_stage_tavern = one("The Blood of the Vine")
_stage = _stage_normalize(_stage_tavern.db.village_stage)
_stage_performer = one("PerformerTester")
assert active_calling(_stage_performer) == "performer"
assert _stage["performance"] is not None, "The performance vanished after restart"
assert _stage["performance"]["mask_id"] == _stage_performer.id
assert _stage["performance"]["tune"] == "ballad"
assert len(_stage["witnesses"]) == 2
assert {w["mask"] for w in _stage["witnesses"]} == {"InnkeepTester", "SmokeTester"}
# GDD T-06: HealerTester left the room before the show, arrived afterward,
# and was refused a firsthand witness record by the ordinary stage command.
# That refusal must not be lost on a real game-server process restart.
assert not any(
    witness.get("mask") == "HealerTester"
    for witness in _stage["witnesses"]
), "A late spectator gained a fabricated firsthand record after restart"
assert calling_record(_stage_performer, "performer")["participation"]["stage_rehearse"] == 1
assert calling_record(_stage_performer, "performer")["participation"]["stage_perform"] == 1
for _action, _entry in (
    ("rehearse", _stage["rehearsals"][0]),
    ("perform", _stage["performance"]),
    ("witness", _stage["witnesses"][0]),
):
    _event = warning_ledger.get_event(_entry["event_id"])
    assert _event["kind"] == "village.stage_" + _action
    assert _event["status"] == "complete"
assert "PerformerTester" in _stage_lines(_stage, _stage["day"])
print("POST_RESTART_SIGNED_TAVERN_PERFORMANCE_GREEN")
print("POST_RESTART_GDD_T06_LATE_NONWITNESS_GREEN")

# GDD-EDGE-14: real stop/start must preserve the separate Chronicler review,
# its signed source acts, and the Performer's attributable contest.
_stage_review = _stage["performance"]["reviews"][0]
_stage_chronicler = one("SmokeTester")
assert active_calling(_stage_chronicler) == "chronicler"
assert _stage_review["mask_id"] == _stage_chronicler.id
assert _stage_review["verdict"] == "praise"
assert _stage_review["contest_event_id"] is not None
_stage_witness = next(w for w in _stage["witnesses"] if w["mask"] == "SmokeTester")
from world.stage_state import verify_review_sources as _verify_review_sources, verify_review_event as _verify_review_event
assert _verify_review_sources(
    _stage["performance"], _stage_witness, {
        "performance": warning_ledger.get_event(_stage["performance"]["event_id"]),
        "rehearsal": warning_ledger.get_event(_stage["performance"]["rehearsal_event_id"]),
        "witness": warning_ledger.get_event(_stage_witness["event_id"]),
    }, day=_stage["day"],
), "The Chronicler review lacks authentic performance and witness sources"
assert _verify_review_event(
    _stage_review, warning_ledger.get_event(_stage_review["event_id"]), _stage["performance"]
), "The review ledger event does not bind its sources"
_stage_contest = warning_ledger.get_event(_stage_review["contest_event_id"])
assert _stage_contest["kind"] == "village.stage_contest"
assert _stage_contest["status"] == "complete"
assert _stage_contest["actor"]["account_id"] == _stage["performance"]["account_id"]
assert _stage_contest["payload"]["review_event_id"] == _stage_review["event_id"]
assert _stage_contest["consequence"]["review_event_id"] == _stage_review["event_id"]
assert "contested by the Performer" in _stage_lines(_stage, _stage["day"])
from world.stage_state import archive_lines as _stage_archive
assert "attributed praise review" in _stage_archive(_stage, _stage["day"])
assert "Performer contested" in _stage_archive(_stage, _stage["day"])
print("POST_RESTART_GDD_EDGE14_SIGNED_REVIEW_CONTEST_GREEN")

# Physical St. Lazarus clinic, signed Healer work and consumed linen persist.
from world.clinic_state import normalize as _clinic_norm, public_lines as _clinic_lines
_church = one("St. Lazarus Church")
_clinic = _clinic_norm(_church.db.village_clinic)
assert _clinic["assessment"] is not None, "Clinical assessment lost on restart"
assert _clinic["treatment"] is not None, "Clinical treatment lost on restart"
assert _clinic["assessment"]["mask"] == "HealerTester"
assert _clinic["treatment"]["mask"] == "HealerTester"
assert _clinic["treatment"]["method"] == "compress"
assert _clinic["linen"] == 3
assert _clinic["treatment"]["assessment_event_id"] == _clinic["assessment"]["event_id"]
assert calling_record(healer_tester, "healer")["participation"]["clinic_assess"] == 1
assert calling_record(healer_tester, "healer")["participation"]["clinic_prepare"] == 1
assert calling_record(healer_tester, "healer")["participation"]["clinic_treat"] == 1
assert not [o for o in healer_tester.contents if o.db.clinic_compress], (
    "The treatment dressing was not consumed from its physical carrier"
)
for _action, _entry in (
    ("assess", _clinic["assessment"]),
    ("treat", _clinic["treatment"]),
):
    _event = warning_ledger.get_event(_entry["event_id"])
    assert _event["kind"] == "village.clinic_" + _action
    assert _event["status"] == "complete"
# GDD T-08: a shared cot and public board do not reveal private case
# details even after a real process restart. Permission is a separate,
# signed, day-scoped fact tied to both account and mask identity.
from world.clinic_state import private_lines as _clinic_private
_clinic_public = _clinic_lines(_clinic, _clinic["day"]).lower()
assert "healertester" not in _clinic_public
assert "cold" not in _clinic_public
assert "used compress" not in _clinic_public
assert "visiting patient" in _clinic_public
assert _clinic["records_permission"]["mask"] == "HealerTester"
assert _clinic["records_permission"]["account_id"] == _clinic["assessment"]["account_id"]
assert _clinic["records_permission"]["mask_id"] == healer_tester.id
_consent_event = warning_ledger.get_event(_clinic["records_permission"]["event_id"])
assert _consent_event["kind"] == "village.clinic_records_permission"
assert _consent_event["status"] == "complete"
_full_clinic = _clinic_private(
    _clinic, _clinic["day"], account_id=_clinic["assessment"]["account_id"],
    mask_id=healer_tester.id,
).lower()
assert "cold" in _full_clinic and "compress" in _full_clinic
assert "healertester" in _full_clinic
_unauthorized_clinic = _clinic_private(
    _clinic, _clinic["day"], account_id=_clinic["assessment"]["account_id"] + 1,
    mask_id=innkeep_tester.id,
).lower()
assert "cold" not in _unauthorized_clinic and "healertester" not in _unauthorized_clinic
assert "permission" in _unauthorized_clinic
from world.clinic_state import refresh as _clinic_refresh
_assert_tomorrow_clinic = _clinic_refresh(_clinic, _clinic["day"] + 1)
assert _assert_tomorrow_clinic["records_permission"] is None
assert len([o for o in _church.contents if o.key == "a clinic treatment cot"]) == 1
# EDGE-25: independently check both signed actors, consumed parcel and
# authoritative cabinet stock after the real Evennia process boundary.
from world import clinic_supply as _clinic_supply
_supply = _clinic["supply"]
assert _supply and _supply["day"] == _clinic["day"]
assert _supply["merchant_account_id"] != _supply["healer_account_id"]
assert _supply["healer_account_id"] == _clinic["assessment"]["account_id"]
assert _supply["merchant_account_id"] == warning_ledger.get_event(
    _supply["source_event_id"])["actor"]["account_id"]
_merchant_event = warning_ledger.get_event(_supply["source_event_id"])
_healer_event = warning_ledger.get_event(_supply["event_id"])
assert _merchant_event["status"] == _healer_event["status"] == "complete"
assert _merchant_event["kind"] == "professional.merchant_clinic_supply"
assert _healer_event["kind"] == "village.clinic_supply_received"
assert _merchant_event["actor"]["mask_id"] == merchant_tester.id
assert _healer_event["actor"]["mask_id"] == healer_tester.id
assert _healer_event["actor"]["account_id"] != _merchant_event["actor"]["account_id"]
assert _healer_event["payload"]["source_merchant_event_id"] == _merchant_event["id"]
assert _healer_event["consequence"]["source_merchant_event_id"] == _merchant_event["id"]
assert _healer_event["consequence"]["consumed_parcel_id"] == _supply["parcel_id"]
assert _merchant_event["consequence"]["parcel_id"] == _supply["parcel_id"]
assert _healer_event["consequence"]["linen_after"] == 3
_market = one("Market Lane")
assert _clinic_supply.stock(_market.db.clinic_linen_stock, _clinic["day"])["remaining"] == 0
assert not [o for o in list(_church.contents) + list(merchant_tester.contents)
            + list(healer_tester.contents) if o.key == "a sealed clinic linen parcel"]
assert calling_record(merchant_tester, "merchant")["participation"]["clinic_supplies_procured"] == 1
assert calling_record(healer_tester, "healer")["participation"]["clinic_supplies_received"] == 1
assert _assert_tomorrow_clinic["supply"] is None
assert _assert_tomorrow_clinic["linen"] == 2
print("POST_RESTART_GDD_EDGE25_SIGNED_DISTINCT_CLINIC_SUPPLY_GREEN")
print("POST_RESTART_PHYSICAL_CLINIC_CARE_GREEN")
print("POST_RESTART_GDD_T08_PRIVATE_CLINIC_PERMISSION_GREEN")

# EDGE-28: original cot, independently authenticated Detective and source
# Healer assessment retain the same verified timeline after a real restart.
from world import clinic_inquiry_state as _clinic_inquiry
_cot = one("a clinic treatment cot")
_detective_clinic = one("DetectiveClinicTester")
assert active_calling(_detective_clinic) == "detective"
_inquiry_records = _clinic_inquiry.normalize(_cot.db.clinic_inquiry)["records"]
assert len(_inquiry_records) == 1, _inquiry_records
_inquiry = _inquiry_records[0]
assert _inquiry["mask_id"] == _detective_clinic.id
assert _inquiry["source_mask_id"] == healer_tester.id
assert _inquiry["account_id"] != _inquiry["source_account_id"]
assert _inquiry["cot_id"] == _cot.id and _inquiry["room_id"] == _church.id
assert _inquiry["source_event_id"] == _clinic["assessment"]["event_id"]
assert _inquiry["interpretation"] == "possible_exposure"
assert _inquiry["alternative"] == "unrelated_illness"
from world.object_properties import is_hidden_mechanical_property as _is_hidden_property
_case_items = [o for o in list(_church.contents) + list(_detective_clinic.contents)
               if o.id == _inquiry["case_item_id"]]
assert len(_case_items) == 1 and _case_items[0].key == "a cluster of mushrooms"
assert _is_hidden_property(_case_items[0], "toxin")
assert _clinic_inquiry.signed_inquiry(_inquiry, warning_ledger.get_event)
_source = warning_ledger.get_event(_inquiry["source_event_id"])
assert _clinic_inquiry.source_valid(_source, _clinic["assessment"], _church.id)
_inquiry_event = warning_ledger.get_event(_inquiry["event_id"])
assert _inquiry_event["kind"] == "village.clinic_inquiry"
assert _inquiry_event["status"] == "complete"
assert _inquiry_event["actor"]["mask_id"] == _detective_clinic.id
assert _inquiry_event["actor"]["account_id"] == _inquiry["account_id"]
assert _inquiry_event["payload"]["source_healer_event_id"] == _source["id"]
assert _inquiry_event["payload"]["case_item_id"] == _inquiry["case_item_id"]
assert _inquiry_event["payload"]["interpretation"] == "possible_exposure"
assert _inquiry_event["payload"]["alternative"] == "unrelated_illness"
assert _inquiry_event["consequence"]["case_item_id"] == _inquiry["case_item_id"]
assert _inquiry_event["consequence"]["causal_status"] == "unproven"
assert _inquiry_event["consequence"]["cot_id"] == _cot.id
assert calling_record(_detective_clinic, "detective")["participation"]["clinic_inquiry"] == 1
_public_inquiry = _clinic_inquiry.public_lines(
    _cot.db.clinic_inquiry, _clinic["day"], event_lookup=warning_ledger.get_event
).lower()
assert "procedural clinic inquiry" in _public_inquiry
assert "competing interpretations" in _public_inquiry
assert "neither causal explanation is proven" in _public_inquiry
assert "cold" not in _public_inquiry and "healertester" not in _public_inquiry
# A missing or forged canonical event cannot be promoted by persisted cot data.
_unverified_inquiry = _clinic_inquiry.public_lines(
    _cot.db.clinic_inquiry, _clinic["day"], event_lookup=lambda _event_id: None
).lower()
assert "requires signed source inspection" in _unverified_inquiry
print("POST_RESTART_GDD_EDGE28_INDEPENDENT_SIGNED_CLINIC_INQUIRY_GREEN")



# Physical courier parcel is consumed only by real Riverside delivery.
from world.courier_state import manifest as _ferry_manifest
_ferry = _ferry_manifest(one("Riverside Path").db.ferry_manifest)
assert len(_ferry["receipts"]) == 1, "Real ferry delivery vanished after restart"
_ferry_receipt = _ferry["receipts"][0]
_wanderer = one("WandererTester")
assert active_calling(_wanderer) == "wanderer"
assert _ferry_receipt["mask"] == "WandererTester"
# An offline mask is no longer puppeted, so `mask.account` is None after
# restart. Match the persisted courier account against the immutable
# signed ledger actor, never a transient live session property.
assert _ferry_receipt["account_id"] == warning_ledger.get_event(
    _ferry_receipt["delivery_event_id"]
)["actor"]["account_id"]
assert calling_record(_wanderer, "wanderer")["participation"]["courier_collections"] == 1
assert calling_record(_wanderer, "wanderer")["participation"]["courier_deliveries"] == 1
assert not [x for x in _wanderer.contents if x.db.ferry_parcel], (
    "An already delivered post parcel remains in the carrier's inventory"
)
for _kind, _eid in (
    ("village.ferry_post_collected", _ferry_receipt["source_event_id"]),
    ("village.ferry_post_delivered", _ferry_receipt["delivery_event_id"]),
):
    _event = warning_ledger.get_event(_eid)
    assert _event["status"] == "complete"
    assert _event["kind"] == _kind
print("POST_RESTART_PHYSICAL_FERRY_POST_GREEN")

# Smith workshop production and Merchant physical custody are durable:
# the consumed item is absent and the Market board still records both
# separately authenticated world events after the true stop/start.
from world import workshop_state as _workshop_rules
_workroom = one("The Market Workshop")
_public_market = one("Market Lane")
_work_docket = _workshop_rules.normalize(_workroom.db.repair_docket)
assert _work_docket["offcuts"] == 1, "Workshop forged stock was replenished on restart"
assert len(_work_docket["crafts"]) == 1
assert _work_docket["installation"] is not None
_repair_craft = _work_docket["crafts"][0]
_repair_install = _work_docket["installation"]
assert _repair_craft["mask"] == "SmithTester"
assert _repair_install["mask"] == "MerchantTester"
assert _repair_install["source_event_id"] == _repair_craft["event_id"]
assert _repair_install["item_id"] == _repair_craft["item_id"]
assert _repair_craft["account_id"] != _repair_install["account_id"]
assert not [x for character in (one("SmithTester"), one("MerchantTester"))
            for x in character.contents if x.db.forged_market_part], (
    "A physically installed hinge remained in inventory after restart"
)
for _kind, _receipt in (
    ("village.market_hinge_forged", _repair_craft),
    ("village.market_hinge_installed", _repair_install),
):
    _event = warning_ledger.get_event(_receipt["event_id"])
    assert _event["kind"] == _kind and _event["status"] == "complete"
    assert _event["actor"]["account_id"] == _receipt["account_id"]
assert calling_record(one("SmithTester"), "smith")["participation"][
    "market_hinges_forged"
] == 1
assert calling_record(one("MerchantTester"), "merchant")["participation"][
    "market_hinges_installed"
] == 1
assert "MerchantTester" in one("a market fittings board").get_display_desc()
assert "1 of 2 iron offcuts" in one("a public smithing bench").get_display_desc()
assert _public_market in [e.destination for e in _workroom.exits]
_next_repair = _workshop_rules.refresh(_work_docket, _work_docket["day"] + 1)
assert _next_repair["offcuts"] == _workshop_rules.DAILY_OFFCUTS
assert _next_repair["installation"] is None
assert _next_repair["history"][-1]["installation"]["mask"] == "MerchantTester"
print("POST_RESTART_TWO_ACCOUNT_MARKET_WORKSHOP_GREEN")



print("POST_RESTART_MARKET_CALLINGS_ASSERTIONS_GREEN")


from world.bridge_choices import normalize as _bridge_state, public_line as _bridge_line
_bridge = one("The Old Stone Bridge")
_bridge_public = _bridge_state(_bridge.db.bridge_inquiry)
_bridge_owner = next((account for account in AccountDB.objects.all()
                      if any(char.id == smoke.id for char in account.characters.all())), None)
assert _bridge_owner is not None, "Owning account not found after disconnect"
_bridge_decision = _bridge_public["resolution"]
assert _bridge_decision is not None, "Bridge physical change lost after restart"
assert _bridge_decision["choice"] == "preserve"
assert _bridge_decision["mask_id"] == smoke.id
assert _bridge_decision["account_id"] == _bridge_owner.id
assert len(_bridge_public["checks"]) == 1, "Bridge upkeep duplicated or vanished"
assert _bridge_public["checks"][0]["account_id"] == _bridge_owner.id
_bridge_event = warning_ledger.get_event(_bridge_decision["event_id"])
assert _bridge_event["kind"] == "village.bridge_response"
assert _bridge_event["status"] == "complete"
assert _bridge_event["payload"]["choice"] == "preserve"
_check_event = warning_ledger.get_event(_bridge_public["checks"][0]["event_id"])
assert _check_event["kind"] == "village.bridge_upkeep"
assert _check_event["status"] == "complete"
assert "canvas cover" in _bridge_line(_bridge_public)
assert "canvas cover" in _bridge.get_display_desc(smoke), (
    "Other visitors cannot see the settled physical world response"
)
from world.bridge_materials import normalize as _market_material_stock
_market = one("Market Lane")
_material_tables = [obj for obj in _market.contents
                    if obj.key == "a civic material table"]
assert len(_material_tables) == 1, "Market supply table was lost or duplicated"
_materials = _market_material_stock(
    _material_tables[0].db.bridge_material_stock,
    _bridge_decision["day"],
)
assert _materials["remaining"]["preserve"] == 1, (
    "Market kit stock was refilled or its withdrawal did not persist"
)
assert _materials["remaining"]["display"] == 2
assert not [obj for obj in smoke.contents
            if obj.db.bridge_material in {"preserve", "display"}], (
    "Consumed bridge construction kit still exists in inventory"
)
_material_consumption = _bridge_event["consequence"]
assert _material_consumption["consumed_item_id"] > 0
_material_origin = warning_ledger.get_event(
    _material_consumption["source_event_id"]
)
assert _material_origin["kind"] == "village.bridge_material_collected"
assert _material_origin["status"] == "complete"
assert _material_origin["actor"]["mask_id"] == smoke.id
assert _material_origin["consequence"]["item_id"] == (
    _material_consumption["consumed_item_id"]
)
assert not search.search_object(
    "a canvas preservation kit"
), "The consumed kit still exists as a free object"
print("POST_RESTART_PHYSICAL_BRIDGE_MATERIALS_GREEN")

print("POST_RESTART_BRIDGE_RESPONSE_GREEN")


print("POST_RESTART_COMMONS_ASSERTIONS_GREEN")
