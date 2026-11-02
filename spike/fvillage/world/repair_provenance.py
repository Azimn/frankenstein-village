"""Verify the existing Broken Mantle ledger chain without creating another store.

Situation rows are references, never proof by themselves. Every professional
handoff must match a completed, actor-signed canonical event. Pure functions
allow hostile or corrupted records to be tested without an Evennia server.
"""
from __future__ import annotations


def _positive(value):
    return type(value) is int and value > 0


def _signed(row, event, kind, calling, situation_id):
    if not hasattr(row, "get") or not hasattr(event, "get"):
        return False
    actor = event.get("actor")
    payload = event.get("payload")
    if not hasattr(actor, "get") or not hasattr(payload, "get"):
        return False
    return (
        _positive(row.get("event_id"))
        and event.get("id") == row["event_id"]
        and event.get("kind") == kind
        and event.get("status") == "complete"
        and row.get("calling") == calling
        and payload.get("professional_calling") == calling
        and payload.get("situation_id") == situation_id
        and _positive(row.get("mask_id"))
        and actor.get("mask_id") == row["mask_id"]
        and actor.get("mask") == row.get("mask")
        and _positive(actor.get("account_id"))
        and _positive(row.get("day"))
        and type(row.get("hour")) is int
        and 0 <= row["hour"] < 24
    )


def verify_diagnosis(row, event, *, lamp_id, situation_id, part):
    """A real Smith inspected the exact physical lamp."""
    return (
        _signed(row, event, "professional.smith_lamp_diagnosis",
                "smith", situation_id)
        and _positive(lamp_id)
        and row.get("lamp_object_id") == lamp_id
        and event["payload"].get("lamp_object_id") == lamp_id
        and row.get("required_part") == part
        and event["payload"].get("required_part") == part
        and row.get("finding") == event["payload"].get("finding")
    )


def verify_procurement(row, event, diagnosis, diagnosis_event, *,
                       stock_id, situation_id, part):
    """A separate Merchant actually spent one matching finite stock unit."""
    if not (
        _signed(row, event, "professional.merchant_repair_procurement",
                "merchant", situation_id)
        and _positive(stock_id)
        and row.get("resource_object_id") == stock_id
        and event["payload"].get("resource_object_id") == stock_id
        and row.get("required_part") == part
        and event["payload"].get("required_part") == part
        and _positive(row.get("source_smith_event_id"))
        and row["source_smith_event_id"] == diagnosis.get("event_id")
        and event["payload"].get("source_smith_event_id")
        == diagnosis.get("event_id")
        and hasattr(diagnosis_event, "get")
        and hasattr(diagnosis_event.get("actor"), "get")
        and event["actor"]["account_id"]
        != diagnosis_event["actor"].get("account_id")
    ):
        return False
    # The payload describes intent. Only the committed consequence proves that
    # the finite physical tray was actually decremented by the signed event.
    consequence = event.get("consequence")
    if not hasattr(consequence, "get"):
        return False
    before, after = row.get("units_before"), row.get("units_after")
    return (
        type(before) is int and type(after) is int
        and before > 0 and after == before - 1
        and event["payload"].get("units_before") == before
        and event["payload"].get("units_after") == after
        and row.get("unit_worth") == event["payload"].get("unit_worth")
        and _positive(consequence.get("resource_object_id"))
        and consequence.get("resource_object_id") == stock_id
        and type(consequence.get("units_before")) is int
        and type(consequence.get("units_after")) is int
        and consequence.get("units_before") == before
        and consequence.get("units_after") == after
        and _positive(consequence.get("source_smith_event_id"))
        and consequence.get("source_smith_event_id") == diagnosis["event_id"]
    )
