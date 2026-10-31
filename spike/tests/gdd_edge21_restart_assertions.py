"""EDGE-21: verify real player stage rail survives an Evennia process restart."""
from evennia.utils import search

from world import stage_fitting_edge21 as rules, stage_fitting_work, stage_work
from world.events import get_event_ledger

tavern = stage_work._tavern()
assert tavern is not None, "Original Tavern missing"
state = rules.normalize(tavern.db.stage_rail_edge21)
assert state["condition"] == "ready", state
assert state["remaining"] == 2, state
assert len(state["plays"]) == 1, state
fitting = state["fitting"]
check = state["soundcheck"]
play = state["plays"][0]
assert fitting["account_id"] != check["account_id"], state
assert fitting["mask_id"] != check["mask_id"], state
assert play["account_id"] == check["account_id"], state
assert play["soundcheck_event_id"] == check["event_id"], state
assert play["tune"] == "reel", state
assert (fitting["day"], fitting["hour"]) <= (check["day"], check["hour"]) <= (
    play["day"], play["hour"]), state
f, why = stage_fitting_work._fit_receipt(tavern)
assert f == fitting and why is None, (f, why)
c, why = stage_fitting_work._check_receipt(tavern)
assert c == check and why is None, (c, why)
valid, why = stage_fitting_work._verified_plays(tavern)
assert valid and why is None, why
ledger = get_event_ledger()
for event_id, kind in (
    (fitting["event_id"], "professional.stage_rail_fitted"),
    (check["event_id"], "professional.stage_rail_soundchecked"),
    (play["event_id"], "professional.stage_acoustic_played"),
):
    event = ledger.get_event(event_id)
    assert event and event["kind"] == kind and event["status"] == "complete", event
assert not any(
    obj.key == "a forged market hinge" and obj.id == fitting["item_id"]
    for obj in search.search_object("a forged market hinge")
), "Consumed physical hinge reappeared after restart"
# Adversarial rollback: a valid pre-play Attribute snapshot is not allowed to
# erase a completed acoustic event or replenish a finite physical fitting.
stale = dict(state, plays=[], remaining=3)
assert rules.normalize(stale)["condition"] == "ready"
tavern.db.stage_rail_edge21 = stale
try:
    valid, reason = stage_fitting_work._verified_plays(tavern)
    assert not valid and "omits" in reason, (valid, reason)
finally:
    tavern.db.stage_rail_edge21 = state
assert stage_fitting_work._verified_plays(tavern) == (True, None)
assert "2 of 3 acoustic uses remain" in stage_fitting_work.public_status(tavern)
# A shape-valid mutable record is not itself proof of a completed source.
# Public status must independently recheck the canonical event ledger.
for damaged in (
    dict(state, fitting=dict(fitting, item_id=999999)),
    dict(state, soundcheck=dict(check, event_id=999999),
         plays=[dict(play, soundcheck_event_id=999999)]),
    dict(state, plays=[], remaining=3),
):
    tavern.db.stage_rail_edge21 = damaged
    try:
        assert "unverified" in stage_fitting_work.public_status(tavern).lower()
        assert "acoustic sets are unavailable" in stage_fitting_work.public_status(tavern)
    finally:
        tavern.db.stage_rail_edge21 = state
assert "2 of 3 acoustic uses remain" in stage_fitting_work.public_status(tavern)
print("POST_RESTART_GDD_EDGE21_PUBLIC_STATUS_SOURCE_VERIFIED_GREEN")
print("POST_RESTART_GDD_EDGE21_STALE_SNAPSHOT_REPLAY_REFUSED_GREEN")
print("POST_RESTART_GDD_EDGE21_INDEPENDENT_SIGNED_RAIL_GREEN")
