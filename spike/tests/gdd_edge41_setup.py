"""Isolate EDGE-41 after the existing regression's day-four assertions.

Only this disposable CI world is reset. No signed evidence is manufactured.
Both role actions and the actual show must occur through authenticated telnet.
"""
from evennia.scripts.models import ScriptDB
from evennia.utils import search
from world import route_surveys, stage_state

def one(key):
    matches = [obj for obj in search.search_object(key) if obj.key == key]
    assert len(matches) == 1, (key, len(matches))
    return matches[0]

clock = ScriptDB.objects.get(db_key="village_time")
day = int(clock.db.day or 1)
assert day >= 4, "EDGE-41 fixture must follow all previous day-four tests"
clock.db.hour = 20
square = one("Village Square")
tavern = one("The Blood of the Vine")
cord = one("a frayed red cord")
assert cord.location == one("The Northern Treeline")
assert stage_state.normalize(tavern.db.village_stage)["performance"] is not None
assert cord.db.route_caution is not None
square.db.daily_route_survey = route_surveys.fresh(day)
tavern.db.village_stage = stage_state.fresh(day)
cord.db.route_caution = None
for key in ("HoundTester", "PerformerTester"):
    one(key).location = square
print("GDD_EDGE41_DISPOSABLE_ISOLATED_PHYSICAL_SCENE_READY", day)
