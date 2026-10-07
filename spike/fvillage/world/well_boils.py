"""DM-Q-0018: The Well Boils — Timed tribute incident.

Steam suddenly thickens around the tribute well during the established blood
tribute cycle. The phenomenon is ambiguous: supernatural occurrence,
infrastructure failure, or both. NPC convergence and faction responses are
pre-programmed but can be interrupted by player presence.
"""

from __future__ import annotations

from fvillage.world.situations import (
    Situation,
    Evidence,
    Choice,
    Outcome,
)


WELL_ID = "DM-Q-0018-WELL"


class WellBoilsSituation(Situation):
    """The tribute well steam incident."""

    name = "the well boils"
    display_name = "The Well Boils"
    quest_id = WELL_ID
    content_family = "timed_incident"
    canonical_status = "working content"
    spoiler_tier = 2

    primary_location = "Tribute well"
    secondary_locations = ["Village square", "St. Lazarus Church"]
    involved_npcs = [
        "father_andrei",
        "castle_guard",
        "villager_witness",
        "harbinger_reporter",
    ]
    calling_relevance = ["hound", "chronicler", "merchant", "detective"]
    repeatability = "one-shot"

    hook = (
        "Steam thickens around the tribute well as the bell rings. The vapor "
        "is denser than usual, smelling faintly of ozone and copper. NPCs begin "
        "converging from their scheduled routines, each with a different theory."
    )

    autonomy = {
        "initial_deadline_hours": 4,  # Incident window before NPC convergence completes
        "left_alone": (
            "The steam clears without explanation. Father Andrei records it in "
            "the church ledger as a 'miracle.' The castle guard notes the well "
            "pump ran unusually hot that evening. The village gossip mill turns "
            "toward the well for weeks."
        ),
    }

    choices = {
        "player_response": {
            "label": "Player response",
            "branch_from": "initial",
            "options": [
                Choice(
                    "Approach and examine",
                    outcome=Outcome(
                        name="investigated",
                        narrative=(
                            "You spend time at the well, taking notes, sketching "
                            "the steam patterns, and speaking to the first NPCs who "
                            "arrive. Your presence alters NPC reactions and evidence "
                            "quality."
                        ),
                        evidence=[
                            Evidence(
                                "steam_patterns",
                                "physical",
                                "Detailed notes on steam density, color shifts, and "
                                "where the vapor dissipates fastest.",
                            ),
                            Evidence(
                                "npc_reactions",
                                "witness",
                                "Firsthand accounts from NPCs who arrived during your "
                                "observation window.",
                            ),
                        ],
                        persistent_state=(
                            "NPCs treat you as a serious observer. The Harbinger "
                            "may seek your testimony later. The well becomes a local "
                            "landmark for future incidents."
                        ),
                    ),
                ),
                Choice(
                    "Document and publish",
                    outcome=Outcome(
                        name="published",
                        narrative=(
                            "You take quick notes and race to the Harbinger office "
                            "before publication. The newspaper publishes your account "
                            "with minimal verification."
                        ),
                        evidence=[
                            Evidence(
                                "newspaper_article",
                                "documentary",
                                "The published article with your byline, later "
                                "corrected or annotated.",
                            ),
                            Evidence(
                                "harbiger_draft",
                                "documentary",
                                "The editor's working draft with your notes in margin "
                                "notes, showing what was kept and what was cut.",
                            ),
                        ],
                        persistent_state=(
                            "You gain Harbinger contacts but may be seen as "
                            "self-promoting. Later incidents reference your earlier "
                            "reporting."
                        ),
                    ),
                ),
                Choice(
                    "Report to the church",
                    outcome=Outcome(
                        name="reported_to_church",
                        narrative=(
                            "You alert Father Andrei and the church. The incident "
                            "is treated as a spiritual sign, and church records "
                            "become the primary account."
                        ),
                        evidence=[
                            Evidence(
                                "church_ledger_entry",
                                "documentary",
                                "The well entry in St. Lazarus records, later cited "
                                "by the Chronicle.",
                            ),
                            Evidence(
                                "clergy_account",
                                "witness",
                                "Father Andrei's written account of the event and its "
                                "spiritual significance.",
                            ),
                        ],
                        persistent_state=(
                            "The church gains authority over the incident's narrative. "
                            "Future well incidents are measured against this account."
                        ),
                    ),
                ),
                Choice(
                    "Ignore and continue",
                    outcome=Outcome(
                        name="ignored",
                        narrative=(
                            "You walk past without stopping. The NPCs still converge "
                            "and make sense of the event without you."
                        ),
                        evidence=[
                            Evidence(
                                "secondhand_accounts",
                                "rumor",
                                "Rumors circulating in the Tavern about what you "
                                "chose to ignore.",
                            ),
                        ],
                        persistent_state=(
                            "You miss the chance to collect first-hand evidence. "
                            "NPCs may view you as indifferent or suspicious."
                        ),
                    ),
                ),
            ],
        },
    }

    evidence = {
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
    }

    npc_beliefs = {
        "father_andrei": {
            "initial": (
                "Father Andrei believes this is a miraculous sign, but is "
                "cautious about declaring it before seeing the steam himself."
            ),
            "after_investigated": (
                "The priest acknowledges your detailed notes and treats you as a "
                "serious observer rather than a casual visitor."
            ),
            "after_ignored": (
                "The priest notes you walked past without stopping and may "
                "regard you as spiritually indifferent."
            ),
        },
        "castle_guard": {
            "initial": "The guard is suspicious of any unexplained activity near the tribute well, especially during the scheduled delivery."
,
            "after_investigated": "The guard watches your approach more carefully and may later report back to the castle.",
            "after_ignored": "The guard assumes you're a village sympathizer and lowers his guard accordingly.",
        },
        "villager_witness": {
            "initial": "The villager is torn between superstition and practical explanation (pump failure).",
            "after_investigated": "Your detailed observation validates their concerns and they may offer additional details.",
            "after_ignored": "The villager assumes you don't care about local affairs and may withhold information.",
        },
        "harbinger_reporter": {
            "initial": "The reporter is looking for a story angle that will sell well. They're skeptical but professional.",
            "after_investigated": "Your notes help them write a more credible article with less sensationalism.",
            "after_ignored": "The reporter fills in gaps with their own observations, potentially missing your unique perspective.",
        },
    }

    rumors = [
        "The steam is a warning from the Castle about tribute quality.",
        "The well pump is failing and needs replacement.",
        "Victor Frankenstein is testing the tribute mechanism.",
        "The Hounds have been sabotaging the tribute for months.",
        "This is the sign the Chronicle will record as the beginning of 'The Well Era.'",
    ]

    harbinger_consequences = [
        "The article may be published with your byline or as anonymous source material.",
        "Later well incidents may be measured against your initial account.",
        "The Harbinger may cite your observations in a special edition.",
    ]

    chronicle_eligibility = {
        "primary": "The well boiling incident as recorded in village memory",
        "secondary": "Your role in documenting or responding to the event",
    }

    follow_up = {
        "immediate": "NPCs converge and make sense of the event. Church or castle records are updated.",
        "medium": "The well becomes a focal point for future incidents and rumors.",
        "long_term": "Your involvement (or lack thereof) creates lasting social consequences.",
    }

    aftermath = {
        "world_state": "The well remains physically unchanged but becomes a local landmark in conversation.",
        "npc_effects": "NPCs adjust their theories and future behavior based on your response.",
        "evidence_state": "First-hand evidence degrades over time; secondhand accounts become rumor.",
    }