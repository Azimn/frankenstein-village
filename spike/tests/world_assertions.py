"""Runtime assertions executed through evennia shell after a second build."""

from evennia import create_script
from evennia.accounts.models import AccountDB
from evennia.scripts.models import ScriptDB
from evennia.utils import search

from commands.account_cmds import _world_entry_allowed
from commands.village_cmds import PLAYABLE_RUMOR_IDS, load_rumor_seeds


def exact_objects(key):
    return [obj for obj in search.search_object(key) if obj.key == key]


def one(key):
    found = exact_objects(key)
    assert len(found) == 1, f"{key!r}: expected exactly one object, found {len(found)}"
    return found[0]


for room_key in (
    "Inn Common Room",
    "Inn Hallway",
    "Village Square",
    "The Blood of the Vine",
    "Tavern Back Hall",
    "The Lamp Shop",
    "St. Lazarus Church",
):
    one(room_key)

for script_key in (
    "world_event_ledger",
    "rumor_registry",
    "resident_population",
    "room_six",
    "moderation_queue",
    "ambient_life",
    "village_time",
):
    count = ScriptDB.objects.filter(db_key=script_key).count()
    assert count == 1, f"{script_key!r}: expected one script, found {count}"

bram = one("Bram")
assert bram.db.till_kr == 37, "rebuild reset Bram's live till"
assert "bram" in (bram.aliases.all() or []), "Bram alias did not converge"

bread = one("a loaf of bread")
assert bread.db.servings == 2, "rebuild reset live sideboard servings"

well = one("well")
assert "straight" in (well.db.desc or "").lower(), "well rumor has no inspectable evidence"

confessional = one("a confessional box")
assert "lavender" in (confessional.db.desc or "").lower(), (
    "confessional rumor has no inspectable evidence"
)

register = one("register")
register_desc = (register.db.desc or "").lower()
assert "last michaelmas" in register_desc and "crossed out" in register_desc, (
    "register rumor has no inspectable evidence"
)

playable = load_rumor_seeds()
ids = {int(num) for num, _body in playable}
assert ids == set(PLAYABLE_RUMOR_IDS) == {151, 201, 236}, ids
assert len(load_rumor_seeds(playable_only=False)) == 250, "canon rumor corpus changed"

# Production resident population: identity, schedules, fallback, persistence,
# progressive depth, fact claims, isolation, event wakeups, and cheap demotion.
import copy
from collections import Counter
from types import SimpleNamespace

from world.resident_data import FACT_BY_ID, RESIDENTS
from world.residents import (
    advance_population,
    all_residents,
    assign_fact,
    decay_resident_engagement,
    expose_fact_as_rumor,
    facts_known_by_player,
    gather_population_for_mass,
    generic_ask_line,
    get_population_registry,
    record_player_interaction,
    resident_state,
    save_state,
    set_lifecycle,
    set_location_availability,
)

population = all_residents()
assert len(population) == len(RESIDENTS) == 36, len(population)
resident_ids = [npc.db.resident_id for npc in population]
assert len(resident_ids) == len(set(resident_ids)), "duplicate resident stable id"
assert sum(
    npc.typeclass_path == "typeclasses.characters.ResidentNPC"
    for npc in population
) == 30
assert not one("M.").tags.has("resident", category="system"), (
    "M. is the dual-ontology Inn exception, not an IC population resident"
)

by_resident_id = {
    npc.db.resident_id: npc
    for npc in population
}
for stable_id, npc in by_resident_id.items():
    state = resident_state(npc)
    assert state["schema_version"] == 1
    assert state["stable_id"] == stable_id
    assert state["simulation_resolution"] in {
        "automaton", "reactive", "engaged", "focused"
    }
    assert state["character_depth"] in {"D", "C", "B", "A"}
    assert set(state["needs"]) == {
        "fatigue", "hunger", "safety", "affiliation", "duty"
    }

population_registry = get_population_registry()
assert population_registry.db.metrics["population_size"] == 36

# The clean-checkout runner assigned a fact and closed the school before this
# second build. Both must survive the idempotent rebuild.
lark = by_resident_id["lark_vessey"]
qa_fact_id = lark.db.qa_fact_id
assert qa_fact_id, "resident persistence sentinel was not created"
assert any(
    fact["fact_id"] == qa_fact_id
    for fact in resident_state(lark)["facts"]
), "resident fact was erased by rebuild"
assert "lark_vessey" in (
    (population_registry.db.fact_claims or {}).get(qa_fact_id) or []
), "global fact claim was erased by rebuild"
school_state = (population_registry.db.location_states or {}).get("schoolhouse")
assert school_state and not school_state["available"]
assert school_state["reason"] == "school_destroyed"

state_snapshot = {
    stable_id: copy.deepcopy(npc.db.resident_state)
    for stable_id, npc in by_resident_id.items()
}
claims_snapshot = copy.deepcopy(dict(population_registry.db.fact_claims or {}))
locations_snapshot = copy.deepcopy(
    dict(population_registry.db.location_states or {})
)

# Acceptance scenario: Wren follows school without cognition when the routine
# is valid, falls back home with an attributable cause when the school is
# destroyed, and resumes after restoration.
wren = by_resident_id["wren_vessey"]
wstate = resident_state(wren)
wstate["wake_reasons"] = []
wstate["engagement"] = 0.0
wstate["engagement_tier"] = "D"
wstate["simulation_resolution"] = "automaton"
wstate["metrics"]["decision_evaluations"] = 0
save_state(wren, wstate)
set_location_availability("schoolhouse", True)
advance_population(day=2, hour=10, emit=False)
wstate = resident_state(wren)
assert wstate["routine"]["logical_location"] == "schoolhouse"
assert wstate["routine"]["source"] == "schedule"
assert wstate["metrics"]["decision_evaluations"] == 0, (
    "successful automaton routine performed unnecessary cognition"
)

from world.events import publish_world_event
ledger = ScriptDB.objects.get(db_key="world_event_ledger")
school_destroyed = publish_world_event(
    "building_destroyed",
    payload={"location_id": "schoolhouse", "cause": "school_destroyed"},
)
advance_population(day=2, hour=10, emit=False)
wstate = resident_state(wren)
assert wstate["routine"]["logical_location"] == RESIDENTS[
    next(
        i for i, resident in enumerate(RESIDENTS)
        if resident["stable_id"] == "wren_vessey"
    )
]["home_id"]
assert wstate["routine"]["source"] == "fallback"
assert wstate["routine"]["reason"] == "school_destroyed"
assert str(school_destroyed["id"]) in wstate["event_flags"]

school_restored = publish_world_event(
    "building_restored",
    payload={"location_id": "schoolhouse", "cause": "repairs_complete"},
)
advance_population(day=2, hour=10, emit=False)
assert resident_state(wren)["routine"]["logical_location"] == "schoolhouse"

# The butcher resolves directly to the correct current state. Skipped hours
# are not replayed, and a dead resident stops following schedules.
otto = by_resident_id["otto_kessler"]
ostate = resident_state(otto)
ostate["wake_reasons"] = []
ostate["engagement"] = 0.0
ostate["engagement_tier"] = "D"
ostate["simulation_resolution"] = "automaton"
ostate["lifecycle"] = {"status": "active", "reason": None, "changed_day": None}
save_state(otto, ostate)
advance_population(day=2, hour=10, emit=False)
assert resident_state(otto)["routine"]["logical_location"] == "butcher_shop"
before_resolutions = resident_state(otto)["metrics"]["routine_resolutions"]
advance_population(day=2, hour=22, emit=False)
ostate = resident_state(otto)
assert ostate["routine"]["logical_location"].startswith("home:")
assert ostate["metrics"]["routine_resolutions"] == before_resolutions + 1
night_routine = copy.deepcopy(ostate["routine"])
set_lifecycle(otto, "dead", reason="qa lifecycle")
advance_population(day=3, hour=10, emit=False)
assert resident_state(otto)["routine"] == night_routine, (
    "dead resident continued following a schedule"
)

# Sunday Mass gathers a deterministic subset of background households and
# releases them back into their routines afterward. A structured incident can
# mark only the explicit witnesses without simulating everyone present.
mass_ids = gather_population_for_mass(8)
assert len(mass_ids) >= 5
assert "wren_vessey" in mass_ids
assert resident_state(wren)["routine"]["logical_location"] == "church"
mass_witnesses = mass_ids[:3]
mass_event = publish_world_event(
    "qa_mass_incident",
    payload={"resident_ids": mass_witnesses},
)
for stable_id in mass_witnesses:
    assert str(mass_event["id"]) in resident_state(
        by_resident_id[stable_id]
    )["event_flags"]
non_witness = next(
    stable_id for stable_id in mass_ids if stable_id not in mass_witnesses
)
assert str(mass_event["id"]) not in resident_state(
    by_resident_id[non_witness]
)["event_flags"]
advance_population(day=8, hour=12, emit=False)
for stable_id in mass_ids:
    assert resident_state(
        by_resident_id[stable_id]
    )["routine"]["logical_location"] != "church", (
        stable_id,
        "resident trapped at church after Mass",
    )

# Attention can deepen an ordinary background resident without making
# narrative importance or active compute the same thing. A second player gets
# a separate relationship view of the same global person and facts.
marta = by_resident_id["marta_kovacs"]
mstate = resident_state(marta)
mstate["relationships"] = {}
mstate["facts"] = []
mstate["engagement"] = 0.0
mstate["engagement_floor"] = 0.0
mstate["engagement_tier"] = "D"
mstate["simulation_resolution"] = "automaton"
mstate["character_depth"] = "D"
mstate["narrative_importance"] = 0
mstate["last_decay_day"] = 1
save_state(marta, mstate)
alice = SimpleNamespace(id=900001, key="qa_alice", has_account=True)
bob = SimpleNamespace(id=900002, key="qa_bob", has_account=True)
for _ in range(41):
    record_player_interaction(marta, alice, kind="talk")
mstate = resident_state(marta)
assert mstate["engagement_tier"] == "A"
assert mstate["character_depth"] == "A"
assert mstate["simulation_resolution"] == "focused"
assert mstate["narrative_importance"] == 0, (
    "player attention incorrectly became narrative importance"
)
assert resident_state(otto)["relationships"] == state_snapshot[
    "otto_kessler"
]["relationships"], "resident relationship state leaked between NPCs"

secret_line = generic_ask_line(marta, alice, "your secret")
assert secret_line and "Keep this where I put it" in secret_line
alice_facts = facts_known_by_player(marta, alice)
bob_facts = facts_known_by_player(marta, bob)
assert len(alice_facts) == 1
assert bob_facts == [], "second player inherited another player's revelation"
shared_fact_id = alice_facts[0]["fact_id"]
assert any(
    fact["fact_id"] == shared_fact_id
    for fact in resident_state(marta)["facts"]
), "revealed fact was not resident-global canon"

decay_resident_engagement(marta, 120)
mstate = resident_state(marta)
assert mstate["engagement_tier"] == "D"
assert mstate["simulation_resolution"] == "automaton"
assert mstate["character_depth"] == "A", (
    "demotion erased accumulated character depth"
)
assert any(
    fact["fact_id"] == shared_fact_id for fact in mstate["facts"]
), "demotion erased persistent facts"
assert str(alice.id) in mstate["relationships"], (
    "demotion erased player relationship history"
)

# Generate facts across many residents. Ordinary irregularities must dominate,
# forced Gothic assignments must remain unique, and assignment alone must not
# magically publish a rumor.
sample_ids = [
    "marta_kovacs", "otto_kessler", "rada_petrescu", "petru_ionescu",
    "ana_ionescu", "miklos_farkas", "elias_dorn", "ilona_szabo",
    "klara_weiss", "pavel_orban", "milena_varga", "sorin_dragomir",
]
classes = Counter()
for stable_id in sample_ids:
    fact = assign_fact(by_resident_id[stable_id])
    assert fact
    classes[fact["class"]] += 1
assert classes["ordinary"] > classes["serious"] + classes["gothic"], classes

gothic_ids = []
for stable_id in (
    "petru_ionescu", "ana_ionescu", "miklos_farkas",
    "elias_dorn", "ilona_szabo", "klara_weiss",
):
    fact = assign_fact(by_resident_id[stable_id], class_hint="gothic")
    assert fact
    if fact["class"] == "gothic":
        gothic_ids.append(fact["fact_id"])
assert gothic_ids, "forced Gothic pool produced no Gothic assignment"
assert len(gothic_ids) == len(set(gothic_ids)), (
    "unique Gothic secret was assigned to multiple residents"
)
for fact_id in gothic_ids:
    assert FACT_BY_ID[fact_id]["claim"] == "unique"
    assert len((population_registry.db.fact_claims or {}).get(fact_id) or []) == 1

rumor_roots_before = {
    rumor["id"]
    for rumor in (rumor_registry.db.rumors or [])
    if str(rumor.get("subject") or "").startswith("resident_fact:")
}
assert not rumor_roots_before
exposed = expose_fact_as_rumor(
    marta,
    shared_fact_id,
    source_actor="qa witness",
)
assert exposed and exposed["published"]
exposed_id = exposed["rumor_id"]
exposed_root = rumor_registry.get_rumor(exposed_id)
assert exposed_root["subject"] == f"resident_fact:{shared_fact_id}"

# Remove QA-only world events and the explicitly exposed QA rumor, then restore
# resident state so the player-facing telnet pass starts from a normal village.
qa_event_ids = {
    school_destroyed["id"],
    school_restored["id"],
    mass_event["id"],
}
ledger.db.events = [
    event for event in (ledger.db.events or [])
    if event.get("id") not in qa_event_ids
]
rumor_registry.db.rumors = [
    rumor for rumor in (rumor_registry.db.rumors or [])
    if rumor.get("id") != exposed_id
]
rumor_registry.db.transmissions = [
    transmission for transmission in (rumor_registry.db.transmissions or [])
    if transmission.get("rumor_id") != exposed_id
]
tavern = one("The Blood of the Vine")
tavern.db.public_rumor_ids = [
    rid for rid in (tavern.db.public_rumor_ids or [])
    if rid != exposed_id
]
if exposed_root:
    tavern.db.player_rumors = [
        body for body in (tavern.db.player_rumors or [])
        if body != exposed_root["claim"]
    ]
for stable_id, old_state in state_snapshot.items():
    by_resident_id[stable_id].db.resident_state = old_state
population_registry.db.fact_claims = claims_snapshot
set_location_availability("schoolhouse", True)

# Resynchronize physical projection to the actual clock after synthetic time
# travel in the assertions above.
clock = ScriptDB.objects.get(db_key="village_time")
advance_population(
    day=clock.db.day or 1,
    hour=clock.db.hour if clock.db.hour is not None else 21,
    emit=False,
)

# Rumors are structured belief objects with immutable roots and append-only
# transmission provenance. The three live canon hooks seed real NPC beliefs.
rumor_registry = ScriptDB.objects.get(db_key="rumor_registry")
canon_roots = [
    dict(rumor)
    for rumor in (rumor_registry.db.rumors or [])
    if rumor.get("canonical_seed_id") is not None
]
assert {r["canonical_seed_id"] for r in canon_roots} == {151, 201, 236}
assert len(canon_roots) == 3, "rebuild duplicated canonical rumor roots"
for root in canon_roots:
    assert root.get("source_actor"), root
    assert root.get("source_type") == "canon_teller", root
    assert root.get("privacy") == "public", root
    assert len(root.get("variants") or []) == 3, root

magda = one("Magda")
vasile = one("Old Vasile")
janos = one("János")
m = one("M.")
assert magda.tags.has("participant", category="rumor")
assert vasile.tags.has("participant", category="rumor")
assert janos.tags.has("participant", category="rumor")
assert not m.tags.has("participant", category="rumor"), (
    "OOC innkeeper must not participate in IC rumor simulation"
)

root = next(r for r in canon_roots if r["canonical_seed_id"] == 201)
root_before = dict(root)
magda_belief = rumor_registry.belief_for(magda, root["id"])
assert magda_belief, "seeded NPC lacks canon rumor belief"

# Tavern life may already have changed Magda's current version before this
# assertion shell starts. Reset only her current belief to a new direct hearing
# so the controlled provenance chain below has a deterministic three links.
rumor_registry.hear_direct(
    root["id"],
    magda,
    source_label=root["source_actor"],
    source_type=root["source_type"],
    location="The Blood of the Vine",
    force_new=True,
)

first = rumor_registry.transmit(
    root["id"],
    magda,
    vasile,
    location="The Blood of the Vine",
    force_accept=True,
    force_variant_index=0,
)
assert first and first["accepted"]
second = rumor_registry.transmit(
    root["id"],
    vasile,
    janos,
    location="The Blood of the Vine",
    force_accept=True,
    force_variant_index=1,
)
assert second and second["accepted"]
assert rumor_registry.get_rumor(root["id"]) == root_before, (
    "retelling mutated the immutable rumor root"
)
chain = rumor_registry.provenance(second["id"])
assert len(chain) == 3, chain
assert chain[0]["parent_id"] is None
assert chain[1]["parent_id"] == chain[0]["id"]
assert chain[2]["parent_id"] == chain[1]["id"]
assert chain[2]["distortion_generation"] == 2
assert chain[2]["claim"] == root["variants"][1]
known = rumor_registry.known_by(root["id"])
known_ids = {entry.get("id") for entry in known}
assert {magda.id, vasile.id, janos.id}.issubset(known_ids)
assert len(rumor_registry.current_claims(root["id"])) >= 2

from world.rumors import propagate_colocated_npcs
autonomous = propagate_colocated_npcs(announce=False, max_per_room=1)
assert autonomous, "routine-scale NPC rumor propagation produced no retelling"

# Event-generated rumors enter the same registry and retain their event link.
from world.events import publish_world_event
qa_event = publish_world_event(
    "qa_rumor",
    actor=magda,
    payload={"proof": True},
    rumor="The QA bell rang twice.",
)
assert qa_event["status"] == "complete"
qa_rumor_id = qa_event["rumor"]["rumor_id"]
qa_root = rumor_registry.get_rumor(qa_rumor_id)
assert qa_root["original_event_id"] == qa_event["id"]
assert qa_root["source_actor"] == "Magda"
assert qa_root["source_type"] == "npc"
assert qa_root["claim"] == "The QA bell rang twice."

# Remove the synthetic event from the same temporary world used by the telnet
# pass. The assertion proves integration without making QA chatter player-facing.
ledger = ScriptDB.objects.get(db_key="world_event_ledger")
ledger.db.events = [
    event for event in (ledger.db.events or [])
    if event.get("id") != qa_event["id"]
]
rumor_registry.db.rumors = [
    rumor for rumor in (rumor_registry.db.rumors or [])
    if rumor.get("id") != qa_rumor_id
]
rumor_registry.db.transmissions = [
    transmission for transmission in (rumor_registry.db.transmissions or [])
    if transmission.get("rumor_id") != qa_rumor_id
]
tavern = one("The Blood of the Vine")
tavern.db.public_rumor_ids = [
    rid for rid in (tavern.db.public_rumor_ids or [])
    if rid != qa_rumor_id
]
tavern.db.player_rumors = [
    body for body in (tavern.db.player_rumors or [])
    if body != "The QA bell rang twice."
]
for npc in search.search_tag("participant", category="rumor"):
    beliefs = dict(npc.db.rumor_beliefs or {})
    beliefs.pop(str(qa_rumor_id), None)
    npc.db.rumor_beliefs = beliefs

# Moderation lifecycle is tested on an isolated temporary script so running
# these assertions against a real development world cannot pollute its queue.
moderation = create_script(
    "typeclasses.scripts.ModerationQueue",
    key="qa_moderation_queue",
    persistent=False,
)
target = AccountDB.objects.order_by("id").first()
assert target is not None, "bootstrap did not create an account"
old_warnings = list(target.db.compact_warning_actions or [])
old_bans = list(target.db.compact_ban_actions or [])
old_notices = list(target.db.moderation_notices or [])
try:
    target.db.compact_warning_actions = []
    target.db.compact_ban_actions = []
    target.db.moderation_notices = []

    first = moderation.submit({
        "reporter_mask": "qa-reporter",
        "target": target.key,
        "target_account_id": target.id,
        "reason": "first reviewed allegation",
    })
    assert _world_entry_allowed(target), "a raw report must never suspend entry"

    denied, error = moderation.ban_report(first["id"], target, note="too soon")
    assert denied is None and "warning" in error.lower(), (
        "ban was allowed before a human-issued warning"
    )
    assert _world_entry_allowed(target), "failed ban attempt changed entry state"

    warning, error = moderation.warn_report(
        first["id"], target, note="human warning test"
    )
    assert warning and error is None and warning["kind"] == "warning"
    assert warning["id"] in (target.db.compact_warning_actions or [])
    assert _world_entry_allowed(target), "warning incorrectly suspended world entry"

    second = moderation.submit({
        "reporter_mask": "qa-reporter",
        "target": target.key,
        "target_account_id": target.id,
        "reason": "second reviewed allegation",
    })
    ban, error = moderation.ban_report(
        second["id"], target, note="human suspension test"
    )
    assert ban and error is None and ban["kind"] == "ban"
    assert ban["id"] in (target.db.compact_ban_actions or [])
    assert not _world_entry_allowed(target), "reviewed ban did not suspend world entry"

    appeal, error = moderation.submit_appeal(
        target, ban["id"], "please review the suspension"
    )
    assert appeal and error is None and appeal["status"] == "open"
    resolved, error = moderation.resolve_appeal(
        appeal["id"], target, "overturn", note="qa reversal"
    )
    assert resolved and error is None and resolved["outcome"] == "overturn"
    assert ban["id"] not in (target.db.compact_ban_actions or [])
    assert _world_entry_allowed(target), "successful appeal did not restore entry"

    warning_appeal, error = moderation.submit_appeal(
        target, warning["id"], "please review the warning"
    )
    assert warning_appeal and error is None
    resolved, error = moderation.resolve_appeal(
        warning_appeal["id"], target, "overturn", note="qa reversal"
    )
    assert resolved and error is None
    assert warning["id"] not in (target.db.compact_warning_actions or [])

    kinds = [action["kind"] for action in moderation.audit_actions(limit=20)]
    assert "warning" in kinds and "ban" in kinds
    assert kinds.count("appeal_overturn") == 2
finally:
    target.db.compact_warning_actions = old_warnings
    target.db.compact_ban_actions = old_bans
    target.db.moderation_notices = old_notices
    moderation.delete()

print("WORLD_ASSERTIONS_GREEN")
