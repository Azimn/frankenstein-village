"""GDD T-12: unattended village-wide incident reaches an honest expiry.

Executed in a clean-checkout QA database through the real Evennia shell,
AFTER a real server restart and existing post-restart assertions. The server
is stopped, so no player can intervene. This is a scripted integration gate,
not an uncoached player or production soak certificate.
"""

from evennia.accounts.models import AccountDB
from evennia.scripts.models import ScriptDB
from world import server_events

# The Evennia server is stopped at this point in run_all.py. Confirm that the
# scenario is actually unattended rather than silently ignoring active players.
assert not any(account.is_connected for account in AccountDB.objects.all()), (
    "T-12 test requires zero connected player accounts"
)

stable_id = server_events.LONG_BLACKOUT_ID
registry = server_events.get_server_event_registry()
assert ScriptDB.objects.filter(db_key="server_event_registry").count() == 1

# Settle the earlier telnet scenario in this disposable QA database, without
# changing its receipts. A distant scheduled day exercises the actual 28-day clock trigger.
preparation = server_events.advance_server_events(day=1018, hour=18)
assert server_events.get_server_event(stable_id)["state"] == "dormant", preparation

before = server_events.get_server_event(stable_id)
previous_occurrences = int(before.get("occurrence_count") or 0)
trigger = server_events.advance_server_events(day=1018, hour=19)
assert trigger["started"] == [stable_id], trigger
started = server_events.get_server_event(stable_id)
assert started and started["state"] == "active"
duplicate_start = server_events.advance_server_events(day=1018, hour=19)
assert stable_id not in duplicate_start["started"], duplicate_start
current = started["current"]
assert current["occurrence"] == previous_occurrences + 1
assert current["responses"] == {} and current["contributors"] == {}
assert (current["end_day"], current["end_hour"]) == (1019, 7)
start_event_id = current["start_event_id"]
assert start_event_id

# Before expiry, the blackout must remain active without a forged player.
early = server_events.advance_server_events(day=1019, hour=6)
assert stable_id not in early["resolved"]
assert server_events.get_server_event(stable_id)["state"] == "active"

due = server_events.advance_server_events(day=1019, hour=7)
assert due["resolved"] == [stable_id], due
aftermath = server_events.get_server_event(stable_id)
assert aftermath["state"] == "aftermath"
result = aftermath["current"]
outcome = result["outcome"]
assert outcome["quality"] == "rough", outcome
assert outcome["completed_response_count"] == 0
assert outcome["completed_responses"] == []
assert result["responses"] == {} and result["contributors"] == {}
assert result["end_event_id"] and result["end_event_id"] != start_event_id
assert (result["aftermath_until_day"], result["aftermath_until_hour"]) == (1019, 13)

ledger = ScriptDB.objects.get(db_key="world_event_ledger")
start_receipt = ledger.get_event(start_event_id)
end_receipt = ledger.get_event(result["end_event_id"])
assert start_receipt["kind"] == "server.long_blackout.started"
assert end_receipt["kind"] == "server.long_blackout.ended"
assert end_receipt["payload"]["outcome_quality"] == "rough"
assert end_receipt["payload"]["completed_responses"] == []
assert not end_receipt.get("actor"), "An unattended event invented a player actor"

# Idempotent replay of the same boundary cannot mint another ending.
repeated = server_events.advance_server_events(day=1019, hour=7)
assert stable_id not in repeated["resolved"], repeated
assert server_events.get_server_event(stable_id)["current"]["end_event_id"] == result["end_event_id"]

expired = server_events.advance_server_events(day=1019, hour=13)
assert expired["cleared"] == [stable_id], expired
final = server_events.get_server_event(stable_id)
assert final["state"] == "dormant" and final["current"] is None
matching = [
    item for item in final["history"]
    if item.get("occurrence") == current["occurrence"]
]
assert len(matching) == 1, "T-12 unattended incident duplicated its history"
assert matching[0]["end_event_id"] == result["end_event_id"]
assert matching[0]["outcome"]["quality"] == "rough"
again = server_events.advance_server_events(day=1019, hour=13)
assert stable_id not in again["cleared"] and stable_id not in again["started"]
assert server_events.get_server_event(stable_id)["history"] == final["history"]
print("GDD_T12_UNATTENDED_BLACKOUT_EXPIRY_GREEN")
