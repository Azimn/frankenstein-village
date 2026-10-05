"""Assertions run after the player telnet pass and a real server restart."""

from evennia.utils import search

from world.residents import facts_known_by_player, resident_state
from world.situations import (
    TITHE_ID,
    TORN_CHRONICLE_ID,
    get_situation,
    situation_status_for_player,
)
from world.publications import (
    chronicle_entries,
    edition_stories,
    latest_edition,
)
from world.timed_incidents import (
    WELL_BOILS_ID,
    advance_timed_incidents,
    get_timed_incident,
    status_for_player as timed_status_for_player,
)


def one(key):
    found = [obj for obj in search.search_object(key) if obj.key == key]
    assert len(found) == 1, (key, len(found))
    return found[0]


miklos = one("Miklós Farkas")
smoke = one("SmokeTester")
state = resident_state(miklos)
relation = (state.get("relationships") or {}).get(str(smoke.id))
assert relation, "telnet interactions did not persist a Miklós relationship"
assert relation["familiarity"] >= 8
assert state["character_depth"] in {"C", "B", "A"}
assert state["simulation_resolution"] in {"reactive", "engaged", "focused"}
assert state["facts"], "history question did not persist progressive characterization"
known = facts_known_by_player(miklos, smoke)
assert known, "revealed fact was not recorded for the player mask"

population = list(search.search_tag("resident", category="system"))
assert len(population) == 36, "resident population changed across restart"

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

print("POST_RESTART_RESIDENT_ASSERTIONS_GREEN")
print("POST_RESTART_PUBLIC_RECORD_ASSERTIONS_GREEN")
print("POST_RESTART_SITUATION_ASSERTIONS_GREEN")
print("POST_RESTART_INCIDENT_FEED_ASSERTIONS_GREEN")
print("POST_RESTART_TIMED_INCIDENT_ASSERTIONS_GREEN")
