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
            "witnesses": [], "safety_warning": None,
            "safety_decision": None, "history": []}


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
    warning = raw.get("safety_warning")
    if (hasattr(warning, "get")
            and all(_ident(warning.get(k)) for k in (
                "account_id", "mask_id", "event_id", "source_event_id",
                "cord_id"))
            and _time(day, warning.get("hour"))):
        result["safety_warning"] = dict(warning)
    decision = raw.get("safety_decision")
    if (hasattr(decision, "get") and result["safety_warning"]
            and all(_ident(decision.get(k)) for k in (
                "account_id", "mask_id", "event_id", "warning_event_id"))
            and decision.get("choice") in {"indoor", "cancel"}
            and decision["warning_event_id"] == result["safety_warning"]["event_id"]
            and decision["account_id"] != result["safety_warning"]["account_id"]
            and _time(day, decision.get("hour"))):
        result["safety_decision"] = dict(decision)
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
    if state["performance"] or state["safety_decision"]:
        state["history"].append({
            "day": state["day"],
            "performance": copy.deepcopy(state["performance"]),
            "witnesses": copy.deepcopy(state["witnesses"]),
            "safety_warning": copy.deepcopy(state["safety_warning"]),
            "safety_decision": copy.deepcopy(state["safety_decision"]),
        })
    return {"day": target, "rehearsals": [], "performance": None,
            "witnesses": [], "safety_warning": None, "safety_decision": None,
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
    if state["safety_warning"] and not state["safety_decision"]:
        return state, False, "A Hound warning requires a Performer decision before the show."
    if state["safety_decision"] and state["safety_decision"]["choice"] == "cancel":
        return state, False, "Today's performance was cancelled after a signed warning."
    if state["safety_decision"] and state["safety_decision"]["hour"] > hour:
        return state, False, "The stage decision cannot occur after this performance."
    rehearsal = next((r for r in state["rehearsals"]
                      if r["account_id"] == aid and r["tune"] == tune), None)
    if not rehearsal:
        return state, False, "Rehearse that piece here before performing."
    if rehearsal["hour"] > hour:
        return state, False, "The rehearsal cannot occur after this performance."
    state["performance"] = {
        "account_id": aid, "mask_id": mid, "mask": str(mask)[:70],
        "tune": tune, "hour": hour, "event_id": eid,
        "rehearsal_event_id": rehearsal["event_id"],
        "safety_decision_event_id": (
            state["safety_decision"]["event_id"] if state["safety_decision"] else None),
        "safety_mode": (
            state["safety_decision"]["choice"] if state["safety_decision"] else "normal"),
        # Eligible accounts must have been actually connected and present
        # at performance time. Arriving later this hour is not witnessing.
        "eligible_audience_ids": sorted({
            i for value in audience_account_ids
            if (i := _ident(value)) is not None and i != aid
        })[:MAX_WITNESSES],
    }
    state["witnesses"] = []
    return state, True, None



def verified_hound_source(route, event, marker, *, account_id, mask_id,
                          source_event_id, cord_id, square_id, day, hour,
                          room_name):
    """Pure fail-closed provenance check for the physical treeline warning.

    The adapter separately checks that these values come from the original
    Square, cord and canonical ledger, not player-provided arguments.
    """
    if not all(_ident(v) for v in (
            account_id, mask_id, source_event_id, cord_id, square_id, day)):
        return False
    if not _time(day, hour):
        return False
    if not all(hasattr(v, "get") for v in (route, event, marker)):
        return False
    source = (route.get("field_decisions") or {}).get("hound") or {}
    actor, payload, effect = (
        event.get("actor") or {}, event.get("payload") or {},
        event.get("consequence") or {})
    h = payload.get("hour")
    return (
        route.get("day") == day
        and source.get("account_id") == account_id
        and source.get("event_id") == source_event_id
        and marker.get("account_id") == account_id
        and marker.get("event_id") == source_event_id
        and marker.get("day") == day
        and event.get("id") == source_event_id
        and event.get("kind") == "village.route_protected"
        and event.get("status") == "complete"
        and actor.get("account_id") == account_id
        and actor.get("mask_id") == mask_id
        and payload.get("site") == "red_cord"
        and payload.get("role") == "hound"
        and payload.get("action") == "protect"
        and payload.get("location") == room_name
        and payload.get("day") == day
        and isinstance(h, int) and not isinstance(h, bool)
        and 0 <= h <= hour
        and effect.get("cord_object_id") == cord_id
        and effect.get("square_room_id") == square_id
        and effect.get("role") == "hound"
        and effect.get("action") == "protect"
        and effect.get("day") == day
        and effect.get("caution_marked") is True
    )

def warn(raw, *, day, hour, account_id, mask_id, mask, event_id,
         source_event_id, cord_id):
    """Hound brings a firsthand, signed physical route caution to the Tavern."""
    state = refresh(raw, day)
    if not _time(day, hour) or day < state["day"]:
        return state, False, "The village clock cannot be rewound."
    values = (account_id, mask_id, event_id, source_event_id, cord_id)
    if not all(_ident(v) for v in values):
        return state, False, "A signed physical source and ordinary account are required."
    if state["performance"]:
        return state, False, "A warning cannot retroactively change an actual show."
    if state["safety_warning"]:
        return state, False, "Today's stage warning is already signed."
    state["safety_warning"] = {
        "account_id": int(account_id), "mask_id": int(mask_id),
        "mask": str(mask)[:70], "event_id": int(event_id),
        "source_event_id": int(source_event_id), "cord_id": int(cord_id),
        "hour": int(hour),
    }
    return state, True, None


def adapt(raw, *, day, hour, account_id, mask_id, mask, event_id, choice):
    """Independent Performer elects a bounded indoor show or cancellation."""
    state = refresh(raw, day)
    if not _time(day, hour) or day < state["day"]:
        return state, False, "The village clock cannot be rewound."
    if choice not in {"indoor", "cancel"}:
        return state, False, "Choose indoor or cancel."
    if not all(_ident(v) for v in (account_id, mask_id, event_id)):
        return state, False, "A signed ordinary account is required."
    warning = state["safety_warning"]
    if not warning:
        return state, False, "A verified Hound warning is required first."
    if int(account_id) == warning["account_id"]:
        return state, False, "The Hound cannot also sign the Performer decision."
    if warning["hour"] > hour:
        return state, False, "The Hound warning has not happened yet."
    if state["performance"]:
        return state, False, "The actual show cannot be changed retroactively."
    if state["safety_decision"]:
        return state, False, "Today's stage safety decision is already signed."
    state["safety_decision"] = {
        "account_id": int(account_id), "mask_id": int(mask_id),
        "mask": str(mask)[:70], "event_id": int(event_id),
        "warning_event_id": warning["event_id"], "hour": int(hour),
        "choice": choice,
    }
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


def public_lines(raw, day):
    state = refresh(raw, day)
    lines = ["The Tavern stage", "Today: village day %d." % state["day"]]
    p = state["performance"]
    if state["safety_warning"]:
        w = state["safety_warning"]
        lines.append("A Hound signed a route caution for this stage (event %d; physical source %d)." % (w["event_id"], w["source_event_id"]))
    if state["safety_decision"]:
        d = state["safety_decision"]
        lines.append("A Performer chose %s after the warning (event %d)." % (d["choice"], d["event_id"]))
    if p:
        lines.append("%s actually performed a %s at hour %02d."
                     % (p["mask"], p["tune"], p["hour"]))
        lines.append("%d other player account(s) witnessed it firsthand."
                     % len(state["witnesses"]))
    else:
        lines.append("No public performance has occurred today.")
    if state["history"]:
        last = state["history"][-1]
        if last.get("performance"):
            lines.append("Previous recorded show: %s, day %d."
                         % (last["performance"]["mask"], last["day"]))
        elif last.get("safety_decision"):
            lines.append("Previous stage decision: %s, day %d."
                         % (last["safety_decision"]["choice"], last["day"]))
    lines.append("Hounds: after survey protect at the real red cord, visit here and stage warn.")
    lines.append("Performers: stage adapt indoor|cancel after a Hound warning.")
    lines.append("Performers: stage rehearse ballad|reel, then stage perform ballad|reel.")
    lines.append("During the actual performance hour, other visitors may stage witness.")
    return "\n".join(lines)
