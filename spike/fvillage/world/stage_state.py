"""Persistent public Tavern music work, without a fabricated audience.

This is a small, renewable, physical profession loop. A rehearsal is a real
signed action and a show occurs only when a Performer actually plays. Other
accounts may explicitly witness it during that village hour.
"""
from __future__ import annotations

import copy

TUNES = ("ballad", "reel")
MAX_HISTORY = 32
MAX_REHEARSALS = 12
MAX_WITNESSES = 20
MAX_INQUIRIES = 6


def _ident(value):
    if isinstance(value, bool):
        return None
    try:
        value = int(value)
    except (TypeError, ValueError, OverflowError):
        return None
    return value if value > 0 else None


def _time(day, hour):
    d = _ident(day)
    if isinstance(hour, bool):
        return None
    try:
        h = int(hour)
    except (TypeError, ValueError, OverflowError):
        return None
    return (d, h) if d and 0 <= h <= 23 else None


def fresh(day=1):
    return {"day": day, "rehearsals": [], "performance": None,
            "witnesses": [], "inquiries": [], "history": []}


def normalize(raw):
    if not hasattr(raw, "get"):
        return fresh()
    try:
        day = max(1, int(raw.get("day") or 1))
    except (TypeError, ValueError, OverflowError):
        day = 1
    result = fresh(day)
    for r in list(raw.get("rehearsals") or [])[-MAX_REHEARSALS * 2:]:
        if not hasattr(r, "get") or r.get("tune") not in TUNES:
            continue
        if (_ident(r.get("account_id")) and _ident(r.get("mask_id"))
                and _ident(r.get("event_id")) and _time(day, r.get("hour"))):
            result["rehearsals"].append(dict(r))
    result["rehearsals"] = result["rehearsals"][-MAX_REHEARSALS:]
    perf = raw.get("performance")
    if (hasattr(perf, "get") and perf.get("tune") in TUNES
            and _ident(perf.get("event_id"))
            and _ident(perf.get("account_id"))
            and _ident(perf.get("mask_id"))
            and _time(day, perf.get("hour"))):
        result["performance"] = dict(perf)
        for r in list(raw.get("witnesses") or [])[-MAX_WITNESSES * 2:]:
            if (hasattr(r, "get") and _ident(r.get("account_id"))
                    and _ident(r.get("event_id"))):
                result["witnesses"].append(dict(r))
    result["witnesses"] = result["witnesses"][-MAX_WITNESSES:]
    if result["performance"]:
        show = result["performance"]
        witness_ids = sorted(r["event_id"] for r in result["witnesses"])
        for row in list(raw.get("inquiries") or [])[-MAX_INQUIRIES * 2:]:
            if not hasattr(row, "get"):
                continue
            aid, mid, eid = (_ident(row.get(k)) for k in
                             ("account_id", "mask_id", "event_id"))
            stage_id = _ident(row.get("stage_object_id"))
            source_id = _ident(row.get("source_event_id"))
            observed = _time(day, row.get("hour"))
            signed_ids = row.get("witness_event_ids")
            if (not all((aid, mid, eid, stage_id, source_id))
                    or not observed or observed[1] < show["hour"]
                    or aid == show["account_id"]
                    or source_id != show["event_id"]
                    or not isinstance(signed_ids, (list, tuple))
                    or sorted(signed_ids) != witness_ids
                    or any(r["account_id"] == aid for r in result["inquiries"])):
                continue
            result["inquiries"].append({
                "account_id": aid, "mask_id": mid, "event_id": eid,
                "mask": str(row.get("mask") or "")[:70],
                "hour": observed[1], "source_event_id": source_id,
                "stage_object_id": stage_id,
                "witness_event_ids": list(witness_ids),
                "firsthand_witness": any(
                    r["account_id"] == aid for r in result["witnesses"]
                ),
            })
    result["inquiries"] = result["inquiries"][-MAX_INQUIRIES:]
    result["history"] = [
        copy.deepcopy(r) for r in list(raw.get("history") or [])
        if hasattr(r, "get") and _ident(r.get("day"))
    ][-MAX_HISTORY:]
    return result


def refresh(raw, day):
    state = normalize(raw)
    target = _ident(day)
    if not target or target <= state["day"]:
        return state
    if state["performance"]:
        state["history"].append({
            "day": state["day"],
            "performance": copy.deepcopy(state["performance"]),
            "witnesses": copy.deepcopy(state["witnesses"]),
            "inquiries": copy.deepcopy(state["inquiries"]),
        })
    return {"day": target, "rehearsals": [], "performance": None,
            "witnesses": [], "inquiries": [],
            "history": state["history"][-MAX_HISTORY:]}


def rehearse(raw, *, day, hour, account_id, mask_id, mask, tune, event_id):
    state = refresh(raw, day)
    if not _time(day, hour) or day < state["day"]:
        return state, False, "The village clock cannot be rewound."
    if tune not in TUNES:
        return state, False, "Choose ballad or reel."
    aid, mid, eid = _ident(account_id), _ident(mask_id), _ident(event_id)
    if not (aid and mid and eid):
        return state, False, "An actual player and signed world event are required."
    if any(r["account_id"] == aid and r["tune"] == tune
           for r in state["rehearsals"]):
        return state, False, "You already rehearsed that piece today."
    if len(state["rehearsals"]) >= MAX_REHEARSALS:
        return state, False, "The stage's rehearsal book is full today."
    state["rehearsals"].append({
        "account_id": aid, "mask_id": mid, "mask": str(mask)[:70],
        "tune": tune, "hour": hour, "event_id": eid,
    })
    return state, True, None


def perform(raw, *, day, hour, account_id, mask_id, mask, tune, event_id,
            audience_account_ids=()):
    state = refresh(raw, day)
    if not _time(day, hour) or day < state["day"]:
        return state, False, "The village clock cannot be rewound."
    if tune not in TUNES:
        return state, False, "Choose ballad or reel."
    aid, mid, eid = _ident(account_id), _ident(mask_id), _ident(event_id)
    if not (aid and mid and eid):
        return state, False, "An actual player and signed world event are required."
    if state["performance"]:
        return state, False, "Today's public performance has already taken place."
    rehearsal = next((r for r in state["rehearsals"]
                      if r["account_id"] == aid and r["tune"] == tune), None)
    if not rehearsal:
        return state, False, "Rehearse that piece here before performing."
    state["performance"] = {
        "account_id": aid, "mask_id": mid, "mask": str(mask)[:70],
        "tune": tune, "hour": hour, "event_id": eid,
        "rehearsal_event_id": rehearsal["event_id"],
        # Eligible accounts must have been actually connected and present
        # at performance time. Arriving later this hour is not witnessing.
        "eligible_audience_ids": sorted({
            i for value in audience_account_ids
            if (i := _ident(value)) is not None and i != aid
        })[:MAX_WITNESSES],
    }
    state["witnesses"] = []
    return state, True, None


def witness(raw, *, day, hour, account_id, mask_id, mask, event_id):
    state = refresh(raw, day)
    if not _time(day, hour) or day < state["day"]:
        return state, False, "The village clock cannot be rewound."
    aid, mid, eid = _ident(account_id), _ident(mask_id), _ident(event_id)
    if not (aid and mid and eid):
        return state, False, "An actual player and signed world event are required."
    show = state["performance"]
    if not show or show["hour"] != hour:
        return state, False, "No live performance is taking place this hour."
    if show["account_id"] == aid:
        return state, False, "Performers cannot sign as their own audience."
    if aid not in show.get("eligible_audience_ids", []):
        return state, False, "Only an audience member present for the actual performance may witness."
    if any(r["account_id"] == aid for r in state["witnesses"]):
        return state, False, "You have already witnessed this performance."
    if len(state["witnesses"]) >= MAX_WITNESSES:
        return state, False, "The witness register is full."
    state["witnesses"].append({
        "account_id": aid, "mask_id": mid,
        "mask": str(mask)[:70], "event_id": eid,
    })
    return state, True, None



def investigate(raw, *, day, hour, account_id, mask_id, mask, event_id,
                source_event_id, source_account_id, source_mask_id,
                source_hour, source_tune, witness_event_ids, stage_object_id):
    """An independent Detective records a qualified, non-exonerating timeline.

    This pure transition cannot authenticate a ledger event. The Evennia
    adapter must verify every source event, actor and physical stage before
    invoking it, including again inside the signed consequence.
    """
    state = refresh(raw, day)
    if not _time(day, hour) or day < state["day"]:
        return state, False, "The village clock cannot be rewound."
    aid, mid, eid = _ident(account_id), _ident(mask_id), _ident(event_id)
    source = _ident(source_event_id)
    source_account = _ident(source_account_id)
    source_mask = _ident(source_mask_id)
    stage_id = _ident(stage_object_id)
    if not all((aid, mid, eid, source, source_account, source_mask, stage_id)):
        return state, False, "A real Detective, stage and signed source are required."
    show = state["performance"]
    if not show:
        return state, False, "There is no actual performance to investigate today."
    if (source != show["event_id"]
            or source_account != show["account_id"]
            or source_mask != show["mask_id"]
            or source_hour != show["hour"]
            or source_tune != show["tune"]):
        return state, False, "The claimed performance does not match the signed stage record."
    if hour < show["hour"]:
        return state, False, "A Detective cannot inspect a performance from the future."
    if aid == show["account_id"]:
        return state, False, "The performing account cannot investigate its own show."
    if any(row["account_id"] == aid for row in state["inquiries"]):
        return state, False, "This Detective already investigated the performance."
    if len(state["inquiries"]) >= MAX_INQUIRIES:
        return state, False, "The stage inquiry docket is full today."
    if not isinstance(witness_event_ids, (list, tuple)):
        return state, False, "Verified witness source events are required."
    actual = sorted(row["event_id"] for row in state["witnesses"])
    supplied = sorted(witness_event_ids)
    if supplied != actual or any(_ident(value) is None for value in supplied):
        return state, False, "Witness evidence does not match the actual stage register."
    state["inquiries"].append({
        "account_id": aid, "mask_id": mid, "mask": str(mask)[:70],
        "event_id": eid, "hour": hour, "source_event_id": source,
        "stage_object_id": stage_id, "witness_event_ids": list(actual),
        "firsthand_witness": any(
            row["account_id"] == aid for row in state["witnesses"]
        ),
    })
    return state, True, None

def public_lines(raw, day):
    state = refresh(raw, day)
    lines = ["The Tavern stage", "Today: village day %d." % state["day"]]
    p = state["performance"]
    if p:
        lines.append("%s actually performed a %s at hour %02d."
                     % (p["mask"], p["tune"], p["hour"]))
        lines.append("%d other player account(s) witnessed it firsthand."
                     % len(state["witnesses"]))
    else:
        lines.append("No public performance has occurred today.")
    if state["inquiries"]:
        lines.append("%d independent Detective stage inquiry record(s); "
                     "a show is not proof of an alibi." % len(state["inquiries"]))
        latest = state["inquiries"][-1]
        lines.append("Latest inquiry: %s inspected the platform with %d "
                     "signed firsthand witness(es)."
                     % (latest["mask"], len(latest["witness_event_ids"])))
    if state["history"]:
        last = state["history"][-1]
        lines.append("Previous recorded show: %s, day %d."
                     % (last["performance"]["mask"], last["day"]))
    lines.append("Performers: stage rehearse ballad|reel, then stage perform ballad|reel.")
    lines.append("During the actual performance hour, other visitors may stage witness.")
    lines.append("Detectives may inspect the platform and use stage investigate "
                 "after a real show; an inquiry never certifies innocence.")
    return "\n".join(lines)
