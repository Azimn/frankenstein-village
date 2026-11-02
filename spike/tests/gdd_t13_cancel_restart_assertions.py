"""GDD T-13: cancelled order and physical recovery survive server restart.

Runs in the same disposable QA database after a real second Evennia
server start/stop, with no connected player. No LLM or live-world writes.
"""
from evennia.scripts.models import ScriptDB
from evennia.utils import search
from evennia.objects.models import ObjectDB
from world import civic_commissions, hearth_state


def one(key):
    found = [obj for obj in search.search_object(key) if obj.key == key]
    assert len(found) == 1, (key, len(found))
    return found[0]


tavern = one("The Blood of the Vine")
ledger = ScriptDB.objects.get(db_key="world_event_ledger")
state = civic_commissions.normalize(tavern.db.civic_commission)
item = state["commission"]
assert state["day"] == 2 and item["id"] == "civic-2"
assert item["status"] == "cancelled", item
assert item["finisher_account"] is None
assert len(item["event_ids"]) == 2
history = [record for record in state["history"] if record["id"] == "civic-2"]
assert len(history) == 1 and history[0] == item
assert not ObjectDB.objects.filter(id=item["bundle_id"]).exists(), (
    "Cancelled order's physical wood reappeared after ordinary delivery"
)
pledge = ledger.get_event(item["event_ids"][0])
cancel = ledger.get_event(item["event_ids"][1])
assert pledge["kind"] == "civic.commission_pledged"
assert cancel["kind"] == "civic.commission_cancelled"
assert pledge["status"] == cancel["status"] == "complete"
assert pledge["actor"]["account_id"] == cancel["actor"]["account_id"]
assert pledge["actor"]["account_id"] == item["supplier_account"]
assert cancel["consequence"]["physical_bundle_retained"] is True
assert cancel["consequence"]["bundle_id"] == item["bundle_id"]

events = list(ledger.db.events or [])
completed = [
    e for e in events if e.get("kind") == "civic.commission_completed"
    and e.get("payload", {}).get("bundle_id") == item["bundle_id"]
]
recovered = [
    e for e in events if e.get("kind") == "civic.hearth_firewood_delivered"
    and e.get("payload", {}).get("gather_event_id") == (
        pledge["payload"].get("source_event_id")
        or next(
            (e.get("id") for e in events
             if e.get("kind") == "civic.hearth_firewood_gathered"
             and e.get("consequence", {}).get("bundle_id") == item["bundle_id"]),
            None,
        )
    )
]
assert not completed, completed
assert len(recovered) == 1 and recovered[0]["status"] == "complete", recovered
assert recovered[0]["actor"]["account_id"] != item["supplier_account"]
assert recovered[0]["consequence"]["reserve"] == (
    hearth_state.hearth(tavern.db.civic_hearth)["reserve"]
), "Restart changed the conserved hearth reserve"
print("POST_RESTART_GDD_T13_CANCELLED_ORDER_AND_RECOVERED_WOOD_GREEN")
