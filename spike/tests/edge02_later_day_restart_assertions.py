"""Read-only EDGE-02 acceptance after actual later-day repair and restarts."""
import os
from evennia.accounts.models import AccountDB
from evennia.scripts.models import ScriptDB
from evennia.utils import search
from world import kitchen_repair_edge02, kitchen_repair_work, workshop_state


def one(key):
    found = [obj for obj in search.search_object(key) if obj.key == key]
    assert len(found) == 1, (key, len(found))
    return found[0]


clock = ScriptDB.objects.get(db_key="village_time")
assert int(clock.db.day or 1) >= 4
_kitchen_pot = one("a communal soup pot")
_kitchen_state = kitchen_repair_edge02.normalize(_kitchen_pot.db.kitchen_repair)
assert _kitchen_state["condition"] == "working", _kitchen_state
_kitchen_inn = _kitchen_state["restriction"]
_kitchen_fix = _kitchen_state["repair"]
_kitchen_smith = one("KitchenSmithTester")
innkeep_tester = one("InnkeepTester")
assert _kitchen_inn["mask_id"] == innkeep_tester.id
assert _kitchen_fix["mask_id"] == _kitchen_smith.id
assert _kitchen_inn["account_id"] != _kitchen_fix["account_id"]
assert _kitchen_inn["day"] == 1
assert 4 <= _kitchen_fix["day"] <= int(clock.db.day)
assert _kitchen_fix["day"] > _kitchen_inn["day"]
assert AccountDB.objects.filter(id=_kitchen_inn["account_id"]).exists()
assert AccountDB.objects.filter(id=_kitchen_fix["account_id"]).exists()
_kitchen_ledger = ScriptDB.objects.get(db_key="world_event_ledger")
_kitchen_restrict_event = _kitchen_ledger.get_event(_kitchen_inn["event_id"])
_kitchen_forge_event = _kitchen_ledger.get_event(_kitchen_fix["forge_event_id"])
_kitchen_repair_event = _kitchen_ledger.get_event(_kitchen_fix["event_id"])
assert _kitchen_restrict_event["kind"] == "professional.innkeep_kitchen_restriction"
assert _kitchen_forge_event["kind"] == "village.market_hinge_forged"
assert _kitchen_repair_event["kind"] == "professional.smith_kitchen_repair"
assert all(row["status"] == "complete" for row in (
    _kitchen_restrict_event, _kitchen_forge_event, _kitchen_repair_event
))
assert _kitchen_restrict_event["actor"]["account_id"] == _kitchen_inn["account_id"]
assert _kitchen_repair_event["actor"]["account_id"] == _kitchen_fix["account_id"]
assert _kitchen_restrict_event["consequence"]["condition"] == "restricted"
assert _kitchen_repair_event["payload"]["restriction_event_id"] == _kitchen_inn["event_id"]
assert _kitchen_repair_event["payload"]["forge_event_id"] == _kitchen_fix["forge_event_id"]
assert _kitchen_repair_event["consequence"]["consumed_item_id"] == _kitchen_fix["item_id"]
assert _kitchen_repair_event["consequence"]["condition"] == "working"
assert _kitchen_forge_event["payload"]["day"] == _kitchen_fix["day"]
assert _kitchen_forge_event["consequence"]["item_id"] == _kitchen_fix["item_id"]
assert not [obj for obj in search.search_object("a forged market hinge")
            if obj.id == _kitchen_fix["item_id"]], "Consumed hinge survived restart"
# Enforce global Workshop conservation from the original signed ledger,
# including the already-main Market and stage fittings on day one.
crafts_by_day = {}
for row in _kitchen_ledger.db.events:
    if row.get("kind") != "village.market_hinge_forged" or row.get("status") != "complete":
        continue
    signed_day = row.get("payload", {}).get("day")
    assert type(signed_day) is int and signed_day >= 1
    crafts_by_day[signed_day] = crafts_by_day.get(signed_day, 0) + 1
assert crafts_by_day.get(1, 0) >= 1
assert crafts_by_day.get(_kitchen_fix["day"], 0) >= 1
assert all(0 < count <= workshop_state.DAILY_OFFCUTS
           for count in crafts_by_day.values()), crafts_by_day
_kitchen_workshop = one("The Market Workshop")
_kitchen_docket = workshop_state.normalize(_kitchen_workshop.db.repair_docket)
_kitchen_crafts = list(_kitchen_docket["crafts"])
for old in _kitchen_docket["history"]:
    _kitchen_crafts.extend(old.get("crafts") or [])
assert any(row["event_id"] == _kitchen_fix["forge_event_id"]
           and row["item_id"] == _kitchen_fix["item_id"]
           for row in _kitchen_crafts), "Signed finite Workshop history lost on restart"
assert kitchen_repair_work.player_simmer_allowed(_kitchen_pot)
print("POST_RESTART_GDD_EDGE02_LATER_DAY_FINITE_SOURCE_CHAIN_GREEN")

# Adversarial persistence rollback: the original completed world events
# must prevent another restriction or fitting if the mutable pot state is
# reset or rewound after a genuine server restart.
from world import kitchen_repair_work
_saved_kitchen_attribute = _kitchen_pot.db.kitchen_repair
try:
    _kitchen_pot.db.kitchen_repair = None
    _prior, _why = kitchen_repair_work._prior_completed_pot_event(
        _kitchen_pot, ("professional.innkeep_kitchen_restriction",
                       "professional.smith_kitchen_repair"))
    assert _prior, "Erasing pot Attribute hid original signed restriction"
    assert "conflicts with signed physical history" in kitchen_repair_work.status()
    assert not kitchen_repair_work.player_simmer_allowed(_kitchen_pot), (
        "Erased signed restriction reopened actual player simmering")
    _kitchen_pot.db.kitchen_repair = {
        "condition": "restricted", "restriction": _kitchen_inn, "repair": None}
    _prior, _why = kitchen_repair_work._prior_completed_pot_event(
        _kitchen_pot, ("professional.smith_kitchen_repair",))
    assert _prior, "Rewinding pot Attribute hid completed Smith fitting"
    assert "conflicts with signed physical history" in kitchen_repair_work.status()
    assert not kitchen_repair_work.player_simmer_allowed(_kitchen_pot), (
        "Rewound signed Smith repair reopened actual player simmering")
    _forged_working = dict(_saved_kitchen_attribute)
    _forged_working["repair"] = dict(
        _kitchen_fix, event_id=_kitchen_inn["event_id"])
    _kitchen_pot.db.kitchen_repair = _forged_working
    assert kitchen_repair_edge02.normalize(
        _kitchen_pot.db.kitchen_repair)["condition"] == "working"
    assert not kitchen_repair_work.player_simmer_allowed(_kitchen_pot), (
        "Shape-valid forged Smith event ID reopened player simmering")
    assert "conflicts with signed physical history" in kitchen_repair_work.status(), (
        "Forged Smith event was advertised as a physical repair")
finally:
    _kitchen_pot.db.kitchen_repair = _saved_kitchen_attribute
assert kitchen_repair_work.player_simmer_allowed(_kitchen_pot), (
    "Original signed Smith repair did not restore legitimate simmering")
assert "physically repaired" in kitchen_repair_work.status()
print("POST_RESTART_GDD_EDGE02_SIGNED_SIMMER_SOURCE_GATE_GREEN")
print("POST_RESTART_GDD_EDGE02_SIGNED_ROLLBACK_REFUSAL_GREEN")
print("POST_RESTART_GDD_EDGE02_SIGNED_PHYSICAL_KITCHEN_REPAIR_GREEN")


print("POST_SECOND_RESTART_GDD_EDGE02_FINITE_KITCHEN_GREEN"
      if os.environ.get("FV_EDGE02_SECOND_RESTART") == "1"
      else "POST_FIRST_RESTART_GDD_EDGE02_FINITE_KITCHEN_GREEN")
