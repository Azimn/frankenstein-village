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
day = int(clock.db.day or 1)
hour = int(clock.db.hour if clock.db.hour is not None else 0)
brazier = one("a public warming brazier")
state = fire.normalize(brazier.db.square_brazier)
# The previous stage advanced the REAL clock past the signed fire deadline,
# then rewound the disposable QA time by one hour before this restart.
# Derive the deadline from persisted ignition instead of assuming day five.
assert len(state["history"]) == 2
ignition = state["history"][0]
assert state["warm_until"] == fire.hour_index(
    ignition["day"], ignition["hour"]
) + 10, state
deadline = state["warm_until"]
assert state["observed_at"] >= deadline + 1, state
now = fire.hour_index(day, hour)
assert deadline - 1 <= now <= state["observed_at"], (now, state)
assert not fire.active(state, day, hour)
# Check the intentionally rewound pre-expiry hour as well; the persisted
# observed high-water must prevent burned fuel from reigniting there.
rewind_hour_index = deadline - 1
rewind_day, rewind_hour = divmod(rewind_hour_index, 24)
assert not fire.active(state, rewind_day + 1, rewind_hour)
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
