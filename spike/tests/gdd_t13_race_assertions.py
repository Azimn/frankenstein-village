"""Verify a two-socket race against actual Evennia objects and signed events.

Run once after disconnect and once after a genuine server restart. Read-only.
A client send barrier is not proof of parallel server execution, so this gate
checks exactly-once consequences without claiming a database stress test.
"""
import os
from evennia.accounts.models import AccountDB
from evennia.objects.models import ObjectDB
from evennia.scripts.models import ScriptDB
from evennia.utils import search
from world import civic_commissions, hearth_state


def one(key):
    found = [obj for obj in search.search_object(key) if obj.key == key]
    assert len(found) == 1, (key, len(found))
    return found[0]


assert not any(a.is_connected for a in AccountDB.objects.all())
tavern = one("The Blood of the Vine")
supplier = AccountDB.objects.get(username="qa_smith_repair")
carrier = AccountDB.objects.get(username="qa_merchant_repair")
assert supplier.id != carrier.id
clock = ScriptDB.objects.get(db_key="village_time")
assert int(clock.db.day or 1) == 3
state = civic_commissions.normalize(tavern.db.civic_commission)
item = state["commission"]
assert state["day"] == 3 and item["id"] == "civic-3", item
assert item["supplier_account"] == supplier.id
assert item["status"] in {"cancelled", "complete"}, item
assert len(item["event_ids"]) == 2, item
assert len([h for h in state["history"] if h["id"] == "civic-3"]) == 1
assert [h for h in state["history"] if h["id"] == "civic-3"][0] == item
assert civic_commissions.refresh(state, 3) == state

ledger = ScriptDB.objects.get(db_key="world_event_ledger")
pledge = ledger.get_event(item["event_ids"][0])
terminal = ledger.get_event(item["event_ids"][1])
assert pledge["kind"] == "civic.commission_pledged"
assert pledge["status"] == terminal["status"] == "complete"
assert pledge["actor"]["account_id"] == supplier.id
assert pledge["consequence"]["bundle_id"] == item["bundle_id"]
assert terminal["payload"]["bundle_id"] == item["bundle_id"]
events = list(ledger.db.events or [])
terminal_events = [
    e for e in events
    if e.get("kind") in {"civic.commission_cancelled", "civic.commission_completed"}
    and e.get("payload", {}).get("bundle_id") == item["bundle_id"]
    and e.get("status") == "complete"
]
assert len(terminal_events) == 1, terminal_events
assert terminal_events[0]["id"] == item["event_ids"][1]

initial_reserve = tavern.db.qa_t13_race_initial_reserve
assert isinstance(initial_reserve, int)
reserve = hearth_state.hearth(tavern.db.civic_hearth)["reserve"]
physical = ObjectDB.objects.filter(id=item["bundle_id"]).first()
if item["status"] == "cancelled":
    assert terminal["kind"] == "civic.commission_cancelled"
    assert terminal["actor"]["account_id"] == supplier.id
    assert terminal["consequence"]["physical_bundle_retained"] is True
    assert item["finisher_account"] is None
    assert physical is not None and physical.location is not None
    assert physical.location.key == "MerchantTester", physical
    assert physical.db.civic_firewood is True
    assert reserve == initial_reserve, (reserve, initial_reserve)
else:
    assert terminal["kind"] == "civic.commission_completed"
    assert terminal["actor"]["account_id"] == carrier.id
    assert item["finisher_account"] == carrier.id
    assert physical is None, "Completed delivery left a duplicate physical bundle"
    assert reserve == initial_reserve + 1, (reserve, initial_reserve)
print(
    "POST_RESTART_GDD_T13_TWO_SOCKET_RACE_CONSERVATION_GREEN"
    if os.environ.get("FV_T13_RACE_RESTART") == "1"
    else "GDD_T13_TWO_SOCKET_RACE_CONSERVATION_GREEN"
)
