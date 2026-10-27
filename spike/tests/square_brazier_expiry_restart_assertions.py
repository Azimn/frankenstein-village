"""One MORE real restart: the Square fire remains dead after clock rewind.

Previous shell ran the ACTUAL VillageTime.at_repeat at the expiry boundary,
then rewound the disposable QA clock one hour. Nothing should relight simply
because an earlier hour is being observed after a server restart.
"""
from evennia.scripts.models import ScriptDB
from evennia.utils import search

from world.square_brazier import is_active
from world import square_brazier_state as fire


def one(key):
    matches = [o for o in search.search_object(key) if o.key == key]
    assert len(matches) == 1, (key, len(matches))
    return matches[0]


clock = ScriptDB.objects.get(db_key="village_time")
assert int(clock.db.day or 1) == 5
assert int(clock.db.hour) == 6
brazier = one("a public warming brazier")
state = fire.normalize(brazier.db.square_brazier)
assert state["observed_at"] == fire.hour_index(5, 7)
assert state["warm_until"] == fire.hour_index(5, 7)
assert not fire.active(state, 5, 6)
assert not is_active()
assert len(state["history"]) == 2
assert "cold" in brazier.get_display_desc(looker=one("SmithTester")).lower()

mask = one("SmithTester")
before = float(mask.db.warmth)
watch = ScriptDB.objects.get(db_key="warmth_watch")
watch._tick_char(mask, "Village Square", "rain")
after = float(mask.db.warmth)
assert round(before - after, 5) == 0.08, (before, after)
assert not any(
    "public square brazier" in msg.lower()
    for msg in mask.sensory_snapshot()["possible_relief"]
), "The body is still being offered expired fire as viable relief"
print("POST_SECOND_RESTART_SQUARE_BRAZIER_EXPIRED_REWIND_INERT_GREEN")
