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
