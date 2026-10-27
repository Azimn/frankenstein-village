"""GDD T-09: verify non-Innkeep finite hunger relief after an actual restart.

The food was prepared and eaten through the public telnet commands, not
manufactured in a shell. Read persistence, custody and one signed event.
"""
from evennia.accounts.models import AccountDB
from evennia.scripts.models import ScriptDB
from evennia.utils import search
from world import soup_state


def one(key):
    objects = [obj for obj in search.search_object(key) if obj.key == key]
    assert len(objects) == 1, (key, len(objects))
    return objects[0]


assert not any(account.is_connected for account in AccountDB.objects.all())
smith = one("SmithTester")
tavern = one("The Blood of the Vine")
bowl = one("a bowl of plain kitchen broth")
clock = ScriptDB.objects.get(db_key="village_time")
assert int(clock.db.day or 1) == 4
# A disconnected mask may be returned to the OOC Inn on logout. Preserve
# the physical bowl and its signed Tavern origin instead of assuming the
# mask remains in the cooking room after an actual process restart.
assert smith.location is not None
smith_owner = AccountDB.objects.get(username="qa_smith_repair")
# A stopped server has no live puppet binding. Durable account ownership
# comes from the playable-character roster, not character.account.
assert smith in smith_owner.characters.all()
assert 72 <= int(smith.db.hunger) < 80, smith.db.hunger  # 96 minus 24; allow login movement
assert bowl.location == smith
assert int(bowl.db.servings or 0) == 0, "Ration refilled across restart"
assert bowl.tags.has("consumable") and bowl.tags.has("food")
source = dict(bowl.db.kitchen_ration or {})
assert source["maker_id"] == smith.id
assert source["base"] == "barley" and source["seasoning"] == "salt"
assert source["source_room_id"] == tavern.id

ledger = ScriptDB.objects.get(db_key="world_event_ledger")
event = ledger.get_event(source["cook_event_id"])
assert event is not None and event["status"] == "complete", event
assert event["kind"] == "village.kitchen_plain_ration"
assert event["actor"]["mask_id"] == smith.id
assert event["actor"]["account_id"] == smith_owner.id
assert event["consequence"]["bowl_id"] == bowl.id
assert event["consequence"]["nourish"] == 24
matching = [
    e for e in (ledger.db.events or [])
    if e.get("kind") == "village.kitchen_plain_ration"
    and e.get("actor", {}).get("mask_id") == smith.id
    and e.get("status") == "complete"
]
assert len(matching) == 1, matching
pantry = soup_state.pantry(tavern.db.soup_pantry, 4)
assert pantry["stock"]["barley"] == 0
assert pantry["stock"]["salt"] == 0
assert not any(value < 0 for value in pantry["stock"].values())
assert not any(value for value in pantry["stock"].values())
assert smith.sensory_snapshot()["bands"]["hunger"] == "hungry"
assert not any("soup ration" in line.lower()
               for line in smith.sensory_snapshot()["possible_relief"])
print("POST_RESTART_GDD_T09_DEPLETED_FARE_PHYSICAL_RELIEF_GREEN")
