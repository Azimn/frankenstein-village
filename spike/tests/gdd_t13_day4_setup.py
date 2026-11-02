"""Prepare a next-day T-13 recovery after the contested day-three terminal action.

Only the disposable QA clock and test markers change here. The new order
must be opened and cancelled through an authenticated ordinary player client.
"""
from evennia.accounts.models import AccountDB
from evennia.scripts.models import ScriptDB
from evennia.utils import search
from world import civic_commissions, hearth_state, community_hearth


def one(key):
    found = [obj for obj in search.search_object(key) if obj.key == key]
    assert len(found) == 1, (key, len(found))
    return found[0]


assert not any(account.is_connected for account in AccountDB.objects.all())
clock = ScriptDB.objects.get(db_key="village_time")
assert int(clock.db.day or 1) == 3
tavern = one("The Blood of the Vine")
supplier = one("SmithTester")
square = one("Village Square")
woodpile = one(community_hearth.WOODPILE_KEY)
prior = civic_commissions.normalize(tavern.db.civic_commission)
old = prior["commission"]
assert old["id"] == "civic-3" and old["status"] in {"cancelled", "complete"}
assert len([record for record in prior["history"] if record["id"] == "civic-3"]) == 1
assert not any(
    obj.key == community_hearth.FIREWOOD_KEY and obj.db.civic_firewood is True
    for obj in supplier.contents
), "Supplier unexpectedly retained the handed-off day-three bundle"
assert hearth_state.source(woodpile.db.civic_wood, 4)["remaining"] > 0
assert supplier.move_to(square, quiet=True)
tavern.db.qa_t13_day4_initial_reserve = hearth_state.hearth(
    tavern.db.civic_hearth
)["reserve"]
clock.db.day = 4
clock.db.hour = 21
print("GDD_T13_NEXT_DAY_AUTHENTICATED_RECOVERY_READY")
