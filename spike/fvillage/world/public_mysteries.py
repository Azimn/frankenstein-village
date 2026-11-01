"""Community-scale public mysteries with evidence/theory separation.

A public mystery is an open question whose local facts can accumulate without
certifying the world bible's intentionally unresolved metaphysics.
"""

from __future__ import annotations

import copy
import hashlib
import re

from evennia import create_script
from evennia.scripts.models import ScriptDB


REGISTRY_KEY = "public_mystery_registry"
MANOR_LIGHTS_ID = "PUBLIC-MANOR-LIGHTS"
BRIDGE_PLAQUE_ID = "PUBLIC-BRIDGE-PLAQUE"
MAX_OBSERVATIONS = 120
MAX_THEORIES = 80
MAX_THEORIES_PER_ACCOUNT_DAY = 3

DEFINITIONS = {
    BRIDGE_PLAQUE_ID: {
        "title": "Who Removed the Old Bridge Plaque?",
        "question": "Why is the inscription missing from the river bridge?",
        "location": "The Old Stone Bridge",
        "unresolved_note": (
            "The empty screw holes, weathering, and witnesses are observable. "
            "No culprit or intended message is certified."
        ),
    },
    MANOR_LIGHTS_ID: {
        "title": "Why Are the Manor Lights Returning?",
        "question": "Why are lights appearing again in the hilltop Manor?",
        "location": "Village Square",
        "unresolved_note": (
            "The village may establish when and where the lights appear. "
            "No metaphysical explanation is certified."
        ),
    },
}


def _registry():
    try:
        return ScriptDB.objects.get(db_key=REGISTRY_KEY)
    except ScriptDB.DoesNotExist:
        return create_script(
            "typeclasses.scripts.PublicMysteryRegistry",
            key=REGISTRY_KEY,
            persistent=True,
        )


def get_public_mystery_registry():
    return _registry()


def _fresh(stable_id):
    definition = DEFINITIONS[stable_id]
    return {
        "id": stable_id,
        "title": definition["title"],
        "question": definition["question"],
        "status": "open",
        "observations": [],
        "theories": [],
        "next_theory_id": 1,
        "first_signal_event_id": None,
        "first_signal_rumor_id": None,
        "first_signal_publications": {},
    }


def ensure_public_mysteries():
    registry = _registry()
    mysteries = copy.deepcopy(dict(registry.db.mysteries or {}))
    created = 0
    for stable_id in DEFINITIONS:
        if stable_id not in mysteries:
            mysteries[stable_id] = _fresh(stable_id)
            created += 1
    registry.db.mysteries = mysteries
    return {"created": created, "count": len(mysteries)}


def get_public_mystery(stable_id=MANOR_LIGHTS_ID):
    raw = dict((_registry().db.mysteries or {}).get(stable_id) or {})
    return copy.deepcopy(raw) if raw else None


def _save(mystery):
    registry = _registry()
    mysteries = copy.deepcopy(dict(registry.db.mysteries or {}))
    mysteries[mystery["id"]] = copy.deepcopy(mystery)
    registry.db.mysteries = mysteries
    return copy.deepcopy(mystery)


def _metric(**deltas):
    registry = _registry()
    metrics = copy.deepcopy(dict(registry.db.metrics or {}))
    for key, value in deltas.items():
        metrics[key] = int(metrics.get(key) or 0) + int(value)
    registry.db.metrics = metrics


def _clock():
    try:
        clock = ScriptDB.objects.get(db_key="village_time")
        return int(clock.db.day or 1), int(
            clock.db.hour if clock.db.hour is not None else 21
        )
    except ScriptDB.DoesNotExist:
        return 1, 21


def _weather():
    try:
        return str(
            ScriptDB.objects.get(db_key="village_weather").db.state or "clear"
        ).lower()
    except ScriptDB.DoesNotExist:
        return "clear"


def manor_light_state(day, hour, weather):
    """Return a deterministic observable state without encoding a cause."""
    day = int(day)
    hour = int(hour)
    weather = str(weather or "clear").lower()
    night = hour >= 18 or hour <= 5

    if not night:
        return {
            "lit": False,
            "pattern": "daylight",
            "detail": (
                "In daylight the Manor is a dark mass of roofline and blind "
                "windows. No artificial light is visible from the square."
            ),
        }

    token = f"manor-lights|{day}|{hour}|{weather}".encode("utf-8")
    roll = int.from_bytes(hashlib.sha256(token).digest()[:4], "big") % 100

    # Fog makes distant light easier to notice as a glow, not more supernatural.
    threshold = 45 if weather == "fog" else 34
    if roll >= threshold:
        return {
            "lit": False,
            "pattern": "dark",
            "detail": (
                "The Manor windows remain dark. The hill gives back only a "
                "broken silhouette."
            ),
        }

    patterns = (
        (
            "one_upper_window",
            "One upper window shows a steady amber rectangle.",
        ),
        (
            "three_windows",
            "Three separated windows glow at once, too far apart to be one room.",
        ),
        (
            "east_gallery",
            "A pale light moves behind the east gallery windows, then holds still.",
        ),
    )
    pattern, detail = patterns[roll % len(patterns)]
    return {
        "lit": True,
        "pattern": pattern,
        "detail": detail,
    }


def _player_ref(player):
    account = getattr(player, "account", None)
    return {
        "mask_id": getattr(player, "id", None),
        "mask": getattr(player, "key", None),
        "account_id": getattr(account, "id", None),
    }


def _signal_publication(mystery, observation, actor):
    if mystery.get("first_signal_event_id") or not observation["lit"]:
        return mystery

    from world.events import publish_world_event

    event = publish_world_event(
        "public_mystery.manor_lights.observed",
        actor=actor,
        payload={
            "public_mystery_id": MANOR_LIGHTS_ID,
            "day": observation["day"],
            "hour": observation["hour"],
            "weather": observation["weather"],
            "pattern": observation["pattern"],
            "harbinger": True,
            "chronicle_eligible": False,
        },
        rumor=(
            "Someone watching from the square saw lights burning again in "
            "the hilltop Manor. Nobody agrees on who could be inside."
        ),
    )
    rumor = event.get("rumor") or {}
    try:
        rumor = dict(rumor)
    except Exception:
        rumor = {}
    mystery["first_signal_event_id"] = event["id"]
    mystery["first_signal_rumor_id"] = rumor.get("rumor_id")
    mystery["first_signal_publications"] = copy.deepcopy(
        event.get("publications") or {}
    )
    _metric(public_signals=1)
    return mystery


def observe_manor(player, *, day=None, hour=None, weather=None):
    mystery = get_public_mystery(MANOR_LIGHTS_ID)
    if not mystery:
        ensure_public_mysteries()
        mystery = get_public_mystery(MANOR_LIGHTS_ID)

    if day is None or hour is None:
        clock_day, clock_hour = _clock()
        day = clock_day if day is None else int(day)
        hour = clock_hour if hour is None else int(hour)
    weather = _weather() if weather is None else str(weather).lower()

    state = manor_light_state(day, hour, weather)
    observation_key = f"{int(day)}:{int(hour)}:{weather}:{state['pattern']}"
    observations = copy.deepcopy(list(mystery.get("observations") or []))
    witness = _player_ref(player)
    witness_id = witness.get("mask_id")

    existing_index = next(
        (
            index
            for index, record in enumerate(observations)
            if record.get("key") == observation_key
        ),
        None,
    )

    if existing_index is None:
        record = {
            "key": observation_key,
            "day": int(day),
            "hour": int(hour),
            "weather": weather,
            "lit": bool(state["lit"]),
            "pattern": state["pattern"],
            "detail": state["detail"],
            "witnesses": [witness] if witness_id is not None else [],
        }
        observations.append(record)
        observations = observations[-MAX_OBSERVATIONS:]
        mystery["observations"] = observations
        mystery = _signal_publication(mystery, record, player)
        _metric(observations=1, witness_links=1 if witness_id is not None else 0)
        _save(mystery)
        return copy.deepcopy(record)

    record = copy.deepcopy(dict(observations[existing_index]))
    witnesses = list(record.get("witnesses") or [])
    if witness_id is not None and not any(
        item.get("mask_id") == witness_id for item in witnesses
    ):
        witnesses.append(witness)
        record["witnesses"] = witnesses
        observations[existing_index] = record
        mystery["observations"] = observations
        _metric(witness_links=1)
        _save(mystery)
    return copy.deepcopy(record)


def manor_description(looker=None):
    day, hour = _clock()
    weather = _weather()
    state = manor_light_state(day, hour, weather)

    if looker is not None and getattr(looker, "has_account", False):
        observe_manor(looker, day=day, hour=hour, weather=weather)

    return (
        "The Manor stands above the village on the hill, too distant for "
        "architectural detail from here. "
        + state["detail"]
        + " Whatever the lights mean, distance does not supply the answer."
    )



def bridge_plaque_state(day, hour, weather):
    """Read a physical object under changing light, never infer a culprit."""
    hour = int(hour)
    weather = str(weather or "clear").lower()
    if weather == "rain":
        return {
            "pattern": "rainwater",
            "detail": (
                "Water gathers in three corners of the clean rectangular "
                "socket, leaving the fourth unexpectedly dry. Four old "
                "screws remain sunk in the stone."
            ),
        }
    if hour >= 18 or hour <= 5:
        return {
            "pattern": "lamplight",
            "detail": (
                "In the weak light, soot is caught beside three screws "
                "while the fourth looks recently rubbed. The missing "
                "plaque's outline is clear against darker stone."
            ),
        }
    return {
        "pattern": "daylight",
        "detail": (
            "The bridge has four brass screws around an empty rectangular "
            "socket. The stone beneath the lost plaque is paler than its "
            "surroundings, and tool scratches cross the lower edge."
        ),
    }


def observe_bridge(player, *, day=None, hour=None, weather=None):
    """Record witnessed physical evidence, requiring actual bridge presence."""
    if getattr(getattr(player, "location", None), "key", None) != "The Old Stone Bridge":
        return None
    if not getattr(player, "has_account", False):
        return None
    mystery = get_public_mystery(BRIDGE_PLAQUE_ID)
    if mystery is None:
        ensure_public_mysteries()
        mystery = get_public_mystery(BRIDGE_PLAQUE_ID)
    if day is None or hour is None:
        current_day, current_hour = _clock()
        day = current_day if day is None else day
        hour = current_hour if hour is None else hour
    weather = _weather() if weather is None else str(weather).lower()
    state = bridge_plaque_state(day, hour, weather)
    key = f"{int(day)}:{int(hour)}:{weather}:{state['pattern']}"
    observations = copy.deepcopy(list(mystery.get("observations") or []))
    witness = _player_ref(player)
    existing = next((i for i, obs in enumerate(observations)
                     if obs.get("key") == key), None)
    if existing is not None:
        result = observations[existing]
        if any(item.get("mask_id") == witness["mask_id"]
               and item.get("account_id") == witness["account_id"]
               for item in result.get("witnesses") or []):
            return copy.deepcopy(result)

        # A second firsthand witness needs their OWN signed source. Sharing
        # the first visitor's event ID would falsely attribute their eyes
        # and account to the later Detective.
        from world.events import publish_world_event

        def consequence(event):
            from django.db import transaction
            with transaction.atomic():
                if (getattr(player, "location", None) is None
                        or player.location.key != "The Old Stone Bridge"
                        or not getattr(player, "has_account", False)
                        or _player_ref(player) != witness
                        # Legacy synthetic, accountless world-assertion witnesses
                        # can inspect explicit test weather/time. Real account
                        # witnesses must match the canonical live clock/weather.
                        or (witness["account_id"] is not None
                            and (_clock() != (int(day), int(hour))
                                 or _weather() != weather))):
                    raise ValueError("The second witness left the physical source.")
                fresh = get_public_mystery(BRIDGE_PLAQUE_ID)
                rows = copy.deepcopy(list(fresh.get("observations") or []))
                match = next((row for row in rows if row.get("key") == key), None)
                if (match is None or match.get("source_event_id") != result.get("source_event_id")
                        or match.get("pattern") != state["pattern"]
                        or any(item.get("account_id") == witness["account_id"]
                                   and item.get("mask_id") == witness["mask_id"]
                                   for item in match.get("witnesses") or [])):
                    raise ValueError("The bridge observation changed before witness signing.")
                match.setdefault("witnesses", []).append(
                    dict(witness, source_event_id=event["id"])
                )
                fresh["observations"] = rows
                _save(fresh)
                _metric(witness_links=1)
                return {"source_event_id":event["id"], "pattern":state["pattern"]}

        publish_world_event(
            "public_mystery.bridge_plaque.observed",
            actor=player,
            payload={
                "public_mystery_id":BRIDGE_PLAQUE_ID,
                "day":int(day), "hour":int(hour), "weather":weather,
                "pattern":state["pattern"], "publicity":"private",
                "harbinger":False, "chronicle_eligible":False,
            },
            consequence=consequence,
        )
        fresh = get_public_mystery(BRIDGE_PLAQUE_ID)
        return copy.deepcopy(next(
            row for row in fresh["observations"] if row.get("key") == key
        ))

    from world.events import publish_world_event
    event = publish_world_event(
        "public_mystery.bridge_plaque.observed",
        actor=player,
        payload={
            "public_mystery_id": BRIDGE_PLAQUE_ID,
            "day": int(day), "hour": int(hour), "weather": weather,
            "pattern": state["pattern"], "publicity": "private",
            "harbinger": False, "chronicle_eligible": False,
        },
    )
    record = {
        "key": key, "day": int(day), "hour": int(hour), "weather": weather,
        "detail": state["detail"], "pattern": state["pattern"],
        "witnesses": [dict(witness, source_event_id=event["id"])], "source_event_id": event["id"],
    }
    observations.append(record)
    mystery["observations"] = observations[-MAX_OBSERVATIONS:]
    if not mystery.get("first_signal_event_id"):
        mystery["first_signal_event_id"] = event["id"]
    _save(mystery)
    _metric(observations=1, witness_links=1)
    return copy.deepcopy(record)


def bridge_plaque_description(looker=None):
    day, hour = _clock()
    weather = _weather()
    evidence = bridge_plaque_state(day, hour, weather)
    if looker is not None:
        observe_bridge(looker, day=day, hour=hour, weather=weather)
    return (
        "The empty plaque socket is part of the bridge's weathered stone. "
        + evidence["detail"]
        + " The physical marks do not explain who removed it. "
        "Compare the public |wmystery bridge|n record with other visitors."
    )


def submit_theory(player, text, stable_id=MANOR_LIGHTS_ID):
    mystery = get_public_mystery(stable_id)
    if not mystery or mystery.get("status") != "open":
        return None, "That public question is not open."

    # This is publicly replayed text. Strip Evennia markup pipes and
    # terminal control characters so a player cannot impersonate system
    # messages or inject forged multi-line testimony.
    body = str(text or "").replace("|", " ")
    body = "".join(ch if ch.isprintable() else " " for ch in body)
    body = re.sub(r"\s+", " ", body).strip()
    if not body:
        return None, "A theory needs actual words."
    if len(body) > 600:
        return None, "Keep a public theory under 600 characters."

    # Keep public evidence from being displaced by a single account's
    # repeated speculation. A bounded archive is not permission to
    # silently erase another player's still-active contribution.
    theories = copy.deepcopy(list(mystery.get("theories") or []))
    if len(theories) >= MAX_THEORIES:
        return None, "The public theory archive is full. Ask human staff to review it."
    author = _player_ref(player)
    day = _clock()[0]
    ident = (
        ("account", author["account_id"])
        if author.get("account_id") is not None
        else ("mask", author.get("mask_id"))
    )
    submitted = sum(
        1 for candidate in theories
        if int(candidate.get("created_day") or 0) == day
        and (
            ("account", (candidate.get("author") or {}).get("account_id"))
            if (candidate.get("author") or {}).get("account_id") is not None
            else ("mask", (candidate.get("author") or {}).get("mask_id"))
        ) == ident
    )
    if submitted >= MAX_THEORIES_PER_ACCOUNT_DAY:
        return None, "You may submit at most three public theories per village day."

    theory = {
        "id": int(mystery.get("next_theory_id") or 1),
        "author": author,
        "text": body,
        "status": "proposed",
        "truth_status": None,
        "created_day": _clock()[0],
        "created_hour": _clock()[1],
    }
    theories.append(theory)
    mystery["theories"] = theories
    mystery["next_theory_id"] = theory["id"] + 1
    _save(mystery)
    _metric(theories=1)
    return copy.deepcopy(theory), None



def hide_theory(moderator, theory_id, reason, stable_id=MANOR_LIGHTS_ID):
    """Conceal publicly submitted abuse without erasing signed provenance."""
    account = getattr(moderator, "account", None)
    if not account or not account.check_permstring("Admin"):
        return None, "Only human staff may moderate public mysteries."
    if getattr(getattr(account, "db", None), "substrate", None) != "human":
        return None, "Only human staff may moderate public mysteries."
    mystery = get_public_mystery(stable_id)
    if not mystery:
        return None, "That public mystery is not indexed."
    clean = str(reason or "").replace("|", " ")
    clean = " ".join("".join(
        ch if ch.isprintable() else " " for ch in clean
    ).split())
    if not 3 <= len(clean) <= 180:
        return None, "Supply a 3 to 180 character human moderation reason."
    try:
        ident = int(theory_id)
    except (ValueError, TypeError):
        return None, "Name a numbered theory."
    theories = copy.deepcopy(list(mystery.get("theories") or []))
    entry = next((candidate for candidate in theories
                  if candidate.get("id") == ident), None)
    if not entry:
        return None, "That theory no longer exists in the public archive."
    if entry.get("status") == "hidden":
        return None, "That theory was already hidden."
    day, hour = _clock()
    entry["status"] = "hidden"
    entry["moderation"] = {
        "account_id": account.id,
        "reason": clean,
        "day": day,
        "hour": hour,
    }
    mystery["theories"] = theories
    _save(mystery)
    _metric(hidden_theories=1)
    return copy.deepcopy(entry), None


def resolve_subject(token):
    token = str(token or "").strip().lower()
    if token in {
        "manor",
        "lights",
        "manor lights",
        "manor-lights",
        "hilltop manor",
        "why are the manor lights returning",
    }:
        return MANOR_LIGHTS_ID
    if token in {
        "bridge", "bridge plaque", "missing plaque", "old stone bridge",
        "missing bridge plaque", "inscription",
    }:
        return BRIDGE_PLAQUE_ID
    return None


def examine_bridge_case(player):
    """Detective signs firsthand marks, never an invented culprit."""
    from world.callings import active_calling
    from world.events import get_event_ledger, publish_world_event
    from world.bridge_case_state import examine

    if not getattr(player, "has_account", False) or active_calling(player) != "detective":
        return None, "Only an active Detective may sign a case examination."
    if getattr(getattr(player, "location", None), "key", None) != "The Old Stone Bridge":
        return None, "Examine the original plaque on the Old Stone Bridge."
    day, hour = _clock()
    mystery = get_public_mystery(BRIDGE_PLAQUE_ID)
    if not mystery:
        return None, "The bridge case registry is unavailable."
    actor = _player_ref(player)
    observations = [
        row for row in mystery.get("observations") or []
        if type(row.get("day")) is int and row["day"] == day
        and any(w.get("account_id") == actor["account_id"]
                and w.get("mask_id") == actor["mask_id"]
                for w in row.get("witnesses") or [])
    ]
    if not observations:
        return None, "Look at the physical plaque today before filing a case examination."
    # Bind the Detective to their own signed observation, not the first
    # witness's shared row event. Legacy unsigned secondary witnesses fail
    # actor verification rather than being grandfathered into evidence.
    observation = copy.deepcopy(dict(observations[-1]))
    witnesses = [dict(w) for w in observation.get("witnesses") or []]
    own = next((w for w in witnesses
                if w.get("account_id") == actor["account_id"]
                and w.get("mask_id") == actor["mask_id"]), None)
    if own is None:
        return None, "The Detective has no firsthand bridge witness."
    observation_id = own.get("source_event_id", observation.get("source_event_id"))
    original_id = observation.get("source_event_id")
    if (type(observation_id) is not int or observation_id < 1
            or type(original_id) is not int or original_id < 1):
        return None, "The physical observation has no valid signed event ID."

    ledger = get_event_ledger()
    signed_observation = ledger.get_event(observation_id)
    original = ledger.get_event(original_id)

    def valid_source(event, expected):
        if not event or event.get("status") != "complete":
            return False
        payload, signed_actor = event.get("payload") or {}, event.get("actor") or {}
        return (
            event.get("kind") == "public_mystery.bridge_plaque.observed"
            and type(event.get("id")) is int
            and type(expected.get("source_event_id")) is int
            and event["id"] == expected["source_event_id"]
            and type(signed_actor.get("account_id")) is int
            and type(signed_actor.get("mask_id")) is int
            and signed_actor["account_id"] == expected.get("account_id")
            and signed_actor["mask_id"] == expected.get("mask_id")
            and signed_actor.get("mask") == expected.get("mask")
            and payload.get("public_mystery_id") == BRIDGE_PLAQUE_ID
            and type(payload.get("day")) is int and payload["day"] == day
            and type(payload.get("hour")) is int
            and payload["hour"] == observation.get("hour")
            and payload.get("weather") == observation.get("weather")
            and payload.get("pattern") == observation.get("pattern")
        )

    first = next((w for w in witnesses
                  if w.get("source_event_id", original_id) == original_id), None)
    if (first is None
            or not valid_source(original, dict(first, source_event_id=original_id))
            or not valid_source(signed_observation,
                                dict(own, source_event_id=observation_id))):
        return None, "The physical observation lacks a matching completed actor-bound source."
    observation["source_event_id"] = observation_id
    observation["witnesses"] = [own]
    _, ok, error = examine(
        mystery, day=day, hour=hour, account_id=actor["account_id"],
        mask_id=actor["mask_id"], mask=actor["mask"],
        event_id=observation_id + 1, observation=observation,
    )
    if not ok:
        return None, error

    def consequence(event):
        updated, valid, reason = examine(
            mystery, day=day, hour=hour, account_id=actor["account_id"],
            mask_id=actor["mask_id"], mask=actor["mask"], event_id=event["id"],
            observation=observation,
        )
        if not valid:
            raise ValueError(reason)
        _save(updated)
        return {
            "case_exam_event_id": event["id"],
            "observation_event_id": observation["source_event_id"],
            "pattern": observation["pattern"], "finding": "physical_marks_only",
        }

    event = publish_world_event(
        "village.bridge_plaque_examined", actor=player,
        payload={
            "day": day, "hour": hour, "location": "The Old Stone Bridge",
            "professional_calling": "detective",
            "observation_event_id": observation["source_event_id"],
            "chronicle_eligible": False, "harbinger": False,
        },
        consequence=consequence,
    )
    return event, None


def publish_bridge_case(player):
    """Independent Chronicler publishes an attributed, non-omniscient bulletin."""
    from world.callings import active_calling
    from world.events import get_event_ledger, publish_world_event
    from world.bridge_case_state import publish

    if not getattr(player, "has_account", False) or active_calling(player) != "chronicler":
        return None, "Only an active Chronicler may publish a case bulletin."
    if getattr(getattr(player, "location", None), "key", None) != "Village Square":
        return None, "Publish the case bulletin from Village Square."
    day, hour = _clock()
    mystery = get_public_mystery(BRIDGE_PLAQUE_ID)
    if not mystery:
        return None, "The bridge case registry is unavailable."
    exams = [x for x in mystery.get("case_examinations") or [] if x.get("day") == day]
    if len(exams) != 1:
        return None, "A signed Detective examination is required today."
    exam_id = exams[0].get("event_id")
    observation_id = exams[0].get("observation_event_id")
    if (type(exam_id) is not int or exam_id < 1
            or type(observation_id) is not int or observation_id < 1):
        return None, "The examination lacks valid signed source IDs."
    source = get_event_ledger().get_event(exam_id)
    actor = _player_ref(player)
    _, ok, error = publish(
        mystery, day=day, hour=hour, account_id=actor["account_id"],
        mask_id=actor["mask_id"], mask=actor["mask"],
        event_id=max(exam_id, observation_id) + 1, source=source,
    )
    if not ok:
        return None, error

    def consequence(event):
        updated, valid, reason = publish(
            mystery, day=day, hour=hour, account_id=actor["account_id"],
            mask_id=actor["mask_id"], mask=actor["mask"], event_id=event["id"],
            source=source,
        )
        if not valid:
            raise ValueError(reason)
        _save(updated)
        return {
            "case_bulletin_event_id": event["id"],
            "source_event_id": exams[0]["event_id"],
            "observation_event_id": exams[0]["observation_event_id"],
            "status": "attributed_evidence_only",
        }

    event = publish_world_event(
        "village.bridge_case_bulletin", actor=player,
        payload={
            "day": day, "hour": hour, "location": "Village Square",
            "professional_calling": "chronicler",
            "source_event_id": exams[0]["event_id"],
            "chronicle_eligible": False, "harbinger": False,
        },
        consequence=consequence,
    )
    return event, None


def resolve_subject(token):
    token = str(token or "").strip().lower()
    if token in {
        "manor",
        "lights",
        "manor lights",
        "manor-lights",
        "hilltop manor",
        "why are the manor lights returning",
    }:
        return MANOR_LIGHTS_ID
    if token in {
        "bridge", "bridge plaque", "missing plaque", "old stone bridge",
        "missing bridge plaque", "inscription",
    }:
        return BRIDGE_PLAQUE_ID
    return None


def mystery_lines(player=None, stable_id=MANOR_LIGHTS_ID):
    mystery = get_public_mystery(stable_id)
    if not mystery:
        return ["No public mystery record is available."]

    definition = DEFINITIONS[stable_id]
    observations = list(mystery.get("observations") or [])
    theories = [
        entry for entry in (mystery.get("theories") or [])
        if entry.get("status") != "hidden"
    ]
    lit_count = sum(1 for record in observations if record.get("lit"))

    lines = [
        mystery["title"],
        "Question: " + mystery["question"],
        (
            f"Shared observations: {len(observations)} "
            f"({lit_count} with visible artificial light)."
            if stable_id == MANOR_LIGHTS_ID
            else f"Shared observations: {len(observations)} physical reports."
        ),
    ]

    if observations:
        lines.append("Latest public observations:")
        for record in observations[-5:]:
            witnesses = len(record.get("witnesses") or [])
            lines.append(
                f"  day {record['day']} {record['hour']:02d}:00, "
                f"{record['weather']}: {record['detail']} "
                f"({witnesses} named witness(es))"
            )
    else:
        lines.append(
            "No shared observation has been logged yet. "
            + (
                "The Manor is visible from the Village Square."
                if stable_id == MANOR_LIGHTS_ID
                else "Inspect the empty plaque socket on the Old Stone Bridge."
            )
        )

    if theories:
        lines.append("Provisional theories:")
        for theory in theories[-5:]:
            author = (theory.get("author") or {}).get("mask") or "unknown"
            lines.append(
                f"  T{theory['id']} {author}: {theory['text']}"
            )
    else:
        lines.append("No public theory has been submitted yet.")

    if stable_id == BRIDGE_PLAQUE_ID:
        from world.bridge_case_state import case_lines
        lines.extend(case_lines(mystery, _clock()[0]))
    lines.append(definition["unresolved_note"])
    return lines
