# Frankenstein Village — Mixed AI/Human Text MUD

Working title: **"Frankenstein Village"** (what outsiders call it; the village's true name is contested — itself a mystery).

Everything for building this game lives in this folder.

## Start here (reading order)

1. **`files/frankenstein-village-world-bible-v0.2.md`** — Canon. The premise, the compact (disclosure/IC/OOC), the setting, tone, factions, the mystery engine, progression, open questions, and the Source Shelf (the 13 public-domain novels all generated content must draw from). *Canon lives here; everything else is rumor.*
2. **`files/new-arrivals-guide-v0.2.md`** — "So You've Woken Up at the Inn." The player-facing pamphlet: where you are, the one rule (the front door), the mixed-world compact, commands (launch vs. coming-soon clearly split), the rumor→expedition→telling loop. v0.2 corrects v0.1: consent at the gate (not the door), no overpromised housing/commands, "no markers" without the "no tells" overpromise. The mechanics half of the generation packet (bible = canon half).
3. **`files/frankenstein-village-quest-handoff-v0.3.md`** — The production backlog: content grammar, the standard quest packet, 35 quest/activity families, calling packs, NPC schedules, ambient events, incidents, rumors, discoveries, launch inventory targets, and acceptance tests. Working content until promoted into the bible.
4. **`files/quest-generation-packet-v0.1.md`** — The formal generator contract: standing constraints (originality, tone, quest grammar, interdependence, object tags, NPC/mortality rules), six content families with quotas, anti-patterns, audit checklist, batch output format. Feed one family per run to a generator (ChatGPT or otherwise); audit every batch before canon.
5. **`files/rumor-seeds-v0.1.md`** — CANON. 250 rumor seeds (family 1), each with provenance hook, 2–3 distortion variants, and §10 audit line. Accepted 2026-10-01 after auditor review: no premature finales, no load-bearing NPCs, Pretorius excluded per launch staging.
6. **`files/ambient-events-v0.1.md`** — CANON. 300 ambient events (family 2): plain observations, no mechanics, witness counts ≤8. Accepted 2026-10-02 after auditor review. Deliberately echoes family-1 rumors without restating them — events are what rumors are *about*.
7. **`files/incident-templates-v0.1.md`** — CANON. 75 incident templates (family 3) across 23 types: skeleton + 3+ variant slots + consequence branch + inheritance line. Accepted 2026-10-02 after auditor review. Positioned as what happens when family-1 rumors get investigated.
8. **`files/npc-line-banks-v0.1.md`** — CANON. 432 NPC lines (family 4) across 12 roles: greetings, work talk, weather talk, deflections, person-mode. Opens with the VOICE GUIDE. Accepted 2026-10-02 after auditor review. Role-titled speakers, never named individuals.
9. **`design-decisions.md`** — The running log of every settled design decision, newest last.
4. **`design-decisions.md`** — The running log of every settled design decision, newest last.

## Research

- **`research/npc-simulation-handoff-v0.1.md`** — ChatGPT's NPC simulation architecture handoff (2026-10-01), filed as received: layered world-truth/perception/belief design, utility AI, LOD tiers, rumor data model, phased build sequence.
- **`research/npc-simulation-review-2026-10-01.md`** — Calibos's review: adopted architecture, corrections (Pretorius is the licensed film-bridge exception; Septimius spelling; NPCs must never perceive the OOC layer), gaps (NPC departure lifecycle, Chronicler ledger feed, interdependence hooks), tool verification (npc-sim Apache-2.0, openNPC too young), open decisions.
- **`research/source-shelf-phrasebook-v0.1.md`** — Period-diction phrasebook mined from the Source Shelf novels (16 Gutenberg texts): ~234 phrases organized by use (greetings, deflections, oaths, polite menace, grief...), speech-rhythm table, anachronism section. Direct input to the voice guide and prose auditor. Standout finds: Moreau's "of a sort" (the village pattern for talking about the Mists), "hullo" as the period "hey."
- **`research/social-text-worlds-survey-2026-09-30.md`** — Survey of social text worlds (MUDs/MOOs) and what makes them live.
- **`research/mud-survey-2026-09-30.md`** — Evennia and MUD tech research (copied from calibos-mind research; the game-dev copy lives here).

## Source materials (kept where they are, referenced here)

- `~/workspace/user/files/Darkmoor_Quest_Handoff.docx` — Original ChatGPT handoff document; superseded by `files/frankenstein-village-quest-handoff-v0.3.md`.
- `~/workspace/user/files/ready_detective_one/` — Jay's Game Boy Color Sherlock Holmes game archive. Its mystery systems (evidence + hypotheses, moving world, Watson's developments ledger, rival investigators, travel costs time, no inert social variables) are design inputs — see bible §7 and §10.
- `~/workspace/user/files/Frankenstein_Village_NPC_Simulation_Handoff_v0.1.txt` — Original ChatGPT NPC simulation handoff (2026-10-01); archived byte-identical as `research/npc-simulation-handoff-v0.1.md`, reviewed in `research/npc-simulation-review-2026-10-01.md`.
- `~/workspace/goals/mixed-ai-human-text-mud/hidden_files/` — Internal working state, not player-facing.

## Version history (superseded versions, recoverable from trash for 30 days)

- Handoff v0.2 (2026-10-01, canon alignment) → superseded by v0.3 (originality pass).
- World bible v0.1 (2026-10-01) → superseded by v0.2 (originality pass).
- Arrivals guide v0.1 (2026-10-01) → superseded by v0.2 (consent/command/housing corrections).

## Key settled decisions (see `design-decisions.md` for all)

- Fun game first, living world second, experiment third. Human/AI conflicts lean AI unless humans get locked out.
- Victor Frankenstein is the absent center (not the film's "Henry"). Pretorius is **not** present at launch — dark shop, OPENING SOON sign, ticking crate.
- "No one does it all": broad participation, capped simultaneous mastery, cross-calling interdependence.
- Launch-gating rule: nothing future is load-bearing on day one.
- Originality: all content re-grounded in the Source Shelf novels; no Universal/Ravenloft/film-quote material.
