# Frankenstein Village: Program-First Roadmap to a Hostable Early-Access Alpha

Status: PROPOSED development plan, not a claim that the target features are implemented.
Date: 2026-10-19
Baseline: main b2088294c76961846acfdee3281f8d40c80ffdcd, passed GitHub Actions run 39189556568.
Priority: Finish the normal text-game code and local verification first. Select and pay for hosting only after the code-ready gate is met. No language model, local inference server, Ollama instance, API key, GPU, or agent framework is required to build, play, test or launch Frankenstein Village.

**Integration reconciliation (2026-10-26):** This is a subordinate proposed **early-access planning roadmap**, not the controlling game-completion standard. The World Bible v0.2 and design doctrine govern canon; the merged Master GDD completion program (`ops/MASTER_GDD_GAME_COMPLETION_PROGRAM_2026-10-25.json`, PR #95) governs FV-G00–FV-G13 and full-game acceptance. PR #89 proposes the model-free product/release contract; until reviewed and integrated, it is not a main-branch authority. The 16–20-room and two-activity early-access targets below do **not** satisfy the Master GDD's larger full-game content quotas. AI-led client testing is optional research and must never block normal-player alpha or release. No PR merge, deployment, or package certification is asserted by this note.

## Decision and product definition

Build a substantial, persistent, Victorian Gothic village MUD with a cozy everyday rhythm, interdependent occupations, a changing population, three consequential mysteries, occasional authentic supernatural phenomena, and meaningful human/AI social play. A person may happily cook, perform, research, trade, or investigate without being forced into a horror quest.

This is an EARLY-ACCESS ALPHA scope with aspirations above a technical alpha. It is NOT a quiet redefinition of the much larger full-launch quotas in files/frankenstein-village-quest-handoff-v0.3.md section 7. An alpha can be code-ready before host selection; a public launch cannot be certified without actual external safety and recovery evidence.

The specific product question is: Can a player enter without developer knowledge, find a satisfying profession or investigation, affect shared world state, leave, and resume with new opportunities? Each programmed system must make that answer more likely. Avoid expanding source banks or adding framework layers if the player cannot experience their effect.

## Ground rules and canonical dependencies

- Canon and tone: files/frankenstein-village-world-bible-v0.2.md and hidden_files/design-doctrine.md. Lore claims remain distinct from world truth. Mystery evidence should admit different interpretations.
- Ten professions: docs/TEN_CALLINGS_LIVING_VILLAGE_V1.md and ops/CALLINGS_SIMULATION_DEPTH_PLAN.md. Four specialties per profession remain the longer-term progression architecture, not ten times four compulsory first-release subsystems.
- Interdependence: shared work and real custody, not artificial role locks that strand solo players. NPC baseline services or timed recovery prevent dead ends.
- Persistence: Evennia remains world authority. Reuse the existing village clock, signed event ledger, object-property system, situation registry, resident simulation, Commons, Chronicle/Harbinger, and finite stock systems. Do not introduce a competing scheduler, parallel economy, an LLM-owned source of physical truth, or a mandatory agent-only route.
- AI and human accounts have the same in-world permissions, privacy, tools, time and resource rules. An agent-facing summary may explain visible commands, never reveal hidden facts.
- All player needs must have world-verifiable relief. No lethal hunger or unfulfillable drives merely for atmosphere.
- Work on one production topic branch at a time. Complete INSPECT -> DESIGN -> IMPLEMENT -> UNIT TEST -> LIVE TELNET -> MULTIACCOUNT -> REAL RESTART -> NEGATIVE CASES -> REVIEW -> MERGE -> VERIFY MAIN. A green pull-request CI is not automatically a green merge commit.
- Do not run fixture playthroughs on a populated server. Preserve private masks, records and databases. Never commit credentials or live user data.

## Existing implementation to preserve

At the audited baseline, the game has 10 walkable in-character rooms plus 2 OOC rooms, 38 authored resident definitions, 10 Calling identities, persistent scheduling and events, a Commons, a real finite hearth/soup/civic economy, a bridge-plaque investigation with persistent alternatives, a rare churchyard Mystic event, player journals/agendas, source-linked publications, and NPC reaction mechanisms.

The static sources include 14 random incident definitions, 1 timed incident and 1 server-wide event framework. The 250 canonical rumor-seed manuscript entries are not 250 initially playable rumors. Existing game and agent tests are substantial: the main branch's full clean-checkout regression passed on the audited SHA. None of this verifies release-host safety or long-term player enjoyment.

Historical note: PR #78 proposed model-led agent NPC interaction; its current disposition must be checked against main before reuse. It cannot be a model-free release dependency. PR #47 documents a future Pretorius laboratory integration and should remain out of this release scope. Issue #35 tracks the separate hosting and release evidence.

## Concrete code-ready targets

| Area | Early-access code-ready acceptance | Full-launch contract remains |
| --- | --- | --- |
| World | 16 to 20 meaningful, connected in-character rooms; every new room has a reason to visit and a returning-state variant | Larger geographically and narratively complete world |
| Callings | All 10 have at least 2 distinct renewable activities each, with physical sources, meaningful choice, persisted effects and no permanent solo dead end | 6 authored quests and 8 to 12 repeatable jobs per Calling; fuller specialty systems |
| Career continuity | Active Calling, apprenticeship, visible work history and at least one demonstrable earned improvement or permission tied to work | Four specialty paths per Calling and richer institutional advancement |
| Work economy | Shared stations, finite supplies, procurement, service requests, handoffs, material provenance, optional solo NPC fallback | Deeper multi-enterprise production and economy |
| Investigations | 3 substantial playable mysteries, each with multiple evidence paths and 2 or more persistent outcome or response variants | 30 small and 10 to 12 major mysteries |
| Incidents | About 30 active random definitions, 4 to 6 timed incidents, 2 to 3 distinct server-wide frameworks, with tested effects | 75+ random, 30 timed and 10 server-wide frameworks |
| Population | Existing residents continue schedules, recurring needs and grounded recognition; selected NPCs sustain follow-ups | Extensive major-NPC arcs and faction repertoires |
| Identity/return | In-world consequences, player work history, Commons follow-up, inventory and personal intentions survive true restart | Long-term retention and richer biographies |
| Mixed play | Standard human command path and safe AI context, cooperative and competing accounts, no privileged bypass | Deeper autonomous agent ecosystems |
| Offline quality | Full clean-checkout CI, local simultaneous-client endurance, negative cases, database rollback rehearsal, scripts for every release path | Actual external host and human-operator certification later |

Quantities here are development planning targets, not documented implementation counts or a declaration of full commercial release. Quality and reachable actions take precedence over inflating definition counts.

## Ordered implementation sequence

### 0. Freeze a trustworthy baseline and retire competing planning threads

Dependency: none. Read the latest main SHA and green Actions run. Generate ops/content_inventory.py JSON and Markdown inventory at that SHA and record gaps separately for source definition, wired bootstrap, player discoverability, actual world mutation, and restart evidence. Compare open PR #78 to main and determine whether its safe visible-NPC information has already been superseded; merge after a fresh green regression or close with an explicit disposition. Leave the portable Pretorius lab design deferred.

Deliverable: single baseline SHA, reproducible inventory, one launch roadmap, one active production branch, and no unverified completion claims.
Done when: the inventory can be regenerated, unresolved PR conflicts are recorded, and the fresh main CI status is linked.

### 1. Complete the first-session and return-session player path

Inspect ordinary account creation, mixed-player compact, mask selection, front door, guide, calling list/work, room clues, Commons, journal, agenda, and browser interface. Ensure the player can find at least three accessible opportunities without consulting developer documentation. Every Calling starts with a genuine in-world contact and a real workplace lead, not a dead command. Returning masks receive current context, not a canned one-shot introduction. Keep M. and the Inn Between distinct from the village.

Deliverable: cohesive first 30 to 60 minute experience for a solo newcomer, plus a reconnection path after another player changes something.
Done when: ordinary web and telnet command transcripts prove a new account can enter, choose a Calling, complete a real action, retain the result after restart, and find another available action after the first closes. A human-facing help prompt and an agent-facing prompt must describe the same permitted options.

### 2. Finish one small shared-work architecture, not a quest mega-framework

Extend the already-live civic commission, Commons, finite resources, event ledger and work participation to support source-based requests, physical delivery or service, a named recipient, optional handoff, due/expiry state, and recorded outcome. Worksites expose stock, work in progress and a next available task. A request is not fulfilled merely by posting or describing it. A lone player can make progress where a profession would otherwise require someone offline, using explicit NPC baseline supply/service or time-bound completion.

Deliverable: reusable modest workplace/commission contract with two differently skinned examples, such as Tavern hospitality and Market Lane repair supply.
Done when: different accounts can create/accept/contribute, spend exact materials once, disconnect/reconnect, observe another person's action, and see success, delay, shortage and cancellation without dupes or invented rewards.

### 3. Expand the village only where gameplay lives

Grow from 10 to roughly 16 to 20 practical in-character locations by adding productive interiors or adjacent districts, not a decorative empty map. Prioritize a forge/workbench, healer or apothecary service space, press/archives, a small staffed lodging reception, a meaningful civic meeting site, and an outdoor route/hazard location. Reuse existing Market Lane, Lamp Shop, Tavern, Church, churchyard, treeline, riverside and bridge when possible. The lodging house is NOT the OOC Inn Between; postpone a full multiroom hotel simulation if it delays the core game.

Deliverable: connected, navigable workplaces and landmarks with daylight/night, weather, event and aftermath text.
Done when: every new room has inspectable objects, an NPC schedule or relevant service, at least one available recurring activity, a clue or historical thread, working exits, and an observed restart-safe world-state change. No dead-end room is added to satisfy a numeric quota.

### 4. Make material systems and village services coherent

Reuse real objects, soup packets, repair parts, hearth fuel and market goods. Introduce only the common primitives jobs need: finite recipes, equipment wear/repair, stock quality, fees/price decisions where meaningful, deliveries and documented transactions. Define safe renewal bounds and NPC baseline so casual play remains cozy rather than a punishment simulator. Standardize source-linked events and inventory custody to prevent phantom crafts or double spending.

Deliverable: one coherent supply and service network connecting at least three work locations and multiple Callings.
Done when: a material can be sourced, transported, transformed, consumed or repaired, credited to the right actor, and recovered or replenished through an actual rule. Test shortage, spoilage, duplicate actions, logout with unfinished inventory, and crash/restart.

### 5. Finish the domestic and market Callings

Innkeep: extend current soups/hearth into recurring guest or diner orders, service quality and follow-up.
Merchant: extend crate procurement, daily market decisions and civic commissions into repeatable priced supply fulfillment and delivery obligations.
Smith: extend lamp/scale work into recurring repair and fabrication orders whose outputs have durability and actual consumers.
Healer: extend assessment/care into recurring patient requests, triage, limited remedies and revisits with uncertainty.

Deliverable: two distinct, renewable, player-observable activities per Calling, with real objects, NPC services and cross-role consequences.
Done when: each has a one-account path and a multi-account improvement path, a meaningful choice, persistent ledger attribution, and a daily-return case in which prior work is still visible.

### 6. Finish the information and cultural Callings

Chronicler: let a player research incompatible sources, edit or correct a sourced local story, and publish a persistent paper or notice without fabricating certified truth.
Performer: add rehearsals, scheduled voluntary shows, audience attendance and remembered performance outcomes on top of music and duets.
Detective: add repeatable evidence handling, witness contradictions, case notes and a responsible way to file provisional conclusions, separate from final mystery truth.
Mystic: add recurring competing-school field studies, controlled vigils or modest services, mundane false alarms and rare world-authoritative anomalies with physical prerequisites.

Deliverable: two renewable, mechanically distinct activities per Calling, and at least one cooperation path linking each to an existing role.
Done when: participation changes a record, schedule, material state, NPC response or public consequence. Absent witnesses never acquire magical knowledge. The paper cannot certify an unsupported claim. Rare magic stays rare.

### 7. Distinguish the field Callings and make travel consequential

Wanderer must become more than four survey signatures: real routes, courier deliveries, changing travel conditions, supplies and firsthand mapping or route advice.
Hound must become different from a Wanderer: track evidence, hazard patrols, escort/protection or rescue work with prevented or mitigated harm, no mandatory combat.
Introduce limited outdoor adversity, changing hazards and recovery paths. Keep route conditions anchored to the existing clock, weather, finite supplies and resident simulation.

Deliverable: two repeatable professional loops for each and one cross-role incident involving at least one non-field Calling.
Done when: movement and evidence affect real services and locations; an unsuccessful patrol or missed courier has bounded, legible aftermath; a solo player can continue rather than wait indefinitely for another user.

### 8. Give advancement and institutions a real purpose

Keep one active Calling and earned work history. Use existing apprenticeships instead of inventing a large XP grind. Implement at least one meaningful, authored career improvement for each Calling, such as access to a better technique, more demanding commission, public responsibility or mentor relationship. Skills and credentials should make available choices richer, not inflate a score. Prototype small multi-specialty identity where practical, but do not require forty fully independent trees before the initial release.

Deliverable: clear progression from newcomer participation to trusted/competent professional work with visible social recognition.
Done when: fresh, returning, mentor and apprentice accounts have tested authorization, graduation/withdrawal, changed available work and preserved prior biography. Changing Calling does not erase accomplishments or grant all powers simultaneously.

### 9. Finish a compelling mystery portfolio

Use the existing bridge plaque as the baseline. Add two more complete substantial investigations from established authored material, prioritizing a newcomer-facing thread such as The Wrong Trunk and a longer village thread such as the Manor Lights or another World Bible-supported case. Use Room Six and current private mystery infrastructure where it fits the OOC/IC boundary. Each needs physical clues, at least two plausible evidence routes, disagreements or misleading testimony, several player responses, world clock consequences, multiplayer discovery, and persistent aftermath. A mystery need not explain the village's deepest supernatural truth.

Deliverable: three individually traversable investigations, at least one ordinary/mundane answer and one genuine Gothic phenomenon somewhere in the portfolio, with follow-up hooks into everyday professions.
Done when: independent scripts prove different branches cannot overwrite each other, clue custody is accurate, players who arrive late can still interact meaningfully, theories are not automatically canon, and aftermath remains visible across restart. A single solution-picking command is insufficient.

### 10. Turn source text into active recurring village life

Extend the active random incident pool from 14 toward about 30, the timed pool from 1 toward 4 to 6, and server-wide frameworks from 1 toward 2 to 3. Use the accepted rumor, ambient and incident manuscripts as source material, but activate only entries with real location/time conditions and appropriate player response or observational consequence. Add low-key seasonal celebrations and routine changes, plus rare, attributable strange incidents. Do not loop the same repaired object into a fake new crisis.

Deliverable: a calendar and environmental ecosystem where different visits generate a useful mix of ordinary work, new mysteries and modest surprises.
Done when: seeded simulations across seasons, weather, downtime and restart demonstrate varied distribution, valid cooldowns, no duplicate tick effects, bounded logs, no ungrounded rumor-to-truth elevation and visible aftermath. Counts alone do not pass the step.

### 11. Make residents, social continuity and the living village react

Improve selected existing residents' reusable professional needs, expectations, relationships and persistent player recognition. Build from Resident Life v2, schedules, population summaries, witnessed-event rules, Bram memory, Commons follow-up and situation consequences. Each major interaction should be attributable to a real witnessed or institutionally transmitted event; an NPC must not know what happened across town merely because it is in the database. Ensure unattended obligations can expire or resolve plausibly without players.

Deliverable: a village that appears to carry on between sessions, with NPC services capable of supporting low concurrent population.
Done when: ordinary residents pursue routines, change plans for authored needs, acknowledge a player's actual signed work, respond differently on return and keep state through restarts. Test day jumps, absentee players, capped memory, privacy and resource failure.

### 12. Harden human/AI access and multiplayer fairness

Recheck the disposition of historical PR #78 against current main, then continue the existing nonprivileged agent context: visible residents, objects, exits and locally possible actions. Verify that ordinary browser and terminal clients can act without inference or agent-only commands. An independently run model-controlled client can be tested later but is optional, never a launch gate. Keep standard browser/terminal UX useful to humans: clear help, errors, contextual work directions and readable descriptions. Check multiaccount resource contention, attempts to forge events, Commons moderation privacy, alternate masks and colliding jobs. Do not add recurring expensive NPC-model inference to the baseline simulation.

Deliverable: an ordinary human-style browser or terminal account can independently enter, discover work, collaborate or disagree, exit and recover using the same world mechanics. Optional model-controlled client research may separately check parity, but is not a release prerequisite.
Done when: local ordinary-account integration covers at least eight simultaneous connections, reconnect/disconnect, stale context, missing NPC, bad command, contested material, false report and mixed-player permissions. This is LOCAL verification, not public-host capacity proof.

### 13. Stabilize, measure content honestly and freeze a candidate

Run the full fresh clean-checkout suite, real telnet and browser smoke, all Calling loops, each mystery branch, repeatable economy flow, 2+ account race conditions, world clock leaps, same-world rebuilds and genuine server stop/start. Perform an offline SQLite backup/restoration rehearsal against a disposable database with protected fixture state. Check logs, errors, bounded history and hidden information exposure. Use ops/content_inventory.py plus reachable-flow evidence to produce a code-ready coverage sheet. Close release-blocking defects and freeze one reviewed main commit.

Deliverable: versioned code-ready build, scripted test report, feature matrix, regression proof, backups/restore evidence on disposable local storage, gameplay instructions and a concise known-limitations note.
Done when: every promised early-access activity works through normal player verbs, no severe data loss/duplication/permission bug is known, the player can complete and resume meaningful work, and the reviewed exact SHA has green main-branch CI. This gate means READY TO PREPARE HOSTING, never PUBLICLY DEPLOYED.

### 14. Only then: choose a host and execute real release operations

Defer platform choice and recurring expense until Step 13 passes. Before any actual external invitation, choose/authorize provider and operator, verify HTTPS/WSS and optional TLS terminal transport, use persistent storage, encrypt/download/restore an off-host backup, verify rollback, monitoring/alerts, moderation escalation and actual public endpoint login, and perform the documented long-running concurrent soak. Follow ops/ALPHA_RELEASE_CHECKLIST.md, ops/deploy/INVITED_ALPHA_GATES_A_B.md, and ops/LAUNCH_EVIDENCE_GATE.md. Do not reuse the declined DigitalOcean proposal as an approved decision or claim public readiness from local CI.

Deliverable: hosted invited/public release decision with real environment and human-operator evidence.
Done when: all applicable external gates are verified on the exact deployed SHA and a human operator explicitly approves launch. Until then the game can be code-ready, not publicly certified.

## Recommended batch order and dependency map

- Batch A, launch spine: 0 -> 1 -> 2. Do not widen the world before a newcomer can find and complete a true renewable work opportunity.
- Batch B, economic core: 3 -> 4 -> 5. Open rooms only together with services, materials and professional work.
- Batch C, ten complete starter careers: 6 -> 7 -> 8. Each role must be individually useful and institutionally connected.
- Batch D, depth and discovery: 9 -> 10 -> 11. Mysteries, incidents and residents should multiply the value of existing verbs rather than introduce isolated systems.
- Batch E, software readiness: 12 -> 13. Fix bugs and prove the actual candidate before any infrastructure expense.
- Batch F, deployment: 14 only after accepted code-ready gate.

After each batch, rerun the full regression, preserve an exact SHA and record changed features, player-visible outcomes, known gaps and remaining blockers. Do not mark whole Callings done based on their identity registration or help text.

## Program-first release scorecard

For every Calling record separately: selected and playable; first meaningful job; first renewable job; second distinct renewable job; partner-specific improvement; persistent result and attribution; NPC fallback; earned improvement; live account command coverage; post-restart evidence. Use verified, partial, blocked or deferred, not subjective percentages.

For each mystery: discovered; physical evidence; competing claims; branch choices; timed/no-player resolution; persistent aftermath; late-player route; tests for truth/privacy and restart.

For each room: accessible; reasons to visit; occupation or shared service; inspectable material evidence; time/weather/event variation; at least one ongoing activity; changed-state text; safe navigation and help.

For each incident: grounded trigger; actual registry/wiring; cooldown; observable consequence; optional player contribution; persistence; no double-fire; source link; automated witness. Include manuscript-only ideas in a separate column.

Quality review can use uncoached players once convenient, but the programming sequence does not depend on scheduling a live alpha cohort. Actual future public release must still satisfy external safety, performance and operational evidence. No software scorecard can certify enjoyment.

## Explicit exclusions until after release

- Castle and Manor interior expansions or an endlessly growing overworld.
- Pretorius arriving or entering play; the dark leased shop remains a deliberate narrative promise.
- Portable laboratory sync, other projects' autonomous agent orchestration, optional speculative cognition architecture.
- Full hotel management, forty specialty careers, advanced culinary sensory preference modeling and generalized complex economic ownership.
- Mandatory combat or a conventional monster-grinding leveling system.
- Paid infrastructure, domain purchases or remote API expenses before code-readiness.

## First coding ticket after this roadmap is accepted

Step 1, complete the player-facing newcomer and return path using the existing guide, calling work, Commons, agenda, agent context and verified renewable commissions. Demonstrate a newcomer choosing Innkeep or Merchant, physically working, leaving a signed state change, returning after a real restart, discovering another activity and receiving guidance grounded in actual case state. Build on existing tests; do not write a second onboarding engine. If the flow already passes, close with evidence and move immediately to Step 2.

At every step prefer one meaningful, fully tested consequence over ten decorative commands.
