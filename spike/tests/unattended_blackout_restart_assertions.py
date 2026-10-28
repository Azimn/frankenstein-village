"""GDD T-12: unattended incident receipts survive another real server restart.

Runs against the disposable clean-checkout Evennia database after the incident
has expired, the server has stopped, and a second server start/stop completed.
This checks persistence, not an uncoached player experience or production soak.
"""

from evennia.accounts.models import AccountDB
from evennia.scripts.models import ScriptDB
from world import server_events

assert not any(account.is_connected for account in AccountDB.objects.all()), (
    "T-12 restart verification requires zero connected player accounts"
)
stable_id = server_events.LONG_BLACKOUT_ID
assert ScriptDB.objects.filter(db_key="server_event_registry").count() == 1
event = server_events.get_server_event(stable_id)
assert event is not None
assert event["state"] == "dormant" and event["current"] is None, event
history = list(event["history"])
assert history, "Blackout resolution disappeared after restart"
occurrence = int(event["occurrence_count"])
matching = [item for item in history if int(item["occurrence"]) == occurrence]
assert len(matching) == 1, "Blackout resolution was duplicated or lost"
resolved = matching[0]
assert resolved["outcome"]["quality"] == "rough", resolved
assert resolved["outcome"]["completed_response_count"] == 0
assert resolved["outcome"]["completed_responses"] == []
assert resolved["responses"] == {} and resolved["contributors"] == {}
assert resolved["start_event_id"] and resolved["end_event_id"]
assert resolved["start_event_id"] != resolved["end_event_id"]

ledger = ScriptDB.objects.get(db_key="world_event_ledger")
start = ledger.get_event(resolved["start_event_id"])
end = ledger.get_event(resolved["end_event_id"])
assert start["kind"] == "server.long_blackout.started"
assert end["kind"] == "server.long_blackout.ended"
assert end["payload"]["outcome_quality"] == "rough"
assert end["payload"]["completed_responses"] == []
assert not end.get("actor"), "Restart invented a player contributor"

# Re-reading after restart must not rewrite the archived outcome or start a
# second incident. No artificial clock advance is needed for this assertion.
assert server_events.get_server_event(stable_id)["history"] == history
assert ScriptDB.objects.filter(db_key="server_event_registry").count() == 1

# The event is over. Restart must not resurrect any of its temporary room
# descriptions, even while unrelated scheduled overlays remain untouched.
# This is a player-visible world-state invariant, not just ledger persistence.
from evennia.utils import search
definition = server_events.DEFINITIONS[stable_id]
active_overlay_id = f"{stable_id}:active"
aftermath_overlay_id = f"{stable_id}:aftermath"
affected_rooms = set(definition["active_overlays"]) | set(definition["aftermath_overlays"])
assert affected_rooms, "T-12 needs actual public locations to verify"
for room_key in sorted(affected_rooms):
    matches = [room for room in search.search_object(room_key) if room.key == room_key]
    assert len(matches) == 1, f"T-12 expected one real room: {room_key}"
    overlays = dict(matches[0].db.scheduled_overlays or {})
    assert active_overlay_id not in overlays, (
        f"Expired blackout still appears active in {room_key}"
    )
    assert aftermath_overlay_id not in overlays, (
        f"Expired blackout aftermath still appears in {room_key}"
    )

# Reconciliation after restart must be idempotent. It must not recreate
# cleared blackout overlays or require a player to dismiss the incident.
assert server_events.reconcile_server_event_overlays() == 0
assert server_events.status_lines() == ["No village-wide emergency is active."]
print("GDD_T12_UNATTENDED_BLACKOUT_OVERLAY_CLEANUP_GREEN")
print("GDD_T12_UNATTENDED_BLACKOUT_RESTART_PERSISTENCE_GREEN")
