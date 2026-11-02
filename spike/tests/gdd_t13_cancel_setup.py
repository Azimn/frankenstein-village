"""Prepare the disposable QA village for a day-two, authenticated T-13 test.

Do not bypass world-service login guards by invoking gameplay on offline masks.
The following player actions are performed over two real telnet connections.
"""
from evennia.scripts.models import ScriptDB
from evennia.utils import search
from world import hearth_state, community_hearth, civic_commissions

def one(key):
    found = [o for o in search.search_object(key) if o.key == key]
    assert len(found) == 1, (key, len(found))
    return found[0]

supplier = one("SmithTester")
carrier = one("MerchantTester")
square = one("Village Square")
tavern = one("The Blood of the Vine")
clock = ScriptDB.objects.get(db_key="village_time")
assert int(clock.db.day or 1) == 1
assert not any(
    obj.key == community_hearth.FIREWOOD_KEY and obj.db.civic_firewood is True
    for obj in supplier.contents + carrier.contents
)
old = civic_commissions.normalize(tavern.db.civic_commission)
assert old["commission"]["status"] == "complete"
clock.db.day = 2
clock.db.hour = 21
assert supplier.move_to(square, quiet=True)
assert carrier.move_to(tavern, quiet=True)
before = hearth_state.hearth(tavern.db.civic_hearth)["reserve"]
assert before < hearth_state.MAX_RESERVE
# This marker is only written in the disposable QA database.
tavern.db.qa_t13_initial_reserve = before
print("GDD_T13_DAY_TWO_AUTHENTICATED_SCENARIO_READY")
