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


def _publish_tavern_rumor(body, *, event_id, actor, kind):
    """Publish a structured public rumor with immutable provenance."""
    import re as _re

    from world.rumors import publish_public_rumor

    schedule_re = _re.compile(r"keeping (different|their old) hours")
    family = "schedule_shift" if schedule_re.search(body or "") else kind
    if actor is None:
        source_actor = kind.replace("_", " ")
        source_type = "world_event"
    else:
        source_actor = getattr(actor, "key", None) or kind.replace("_", " ")
        source_type = "player" if getattr(actor, "has_account", False) else "npc"

    return publish_public_rumor(
        body,
        source_actor=source_actor,
        source_type=source_type,
        original_event_id=event_id,
        subject=kind,
        location="The Blood of the Vine",
        family=family,
    )


def _notify_public_records(event):
    try:
        from world.publications import ingest_event
        refs = ingest_event(event)
        if any(value is not None for value in refs.values()):
            event = get_event_ledger().update_event(
                event["id"],
                publications=refs,
            ) or event
    except Exception:
        pass
    return event


def _notify_resident_population(event):
    try:
        from world.residents import consume_world_event
        consume_world_event(event)
    except Exception:
        pass
    return event


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
        rumor_result = _publish_tavern_rumor(
            rumor,
            event_id=event["id"],
            actor=actor,
            kind=kind,
        )
        event = ledger.update_event(
            event["id"],
            status="rumor_published" if rumor_result["published"] else "rumor_deferred",
            rumor=rumor_result,
        )

    if consequence is None:
        completed = ledger.update_event(event["id"], status="complete")
        completed = _notify_public_records(completed)
        return _notify_resident_population(completed)

    try:
        consequence_result = consequence(event)
    except Exception as err:
        ledger.update_event(
            event["id"],
            status="consequence_failed",
            consequence={"error": type(err).__name__, "message": str(err)},
        )
        raise

    completed = ledger.update_event(
        event["id"],
        status="complete",
        consequence=consequence_result,
        completed_at=time.time(),
    )
    completed = _notify_public_records(completed)
    return _notify_resident_population(completed)
