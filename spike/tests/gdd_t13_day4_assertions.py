"""Read-only T-13 next-day recovery and real restart conservation checks.

The day-four pledge and cancellation are made by a logged-in player over
telnet, never by this shell. Run again after an actual Evennia restart.
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


assert not any(account.is_connected for account in AccountDB.objects.all())
clock = ScriptDB.objects.get(db_key="village_time")
assert int(clock.db.day or 1) == 4
tavern = one("The Blood of the Vine")
ledger = ScriptDB.objects.get(db_key="world_event_ledger")
supplier = AccountDB.objects.get(username="qa_smith_repair")
carrier = AccountDB.objects.get(username="qa_merchant_repair")
assert supplier.id != carrier.id

state = civic_commissions.normalize(tavern.db.civic_commission)
item = state["commission"]
assert state["day"] == 4 and item["id"] == "civic-4"
assert item["status"] == "cancelled", item
assert item["supplier_account"] == supplier.id
assert item["finisher_account"] is None
assert len(item["event_ids"]) == 2
assert civic_commissions.refresh(state, 4) == state
for day in (2, 3, 4):
    matches = [record for record in state["history"] if record["id"] == f"civic-{day}"]
    assert len(matches) == 1, (day, matches)
    assert matches[0]["status"] in {"cancelled", "complete"}
assert [record for record in state["history"] if record["id"] == "civic-4"][0] == item

previous = [record for record in state["history"] if record["id"] == "civic-3"][0]
assert previous["bundle_id"] != item["bundle_id"]
assert previous["status"] in {"cancelled", "complete"}
assert len(previous["event_ids"]) == 2
previous_terminal = ledger.get_event(previous["event_ids"][1])
assert previous_terminal["kind"] == (
    "civic.commission_cancelled" if previous["status"] == "cancelled"
    else "civic.commission_completed"
)
assert previous_terminal["status"] == "complete"
previous_object = ObjectDB.objects.filter(id=previous["bundle_id"]).first()
if previous["status"] == "cancelled":
    assert previous_object is not None
    assert previous_object.location is not None
    assert previous_object.location.key == "MerchantTester"
else:
    assert previous_object is None

pledge = ledger.get_event(item["event_ids"][0])
cancel = ledger.get_event(item["event_ids"][1])
assert pledge["kind"] == "civic.commission_pledged"
assert cancel["kind"] == "civic.commission_cancelled"
assert pledge["status"] == cancel["status"] == "complete"
assert pledge["actor"]["account_id"] == cancel["actor"]["account_id"] == supplier.id
assert pledge["consequence"]["bundle_id"] == item["bundle_id"]
assert cancel["consequence"]["physical_bundle_retained"] is True
events = list(ledger.db.events or [])
terminal = [
    event for event in events
    if event.get("kind") in {"civic.commission_cancelled", "civic.commission_completed"}
    and event.get("payload", {}).get("bundle_id") == item["bundle_id"]
    and event.get("status") == "complete"
]
assert len(terminal) == 1 and terminal[0]["id"] == item["event_ids"][1]
physical = ObjectDB.objects.filter(id=item["bundle_id"]).first()
assert physical is not None and physical.location is not None
assert physical.location.key == "SmithTester"
assert physical.db.civic_firewood is True
assert int(physical.db.source_day) == 4
reserve = hearth_state.hearth(tavern.db.civic_hearth)["reserve"]
assert reserve == tavern.db.qa_t13_day4_initial_reserve

print(
    "POST_RESTART_GDD_T13_NEXT_DAY_RECOVERY_GREEN"
    if os.environ.get("FV_T13_DAY4_RESTART") == "1"
    else "GDD_T13_NEXT_DAY_RECOVERY_GREEN"
)
