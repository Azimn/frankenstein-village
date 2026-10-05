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
