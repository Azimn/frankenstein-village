"""GDD-EDGE-21: finite physical stage rail and independently tested acoustics.

Pure rules. The Tavern owns the record; Workshop owns finite material.
A signed Smith installation does not imply that a Performer tested the rail.
"""
from __future__ import annotations

from collections.abc import Mapping, Sequence

USES = 3


def _id(v):
    return v if type(v) is int and v > 0 else None


def _time(day, hour):
    return _id(day) is not None and type(hour) is int and 0 <= hour <= 23


def _row(row, extra=()):
    return (isinstance(row, Mapping) and _time(row.get("day"), row.get("hour"))
            and all(_id(row.get(k)) for k in
                    ("event_id", "account_id", "mask_id", *extra)))


def fresh():
    return {"condition": "worn", "fitting": None, "soundcheck": None,
            "plays": [], "remaining": 0}


def invalid():
    return {"condition": "invalid", "fitting": None, "soundcheck": None,
            "plays": [], "remaining": 0}


def normalize(raw):
    if raw is None:
        return fresh()
    if not isinstance(raw, Mapping):
        return invalid()
    condition = raw.get("condition")
    if (condition == "worn" and raw.get("fitting") is None
            and raw.get("soundcheck") is None
            and raw.get("plays", []) == [] and raw.get("remaining", 0) == 0):
        return fresh()
    f = raw.get("fitting")
    if condition not in ("fitted", "ready", "spent") or not _row(
            f, ("item_id", "forge_event_id", "workshop_id", "tavern_id")):
        return invalid()
    if f["forge_event_id"] == f["event_id"]:
        return invalid()
    check = raw.get("soundcheck")
    if condition == "fitted" and check is not None:
        return invalid()
    if condition != "fitted" and not _row(check, ("fitting_event_id",)):
        return invalid()
    if check is not None and (
            check["event_id"] in (f["event_id"], f["forge_event_id"])
            or check["fitting_event_id"] != f["event_id"]
            or check["account_id"] == f["account_id"]
            or check["mask_id"] == f["mask_id"]
            or (check["day"], check["hour"]) < (f["day"], f["hour"])):
        return invalid()
    plays = raw.get("plays", [])
    if (not isinstance(plays, Sequence) or isinstance(plays, (str, bytes))
            or len(plays) > USES):
        return invalid()
    clean = []
    for p in plays:
        if (not _row(p, ("soundcheck_event_id",))
                or not isinstance(p.get("tune"), str)
                or p["tune"] not in ("ballad", "reel")
                or check is None
                or (p["day"], p["hour"]) < (f["day"], f["hour"])):
            return invalid()
        # The latest soundcheck is retained in the physical Attribute. A set
        # on that same day must belong to that exact signed Performer event;
        # earlier days have separate historical checks in the world ledger.
        if (p["day"] > check["day"]
                or (p["day"] == check["day"] and (
                    p["soundcheck_event_id"] != check["event_id"]
                    or p["account_id"] != check["account_id"]
                    or p["mask_id"] != check["mask_id"]
                    or p["hour"] < check["hour"]))
                or p["soundcheck_event_id"] in (f["event_id"], f["forge_event_id"])
                or p["event_id"] in (f["event_id"], f["forge_event_id"],
                                     p["soundcheck_event_id"], check["event_id"])):
            return invalid()
        if (clean and (p["day"], p["hour"]) < (clean[-1]["day"], clean[-1]["hour"])):
            return invalid()
        if any(q["day"] == p["day"] or p["event_id"] in
               (q["event_id"], q["soundcheck_event_id"]) or
               p["soundcheck_event_id"] in
               (q["event_id"], q["soundcheck_event_id"]) for q in clean):
            return invalid()
        clean.append({k: p[k] for k in
                      ("day", "hour", "event_id", "account_id", "mask_id",
                       "soundcheck_event_id", "tune")})
    remaining = raw.get("remaining")
    if (type(remaining) is not int or remaining != USES - len(clean)
            or (condition == "spent") != (remaining == 0)
            or (condition == "fitted" and (clean or remaining != USES))
            or (condition == "ready" and check is None)):
        return invalid()
    fitting = {k: f[k] for k in
               ("day", "hour", "event_id", "account_id", "mask_id",
                "item_id", "forge_event_id", "workshop_id", "tavern_id")}
    checked = ({k: check[k] for k in
                ("day", "hour", "event_id", "account_id", "mask_id",
                 "fitting_event_id")} if check is not None else None)
    return {"condition": condition, "fitting": fitting,
            "soundcheck": checked, "plays": clean, "remaining": remaining}


def fit(raw, *, day, hour, event_id, account_id, mask_id,
        item_id, forge_event_id, workshop_id, tavern_id):
    state = normalize(raw)
    if state["condition"] != "worn":
        return state, False, "The stage rail is already fitted or its record is invalid."
    vals = (event_id, account_id, mask_id, item_id, forge_event_id,
            workshop_id, tavern_id)
    if (not _time(day, hour) or not all(_id(v) for v in vals)
            or event_id == forge_event_id):
        return state, False, "A real fitting, signed Smith and village shift are required."
    state["condition"] = "fitted"
    state["remaining"] = USES
    state["fitting"] = dict(day=day, hour=hour, event_id=event_id,
                            account_id=account_id, mask_id=mask_id,
                            item_id=item_id, forge_event_id=forge_event_id,
                            workshop_id=workshop_id, tavern_id=tavern_id)
    return state, True, None


def soundcheck(raw, *, day, hour, event_id, account_id, mask_id):
    state = normalize(raw)
    if state["condition"] not in ("fitted", "ready"):
        return state, False, "A usable, physically fitted stage rail is required."
    f = state["fitting"]
    c = state["soundcheck"]
    if not _time(day, hour) or not all(_id(v) for v in (event_id, account_id, mask_id)):
        return state, False, "A signed Performer and village shift are required."
    used = {f["event_id"], f["forge_event_id"]}
    for prior in state["plays"]:
        used.update((prior["event_id"], prior["soundcheck_event_id"]))
    if c:
        used.add(c["event_id"])
    if event_id in used:
        return state, False, "The signed soundcheck event must be distinct from its sources."
    if (day, hour) < (f["day"], f["hour"]):
        return state, False, "The fitting has not yet been installed."
    if account_id == f["account_id"] or mask_id == f["mask_id"]:
        return state, False, "A different Performer account must test the Smith's work."
    if c and day <= c["day"]:
        return state, False, "Today's soundcheck is already signed."
    if state["plays"] and day <= state["plays"][-1]["day"]:
        return state, False, "The rail was already played this day."
    state["condition"] = "ready"
    state["soundcheck"] = dict(day=day, hour=hour, event_id=event_id,
                               account_id=account_id, mask_id=mask_id,
                               fitting_event_id=f["event_id"])
    return state, True, None


def acoustic(raw, *, day, hour, event_id, account_id, mask_id, tune):
    state = normalize(raw)
    if state["condition"] != "ready":
        return state, False, "A usable, independently soundchecked rail is required."
    c = state["soundcheck"]
    if not _time(day, hour) or not all(_id(v) for v in (event_id, account_id, mask_id)):
        return state, False, "A signed Performer and village shift are required."
    used = {state["fitting"]["event_id"], state["fitting"]["forge_event_id"],
            c["event_id"]}
    for prior in state["plays"]:
        used.update((prior["event_id"], prior["soundcheck_event_id"]))
    if event_id in used:
        return state, False, "The signed acoustic event must be distinct from its sources."
    if tune not in ("ballad", "reel"):
        return state, False, "Choose ballad or reel."
    if day != c["day"] or hour < c["hour"]:
        return state, False, "Soundcheck this rail on the current day before playing."
    if account_id != c["account_id"] or mask_id != c["mask_id"]:
        return state, False, "The soundchecking Performer must play this acoustic set."
    if any(p["day"] == day for p in state["plays"]):
        return state, False, "Today's acoustic set has already been played."
    state["plays"].append(dict(day=day, hour=hour, event_id=event_id,
                               account_id=account_id, mask_id=mask_id,
                               soundcheck_event_id=c["event_id"], tune=tune))
    state["remaining"] -= 1
    if not state["remaining"]:
        state["condition"] = "spent"
    return state, True, None


def public_lines(raw):
    s = normalize(raw)
    if s["condition"] == "worn":
        return ("Stage rail: worn. A Smith can bring a real Workshop-forged hinge "
                "and use stage fit. Ordinary rehearsal and performance still work.")
    if s["condition"] == "invalid":
        return "Stage rail: inconsistent record; acoustic sets are unavailable."
    if s["condition"] == "spent":
        return "Stage rail: worn out after three acoustic sets; no more amplified sets."
    return ("Stage rail: %s, %d of %d acoustic uses remain. "
            "An independent Performer uses stage soundcheck, then "
            "stage acoustic ballad or stage acoustic reel on that day."
            % (s["condition"], s["remaining"], USES))
