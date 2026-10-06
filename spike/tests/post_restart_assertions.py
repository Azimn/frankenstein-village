"""Assertions run after the player telnet pass and a real server restart."""

from evennia.scripts.models import ScriptDB
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
print("POST_RESTART_SCHEDULED_EVENT_ASSERTIONS_GREEN")
