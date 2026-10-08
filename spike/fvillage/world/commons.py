"""Persistent village commons, held by the world rather than a player."""

from __future__ import annotations

from evennia import create_script
from evennia.scripts.models import ScriptDB

from world import commons_state


def registry():
    try:
        return ScriptDB.objects.get(db_key="village_commons")
    except ScriptDB.DoesNotExist:
        return create_script(
            "typeclasses.scripts.VillageCommonsRegistry",
            key="village_commons",
            persistent=True,
        )


def current():
    return commons_state.normalize(registry().db.state)


def identity(mask):
    account = getattr(mask, "account", None)
    if not account:
        return None
    return {
        "account_id": account.id,
        "mask_id": mask.id,
        "mask": mask.key,
    }


def _clock():
    try:
        script = ScriptDB.objects.get(db_key="village_time")
        return int(script.db.day or 1), int(
            script.db.hour if script.db.hour is not None else 21
        )
    except ScriptDB.DoesNotExist:
        return 1, 21


def change(mask, verb, notice_id=None, kind=None, text=None):
    actor = identity(mask)
    if not actor:
        return None, "Only a logged-in mask may sign the public commons."
    day, hour = _clock()
    stored = registry()
    state = commons_state.normalize(stored.db.state)
    if verb == "post":
        state, record, error = commons_state.post(
            state, actor, kind, text, day=day, hour=hour
        )
    elif verb == "reply":
        state, record, error = commons_state.reply(
            state, notice_id, actor, text, day=day, hour=hour
        )
    elif verb == "close":
        state, record, error = commons_state.close(
            state, notice_id, actor, text, day=day, hour=hour
        )
    elif verb == "hide":
        account = mask.account
        if not account.check_permstring("Admin") or account.db.substrate != "human":
            return None, "Only human staff may hide a public notice."
        state, record, error = commons_state.hide(
            state, notice_id, actor, text, day=day, hour=hour
        )
    else:
        return None, "Unknown commons action."
    if error:
        return None, error

    # Synchronous write before event fanout. The correspondence remains
    # durable even if a subscriber to the public event system fails.
    stored.db.state = state
    from world.events import publish_world_event
    publish_world_event(
        "civic.commons_" + verb,
        actor=mask,
        payload={
            "notice_id": record["id"] if verb != "reply" else int(notice_id),
            "kind": kind if verb == "post" else None,
            "harbinger": False,
            "chronicle_eligible": False,
        },
    )
    return record, None


def report(mask, notice_id, reason):
    """Send a signed complaint for human review, without hiding automatically."""
    import time
    from commands.village_cmds import _moderation_queue

    complaint = commons_state.clean(reason, 180)
    if not complaint:
        return None, "Supply a brief reason, up to 180 characters."
    notice = commons_state.get_notice(current(), notice_id)
    if not notice or notice.get("hidden"):
        return None, "There is no public notice with that number."
    actor = identity(mask)
    if not actor:
        return None, "A logged-in mask is required."
    from evennia.accounts.models import AccountDB
    owner_id = notice["author"]["account_id"]
    owner = AccountDB.objects.filter(id=owner_id).first()
    record = _moderation_queue().submit({
        "created_at": time.time(),
        "reporter_account": mask.account.key,
        "reporter_account_id": actor["account_id"],
        "reporter_mask": actor["mask"],
        "reporter_mask_id": actor["mask_id"],
        "target": notice["author"]["mask"],
        "target_mask_id": notice["author"]["mask_id"],
        "target_account": owner.key if owner else None,
        "target_account_id": owner_id,
        "reason": "Commons notice #" + str(notice_id) + ": " + complaint,
        "location": mask.location.key if mask.location else None,
        "notice_id": int(notice_id),
    })
    return record, None
