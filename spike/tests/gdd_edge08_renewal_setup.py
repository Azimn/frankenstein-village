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
from evennia.accounts.models import AccountDB
hound_account = AccountDB.objects.get(username="qa_hound_protection")
assert any(character.id == hound.id for character in hound_account.characters.all()), (
    "Original signed Hound mask is no longer owned by its account"
)
# A disconnected mask may be unplaced after prior regression/restart steps.
# Do not teleport it in a privileged shell. Re-entry and legal travel are
# tested through the original authenticated player client below.
innkeep_account = AccountDB.objects.get(username="qa_innkeep_care")
assert hound_account.id != innkeep_account.id
assert any(character.id == innkeep.id for character in innkeep_account.characters.all()), (
    "Original signed Innkeep mask is no longer owned by its account"
)
# No privileged placement: both unplaced masks must be recovered by the
# ordinary authenticated IC path, then walk through the actual front door.
print("EDGE08_RENEWAL_START_ROOMS",
      getattr(hound.location, "key", "UNPLACED"),
      getattr(innkeep.location, "key", "UNPLACED"))
receipts = list((tavern.db.route_refuge or {}).get("history") or [])
assert len(receipts) == 1, "Initial-day signed meal must exist before renewal"
assert receipts[0]["source_protect_event_id"] == prior["event_id"]
clock.db.day = max(int(clock.db.day or 1), prior["day"]) + 1
clock.db.hour = 21
assert int(clock.db.day) > prior["day"]
print("GDD_EDGE08_NEXT_DAY_RENEWAL_READY", int(clock.db.day))
