"""Pure provenance checks for the Healer to Chronicler well warning.

The situation row is a pointer to a source, not proof that the source happened.
Only a completed event in the existing canonical ledger can authorize publication.
No clinical magnitude is copied into the public warning.
"""

from collections.abc import Mapping

def _id(value):
    return type(value) is int and value > 0


def _hour(value):
    return type(value) is int and 0 <= value <= 23


def verify_healer_source(finding, event, *, chronicler_account_id, day, hour, situation_id):
    """Return (accepted, reason), without mutating either source.

    The two professional contributions must come from different authenticated
    accounts. Event kind, completion, actor, situation, object, property, and
    signed clock must agree with the persisted finding. No row-only trust.
    """
    invalid = "The Healer finding has no matching completed signed source event."
    if not isinstance(finding, Mapping) or not isinstance(event, Mapping):
        return False, invalid
    if not _id(chronicler_account_id) or not _id(day) or not _hour(hour):
        return False, "A signed Chronicler account and valid village clock are required."
    if event.get("kind") != "professional.healer_finding_submitted":
        return False, invalid
    if event.get("status") != "complete":
        return False, invalid
    actor = event.get("actor")
    payload = event.get("payload")
    if not isinstance(actor, Mapping) or not isinstance(payload, Mapping):
        return False, invalid
    for key in ("event_id", "account_id", "mask_id", "object_id", "day"):
        if not _id(finding.get(key)):
            return False, invalid
    if not _hour(finding.get("hour")):
        return False, invalid
    if not _id(actor.get("account_id")) or not _id(actor.get("mask_id")):
        return False, invalid
    if not _id(event.get("id")) or event["id"] != finding["event_id"]:
        return False, invalid
    if actor["account_id"] != finding["account_id"]:
        return False, invalid
    if actor["mask_id"] != finding["mask_id"] or actor.get("mask") != finding.get("mask"):
        return False, invalid
    if actor["account_id"] == chronicler_account_id:
        return False, "A separate account must publish the Healer's finding."
    if finding.get("calling") != "healer":
        return False, invalid
    if finding.get("object_key") != "a cluster of mushrooms":
        return False, invalid
    if finding.get("property") != "toxin":
        return False, invalid
    if type(finding.get("value")) not in (int, float) or finding["value"] <= 0:
        return False, invalid
    expected = {
        "situation_id": situation_id,
        "source_object_id": finding["object_id"],
        "source_object_key": finding["object_key"],
        "mechanical_property": finding["property"],
        "mechanical_value": finding["value"],
        "professional_calling": "healer",
        "day": finding["day"],
        "hour": finding["hour"],
        "publicity": "private",
        "harbinger": False,
        "chronicle_eligible": False,
    }
    if any(payload.get(key) != value for key, value in expected.items()):
        return False, invalid
    if (finding["day"], finding["hour"]) > (day, hour):
        return False, "The signed Healer finding is later than the village clock."
    return True, None
