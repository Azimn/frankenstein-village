"""GDD T-13: actual Evennia objects survive a cancelled supplier order.

Runs only in the disposable clean-checkout QA database, after the existing
day-one telnet scenario and its first real process restart. This is a
two-account world-service integration test, not a simultaneous socket race.
"""
from evennia.scripts.models import ScriptDB
from evennia.utils import search
from evennia.objects.models import ObjectDB
from world import civic_commissions, civic_work, community_hearth, hearth_state


def one(key):
    found = [obj for obj in search.search_object(key) if obj.key == key]
    assert len(found) == 1, (key, len(found))
    return found[0]


supplier = one("SmithTester")
carrier = one("MerchantTester")
square = one("Village Square")
tavern = one("The Blood of the Vine")
clock = ScriptDB.objects.get(db_key="village_time")
ledger = ScriptDB.objects.get(db_key="world_event_ledger")

assert supplier.account and carrier.account
assert supplier.account.id != carrier.account.id
assert int(clock.db.day or 1) == 1, "T-13 QA starts after day-one play"
assert not any(
    o.key == community_hearth.FIREWOOD_KEY and o.db.civic_firewood is True
    for o in supplier.contents + carrier.contents
), "Earlier test left a physical firewood bundle in a test player's hands"

# The server is stopped. Advance only the existing QA village clock to the
# next day, preserving the earlier completed order and its signed receipts.
clock.db.day = 2
clock.db.hour = 21
assert supplier.move_to(square, quiet=True)
assert carrier.move_to(tavern, quiet=True)
before = hearth_state.hearth(tavern.db.civic_hearth)["reserve"]
assert before < hearth_state.MAX_RESERVE

gathered, error = community_hearth.gather(supplier)
assert gathered and not error, error
bundles = [
    obj for obj in supplier.contents
    if obj.key == community_hearth.FIREWOOD_KEY
    and obj.db.civic_firewood is True
]
assert len(bundles) == 1, bundles
bundle = bundles[0]
bundle_id = bundle.id
gather_id = bundle.db.gather_event_id

pledged, error = civic_work.pledge(supplier)
assert pledged and not error, error
assert pledged["bundle_id"] == bundle_id
assert bundle.move_to(carrier, quiet=True), "Physical handoff failed"
assert bundle.location == carrier

# The carrier cannot cancel the supplier's signed work order.
rejected, error = civic_work.cancel(carrier)
assert rejected is None and "original supplier" in error.lower(), error

cancelled, error = civic_work.cancel(supplier)
assert cancelled and not error, error
state = civic_commissions.normalize(tavern.db.civic_commission)
item = state["commission"]
assert state["day"] == 2 and item["status"] == "cancelled"
assert item["supplier_account"] == supplier.account.id
assert item["bundle_id"] == bundle_id
assert len(item["event_ids"]) == 2
assert len([h for h in state["history"] if h["id"] == "civic-2"]) == 1
assert hearth_state.hearth(tavern.db.civic_hearth)["reserve"] == before
assert bundle.location == carrier, "Cancellation confiscated physical wood"
assert ObjectDB.objects.filter(id=bundle_id).exists()

# The now-cancelled commission cannot consume the same item, but the
# ordinary physical hearth delivery remains a valid recovery path.
rejected, error = civic_work.deliver(carrier)
assert rejected is None and error, (rejected, error)
assert hearth_state.hearth(tavern.db.civic_hearth)["reserve"] == before
delivered, error = community_hearth.deliver(carrier)
assert delivered and not error, error
assert hearth_state.hearth(tavern.db.civic_hearth)["reserve"] == before + 1
assert not ObjectDB.objects.filter(id=bundle_id).exists()

events = list(ledger.db.events or [])
def matching(kind):
    return [
        event for event in events
        if event.get("kind") == kind
        and event.get("payload", {}).get("bundle_id") == bundle_id
    ]

assert len(matching("civic.commission_pledged")) == 1
assert len(matching("civic.commission_cancelled")) == 1
assert not matching("civic.commission_completed")
for event_id in item["event_ids"]:
    assert ledger.get_event(event_id)["status"] == "complete"
cancel_event = ledger.get_event(item["event_ids"][-1])
assert cancel_event["actor"]["account_id"] == supplier.account.id
assert cancel_event["consequence"]["physical_bundle_retained"] is True
assert delivered["event_id"] != item["event_ids"][-1]
assert ledger.get_event(delivered["event_id"])["payload"]["gather_event_id"] == gather_id
print("GDD_T13_CANCEL_BEFORE_DELIVER_REAL_OBJECT_CONSERVATION_GREEN")
