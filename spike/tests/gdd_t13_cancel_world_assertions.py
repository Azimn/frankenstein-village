"""Verify authenticated T-13 actions after the live two-account telnet pass.

Read only: the actual game commands ran while both accounts were connected.
This shell must not manufacture a session to bypass the production guards.
"""
from evennia.accounts.models import AccountDB
from evennia.scripts.models import ScriptDB
from evennia.objects.models import ObjectDB
from evennia.utils import search
from world import civic_commissions, hearth_state

def one(key):
    found = [obj for obj in search.search_object(key) if obj.key == key]
    assert len(found) == 1, (key, len(found))
    return found[0]

tavern = one("The Blood of the Vine")
supplier = AccountDB.objects.get(username="qa_smith_repair")
carrier = AccountDB.objects.get(username="qa_merchant_repair")
assert supplier.id != carrier.id
ledger = ScriptDB.objects.get(db_key="world_event_ledger")
state = civic_commissions.normalize(tavern.db.civic_commission)
item = state["commission"]
assert state["day"] == 2 and item["id"] == "civic-2"
assert item["status"] == "cancelled", item
assert item["supplier_account"] == supplier.id
assert item["finisher_account"] is None
assert len(item["event_ids"]) == 2
assert len([h for h in state["history"] if h["id"] == "civic-2"]) == 1
assert not ObjectDB.objects.filter(id=item["bundle_id"]).exists()
before = tavern.db.qa_t13_initial_reserve
assert isinstance(before, int)
assert hearth_state.hearth(tavern.db.civic_hearth)["reserve"] == before + 1

pledge = ledger.get_event(item["event_ids"][0])
cancel = ledger.get_event(item["event_ids"][1])
assert pledge["kind"] == "civic.commission_pledged"
assert cancel["kind"] == "civic.commission_cancelled"
assert pledge["status"] == cancel["status"] == "complete"
assert pledge["actor"]["account_id"] == cancel["actor"]["account_id"] == supplier.id
assert cancel["consequence"]["physical_bundle_retained"] is True
assert cancel["consequence"]["bundle_id"] == item["bundle_id"]
gather_id = pledge["consequence"]["source_event_id"]
events = list(ledger.db.events or [])
def matching(kind):
    return [e for e in events if e.get("kind") == kind and
            e.get("payload", {}).get("bundle_id") == item["bundle_id"]]
assert len(matching("civic.commission_pledged")) == 1
assert len(matching("civic.commission_cancelled")) == 1
assert not matching("civic.commission_completed")
recovery = [e for e in events if
            e.get("kind") == "civic.hearth_firewood_delivered" and
            e.get("payload", {}).get("gather_event_id") == gather_id]
assert len(recovery) == 1, recovery
assert recovery[0]["status"] == "complete"
assert recovery[0]["actor"]["account_id"] == carrier.id
assert recovery[0]["consequence"]["reserve"] == before + 1
print("GDD_T13_CANCEL_BEFORE_DELIVER_REAL_OBJECT_CONSERVATION_GREEN")
