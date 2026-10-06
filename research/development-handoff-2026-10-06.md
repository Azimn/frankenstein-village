# Frankenstein Village Development Handoff

Date: 2026-10-06

Repository: https://github.com/Azimn/frankenstein-village

Audited current `main` for this refreshed handoff: `d563ef46fc9bc33a13bd7b6e730ee0f733b3aa2a`

Use the actual current `main` branch at the start of the takeover session. Do not assume the baseline above is still current if another developer or agent has landed work since this document was written.

## Current takeover state as of the refreshed handoff

Before doing any development, verify that `main` is still at or descended from:

`d563ef46fc9bc33a13bd7b6e730ee0f733b3aa2a`

The clean-checkout regression for that exact commit passed in GitHub Actions run:

`37472901213`

The repository has advanced beyond the earlier snapshot in this document. In particular, current `main` already contains:

- the merged weighted random-world-incident layer;
- village-scale server events;
- public mystery evidence and provisional theory infrastructure;
- persistent seasonal/chapter frameworks;
- this production handoff document.

There is also an open PR at the time of this refresh:

`PR #15 - Add mask-specific private mystery threads`

Known PR #15 head when this handoff was refreshed:

`36a234c5291df2feddbb90f185086f1487e598a2`

Its base is older than current `main`, and GitHub currently reports it as non-mergeable.

Do not discard it and do not blindly merge it.

The first development task for the next instance is to inspect the exact PR #15 delta against current `main`, determine whether the implementation is still sound, transplant or reconcile the private-mystery work onto current `main`, run the full regression suite, fix all conflicts and behavioral regressions, and only then merge it.

If PR #15 has already been superseded, merged, closed with replacement work, or otherwise changed by the time the takeover begins, use the actual current repository state instead.

# TAKEOVER PROMPT

You are taking over active production development of Frankenstein Village.

Your mission is not to brainstorm, rewrite the architecture from scratch, or produce another planning document. Your mission is to inspect the live repository, preserve what already works, and continue implementing the remaining authoritative production backlog until the repository's launch list is genuinely complete, tested, documented, and playable.

Work directly from:

`https://github.com/Azimn/frankenstein-village`

Treat the live repository as authoritative.

If this handoff, prior chat history, an addendum, a remembered summary, or your own assumptions conflict with the repository, the repository wins.

Within the repository, use the following precedence rules:

1. `files/frankenstein-village-world-bible-v0.2.md` defines canon, setting, unresolved questions, tone, world rules, and launch constraints.
2. `files/frankenstein-village-quest-handoff-v0.3.md` defines the production backlog, content families, calling packs, launch inventory targets, and acceptance tests.
3. `files/quest-generation-packet-v0.1.md` defines the formal content-generation contract and quotas.
4. Accepted canon banks such as `files/incident-templates-v0.1.md`, `files/rumor-seeds-v0.1.md`, `files/ambient-events-v0.1.md`, and `files/npc-line-banks-v0.1.md` define accepted content seeds.
5. `design-decisions.md` records settled architecture and implementation doctrine.
6. `spike/BUILD_NOTES.md` records the executable contracts of systems that have actually been implemented.
7. Live code and tests define what currently exists. If live behavior conflicts with canon or a settled repository decision, fix the implementation rather than silently changing canon.

Do not rely on stale conversation summaries when the live repository can answer the question.

Do not resurrect old branches or closed pull requests merely because they appear in prior logs. Inspect current `main` first.

## Current project doctrine

Frankenstein Village is a persistent Evennia text world for human and AI players.

The server hosts the place, not dozens of continuously thinking minds.

The governing simulation principle is:

`continuity is always active; cognition is activated only when required`

The world should simulate persistent consequences, locations, schedules, relationships, evidence, records, rumors, economic needs, and other state that can matter later. It should not continuously simulate decorative internal experience that nobody can observe and that produces no later consequence.

Important launch principles include:

- mystery over horror;
- 1890s European Gothic atmosphere;
- persistent world, no player wipes;
- human and AI account disclosure occurs at the gate, not through IC markers;
- NPCs never perceive the OOC layer;
- no levels or conventional XP at launch;
- callings provide social capability, access, reputation, work, and interdependence;
- no one does everything;
- player absence must not be punished;
- time continues while players are offline;
- rumors are beliefs with provenance, not truth flags;
- Chronicle truth and Harbinger reporting must remain epistemically distinct;
- no specific mortal NPC may be load-bearing;
- anyone can die or depart;
- world consequences should survive the person who caused them;
- intentionally unresolved World Bible questions must stay unresolved unless the Bible itself is explicitly revised;
- strange events are allowed, but ordinary life must remain substantially more common than Gothic anomaly;
- text is the medium advantage: use compact mechanics plus rich prose rather than creating invisible simulation complexity.

Do not introduce hidden account substrate into the in-character world.

Do not create dozens of rooms merely to justify a system.

Do not make every event into a quest.

Do not make every incident into a rumor.

Do not make every rumor into a newspaper article.

Do not make every newspaper article into Chronicle truth.

## Current live implementation snapshot

The following systems are already established on current `main`. Inspect them before modifying them.

### World and regression foundation

The live Evennia game is under:

`spike/fvillage/`

The full clean-checkout acceptance command is:

`python3.12 spike/tests/run_all.py`

The regression suite includes clean bootstrap, idempotent rebuild, runtime assertions, a real server start, real telnet interaction, real server stop/restart, and post-restart persistence assertions.

Do not call a slice complete merely because unit-level assertions pass. The network and restart paths are part of the release gate.

### Persistent resident population

Key files:

- `spike/fvillage/world/resident_data.py`
- `spike/fvillage/world/residents.py`
- `prototype/engagement-tiers/`

The production population is approximately 36 named residents with stable IDs, genealogy, households, occupations, schedules, logical locations, event-aware fallbacks, player-specific relationship state, persistent facts, engagement-based simulation resolution, and cheap automaton behavior.

Simulation resolution, accumulated character depth, and narrative importance are mechanically separate.

Residents may become deeper through player attention and later return to low-cost routine simulation without losing established continuity.

Existing authored NPCs retain their specialized behavior.

Do not replace this with one LLM agent per resident.

### Rumor provenance

Key file:

`spike/fvillage/world/rumors.py`

Rumors have immutable root records and append-only transmissions.

NPC and player belief state is distinct from objective world truth.

Retelling preserves lineage.

Event-generated rumors retain causal event references.

The full 250-rumor canon bank exists, but only reachable content should surface.

### Canonical world-event ledger

Key file:

`spike/fvillage/world/events.py`

Structured world events are the canonical causal substrate.

Systems consume structured events directly.

Do not convert known game events into prose and then use NLP to rediscover what happened.

### Harbinger and Chronicle public memory

Key file:

`spike/fvillage/world/publications.py`

The Harbinger is fast, public, fallible, corrigible reporting.

The Chronicle is slower, provenance-first institutional memory.

Player depositions canonize that a player gave an account, not that the account is true.

Corrections and annotations append without silently rewriting prior records.

Private and sealed events do not automatically enter public records.

### Shared autonomous situations

Key file:

`spike/fvillage/world/situations.py`

Situations are shared world state, not per-player quest instances.

Per-mask evidence is separate from objective situation state.

Current live vertical slices include:

- The Tithe Strongbox
- The Torn Chronicle

The incident feed supports dormant eligibility, prerequisites, active-slot limits, deterministic surfacing, autonomous deadlines, shared door-closing choices, rumor/public-record aftermath, and persistence.

### Timed world windows

Key file:

`spike/fvillage/world/timed_incidents.py`

The first live timed incident is The Well Boils.

Timed windows distinguish firsthand evidence from aftermath evidence.

Absence does not erase content: an unwitnessed window can still leave residue, rumor, and later public reporting.

Restart catch-up resolves directly from current time rather than replaying elapsed sub-ticks.

### Recurring village calendar

Key file:

`spike/fvillage/world/scheduled_events.py`

Current recurring public rhythms include:

- daily Harbinger publication;
- Saturday Market Morning;
- Sunday Service.

The village clock is the authoritative scheduler.

Do not create a separate ticker for every recurring system.

### Weighted random world incidents

Key file:

`spike/fvillage/world/random_incidents.py`

Current accepted examples include:

- Public Sneeze
- Extinguished Lamp

Selection is restart-stable and deterministic for a given world-state boundary while remaining stochastic across changing day, hour, weather, resident density, occupancy, and seasonal context.

Mundane texture is intentionally weighted above odd signal.

Random incidents are private structured occurrences by default and do not automatically become rumors, Harbinger stories, Chronicle entries, or quests.

Room text is a projection from persistent state and is reconstructed after restart.

Note: a previous PR numbered #11 was closed during concurrent development. Do not resurrect it. The random-incident system and subsequent work are already represented on current `main`.

### Village-scale server events

Key file:

`spike/fvillage/world/server_events.py`

The first production framework is The Long Blackout.

It has one shared village state, local response nodes, autonomous resolution, public consequences, Harbinger/rumor projection, Chronicle eligibility on completion, and restart-safe overlays.

### Public mystery layer

Key file:

`spike/fvillage/world/public_mysteries.py`

The first public mystery is Why Are the Manor Lights Returning?

Observations are objective local facts.

Player theories remain provisional and do not receive automatic truth values.

There is deliberately no generic "solve" operation for intentionally unresolved mysteries.

### Seasonal chapter framework

Key file:

`spike/fvillage/world/seasonal_frameworks.py`

The project now has a six-chapter 365-village-day modifier cycle without settling the still-open exact civil year.

The initial chapter is The Weeks of Long Shadows.

Seasonal state modifies existing weather, random-incident weighting, optional evening routines, economy tags, and content eligibility.

Chapter transitions enter Harbinger and Chronicle history.

### Existing world features that must remain intact

The current game also includes:

- Inn Between OOC hub and compact;
- persistent private rooms;
- village square;
- Blood of the Vine;
- St. Lazarus Church;
- Lamp Shop;
- coin economy and basic consumables;
- hunger and drunkenness;
- Tavern regular routines;
- confession privacy;
- fiddle practice, duet, dice, seating, and related social verbs;
- Room Six mystery;
- moderation/report/warning/suspension/appeal lifecycle;
- account-level human/AI disclosure.

Preserve backward compatibility.

## Important implementation lessons already learned

These are not theoretical. Previous regression loops found them.

### Evennia persistent wrappers are not always literal dict objects

Do not assume `isinstance(value, dict)`.

Use mapping semantics, usually `collections.abc.Mapping`, where persistent Attribute values may be Evennia wrappers.

### Event IDs must remain monotonic

Do not rewind event allocators during QA cleanup.

A reused event ID can make stale resident flags appear to refer to a new event.

Gaps are harmless. Identity reuse is not.

### Clean synthetic QA symmetrically

If a synthetic event is removed from the canonical ledger during test cleanup, remove the corresponding synthetic resident event flags, rumor roots/transmissions, publication artifacts, overlays, or other derived QA state as appropriate.

### Authored NPC schedules are real

Do not make a specific NPC's physical presence load-bearing in a network test unless the schedule guarantees it.

Prefer multiple evidence paths.

A witness can be useful without being mandatory.

### Logical and physical location are distinct for background residents

Many background residents project unbuilt homes, workplaces, school, fields, and similar logical locations into the physical Offstage room.

Social co-location must compare logical location for population-managed residents so everyone in Offstage does not appear to be together.

Authored residents with real rooms keep their physical room as authority.

### Public-record provenance must remain visible in prose

If information is reconstructed from Harbinger files, the player-facing text must explicitly say it is press-derived or reconstructed rather than recovered original truth.

Do not preserve provenance only in hidden metadata.

### Do not test implementation accidents

Tests should validate contractual behavior.

For example, an eligible random social incident may choose either of several public rooms. Test that the selected room is valid and correctly receives the overlay rather than hard-coding one room unless the canon requires it.

### Temporary room text is projection

Scheduled, random, seasonal, server-event, and similar overlays must be reconstructable from persistent state after restart.

Do not use room description mutation as the sole source of truth.

### Avoid doubled articles in object keys

Do not create an object key such as "the tithe roll" when Evennia may render an article automatically and produce "a the tithe roll".

Use article-free canonical keys and natural aliases.

## Current backlog status

Do not confuse "framework exists" with "launch family complete."

The production handoff's launch inventory targets are much larger than the current implementation.

### Frameworks substantially implemented

The following families have working production foundations and at least one real vertical slice:

- 3.15 Timed incidents
- 3.16 Scheduled world events
- 3.17 Random world incidents
- 3.18 Server-wide events
- 3.19 Seasonal/chapter frameworks
- 3.20 Public mysteries
- 3.22 Harbinger infrastructure
- 3.23 Chronicler infrastructure

These are NOT complete at launch inventory scale.

For example, the target remains approximately:

- 30 timed incidents;
- 75+ random incident templates;
- 10 server-wide event frameworks;
- 50+ Harbinger templates.

Do not hand-code 75 copies of the same engine. Continue converting accepted content into data-driven definitions and reusable handlers.

### Immediate next backlog item

Unless current `main` has already added it by the time you take over, the next unresolved numbered family after the completed framework sequence is:

`3.21 Private mysteries`

Read lines 689 onward of:

`files/frankenstein-village-quest-handoff-v0.3.md`

A private mystery must create information asymmetry without becoming a solo instance or a server-wide bottleneck.

Good first candidates from the accepted list include:

- The Note Under Your Door
- The Object in Your Room
- The Wrong Memory in the Ledger
- A Private Invitation

Design the framework so private knowledge can be shared voluntarily and can later interact with rumors, relationships, records, and shared situations without making one inactive account load-bearing.

### Major content families still largely missing or underbuilt

The following production families should be considered incomplete unless a fresh inspection proves otherwise:

#### 3.1 through 3.14

- Newcomer quests
- Civic quests
- Rumor quests
- Small mysteries at launch scale
- Long mystery chains
- Expeditions
- Group investigations
- Social expeditions
- Faction quests
- Cross-faction conflicts
- Debt quests
- Bond quests
- Hyde quests
- Rival investigator quests

Some current systems provide reusable foundations for these, but the families and launch inventories are not complete.

Do not reinvent state machines for each family. Reuse situations, resident relationships, rumors, publications, calendar state, timed windows, server events, and persistent records.

#### 3.21

Private mysteries remain a major missing framework.

#### 3.22 and 3.23

Harbinger and Chronicle infrastructure exists.

The authored content family is not complete at launch scale.

Continue adding data-driven editorial, correction, deposition, archive, index, disagreement, and public-memory situations without violating provenance.

#### 3.24 Economic content

The game has coins and a few local purchases, but not a production economic-content system that connects real consumers, shortages, institutions, weather, chapters, community projects, and prices.

The repository already exposes seasonal economy modifiers for future systems.

Use them.

#### 3.25 Procurement quests

Largely missing.

Procurement must answer:

- why this object;
- why now;
- who else wants it;
- what changes if it is not obtained;
- what route, provenance, timing, or quality constraint makes it more than a fetch quest.

#### 3.26 Crafting commissions

Largely missing.

Do not implement this before the minimal systemic-object property/tag layer exists.

Crafted items should retain useful provenance such as maker, commissioner, date, materials, repairs, and ownership history.

#### 3.27 Travel quests

Largely missing.

Travel time, weather, route access, schedules, and missed opportunities must matter.

Avoid teleporting quest logic.

#### 3.28 Watch quests

The Manor Lights public-mystery infrastructure is a useful foundation, but there is no general longitudinal watch-log system yet.

Watch content should record timestamped observations and make accumulated data useful.

#### 3.29 Cartography quests

Largely missing.

Maps need provenance and date.

Old maps should become historical evidence rather than silently updating when the world changes.

#### 3.30 Collection quests

Largely missing.

Collections need useful metadata, not only item counts.

#### 3.31 Puzzles and ciphers

Largely missing.

Puzzles must arise from world logic, documents, maps, mechanisms, schedules, or period technology.

Avoid arbitrary detached riddles.

#### 3.32 Moral choice quests

The existing strongbox and Chronicle-gap choices provide useful patterns, but the larger family remains underbuilt.

Do not assign morality points.

Outcomes should come from institutions and people with their own values.

#### 3.33 Failure content

Some existing situations already produce autonomous aftermath, but there is no generalized launch-scale failure content layer.

Failure should produce changed state, new relationships, rumors, debt, closure, delay, or another playable branch rather than only "quest failed."

#### 3.34 Delay content

Underbuilt.

Offline time must remain causally meaningful.

#### 3.35 Repeat-visit location states

Underbuilt.

Locations should accumulate altered descriptions, recurring traces, repair states, social memory, and event consequences where appropriate.

## Calling system remains a major foundation gap

Section 4 defines content packs for:

- Innkeep
- Chronicler
- Smith
- Healer
- Merchant
- Wanderer
- Performer
- Detective
- Hound

The World Bible defines callings as social capability and endgame structure, not combat classes.

The repository's design doctrine includes:

- broad participation;
- capped simultaneous mastery;
- no one does it all;
- cross-calling interdependence;
- apprenticeship;
- respecialization with retained history;
- calling ranks and institutional responsibilities.

Do not add conventional levels or XP.

Before bulk calling-specific quests, inspect whether a calling-core implementation has appeared on current `main`.

If not, build the smallest persistent calling architecture that can actually support one complete calling vertical slice, test it, then expand.

Launch targets include:

- at least 6 authored quests per calling;
- approximately 8-12 repeatable professional jobs per calling.

Do not mark Section 4 complete merely because calling names exist in documentation.

## Systemic object and crafting foundation remains important

`design-decisions.md` specifies a small mechanical property/tag model plus free flavor text.

The current intended compact tag pool is approximately:

- harm
- toxin
- mend
- ward
- holds
- fuel
- uses
- worth
- perish
- tale
- hidden:<tag>

An authored object should normally carry no more than roughly three mechanical tags.

This is the foundation for economic content, procurement, crafting, hidden properties, evidence, provenance, durability, storage, and later systemic consequence.

Before implementing Section 3.26 at scale, create the smallest complete property-driven object vertical slice if it does not already exist.

Use actual executable verbs.

Do not build a speculative object-component architecture with no playable use.

## Section 5 remains substantially incomplete at launch scale

### 5.1 Ambient micro-content bank

The accepted 300-event content bank exists.

Runtime integration is not equivalent to the full bank being playable.

Build data-driven loading and location/time/state eligibility rather than manually wiring hundreds of if-statements.

Ambient events should remain observations, not automatic mysteries.

### 5.2 NPC schedules

The production resident scheduler is substantially implemented.

Continue expanding only where a backlog item requires it.

### 5.3 Major NPC personal arcs

The seed bank exists.

The launch target of several arcs per major NPC is not complete.

Use persistent concerns, events, relationships, correspondence, and institutions.

Do not turn major NPCs into static quest dispensers.

### 5.4 Player-generated quest templates

Largely missing.

Examples include:

- Wanted: Witnesses
- Buy Order
- Guide Needed
- Research Assistance
- Missing Person
- Commission
- Escort Request
- Public Meeting
- Reward for Return
- Apprentice Wanted
- Theory Review
- Community Collection

Build structured templates with provenance and expiry.

Do not let player requests mutate canonical truth merely because they were posted.

### 5.5 Community projects

Largely missing.

Target: at least 6 meaningful projects.

Projects require distinct contribution types and persistent world changes.

### 5.6 Hidden discoveries

The target is 50+.

Some current objects provide hidden evidence, but the inventory is far from complete.

Use subtle physical clues and provenance.

Avoid turning every hidden detail into supernatural content.

### 5.7 Legendary discoveries

The event, Chronicle, Harbinger, rumor, and publication systems now provide much of the propagation path.

A generic salience/legend promotion layer may still be incomplete.

The intended pipeline is roughly:

`action -> systemic consequence -> salience -> Chronicle -> Harbinger -> rumor -> new hooks`

Do not make every unusual event legendary.

### 5.8 AI-compatible activities without AI-only rules

Still underbuilt.

Any useful activity available to AI players must also be available to humans under the same IC rules.

Likely foundations include watch logs, archive comparison, rumor provenance audit, route revalidation, market price logging, and correspondence indexing.

### 5.9 Retirement and death content

Player retirement/death remains a major unfinished product area unless a fresh inspection proves otherwise.

The accepted content includes:

- hand over keys;
- final Chronicle entry;
- settle ledger;
- choose apprentice;
- farewell supper;
- into the Mists;
- leave collection;
- retire mask;
- funeral;
- estate;
- last case inheritance;
- obituary;
- memorial entry;
- unfinished debt;
- empty routine;
- suspicious death.

The project also adopted a death-memory rule from persistent-world research: characters should not be able to testify from personal memory about their own death.

Implement lifecycle consequences carefully.

Do not erase prior history when a mask retires or dies.

## Full implementation packets

Section 6 includes full packets such as:

- DM-Q-0001 The Wrong Trunk
- DM-Q-0017 Tomorrow's Obituary
- DM-Q-0033 The Tribute Runs Thin
- DM-Q-0040 Dinner Below
- DM-Q-0057 Your Fortune Has Already Happened
- DM-Q-0060 The Road That Returns
- DM-Q-0101 The Long Blackout
- DM-Q-0112 The Public Theory Board

The Long Blackout and public-theory concepts now have live foundations.

The others remain excellent acceptance targets because they exercise different combinations of systems.

Do not assume an implementation packet is complete merely because its enabling subsystem exists.

## Launch inventory targets remain the final bar

From Section 7:

- Newcomer scenarios: 12
- Small mysteries: 30
- Major mystery chains: 10-12
- Civic quests: 30
- Calling-specific authored quests: 6 per Calling minimum
- Repeatable professional jobs: 8-12 per Calling
- Faction quests: 8-10 per faction
- Cross-faction conflicts: 20
- Expedition locations: 10-12
- Social expeditions: 12
- Group investigations: 12
- Timed incidents: 30
- Random incident templates: 75+
- Server-wide event frameworks: 10
- Community projects: 6+
- Hidden discoveries: 50+
- Major NPC personal arcs: 3-5 per major NPC
- Rumor seeds: 250+
- Ambient room events: 300+
- Harbinger templates: 50+
- Player-request templates: 30+

The repository already has the 250-rumor bank and 300 ambient-event bank as accepted content documents, but content-bank existence is not the same as runtime reachability.

Treat these as density targets, not an instruction to hand-code hundreds of bespoke classes.

Prefer:

- data-driven templates;
- parameterized systems;
- shared state machines;
- accepted content banks;
- world-state eligibility;
- reusable aftermath handlers;
- provenance-aware generators.

## Acceptance tests that must remain binding

Every quest/content slice should satisfy the repository's Section 7 acceptance tests.

At minimum:

- natural discovery without floating quest marker;
- objective world state separated from belief and rumor;
- at least one decision changes more than reward payout;
- defined no-intervention path;
- time matters where appropriate;
- multiplayer contributions can differ;
- useful persistent consequence;
- failure or delay produces playable aftermath;
- no decorative numbers with no behavior;
- no IC substrate leakage;
- no accidental answer to intentionally unresolved canon;
- still sensible after another player interacted first;
- normal, active, aftermath, and return-visit prose where state visibly changes.

Location acceptance requires:

- normal description;
- time variation where meaningful;
- weather/event variation where meaningful;
- schedule integration;
- ambient events;
- searchable details;
- information sources;
- recurring activity;
- several hooks or dependencies;
- learnable social/historical context;
- altered post-event states.

Persistent NPC acceptance requires:

- role;
- daily/weekly schedule;
- conversational priorities;
- known rumors with provenance;
- social relationships;
- public and private concerns;
- recurring need;
- personal arc seed;
- event reaction rules;
- player interaction memory where implemented;
- beliefs kept separate from objective unresolved mystery state.

## Recommended continuation order

Do not blindly follow section numbers if a missing dependency blocks several later families.

However, preserve the user's one-item-at-a-time development rhythm.

At the start of each slice:

1. Re-read current `main`.
2. Re-check the production handoff.
3. Identify the smallest missing dependency that closes one real backlog item.
4. Implement one complete vertical slice.
5. Test it through the real game.
6. Merge only when the exact PR head passes.
7. Re-run against merged `main`.
8. Update the user with what is actually complete.
9. Continue to the next item.

Unless current `main` has already filled it, the recommended immediate next item is:

`3.21 Private mysteries`

After that, the recommended dependency order is:

1. Finish Harbinger/Chronicle content frameworks where the existing publication substrate can support them cheaply.
2. Implement the minimal systemic-object/tag vertical slice.
3. Implement the persistent calling/interdependence core.
4. Build economic content and demand state.
5. Add procurement on top of real economic needs.
6. Add crafting commissions with object provenance.
7. Build reusable travel/watch/cartography/collection infrastructure.
8. Add puzzles and ciphers on top of documents, maps, schedules, and devices.
9. Expand moral/failure/delay/repeat-visit patterns using the existing situation engine.
10. Build player-generated request templates and community projects.
11. Implement player retirement/death lifecycle content and inheritance.
12. Expand newcomer, civic, rumor, faction, cross-faction, expedition, social, group, debt, bond, Hyde, and rival-investigator families.
13. Integrate accepted ambient and incident banks into data-driven runtime selection.
14. Expand every framework family toward launch inventory targets.
15. Complete major NPC personal arcs, hidden discoveries, legendary discoveries, and AI-compatible work.
16. Run final launch-density, accessibility, parser-tolerance, performance, prose, persistence, and low-staff-operation audits.

If a later dependency needs to move ahead of this order, document why in `design-decisions.md`.

## Required engineering loop

For every meaningful subsystem, repeat:

`INSPECT -> MODEL -> IMPLEMENT -> TEST -> SIMULATE -> BREAK -> FIX -> RETEST -> PLAY -> REVIEW -> MERGE -> VERIFY MAIN -> REPEAT`

### INSPECT

Read the live files.

Do not duplicate existing machinery.

Identify:

- persistent state ownership;
- existing APIs;
- canonical content;
- tests;
- event inputs;
- emitted events;
- publication effects;
- rumor effects;
- NPC effects;
- OOC/IC boundaries;
- migration needs;
- concurrency risks;
- restart behavior.

### MODEL

Write down the smallest coherent architecture before coding.

Answer:

- what owns the state;
- whether the state is objective, belief, publication, or player-private knowledge;
- how it starts;
- how it changes;
- how nobody-intervenes progression works;
- what persists;
- what is intentionally ephemeral;
- which existing subsystem should be reused;
- what the player actually does.

### IMPLEMENT

Build one complete vertical slice.

Avoid speculative interfaces with no playable use.

Prefer data definitions plus shared handlers over copy-pasted classes.

### TEST

Add automated coverage for:

- happy path;
- boundary conditions;
- two-player divergence where relevant;
- no-player path;
- restart persistence;
- idempotent rebuild;
- relevant NPC isolation;
- provenance;
- deadline/catch-up behavior;
- stale state;
- invalid commands;
- branch closure;
- previous-feature regression.

### SIMULATE

Where appropriate, advance days or weeks.

Ask whether state remains coherent without observers.

### BREAK

Actively look for:

- global mutable state leakage;
- duplicate unique records;
- stale overlays;
- schedule drift;
- dead residents acting;
- inactive players counted as live witnesses;
- rumor becoming truth;
- Harbinger becoming omniscient;
- Chronicle silently rewriting itself;
- event ID reuse;
- per-player private worlds where shared state was required;
- one mortal NPC becoming load-bearing;
- unbounded histories;
- restart rerolls;
- random supernatural saturation;
- hidden OOC leakage;
- expensive cognition with no consequence;
- test cleanup contaminating later network play.

### FIX AND RETEST

Correct defects before declaring limitations.

Run the entire regression suite again.

### PLAY

Use the real telnet path.

Do not substitute direct function calls for all player-facing verification.

If a feature is meant to be discoverable through ordinary verbs, test those verbs.

### REVIEW

Ask whether the final behavior still matches the core doctrine:

- persistent world state;
- shared reality;
- time continues;
- no forced markers;
- consequences outlive individuals;
- knowledge and truth are distinct;
- ordinary life dominates anomaly;
- low compute when unobserved;
- real multiplayer divergence without private copies of the world.

### MERGE

Use a dedicated branch and PR.

Do not merge merely because the code looks correct.

Before merge:

- verify current `main` has not moved incompatibly;
- ensure exact PR head is green;
- rebase or reconcile if needed;
- preserve concurrent work.

After merge:

- verify the actual merged `main` commit;
- run the release gate again when workflow support exists;
- never claim the item complete from branch CI alone.

## Git and concurrency discipline

Other agents or developers may update `main` while you work.

Before beginning a new slice, fetch current `main`.

Before opening or merging a PR, fetch current `main` again.

If `main` moved:

- inspect the delta;
- do not overwrite it;
- adapt your branch;
- reuse new systems when possible;
- retest integrations.

Do not delete or replace another developer's work merely to simplify your branch.

Closed or superseded PRs are historical evidence, not instructions.

## User update cadence

The user wants to proceed through the list one item at a time.

After each completed and verified item:

- state what was implemented;
- name the exact merged `main` commit;
- name the relevant Actions run if available;
- explain any defects CI caught and how they were fixed;
- distinguish framework completion from launch-content completion;
- identify the next backlog item;
- continue when the user asks.

If one item is very small and naturally shares the same dependency boundary, two may be completed together, but do not turn a request for incremental work into a giant unreviewable rewrite.

## Documentation discipline

Update:

- `README.md` when player-visible capability changes;
- `design-decisions.md` when architecture or doctrine changes;
- `spike/BUILD_NOTES.md` when executable contracts and regression gates change;
- `files/new-arrivals-guide-v0.2.md` when live player commands change.

Do not let docs promise features that the game does not actually support.

Do not silently edit canon merely to make code easier.

## Style and content constraints

Use no em dash in project-authored prose.

Preserve period-appropriate language.

Do not make NPC dialogue generically "AI literary."

Run the NPC prose rubric where NPC-spoken lines change.

Color must never carry meaning alone.

Do not spam announcements.

Parser synonyms and abbreviations should improve before launch.

Staff actions must remain logged, human-reviewed, appealable, and boring.

Accessibility and low-staff operation are launch concerns, not post-launch polish.

## Definition of done for the entire takeover

Do not stop because the architectures exist.

The project is finished only when:

- the authoritative production backlog has been implemented or explicitly closed with a repository decision;
- launch inventory targets are met through data-driven content and reusable systems;
- callings and interdependence are real mechanics;
- economy, procurement, and crafting are real mechanics;
- player-generated requests and community projects work;
- retirement/death has persistent social and institutional consequences;
- accepted content banks are actually reachable in play;
- major NPCs have persistent arcs without becoming load-bearing;
- human and AI players use the same in-world rules;
- the world remains coherent across long offline periods;
- restart does not erase or reroll persistent truth;
- tests cover clean build, persistent rebuild, network play, restart, and long-run behavior;
- the game remains playable when no staff member is actively DMing;
- the launch acceptance tests in Section 7 pass;
- the user can enter with no plan, notice change, hear multiple leads, choose an activity, involve other people, miss something because time passed, create a persistent consequence, leave, return later, and find a world that remembers.

Do not declare completion while large backlog sections exist only as prose.

Do not declare completion while launch target counts are still represented only by accepted markdown banks that the runtime cannot surface.

Do not declare completion while core progression or interdependence is still hypothetical.

Keep working through the authoritative list one production item at a time.

# First action for the takeover instance

Immediately:

1. Fetch and inspect current `main`.
2. Read the World Bible, production handoff, generation packet, recent design decisions, recent build notes, and current regression harness.
3. Run or inspect the current clean-checkout regression state before modifying code.
4. Produce a compact dependency/status matrix for the remaining backlog.
5. Inspect PR #15 before starting new Private Mysteries code. It already contains a candidate implementation but was based on an older `main` and was non-mergeable when this handoff was refreshed.
6. If PR #15 remains relevant, reconcile or transplant it onto current `main`, preserve newer work, run the full regression suite, and complete Section 3.21 from that reconciled foundation rather than writing a duplicate implementation.
7. If PR #15 has already been superseded or current `main` already contains Private Mysteries, identify the next unresolved dependency from the repository.
8. Continue the loop without rebuilding systems that already exist.

The repository is the source of truth.
