"""GDD T-09: disposable QA setup for relief after finite sideboard exhaustion.

Only seeds an already-built QA world with honest depleted resources and
a hungry, established non-Innkeep. All relief actions are then issued over
an authenticated ordinary client, never through this offline shell.
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
clock = ScriptDB.objects.get(db_key="village_time")
day = int(clock.db.day or 1)
assert day == 4, day
tavern = one("The Blood of the Vine")
smith = one("SmithTester")
assert smith.account and smith.account.username == "qa_smith_repair"
assert smith.move_to(tavern, quiet=True)
# The baseline NPC refill needs the keeper physically on duty. Make this a
# genuinely unattended-Tavern shortage in the disposable QA world, rather
# than racing a routine sideboard refill during authenticated commands.
keeper = one("Bram")
if keeper.location == tavern:
    assert keeper.move_to(one("Village Square"), quiet=True)
assert keeper.location != tavern
smith.db.hunger = 96
smith.db.queasy = 0

# All three ordinary house dishes are physically exhausted. This isn't
# a new pantry or an AI-only rescue. The sole finite relief is one real
# cooking opportunity already present in the shared soup stock.
for key in ("a loaf of bread", "a wedge of cheese", "a bowl of stew"):
    plate = one(key)
    assert plate.location == tavern, (key, plate.location)
    plate.db.servings = 0

pantry = soup_state.pantry(tavern.db.soup_pantry, day)
pantry["stock"] = {item: 0 for item in soup_state.BASE_STOCK}
pantry["stock"]["barley"] = 1
pantry["stock"]["salt"] = 1
tavern.db.soup_pantry = pantry
assert not any(o.key == "a bowl of plain kitchen broth" for o in smith.contents)
print("GDD_T09_ALL_SIDEBOARD_EXHAUSTED_SINGLE_PANTRY_MEAL_READY")
