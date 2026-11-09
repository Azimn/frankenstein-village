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
# Clock-rollover tolerance (harness fix, 2026-11-08): earlier suite phases
# keep the server running long enough that the village clock — which starts
# on day 1 at hour 21 — can legitimately roll to day 2 on its own before
# this setup runs. That rollover is harmless here: midnight only advances
# the clock fields. The stored day-one commission is not rewritten at
# rollover (civic_commissions.normalize is day-agnostic; refresh() applies
# the day change lazily at gameplay reads), no firewood is handed to the
# testers, and the hearth reserve is read dynamically below. So accept a
# clock that already rolled and pin day 2 / hour 21 exactly as before. A
# clock at day 3+ means the day-two window this scenario prepares was
# genuinely missed, so keep failing loudly rather than rewinding — this
# suite never backdates the clock or world receipts (see the EDGE-18
# future-day step in run_all.py).
start_day = int(clock.db.day or 1)
assert start_day in (1, 2), start_day
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
