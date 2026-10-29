"""Read-only real-restart verification of the second EDGE-08 Hound/Innkeep day."""
from evennia.utils import search
from evennia.accounts.models import AccountDB
from world import route_surveys, refuge_state
from world.events import get_event_ledger
from world.discoveries import observed_caution

def one(key):
    rows = [obj for obj in search.search_object(key) if obj.key == key]
    assert len(rows) == 1, (key, len(rows))
    return rows[0]

def owner(mask):
    accounts = [account for account in AccountDB.objects.all()
                if any(character.id == mask.id for character in account.characters.all())]
    assert len(accounts) == 1
    return accounts[0]

cord = one("a frayed red cord")
square = one("Village Square")
tavern = one("The Blood of the Vine")
hound = one("HoundTester")
innkeep = one("InnkeepTester")
hound_account, inn_account = owner(hound), owner(innkeep)
assert hound_account.id != inn_account.id
marker = dict(cord.db.route_caution or {})
history = list(cord.db.route_caution_history or [])
assert history, "Original physical marker history was lost"
old = dict(history[-1])
assert old["day"] < marker["day"]
assert marker["prior_caution_event_id"] == old["event_id"]
route = route_surveys.normalize(square.db.daily_route_survey)
assert route["day"] == marker["day"]
assert route["field_decisions"]["hound"]["event_id"] == marker["event_id"]
assert route["field_decisions"]["hound"]["retied_previous_day"] is True
assert route["history"][-1]["field_decisions"]["hound"]["event_id"] == old["event_id"]
ledger = get_event_ledger()
old_event = ledger.get_event(old["event_id"])
source = ledger.get_event(marker["event_id"])
assert refuge_state.protection_valid(old_event, old, cord.id)
assert refuge_state.protection_valid(source, marker, cord.id)
assert source["payload"]["prior_caution_event_id"] == old["event_id"]
assert source["consequence"]["prior_caution_event_id"] == old["event_id"]
assert source["actor"]["account_id"] == hound_account.id
assert observed_caution(hound.db.landmark_latest_view,
                        day=marker["day"], hour=21,
                        source_event_id=marker["event_id"], cord_id=cord.id)
last = dict(cord.db.refuge_dispatch_last or {})
assert last["day"] == marker["day"]
assert last["source_protect_event_id"] == marker["event_id"]
rows = list((tavern.db.route_refuge or {}).get("history") or [])
assert len(rows) == 2, rows
first, second = rows
assert first["source_protect_event_id"] == old["event_id"]
assert second["source_protect_event_id"] == marker["event_id"]
assert second["hound_account_id"] == hound_account.id
assert second["innkeep_account_id"] == inn_account.id
assert second["hound_mask_id"] == hound.id
assert second["innkeep_mask_id"] == innkeep.id
dispatch = ledger.get_event(second["dispatch_event_id"])
meal = ledger.get_event(second["event_id"])
assert dispatch["status"] == "complete"
assert dispatch["consequence"]["source_protect_event_id"] == marker["event_id"]
assert meal["status"] == "complete"
assert meal["actor"]["account_id"] == inn_account.id
assert meal["consequence"]["consumed_dispatch_id"] == second["item_id"]
assert meal["consequence"]["source_protect_event_id"] == marker["event_id"]
assert not search.search_object("a signed treeline refuge dispatch")
assert any(obj.id == second["bowl_id"] for obj in hound.contents)
assert refuge_state.public_lines(tavern.db.route_refuge).startswith(
    "2 signed Hound arrivals")
print("POST_RESTART_GDD_EDGE08_LATER_DAY_SIGNED_FINITE_REFUGE_GREEN")
