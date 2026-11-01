"""Forward-only disposable QA day for a second authenticated Hound warning."""
from evennia.scripts.models import ScriptDB
from evennia.utils import search
from world import stage_state

def one(key):
    found = [obj for obj in search.search_object(key) if obj.key == key]
    assert len(found) == 1, (key, len(found))
    return found[0]

clock = ScriptDB.objects.get(db_key="village_time")
tavern = one("The Blood of the Vine")
cord = one("a frayed red cord")
stage = stage_state.normalize(tavern.db.village_stage)
prior = dict(cord.db.route_caution or {})
assert stage["performance"] and stage["safety_decision"]
assert prior["day"] == stage["day"]
assert prior["event_id"] == stage["safety_warning"]["source_event_id"]
old_day = max(int(clock.db.day or 1), stage["day"])
clock.db.day = old_day + 1
clock.db.hour = 0
assert int(clock.db.day) > prior["day"]
print("GDD_EDGE41_RENEWAL_FORWARD_DAY_READY", int(clock.db.day))
