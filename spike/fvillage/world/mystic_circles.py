"""Guild circles and objectively occurring, uncommon churchyard anomaly.

Pure rules, independent of Evennia. One specified night per village week
the grave inscription changes without tooling. Everyone sees the same stone,
but a player's explanation never upgrades itself into a certified cause.
"""
from __future__ import annotations

import copy

MAX_STUDIES = 48
METHODS = frozenset({"measure", "vigil"})
NPCS = {
    "beatrice_harcourt": {
        "circle": "The Correspondents",
        "opening": (
            "I keep times, witnesses and measurements. I am not prepared "
            "to call every puzzling stone a haunting."
        ),
        "approach": (
            "The old lettering needs three independent readings, not an "
            "exciting story. Mirela's oral history may tell me where to look, "
            "but I will not file it as a measurement."
        ),
        "disagreement": (
            "Mirela believes I failed to credit the family who first saw "
            "the mark change. On that particular point, she is correct."
        ),
    },
    "mirela_dobre": {
        "circle": "The Hearth Circle",
        "opening": (
            "A grave belongs to a family before it belongs to anybody's "
            "notebook. That does not make me blind to a trick."
        ),
        "approach": (
            "Ask who tended the grave and which visits were witnessed. "
            "The customs matter. A laboratory can measure the wrong thing "
            "with excellent precision."
        ),
        "disagreement": (
            "Miss Harcourt keeps a fine clock. I would gladly use it. "
            "She might first ask before printing a family's names."
        ),
    },
}


def manifested(day, hour):
    """A world-clock condition, not an account/personality roll."""
    try:
        d, h = int(day), int(hour)
    except (TypeError, ValueError, OverflowError):
        return False
    return d >= 1 and (d - 1) % 7 == 0 and h in (21, 22)


def manifestation_text(day, hour):
    if not manifested(day, hour):
        return ""
    return (
        "For a moment, while no hand or chisel touches the stone, the "
        "older engraved date advances by one day. The groove itself "
        "changes shape beneath the moss, not merely its shadow. "
        "The original cutting slowly returns."
    )


def _id(x):
    if isinstance(x, bool):
        return None
    try:
        number = int(x)
    except (TypeError, ValueError, OverflowError):
        return None
    return number if number > 0 else None


def normalize(raw):
    if not hasattr(raw, "get"):
        return {"studies": []}
    rows = []
    try:
        candidates = list(raw.get("studies") or [])
    except (TypeError, ValueError):
        candidates = []
    for item in candidates[-MAX_STUDIES * 2:]:
        if not hasattr(item, "get") or item.get("method") not in METHODS:
            continue
        d = _id(item.get("day"))
        a = _id(item.get("account_id"))
        m = _id(item.get("mask_id"))
        e = _id(item.get("event_id"))
        if None in (d, a, m, e):
            continue
        rows.append({
            "day": d, "account_id": a, "mask_id": m, "event_id": e,
            "mask": str(item.get("mask") or "")[:70],
            "method": item["method"],
        })
    return {"studies": rows[-MAX_STUDIES:]}


def record(raw, method, *, day, account_id, mask_id, mask, event_id):
    state = normalize(raw)
    if method not in METHODS:
        return state, False, "Choose a measured study or a vigil."
    aid, mid, event, d = map(_id, (account_id, mask_id, event_id, day))
    if None in (aid, mid, event, d):
        return state, False, "Signed identity and village day are required."
    if any(row["day"] > d for row in state["studies"]):
        return state, False, "A later churchyard study is already recorded."
    if any(row["day"] == d and row["account_id"] == aid
           for row in state["studies"]):
        return state, False, "Your account has already filed a study tonight."
    state["studies"].append({
        "day": d, "account_id": aid, "mask_id": mid,
        "mask": str(mask or "")[:70],
        "method": method, "event_id": event,
    })
    state["studies"] = state["studies"][-MAX_STUDIES:]
    return state, True, None


def dialogue(resident_id, topic=""):
    source = NPCS.get(resident_id)
    if not source:
        return None
    t = str(topic or "").lower()
    if any(x in t for x in ("mirela", "harcourt", "disagree", "rival", "credit")):
        return source["disagreement"]
    if any(x in t for x in ("grave", "mystic", "method", "spirit", "research",
                             "ritual", "folklore", "society", "guild")):
        return source["approach"]
    return source["opening"]


def public_lines(raw):
    state = normalize(raw)
    lines = [
        "The Guild of Mystics is a social guild, not a test of ancestry.",
        "The Correspondents and the Hearth Circle disagree over methods. "
        "Neither controls the profession.",
    ]
    if state["studies"]:
        row = state["studies"][-1]
        action = "measured study" if row["method"] == "measure" else "vigil"
        lines.append(
            f"Most recent signed {action}: {row['mask']}, village "
            f"day {row['day']}, world event {row['event_id']}. "
            "The cause remains unsettled."
        )
    return lines
