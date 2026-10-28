"""Advance the disposable EDGE-41 scene after a signed second-day cancellation.

No source or player action is fabricated. The next protection must succeed
against the physical cord's persisted history of the earlier renewal.
"""
from evennia.scripts.models import ScriptDB
from evennia.utils import search
from world import stage_state, route_work

def one(key):
    found = [obj for obj in search.search_object(key) if obj.key == key]
    assert len(found) == 1, (key, len(found))
    return found[0]

clock = ScriptDB.objects.get(db_key="village_time")
tavern = one("The Blood of the Vine")
square = one("Village Square")
cord = one("a frayed red cord")
stage = stage_state.normalize(tavern.db.village_stage)
prior = dict(cord.db.route_caution or {})
history = list(cord.db.route_caution_history or [])
assert stage["safety_decision"] and stage["safety_decision"]["choice"] == "cancel"
assert stage["performance"] is None
assert len(history) == 1, history
assert prior["day"] == stage["day"]
assert prior["prior_caution_event_id"] == history[-1]["event_id"]
assert route_work._signed_prior_caution(cord, square, history[-1], prior["day"])
clock.db.day = max(int(clock.db.day or 1), prior["day"]) + 1
clock.db.hour = 0
assert int(clock.db.day) > prior["day"]
print("GDD_EDGE41_THIRD_DAY_PERSISTED_HISTORY_READY", int(clock.db.day))
