"""DM-Q-0017: Tomorrow's Obituary — Harbinger editorial incident.

A legitimate obituary for a living resident reaches the Harbinger office.
The editor must decide whether to print, investigate, delay, or suppress it.
Different choices create different public beliefs and rival theories.
"""

from __future__ import annotations

from fvillage.world.situations import (
    Situation,
    Evidence,
    Choice,
    Outcome,
)


OBT_ID = "DM-Q-0017-OBTUARY"


class ObituarySituation(Situation):
    """The obituary editorial incident."""

    name = "tomorrow's obituary"
    display_name = "Tomorrow's Obituary"
    quest_id = OBT_ID
    content_family = "rumor"
    canonical_status = "working content"
    spoiler_tier = 2

    primary_location = "Harbinger office"
    secondary_locations = ["Village square", "Church"]
    involved_npcs = [
        "harbinger_editor",
        "printer",
        "witness",
        "rival_detective",
    ]
    calling_relevance = ["chronicler", "detective", "merchant"]
    repeatability = "one-shot"

    hook = (
        "A typed obituary sits on the editorial desk, signed by a grieving family "
        "for a resident who is still walking through the square. The copy appears "
        "legitimate: correct spelling, proper format, matching handwriting with "
        "previous submissions. But its source is unclear."
    )

    autonomy = {
        "initial_deadline_hours": 12,  # Publication deadline
        "left_alone": (
            "The printer schedules the obituary for tomorrow's edition. "
            "Village rumors spread. A rival investigator publishes a competing theory."
        ),
    }

    choices = {
        "editor_decision": {
            "label": "Editorial decision",
            "branch_from": "initial",
            "options": [
                Choice(
                    "Publish as submitted",
                    outcome=Outcome(
                        name="published",
                        narrative=(
                            "The obituary appears in tomorrow's edition with no "
                            "note of discrepancy. The editor's authority is preserved, "
                            "but the error becomes canonized in public memory."
                        ),
                        evidence=[
                            Evidence(
                                "printed_obituary",
                                "documentary",
                                "The published article, signed by the editor.",
                            ),
                            Evidence(
                                "rival_theory",
                                "rumor",
                                "A competing account published by the rival investigator.",
                            ),
                        ],
                        persistent_state=(
                            "Public belief that the deceased died; Harbinger "
                            "credibility permanently altered; editor may face "
                            "accountability from the board."
                        ),
                    ),
                ),
                Choice(
                    "Delay and investigate",
                    outcome=Outcome(
                        name="investigated",
                        narrative=(
                            "The printer holds the plates. The editor requests "
                            "witnesses and source verification. By deadline, "
                            "some evidence supports the obituary's claim, "
                            "others contradict it. The article is published "
                            "with a brief editorial note."
                        ),
                        evidence=[
                            Evidence(
                                "editorial_note",
                                "documentary",
                                "The published article with verification notes.",
                            ),
                            Evidence(
                                "witness_testimony",
                                "witness",
                                "Conflicting accounts from people who claimed to know the deceased.",
                            ),
                        ],
                        persistent_state=(
                            "The village learns how to verify claims; the editor "
                            "gains credibility for caution; the obituary author "
                            "may be identified and confronted."
                        ),
                    ),
                ),
                Choice(
                    "Suppress without explanation",
                    outcome=Outcome(
                        name="suppressed",
                        narrative=(
                            "The printer withdraws the obituary at the last minute. "
                            "No explanation is given. The story becomes a rumor "
                            "about a 'mistake' or a 'censored tale'."
                        ),
                        evidence=[
                            Evidence(
                                "suppressed_draft",
                                "documentary",
                                "The withdrawn copy, now unavailable in any official edition.",
                            ),
                            Evidence(
                                "rumor_of_censorship",
                                "rumor",
                                "Whispers that the story was too dangerous to print.",
                            ),
                        ],
                        persistent_state=(
                            "The obituary author may feel betrayed; the editor "
                            "loses credibility with readers who value transparency; "
                            "a faction suspects the story contained a warning."
                        ),
                    ),
                ),
            ],
        },
    }

    evidence = {
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
    }

    npc_beliefs = {
        "harbinger_editor": {
            "initial": (
                "The editor believes the obituary is legitimate but feels "
                "obliged to verify because of the board directive. They are "
                "conflicted between journalistic duty and institutional caution."
            ),
            "after_publish": (
                "The editor defends their decision, claiming they 'trusted the "
                "source and the format.' They may avoid future editorial notes "
                "to preserve authority."
            ),
            "after_suppress": (
                "The editor claims the story was 'too controversial,' but "
                "the editorial board may question whether that is a valid "
                "justification for suppressing a legitimate article."
            ),
        },
        "printer": {
            "initial": "The printer believes the obituary is routine content. They follow the editor's decision without question.",
            "after_publish": "The printer notes the obituary ran smoothly, with no technical issues. They may be asked to repeat the run.",
            "after_suppress": "The printer is left with idle plates and unused ink. They may suggest that 'a story that big doesn't just disappear.'",
        },
        "witness": {
            "initial": "The witness believes they saw the deceased clearly and is frustrated that the obituary may have been premature.",
            "after_publish": "The witness feels vindicated but uncomfortable, because the obituary may have been written by someone who knew them.",
            "after_suppress": "The witness speculates that the story contained something 'too sensitive' for publication.",
        },
        "rival_detective": {
            "initial": "The detective believes the obituary is part of a pattern of false death notices used to manipulate public opinion.",
            "after_publish": "The detective publishes a theory that the deceased was actually alive and used the obituary to create an alibi.",
            "after_suppress": "The detective claims the suppression proves the story contained 'something dangerous,' increasing public suspicion.",
        },
    }

    rumors = [
        "The obituary was submitted by a foreign correspondent.",
        "The deceased was actually a member of the Hounds.",
        "The editor is using the obituary to test the printing schedule.",
        "The obituary author is still alive and will appear at the next council meeting.",
    ]

    harbinger_consequences = [
        "The story may be republished as a correction or as a 'story of the week.'",
        "The editorial board may issue a statement on verifying obituary sources.",
        "The obituary may appear in the Chronicle as a notable error or cautionary tale.",
    ]

    chronicle_eligibility = {
        "primary": "A published false obituary in the Harbinger",
        "secondary": "The editor's response to the incident",
    }

    follow_up = {
        "immediate": "Investigation of the obituary's source and the deceased's whereabouts.",
        "medium": "Publication of a correction or editorial note explaining the incident.",
        "long_term": "Debate over the ethics of publishing death notices without verification.",
    }

    aftermath = {
        "world_state": "Public belief about the deceased is altered; rumors about the editor's credibility spread.",
        "npc_effects": "The rival detective gains followers; the editor may become more cautious or more defensive.",
        "evidence_state": "The obituary copy may be archived, destroyed, or repurposed as evidence in a future case.",
    }