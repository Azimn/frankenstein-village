"""Persistent multiplayer situation and incident engine.

Situations are shared world state. They do not belong to one player and they do
not freeze while nobody is looking. Per-player knowledge is stored separately
from objective state so several players can discover different evidence, arrive
late, disagree, or act on the same situation.

The first production template is canon incident #6, "The tithe strongbox."
"""

from __future__ import annotations

import copy
import time
from collections.abc import Mapping

from evennia import create_script
from evennia.scripts.models import ScriptDB
from evennia.utils import search


REGISTRY_KEY = "situation_registry"
TRUNK_ID = "DM-Q-0001-WRONG-TRUNK"
OBT_ID = "DM-Q-0017-OBTUARY"
WELL_ID = "DM-Q-0018-WELL"
TITHE_ID = "INC-0006-TITHE-STRONGBOX"
TORN_CHRONICLE_ID = "INC-0008-TORN-CHRONICLE"

STATE_ORDER = {
    "dormant": 0,
    "surfaced": 1,
    "investigating": 2,
    "changing": 3,
    "resolved_locally": 4,
    "aftermath": 5,
    "dormant_recurrence": 6,
}

TEMPLATES = {
    TRUNK_ID: {
        "template_id": "dm-q-0001",
        "working_title": "The Wrong Trunk",
        "content_family": "newcomer",
        "canonical_status": "working content",
        "spoiler_tier": 1,
        "primary_location": "Inn Between",
        "secondary_locations": ["Village Square"],
        "involved_npcs": ["porter", "innkeeper", "harbinger_worker"],
        "factions": [],
        "calling_relevance": ["wanderer", "detective", "chronicler"],
        "repeatability": "one-shot",
        "hook": (
            "A trunk arrives at the Inn Between, tagged with your name but bearing "
            "older initials beneath. Inside, old travel tags, a silver locket, and "
            "wear marks tell a story that predates your arrival."
        ),
        "autonomy": {
            "initial_deadline_days": 7,
            "left_alone": (
                "The Innkeeper moves the trunk to long-term storage. Rumor suggests "
                "the owner never returned — or left without telling."
            ),
        },
        "choices": {},  # No explicit door-closing choices; autonomous progression handles outcomes
        "evidence": {
            "tag": {
                "label": "old travel tag",
                "provenance": "physical",
                "summary": (
                    "A faded paper tag showing initials 'V.D.' and a location code "
                    "too worn to read. Once pinned to a suitcase handle."
                ),
            },
            "locket": {
                "label": "small silver locket",
                "provenance": "physical",
                "summary": (
                    "A tarnished oval locket, no engraving visible. The clasp shows "
                    "the same wear as the trunk's latch: months or years of use."
                ),
            },
            "receipt": {
                "label": "travel receipt",
                "provenance": "documentary",
                "summary": (
                    "A folded receipt from a coach departing Borgo Pass three months "
                    "ago. The passenger name line is blank; only the date, route "
                    "number, and fare stamp remain."
                ),
            },
            "wear_marks": {
                "label": "wear marks on trunk",
                "provenance": "environmental",
                "summary": (
                    "A circular dent near the bottom, scuffs from cobblestone, and "
                    "a faint oil stain on the underside suggesting recent movement."
                ),
            },
        },
    },
    TITHE_ID: {
        "template_id": "canon-incident-006",
        "working_title": "The Tithe Strongbox",
        "content_family": "incident",
        "canonical_status": "canon template instantiated",
        "spoiler_tier": 1,
        "primary_location": "St. Lazarus Church",
        "secondary_locations": ["The Blood of the Vine"],
        "involved_npcs": ["father_andrei"],
        "factions": ["St. Lazarus"],
        "calling_relevance": ["chronicler", "detective", "hound"],
        "repeatability": "one-shot",
        "hook": (
            "The church tithe strongbox stands open and light. "
            "The lock is unforced; the vestry key is where it normally hangs."
        ),
        "autonomy": {
            "initial_deadline_days": 7,
            "quiet_deadline_days": 7,
            "left_alone": (
                "Giving dries up. The church roof repair is delayed another winter, "
                "and the parish finally adopts a two-key rule after trust is already lost."
            ),
            "quiet_outcome": (
                "The church keeps the inquiry private for a week. No culprit is named. "
                "The strongbox returns under a two-key rule, but the trail is cold."
            ),
        },
        "choices": {
            "openly": {
                "label": "raise the accusation openly",
                "minimum_evidence": 2,
                "closes": "quiet investigation",
            },
            "quietly": {
                "label": "investigate quietly for a week",
                "minimum_evidence": 2,
                "closes": "public accusation",
            },
        },
        "evidence": {
            "lock": {
                "label": "the unforced lock",
                "provenance": "physical",
                "summary": (
                    "The lock is unforced. Fresh oil and key-scratches sit around "
                    "the ward: somebody opened it with a key or a very good copy."
                ),
            },
            "roll": {
                "label": "the tithe roll",
                "provenance": "documentary",
                "summary": (
                    "The tithe roll was balanced the previous evening and records "
                    "enough coin that the present lightness cannot be bookkeeping."
                ),
            },
            "andrei": {
                "label": "Father Andrei's account",
                "provenance": "witness",
                "summary": (
                    "Andrei says the vestry key was on its usual hook when the loss "
                    "was found. He will not accuse anyone merely for having entered church."
                ),
            },
        },
        "inheritance": (
            "The churchwardens hold duplicate keys and the tithe roll; "
            "the Harbinger files preserve the later public account."
        ),
        "legend": "The two-key rule is cited whenever anything later goes missing.",
        "feed": {
            "initial_state": "surfaced",
            "weight": 100,
            "after": [],
        },
    },
    TORN_CHRONICLE_ID: {
        "template_id": "canon-incident-008",
        "working_title": "The Torn Chronicle",
        "content_family": "incident",
        "canonical_status": "canon template instantiated",
        "spoiler_tier": 1,
        "primary_location": "Chronicle",
        "secondary_locations": ["The Blood of the Vine"],
        "involved_npcs": ["ilona_szabo"],
        "factions": ["Chronicler"],
        "calling_relevance": ["chronicler", "detective"],
        "repeatability": "one-shot",
        "hook": (
            "A numbered sequence of Chronicle pages has been cut out cleanly. "
            "The stubs remain, and the Harbinger archive still covers the missing dates."
        ),
        "autonomy": {
            "initial_deadline_days": 10,
            "left_alone": (
                "The gap remains untouched long enough to become famous in its own right. "
                "Visitors begin coming to see what the village chose not to rewrite."
            ),
        },
        "choices": {
            "reconstruct": {
                "label": "reconstruct the missing sequence from Harbinger files",
                "minimum_evidence": 2,
                "closes": "preserve the gap",
                "aliases": ["rewrite", "restore", "reconstruct"],
            },
            "preserve": {
                "label": "preserve the numbered gap as an honest wound",
                "minimum_evidence": 2,
                "closes": "reconstruct from the newspaper",
                "aliases": ["leave", "gap", "preserve"],
            },
        },
        "evidence": {
            "gap": {
                "label": "the numbered page stubs",
                "provenance": "physical",
                "summary": (
                    "The pages were cut out cleanly rather than torn. Numbered stubs "
                    "show exactly which sequence is missing, but not what those pages said."
                ),
            },
            "harbinger_archive": {
                "label": "the surviving Harbinger files",
                "provenance": "documentary",
                "summary": (
                    "Printed issues survive for the missing dates. They can supply an "
                    "account, but their own source notes and corrections show why newspaper "
                    "copy cannot be treated as recovered server truth."
                ),
            },
            "ilona": {
                "label": "Ilona Szabó's assessment",
                "provenance": "witness",
                "summary": (
                    "Ilona confirms that the cut was deliberate and the numbering is genuine. "
                    "She refuses to pretend that surviving newspaper copy is the same thing as "
                    "the missing Chronicle pages."
                ),
            },
        },
        "inheritance": (
            "The numbered stubs, Harbinger files, and public record itself carry the thread "
            "even if the current Chronicler dies or leaves."
        ),
        "legend": (
            "The missing sequence becomes a standing example whenever later generations "
            "argue over whether uncertainty should be repaired or preserved."
        ),
        "feed": {
            "initial_state": "dormant",
            "weight": 70,
            "after": [TITHE_ID],
        },
    },
    OBT_ID: {
        "template_id": "dm-q-0017",
        "working_title": "Tomorrow's Obituary",
        "content_family": "rumor",
        "canonical_status": "working content",
        "spoiler_tier": 2,
        "primary_location": "Harbinger office",
        "secondary_locations": ["Village square", "Church"],
        "involved_npcs": ["harbinger_editor", "printer", "witness", "rival_detective"],
        "factions": ["Harbinger"],
        "calling_relevance": ["chronicler", "detective", "merchant"],
        "repeatability": "one-shot",
        "hook": (
            "A typed obituary sits on the editorial desk, signed by a grieving family "
            "for a resident who is still walking through the square. The copy appears "
            "legitimate: correct spelling, proper format, matching handwriting with "
            "previous submissions. But its source is unclear."
        ),
        "autonomy": {
            "initial_deadline_hours": 12,
            "left_alone": (
                "The printer schedules the obituary for tomorrow's edition. "
                "Village rumors spread. A rival investigator publishes a competing theory."
            ),
        },
        "choices": {
            "editor_decision": {
                "label": "Editorial decision",
                "branch_from": "initial",
                "options": [
                    {"label": "Publish as submitted", "outcome": "published"},
                    {"label": "Delay and investigate", "outcome": "investigated"},
                    {"label": "Suppress without explanation", "outcome": "suppressed"},
                ],
            },
        },
        "evidence": {
            "obituary_copy": {
                "label": "typed obituary copy",
                "provenance": "documentary",
                "summary": (
                    "A professionally typeset obituary for the deceased, written "
                    "in the standard Harbinger format. The date of death is precise "
                    "and matches the family's account. The source signature is "
                    "legible but unfamiliar to the editorial staff."
                ),
            },
            "source_letter": {
                "label": "letter from the family",
                "provenance": "documentary",
                "summary": (
                    "A sealed letter accompanying the obituary, explaining why "
                    "publication is urgent. The handwriting matches known family "
                    "samples, but the letter contains no specific biographical details "
                    "only a request for speed."
                ),
            },
            "rival_theory": {
                "label": "rival investigator's theory",
                "provenance": "rumor",
                "summary": (
                    "A detective who specializes in 'false death notices' has "
                    "published a theory that the obituary is part of a pattern of "
                    "identity theft used to clear debts or evade legal obligations."
                ),
            },
            "witness_accounts": {
                "label": "witness testimony",
                "provenance": "witness",
                "summary": (
                    "Several villagers recall seeing the deceased in public over "
                    "the past month. Their confidence varies, and their descriptions "
                    "of the person disagree in minor but notable details."
                ),
            },
            "printer_notes": {
                "label": "printer's production notes",
                "provenance": "documentary",
                "summary": (
                    "Internal notes about scheduling, ink usage, and plate changes "
                    "that reveal the obituary was assigned a premium time slot, "
                    "suggesting it was expected to be front-page content."
                ),
            },
            "board_directive": {
                "label": "editorial board directive",
                "provenance": "documentary",
                "summary": (
                    "A confidential memo from the board warning editors against "
                    "publishing 'unverified obituaries' due to a recent scandal "
                    "where false death notices were used to manipulate public opinion."
                ),
            },
        },
        "npc_beliefs": {
            "harbinger_editor": {
                "initial": (
                    "The editor believes the obituary is legitimate but feels "
                    "obliged to verify because of the board directive. They are "
                    "conflicted between journalistic duty and institutional caution."
                ),
            },
            "rival_detective": {
                "initial": "The detective believes the obituary is part of a pattern of false death notices.",
            },
        },
        "rumors": [
            "The obituary was submitted by a foreign correspondent.",
            "The deceased was actually a member of the Hounds.",
            "The editor is using the obituary to test the printing schedule.",
            "The obituary author is still alive and will appear at the next council meeting.",
        ],
        "harbinger_consequences": [
            "The story may be republished as a correction or as a 'story of the week.'",
            "The editorial board may issue a statement on verifying obituary sources.",
            "The obituary may appear in the Chronicle as a notable error or cautionary tale.",
        ],
        "chronicle_eligibility": {
            "primary": "A published false obituary in the Harbinger",
            "secondary": "The editor's response to the incident",
        },
        "follow_up": {
            "immediate": "Investigation of the obituary's source and the deceased's whereabouts.",
            "medium": "Publication of a correction or editorial note explaining the incident.",
            "long_term": "Debate over the ethics of publishing death notices without verification.",
        },
        "aftermath": {
            "world_state": "Public belief about the deceased is altered; rumors about the editor's credibility spread.",
            "npc_effects": "The rival detective gains followers; the editor may become more cautious or more defensive.",
            "evidence_state": "The obituary copy may be archived, destroyed, or repurposed as evidence in a future case.",
        },
    },}


def _clock():
    try:
        clock = ScriptDB.objects.get(db_key="village_time")
        return int(clock.db.day or 1), int(
            clock.db.hour if clock.db.hour is not None else 21
        )
    except ScriptDB.DoesNotExist:
        return 1, 21


def _registry():
    try:
        return ScriptDB.objects.get(db_key=REGISTRY_KEY)
    except ScriptDB.DoesNotExist:
        return create_script(
            "typeclasses.scripts.SituationRegistry",
            key=REGISTRY_KEY,
            persistent=True,
        )


def get_situation_registry():
    return _registry()


def _player_key(player):
    return str(getattr(player, "id", ""))


def _new_situation(stable_id, *, day, hour):
    template = TEMPLATES[stable_id]
    initial_state = (template.get("feed") or {}).get(
        "initial_state", "dormant"
    )
    surfaced = initial_state == "surfaced"
    deadline_day = (
        int(day) + int(template["autonomy"]["initial_deadline_days"])
        if surfaced
        else None
    )
    return {
        "id": stable_id,
        "template_id": template["template_id"],
        "working_title": template["working_title"],
        "content_family": template["content_family"],
        "canonical_status": template["canonical_status"],
        "spoiler_tier": template["spoiler_tier"],
        "primary_location": template["primary_location"],
        "secondary_locations": list(template["secondary_locations"]),
        "involved_npcs": list(template["involved_npcs"]),
        "factions": list(template["factions"]),
        "calling_relevance": list(template["calling_relevance"]),
        "repeatability": template["repeatability"],
        "state": initial_state,
        "surfaced_day": int(day) if surfaced else None,
        "surfaced_hour": int(hour) if surfaced else None,
        "deadline_day": deadline_day,
        "deadline_hour": int(hour) if surfaced else None,
        "surface_count": 1 if surfaced else 0,
        "branch": None,
        "resolved_day": None,
        "resolved_hour": None,
        "objective_mutations": {},
    WELL_ID: {
        "template_id": "dm-q-0018",
        "working_title": "The Well Boils",
        "content_family": "timed_incident",
        "canonical_status": "working content",
        "spoiler_tier": 2,
        "primary_location": "Tribute well",
        "secondary_locations": ["Village square", "St. Lazarus Church"],
        "involved_npcs": ["father_andrei", "castle_guard", "villager_witness", "harbinger_reporter"],
        "factions": ["St. Lazarus", "Castle"],
        "calling_relevance": ["hound", "chronicler", "merchant", "detective"],
        "repeatability": "one-shot",
        "hook": (
            "Steam thickens around the tribute well as the bell rings. The vapor "
            "is denser than usual, smelling faintly of ozone and copper. NPCs begin "
            "converging from their scheduled routines, each with a different theory."
        ),
        "autonomy": {
            "initial_deadline_hours": 4,
            "left_alone": (
                "The steam clears without explanation. Father Andrei records it in "
                "the church ledger as a 'miracle.' The castle guard notes the well "
                "pump ran unusually hot that evening. The village gossip mill turns "
                "toward the well for weeks."
            ),
        },
        "choices": {
            "player_response": {
                "label": "Player response",
                "branch_from": "initial",
                "options": [
                    {"label": "Approach and examine", "outcome": "investigated"},
                    {"label": "Document and publish", "outcome": "published"},
                    {"label": "Report to the church", "outcome": "reported_to_church"},
                    {"label": "Ignore and continue", "outcome": "ignored"},
                ],
            },
        },
        "evidence": {
            "steam_condensation": {
                "label": "condensation on nearby surfaces",
                "provenance": "physical",
                "summary": (
                    "Metal surfaces within 15 feet show water droplets and slight "
                    "corrosion. The pattern suggests sustained steam rather than a "
                    "brief burst."
                ),
            },
            "copper_odor": {
                "label": "faint copper smell",
                "provenance": "environmental",
                "summary": (
                    "A metallic tang lingers near the well. Could be pipe corrosion, "
                    "or something more unusual."
                ),
            },
            "well_pump_heat": {
                "label": "pump temperature",
                "provenance": "environmental",
                "summary": (
                    "The tribute well pump housing is warmer than normal, suggesting "
                    "unusual electrical load or mechanical friction."
                ),
            },
            "npc_testimony": {
                "label": "converging witness accounts",
                "provenance": "witness",
                "summary": (
                    "Multiple NPCs arrive within minutes of each other, each with "
                    "different theories about the cause and meaning of the steam."
                ),
            },
            "harbinger_note": {
                "label": "reporter's field notes",
                "provenance": "documentary",
                "summary": (
                    "A Harbinger reporter arrives with notebook and pencil. Their "
                    "initial observations may contradict or support your own."
                ),
            },
            "church_ledger": {
                "label": "pre-existing ledger entry",
                "provenance": "documentary",
                "summary": (
                    "The church already has an entry for 'unusual well behavior' "
                    "from a previous week. This incident may be a recurrence."
                ),
            },
        },
        "npc_beliefs": {
            "father_andrei": {
                "initial": "Father Andrei believes this is a miraculous sign, but is cautious about declaring it.",
            },
            "castle_guard": {
                "initial": "The guard is suspicious of any unexplained activity near the tribute well.",
            },
            "villager_witness": {
                "initial": "The villager is torn between superstition and practical explanation (pump failure).",
            },
            "harbinger_reporter": {
                "initial": "The reporter is looking for a story angle that will sell well. They're skeptical but professional.",
            },
        },
        "rumors": [
            "The steam is a warning from the Castle about tribute quality.",
            "The well pump is failing and needs replacement.",
            "Victor Frankenstein is testing the tribute mechanism.",
            "The Hounds have been sabotaging the tribute for months.",
            "This is the sign the Chronicle will record as the beginning of 'The Well Era.'",
        ],
        "harbinger_consequences": [
            "The article may be published with your byline or as anonymous source material.",
            "Later well incidents may be measured against your initial account.",
            "The Harbinger may cite your observations in a special edition.",
        ],
        "chronicle_eligibility": {
            "primary": "The well boiling incident as recorded in village memory",
            "secondary": "Your role in documenting or responding to the event",
        },
        "follow_up": {
            "immediate": "NPCs converge and make sense of the event. Church or castle records are updated.",
            "medium": "The well becomes a focal point for future incidents and rumors.",
            "long_term": "Your involvement (or lack thereof) creates lasting social consequences.",
        },
        "aftermath": {
            "world_state": "The well remains physically unchanged but becomes a local landmark in conversation.",
            "npc_effects": "NPCs adjust their theories and future behavior based on your response.",
            "evidence_state": "First-hand evidence degrades over time; secondhand accounts become rumor.",
        },
    },        "player_knowledge": {},
        "choice_history": [],
        "event_ids": [],
        "rumor_ids": [],
        "publications": [],
        "aftermath": None,
        "version": 1,
    }


def ensure_situations():
    registry = _registry()
    situations = copy.deepcopy(dict(registry.db.situations or {}))
    day, hour = _clock()
    created = 0
    for stable_id in TEMPLATES:
        if stable_id not in situations:
            situations[stable_id] = _new_situation(
                stable_id,
                day=day,
                hour=hour,
            )
            created += 1
    registry.db.situations = situations
    return {"created": created, "count": len(situations)}


ACTIVE_STATES = {"surfaced", "investigating", "changing"}


def _feed_eligible(stable_id, situations, *, day, hour):
    situation = dict(situations.get(stable_id) or {})
    template = TEMPLATES[stable_id]
    feed = dict(template.get("feed") or {})
    if situation.get("state") not in {"dormant", "dormant_recurrence"}:
        return False

    for dependency in feed.get("after") or []:
        prior = dict(situations.get(dependency) or {})
        if prior.get("state") not in {"aftermath", "resolved_locally"}:
            return False

    not_before_day = feed.get("not_before_day")
    if not_before_day is not None and int(day) < int(not_before_day):
        return False

    cooldown_until = situation.get("cooldown_until_day")
    if cooldown_until is not None and int(day) < int(cooldown_until):
        return False

    required_weather = feed.get("weather")
    if required_weather:
        try:
            weather = ScriptDB.objects.get(db_key="village_weather")
            if str(weather.db.current or weather.db.state or "").lower() not in {
                str(value).lower() for value in required_weather
            }:
                return False
        except ScriptDB.DoesNotExist:
            return False

    required_season_tags = set(feed.get("season_tags") or [])
    if required_season_tags:
        try:
            from world.seasonal_frameworks import content_tags
            if not required_season_tags.issubset(content_tags()):
                return False
        except Exception:
            return False

    return True


def incident_feed_candidates(*, day=None, hour=None):
    """Return deterministic eligible incident candidates in feed order."""
    if day is None or hour is None:
        now_day, now_hour = _clock()
        day = now_day if day is None else int(day)
        hour = now_hour if hour is None else int(hour)

    situations = copy.deepcopy(dict(_registry().db.situations or {}))
    candidates = []
    for stable_id, template in TEMPLATES.items():
        if not _feed_eligible(
            stable_id,
            situations,
            day=int(day),
            hour=int(hour),
        ):
            continue
        feed = dict(template.get("feed") or {})
        score = int(feed.get("weight") or 0)
        preferred_hours = list(feed.get("preferred_hours") or [])
        if preferred_hours and int(hour) in preferred_hours:
            score += 15
        candidates.append({
            "id": stable_id,
            "score": score,
            "title": template["working_title"],
        })
    return sorted(
        candidates,
        key=lambda entry: (-entry["score"], entry["id"]),
    )


def _surface_side_effects(stable_id):
    if stable_id == TORN_CHRONICLE_ID:
        try:
            from world.publications import get_public_record_registry
            public_records = get_public_record_registry()
            public_records.db.chronicle_gap_policy = "open_gap"
            public_records.db.chronicle_gap_source = None
        except Exception:
            pass


def surface_incident_feed(*, day=None, hour=None, max_active=1):
    """Fill available incident slots without player ownership or acceptance."""
    if day is None or hour is None:
        now_day, now_hour = _clock()
        day = now_day if day is None else int(day)
        hour = now_hour if hour is None else int(hour)

    registry = _registry()
    situations = copy.deepcopy(dict(registry.db.situations or {}))
    active = sum(
        1 for situation in situations.values()
        if dict(situation).get("state") in ACTIVE_STATES
    )
    slots = max(0, int(max_active) - active)
    if not slots:
        return []

    surfaced = []
    candidates = incident_feed_candidates(day=day, hour=hour)
    for candidate in candidates[:slots]:
        stable_id = candidate["id"]
        situation = dict(situations[stable_id])
        template = TEMPLATES[stable_id]
        situation["state"] = "surfaced"
        situation["surfaced_day"] = int(day)
        situation["surfaced_hour"] = int(hour)
        situation["deadline_day"] = int(day) + int(
            template["autonomy"]["initial_deadline_days"]
        )
        situation["deadline_hour"] = int(hour)
        situation["surface_count"] = int(situation.get("surface_count") or 0) + 1
        situations[stable_id] = situation
        surfaced.append(stable_id)

    if surfaced:
        registry.db.situations = situations
        for stable_id in surfaced:
            _surface_side_effects(stable_id)
        _metrics(feed_surfaces=len(surfaced))
    _metrics(feed_checks=1)
    return surfaced


SUBJECT_ALIASES = {
    "strongbox": TITHE_ID,
    "tithe": TITHE_ID,
    "tithe strongbox": TITHE_ID,
    "church strongbox": TITHE_ID,
    TITHE_ID.lower(): TITHE_ID,
    "chronicle": TORN_CHRONICLE_ID,
    "torn chronicle": TORN_CHRONICLE_ID,
    "chronicle gap": TORN_CHRONICLE_ID,
    "missing pages": TORN_CHRONICLE_ID,
    TORN_CHRONICLE_ID.lower(): TORN_CHRONICLE_ID,
}


def resolve_situation_subject(subject):
    return SUBJECT_ALIASES.get(str(subject or "").strip().lower())


def _normalize_choice(stable_id, choice):
    raw = str(choice or "").strip().lower()
    template = TEMPLATES.get(stable_id) or {}
    for canonical, definition in (template.get("choices") or {}).items():
        aliases = set(definition.get("aliases") or [])
        aliases.add(canonical)
        if raw in aliases:
            return canonical
    if stable_id == TITHE_ID:
        legacy = {
            "open": "openly",
            "public": "openly",
            "publicly": "openly",
            "accuse": "openly",
            "quiet": "quietly",
            "private": "quietly",
            "privately": "quietly",
        }
        return legacy.get(raw, raw if raw in {"openly", "quietly"} else None)
    return None


def choice_names(stable_id):
    return list((TEMPLATES.get(stable_id) or {}).get("choices") or {})


def get_situation(stable_id=TITHE_ID):
    situation = dict((_registry().db.situations or {}).get(stable_id) or {})
    return copy.deepcopy(situation) if situation else None


def _save(situation):
    registry = _registry()
    situations = copy.deepcopy(dict(registry.db.situations or {}))
    situations[situation["id"]] = copy.deepcopy(situation)
    registry.db.situations = situations
    return copy.deepcopy(situation)


def _metrics(**deltas):
    registry = _registry()
    metrics = copy.deepcopy(dict(registry.db.metrics or {}))
    for key, value in deltas.items():
        metrics[key] = int(metrics.get(key) or 0) + int(value)
    registry.db.metrics = metrics


def _knowledge(situation, player):
    key = _player_key(player)
    current = dict((situation.get("player_knowledge") or {}).get(key) or {})
    return {
        "player_id": getattr(player, "id", None),
        "player_name": getattr(player, "key", None),
        "discovered": bool(current.get("discovered")),
        "evidence": list(current.get("evidence") or []),
        "first_day": current.get("first_day"),
        "first_hour": current.get("first_hour"),
        "last_day": current.get("last_day"),
        "last_hour": current.get("last_hour"),
        "developments": list(current.get("developments") or []),
    }


def discover_situation(player, stable_id=TITHE_ID, *, note=None):
    situation = get_situation(stable_id)
    if not situation:
        return None
    day, hour = _clock()
    knowledge = _knowledge(situation, player)
    first = not knowledge["discovered"]
    if first:
        knowledge["discovered"] = True
        knowledge["first_day"] = day
        knowledge["first_hour"] = hour
        knowledge["developments"].append(
            "You discovered that the church tithe strongbox is open and light."
        )
    if note and note not in knowledge["developments"]:
        knowledge["developments"].append(str(note))
    knowledge["last_day"] = day
    knowledge["last_hour"] = hour
    all_knowledge = dict(situation.get("player_knowledge") or {})
    all_knowledge[_player_key(player)] = knowledge
    situation["player_knowledge"] = all_knowledge
    _save(situation)
    if first:
        _metrics(discoveries=1)
    return copy.deepcopy(knowledge)


def discover_evidence(player, evidence_id, stable_id=TITHE_ID):
    situation = get_situation(stable_id)
    template = TEMPLATES.get(stable_id)
    if not situation or not template or evidence_id not in template["evidence"]:
        return None
    if STATE_ORDER.get(situation["state"], 0) < STATE_ORDER["surfaced"]:
        return None

    knowledge = discover_situation(player, stable_id)
    if evidence_id not in knowledge["evidence"]:
        knowledge["evidence"].append(evidence_id)
        evidence = template["evidence"][evidence_id]
        knowledge["developments"].append(
            f"Evidence: {evidence['label']}. {evidence['summary']}"
        )
        day, hour = _clock()
        knowledge["last_day"] = day
        knowledge["last_hour"] = hour
        all_knowledge = dict(situation.get("player_knowledge") or {})
        all_knowledge[_player_key(player)] = knowledge
        situation["player_knowledge"] = all_knowledge
        if situation["state"] == "surfaced":
            situation["state"] = "investigating"
        _save(situation)
        _metrics(discoveries=1)
    return copy.deepcopy(template["evidence"][evidence_id])


def known_situations(player):
    result = []
    for stable_id, raw in (_registry().db.situations or {}).items():
        situation = dict(raw)
        knowledge = _knowledge(situation, player)
        if knowledge["discovered"]:
            result.append((copy.deepcopy(situation), knowledge))
    return sorted(
        result,
        key=lambda pair: (
            int(pair[1].get("last_day") or 0),
            int(pair[1].get("last_hour") or 0),
            pair[0]["id"],
        ),
        reverse=True,
    )


def _church():
    found = [
        obj for obj in search.search_object("St. Lazarus Church")
        if obj.key == "St. Lazarus Church"
    ]
    return found[0] if found else None


def _record_event(situation, event):
    if not event:
        return situation
    ids = list(situation.get("event_ids") or [])
    if event["id"] not in ids:
        ids.append(event["id"])
    situation["event_ids"] = ids
    rumor = event.get("rumor") or {}
    if isinstance(rumor, Mapping) and rumor.get("rumor_id"):
        rumor_ids = list(situation.get("rumor_ids") or [])
        if rumor["rumor_id"] not in rumor_ids:
            rumor_ids.append(rumor["rumor_id"])
        situation["rumor_ids"] = rumor_ids
    pubs = event.get("publications") or {}
    if isinstance(pubs, Mapping) and any(v is not None for v in pubs.values()):
        publications = list(situation.get("publications") or [])
        publications.append(dict(pubs))
        situation["publications"] = publications
    return situation


def _apply_two_key_rule():
    church = _church()
    if not church:
        return {"church_found": False}
    church.db.tithe_strongbox_policy = "two_key"
    return {
        "church_found": True,
        "tithe_strongbox_policy": "two_key",
    }


def _apply_open_aftermath(situation, player):
    from world.events import publish_world_event

    day, hour = _clock()

    def consequence(_event):
        result = _apply_two_key_rule()
        church = _church()
        if church:
            church.db.tithe_confidence = "divided"
        result["tithe_confidence"] = "divided"
        return result

    event = publish_world_event(
        "incident.tithe_strongbox.open_accusation",
        actor=player,
        payload={
            "situation_id": situation["id"],
            "headline": "Church Strongbox Loss Made Public",
            "public_summary": (
                "The missing tithe money has been raised openly before the village. "
                "The lock showed no force, and St. Lazarus has adopted a two-key rule."
            ),
            "chronicle_eligible": True,
            "publication_priority": "special",
            "resident_ids": ["father_andrei"],
        },
        rumor=(
            "St. Lazarus keeps two keys to the tithe box now. Someone opened the old "
            "lock without forcing it, and the whole village heard about it."
        ),
        consequence=consequence,
    )
    situation = _record_event(situation, event)
    situation["state"] = "aftermath"
    situation["branch"] = "openly"
    situation["resolved_day"] = day
    situation["resolved_hour"] = hour
    situation["objective_mutations"] = {
        "tithe_strongbox_policy": "two_key",
        "tithe_confidence": "divided",
    }
    situation["aftermath"] = (
        "The accusation is public. St. Lazarus now uses two keys; the missing "
        "money remains an open wound rather than a solved theft."
    )
    return situation


def _begin_quiet_investigation(situation, player):
    from world.events import publish_world_event

    day, hour = _clock()
    event = publish_world_event(
        "incident.tithe_strongbox.quiet_inquiry",
        actor=player,
        payload={
            "situation_id": situation["id"],
            "publicity": "private",
            "resident_ids": ["father_andrei"],
        },
    )
    situation = _record_event(situation, event)
    situation["state"] = "changing"
    situation["branch"] = "quietly"
    situation["deadline_day"] = day + int(
        TEMPLATES[situation["id"]]["autonomy"]["quiet_deadline_days"]
    )
    situation["deadline_hour"] = hour
    situation["aftermath"] = None
    return situation


def _set_chronicle_gap_policy(policy, *, source=None):
    from world.publications import get_public_record_registry

    registry = get_public_record_registry()
    registry.db.chronicle_gap_policy = str(policy)
    registry.db.chronicle_gap_source = source
    return {
        "chronicle_gap_policy": str(policy),
        "chronicle_gap_source": source,
    }


def _apply_torn_reconstruct(situation, player):
    from world.events import publish_world_event

    day, hour = _clock()

    def consequence(_event):
        return _set_chronicle_gap_policy(
            "reconstructed_from_harbinger",
            source="Harbinger archive",
        )

    event = publish_world_event(
        "incident.torn_chronicle.reconstructed",
        actor=player,
        payload={
            "situation_id": situation["id"],
            "headline": "Missing Chronicle Sequence Reconstructed",
            "public_summary": (
                "The missing Chronicle sequence has been reconstructed from surviving "
                "Harbinger files. The replacement is explicitly marked as press-derived "
                "rather than recovered original text."
            ),
            "chronicle_summary": (
                "The Chronicle records that its missing numbered sequence was "
                "reconstructed from surviving Harbinger files. The reconstruction is "
                "marked as press-derived and does not claim to recover the lost original."
            ),
            "chronicle_eligible": True,
            "publication_priority": "special",
            "resident_ids": ["ilona_szabo"],
        },
        rumor=(
            "They filled the Chronicle's missing pages from old Harbinger files. "
            "Some call it repair; some call it copying yesterday's mistakes into history."
        ),
        consequence=consequence,
    )
    situation = _record_event(situation, event)
    situation["state"] = "aftermath"
    situation["branch"] = "reconstruct"
    situation["resolved_day"] = day
    situation["resolved_hour"] = hour
    situation["objective_mutations"] = {
        "chronicle_gap_policy": "reconstructed_from_harbinger",
        "chronicle_gap_source": "Harbinger archive",
    }
    situation["aftermath"] = (
        "The numbered gap has been filled with a reconstruction derived from surviving "
        "Harbinger issues. The new pages are plainly marked as reconstruction, not original."
    )
    return situation


def _apply_torn_preserve(situation, player):
    from world.events import publish_world_event

    day, hour = _clock()

    def consequence(_event):
        return _set_chronicle_gap_policy("preserved_gap", source=None)

    event = publish_world_event(
        "incident.torn_chronicle.gap_preserved",
        actor=player,
        payload={
            "situation_id": situation["id"],
            "headline": "Chronicle Leaves Missing Sequence Blank",
            "public_summary": (
                "The Chronicler has preserved the numbered gap rather than replace "
                "missing pages with a newspaper reconstruction. The absence is now "
                "part of the public record."
            ),
            "chronicle_summary": (
                "The Chronicle records the decision to preserve its missing numbered "
                "sequence as a documented gap rather than infer lost text from the press."
            ),
            "chronicle_eligible": True,
            "publication_priority": "special",
            "resident_ids": ["ilona_szabo"],
        },
        rumor=(
            "The Chronicler left the missing pages blank on purpose. The empty sequence "
            "now says more to half the village than a reconstruction would have."
        ),
        consequence=consequence,
    )
    situation = _record_event(situation, event)
    situation["state"] = "aftermath"
    situation["branch"] = "preserve"
    situation["resolved_day"] = day
    situation["resolved_hour"] = hour
    situation["objective_mutations"] = {
        "chronicle_gap_policy": "preserved_gap",
        "chronicle_gap_source": None,
    }
    situation["aftermath"] = (
        "The numbered gap remains visible and documented. Later readers can see where "
        "the record failed instead of mistaking a reconstruction for recovered history."
    )
    return situation


def _apply_choice(situation, player, normalized):
    stable_id = situation["id"]
    if stable_id == TITHE_ID:
        if normalized == "openly":
            return _apply_open_aftermath(situation, player)
        if normalized == "quietly":
            return _begin_quiet_investigation(situation, player)
    elif stable_id == TORN_CHRONICLE_ID:
        if normalized == "reconstruct":
            return _apply_torn_reconstruct(situation, player)
        if normalized == "preserve":
            return _apply_torn_preserve(situation, player)
    return None


def choose(player, choice, stable_id=TITHE_ID):
    """Make the first canonical door-closing choice for a shared situation."""
    situation = get_situation(stable_id)
    template = TEMPLATES.get(stable_id)
    if not situation or not template:
        return None, "That situation is not present in the village."
    if situation.get("state") == "dormant":
        return None, "That situation has not surfaced in the village."

    normalized = _normalize_choice(stable_id, choice)
    if normalized not in template["choices"]:
        options = " or ".join(choice_names(stable_id))
        return None, f"Choose {options}."

    if situation.get("branch") or STATE_ORDER.get(
        situation.get("state"), 0
    ) >= STATE_ORDER["changing"]:
        return None, (
            "That door has already closed. The situation has changed for everyone."
        )

    knowledge = _knowledge(situation, player)
    required = int(template["choices"][normalized]["minimum_evidence"])
    if len(set(knowledge["evidence"])) < required:
        return None, (
            f"You have {len(set(knowledge['evidence']))} useful evidence source(s). "
            f"You need at least {required} before making that choice."
        )

    day, hour = _clock()
    history = list(situation.get("choice_history") or [])
    history.append({
        "choice": normalized,
        "player_id": getattr(player, "id", None),
        "player_name": getattr(player, "key", None),
        "day": day,
        "hour": hour,
        "evidence_ids": list(knowledge["evidence"]),
    })
    situation["choice_history"] = history

    situation = _apply_choice(situation, player, normalized)
    if not situation:
        return None, "That choice has no implemented world consequence."

    _save(situation)
    _metrics(choices=1)
    discover_situation(
        player,
        stable_id,
        note=f"You chose to {template['choices'][normalized]['label']}.",
    )

    # A resolved incident frees a feed slot immediately. A changing incident
    # still occupies its slot until its autonomous deadline is reached.
    surface_incident_feed(day=day, hour=hour, max_active=1)
    return get_situation(stable_id), None

def _left_alone(situation):
    from world.events import publish_world_event

    day, hour = _clock()

    def consequence(_event):
        result = _apply_two_key_rule()
        church = _church()
        if church:
            church.db.tithe_confidence = "low"
            church.db.roof_repair_delay_winters = int(
                church.db.roof_repair_delay_winters or 0
            ) + 1
        result.update({
            "tithe_confidence": "low",
            "roof_repair_delay_winters": (
                int(church.db.roof_repair_delay_winters or 0) if church else 1
            ),
        })
        return result

    event = publish_world_event(
        "incident.tithe_strongbox.left_alone",
        payload={
            "situation_id": situation["id"],
            "headline": "Church Giving Falls After Unresolved Loss",
            "public_summary": (
                "The tithe loss was never publicly settled. Giving has fallen, "
                "the roof repair has slipped another winter, and the strongbox "
                "now requires two keys."
            ),
            "chronicle_eligible": True,
            "resident_ids": ["father_andrei"],
        },
        rumor=(
            "Nobody ever settled what happened to the church money. People give "
            "less now, and two different hands are needed to open the box."
        ),
        consequence=consequence,
    )
    situation = _record_event(situation, event)
    situation["state"] = "aftermath"
    situation["branch"] = "left_alone"
    situation["resolved_day"] = day
    situation["resolved_hour"] = hour
    situation["objective_mutations"] = {
        "tithe_strongbox_policy": "two_key",
        "tithe_confidence": "low",
        "roof_repair_delay_winters": int(
            getattr(_church().db, "roof_repair_delay_winters", 1) or 1
        ) if _church() else 1,
    }
    situation["aftermath"] = TEMPLATES[situation["id"]]["autonomy"]["left_alone"]
    return situation


def _torn_left_alone(situation):
    from world.events import publish_world_event

    day, hour = _clock()

    def consequence(_event):
        return _set_chronicle_gap_policy("famous_gap", source=None)

    event = publish_world_event(
        "incident.torn_chronicle.left_alone",
        payload={
            "situation_id": situation["id"],
            "headline": "Visitors Come to See the Chronicle Gap",
            "public_summary": (
                "The missing Chronicle sequence has remained untouched long enough "
                "to become an object of study. Visitors now ask to see the numbered stubs."
            ),
            "chronicle_summary": (
                "The Chronicle records that its missing sequence remains unreconstructed "
                "and has itself become a subject of public and scholarly attention."
            ),
            "chronicle_eligible": True,
            "resident_ids": ["ilona_szabo"],
        },
        rumor=(
            "People have begun coming from outside the village just to see the Chronicle's "
            "missing pages. Nobody agrees whether that makes the gap evidence or attraction."
        ),
        consequence=consequence,
    )
    situation = _record_event(situation, event)
    situation["state"] = "aftermath"
    situation["branch"] = "left_alone"
    situation["resolved_day"] = day
    situation["resolved_hour"] = hour
    situation["objective_mutations"] = {
        "chronicle_gap_policy": "famous_gap",
        "chronicle_gap_source": None,
    }
    situation["aftermath"] = TEMPLATES[situation["id"]]["autonomy"]["left_alone"]
    return situation


def _finish_quiet(situation):
    from world.events import publish_world_event

    day, hour = _clock()

    def consequence(_event):
        result = _apply_two_key_rule()
        church = _church()
        if church:
            church.db.tithe_confidence = "guarded"
        result["tithe_confidence"] = "guarded"
        return result

    event = publish_world_event(
        "incident.tithe_strongbox.quiet_aftermath",
        payload={
            "situation_id": situation["id"],
            "headline": "St. Lazarus Changes Strongbox Procedure",
            "public_summary": (
                "After a private week-long inquiry, St. Lazarus has placed the "
                "tithe strongbox under a two-key rule. No culprit has been named."
            ),
            "chronicle_eligible": True,
            "resident_ids": ["father_andrei"],
        },
        rumor=(
            "The church changed the tithe-box locks after a week of quiet questions. "
            "No one was named, which has not stopped the naming."
        ),
        consequence=consequence,
    )
    situation = _record_event(situation, event)
    situation["state"] = "aftermath"
    situation["resolved_day"] = day
    situation["resolved_hour"] = hour
    situation["objective_mutations"] = {
        "tithe_strongbox_policy": "two_key",
        "tithe_confidence": "guarded",
    }
    situation["aftermath"] = TEMPLATES[situation["id"]]["autonomy"]["quiet_outcome"]
    return situation


def advance_situations(*, day=None, hour=None):
    """Advance due situations directly to current time.

    Cost depends on active situation count, not elapsed world time.
    """
    if day is None or hour is None:
        now_day, now_hour = _clock()
        day = now_day if day is None else int(day)
        hour = now_hour if hour is None else int(hour)

    registry = _registry()
    situations = copy.deepcopy(dict(registry.db.situations or {}))
    advanced = 0
    for stable_id, raw in list(situations.items()):
        situation = dict(raw)
        if situation.get("state") in {
            "aftermath", "resolved_locally", "dormant_recurrence"
        }:
            continue
        due = (
            int(situation.get("deadline_day") or 10**9),
            int(situation.get("deadline_hour") or 0),
        )
        if (int(day), int(hour)) < due:
            continue

        if stable_id == TITHE_ID and situation.get("branch") == "quietly":
            situation = _finish_quiet(situation)
        elif stable_id == TITHE_ID and not situation.get("branch"):
            situation = _left_alone(situation)
        elif stable_id == TORN_CHRONICLE_ID and not situation.get("branch"):
            situation = _torn_left_alone(situation)
        else:
            continue
        situations[stable_id] = situation
        advanced += 1

    if advanced:
        registry.db.situations = situations
        _metrics(autonomous_advances=advanced)
    surfaced = surface_incident_feed(
        day=int(day),
        hour=int(hour),
        max_active=1,
    )
    return advanced


def situation_status_for_player(player, stable_id=TITHE_ID):
    situation = get_situation(stable_id)
    if not situation:
        return None
    knowledge = _knowledge(situation, player)
    if not knowledge["discovered"]:
        return None
    template = TEMPLATES[stable_id]
    evidence = [
        {
            "id": evidence_id,
            **template["evidence"][evidence_id],
        }
        for evidence_id in knowledge["evidence"]
        if evidence_id in template["evidence"]
    ]
    return {
        "id": stable_id,
        "title": situation["working_title"],
        "state": situation["state"],
        "branch": situation.get("branch"),
        "deadline_day": situation.get("deadline_day"),
        "deadline_hour": situation.get("deadline_hour"),
        "evidence": evidence,
        "developments": list(knowledge["developments"]),
        "aftermath": situation.get("aftermath"),
        "inheritance": template["inheritance"],
        "choices": list(template.get("choices") or {}),
    }


def chronicle_gap_description(looker=None):
    situation = get_situation(TORN_CHRONICLE_ID)
    if not situation or situation.get("state") == "dormant":
        return None
    if looker is not None:
        discover_evidence(looker, "gap", TORN_CHRONICLE_ID)

    branch = situation.get("branch")
    if situation.get("state") == "aftermath":
        if branch == "reconstruct":
            return (
                "The numbered stubs are still visible, but a replacement sequence has "
                "been inserted after them. Every reconstructed page is marked in the "
                "margin: DERIVED FROM HARBINGER FILES. The replacement is press-derived, "
                "not recovered original text; the source difference is not hidden."
            )
        if branch == "preserve":
            return (
                "The numbered stubs remain between blank guard leaves. A note records "
                "that the missing sequence was deliberately left unreconstructed. "
                "Nothing pretends to know what the cut pages said."
            )
        return (
            "The numbered stubs remain under a protective guard sheet. Visitors have "
            "begun asking to see the famous gap, which the Chronicle still refuses to fill."
        )

    return (
        "A numbered run of Chronicle pages is missing. The leaves were cut out cleanly, "
        "not torn; the narrow stubs remain bound in sequence. Their numbers establish "
        "exactly where the absence begins and ends, but the surviving paper does not "
        "tell you what the pages said."
    )


def harbinger_archive_evidence(looker=None):
    situation = get_situation(TORN_CHRONICLE_ID)
    if not situation or situation.get("state") == "dormant":
        return None
    if looker is not None:
        discover_evidence(looker, "harbinger_archive", TORN_CHRONICLE_ID)
    return (
        "Older bound Harbinger files cover the Chronicle's missing dates. They preserve "
        "printable accounts, source language, and later corrections, but they are still "
        "newspaper records rather than the missing Chronicle originals."
    )


def resident_situation_ask(npc, player, topic):
    if getattr(npc.db, "resident_id", None) != "ilona_szabo":
        return None
    lowered = str(topic or "").lower()
    if not any(
        token in lowered
        for token in ("chronicle", "missing page", "missing pages", "gap", "torn")
    ):
        return None
    situation = get_situation(TORN_CHRONICLE_ID)
    if not situation or situation.get("state") == "dormant":
        return None
    discover_evidence(player, "ilona", TORN_CHRONICLE_ID)
    if situation.get("state") == "aftermath":
        if situation.get("branch") == "reconstruct":
            return (
                "We reconstructed it from the Harbinger, and marked every line for "
                "what it is. A copied account is not a recovered page."
            )
        if situation.get("branch") == "preserve":
            return (
                "I left the gap visible. An honest absence is better than a confident "
                "invention wearing archival ink."
            )
        return (
            "The gap has become famous enough to attract visitors. Fame has not made "
            "the missing pages any less missing."
        )
    return (
        "The cut was clean, and the numbering is genuine. The Harbinger files survive, "
        "but I will not call newspaper copy the same thing as the pages we lost."
    )


def decision_message(stable_id, branch):
    if stable_id == TITHE_ID:
        if branch == "openly":
            return (
                "You raise the missing tithe openly. The accusation is now public, "
                "the church changes its strongbox procedure, and the quiet road is closed."
            )
        return (
            "You ask that the inquiry stay quiet for a week. The public accusation road "
            "is closed, and the village clock keeps moving."
        )
    if stable_id == TORN_CHRONICLE_ID:
        if branch == "reconstruct":
            return (
                "You authorize a reconstruction from the Harbinger archive. The replacement "
                "pages are marked as press-derived, and the choice is now part of village history."
            )
        return (
            "You preserve the numbered gap instead of reconstructing it. The absence remains "
            "visible, documented, and shared by every later reader."
        )
    return "The shared situation changes."


def strongbox_description(looker=None):
    situation = get_situation(TITHE_ID)
    if not situation:
        return (
            "A small iron parish strongbox sits under the vestry table, "
            "closed and unremarkable."
        )
    state = situation.get("state")
    branch = situation.get("branch")
    if state == "aftermath":
        if branch == "openly":
            return (
                "The tithe strongbox sits shut beneath the vestry table. Two "
                "different keyholes now govern the lid. The new hardware is "
                "practical; the silence around it is not."
            )
        if branch == "quietly":
            return (
                "The tithe strongbox is shut again. A second lock has been fitted "
                "beside the first, new brass against old iron. Nobody in church "
                "volunteers a name."
            )
        return (
            "The tithe strongbox is shut under two locks now. The roof above it "
            "still wants repair, and the collection plate has grown quieter."
        )

    return (
        "The church tithe strongbox stands open beneath the vestry table and is "
        "much too light. The lock is not forced. Around the ward, fresh oil and "
        "fine key-scratches catch the candlelight. The vestry key itself hangs "
        "on its ordinary hook."
    )


def tithe_roll_description(looker=None):
    situation = get_situation(TITHE_ID)
    if situation and situation.get("state") == "aftermath":
        return (
            "The tithe roll remains in its ruled columns. A later note in another "
            "hand records the new two-key strongbox procedure. The missing sum is "
            "still not crossed out."
        )
    return (
        "The parish tithe roll is ruled in ink and balanced through the previous "
        "evening. Its recorded total is too large to fit the nearly empty box now "
        "sitting open nearby. Whatever is missing was not an accounting error."
    )
