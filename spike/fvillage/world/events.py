"""Generic persistent-event pipeline.

Ordering is deliberate and invariant:

    event -> canonical ledger -> optional rumor -> consequence

The ledger records intent before any mutable world state changes. This gives
later systems a stable causal record even when a consequence fails halfway.
"""

from __future__ import annotations

import time

from evennia import create_script
from evennia.scripts.models import ScriptDB
from evennia.utils import search


LEDGER_KEY = "world_event_ledger"


def get_event_ledger():
    try:
        return ScriptDB.objects.get(db_key=LEDGER_KEY)
    except ScriptDB.DoesNotExist:
        return create_script(
            "typeclasses.scripts.WorldEventLedger",
            key=LEDGER_KEY,
            persistent=True,
        )


def _actor_ref(actor):
    if actor is None:
        return None
    account = getattr(actor, "account", None)
    return {
        "mask": getattr(actor, "key", None),
        "mask_id": getattr(actor, "id", None),
        "account_id": getattr(account, "id", None),
    }


def _publish_tavern_rumor(body):
    """Publish through the existing player-rumor surface."""
    found = [
        obj for obj in search.search_object("The Tavern")
        if obj.key == "The Tavern"
    ]
    if not found:
        return {"published": False, "reason": "tavern_missing", "body": body}
    tavern = found[0]
    rumors = list(tavern.db.player_rumors or [])
    if body not in rumors:
        rumors.append(body)
        tavern.db.player_rumors = rumors[-50:]
    return {"published": True, "location": tavern.key, "body": body}


def publish_world_event(
    kind,
    *,
    actor=None,
    payload=None,
    rumor=None,
    consequence=None,
):
    """Run one event through the canonical pipeline.

    `consequence` is a callable accepting the already-ledgered event dict.
    Its return value must be database-serializable and is written back to the
    event record. Exceptions are recorded as a failed consequence and raised.
    """
    ledger = get_event_ledger()
    event = ledger.begin_event({
        "kind": kind,
        "recorded_at": time.time(),
        "actor": _actor_ref(actor),
        "payload": dict(payload or {}),
        "rumor": None,
        "consequence": None,
    })

    if rumor:
        rumor_result = _publish_tavern_rumor(rumor)
        event = ledger.update_event(
            event["id"],
            status="rumor_published" if rumor_result["published"] else "rumor_deferred",
            rumor=rumor_result,
        )

    if consequence is None:
        return ledger.update_event(event["id"], status="complete")

    try:
        consequence_result = consequence(event)
    except Exception as err:
        ledger.update_event(
            event["id"],
            status="consequence_failed",
            consequence={"error": type(err).__name__, "message": str(err)},
        )
        raise

    return ledger.update_event(
        event["id"],
        status="complete",
        consequence=consequence_result,
        completed_at=time.time(),
    )
