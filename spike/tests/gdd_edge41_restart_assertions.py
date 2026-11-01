"""Verify EDGE-41 source, separate accounts and indoor show after real restart."""
from evennia.utils import search
from evennia.accounts.models import AccountDB
from world.stage_state import normalize
from world.events import get_event_ledger
from world import stage_state

def one(key):
    matches = [obj for obj in search.search_object(key) if obj.key == key]
    assert len(matches) == 1, (key, len(matches))
    return matches[0]

def owner(mask):
    # Evennia releases mask.account on logout. Ownership survives restarts
    # through the account's persistent character roster, not puppet state.
    owners = [
        account for account in AccountDB.objects.all()
        if any(character.id == mask.id for character in account.characters.all())
    ]
    assert len(owners) == 1, (mask.key, len(owners))
    return owners[0]

tavern = one("The Blood of the Vine")
square = one("Village Square")
cord = one("a frayed red cord")
hound = one("HoundTester")
performer = one("PerformerTester")
hound_account = owner(hound)
performer_account = owner(performer)
assert hound_account.id != performer_account.id
state = normalize(tavern.db.village_stage)
warn = state["safety_warning"]
decision = state["safety_decision"]
show = state["performance"]
assert warn and decision and show
assert warn["account_id"] == hound_account.id
assert decision["account_id"] == performer_account.id
assert warn["account_id"] != decision["account_id"]
assert warn["mask_id"] == hound.id
assert decision["mask_id"] == performer.id
assert decision["warning_event_id"] == warn["event_id"]
assert decision["choice"] == "indoor"
assert show["safety_mode"] == "indoor"
assert show["safety_decision_event_id"] == decision["event_id"]
assert show["account_id"] == performer_account.id
assert len(state["witnesses"]) == 1
assert state["witnesses"][0]["account_id"] == hound_account.id
ledger = get_event_ledger()
source = ledger.get_event(warn["source_event_id"])
signed_warning = ledger.get_event(warn["event_id"])
signed_decision = ledger.get_event(decision["event_id"])
assert signed_warning["kind"] == "village.stage_warned"
assert signed_decision["kind"] == "village.stage_adapted"
assert all(e["status"] == "complete" for e in (source, signed_warning, signed_decision))
assert signed_warning["actor"]["account_id"] == hound_account.id
assert signed_decision["actor"]["account_id"] == performer_account.id
assert signed_warning["consequence"]["source_event_id"] == source["id"]
assert signed_decision["consequence"]["warning_event_id"] == warn["event_id"]
assert stage_state.verified_hound_source(
    square.db.daily_route_survey, source, cord.db.route_caution,
    account_id=hound_account.id, mask_id=hound.id,
    source_event_id=source["id"], cord_id=cord.id, square_id=square.id,
    day=state["day"], hour=23, room_name="The Northern Treeline")
print("POST_RESTART_GDD_EDGE41_INDEPENDENT_SIGNED_INDOOR_SHOW_GREEN")
