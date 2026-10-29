"""Advance only the disposable QA village clock; no player action is forged."""
from evennia.scripts.models import ScriptDB
from evennia.utils import search

def one(key):
    rows = [obj for obj in search.search_object(key) if obj.key == key]
    assert len(rows) == 1, (key, len(rows))
    return rows[0]

clock = ScriptDB.objects.get(db_key="village_time")
cord = one("a frayed red cord")
tavern = one("The Blood of the Vine")
hound = one("HoundTester")
innkeep = one("InnkeepTester")
prior = dict(cord.db.route_caution or {})
assert type(prior.get("event_id")) is int and prior["event_id"] > 0
assert type(prior.get("day")) is int and prior["day"] >= 1
assert hound.location is not None, "Hound mask must still be in the physical world"
assert innkeep.location == tavern, ("Innkeep not at Tavern", getattr(innkeep.location, "key", None))
print("EDGE08_RENEWAL_START_ROOMS", hound.location.key, innkeep.location.key)
receipts = list((tavern.db.route_refuge or {}).get("history") or [])
assert len(receipts) == 1, "Initial-day signed meal must exist before renewal"
assert receipts[0]["source_protect_event_id"] == prior["event_id"]
clock.db.day = max(int(clock.db.day or 1), prior["day"]) + 1
clock.db.hour = 21
assert int(clock.db.day) > prior["day"]
print("GDD_EDGE08_NEXT_DAY_RENEWAL_READY", int(clock.db.day))
