"""GDD-EDGE-21: signed stage rail installation and independent acoustic work."""
from __future__ import annotations

from django.db import transaction

from world import stage_fitting_edge21 as rules, stage_work, workshop_work
from world.callings import active_calling, record_participation
from world.events import get_event_ledger, publish_world_event


def _guard(mask, calling):
    tavern, error = stage_work._guard(mask)
    if error:
        return None, error
    if active_calling(mask) != calling:
        return None, "An active %s Calling is required." % calling.title()
    return tavern, None


def status(mask):
    tavern, error = stage_work._guard(mask)
    if error:
        return error
    return rules.public_lines(tavern.db.stage_rail_edge21)


def _forge(item):
    source = item.db.forged_market_part
    workshop = workshop_work._room(workshop_work.WORKSHOP)
    if not hasattr(source, "get") or workshop is None:
        return None, "The hinge lacks a real Workshop source."
    eid = source.get("source_event_id")
    if type(eid) is not int or eid <= 0:
        return None, "The hinge has no signed forging event."
    event = get_event_ledger().get_event(eid)
    if (not event or event.get("status") != "complete"
            or event.get("kind") != "village.market_hinge_forged"
            or not hasattr(event.get("actor"), "get")
            or not hasattr(event.get("payload"), "get")
            or not hasattr(event.get("consequence"), "get")
            or event["actor"].get("account_id") != source.get("smith_account_id")
            or event["payload"].get("room_id") != workshop.id
            or event["payload"].get("day") != source.get("issued_day")
            or event["consequence"].get("item_id") != item.id
            or event["consequence"].get("source_room_id") != workshop.id
            or source.get("source_room_id") != workshop.id
            or type(source.get("issued_day")) is not int
            or type(event["payload"].get("hour")) is not int
            or not 0 <= event["payload"]["hour"] <= 23
            or (source["issued_day"], event["payload"]["hour"]) > stage_work._clock()):
        return None, "The hinge does not match a completed, dated forge receipt."
    return {"forge_event_id": eid, "workshop_id": workshop.id}, None


def _fit_receipt(tavern):
    state = rules.normalize(tavern.db.stage_rail_edge21)
    f = state["fitting"]
    if f is None:
        return None, "No signed physical stage fitting exists."
    event = get_event_ledger().get_event(f["event_id"])
    if (not event or event.get("status") != "complete"
            or event.get("kind") != "professional.stage_rail_fitted"
            or not hasattr(event.get("actor"), "get")
            or not hasattr(event.get("payload"), "get")
            or not hasattr(event.get("consequence"), "get")
            or event["actor"].get("account_id") != f["account_id"]
            or event["actor"].get("mask_id") != f["mask_id"]
            or event["payload"].get("tavern_id") != tavern.id
            or event["payload"].get("day") != f["day"]
            or event["payload"].get("hour") != f["hour"]
            or event["payload"].get("forge_event_id") != f["forge_event_id"]
            or event["consequence"].get("consumed_item_id") != f["item_id"]
            or event["consequence"].get("workshop_id") != f["workshop_id"]
            or event["consequence"].get("tavern_id") != tavern.id):
        return None, "The stage rail lacks an authentic completed Smith event."
    forge = get_event_ledger().get_event(f["forge_event_id"])
    if (not forge or forge.get("status") != "complete"
            or forge.get("kind") != "village.market_hinge_forged"
            or not hasattr(forge.get("consequence"), "get")
            or forge["consequence"].get("item_id") != f["item_id"]
            or forge["consequence"].get("source_room_id") != f["workshop_id"]):
        return None, "The stage rail lacks an authentic physical fitting source."
    return f, None


def _check_receipt(tavern):
    state = rules.normalize(tavern.db.stage_rail_edge21)
    c = state["soundcheck"]
    if c is None:
        return None, "The rail has no completed Performer soundcheck."
    event = get_event_ledger().get_event(c["event_id"])
    if (not event or event.get("status") != "complete"
            or event.get("kind") != "professional.stage_rail_soundchecked"
            or not hasattr(event.get("actor"), "get")
            or not hasattr(event.get("payload"), "get")
            or not hasattr(event.get("consequence"), "get")
            or event["actor"].get("account_id") != c["account_id"]
            or event["actor"].get("mask_id") != c["mask_id"]
            or event["payload"].get("day") != c["day"]
            or event["payload"].get("hour") != c["hour"]
            or event["payload"].get("tavern_id") != tavern.id
            or event["payload"].get("fitting_event_id") != c["fitting_event_id"]
            or event["consequence"].get("soundcheck_event_id") != c["event_id"]
            or event["consequence"].get("tavern_id") != tavern.id):
        return None, "The acoustic check lacks an authentic Performer event."
    return c, None


def act(mask, action, tune=None):
    if action not in ("fit", "soundcheck", "acoustic"):
        return None, "Use stage fit, stage soundcheck, or stage acoustic ballad or reel."
    calling = "smith" if action == "fit" else "performer"
    tavern, error = _guard(mask, calling)
    if error:
        return None, error
    if action == "acoustic" and tune not in ("ballad", "reel"):
        return None, "Choose stage acoustic ballad or stage acoustic reel."
    if action != "acoustic" and tune is not None:
        return None, "This action does not take a tune."
    item = None
    source = None
    if action == "fit":
        items = [o for o in mask.contents
                 if o.key == workshop_work.FITTING
                 and hasattr(o.db.forged_market_part, "get")]
        if len(items) != 1:
            return None, "Carry one real Workshop-forged hinge to the Tavern."
        item = items[0]
        source, error = _forge(item)
        if error:
            return None, error
    else:
        _fitting, error = _fit_receipt(tavern)
        if error:
            return None, error
        if action == "acoustic":
            _check, error = _check_receipt(tavern)
            if error:
                return None, error
    day, hour = stage_work._clock()
    account_id = mask.account.id
    mask_id = mask.id
    props = dict(day=day, hour=hour, account_id=account_id, mask_id=mask_id)
    if action == "fit":
        props.update(item_id=item.id, tavern_id=tavern.id, **source)
    if action == "acoustic":
        props["tune"] = tune
    transform = getattr(rules, action)
    _preview, ok, why = transform(tavern.db.stage_rail_edge21, event_id=1, **props)
    if not ok:
        return None, why

    def consequence(event):
        with transaction.atomic():
            if (stage_work._clock() != (day, hour) or mask.location != tavern
                    or active_calling(mask) != calling
                    or not getattr(mask, "account", None)
                    or mask.account.id != account_id or mask.id != mask_id):
                raise RuntimeError("The acting player, Calling or shift changed.")
            if action == "fit":
                if item.location != mask:
                    raise RuntimeError("The real hinge is no longer carried.")
                current_source, source_error = _forge(item)
                if source_error or current_source != source:
                    raise RuntimeError(source_error or "Forge receipt changed.")
            else:
                _f, fit_error = _fit_receipt(tavern)
                if fit_error:
                    raise RuntimeError(fit_error)
                if action == "acoustic":
                    _c, check_error = _check_receipt(tavern)
                    if check_error:
                        raise RuntimeError(check_error)
            changed, valid, reason = transform(
                tavern.db.stage_rail_edge21, event_id=event["id"], **props)
            if not valid:
                raise RuntimeError(reason)
            tavern.db.stage_rail_edge21 = changed
            consumed = None
            if action == "fit":
                consumed = item.id
                item.delete()
            return {"tavern_id": tavern.id, "day": day, "hour": hour,
                    "condition": changed["condition"],
                    "remaining": changed["remaining"],
                    "consumed_item_id": consumed,
                    "workshop_id": source["workshop_id"] if source else None,
                    "soundcheck_event_id": event["id"] if action == "soundcheck" else
                        (changed["soundcheck"]["event_id"] if changed["soundcheck"] else None),
                    "tune": tune}

    event = publish_world_event(
        {"fit": "professional.stage_rail_fitted",
         "soundcheck": "professional.stage_rail_soundchecked",
         "acoustic": "professional.stage_acoustic_played"}[action],
        actor=mask,
        payload={"day": day, "hour": hour, "tavern_id": tavern.id,
                 "forge_event_id": source["forge_event_id"] if source else None,
                 "fitting_event_id": (
                     rules.normalize(tavern.db.stage_rail_edge21)["fitting"]["event_id"]
                     if action != "fit" else None),
                 "tune": tune, "professional_calling": calling,
                 "harbinger": False, "chronicle_eligible": False},
        consequence=consequence,
    )
    record_participation(mask, "stage_rail_" + action, calling=calling)
    return {"event_id": event["id"], "action": action, "tune": tune}, None
