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
            "witnesses": [], "history": []}


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
        result["performance"]["reviews"] = [
            dict(r) for r in list(perf.get("reviews") or [])
            if hasattr(r, "get") and r.get("verdict") in ("praise", "critique")
            and _ident(r.get("account_id")) and _ident(r.get("mask_id"))
            and _ident(r.get("event_id")) and _ident(r.get("witness_event_id"))
            and _ident(r.get("performance_event_id"))
        ][:8]
        for r in list(raw.get("witnesses") or [])[-MAX_WITNESSES * 2:]:
            if (hasattr(r, "get") and _ident(r.get("account_id"))
                    and _ident(r.get("event_id"))):
                result["witnesses"].append(dict(r))
    result["witnesses"] = result["witnesses"][-MAX_WITNESSES:]
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
        })
    return {"day": target, "rehearsals": [], "performance": None,
            "witnesses": [], "history": state["history"][-MAX_HISTORY:]}


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



MAX_REVIEWS = 8
VERDICTS = ("praise", "critique")


def _signed_stage_event(event, *, kind, event_id, account_id, mask_id, day, hour=None, tune=None):
    """Check a completed canonical source, not just a copied event number."""
    if not hasattr(event, "get") or event.get("kind") != "village.stage_" + kind:
        return False
    if event.get("status") != "complete" or _ident(event.get("id")) != _ident(event_id):
        return False
    actor, payload = event.get("actor") or {}, event.get("payload") or {}
    if not hasattr(actor, "get") or not hasattr(payload, "get"):
        return False
    if (_ident(actor.get("account_id")) != _ident(account_id)
            or _ident(actor.get("mask_id")) != _ident(mask_id)
            or _ident(payload.get("day")) != _ident(day)):
        return False
    if hour is not None and payload.get("hour") != hour:
        return False
    if tune is not None and payload.get("tune") != tune:
        return False
    return True


def verify_review_sources(show, witness, events, *, day):
    """A review needs actual rehearsal, performance and firsthand witness."""
    if not hasattr(show, "get") or not hasattr(witness, "get") or not hasattr(events, "get"):
        return False
    if _ident(show.get("account_id")) == _ident(witness.get("account_id")):
        return False
    performance = events.get("performance")
    rehearsal = events.get("rehearsal")
    witnessed = events.get("witness")
    if not _signed_stage_event(
        performance, kind="perform", event_id=show.get("event_id"),
        account_id=show.get("account_id"), mask_id=show.get("mask_id"),
        day=day, hour=show.get("hour"), tune=show.get("tune"),
    ):
        return False
    if not _signed_stage_event(
        rehearsal, kind="rehearse", event_id=show.get("rehearsal_event_id"),
        account_id=show.get("account_id"), mask_id=show.get("mask_id"),
        day=day, tune=show.get("tune"),
    ):
        return False
    if not _signed_stage_event(
        witnessed, kind="witness", event_id=witness.get("event_id"),
        account_id=witness.get("account_id"), mask_id=witness.get("mask_id"),
        day=day, hour=show.get("hour"),
    ):
        return False
    return (
        (performance.get("consequence") or {}).get("performance_event_id")
        == show.get("event_id")
        and (witnessed.get("consequence") or {}).get("performance_event_id")
        == show.get("event_id")
    )


def verify_review_event(review, event, show):
    """A contest must reference a completed, source-bound Chronicler review."""
    if not _signed_stage_event(
        event, kind="review", event_id=review.get("event_id"),
        account_id=review.get("account_id"), mask_id=review.get("mask_id"),
        day=review.get("day"), hour=review.get("hour"),
    ):
        return False
    payload, consequence = event.get("payload") or {}, event.get("consequence") or {}
    return (
        payload.get("source_performance_event_id") == show.get("event_id")
        and payload.get("source_witness_event_id") == review.get("witness_event_id")
        and payload.get("verdict") == review.get("verdict")
        and consequence.get("performance_event_id") == show.get("event_id")
        and consequence.get("review_event_id") == review.get("event_id")
    )


def review(raw, *, day, hour, account_id, mask_id, mask, event_id,
           verdict, performance_event_id, witness_event_id):
    state = refresh(raw, day)
    if not _time(day, hour) or day < state["day"]:
        return state, False, "The village clock cannot be rewound."
    if verdict not in VERDICTS:
        return state, False, "Choose praise or critique."
    aid, mid, eid = _ident(account_id), _ident(mask_id), _ident(event_id)
    show = state["performance"]
    if not (aid and mid and eid):
        return state, False, "An actual player and signed event are required."
    if not show or show["event_id"] != _ident(performance_event_id):
        return state, False, "A real performance must exist today."
    if show["account_id"] == aid:
        return state, False, "A Performer cannot review their own work."
    witness = next((
        w for w in state["witnesses"]
        if w["account_id"] == aid and w["mask_id"] == mid
        and w["event_id"] == _ident(witness_event_id)
    ), None)
    if not witness:
        return state, False, "Sign firsthand stage witness before reviewing."
    reviews = list(show.get("reviews") or [])
    if any(r["account_id"] == aid for r in reviews):
        return state, False, "This account already reviewed the performance."
    if len(reviews) >= MAX_REVIEWS:
        return state, False, "The review book is full for this performance."
    reviews.append({
        "account_id": aid, "mask_id": mid, "mask": str(mask)[:70],
        "day": day, "hour": hour, "event_id": eid,
        "performance_event_id": show["event_id"],
        "witness_event_id": witness["event_id"],
        "verdict": verdict, "contest_event_id": None,
    })
    show["reviews"] = reviews
    return state, True, None


def contest(raw, *, day, hour, account_id, mask_id, mask, event_id,
            review_event_id):
    state = refresh(raw, day)
    if not _time(day, hour) or day < state["day"]:
        return state, False, "The village clock cannot be rewound."
    aid, mid, eid = _ident(account_id), _ident(mask_id), _ident(event_id)
    show = state["performance"]
    if not (aid and mid and eid):
        return state, False, "An actual player and signed event are required."
    if not show or show["account_id"] != aid or show["mask_id"] != mid:
        return state, False, "Only the original Performer can contest this review."
    target = next((
        r for r in show.get("reviews") or []
        if r["event_id"] == _ident(review_event_id)
    ), None)
    if not target:
        return state, False, "No such signed review exists for this performance."
    if target.get("contest_event_id"):
        return state, False, "This review has already been contested."
    target["contest_event_id"] = eid
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
        for review_record in p.get("reviews") or []:
            lines.append("%s filed an attributed %s review (event %s)%s."
                         % (review_record["mask"], review_record["verdict"],
                            review_record["event_id"],
                            ", contested by the Performer" if review_record.get("contest_event_id") else ""))
    else:
        lines.append("No public performance has occurred today.")
    if state["history"]:
        last = state["history"][-1]
        lines.append("Previous recorded show: %s, day %d."
                     % (last["performance"]["mask"], last["day"]))
    lines.append("Performers: stage rehearse ballad|reel, then stage perform ballad|reel.")
    lines.append("During the actual performance hour, other visitors may stage witness.")
    lines.append("A firsthand Chronicler may stage review praise|critique; the Performer may stage contest <review event>.")
    return "\n".join(lines)
