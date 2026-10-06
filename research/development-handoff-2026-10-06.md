# Frankenstein Village Development Handoff

Date: 2026-10-06

Repository: https://github.com/Azimn/frankenstein-village

This document is the current production continuity checkpoint. It replaces the earlier October 6 takeover state that described PR #15 as unresolved. Always fetch the actual current `main` before development. If this handoff conflicts with newer repository state, the repository wins.

## Exact verified checkpoint

The production `main` at this checkpoint is:

`ff52e2a7fa83fdff8a4684ac6cd597732adca5e9`

This is the merge commit for PR #18, `Preserve incompatible Chronicle accounts`.

The merged-main clean-checkout release run is:

`37487830021`

Result:

`SUCCESS`

The release job is:

`112352422550`

The verified log contains `WORLD_ASSERTIONS_GREEN`, `TELNET_PLAYTHROUGH_GREEN`, post-restart persistence markers, and `ALL FRANKENSTEIN VILLAGE REGRESSIONS GREEN`. The same log contains no `Traceback` and no `AssertionError`.

There were no open pull requests when this checkpoint was written.

Do not assume these facts remain current. Fetch `main`, open pull requests, and recent Actions runs before making the next change.

## Authority and precedence

The authority order remains unchanged. `files/frankenstein-village-world-bible-v0.2.md` controls canon, setting, unresolved questions, world rules, tone, and launch constraints. `files/frankenstein-village-quest-handoff-v0.3.md` controls the production backlog, content families, implementation expectations, calling packs, inventory targets, and acceptance tests. `files/quest-generation-packet-v0.1.md` controls formal content-generation rules and quotas. Accepted content banks define approved production material. `design-decisions.md` records settled architecture and doctrine. `spike/BUILD_NOTES.md` records executable contracts and regression expectations. Live code and tests show what actually exists.

When code conflicts with settled canon or an accepted repository decision, fix the implementation. Do not silently rewrite canon to make implementation easier. Do not rely on chat memory when the repository can answer the question.

## Governing engineering loop

Continue using:

`INSPECT -> MODEL -> IMPLEMENT -> TEST -> SIMULATE -> BREAK -> FIX -> RETEST -> PLAY -> REVIEW -> MERGE -> VERIFY MAIN -> REPEAT`

A production family is not complete because a framework, registry, interface, or happy-path test exists. A slice is complete only when it is executable through the real game interface, survives restart where persistence applies, preserves prior accepted behavior, and passes the exact-head release gate.

The full clean-checkout acceptance command remains:

`python3.12 spike/tests/run_all.py`

The release gate includes fresh bootstrap, idempotent world build, runtime assertions, real Evennia server startup, real telnet interaction, shutdown, restart, and post-restart persistence verification.

## Project doctrine

Frankenstein Village is a persistent Evennia text world for human and AI players. The server hosts the place rather than continuously simulating dozens of expensive thinking agents.

The governing principle remains:

`CONTINUITY IS ALWAYS ACTIVE. COGNITION IS ACTIVATED ONLY WHEN REQUIRED.`

Persist locations, schedules, households, genealogy, relationships, beliefs, evidence, rumors, public records, commitments, possessions, injuries, institutions, economic consequences, events, historical traces, deadlines, altered locations, player-specific knowledge, and NPC-specific memory where those facts can matter later. Do not continuously generate internal monologues, decorative conversations, invisible animation, or psychological state with no later consequence.

Preserve the 1890s European Gothic setting, mystery-over-horror balance, persistent world, no player wipes, OOC human/AI disclosure, no IC human/AI markers, no conventional level or XP progression, social and institutional callings, no punishment for player absence, continuing world time, provenance-bearing rumors, fallible Harbinger reporting, provenance-first Chronicle records, non-load-bearing mortal NPCs, unresolved canon mysteries, ordinary life outweighing anomaly, shared IC rules for humans and AIs, and text-first systemic design.

## Completed production work immediately before this checkpoint

### Private Mysteries, Section 3.21

PR #15 was not discarded or duplicated. Its implementation was reconciled against newer `main`, repaired, retested, merged, and then verified again on merged `main`.

The critical regression in the old PR was a telnet test that attempted to disclose a private rumor to Magda when her real schedule placed her elsewhere. The game correctly rejected the interaction. The test was repaired to use Bram, whose tavernkeeper role makes his presence deterministic for that path.

The reconciled candidate head was `c232b6923bbabd00ce6c6ad8ca5d3fd1caf58e9b`. Exact-head Actions run `37482346219` succeeded. PR #15 merged as `eb8cb95e9961d05c88b3f3ea2c069572afe068da`. Merged-main Actions run `37482686932` also succeeded.

Private Mysteries now supports mask-specific private thread state, private rumor provenance, deliberate disclosure bookkeeping, the `secrets` / `private` player memory aid, real telnet disclosure, and restart persistence. Disclosure shares knowledge without transferring private-thread ownership. Private mystery existence does not automatically enter the public rumor pool.

### Chronicler content, Section 3.23, Two Versions Survive

PR #18 implemented the accepted `TWO VERSIONS SURVIVE` case on the existing public-record substrate rather than creating a second quest engine.

Distinct signed depositions concerning the same rumor root now produce one persistent Chronicle disagreement record. The disagreement itself can become an institutional fact without selecting one underlying claim as truth. The record uses `claim_status = "documented_disagreement"`, retains rumor and deposition provenance, preserves source masks and claims, and explicitly states that the archive does not choose a verified version.

Later distinct versions append provenance-bearing annotations rather than silently rewriting the original disagreement text. Repeated copies of an already represented claim do not create duplicate disagreement records.

The player-facing command is:

`chronicle compare R<number>`

It renders all currently preserved distinct versions with count-neutral wording and states that no version is certified as truth.

Upgrade safety is implemented. `reconcile_chronicle_disagreements()` performs an idempotent global backfill during world build for persistent worlds that already contain incompatible depositions. `reconcile_chronicle_disagreement(rumor_id)` provides a single-root lazy recovery path for player comparison without running the global migration on every command.

Regression coverage uses naturally divergent versions of the canon well rumor held by Old Vasile, János, and Magda. It verifies first and second depositions, third-version annotation, one stable disagreement record, migration from persisted depositions with no derived record, idempotence, single-root lazy recovery, real telnet comparison showing all three witnesses, and restart persistence.

PR #18 went through repeated exact-head release and review loops. The first review found that old persisted depositions were not backfilled until a new deposition arrived. That was fixed. The second review found that player comparison invoked the global migration and could scale poorly with archive size. That was fixed by single-root lazy reconciliation. The third review found player-facing wording that still said `Two versions survive` after a third version existed. That was fixed with count-neutral wording and stronger telnet coverage.

The final PR head was:

`b23ad03dc727b54d370e360c5597df91bfcae538`

Exact-head Actions run:

`37487303392`

Result:

`SUCCESS`

The final automated review on that exact head reported no major issues.

PR #18 merged as:

`ff52e2a7fa83fdff8a4684ac6cd597732adca5e9`

The merged-main release run `37487830021` succeeded and is the authoritative verification for this checkpoint.

## Current live production foundations

The live game remains under `spike/fvillage/`. Existing production foundations include the Inn Between OOC hub and private rooms, village square, Blood of the Vine, St. Lazarus Church, Lamp Shop, coin economy and consumables, hunger and drunkenness, authored social verbs, Room Six, moderation lifecycle, account-level human/AI disclosure, the persistent resident population, structured rumor provenance, canonical event ledger, Harbinger and Chronicle public memory, shared situations, timed windows, recurring public calendar, weighted random incidents, seasonal chapters, village-scale server events, public mysteries, and private mysteries.

The production resident system remains approximately 36 named residents with stable identity, genealogy, households, occupations, schedules, logical locations, event-aware fallbacks, player-specific relationship state, persistent facts, engagement-based simulation resolution, and low-cost automaton behavior.

Do not replace the resident population with one continuously thinking LLM agent per resident.

## Important implementation lessons that remain binding

Evennia persistent Attribute values may use wrapper mappings, so do not assume literal `dict` identity when mapping semantics are sufficient.

Event IDs must remain monotonic. Never rewind allocators during QA cleanup because identity reuse can make stale flags appear to reference a new event.

Synthetic QA cleanup must be symmetrical. If a synthetic canonical event is removed, remove its synthetic derived flags, rumor records, publication artifacts, overlays, and other test state as appropriate.

Authored NPC schedules are real. Do not make a particular NPC physically load-bearing in network tests unless their schedule guarantees presence.

Background-resident logical location and physical Offstage location are distinct. Social co-location for population-managed residents must use logical location.

Public-record provenance must remain visible in player-facing prose, not only hidden metadata.

Temporary room text is projection from persistent state. It must be reconstructable after restart.

Tests should validate contractual behavior rather than incidental implementation choices.

## Backlog position

Section 3.21 now has a real Private Mysteries production foundation and vertical slice. Section 3.23 now includes the production `Two Versions Survive` Chronicle case in addition to the pre-existing deposition, annotation, archive, and missing-record foundations.

Do not interpret those statements as launch-density completion. The production handoff's much larger family and inventory targets still apply.

The repository's documented dependency order says to continue Harbinger and Chronicle content frameworks where the existing publication substrate can support them cheaply before moving to the systemic object/tag foundation, calling/interdependence core, economy, procurement, crafting, travel/watch/cartography/collection, puzzles, broader failure and delay patterns, player-generated requests, community projects, lifecycle content, and large-scale family expansion.

The immediate next production task is therefore to inspect the current Section 3.22 Harbinger and Section 3.23 Chronicler accepted cases against the now-merged publication substrate and choose the next genuinely missing playable vertical slice. Do not assume a particular candidate from this handoff. Re-read current `main`, `files/frankenstein-village-quest-handoff-v0.3.md`, `spike/fvillage/world/publications.py`, the Chronicle and Harbinger command surface, current tests, and recent design decisions. Select the smallest dependency-clean case that closes an accepted backlog item without inventing premature calling permissions or a duplicate state machine.

Likely candidates should be evaluated, not assumed. Harbinger cases such as `The Correction` may already have significant substrate support through correction APIs. Chronicler cases such as `The Refused Entry` or `The Battle Over One Sentence` may expose a genuinely missing institutional behavior. The repository inspection must decide.

After the Harbinger/Chronicle content-framework pass is sufficiently complete, the next major dependency is the minimal systemic object/property/tag vertical slice described in `design-decisions.md`, followed by the persistent calling/interdependence core.

## Remaining launch scale

The launch inventory targets in Section 7 remain the final bar. Existing accepted markdown banks are not equivalent to runtime reachability. Continue favoring data-driven definitions, parameterized systems, shared state machines, accepted content banks, world-state eligibility, reusable aftermath handlers, and provenance-aware generation over hand-coded duplicate classes.

Large families remain incomplete at launch scale, including newcomer, civic, rumor, small and long mysteries, expeditions, group and social investigations, factions, cross-faction conflict, debt, bonds, Hyde, rival investigator content, economic content, procurement, crafting commissions, travel, watch, cartography, collections, puzzles, moral choice, failure, delay, repeat-visit states, player-generated requests, community projects, retirement and death, major NPC arcs, hidden discoveries, legendary discoveries, and AI-compatible work.

Callings remain a major foundation gap unless a fresh repository inspection proves otherwise. The intended callings are social and institutional capability structures rather than combat classes or conventional levels. The project still needs a persistent architecture capable of supporting interdependence, apprenticeship, rank, mastery limits, respecialization history, institutional responsibilities, authored calling quests, and repeatable professional jobs.

## Concurrency discipline

Before every new slice, fetch current `main`, inspect open pull requests, and inspect recent Actions runs. If another developer has advanced the repository, reconcile rather than overwrite. Closed or superseded branches are historical evidence, not instructions.

Before merge, verify current `main` again and require exact-head CI. After merge, verify the actual merged `main` commit and its release workflow. Never claim completion from branch CI alone.

## Documentation discipline

Update `README.md` for player-visible capability, `design-decisions.md` for architectural doctrine, `spike/BUILD_NOTES.md` for executable contracts and regression gates, and `files/new-arrivals-guide-v0.2.md` for live player commands.

Do not let documentation promise behavior that is not executable.

## Conversation context checkpoint protocol

Long production sessions must not rely on one chat indefinitely. There is no trustworthy exact percentage for remaining model context, so do not invent one.

Use a practical traffic-light protocol. Normal work is GREEN. Move to YELLOW after several large repository inspections, long test logs, repeated implementation and review loops, or multiple major merge boundaries. At YELLOW, prepare an exact continuity snapshot. Move to RED, also called `HANDOFF NOW`, when context has been compacted, the session has crossed several large production slices, or a clean verified merge boundary is available and further work would risk losing precision.

A RED checkpoint should preserve the exact repository, `main` SHA, active branch and PR if any, exact CI run and result, completed slice, defects found and fixed, open work, next dependency, and key design decisions. Then continue in a fresh conversation by instructing the next instance to inspect current `main` first and use this repository handoff.

This document is itself such a RED checkpoint.

## First action for the next production instance

Fetch current `main` and confirm whether it is still `ff52e2a7fa83fdff8a4684ac6cd597732adca5e9` or a descendant. Inspect open PRs and recent Actions runs. Read the authority files and recent Build Notes. Confirm that Private Mysteries and Chronicle disagreement preservation are present. Then inspect Section 3.22 and Section 3.23 against the current publication code and select the next missing playable content-framework slice.

Do not rebuild Private Mysteries.

Do not rebuild Chronicle disagreement preservation.

Do not skip directly to a later subsystem merely because it is more interesting.

Continue one production item at a time through the authoritative backlog.
