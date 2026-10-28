"""Verify renewable physical cord and second-day independent decision after restart."""
from evennia.utils import search
from evennia.accounts.models import AccountDB
from world import stage_state, route_surveys, route_work
from world.events import get_event_ledger

def one(key):
    found = [obj for obj in search.search_object(key) if obj.key == key]
    assert len(found) == 1, (key, len(found))
    return found[0]

def owner(mask):
    found = [a for a in AccountDB.objects.all()
             if any(c.id == mask.id for c in a.characters.all())]
    assert len(found) == 1
    return found[0]

tavern = one("The Blood of the Vine")
square = one("Village Square")
cord = one("a frayed red cord")
hound = one("HoundTester")
performer = one("PerformerTester")
hound_id = owner(hound).id
performer_id = owner(performer).id
assert hound_id != performer_id
stage = stage_state.normalize(tavern.db.village_stage)
route = route_surveys.normalize(square.db.daily_route_survey)
marker = dict(cord.db.route_caution or {})
history = list(cord.db.route_caution_history or [])
assert len(history) >= 1
old = history[-1]
assert old["day"] < marker["day"]
assert marker["prior_caution_event_id"] == old["event_id"]
assert marker["account_id"] == hound_id
assert route_work._signed_prior_caution(cord, square, old, marker["day"])
assert not route_work._signed_prior_caution(
    cord, square, {**old, "event_id": 99999999}, marker["day"])
assert not route_work._signed_prior_caution(
    cord, square, {**old, "day": marker["day"]}, marker["day"])
assert not route_work._signed_prior_caution(
    cord, square, {**old, "account_id": performer_id}, marker["day"])
assert route["day"] == stage["day"] == marker["day"]
assert route["field_decisions"]["hound"]["event_id"] == marker["event_id"]
assert route["field_decisions"]["hound"]["retied_previous_day"] is True
assert route["history"][-1]["field_decisions"]["hound"]["event_id"] == old["event_id"]
assert stage["history"][-1]["performance"]["safety_mode"] == "indoor"
assert stage["performance"] is None
warn = stage["safety_warning"]
decision = stage["safety_decision"]
assert warn and decision
assert warn["source_event_id"] == marker["event_id"]
assert warn["account_id"] == hound_id
assert decision["account_id"] == performer_id
assert decision["choice"] == "cancel"
assert decision["warning_event_id"] == warn["event_id"]
ledger = get_event_ledger()
old_source = ledger.get_event(old["event_id"])
source = ledger.get_event(marker["event_id"])
signed_warning = ledger.get_event(warn["event_id"])
signed_decision = ledger.get_event(decision["event_id"])
assert all(e["status"] == "complete" for e in (
    old_source, source, signed_warning, signed_decision))
assert source["kind"] == "village.route_protected"
assert source["payload"]["prior_caution_event_id"] == old["event_id"]
assert source["consequence"]["prior_caution_event_id"] == old["event_id"]
assert source["consequence"]["cord_object_id"] == cord.id
assert source["consequence"]["square_room_id"] == square.id
assert signed_warning["actor"]["account_id"] == hound_id
assert signed_decision["actor"]["account_id"] == performer_id
assert signed_decision["consequence"]["warning_event_id"] == warn["event_id"]
assert stage_state.verified_hound_source(
    route, source, marker, account_id=hound_id, mask_id=hound.id,
    source_event_id=source["id"], cord_id=cord.id, square_id=square.id,
    day=stage["day"], hour=23, room_name="The Northern Treeline")
print("POST_RESTART_GDD_EDGE41_LATER_DAY_SIGNED_CANCEL_GREEN")
