"""Prepare a real two-socket cancel-versus-deliver race on day three.

This touches only the disposable clean-checkout QA database. The server is
stopped. No gameplay call is made on a mask without an authenticated session.
"""
from evennia.scripts.models import ScriptDB
from evennia.utils import search
from world import civic_commissions, hearth_state, community_hearth


def one(key):
    found = [obj for obj in search.search_object(key) if obj.key == key]
    assert len(found) == 1, (key, len(found))
    return found[0]


supplier = one("SmithTester")
carrier = one("MerchantTester")
square = one("Village Square")
tavern = one("The Blood of the Vine")
clock = ScriptDB.objects.get(db_key="village_time")
assert int(clock.db.day or 1) == 2
previous = civic_commissions.normalize(tavern.db.civic_commission)
assert previous["commission"]["status"] == "cancelled"
assert previous["commission"]["id"] == "civic-2"
assert not any(
    obj.key == community_hearth.FIREWOOD_KEY and obj.db.civic_firewood is True
    for obj in supplier.contents + carrier.contents
)
reserve = hearth_state.hearth(tavern.db.civic_hearth)["reserve"]
assert reserve < hearth_state.MAX_RESERVE, reserve
clock.db.day = 3
clock.db.hour = 21
assert supplier.move_to(square, quiet=True)
assert carrier.move_to(tavern, quiet=True)
tavern.db.qa_t13_race_initial_reserve = reserve
print("GDD_T13_TWO_SOCKET_RACE_DAY_THREE_READY")
