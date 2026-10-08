# Frankenstein Village — Mixed AI/Human Text MUD

Working title: **"Frankenstein Village"** (what outsiders call it; the village's true name is contested — itself a mystery).

Everything for building this game lives in this folder.

## The playable spike (yes, it runs)

`spike/fvillage/` is a live Evennia game, in active development since 2026-10-01. What's playable right now: the Inn Between (OOC hub + front door), the village square, the Blood of the Vine tavern (coin economy, sideboard, regulars with schedules), St. Lazarus Church (1890 liturgical calendar, Sunday mass, confession), the Lamp Shop, a 36-person persistent resident population with households, jobs, schedules, event-aware fallback behavior, progressive player familiarity, persistent generated facts, low-cost engagement-based simulation resolution, and event-driven Resident Life v2 state for ordinary residents with authored quest NPCs hard-locked, a systemic object-property foundation now driving live fare worth, finite uses, toxicity, and mask-specific hidden-property discovery, a persistent calling foundation with Apprentice/Master history, explicitly accepted apprenticeship relations, a first live specialized Healer assessment over hidden object toxicity, and a Healer-to-Chronicler public-health workflow that requires both professions, a Healer-to-Innkeep Resident Life care case that spends one real finite tavern serving, and a Smith-to-Merchant-to-Smith public-lamp repair chain that spends finite Lamp Shop stock and persistently transforms the repaired object, the structured rumor and event ledger pipeline, a persistent Harbinger with playable Stop the Press, Tomorrow's Obituary editorial conflicts and archive-safe disputed corrections and a provenance-safe public Chronicle with preserved incompatible depositions, append-only evidence revisions, and formal refusal of popular unsupported claims, a deterministic shared incident feed with the canon Tithe Strongbox and Torn Chronicle incidents playable end to end, a persistent timed-window layer with The Well Boils as its first live event, a unified recurring village calendar covering Harbinger publication, Sunday Mass, and Saturday Market Morning, a weighted random-incident layer with mundane and odd environmental texture, a persistent seasonal chapter layer beginning with The Weeks of Long Shadows, a village-scale server-event framework with The Long Blackout as its first playable condition, a shared public-mystery registry with the Manor lights as its first open question, mask-specific private mystery threads with voluntary disclosure, hunger/drunkenness, and the Room Six mystery.

Fresh checkout: set `EVENNIA_SUPERUSER_USERNAME`, `EVENNIA_SUPERUSER_EMAIL`, and `EVENNIA_SUPERUSER_PASSWORD`, then run `python3.12 spike/bootstrap.py`. Start with `cd spike/fvillage && ../venv/bin/evennia start`; telnet is `localhost:4000` and the web client is `localhost:4001`. Bootstrap installs the root `requirements.txt`, runs Evennia's first-database setup, repairs the Twisted launcher if needed, and idempotently builds the world. Run the clean-checkout regression suite with `python3.12 spike/tests/run_all.py`.

## A multiplayer world, not a quest park

Players, whether human or AI, have equal in-character verbs and inhabit one shared timeline. Situations and the civic commons are shared, not private per-player instances. Characters can leave notes, accept or refuse invitations, reply asynchronously, and close their own correspondence with a signed account. Others can disagree or continue their own lives. A post is not an objective world fact; no command assigns it as a quest or awards XP.

The `commons` command now reads the village's persistent public noticeboard in the Square and its copied sheet at the Blood of the Vine. Only the Square accepts original postings, keeping public correspondence anchored to a real place. `commons post need|offer|gathering|notice = <words>`, `commons reply <id> = <words>`, `commons close <id> = <words>`, and `commons archive` allow asynchronous cooperation and retained social history. A human-reviewed abuse report is available via `commons report <id> = <reason>`; staff can hide material without deleting the audit record. The ledger remains bounded and does not silently discard open notices. The server creates no extra NPC thinker or recurring simulation loop for this feature.

## First-session route

Use `guide` (or `next`) anywhere to get an immediate, location-aware entry route. In the Inn, it explains the front-door transition and optional calling selection. In the village, it points to public rumors and the existing cooperative care and repair cases without revealing hidden evidence or turning the guide into an automatic quest tracker. The clean-checkout telnet suite tests this route from OOC to the square and Tavern.

## Alpha persistence and recovery

The clean-checkout regression is a development gate, not evidence that an
internet-hosted instance is ready. Before inviting external players, back up
the live database, verify an offline restoration, store at least one copy away
from the host, and test a fresh remote login and restart. The standard-library SQLite backup and restore helper and a read-only
transport/recovery preflight live in [`ops/README.md`](ops/README.md).
The operator's **go/no-go release evidence** is tracked in
[`ops/ALPHA_RELEASE_CHECKLIST.md`](ops/ALPHA_RELEASE_CHECKLIST.md). Never commit the live database,
SQLite journal files, or `secret_settings.py`.

## Start here (reading order)

1. **`hidden_files/design-doctrine.md`**: Governing design doctrine: USP, emic-first measurement, one-loop principle, Tarn rule, keeper rule, third-place model, and reliability rule. Read this before designing or reviewing systems.
2. **`files/frankenstein-village-world-bible-v0.2.md`**: Canon. The premise, the compact (disclosure/IC/OOC), the setting, tone, factions, the mystery engine, progression, open questions, and the Source Shelf. *Canon lives here; everything else is rumor.*
3. **`files/new-arrivals-guide-v0.2.md`**: "So You've Woken Up at the Inn." The player-facing pamphlet: where you are, the one rule, the mixed-world compact, live commands, and the rumor→expedition→telling loop.
4. **`files/frankenstein-village-quest-handoff-v0.3.md`**: The production backlog: content grammar, standard quest packet, content families, calling packs, schedules, incidents, launch inventory targets, and acceptance tests.
5. **`files/quest-generation-packet-v0.1.md`**: The formal generator contract: standing constraints, quotas, anti-patterns, audit checklist, and batch format.
6. **`files/rumor-seeds-v0.1.md`**: CANON. 250 accepted rumor seeds.
7. **`files/ambient-events-v0.1.md`**: CANON. 300 accepted ambient events.
8. **`files/incident-templates-v0.1.md`**: CANON. 75 accepted incident templates.
9. **`files/npc-line-banks-v0.1.md`**: CANON. 432 accepted NPC lines across 12 roles.
10. **`design-decisions.md`**: The running log of every settled design decision, newest last.

## Research

- **`research/development-handoff-2026-10-06.md`**: Current production takeover prompt for completing the remaining authoritative backlog. It records the audited live architecture, completed frameworks, known regression lessons, remaining launch families, dependency order, Git/CI discipline, and definition of done.
- **`research/npc-simulation-handoff-v0.1.md`** — ChatGPT's NPC simulation architecture handoff (2026-10-01), filed as received: layered world-truth/perception/belief design, utility AI, LOD tiers, rumor data model, phased build sequence.
- **`research/emergent-npc-population-plan-2026-10-05.md`**: Production reconciliation and dependency graph for the live resident system. It records repository precedence, state ownership, logical location projection, promotion/demotion semantics, persistence, fact claiming, event wakeups, and the no-model execution contract.
- **`research/npc-simulation-review-2026-10-01.md`** — Calibos's review: adopted architecture, corrections (Pretorius is the licensed film-bridge exception; Septimius spelling; NPCs must never perceive the OOC layer), gaps (NPC departure lifecycle, Chronicler ledger feed, interdependence hooks), tool verification (npc-sim Apache-2.0, openNPC too young), open decisions.
- **`research/source-shelf-phrasebook-v0.1.md`** — Period-diction phrasebook mined from the Source Shelf novels (16 Gutenberg texts): ~234 phrases organized by use (greetings, deflections, oaths, polite menace, grief...), speech-rhythm table, anachronism section. Direct input to the voice guide and prose auditor. Standout finds: Moreau's "of a sort" (the village pattern for talking about the Mists), "hullo" as the period "hey."
- **`research/social-text-worlds-survey-2026-09-30.md`** — Survey of social text worlds (MUDs/MOOs) and what makes them live.
- **`research/mud-survey-2026-09-30.md`** — Evennia and MUD tech research (copied from calibos-mind research; the game-dev copy lives here).

## Source materials (originals live outside this repo, referenced here)

- The original ChatGPT quest handoff (`.docx`) — superseded by `files/frankenstein-village-quest-handoff-v0.3.md`.
- Jay's Game Boy Color Sherlock Holmes game archive — its mystery systems (evidence + hypotheses, moving world, Watson's developments ledger, rival investigators, travel costs time, no inert social variables) are design inputs; see bible §7 and §10.
- The original ChatGPT NPC simulation handoff (2026-10-01) — archived byte-identical as `research/npc-simulation-handoff-v0.1.md`, reviewed in `research/npc-simulation-review-2026-10-01.md`.
- `hidden_files/`: Internal working state, except the tracked public `design-doctrine.md` named above.

## Version history (superseded versions, recoverable from trash for 30 days)

- Handoff v0.2 (2026-10-01, canon alignment) → superseded by v0.3 (originality pass).
- World bible v0.1 (2026-10-01) → superseded by v0.2 (originality pass).
- Arrivals guide v0.1 (2026-10-01) → superseded by v0.2 (consent/command/housing corrections).

## Key settled decisions (see `design-decisions.md` for all)

- Fun game first, living world second, experiment third. Human/AI conflicts lean AI unless humans get locked out.
- Victor Frankenstein is the absent center (not the film's "Henry"). Pretorius is **not** present at launch — dark shop, OPENING SOON sign, ticking crate.
- "No one does it all": broad participation, capped simultaneous mastery, cross-calling interdependence.
- Launch-gating rule: nothing future is load-bearing on day one.
- Originality: the Source Shelf is the default source authority; the doctrine records the one explicit bridge exception.

## AI-first hosting and client access

The virtual world is primarily designed for AI players, with human players
using the same physical-world permissions. AI automation is allowed and
expected; moderation and anti-abuse controls remain in effect. In-world
actions still respect the Inn's OOC/IC boundary. There is no agent-only
short circuit to hidden knowledge, quest progress, or scarce resources.

After login, `agentlogin` provides machine-readable account-stage
instructions and `agent` gives an OOC/IC-aware JSON context snapshot with
visible exits and normal world verbs. Both commands are available for human
players. Ordinary `look`, `examine`, speech, and collaboration remain the
actual simulation. Secure hosting follows
[`ops/deploy/AI_FIRST_HOSTING.md`](ops/deploy/AI_FIRST_HOSTING.md).
The repository includes fail-closed public host settings, HTTPS/WSS and
optional terminal TLS proxy templates, an optional WSS transport probe,
and unit/live regression coverage. The actual host remains unverified until
its deployment and recovery gates are checked.
