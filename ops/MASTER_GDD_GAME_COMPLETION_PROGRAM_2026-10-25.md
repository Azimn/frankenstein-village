# Frankenstein Village 1.0 — Master GDD development program

**Status:** Operational planning draft dated 2026-10-25. This is the **game-completion** production plan, not deployment authorization or a World Bible amendment.  
**Controlling reference:** [Master GDD searchable review text](../docs/FRANKENSTEIN_VILLAGE_MASTER_GDD_REVIEW_2026-10-25.md), especially §§2, 5–6, 8–10, 12–15, 17–23 and Appendices A–C. The original 31-page review-draft PDF remains layout-authoritative.  
**Repository baseline:** main `9b16f73f1acec60cd7803476caaa744a5be4a42f` before subsequent PR integration.  
**Integration policy:** No new repository, no new quest engine, no redesign of already implemented Evennia world systems; use approved systems and profession contracts. No automatic merges. No schedules, staffing, hosting costs or commercial assumptions invented.

## Decision: what "finish the game" means

**The milestone is a complete, richly playable 1.0 game build, not an invited-alpha host.** Maintain the full GDD §15/World handoff §7 content goals. All ten Callings must offer meaningful, varied choices and real connected professional lives. Author and test actual world effects, not merely definitions or command aliases. Ordinary village life and third-place social play are intrinsically valuable even when no quest is active. Rare supernatural events matter by contrast.

Until measured, code and documents represent **source claims**, not proof of fun or finished systems. `V/S/D/C` pair classifications are **starting evidence only**, never readiness percentages.

We distinguish two independent decisions:
- **G-Complete:** fully authored, integrated, balanced, tested, polished game on reproducible local build; no purchased host needed.
- **Public Shipping:** only after G-Complete, approve external service, safety, licensing, operations and rights under GDD §22; do not let a server subscription dictate game scope.

## The nonnegotiable system contract (GDD §§5–6 and 18)

Reuse one authoritative village clock; existing Evennia objects/mechanic tags; hearth, soup, market, workshop, clinic, courier, stage, survey and bridge state; situation/incident state; event ledger; Commons/Chronicle/Harbinger; player biography/apprenticeships; local NPC schedules. New profession behaviors are **methods applied to existing state**, never a second store of “truth,” stock, money, patient condition, reputation or private accounts.

Loop: live need -> legitimate observation -> distinct role choice -> verify authority/location/material/time/consent -> exact physical action -> canonical state + provenance -> bounded eyewitness and dissemination -> success/partial/failed/finished-by-others state -> credible next opportunity. A zero-concurrency player can pursue an authentic solo route, with bounded and sourced NPC baseline service only where authorized.

**Keeper locks:** Mystic B1 Guild authority, B2 reading truth-value, B3 Guild venue, B4 ritual/study failure effects remain reserved. No capabilities depending on them may be implemented by inference. Book conflicts are registered and escalated, not silently resolved.

## Dependency-managed work packages (GDD §21 A–F)

The first pass is **graph-first**, not role-by-role. Each package selects an existing shared world object or authoritative service, then builds diverse Calling contributions around it. Existing chains: Merchant–Smith–Chronicler market standards, Innkeep–Healer care, Healer–Chronicler health warning and Merchant–Innkeep soup supply. Put genuinely independent role decisions into those stories; do not mark “three Callings complete” when only one scenario works.

| ID | Phase | Work package | Prerequisites | Required evidence |
| --- | --- | --- | --- | --- |
| FV-G00 | Setup | Pin design authority and reconcile open PRs | None | No duplicate changes, higher-authority World Bible conflicts marked for keeper, fresh exact-commit CI after eventual integration. |
| FV-G01 | A | Executable game-content and 45-edge coverage register | FV-G00 | Live discoverability not inferred from manuscript counts; all unknown states explicitly unverified. |
| FV-G02 | A | Verify common action/evidence architecture in place | FV-G00 | Ordinary account tests and §19 T-01–T-16 baseline gap report, including races and idempotency. |
| FV-G03 | A | Verify bounded Mystic phenomenon without canon expansion | FV-G00, FV-G02 | Two observers agree on objective physical change; absent mask has no firsthand observation; B1–B4 remain BLOCKED. |
| FV-G04 | B | Shared staffed work and care continuity | FV-G01, FV-G02 | Two distinct repeatable decisions, cross-role optional assistance, depleted/failure/return routes, exact state change and local restart. |
| FV-G05 | C | Craft, trade and accountable public records | FV-G01, FV-G02 | Exactly-once material custody, real installed object change, fair actor guards, content choices, correct notice-versus-truth separation. |
| FV-G06 | D | Distinct field, safety and investigation gameplay | FV-G01, FV-G02 | One physical route may produce different justified professional reports; no cloned world truth, valid solo/late paths, conservation of courier/repair items. |
| FV-G07 | E | Culture, social leisure and rare uncanniness | FV-G01, FV-G02, FV-G03 | Quiet-room path valuable; no fabricated attendees; witnesses limited; no undocumented ritual powers or random fantasy truth. |
| FV-G08 | F | Full Calling-authored jobs, quests and progression | FV-G04, FV-G05, FV-G06, FV-G07 | Per-item cards with source, meaningful branch, cost, actual change, reentry, uncoached discovery; aliases and trivial recipe variants do not count. |
| FV-G09 | F | World, mysteries, event and NPC content density | FV-G01, FV-G04, FV-G05, FV-G06, FV-G07 | Complete inventory statuses and player-reachable results. Faction count and major NPC roster must come from controlling Bible, not guessed. |
| FV-G10 | F | Coherence, UX and real-player engagement polish | FV-G08, FV-G09 | Uncoached normal-client first evening, short/full session, return and voluntary leisure observations; no invisible dead ends, no known major usability blockers. |
| FV-G11 | F | 45-edge, 16 negative-case and full-game regression qualification | FV-G08, FV-G09, FV-G10 | Per-edge signed dossiers: distinct role actions, finite objects, NPC/solo path, witnesses, idempotency, UI parity, real restart and uncoached quality. |
| FV-G12 | Game complete | Freeze a game-complete 1.0 candidate | FV-G11 | No known critical/major gameplay defects, unchanged World Bible authority, complete §15 content evidence and meaningful player return experience. |
| FV-G13 | Post game-complete | Public operations and shipping approval (separate) | FV-G12 | GDD §22/Appendix C decisions documented and independently tested; never substitute server go-live for game completion. |

### Deliverables and acceptance by package

#### FV-G00: Pin design authority and reconcile open PRs

**Depends on:** none.

**Deliver:** Exact SHA authority/conflict register; select surviving #89/#90 and #91/#92 code paths; review #93/#94 as subordinate sources; retain draft status until separately approved.

**Exit test:** No duplicate changes, higher-authority World Bible conflicts marked for keeper, fresh exact-commit CI after eventual integration.

**State:** PLANNED; no task is complete merely because this document was committed.

#### FV-G01: Executable game-content and 45-edge coverage register

**Depends on:** FV-G00.

**Deliver:** 21-family section 15 inventory and all 10 Calling / 45 edge evidence cards, with source file + command + room + owner + canonical transition + restart/UX proof.

**Exit test:** Live discoverability not inferred from manuscript counts; all unknown states explicitly unverified.

**State:** PLANNED; no task is complete merely because this document was committed.

#### FV-G02: Verify common action/evidence architecture in place

**Depends on:** FV-G00.

**Deliver:** Map existing Evennia CmdSets, physical inventory, clock, situation, ledger, Commons, NPC memory and job systems; test their existing contracts; no competing stores.

**Exit test:** Ordinary account tests and §19 T-01–T-16 baseline gap report, including races and idempotency.

**State:** PLANNED; no task is complete merely because this document was committed.

#### FV-G03: Verify bounded Mystic phenomenon without canon expansion

**Depends on:** FV-G00, FV-G02.

**Deliver:** Inspect source-reported Harcourt/Dobre, current rare churchyard inscription, presence/observation and method record. Ledger, restart and non-witness claims checked.

**Exit test:** Two observers agree on objective physical change; absent mask has no firsthand observation; B1–B4 remain BLOCKED.

**State:** PLANNED; no task is complete merely because this document was committed.

#### FV-G04: Shared staffed work and care continuity

**Depends on:** FV-G01, FV-G02.

**Deliver:** Extend existing Tavern hearth/soup, Innkeep shared services, Healer clinic patient state, guest/referral demand and limited NPC baseline. Consume authentic stock, preserve privacy and status.

**Exit test:** Two distinct repeatable decisions, cross-role optional assistance, depleted/failure/return routes, exact state change and local restart.

**State:** PLANNED; no task is complete merely because this document was committed.

#### FV-G05: Craft, trade and accountable public records

**Depends on:** FV-G01, FV-G02.

**Deliver:** Extend real Merchant supplies, Smith Market Workshop and existing Chronicler source/attestation. Signed orders, repairs, material quality, refunds/corrections and contested claims.

**Exit test:** Exactly-once material custody, real installed object change, fair actor guards, content choices, correct notice-versus-truth separation.

**State:** PLANNED; no task is complete merely because this document was committed.

#### FV-G06: Distinct field, safety and investigation gameplay

**Depends on:** FV-G01, FV-G02.

**Deliver:** Wanderer passability/logistics vs Hound threat/protection vs Detective provenance/inference; reuse route survey, bridge, ferry post, physical clues; include Healer/Smith/Merchant support.

**Exit test:** One physical route may produce different justified professional reports; no cloned world truth, valid solo/late paths, conservation of courier/repair items.

**State:** PLANNED; no task is complete merely because this document was committed.

#### FV-G07: Culture, social leisure and rare uncanniness

**Depends on:** FV-G01, FV-G02, FV-G03.

**Deliver:** Performer rehearsal/booked audience/witnessed memory and Tavern demand, purposeful voluntary games, documented Gothic rarity; Mystic only approved observation until keeper rulings.

**Exit test:** Quiet-room path valuable; no fabricated attendees; witnesses limited; no undocumented ritual powers or random fantasy truth.

**State:** PLANNED; no task is complete merely because this document was committed.

#### FV-G08: Full Calling-authored jobs, quests and progression

**Depends on:** FV-G04, FV-G05, FV-G06, FV-G07.

**Deliver:** All ten roles reach §15: 6 distinct authored quests each (≥60) and 8–12 distinct renewable professional loops each (80–120), four focuses as design organization; valid Apprentice/Master institutional paths.

**Exit test:** Per-item cards with source, meaningful branch, cost, actual change, reentry, uncoached discovery; aliases and trivial recipe variants do not count.

**State:** PLANNED; no task is complete merely because this document was committed.

#### FV-G09: World, mysteries, event and NPC content density

**Depends on:** FV-G01, FV-G04, FV-G05, FV-G06, FV-G07.

**Deliver:** Reach other §15 families: newcomer paths, small/major mysteries, civic/faction/conflicts, expedition/social/group encounters, random/timed/world incidents, ambient/rumor/Harbinger, projects, discoveries, request templates and NPC arcs.

**Exit test:** Complete inventory statuses and player-reachable results. Faction count and major NPC roster must come from controlling Bible, not guessed.

**State:** PLANNED; no task is complete merely because this document was committed.

#### FV-G10: Coherence, UX and real-player engagement polish

**Depends on:** FV-G08, FV-G09.

**Deliver:** Onboarding, help, action feedback, credible Bram/resident recognition, OOC/IC separation, consent, equal human/AI client affordances, Tarn needs with relief, agency and meaningful failure recovery.

**Exit test:** Uncoached normal-client first evening, short/full session, return and voluntary leisure observations; no invisible dead ends, no known major usability blockers.

**State:** PLANNED; no task is complete merely because this document was committed.

#### FV-G11: 45-edge, 16 negative-case and full-game regression qualification

**Depends on:** FV-G08, FV-G09, FV-G10.

**Deliver:** Source-linked evidence for 45 pairwise collaborations; rerun six V chains, verify six S, 24 D, and only authorized portions of nine C. Run all §19 T-01–T-16 negative scenarios and local multi-account/restart tests.

**Exit test:** Per-edge signed dossiers: distinct role actions, finite objects, NPC/solo path, witnesses, idempotency, UI parity, real restart and uncoached quality.

**State:** PLANNED; no task is complete merely because this document was committed.

#### FV-G12: Freeze a game-complete 1.0 candidate

**Depends on:** FV-G11.

**Deliver:** Lock exact reproducible main SHA, player-facing feature inventory, successful regression, known-defect register and verified content count; reviewer certifies GAME design and execution, not hosting.

**Exit test:** No known critical/major gameplay defects, unchanged World Bible authority, complete §15 content evidence and meaningful player return experience.

**State:** PLANNED; no task is complete merely because this document was committed.

#### FV-G13: Public operations and shipping approval (separate)

**Depends on:** FV-G12.

**Deliver:** After the game is complete, choose real platform/host/operator; prove privacy, rights/assets, moderation, external access, restore, concurrency and patch/rollback for intended public release.

**Exit test:** GDD §22/Appendix C decisions documented and independently tested; never substitute server go-live for game completion.

**State:** PLANNED; no task is complete merely because this document was committed.


## Whole-game §15 targets (counts do not assert implementation)

| Source family | Authoritative full-game target |
| --- | ---: |
| Newcomer scenarios | 12 |
| Small mysteries | 30 |
| Major mysteries | 10–12 |
| Civic quests | 30 |
| Calling-specific authored quests | 6 × 10 = 60 minimum |
| Calling repeatable professional jobs | 8–12 × 10 = 80–120 distinct loops |
| Faction quests | 8–10 per canon faction, denominator requires Bible review |
| Cross-faction conflicts | 20 |
| Expedition locations | 10–12 |
| Social expeditions | 12 |
| Group investigations | 12 |
| Timed incidents | 30 |
| Random incident templates | 75+ |
| Server-wide event frameworks | 10 |
| Community projects | 6+ |
| Hidden discoveries | 50+ |
| Major NPC arcs | 3–5 per major NPC, roster requires canon verification |
| Rumor seeds | 250+ |
| Ambient room events | 300+ |
| Harbinger templates | 50+ |
| Player-request templates | 30+ |

Only count an item once it has a natural in-world discovery path, a nontrivial choice, an authoritative consequential action, failed/late/return branches and restart evidence. Track **manuscript -> declaration -> initialized -> discovered ordinary client -> changed authoritative world -> post-restart -> uncoached player found**. Publish both count and evidence tier, never a meaningless single completion percentage.

## Per-role definition of done (GDD §8.11 and §19.3)

For **Innkeep, Chronicler, Smith, Healer, Merchant, Wanderer, Performer, Detective, Hound and Mystic**, capture all: first job discoverable by a normal account; at least two **different** short loops; long responsibility; four proposed specialty groupings understood without inventing new ranks; an approved Apprentice/Master route and consensual apprenticeship; optional neighbor contribution and valid solo alternative; finite resources; refusal, loss, stock-empty and someone-else-finished aftermath; connected social/leisure actions; a real process restart; uncoached human and naive AI/Calibos research not spoiled by code exposure; §15 authored quota.

Hound must not merely reuse Wanderer's exact survey as its sole game loop; investigate **threat/protection vs passability/logistics** over the same route state. Chronicler reporting never sets world truth; Mystic study does not certify a ghost or reading; performers never manufacture absent audiences.

## 45-edge contract ledger (GDD §§9–10 and §19.2)

**Working evidence register:** [`MASTER_GDD_45_EDGE_REGISTER_2026-10-25.json`](MASTER_GDD_45_EDGE_REGISTER_2026-10-25.json) contains all 45 source-extracted numbered pair contracts. Every entry begins **unverified** and exposes fields for normal-client discovery, two distinct methods, source owner, finite guard, solo fallback, state change, negative cases, two-account trace, restart proof and uninformed-player feedback. Update a record only from evidence, not prose.

Every distinct pair gets its own **evidence dossier** keyed by the PDF's numbered map. The baseline classification is **V6, S6, D24, C9**. Be careful with the PDF's explicit earlier-label correction: **V3 = Innkeep–Healer, V4 = Innkeep–Merchant**. The earlier draft's opposite example was a cross-reference typo. Never blindly import pair IDs from earlier PR #94 without checking this correction.

Evidence fields: two real professions; actual location/item/encounter; source-of-truth module; two distinct professional methods; material cost or bounded time; limited witnesses/consent; co-op and zero-population fallback; conflicting simultaneous action; completed/expired/shortage/restart behavior; authorial source; exact commit and automated tests; uncoached player understanding. A power-dependent C edge cannot ship until keeper approves its canon.

## QA program (GDD §19.4), all 16 scenarios must have trace IDs

- T-01 interrupted finite item handoff and exactly one custodian.
- T-02 simultaneous reservations of last unit (one succeeds).
- T-03 completed lamp cannot be “repaired” twice.
- T-04 market hold across offline clock progression does not deadlock.
- T-05 unsupported article remains a claim, not physical truth.
- T-06 non-witness cannot remember a missed performance firsthand.
- T-07 Wanderer passability and Hound threat interpretation differ on one road.
- T-08 healer assessment cannot expose unauthorized patient record.
- T-09 any bodily drive has viable relief even when one source is exhausted.
- T-10 identical relevant permissions/outcomes for human and external-agent clients.
- T-11 shared rare inscription witness sees consistent physical evidence; absent third party does not.
- T-12 unattended scheduled event resolves without forged player work.
- T-13 two-account cancel/complete race has one terminal result.
- T-14 leaving apprenticeship respects consent and persistent biography.
- T-15 corrected article keeps source-limited audit/history and recipient effects.
- T-16 interrupted multi-step responsibility has truthful pending/resumed/expired/completed-by-others outcomes.

Technical tests alone don't certify experience. Pair executed unit/telnet, two-account and real local-restart evidence with uncoached human and naive AI play BEFORE revealing source. Track surprise and player interpretation through the emic-first method. Do not invent launch thresholds (latency, retention, concurrent capacity) before measurement.

## Production practice: content cards, approvals and no wheel reinvention

Use Appendix A of the GDD as the **standard work item**: content ID, role(s), source owner, canonical clearance, live trigger, exposed first verb, choice and cost, authoritative before/after, witness, branching/negative prose, interruption, NPC fallback, idempotency, test links, player reports and reviewer. Implement using appropriate current handler/service, not a new global quest layer.

**No scope laundering:** a nice manual, 45 designed overlaps, 250 rumor manuscript entries or green unit suite is not 1.0. Conversely, *existing working systems stay in place* unless proof identifies a concrete defect.

## Next immediate, reviewable execution

1. Freeze the exact source/canon/PR reconciliation map. GDD PDF's “repository uninspected” caveat must be upgraded with actual linked source evidence; #89/#90 and #91/#92 duplication handled separately and only with approval. PR #93 audit and #94 pair design remain unmerged inputs, not conflicts to solve by creating another engine.
2. Generate a **source-owner and discoverable gameplay matrix** for the 45 pair IDs and 21 §15 content families. Distinguish inventory definition from playable mechanic. Test baseline chain V3, V4, V10–V12 and V19 with real states before selecting next implementation.
3. Build one cross-role scenario at a time through the **existing** authoritative resource owners, selected by the reach and reuse of its shared state. Every role enters the whole design; no arbitrarily isolated career silo.
4. Run GDD T-01–T-16 and role-by-role negative variants continuously. Author more genuine content and polish over the entire village using complete content cards.
5. Once §15 and evidence signoffs pass, freeze **game complete**. Only then begin externally hosted production qualification under GDD §22.

## Recorded decisions needed, not implied approvals

- Canon: B1–B4 Mystic matters and any other World Bible conflicts.
- Product: confirm full-1.0 scope; exact client/AI pair onboarding and release definition.
- Professions: authored Master promotion conditions and specialty access, consistent with existing Apprentice/Master.
- Economy: nontrivial pricing, wages, credit and owner rights beyond existing state.
- Experience: any concrete future visual/audio mandates (currently optional); release targets after real player research.
- Post-game: licensing, moderation, age/privacy, actual host and budget, release approvals.
No unresolved choice should stall unrelated authorized ordinary game work.

**Not in scope of this document change:** merges, gameplay-code rewrites, new repositories, live hosting, purchases, new Mystic powers, world-canon edits, or a fabricated certification of launch readiness.
