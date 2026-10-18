"""Cheap, source-aware civic recognition for persistent village residents.

Residents know the *public Square board*, not hidden events or every player's
movements. A mask must have actually signed today's physical route inspection
before an NPC may recognize their work. The relation bonus is limited to one
encounter per NPC/mask/day, survives restart and cannot cross IC masks.
"""
from __future__ import annotations

from world import route_surveys
from world.discoveries import LANDMARKS

MAX_RECOGNITIONS = 128

_SITE_REMARKS = {
    "grave_marker": "Graves are easier to misread than people think.",
    "red_cord": "The north edge changes faster than an old map does.",
    "market_scale": "Traders notice when somebody checks the weights.",
    "river_gauge": "The river never tells you its depth twice alike.",
}


def signed_checkpoint(raw, day, *, account_id, mask_name):
    """Return one genuinely signed checkpoint, never rumors or other masks."""
    if type(account_id) is not int or account_id <= 0:
        return None
    if not isinstance(mask_name, str) or not mask_name:
        return None
    try:
        state = route_surveys.refresh(raw, day)
    except (ValueError, TypeError, KeyError):
        return None
    if state["day"] != day:
        return None
    for ident in route_surveys.SITES:
        report = state["reports"].get(ident)
        if (report and report["account_id"] == account_id
                and report["mask"] == mask_name
                and type(report["event_id"]) is int
                and report["event_id"] > 0):
            return {
                "site": ident, "event_id": report["event_id"],
                "room": LANDMARKS[ident]["room"],
                "count": len(state["reports"]),
                "complete": route_surveys.complete(state),
            }
    return None


def public_route_line(raw, day, *, account_id, mask_name):
    """Only statements supportable by the named public report are spoken."""
    try:
        state = route_surveys.refresh(raw, day)
        count = len(state["reports"]) if state["day"] == day else 0
    except (ValueError, TypeError, KeyError):
        count = 0
    signed = signed_checkpoint(
        raw, day, account_id=account_id, mask_name=mask_name
    )
    if signed:
        return (
            f"The Square's board carries your signed inspection from "
            f"{signed['room']}. I wasn't there to watch you, but the record "
            "means somebody actually walked that ground. "
            + _SITE_REMARKS[signed["site"]]
            + (
                " All four checkpoints have reports today."
                if signed["complete"] else
                f" The village still needs {len(route_surveys.SITES)-count} "
                "more checkpoint reports."
            )
        ), signed
    return (
        f"The Square's public board shows {count} of "
        f"{len(route_surveys.SITES)} road checkpoints today. "
        "A name only belongs on it after the traveler checks the place."
    ), None


def normalized_recognitions(raw):
    result = []
    seen = set()
    try:
        records = list(raw or [])[-(MAX_RECOGNITIONS * 3):]
    except (TypeError, ValueError):
        return []
    for row in records:
        if not hasattr(row, "get"):
            continue
        try:
            mask_id = int(row["mask_id"])
            day = int(row["day"])
            event_id = int(row["event_id"])
        except (KeyError, ValueError, TypeError, OverflowError):
            continue
        site = row.get("site")
        if (mask_id <= 0 or day < 1 or event_id <= 0
                or not isinstance(site, str) or site not in LANDMARKS):
            continue
        marker = (mask_id, day)
        if marker in seen:
            continue
        seen.add(marker)
        result.append({
            "mask_id": mask_id, "day": day,
            "site": site, "event_id": event_id,
        })
    return result[-MAX_RECOGNITIONS:]


def mark_recognized(raw, *, mask_id, day, site, event_id):
    records = normalized_recognitions(raw)
    try:
        mask_id, day, event_id = int(mask_id), int(day), int(event_id)
    except (TypeError, ValueError, OverflowError):
        return records, False
    if (mask_id <= 0 or day < 1 or event_id <= 0
            or site not in LANDMARKS):
        return records, False
    if any(row["mask_id"] == mask_id and row["day"] == day
           for row in records):
        return records, False
    records.append({
        "mask_id": mask_id, "day": day, "site": site, "event_id": event_id,
    })
    return records[-MAX_RECOGNITIONS:], True


def remembered_help(raw, *, mask_id, current_day):
    """A returning relationship remembers help, without retelling secrets."""
    records = [
        row for row in normalized_recognitions(raw)
        if row["mask_id"] == mask_id and row["day"] <= current_day
    ]
    if not records:
        return None
    last = max(records, key=lambda row: (row["day"], row["event_id"]))
    if last["day"] == current_day:
        return (
            "You've already put your name to the public roads survey today. "
            "That is more useful than another guess at what lies outside."
        )
    return (
        f"I remember you helping with the route survey on village day "
        f"{last['day']}. Today's roads haven't checked themselves."
    )
