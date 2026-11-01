"""Persistent public Tavern music work, without a fabricated audience.

This is a small, renewable, physical profession loop. A rehearsal is a real
signed action and a show occurs only when a Performer actually plays. Other
accounts may explicitly witness it during that village hour.
"""
from __future__ import annotations

import copy
from collections.abc import Mapping, Sequence

TUNES = ("ballad", "reel")
MAX_HISTORY = 32
MAX_REHEARSALS = 12
MAX_WITNESSES = 20


def _ident(value):
    """Accept actual positive IDs or ASCII decimal IDs, never truncated floats."""
    if isinstance(value, bool):
        return None
    if isinstance(value, int):
        return value if value > 0 else None
    if isinstance(value, str) and value.isascii() and value.isdecimal():
        try:
            parsed = int(value)
        except ValueError:
            return None
        return parsed if parsed > 0 else None
    return None



def parse_review_id(value):
    """Accept only positive signed 64-bit review event IDs, without coercion."""
    if isinstance(value, bool):
        return None
    limit = (1 << 63) - 1
    if isinstance(value, int):
        return value if 0 < value <= limit else None
    if (isinstance(value, str) and 0 < len(value) <= 20
            and all("0" <= ch <= "9" for ch in value)):
        parsed = int(value)
        return parsed if 0 < parsed <= limit else None
    return None


def _time(day, hour):
    d = _ident(day)
    if isinstance(hour, bool):
        return None
    if isinstance(hour, int):
        h = hour
    elif isinstance(hour, str) and hour.isascii() and hour.isdecimal():
        try:
            h = int(hour)
        except ValueError:
            return None
    else:
        return None
    return (d, h) if d and 0 <= h <= 23 else None


def _records(value):
    """Only finite sequence containers can supply persisted state records.

    Corrupt scalar or mapping containers are not iterable evidence. Keep
    Mapping-backed rows, including Evennia persistence wrappers.
    """
    # Evennia stores lists as _SaverList (MutableSequence), not list.
    # Restrict input to real sequences, never strings, bytes or mappings.
    if not isinstance(value, Sequence) or isinstance(value, (str, bytes, bytearray)):
        return []
    return [row for row in value if isinstance(row, Mapping)]


def _eligible_accounts(raw, performer_id):
    """Retain only actual bounded audience identifiers from persisted state."""
    if not isinstance(raw, Sequence) or isinstance(raw, (str, bytes, bytearray)):
        return []
    return sorted({
        account for value in raw[:MAX_WITNESSES * 2]
        if (account := _ident(value)) is not None and account != performer_id
    })[:MAX_WITNESSES]


def fresh(day=1):
    return {"day": day, "rehearsals": [], "performance": None,
            "witnesses": [], "safety_warning": None,
            "safety_decision": None, "service": None, "history": []}


def normalize(raw):
    if not hasattr(raw, "get"):
        return fresh()
    day = _ident(raw.get("day"))
    if day is None:
        # An invalid persisted day cannot certify any retained stage action.
        return fresh()
    result = fresh(day)
    for r in _records(raw.get("rehearsals"))[-MAX_REHEARSALS * 2:]:
        if not hasattr(r, "get") or r.get("tune") not in TUNES:
            continue
        if (_ident(r.get("account_id")) and _ident(r.get("mask_id"))
                and _ident(r.get("event_id")) and _time(day, r.get("hour"))):
            receipt = dict(r)
            for key in ("account_id", "mask_id", "event_id", "hour"):
                receipt[key] = int(receipt[key])
            result["rehearsals"].append(receipt)
    result["rehearsals"] = result["rehearsals"][-MAX_REHEARSALS:]
    perf = raw.get("performance")
    if (hasattr(perf, "get") and perf.get("tune") in TUNES
            and _ident(perf.get("event_id"))
            and _ident(perf.get("account_id"))
            and _ident(perf.get("mask_id"))
            and _time(day, perf.get("hour"))):
        result["performance"] = dict(perf)
        for key in ("account_id", "mask_id", "event_id", "hour"):
            result["performance"][key] = int(perf[key])
        eligible = _eligible_accounts(
            perf.get("eligible_audience_ids"), _ident(perf.get("account_id"))
        )
        result["performance"]["eligible_audience_ids"] = eligible
        result["performance"]["reviews"] = [
            dict(r) for r in list(perf.get("reviews") or [])
            if hasattr(r, "get") and r.get("verdict") in ("praise", "critique")
            and _ident(r.get("account_id")) and _ident(r.get("mask_id"))
            and _ident(r.get("event_id")) and _ident(r.get("witness_event_id"))
            and _ident(r.get("performance_event_id"))
        ][:8]
        seen = set()
        for r in _records(raw.get("witnesses"))[-MAX_WITNESSES * 2:]:
            account = _ident(r.get("account_id"))
            event = _ident(r.get("event_id"))
            if account in eligible and event and account not in seen:
                seen.add(account)
                receipt = dict(r)
                receipt["account_id"] = account
                receipt["event_id"] = event
                result["witnesses"].append(receipt)
    result["witnesses"] = result["witnesses"][-MAX_WITNESSES:]
    # A catered service is credible only with an actual show, an independent
    # Innkeep, a physical bowl receipt and a real signed audience witness.
    service = raw.get("service")
    show = result["performance"]
    if (show and result["witnesses"] and hasattr(service, "get")
            and all(_ident(service.get(key)) for key in (
                "account_id", "mask_id", "event_id", "bowl_id",
                "cook_event_id", "performance_event_id", "witness_event_id"))
            and service.get("performance_event_id") == show["event_id"]
            and _ident(service.get("account_id")) != show["account_id"]
            and service.get("hour") == show["hour"]
            and not isinstance(service.get("witness_count"), bool)
            and _ident(service.get("witness_count"))
            and int(service["witness_count"]) <= len(result["witnesses"])
            and _ident(service.get("event_id")) > max(
                show["event_id"], _ident(service.get("cook_event_id")),
                _ident(service.get("witness_event_id")))
            and any(w["event_id"] == service["witness_event_id"]
                    for w in result["witnesses"])):
        result["service"] = {
            "account_id": int(service["account_id"]),
            "mask_id": int(service["mask_id"]),
            "mask": str(service.get("mask") or "")[:70],
            "hour": show["hour"], "event_id": int(service["event_id"]),
            "bowl_id": int(service["bowl_id"]),
            "cook_event_id": int(service["cook_event_id"]),
            "performance_event_id": show["event_id"],
            "witness_event_id": int(service["witness_event_id"]),
            "witness_count": int(service["witness_count"]),
        }
    warning = raw.get("safety_warning")
    if (hasattr(warning, "get")
            and all(_ident(warning.get(k)) for k in (
                "account_id", "mask_id", "event_id", "source_event_id",
                "cord_id"))
            and _time(day, warning.get("hour"))):
        result["safety_warning"] = dict(warning)
        for key in ("account_id", "mask_id", "event_id",
                    "source_event_id", "cord_id", "hour"):
            result["safety_warning"][key] = int(warning[key])
    decision = raw.get("safety_decision")
    if (hasattr(decision, "get") and result["safety_warning"]
            and all(_ident(decision.get(k)) for k in (
                "account_id", "mask_id", "event_id", "warning_event_id"))
            and decision.get("choice") in {"indoor", "cancel"}
            and _ident(decision["warning_event_id"]) == result["safety_warning"]["event_id"]
            and _ident(decision["account_id"]) != result["safety_warning"]["account_id"]
            and _time(day, decision.get("hour"))
            and int(decision["hour"]) >= int(result["safety_warning"]["hour"])):
        result["safety_decision"] = dict(decision)
        for key in ("account_id", "mask_id", "event_id",
                    "warning_event_id", "hour"):
            result["safety_decision"][key] = int(decision[key])
    for row in _records(raw.get("history")):
        historical_day = _ident(row.get("day"))
        if historical_day is None or historical_day >= day:
            continue
        receipt = copy.deepcopy(dict(row))
        receipt["day"] = historical_day
        result["history"].append(receipt)
    result["history"] = result["history"][-MAX_HISTORY:]
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
            "service": copy.deepcopy(state["service"]),
        })
    return {"day": target, "rehearsals": [], "performance": None,
            "witnesses": [], "safety_warning": None, "safety_decision": None,
            "service": None, "history": state["history"][-MAX_HISTORY:]}


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
    if not all(isinstance(v, Mapping) for v in (route, event, marker)):
        return False
    decisions = route.get("field_decisions")
    if not isinstance(decisions, Mapping):
        return False
    source = decisions.get("hound")
    actor, payload, effect = (
        event.get("actor"), event.get("payload"),
        event.get("consequence"))
    # Corrupted or forged persisted nested structures must be rejected as
    # missing evidence, not crash an ordinary player's stage command.
    if not all(isinstance(v, Mapping) for v in (source, actor, payload, effect)):
        return False
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
    performance_result = performance.get("consequence") or {}
    witness_result = witnessed.get("consequence") or {}
    return (hasattr(performance_result, "get") and hasattr(witness_result, "get")
            and performance_result.get("performance_event_id") == show.get("event_id")
            and witness_result.get("performance_event_id") == show.get("event_id"))


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


def cater(raw, *, day, hour, account_id, mask_id, mask, event_id,
          bowl_id, cook_event_id):
    """One finite Innkeep food service linked to a witnessed real show.

    The Evennia adapter must separately verify the real bowl, its completed
    cooking event, active Innkeep Calling and physical Tavern location.
    """
    state = refresh(raw, day)
    if not _time(day, hour) or day < state["day"]:
        return state, False, "The village clock cannot be rewound."
    aid, mid, eid = _ident(account_id), _ident(mask_id), _ident(event_id)
    bid, cid = _ident(bowl_id), _ident(cook_event_id)
    if not all((aid, mid, eid, bid, cid)):
        return state, False, "A signed Innkeep and physical cooked bowl are required."
    show = state["performance"]
    if not show:
        return state, False, "No real Performer show has taken place today."
    if show["hour"] != hour:
        return state, False, "The audience has left this performance hour."
    if show["account_id"] == aid:
        return state, False, "An independent Innkeep must provide the food service."
    if not state["witnesses"]:
        return state, False, "No audience member signed attendance at this show."
    if state["service"]:
        return state, False, "This performance has already received its catered bowl."
    witness = state["witnesses"][0]
    if eid <= max(show["event_id"], cid, witness["event_id"]):
        return state, False, "The service must follow the signed show, witness and cooking."
    state["service"] = {
        "account_id": aid, "mask_id": mid, "mask": str(mask)[:70],
        "hour": hour, "event_id": eid, "bowl_id": bid,
        "cook_event_id": cid, "performance_event_id": show["event_id"],
        "witness_event_id": witness["event_id"],
        "witness_count": len(state["witnesses"]),
    }
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
        if state["service"]:
            meal = state["service"]
            lines.append("%s provided one real cooked soup bowl for the witnessed show "
                         "(service event %d, bowl %d, cooking event %d)."
                         % (meal["mask"], meal["event_id"], meal["bowl_id"],
                            meal["cook_event_id"]))
        for review_record in p.get("reviews") or []:
            lines.append("%s filed an attributed %s review (event %s)%s."
                         % (review_record["mask"], review_record["verdict"],
                            review_record["event_id"],
                            ", contested by the Performer" if review_record.get("contest_event_id") else ""))
    else:
        lines.append("No public performance has occurred today.")
    if state["history"]:
        last = state["history"][-1]
        prior_show = last.get("performance")
        prior_decision = last.get("safety_decision")
        if isinstance(prior_show, Mapping) and isinstance(prior_show.get("mask"), str):
            lines.append("Previous recorded show: %s, day %d." % (prior_show["mask"], last["day"]))
        elif isinstance(prior_decision, Mapping) and prior_decision.get("choice") in {"indoor", "cancel"}:
            lines.append("Previous stage decision: %s, day %d." % (prior_decision["choice"], last["day"]))
    lines.append("Hounds: after survey protect at the real red cord, visit here and stage warn.")
    lines.append("Performers: stage adapt indoor or stage adapt cancel after a Hound warning.")
    lines.append("Performers: stage rehearse ballad or stage rehearse reel, then stage perform ballad or stage perform reel.")
    lines.append("During the actual performance hour, other visitors may stage witness.")
    lines.append("A firsthand Chronicler may stage review praise (or critique); the Performer may stage contest <review event>.")
    lines.append("Innkeeps: after a real audience witness, carry a cooked soup bowl and use stage cater in the same hour.")
    return "\n".join(lines)


def archive_lines(raw, day):
    """Public, attributed stage record. Reviews are opinions, not world truth."""
    state = refresh(raw, day)
    shows = list(state["history"][-10:])
    if state["performance"]:
        shows.append({
            "day": state["day"], "performance": state["performance"],
            "witnesses": state["witnesses"],
        })
    lines = ["The Tavern's signed performance and review archive"]
    if not shows:
        lines.append("No performances have been recorded.")
    for item in shows:
        show = item.get("performance") or {}
        if not show:
            continue
        lines.append("Day %s: %s played %s (performance event %s; %s signed witnesses)."
                     % (item["day"], show.get("mask"), show.get("tune"),
                        show.get("event_id"), len(item.get("witnesses") or [])))
        for record in show.get("reviews") or []:
            lines.append("  %s: attributed %s review, event %s, witness event %s%s."
                         % (record.get("mask"), record.get("verdict"),
                            record.get("event_id"), record.get("witness_event_id"),
                            "; Performer contested in event %s" % record["contest_event_id"]
                            if record.get("contest_event_id") else ""))
    lines.append("A review reports a Chronicler's opinion, not objective proof.")
    return "\n".join(lines)
