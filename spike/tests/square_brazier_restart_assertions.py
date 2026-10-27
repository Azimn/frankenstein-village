"""Persisted two-account public-brazier proof after actual Evennia restart.

Both firewood bundles were gathered earlier through normal commands and
consumed by two authenticated masks. No admin made a fire. The script
verifies physical custody, canonical events, expiry and bodily warmth.
"""
from evennia.accounts.models import AccountDB
from evennia.objects.models import ObjectDB
from evennia.scripts.models import ScriptDB
from evennia.utils import search

from world import square_brazier_state as fire
from world.square_brazier import is_active


def one(key):
    matches = [obj for obj in search.search_object(key) if obj.key == key]
    assert len(matches) == 1, (key, len(matches))
    return matches[0]


assert not any(account.is_connected for account in AccountDB.objects.all())
clock = ScriptDB.objects.get(db_key="village_time")
day, hour = int(clock.db.day or 1), int(clock.db.hour or 0)
assert day == 4, day
square = one("Village Square")
brazier = one("a public warming brazier")
smith = one("SmithTester")
merchant = one("MerchantTester")
assert brazier.location == square and smith.location == square
assert merchant.location == square
assert brazier.typeclass_path == "typeclasses.objects.SquareBrazier"
assert brazier.access(smith, "get", default=True) is False

state = fire.normalize(brazier.db.square_brazier)
assert len(state["history"]) == 2, state
first, second = state["history"]
assert (first["mask_id"], first["mode"]) == (smith.id, "light")
assert (second["mask_id"], second["mode"]) == (merchant.id, "feed")
assert first["bundle_id"] == smith.db.qa_brazier_bundle_id
assert first["bundle_id"] != second["bundle_id"]
assert first["event_id"] != second["event_id"]
assert state["warm_until"] == fire.hour_index(4, first["hour"]) + 10, state
assert fire.active(state, day, hour), "The true signed fire ended before restart"
assert not fire.active(state, 5, 12), "Expired fire incorrectly survives a later day"
assert is_active(), "Runtime warmth check could not find persisted fire"

ledger = ScriptDB.objects.get(db_key="world_event_ledger")
for index, record in enumerate((first, second)):
    signed = ledger.get_event(record["event_id"])
    assert signed is not None and signed["status"] == "complete", signed
    assert signed["kind"] == (
        "civic.square_brazier_light" if index == 0
        else "civic.square_brazier_feed"
    )
    assert signed["actor"]["mask_id"] == record["mask_id"]
    assert signed["payload"]["bundle_id"] == record["bundle_id"]
    assert signed["payload"]["gather_event_id"] == record["gather_event_id"]
    assert signed["consequence"]["brazier_id"] == brazier.id
    assert signed["consequence"]["bundle_id"] == record["bundle_id"]
    assert ObjectDB.objects.filter(id=record["bundle_id"]).first() is None, (
        "Consumed physical firewood reappeared after restart", record
    )
    gather = ledger.get_event(record["gather_event_id"])
    assert gather is not None and gather["status"] == "complete"
    assert gather["kind"] == "civic.hearth_firewood_gathered"

# The same production WarmthWatch modifies the existing body while the fire
# is active, including in rain. No new character meter or second drive.
watch = ScriptDB.objects.get(db_key="warmth_watch")
before = float(smith.db.warmth)
assert before < 0.9, before
watch._tick_char(smith, "Village Square", "rain")
after = float(smith.db.warmth)
assert round(after - before, 5) == 0.04, (before, after)
assert smith.sensory_snapshot()["bands"]["warmth"] in {
    "cool", "cold", "freezing", "warm"
}
assert any(
    "public square brazier" in line.lower()
    for line in smith.sensory_snapshot()["possible_relief"]
), "Actual warm project did not appear in the local body guidance"
from world.square_brazier import status_lines
assert "Last supplied by MerchantTester" in status_lines(smith)
assert "Split logs glow" in brazier.get_display_desc(looker=smith)
print("POST_RESTART_SQUARE_BRAZIER_REAL_TWO_ACCOUNT_FIRE_AND_WARMTH_GREEN")

# Advance the ACTUAL existing village-time Script past the deadline
# derived from the signed ignition, not a hard-coded day-five hour.
# Real T-13 play can advance the village clock before this project starts.
deadline = state["warm_until"]
assert fire.hour_index(day, hour) < deadline
expiry_day, expiry_hour = divmod(deadline, 24)
expiry_day += 1
clock.db.day = expiry_day
clock.db.hour = expiry_hour
clock.at_repeat()  # one genuine clock tick past the actual signed deadline
assert fire.hour_index(int(clock.db.day), int(clock.db.hour)) == deadline + 1
expired = fire.normalize(brazier.db.square_brazier)
assert expired["observed_at"] == deadline + 1, expired
assert not is_active()
# Deliberately rewind the disposable QA clock to an hour when the fire
# otherwise would have been burning. Its persisted high-water prevents
# resurrecting fuel already consumed, including across midnight.
rewind_day, rewind_hour = divmod(deadline - 1, 24)
rewind_day += 1
clock.db.day = rewind_day
clock.db.hour = rewind_hour
assert not is_active(), "A clock rewind resurrected already-spent public fuel"
assert not fire.active(brazier.db.square_brazier, rewind_day, rewind_hour)
assert len(fire.normalize(brazier.db.square_brazier)["history"]) == 2
print("SQUARE_BRAZIER_ACTUAL_CLOCK_EXPIRY_AND_REWIND_REFUSED_GREEN")
