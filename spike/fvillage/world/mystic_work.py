"""Real village Mystic study: location, firsthand event, signed provenance."""
from __future__ import annotations

from django.db import transaction
from evennia.scripts.models import ScriptDB
from evennia.utils import search

from world import mystic_circles
from world.callings import active_calling, record_participation
from world.events import publish_world_event

GRAVE_KEY = "a weathered grave marker"
ROOM_KEY = "St. Lazarus Churchyard"


def clock():
    try:
        s = ScriptDB.objects.get(db_key="village_time")
        return int(s.db.day or 1), int(
            s.db.hour if s.db.hour is not None else 21
        )
    except ScriptDB.DoesNotExist:
        return 1, 21


def churchyard():
    return next((o for o in search.search_object(ROOM_KEY)
                 if o.key == ROOM_KEY and o.location is None
                 and o.tags.has("ic", category="side")), None)


def witness_description(looker, grave):
    """Called by a physical look at the EXISTING public grave marker."""
    day, hour = clock()
    physical = mystic_circles.manifestation_text(day, hour)
    if not physical:
        return ""
    room = churchyard()
    account = getattr(looker, "account", None)
    account_id = getattr(account, "id", None)
    mask_id = getattr(looker, "id", None)
    if (isinstance(account_id, int) and account_id > 0
            and isinstance(mask_id, int) and mask_id > 0
            and not isinstance(account_id, bool)
            and getattr(looker, "db", None) is not None
            and room is not None and grave.location == room
            and getattr(looker, "location", None) == room
            and grave.key == GRAVE_KEY):
        looker.db.mystic_grave_witness = {
            "day": day, "hour": hour, "grave_id": grave.id,
            "mask_id": mask_id, "account_id": account_id,
        }
    return physical


def status(mask=None):
    room = churchyard()
    day, hour = clock()
    lines = ["|wGuild of Mystics|n"]
    lines.extend(mystic_circles.public_lines(
        room.db.mystic_studies if room else None
    ))
    lines.append(
        "Beatrice Harcourt (Correspondents): controlled measurements. "
        "Mirela Dobre (Hearth Circle): folklore and the ethics of testimony."
    )
    lines.append(
        "The unusual grave lettering is visible on one night each village week. "
        "There is no need to claim a spirit caused it."
    )
    if room and getattr(mask, "location", None) == room:
        if mystic_circles.manifested(day, hour):
            lines.append(
                "The old grave marker is behaving impossibly. "
                "Look grave marker to witness it firsthand. "
                "A Mystic may then use mystic study measure or mystic study vigil."
            )
        else:
            lines.append(
                "The stone's lettering is ordinary now. An old rumor does not "
                "count as a new firsthand study."
            )
    else:
        lines.append(
            "Visit St. Lazarus Churchyard to examine the weathered grave marker."
        )
    return "\n".join(lines)


def study(mask, method):
    if method not in mystic_circles.METHODS:
        return None, "Use mystic study measure or mystic study vigil."
    account = getattr(mask, "account", None)
    room = churchyard()
    if not account or room is None or mask.location != room:
        return None, "The actual churchyard is required for a signed study."
    if active_calling(mask) != "mystic":
        return None, "Only an active Mystic may submit a professional study."
    day, hour = clock()
    if not mystic_circles.manifested(day, hour):
        return None, "The stone is ordinary tonight. No new anomaly can be certified."
    observation = dict(mask.db.mystic_grave_witness or {})
    if (observation.get("day") != day
            or observation.get("hour") != hour
            or observation.get("mask_id") != mask.id
            or observation.get("account_id") != account.id):
        return None, "Look grave marker here during the occurrence, not from rumor."
    grave = next((o for o in room.contents if o.key == GRAVE_KEY), None)
    if not grave or observation.get("grave_id") != grave.id:
        return None, "The physical evidence is not present."

    _, accepted, error = mystic_circles.record(
        room.db.mystic_studies, method, day=day, account_id=account.id,
        mask_id=mask.id, mask=mask.key, event_id=1,
    )
    if not accepted:
        return None, error

    def consequence(event):
        with transaction.atomic():
            if (mask.location != room or active_calling(mask) != "mystic"
                    or not mystic_circles.manifested(*clock())):
                raise RuntimeError("The site or conditions changed.")
            if dict(mask.db.mystic_grave_witness or {}) != observation:
                raise RuntimeError("The witness record changed.")
            current, ok, problem = mystic_circles.record(
                room.db.mystic_studies, method,
                day=day, account_id=account.id, mask_id=mask.id,
                mask=mask.key, event_id=event["id"],
            )
            if not ok:
                raise RuntimeError(problem)
            room.db.mystic_studies = current
            return {
                "method": method, "observed_grave_id": grave.id,
                "observation_day": day, "observation_hour": hour,
            }

    event = publish_world_event(
        "village.mystic_grave_study", actor=mask,
        payload={
            "method": method, "day": day, "hour": hour,
            "room": ROOM_KEY, "evidence_id": "grave_marker",
            "observation_quality": "firsthand",
            "harbinger": False, "chronicle_eligible": False,
        },
        consequence=consequence,
    )
    record_participation(mask, "mystic_grave_studies", calling="mystic")
    return {
        "event_id": event["id"], "method": method,
        "public": status(mask),
    }, None
