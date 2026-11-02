"""Third distinct Hound warning and independent Performer decision after restart."""
from collections.abc import Sequence, Mapping
from evennia.utils import search
from evennia.accounts.models import AccountDB
from world import route_work, route_surveys, stage_state, stage_work
from world.events import get_event_ledger

def one(key):
    found = [obj for obj in search.search_object(key) if obj.key == key]
    assert len(found) == 1, (key, len(found))
    return found[0]

def owner(mask):
    found = [account for account in AccountDB.objects.all()
             if any(character.id == mask.id for character in account.characters.all())]
    assert len(found) == 1
    return found[0]

tavern = one("The Blood of the Vine")
square = one("Village Square")
cord = one("a frayed red cord")
hound = one("HoundTester")
performer = one("PerformerTester")
hound_id, performer_id = owner(hound).id, owner(performer).id
assert hound_id != performer_id
raw_history = cord.db.route_caution_history
assert isinstance(raw_history, Sequence) and not isinstance(raw_history, (str, bytes))
history = list(raw_history)
assert len(history) == 2, history
assert all(isinstance(item, Mapping) for item in history)
marker = dict(cord.db.route_caution or {})
first, second = history
assert first["day"] < second["day"] < marker["day"]
assert second["prior_caution_event_id"] == first["event_id"]
assert marker["prior_caution_event_id"] == second["event_id"]
assert all(row["account_id"] == hound_id for row in (first, second, marker))
assert route_work._signed_prior_caution(cord, square, first, marker["day"])
assert route_work._signed_prior_caution(cord, square, second, marker["day"])
route = route_surveys.normalize(square.db.daily_route_survey)
stage = stage_state.normalize(tavern.db.village_stage)
assert route["day"] == stage["day"] == marker["day"]
assert route["field_decisions"]["hound"]["event_id"] == marker["event_id"]
assert route["field_decisions"]["hound"]["retied_previous_day"] is True
assert route["history"][-1]["field_decisions"]["hound"]["event_id"] == second["event_id"]
assert stage["performance"] is None
warning, decision = stage["safety_warning"], stage["safety_decision"]
assert warning and decision and decision["choice"] == "cancel"
assert warning["account_id"] == hound_id
assert decision["account_id"] == performer_id
assert warning["source_event_id"] == marker["event_id"]
assert decision["warning_event_id"] == warning["event_id"]
ledger = get_event_ledger()
for index, row in enumerate((first, second, marker)):
    event = ledger.get_event(row["event_id"])
    assert event["status"] == "complete" and event["kind"] == "village.route_protected"
    assert event["consequence"]["cord_object_id"] == cord.id
    assert event["consequence"]["square_room_id"] == square.id
    if index:
        previous = (first, second)[index - 1]
        assert event["payload"]["prior_caution_event_id"] == previous["event_id"]
        assert event["consequence"]["prior_caution_event_id"] == previous["event_id"]
assert stage_work._verified_warning(stage, marker["day"], 23)
assert stage_work._verified_decision(stage, marker["day"], 23)
assert ledger.get_event(warning["event_id"])["status"] == "complete"
assert ledger.get_event(decision["event_id"])["status"] == "complete"
print("POST_RESTART_GDD_EDGE41_THIRD_DAY_SIGNED_HISTORY_GREEN")
