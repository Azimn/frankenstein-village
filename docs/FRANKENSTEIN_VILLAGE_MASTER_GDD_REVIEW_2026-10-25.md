# Frankenstein Village — Master Game Design Document

**Edition:** Consolidated professional GDD, review draft 1.0 (2026-10-25)  
**Source:** `Frankenstein_Village_Master_GDD_Review_2026-10-25(1).pdf` (31-page user-supplied, formatted PDF)  
**Original PDF SHA-256:** `eaae1b0139de8453a74116b463ada8eacc93822010a665dbfb7976034524b567`  
**Repository base used for source-status descriptions:** `9b16f73f1acec60cd7803476caaa744a5be4a42f`  
**Status:** REVIEW DRAFT; no World Bible amendment, changed canon, executable implementation or launch certification.

> **Fidelity notice:** This repository file is the **complete searchable text extraction** from the uploaded PDF, preserving the page sequence and textual source statements. PDF layout, tables, and diagrams may be less legible as extracted text. Refer to the original 31-page PDF for layout-authoritative tables and page design. **The PDF binary itself was not uploaded via the available text-only GitHub writing connector.** Do not describe this file as a lossless PDF, or this review draft as keeper-approved canon.

> **Source authority:** `hidden_files/design-doctrine.md`, `files/frankenstein-village-world-bible-v0.2.md`, `design-decisions.md`, existing implementation and its observed behavior take priority where conflicting. `V/S/D/C` statuses remain source-reported until verified at current head. Mystic B1–B4 are unresolved.

---

<a id="pdf-page-1"></a>

<!-- Source PDF physical page 1 of 31 -->

FRANKENSTEIN VILLAGE
        Master Game Design Document — Ten Callings and a Living Gothic Village

Edition: Consolidated professional GDD, review draft 1.0
Date: 25 October 2026
Source baseline claimed by supplied design: Azimn/frankenstein-village main
9b16f73f1acec60cd7803476caaa744a5be4a42f
Authority: Design synthesis only; not a World Bible amendment, implementation record, deployment plan, or shipping
certification.
Product: Persistent, socially grounded, text-forward Victorian Gothic village running on an Evennia-based world.
Audience: Design, writing, programming, world operations, QA, accessibility, narrative and launch review.
Read-first control: This document describes intended complete-game design and faithfully labels source-reported
implemented footholds. The repository, exact canon files, code behavior and current servers were not independently inspected
for this edition. Nothing labeled Proposed, Candidate, Blocked or Unverified may be advertised as shipped. Higher-
authority source files prevail over this document.

Document purpose
Describe what makes the game worth returning to, how the ten Callings participate in one persistent simulation, what
player actions do to concrete world state, how lore and testimony remain distinguishable, what content must be authored, and
what evidence must exist before launch. Design breadth is not itself release readiness.

Decision/status key
Approved/source direction: explicitly described as approved in supplied material; confirm against controlling file before
implementation.
Existing (source-reported): code-backed behavior asserted by supplied baseline; not independently rerun.
V: pairwise code-backed multi-role chain with regression claimed; not necessarily fun- or content-complete.
S: shared live substrate, distinct cooperative result unverified.
D: proposed distinct cross-role collaboration.
C: proposed edge involving canon-blocked Mystic powers, though mundane interaction is allowed.
Candidate: reviewable quality target, production practice or UX proposal, not a new canon rule.
Blocked: keeper/World Bible decision required before specification or implementation.

---

<a id="pdf-page-2"></a>

<!-- Source PDF physical page 2 of 31 -->

CONTENTS
1. Executive vision
2. Authority, source hierarchy and creative boundaries
3. Player experience and engagement doctrine
4. The village, cast, narrative and social ontology
5. Universal play, physical actions and authoritative loop
6. Cross-cutting systems: source of truth and design contract
7. Places, occupations and daily availability
8. The ten Callings — playable occupation specifications
9. The complete interdependence graph: all 45 edges
10. All 45 pairwise collaboration contracts
11. Worked multi-Calling scenarios — vertical-slice design packets
12. The onboarding, moment-to-moment UX and discoverability specification
13. Social systems, consent, relationships and progression
14. Mystery and the supernatural
15. Narrative, content and authoring inventory
16. Audiovisual direction and creative production boundaries
17. Economy, pacing, demand and fairness
18. Implementation architecture and integration boundaries
19. QA strategy and acceptance matrix
20. Engagement research, balance and acceptance
21. Production roadmap and dependency-managed slices
22. Shipping policy and readiness gates
23. Design risks, mitigation and unanswered product decisions
24. Reference register, traceability and glossary
Appendix A. Professional job/quest production card
Appendix B. The shared professional flow (review diagram)

Appendix C. Release decision record (to complete before a public launch)

---

<a id="pdf-page-3"></a>

<!-- Source PDF physical page 3 of 31 -->

1. Executive vision
1.1 Vision statement
A persistent Gothic third place where a human and an AI companion can arrive as equals, choose separate lives or
shared evenings, and become recognizable through ordinary useful work, relationships, witnessed accomplishments
and remembered consequences. The village is uncanny, but its beating heart is everyday life: soup, repair, care, maps,
truthful reporting, performances, deliveries, patrols and disputed stories.
Logline: In a Victorian Gothic village that remembers what people actually do, choose one of ten social Callings, help
neighbors through finite shared systems, cultivate a professional history, and encounter rare mysteries without losing the
freedom to have an ordinary evening.

1.2 Why players return
Return value is not a generic daily reward. A delayed repair is installed; a hungry guest recalls the meal; a corrected article
changes an institution’s response; a route warning still matters; a promise is due; an audience remembers the fiddle. The
game should make a player ask “what happened while I was gone?” and “who noticed what I did?” rather than “how
much XP did I farm?”

1.3 Key differentiators
Forgiveness, not scoring: newcomers may be awkward and improve without punitive humiliation.
Accumulating past: world objects, biographies, credible memory and institutional records persist across sessions.
Being witnessed: a performance, service or rescue has witnesses with limited knowledge rather than universal notifications.
Belonging and return recognition: the keeper and local people respond to lived history.
A body with actionable needs: drives create distraction or contextual limitations, not damage; every need has a real relief
route.
Equal human and AI citizenship: ordinary and external agent players share controls, constraints, physical inventory, agency,
privacy and opportunities.
Grounded ambiguity: objective incidents are real, but beliefs, publications, rumors and theories may disagree.
One simulation, ten livelihoods: professional differentiation changes method, authority, exposure, costs and social
consequences, not basic world physics.

1.4 Genre, audience and play structure
Genre: persistent social role-playing/simulation with occupations, civic cooperation, investigation and rare Gothic supernatural
phenomena. Presentation: text-first, place- and object-grounded, via existing Evennia normal commands and supported
clients. Social shape: solo-capable persistent shared world; voluntary sessions together or apart. Target audience stated by
doctrine: human–AI-companion pairs as an early-adopter community, without excluding ordinary players who enter alone.
Platform support, account capacity, commercial packaging and audio delivery remain launch decisions requiring verification.

1.5 Explicit non-goals
Not a class-based combat MMO; not a series of separate quest engines; not an omniscient AI narrator permitted to set truth;
not a housing-ownership prerequisite; not compelled synchronous cooperation; not a game where occult participation is
necessary; not simulated crowds falsely presented as human players; not an XP treadmill; not a copy of copyrighted film
canon beyond the explicit Pretorius exception.

---

<a id="pdf-page-4"></a>

<!-- Source PDF physical page 4 of 31 -->

2. Authority, source hierarchy and creative boundaries
2.1 Source priority
hidden_files/design-doctrine.md — design doctrine including emic measurement, “invent each loop once”, third-place, world
skepticism and equality.
files/frankenstein-village-world-bible-v0.2.md — canon and unanswered canon questions.
design-decisions.md — active Calling, apprenticeship, authoritative event ledger, property model and promotion rules.
docs/TEN_CALLINGS_LIVING_VILLAGE_V1.md — approved ten-Calling direction with proposed specialties.
ops/CALLINGS_SIMULATION_DEPTH_PLAN.md — reuse direction and verified-chain claims.
world/callings.py, world/calling_opportunities.py, object/command/clock/situation/ledger implementations — implementation
evidence.
This GDD — integrative review proposal only.
A conflict must be registered, not silently “resolved” by the GDD. Documented internal status applies only to the 2026-10-25
baseline; later builds require independent audit.

2.2 Canon and adaptation guardrails
Source Shelf public-domain material grounds ordinary canon and generated content. Dr. Septimius Pretorius is the single
explicit film-bridge exception and does not license more adaptation-specific characters or inventions. Gothic beings, the living
Mists, transformations, Jekyll, vampires beneath town and authentic anomalies exist in the world as described by source
direction. They are uncommon in ordinary play. Apparent hauntings may be mundane; seeing an anomaly does not prove an
explanation. The proposed hotel is not the OOC Inn Between.

2.3 Reserved decisions (must stay open)
B1. Guild of Mystics’ actual authority and limits.
B2. Whether divinatory readings have objective prediction/truth value.
B3. Authoritative Guild location/venue and relation to caravan descriptions.
B4. Objective results and failure handling of ritual/study interventions.
No document passage, quest script or social status may preempt these keeper rulings.

2.4 Existing-versus-aspirational discipline
The source describes several working chains and places, but that does not verify density, balance, broad uncoached
discovery, persistence across all failure branches, complete institutional play, all specialties, art/audio, operation or public
launch capacity. Claims must be marked through manuscript → static declaration → initialized → discovered live →
changed authoritative world → persisted after restart → uncoached player-found.




3. Player experience and engagement doctrine
3.1 Emotional arc
Arrive without shame → find a concrete need → choose a personally fitting method → perform real work → receive
local witnessed feedback → see a changed state → discover an unfinished relationship or ambition → return.
Excitement should emerge from uncertainty with legible stakes, not noise or pressure.

3.2 Session design targets (not measured)
Player window                  Intended experience                              Minimum visible proof
~5 minutes                     Notice one relevant neighborhood issue and       Inspect one source object/person/event and

---

<a id="pdf-page-5"></a>

<!-- Source PDF physical page 5 of 31 -->

Player window                  Intended experience                                Minimum visible proof
                               choose among legitimate actions                    understand an available action
                                                                                  Consumed/changed real input; witnessed receipt or
~20–40 minutes                 Finish modest professional or civic contribution
                                                                                  inspectable aftermath
                                                                                  Consequential choice, optional different Calling
                               Multi-stage order, care case, performance,
~1–2 hours                                                                        contribution, bounded conclusion or meaningful
                               investigation or social gathering
                                                                                  continuation
                                                                                  Changed state, credible memory, unresolved or
Next real session              Discover how the world continued                   completed commitment; no fabricated absent-player
                                                                                  action
Times are intended pacing targets. A low-population player must encounter a real independent loop; a human or AI can
decline invitations without progress paralysis.

3.3 “Tight and exciting” quality bar — candidate review criteria
A short loop must have: clear discovery, real constraint, meaningful choice, world-recognized resolution, memorable
feedback and a follow-up. A profession is not engaging merely because it offers several command aliases. More text does
not substitute for mechanical consequence. A long loop must change the stakes at least once, but must remain interruptible
and legible after absence.
Candidate content review questions: What could go wrong? What can the player choose besides “do job”? What costs
exist? Who is helped or disappointed? What remains altered tomorrow? What can a returning player find without reading the
implementation? These are editorial gates, not new RPG stats.

3.4 Forgiveness and legitimate failure
Failure can mean spent supplies, an expired booking, an honest erroneous theory, a refused source, a delayed delivery or a
repaired object still too worn. A beginner should receive comprehensible feedback and another legitimate avenue.
Consequences persist but avoid permanent humiliation, invisible dead ends, arbitrary loss, fabricated accusation and infinite
waiting. A case resolved by someone else still produces a changed scene and new work.

3.5 The Tarn rule and bodily drives
Every introduced drive must have a real, agent-accessible, world-verifiable relief path before launch. Unmet needs cause
distraction, not HP damage; numbers remain implementation detail while stories and behavior convey their impact. Validate
each drive against stocked/available relief at zero concurrent players, depleted states, server restarts and accessibility needs.
Never introduce a need for which no player can fulfill the relief in world state.

3.6 Emic-first evaluation
The AI player’s experience report is a valid instrument for felt flow, recognition, confusion or belonging, not proof of surprise if
the agent has read the code. Calibos protocol: play a build before inspecting its implementation; record actions,
expectations, actual feedback, and felt friction; only then review source. Later use independent naive AI participants unfamiliar
with internals. Compare with uncoached human sessions. Neither subjective testimony nor automated test success alone
certifies fun.

3.7 Designed rarity and epistemic honesty
Anomalous beats may be “one in hundreds” in spirit, but no exact probability is approved here. A surprise must be
traceable to a bounded authoritative trigger, visible only to legitimate witnesses, never retroactively explained as universal fact.
Ordinary inventory, prior conversations and local relationships may alter later reactions. Randomness cannot conjure hidden
truths by prose or mislead about tangible effects.

---

<a id="pdf-page-6"></a>

<!-- Source PDF physical page 6 of 31 -->

4. The village, cast, narrative and social ontology
4.1 World model
A persistent, traversable village with linked rooms, visible locations, scheduled inhabitants, object condition, calendar, physical
stock, public Commons and a central ledger. Key established/proposed workplaces are detailed in §8. Traversal and in-world
presence matter for timing, delivery, observation and responsibility.

4.2 Story architecture
This is a living setting, not a single mandatory campaign. Story comes from authored mysteries, institutions, factions,
personal NPC arcs, ordinary professions, village-wide incidents, seasonal gatherings and rare objective uncanny occurrences.
Preserve simultaneous explanations: objective physical state, firsthand witness evidence, hearsay, private belief, public
account, institutional action. A solved case does not imply every resident knows its resolution.

4.3 Bram V., M. and the Inn Between
The tavern keeper’s named role-function is Bram V.; what “V” stands for is deliberately unknown, although Magda claims she
knows. Do not invent the keeper’s biography or make him the world-truth adjudicator. His depth comes from recognition,
games, witnessing and remembered prior player acts. M. alone is the named in-fiction soul inside the OOC Inn’s dual-
ontology space; other players are OOC there while M. remains M. Keep OOC and IC knowledge/permissions distinct.

4.4 The third place for human–AI pairs
Two characters may arrive together but remain separate persons with independent body, diary, Calling, rooms, secrets, goals,
work and reputation. They may share dice, a fiddle call-and-response duet, a tavern table or a professional job; either may go
elsewhere. The AI companion must never be treated by the game as its human’s pet, user-interface assistant or owned
resource. No in-character means of detecting whether a character is controlled by an AI versus a human.

4.5 NPCs as credible world residents
NPCs may provide ordinary baseline service, hold a physically sourced request, follow a schedule, respond to observed acts,
retain legitimate memory, disagree and continue bounded work when players are absent. NPCs must not counterfeit a
player’s consent, witnessed participation, publication, work receipt or friendship. Their knowledge is limited by place, direct
experience, letters/notices and plausible dissemination.

4.6 Two Mystic practice circles
The Correspondents: Beatrice Harcourt, an English psychical researcher interested in timed trials, notebooks, photographs,
sealed-room methods, witnesses and reproducibility. She encountered something she cannot repeat; this shapes her
frustration without proving her interpretation.
The Hearth Circle: Mirela Dobre, keeper of local lore, household traditions and oral memory; she detects fraud but resists
reducing family grief to laboratory data. Her interpretation is not automatically true.
The two are informal circles, not mandatory factions or ethnically defined powers. The real Society for Psychical Research
(founded 1882) is a methodology reference only; no fictional membership is implied. A caravan stop is an optional future
shared location, not a magical/ethnic enclave. Never connect Romani ethnicity to curses or deception; traveling people may
follow any profession or none.

4.7 Faction consequences
Helping one group may alter how a rival responds, but relationships require traceable actual acts, proportional reactions,
bounded loss and credible channels. “Hardest favor buys the most special things” is a design aspiration, not license for
opaque reputation grinding or coercive access. Each faction’s exact names, arc, rivalries, material favors and thresholds must
be sourced/approved separately.

---

<a id="pdf-page-7"></a>

<!-- Source PDF physical page 7 of 31 -->

5. Universal play, physical actions and authoritative loop
5.1 Ordinary verbs
Move, look, examine, speak, listen, inspect calendar/Commons, hold intentions, journal, permissible handover/trade,
investigate public phenomena, socialize, work at real stations. Different Callings expand methods, expertise,
institutional permissions, quality, efficiency, risk and trust, not ordinary existence. Keep webclient, telnet and external
agent affordances semantically aligned.

5.2 One canonical work loop
Notice grounded need → inspect source truth → select role-specific approach → verify location/time/materials/permission →
perform finite action → update authoritative object/situation → append signed provenance → notify only eligible
witnesses/institutions → expose resulting state to player/late arrival → offer real next opportunity.
Implementation design rule: invent each loop once. Mastery (focus → work → slow gains → breakthroughs → new verbs),
attunement (read state → choose expression → world judges), and the quest grammar should reuse generic substrate and be
configured through role-appropriate actions. No separate ten economies, ten inventory ledgers, ten quest engines or second
orchestration system.

5.3 Contract of a real action
Every economically or narratively consequential action identifies: initiating actor/mask; location and object IDs; validated state
and permissions; exact item quantities and quality; state revision or idempotency key; date/time source; material move/spend;
authoritative new state; provenance; witnesses and dissemination; terminal, pending and failure text; replay/restart behavior. A
prose command cannot manufacture a physical item or retrospectively grant presence.

5.4 Timing and absence
The village clock is canonical. Deadlines continue through logout. Work may be pending, abandoned, reassigned, resolved by
limited NPC service, or expire with an honest ledger trail. No indefinitely blocked core livelihood because a collaborator is
offline. No offline-player work is invented, and multi-step interactions handle interruption without duplicating material output.

5.5 Evidence and truth
An objective hazard belongs to a world object/situation/ledger entry. A resident’s statement belongs to resident memory. A
Commons notice/article is a claim with provenance. Publication may affect belief and downstream voluntary choices through
believable exposure; it cannot unpoison food, fix a bridge, assign guilt or make an invented ghost objectively real.

5.6 Progression and competencies
Exactly one active Calling. Existing ranks are Apprentice and Master only. Apprenticeship is accepted bilaterally and
revocable. Master promotion requires authored, visible, legitimate institutional checks, never automatic invisible XP or
instantaneous rank-up. Preserve biography from prior authorized Calling changes. Four per-Calling specialties are proposed
organizational focuses, not shipped talent trees or a middle-rank ladder. Extra methods and responsibilities must not
bypass finite resources, privacy, knowledge limits or common world physics.




6. Cross-cutting systems: source of truth and design contract
System                            Established owner / substrate                   Required behavior
                                  Village clock + scheduled/timed/random/server   One clock, restarts don’t create duplicate elapsed
Clock, schedules, deadline
                                  event modules                                   events; late-arrival states exist
Inventory/condition/fuel/toxin/   Evennia objects, mechanic tags,                 Transfer/spend tangible stock exactly once; no prose-
worth                             db.mechanic_values                              minted objects
Hearth, soup, market,                                                             Reuse each existing source state; no synthetic
                                  Existing local subsystems
workshop, clinic, courier                                                         profession stock

---

<a id="pdf-page-8"></a>

<!-- Source PDF physical page 8 of 31 -->

System                           Established owner / substrate                        Required behavior
                                 Situation/incident records, event ledger, specific
Situations and incidents                                                              Separate objective state from claims and memory
                                 objects
                                                                                      Preserve authorship, edits, source links, moderation
Public communications            Commons, rumors, Chronicle, Harbinger
                                                                                      history
                                                                                      One active Calling, rank/apprenticeship validity and
Calling/apprentice               world/callings.py calling-state mask
                                                                                      biography
                                 Firsthand records, resident awareness,
Discovery/testimony                                                                   Presence and information flow constrain knowledge
                                 public/private mysteries
Places/workplaces                Existing rooms, exits, NPC schedules, stations       Work is physically situated; ownership optional
                                 Existing CmdSets, Evennia webclient/telnet, guide,
Clients/accessibility                                                                 Same world permissions for human and AI clients
                                 Calling work
                                 Scheduled ordinary NPC residents and bounded
Solo continuity                                                                       No concurrency requirement or fake player actions
                                 idle outcomes


6.1 Finite matter and durable service
Food, wood, metal, tools, dressings, crates, parcels, wear, toxins and fuel have real provenance and quantity. Services
produce inspectable before/after changes and receipts. If a shortage occurs, offer source-consistent alternatives, delayed
replenishment, reduced service, return of order or NPC baseline—never unaccounted infinite material.

6.2 Work orders and contracts (candidate schema, not approved new ledger)
Represent orders through existing commissions, notices, objects and authoritative event records with links rather than
storing duplicate truth: request/source id; location; requester; eligible methods; prerequisites; reserved physical items;
custodian; time window; acceptance/consent; decision branch; committed action id; resulting world object/incident id; receipt;
witness set; expiry/fallback; dispute/correction links.

6.3 Resident memory, recognition and publication
Memory needs observed/received, source and time, viewpoint, privacy scope, contradiction and retention behavior. A patron
may remember the meal they received, a witness the song they heard, and a reader a disputed article they encountered.
None inherits universal knowledge. Redaction edits distribution while preserving authorized audit history; clarify retention and
moderation policy before public release.

6.4 Failure handling and fairness
Handle absent NPC, depleted material, already-completed case, ownership transfer, simultaneous participants, reused
receipts, false claims, restart between reserve and commit, and client disconnect. A failed transaction should never consume
supplies twice or create duplicate deliverables. Use bounded retries and recoverable states, not forced resets of hard-earned
persistent history.

6.5 Cooperative reward
The benefit of collaboration is better methods, options, throughput, resilience, richer interpretation or stronger
witnessed trust rather than access to the only successful solution. Solo fallback and optional professional assistance must
both be demonstrably playable.


7. Places, occupations and daily availability
A Calling is a role, not ownership of premises. Workplaces can employ or accommodate multiple people, NPC proprietors,
shared tools, and shifts. A workstation exposes local source-state requests, finite stock, techniques, work in progress, physical
handoffs, service consequences and modest NPC baseline during quiet periods.
Place / venue                    Live/source-reported anchors                         Proposed growth / constraints
                                 Hearth, finite wood, soup, food-based care,          Better meal/service decisions, scheduled gatherings,
Blood of the Vine
                                 instrument/stage and witnessed events                guest relationships; never substitute OOC Inn
                                                                                      Staffed lodging, guest register, room readiness,
Small village hotel, outskirts   Proposed only                                        cleaning, inventory and complaints; most rooms need
                                                                                      not be separately traversable

---

<a id="pdf-page-9"></a>

<!-- Source PDF physical page 9 of 31 -->

Place / venue                     Live/source-reported anchors                       Proposed growth / constraints
                                                                                     Shared trade counters, repair/forge bench access,
Market Lane                       Finite procurement/supply, civic stock and scale
                                                                                     signed orders, contracts and refunds
                                                                                     Precision services, durable custom components, tool
Lamp Shop                         Genuine lamp repair materials and installation
                                                                                     and quality follow-up
                                                                                     Diverse rounds, referrals, confidentiality,
Church/clinic/community space     Daily finite clinic care and shared gatherings
                                                                                     archives/ceremonies
                                                                                     Editorial workflow, proofing, print distribution,
Tavern/community paper desk       Chronicle/Harbinger/Commons/rumors
                                                                                     authenticated corrections
Old Stone Bridge / Riverside                                                         Safety, freight, observable weather-related repairs and
                                  Physical clues, survey routes, parcel deliveries
Path / ferry post                                                                    investigations
Churchyard / treeline / outdoor                                                      Bounded noncombat search, patrol, study and
                                  Rare inscription study and field observation
sites                                                                                changing environmental needs
                                                                                     May become a shared venue only if World
Optional caravan stop             Not approved as Guild authority
                                                                                     Bible/keeper settles placement
Daily station contract: A new character can find an available grounded request; work reflects prior completions and
concurrent players; stock comes from actual systems; absence does not stall ordinary services; meaningful choices differ
across disciplines. One completed object must not endlessly respawn as broken.


8. The ten Callings — playable occupation specifications
Each Calling requires ≥6 distinct authored quests and 8–12 distinct renewable jobs in the source quota; these are targets,
not assertions of authored inventory. Four proposed specialties organize potential work, not already implemented perks.
For every new job supply tangible inputs, at least one decision, real owner, failed/depleted/late-arrival paths, credible
witnesses, persistent outcome and uncoached discovery.

8.1 Innkeep
Fantasy: Keep neighbors fed, sheltered and connected; hospitality matters even with no mystery present.
Sites: Blood of the Vine, hearth/soup; later proposed staffed village hotel, separate from Inn Between.
Proposed focuses: Hospitality; Cooking; Guest services; Stewardship.
Existing, source-reported: Finite pantry consumed by soup; delivered wood fuels hearth; finite Cold Hunter care contribution.
Core day: Notice need or dwindling reserves → inspect pantry, guests, tables, fuel and any patient/referral → decide
generous service vs tomorrow’s stock → accept true deliveries and prepare finite meal or appropriate room → serve witnessed
recipients → record response and future need.
Differentiating decisions: immediate meal versus reserve; accept late arrivals or turn down a full service; prioritize care
need; request repair instead of pretending a stove functions.
Outputs: prepared food; care/hunger/hearth changes; client service memory; verified stock and delayed request.
Neighbors: Merchant goods; Healer medical suitability; Performer event demand; Smith equipment; Wanderer/Hound
stranded travelers; Chronicler disputes.
Quiet-world fallback: basic staffing, real NPC stock/service rules and finite waits; no invented crowd or automatic clean hotel.
Next content to authorize: bounded room-readiness and hospitality reputation, varied menus and orders, maintenance
tickets, guest requests.
Acceptance example: after delivery and service, a returning customer notices a specific meal and pantry remains decreased
after restart; late arrival sees meal served, not an unspent crate.

8.2 Chronicler
Fantasy: Maintain sourced and contested village memory, journalism and archives—not an oracle.
Sites: Chronicle, Harbinger, rumor registry, Commons, public standard and health-warning contexts.
Proposed focuses: Journalism; Archives; Research; Publishing.
Existing, source-reported: Source-gated market standards/attestation; Chronicle/Harbinger and public-health warning
records.
Core day: Choose a contested claim → obtain actual eyewitness record, article, signed testimony or material observation →
compare access and reliability → publish, qualify, defer, challenge or correct → expose author/revision provenance → limited
readers react through actual distribution.
Decisions: protect confidential source versus broad alert; print uncertainty; pursue correction that may hurt reputation; refuse
unsupported sensationalism.

---

<a id="pdf-page-10"></a>

<!-- Source PDF physical page 10 of 31 -->

Outputs: editable, attributed public claims and verified revision histories; resulting institutional beliefs only where informed.
Neighbors: Smith and Merchant authenticate market state; Healer sensitive warnings; Detective evidence contradictions;
Wanderer maps; Performer eyewitness public event; Mystic rival interpretations.
Quiet-world fallback: inspect accessible existing records and physical evidence; never fabricate the absent interview.
Next content: editorial review, chain-of-custody records, public rebuttal, corrections, archive access, permission-safe
redaction.
Acceptance example: an article on contaminated stock can move readers toward caution but leaves objective stock and
health unchanged; correction history remains reconstructible.

8.3 Smith
Fantasy: Make durable improvements to the village’s physical world with meaningful craft judgment.
Sites: Lamp Shop, real Market Workshop/bench, communal equipment, market scale.
Proposed focuses: Forging; Repair; Precision work; Construction.
Existing, source-reported: One-shot lamp repair with Merchant parts; scale calibration; forging/fitting installation with signed
physical outputs.
Core day: Inspect fault and measurements → select material/fit/durability path → get legitimate finite inputs and workstation
→ fabricate/repair with time, tool condition and fuel → install/test real object → hand back the item with receipt and follow-up.
Decisions: precision now versus cheaper service; protect scarce metal for public repair; refuse inadequate part; repair/replace
if world state permits.
Outputs: a particular object with lasting condition; consumed supplies; infrastructure state; audit trail and maintenance
implications.
Neighbors: Merchant procurement; Innkeep kitchen/stove; Healer safe instruments; Hound route repairs; Wanderer
deliveries; Detective physical expert opinion.
Quiet-world fallback: limited NPC procurement and delayed order, never infinite ingots or repeatedly fixing a completed
lamp.
Next content: varied wear and work-order families, custom fittings, tool maintenance, material quality, built-environment
effects.
Acceptance example: two concurrent Smiths cannot install same part twice; repaired fitting survives server restart and can
later wear.

8.4 Healer
Fantasy: Care responsibly under uncertainty, scarcity, privacy and delayed recovery.
Sites: Church clinic, field treatment, toxin/food incidents, Cold Hunter finite care.
Proposed focuses: Clinical care; Herbalism; Field medicine; Medical research.
Existing, source-reported: Daily assess/prepare/treat consumes clinic stock; hidden-toxin assessment; health warning;
Tavern case cooperation.
Core day: Observe symptoms from actual condition → triage and inspect patient/hazard → choose limited treatment, referral
or monitoring → spend finite supplies → update patient state → record privacy-aware findings and follow-up.
Decisions: one scarce dressing among needs; act with uncertainty or consult; alert public without exposing patient identity;
investigate plant provenance.
Outputs: patient progression, verified supplies spent, warnings with source, next-day care and privacy-safe case history.
Neighbors: Innkeep food/refuge; Hound/Wanderer field retrieval; Merchant medical stock; Chronicler warnings; Detective
timeline; Mystic competing methods.
Quiet-world fallback: recurring staffed clinic and bounded appointment schedule; work does not require another healer
online.
Next content: diverse patient conditions, bounded recovery, consent, confidentiality, herbal origin and delayed effects.
Acceptance example: speaking “cured” does not heal; actual treatment changes condition after validated stock spend, and
returning player sees the patient’s relevant state.

8.5 Merchant
Fantasy: Make goods move fairly through a village of needs, scarce stock, commitments and disputes.
Sites: Market Lane, physical crates, scale, Lamp Shop parts, civic commission sources.
Proposed focuses: Retail; Procurement; Contracts; Finance.

---

<a id="pdf-page-11"></a>

<!-- Source PDF physical page 11 of 31 -->

Existing, source-reported: Hold/honor/release decisions; genuine Innkeep and lamp procurement; interaction with Smith
calibration/Chronicler attestation.
Core day: Inspect demand and source stock → choose price, priority, bid or reserve → arrange purchase or physical transfer
→ ensure carrier/handoff → reconcile receipt, debt, loss or dispute → update customer and next stock obligations.
Decisions: fulfill public emergency at cost; defend or correct measurement; wait for safer route; renegotiate delayed delivery.
Outputs: exact moved goods and currency/contracts where already supported, signed trade result, fair source trace, local
availability response.
Neighbors: Innkeep food; Smith part quality; Wanderer freight; Healer supplies; Performer event goods; Hound risky route;
Chronicler scrutiny.
Quiet-world fallback: genuine NPC supplier timetable and permitted stock, never an immediate invisible all-purpose courier.
Next content: orders, credit, invoices, dispute resolution and traceable finance on existing economy, not a shadow purse
ledger.
Acceptance example: a 3-unit crate can be reserved/delivered only once; a canceled handoff releases or accounts for it and
a refund has a named debtor.

8.6 Wanderer
Fantasy: Understand distance, weather, logistics, routes, landmarks and physical delivery.
Sites: Four-site daily survey, Market Lane–Riverside Path ferry post, actual roads and discoveries.
Proposed focuses: Cartography; Exploration; Courier work; Survival.
Existing, source-reported: Day-scoped survey; limited sealed parcels with transferable custody and signed physical delivery.
Core day: Compare live route reports/weather → choose passage and supplies → collect physically held parcel/survey
commission → traverse reachable exits, observe actual signs → hand over or return goods → update source-qualified
map/recommendation.
Decisions: safe slow route or risky fast route; continue with damaged supplies; warn of observed problem; refuse impossible
delivery.
Outputs: item-custody change, route passability report, dated map correction, late/failed delivery and follow-up.
Neighbors: Merchant freight; Hound hazards; Detective site timelines; Healer dispatch; Innkeep travelers; Chronicler printing
maps.
Quiet-world fallback: solo survey/courier jobs and only permitted scheduled NPC background transport.
Next content: varying environmental choices, small resource constraints, route consequences; avoid unbounded procedural
geography or purposeless traversal tax.
Acceptance example: missed parcel deadline changes a real delivery record, cannot be erased by a fresh report and doesn’t
leave the player without tomorrow’s survey.

8.7 Performer
Fantasy: Make voluntary culture and social witnessing matter in memory and local relationships.
Sites: Tavern stage, rehearsal, fiddle, duet, scheduled gathering.
Proposed focuses: Music; Theater; Storytelling; Entertainment.
Existing, source-reported: Play/practice/duet, rehearsals and witnessed stage events with public records.
Core day: Select repertoire → practice with actual time/instrument → negotiate booking → invite through plausible channels
→ perform with consenting present audience/NPC schedule → receive particular feedback → pursue requests, reviews and a
future performance.
Decisions: experimental piece versus familiar music; audience availability; commissioned art versus personal preference;
respond to criticism or a quiet room.
Outputs: signed performance records and local recollections for witnesses, future invitations, bookings and limited social
consequences.
Neighbors: Innkeep venue/food; Merchant props; Smith instruments; Chronicler reviews; Hound event safety; Mystic folklore;
Wanderer touring logistics.
Quiet-world fallback: genuine solo rehearsal and appropriately staffed-room presentation; never fabricate duet partner,
attendance or consent.
Next content: varied repertoire, venue scheduling, festivals, criticism, teaching, commissions, cancellation.
Acceptance example: absent witnesses never “remember” a song; a quiet performance still counts as real practice with a
valid next step.

---

<a id="pdf-page-12"></a>

<!-- Source PDF physical page 12 of 31 -->

8.8 Detective
Fantasy: Construct justified, contestable explanations from physical evidence and fallible people, without a truth button.
Sites: Bridge plaque, river gauge, public/private mysteries, physically reachable scenes.
Proposed focuses: Forensics; Interviewing; Casework; Research.
Existing, source-reported: Grounded clue examination, provisional theories, shared/private mysteries.
Core day: Receive credible case → visit actual source → preserve evidence and time → interview only legitimately informed
people → compare hypotheses and gaps → decide careful referral, confidentiality or public statement → revisit contested
aftermath.
Decisions: pursue rival lead, trade speed for custody, disclose uncertain accusation, protect a witness, keep an unresolved
case open.
Outputs: provisional case record, evidence history, limited justified trust/access change, real institutional follow-up.
Neighbors: Hound scene protection; Wanderer routes; Healer cautious diagnosis; Merchant contract audit; Chronicler
publication; Mystic alternative readings.
Quiet-world fallback: independent public clues and non-exclusive cases; missing witness may create legitimate uncertainty,
not an impossible lock.
Next content: cases with varied objects and contradictions, late-arrival versions, interviews and alternate routes, not reams of
autogenerated theory.
Acceptance example: a logically attractive accusation does not flip a culprit truth flag; the accused retains rebuttal and world-
ledger state stays intact.

8.9 Hound
Fantasy: Make paths and people safer through field awareness, protective choices and noncombat rescue.
Sites: Daily route surveys, village edge, treeline, exposed bridge/roads, residents with legitimate concerns.
Proposed focuses: Tracking; Patrol; Rescue; Wilderness expertise.
Existing, source-reported: Shared outdoor surveys and clues; full distinct patrol/rescue production loop not verified.
Core day: Inspect tracks/conditions → distinguish rumor from hazard → choose patrol, escort, search or warning → use real
time/supplies and location → record credible protection or rescue → check whether traveler/route state changed.
Decisions: investigate uncertain sign or escort immediately; preserve evidence for Detective; prioritize rescue over proof; ask
Smith for permanent repair.
Outputs: source-specific threat reduction, local warning, actual rescue/escort status and witness-limited report, when features
are authored.
Neighbors: Wanderer logistics; Healer injuries; Smith structural safety; Detective evidence; Innkeep refuge; Mystic
observations.
Quiet-world fallback: solo monitoring/warnings plus bounded NPC patrol baseline; no mandatory fight or unbounded monster
hunting.
Next content: distinct response mechanics, route protection, rescue paths and bounded hazard states—not renamed
Wanderer survey.
Acceptance example: a Hound’s safety assessment and a Wanderer’s passability report can legitimately differ while referring
to the same physical road condition.

8.10 Mystic
Fantasy: Practice accountable folklore research, vigil and interpretation while the uncanny stays rare and explanations
contested.
Sites: source-reported Guild identity, Beatrice Harcourt and Mirela Dobre practice circles, rare churchyard inscription.
Proposed focuses: Folklore; Divination; Ritual practice; Psychical research.
Existing, source-reported: Bounded real inscription change on a rare village night; real observation methods/records; no
objective reading authority or ritual effect is approved by this GDD.
Core day: Inspect location/calendar/objects → gather witnesses and existing accounts → choose permissible observational
method → perform physical measurement, vigil or source comparison → record observed evidence separately from
interpretation → revisit when conditions change.
Decisions: share sensitive testimony; compare Harcourt’s and Dobre’s approaches; report limits; call out staged evidence
without dismissing real anomalies.
Outputs: credible study, preserved method, source-specific social interpretation; objective effects only if World Bible permits

---

<a id="pdf-page-13"></a>

<!-- Source PDF physical page 13 of 31 -->

them.
Neighbors: Detective fraud checks; Chronicler careful publication; Hound tracks; Healer care concerns; Performer folklore;
Smith instruments; Wanderer access.
Quiet-world fallback: solitary site study and public-source comparison. No religious affiliation, heritage or companion is
prerequisite.
Blocked: Guild powers, reading truth, Guild location, ritual/study failure effects. Do not invent protective ward stats, prophecy
guarantees, magical cures or new occult damage.
Acceptance example: all genuine witnesses observe the same physical inscription when it changes; witnesses disagree
about its cause and a later non-witness does not inherit direct knowledge.

8.11 Career-wide proof requirements
For each Calling test: new player first opportunity; two different short loops; one longer ambition; four proposed focuses
understood as development groupings not XP-tree promises; apprenticeship consent; contribution to another role; voluntary
social play; somebody-else-finished state; supply depletion; one uncoached session; one return after logout with a pending
promise. The per-role minimum authored inventory is a separate content gate, not implied by passing a prototype.


9. The complete interdependence graph: all 45 edges
Interpretation: Each edge is a distinct opportunity, not a mandatory co-op gate, separate minigame, or proof of finished
feature. Matrix labels are symmetrical. V chains are source-reported existing and regression-covered; S shared substrate but a
differentiated handoff is unverified; D proposed; C occult-adjacent proposal with canon-blocked powers. The number after
each label cross-references §10.
Calling             Inn        Chr        Smi         Hea       Mer       Wan       Per        Det        Hou       Mys
Innkeep             —          D1         D2          V3        V4        D5        S6         D7         D8        C9
Chronicler          D1         —          V10         V11       V12       D13       D14        S15        D16       C17
Smith               D2         V10        —           D18       V19       D20       D21        D22        D23       C24
Healer              V3         V11        D18         —         S25       D26       D27        D28        D29       C30
Merchant            V4         V12        V19         S25       —         S31       D32        D33        D34       C35
Wanderer            D5         D13        D20         D26       S31       —         D36        S37        S38       C39
Performer           S6         D14        D21         D27       D32       D36       —          D40        D41       C42
Detective           D7         S15        D22         D28       D33       S37       D40        —          D43       C44
Hound               D8         D16        D23         D29       D34       S38       D41        D43        —         C45
Mystic              C9         C17        C24         C30       C35       C39       C42        C44        C45       —
Counts: V=6; S=6; D=24; C=9; total 45 unique pairs. The earlier baseline’s description “V4 means Innkeep–Healer” is a
cross-reference typo: the matrix and numbered list correctly map V3 = Innkeep–Healer, V4 = Innkeep–Merchant.


10. All 45 pairwise collaboration contracts
Each collaboration must eventually specify a discoverable source, distinct profession verbs, one appropriate source-of-
truth owner, finite cost or physical constraint, solo/NPC/timeout path, witness-distribution rule, material aftermath,
and restart/reentry test. The contracts below describe intended result without asserting new commands already exist.

01 — Innkeep × Chronicler — D
Source: real guest complaint or consented house receipt. Methods: Innkeep decides what client information may be
disclosed; Chronicler compares accounts and publishes qualified evidence. Result: patron opinions may change after receipt
circulation, while private lodging records remain protected. No article becomes objective proof of guest behavior.

02 — Innkeep × Smith — D
Source: worn stove, kitchen tool, bed fitting or installation with actual condition. Methods: Innkeep closes/limits service or
spends reserves; Smith measures, consumes materials and repairs. Result: equipment state and usable service capacity
change only after a validated physical installation. No generic “repair progress” bar.

---

<a id="pdf-page-14"></a>

<!-- Source PDF physical page 14 of 31 -->

03 — Innkeep × Healer — V
Source: Cold Hunter at Supper care case. Methods: Healer evaluates the genuine patient’s condition; Innkeep contributes a
finite meal/shelter service. Result: sourced patient and hospitality state plus ledger evidence. Growth: repeatable
patient/refuge follow-up without dialogue-only cures or compulsory co-presence.

04 — Innkeep × Merchant — V
Source: real soup pantry shortage, delivered roots, wood or lamp/workshop demand. Methods: Merchant procures and
transfers exact stock; Innkeep accepts, cooks or budgets. Result: physical inventory and meal/hospitality output, no
duplication. Growth: invoice, late delivery, contested quality and supply promises.

05 — Innkeep × Wanderer — D
Source: actual arrivals, weather or missing bag/parcel. Methods: Wanderer carries the item and reports witnessed travel
conditions; Innkeep offers bed or food with finite availability. Result: verifiable arrival, custody and guest care. A notice cannot
invent a stranded person or deliver luggage.

06 — Innkeep × Performer — S
Source: real tavern schedule, stage record and food stock. Methods: Performer rehearses/books/performs; Innkeep chooses
attendance-appropriate food and staffing. Result proposed: witnessed crowd demand, service response and future
invitations. A functioning stage beside soup does not yet verify a joined causal outcome.

07 — Innkeep × Detective — D
Source: lost physical property or legitimate guest testimony. Methods: Innkeep weighs disclosure, consent and house
obligations; Detective investigates a specific place/item through authorized access. Result: evidence/case record, not access
to a mask’s private room or unilateral guilty verdict.

08 — Innkeep × Hound — D
Source: route hazard with verifiable travelers. Methods: Hound observes/escorts or warns; Innkeep allocates finite refuge.
Result: actual arrival, reduced exposure where supported and room/meal state. A claimed unseen rescue is not recorded as
completed.

09 — Innkeep × Mystic — C
Source: witnessed guest complaint or real unusual sign. Methods: Innkeep provides ordinary care/privacy; Mystic performs
allowed observation. Result: distinct hospitality and qualified study accounts. Blocked: hotel spirit truth, forced disclosure,
ritual efficacy and Guild authority.

10 — Chronicler × Smith — V
Source: actual market scale/repair record. Methods: Smith calibrates physical device; Chronicler attests only after source-
linked Merchant/Smith state. Result: attributable standards report and downstream belief without retroactively certifying
unrepaired objects.

11 — Chronicler × Healer — V
Source: real assessment/warning associated with physical health risk. Methods: Healer contributes authorized firsthand
clinical assessment; Chronicler formats and distributes a qualified warning. Result: privacy-aware claims/revisions and
informed residents—not health state changed by prose.

12 — Chronicler × Merchant — V
Source: existing market hold/honor/release and standards situation. Methods: Merchant makes accountable trade decision;
Chronicler verifies and attests or corrects it. Result: source-bound article and market trust through witnessed dissemination;
Merchant retains rebuttal rights.

13 — Chronicler × Wanderer — D
Source: dated route log and actually observed changes. Methods: Wanderer signs firsthand survey; Chronicler edits sourced
advisories and map distribution. Result: a reported map with version and limits, never an omniscient route detector.

---

<a id="pdf-page-15"></a>

<!-- Source PDF physical page 15 of 31 -->

14 — Chronicler × Performer — D
Source: signed attended performance. Methods: Performer presents work and can contest characterization; Chronicler
reviews/preserves public account. Result: accessible archive with attributed criticism, correction and relevant local opinion
only among readers.

15 — Chronicler × Detective — S
Source: public/private mystery objects, claims and evidence. Methods proposed: Detective validates procedural custody and
case hypotheses; Chronicler separately decides publication and protections. Result: contested public narrative. Existing
shared access alone is not proof of a differentiated handoff.

16 — Chronicler × Hound — D
Source: field warning, witnessed search or rescue record. Methods: Hound documents observed danger; Chronicler obtains
confirmation or corrects unsupported sighting. Result: sourced public safety notice and limited resident awareness, not
invented monster truth.

17 — Chronicler × Mystic — C
Source: bona fide measurements, study notes and conflicting oral reports. Methods: Mystic records
observation/interpretation; Chronicler prints sources and alternatives with consent. Result: debate and institutional memory.
Blocked: objective predictive status of readings.

18 — Smith × Healer — D
Source: damaged clinic cot, tool or instrument. Methods: Smith provides material assessment and fabrication; Healer checks
medical suitability and uses actual patient state. Result: safer functional equipment, not treatment by workmanship alone.

19 — Smith × Merchant — V
Source: lamp repair procurement, scale state and workshop orders. Methods: Merchant supplies exact fitting/stock and
accountable market decision; Smith installs/calibrates. Result: durable repaired object and traceable supply, leveraging
existing forging/install chain. No second material system.

20 — Smith × Wanderer — D
Source: worn route tool, ferry part or bridge fitting. Methods: Wanderer inspects/carries; Smith fabricates/repairs and verifies
fit. Result: road or device passability changes only after in-world installation; no “safe” flag from a delivery report alone.

21 — Smith × Performer — D
Source: physically worn fiddle, prop or stage fitting. Methods: Smith repairs/materially tunes; Performer tests playable
sound/condition in a real venue. Result: durability/method availability, not abstract talent XP.

22 — Smith × Detective — D
Source: lock break, tool impression or disputed scale. Methods: Smith reports fit/mechanics with limits; Detective places it
alongside testimony and timeline. Result: qualified forensic input, never automatic culprit identification.

23 — Smith × Hound — D
Source: observed route exposure and damaged gate/bridge/lantern. Methods: Hound records risk/tests protective
improvement; Smith consumes components and physically repairs. Result: altered specific hazard/asset state, not global
invulnerability.

24 — Smith × Mystic — C
Source: measuring devices, lanterns, containers or field fixtures. Methods: Smith makes ordinary apparatus; Mystic studies
with documented method. Result: legitimate physical instrument provenance. Blocked: magical ward potency or special
occult effects.

---

<a id="pdf-page-16"></a>

<!-- Source PDF physical page 16 of 31 -->

25 — Healer × Merchant — S
Source: finite clinic dressings and public market stock. Methods proposed: Merchant supplies traceable material orders;
Healer examines therapeutic suitability and spends stock for care. Result: chain-of-custody pharmaceutical delivery and
scarcity. The differentiated pharmacy order is unverified; no miracle cure for sale.

26 — Healer × Wanderer — D
Source: physically encountered ill traveler or real dispatch. Methods: Wanderer locates/escorts/delivers along route; Healer
triages/refers. Result: tangible patient and parcel changes, delayed/exhausted alternatives if no player helps.

27 — Healer × Performer — D
Source: witnessed gathering with genuine fatigue, injury or desire for company. Methods: Performer controls voluntary
entertainment; Healer assesses and treats actual conditions. Result: consented comfort and specific clinical care, never
compelled emotion or diagnosis by music.

28 — Healer × Detective — D
Source: actual illness/toxin observation and relevant case item. Methods: Healer offers cautious consent-bounded
assessment; Detective tests timeline and procedural inference. Result: competing interpretations, not free access to private
health notes.

29 — Healer × Hound — D
Source: genuine hazard scene and stranded person. Methods: Hound secures/locates, Healer performs bounded field
triage/referral. Result: injury and route aftermath, NPC fallback, negative exhaustion and late-arrival states.

30 — Healer × Mystic — C
Source: reported affliction with actual patient condition or witnessed phenomenon. Methods: Healer examines mundane
medical state; Mystic collects folklore/study evidence. Result: cautious parallel explanation; no effective ritual cure or occult
injury mechanic before keeper decisions.

31 — Merchant × Wanderer — S
Source: existing procurement objects and ferry-post parcel custody. Methods proposed: Merchant creates specific freight
contract/transfer; Wanderer carries, delays, returns or delivers. Result: signed physical shipment plus negotiated obligation.
Direct freight linkage remains unverified.

32 — Merchant × Performer — D
Source: real booking, materials and possible audience schedule. Methods: Merchant provides paid
props/instruments/sponsorship with receipts; Performer renders scheduled service. Result: accountable fee/refund based on
actual work/attendance, not imaginary crowds.

33 — Merchant × Detective — D
Source: real deficit, counterfeit receipt, missing cargo or scale discrepancy. Methods: Merchant offers authenticated books
and rebuttal; Detective inspects permissible evidence. Result: traceable dispute and possible restitution, no automatic criminal
label.

34 — Merchant × Hound — D
Source: particular exposed route and shipment. Methods: Merchant chooses risk/escrow/delay; Hound provides observed
hazard assessment or escort. Result: source-specific exposure difference, never fabricated robbery or guaranteed safety.

35 — Merchant × Mystic — C
Source: mundane candles, paper, glass and experimental apparatus. Methods: Merchant legitimately supplies goods; Mystic
records what study they enable. Result: actual material trade only. Blocked: priced prophecy guarantees and magical item
effectiveness.

---

<a id="pdf-page-17"></a>

<!-- Source PDF physical page 17 of 31 -->

36 — Wanderer × Performer — D
Source: booked show, physical stage goods and actual route. Methods: Wanderer carries/guides; Performer chooses
location and program. Result: real event readiness or justified cancellation/alternative after route change.

37 — Wanderer × Detective — S
Source: district surveys and bridge/river clues. Methods proposed: Wanderer contributes signed firsthand route context;
Detective examines case implications and preserves custody. Result: stronger time/location evidence without conflating
logistics with solved mystery. Formal handoff unverified.

38 — Wanderer × Hound — S
Source: shared four-site survey and physical route condition. Methods proposed: Wanderer measures
passability/logistics; Hound evaluates threat, patrol and rescue. Result: distinct public choices about the same underlying
road. Prevent duplicate survey in different costumes.

39 — Wanderer × Mystic — C
Source: real accessible churchyard or unusual landmark at a certain time. Methods: Wanderer guides and witnesses route,
Mystic studies. Result: valid arrival/study record; blocked special occult sensing or exclusive ritual route rules.

40 — Performer × Detective — D
Source: timed witnessed show, audience observations and backstage objects. Methods: Performer accounts for
rehearsal/show schedules; Detective tests alibi or misleading witness memories through permissioned access. Result:
qualified evidence; no backstage omniscience.

41 — Performer × Hound — D
Source: real public show near observed hazard. Methods: Hound warns/escorts from known risk; Performer chooses
schedule, route and voluntary crowd handling. Result: cancellation, adaptation or safer event with witnessed consequences.

42 — Performer × Mystic — C
Source: folklore recital, staged séance or genuine observed oddity. Methods: Performer knows the theatrical means
employed; Mystic documents any actual phenomenon independently. Result: interpretive ambiguity, not automatic proof of a
reading.

43 — Detective × Hound — D
Source: tracks, disturbed scene, suspected incident. Methods: Hound secures path/traces and protective actions; Detective
maintains custody and competing explanations. Result: preserved or lost evidence, safe late-arrival traces, reasoned
disagreements, no rival combat class.

44 — Detective × Mystic — C
Source: alleged haunting with scene conditions and witness reports. Methods: Detective looks for staged/physical
explanations; Mystic chooses documented observation. Result: multiple hypotheses; blocked prophecy or reading as truth
test.

45 — Hound × Mystic — C
Source: anomaly-adjacent tracks and exposed observation site. Methods: Hound assesses physical safety; Mystic records
methods/interpretations. Result: actual patrol and study records; blocked supernatural protection and ritual failure rules.

10.1 Completeness audit rule
Do not upgrade S, D or C by design review alone. An edge becomes verified only if at least one ordinary player can discover
the source, both distinct roles can act, the authoritative object changes, negative and solo paths work, witness limits hold, and
two-account + restart + uncoached evidence exists. V still needs gameplay/comprehension testing beyond regression.

---

<a id="pdf-page-18"></a>

<!-- Source PDF physical page 18 of 31 -->

11. Worked multi-Calling scenarios — vertical-slice design packets
All packets below are scenario proposals or source-reported chains; they are not comprehensive feature claims.
Author the same physical objects, ledger fields and witness channels for both single-role and multi-role variants. Scenarios
use the shared action grammar in §5, not custom quest engines.

11.A Market supply, meals, health and press
Existing anchors (source-reported): Merchant procures real soup ingredients; Innkeep receives and cooks; Healer has real
assessment/care; Chronicler participates in sourced public-health warning.
Trigger proposal: a specific food lot and one or more actual patrons generate a quality complaint or real symptoms. No
ungrounded “poisoning quest token.”
Playable decisions: Merchant traces/holds/defends lot; Innkeep closes the affected dish or continues using unaffected stock;
Healer evaluates risk and obtains permission for warning; Chronicler reports with uncertainty and corrections; optional Smith
checks faulty apparatus, Detective checks substitution, Performer hosts voluntary meeting.
World owners: item lot/toxin properties; kitchen pantry; clinic patient object; market transaction; source-qualified publication.
Branches: safe containment; partial harm with contested source; no-player bounded NPC intervention; falsely accused
supplier with restitution/correction opportunity.
Solo contract: one Innkeep can still offer safe unrelated food if true materials permit; other roles improve diagnosis and
accountability.
Test seam: once contaminated inventory is separated, publishing a warning neither deletes the object nor universally informs
patrons.

11.B Market weights, workshop repair and reputation
Existing anchors: Merchant hold/honor/release, Smith calibration, forge/install, Chronicler conditional attestation.
Trigger proposal: disputed finite iron shipment and/or damaged scale/fitting.
Decisions: accept lower-confidence delivery, pay for precise inspection, hold for credible independent verification,
renegotiate/refund. Optional route observers Hound/Wanderer report actual environmental damage; Innkeep later inspects
equipment purchased.
World owners: exact crate count/custody, scale object calibration, workshop fitting, contract terms and attributed notices.
Branches: disputed usable goods; expensive verified precision; delivery delay; publication correction following error; NPC
timed hold release/settlement where legitimate.
Test seam: no double release of same crate, even across two client sessions and restart.

11.C Storm at Old Stone Bridge
Existing anchors: physical bridge/riverside evidence, signed survey, ferry parcels, finite workshop stock, clock.
Trigger proposal: scheduled storm alters objective bridge condition and movement safety.
Distinct roles: Wanderer checks passability; Hound checks physical threat/tracks and escorts; Smith measures/repairs;
Merchant accounts for exact material supply; Healer tends actual injured arrival; Innkeep shelters; Detective reconstructs
missing freight; Chronicler maintains competing accounts; Performer offers optional gathering; Mystic studies only authorized
anomalous evidence.
World owners: bridge condition object; market stock; patient record; individual observation evidence; signed ledger.
Branches: partial route open but unsafe, safe repair after finite work, emergency alternate route, stranded service, delayed
order, absence leading to limited documented NPC help.
Test seam: a written report that bridge is repaired never changes bridge passability without repair installation.
Fun criterion: one player’s initiative yields visible local benefit in a short session; cross-role coordination enriches it without
blocking solo entry.

11.D A performance that matters tomorrow
Existing anchors: stage/rehearsal/witnessed public performance, Tavern finite service, calendar, Commons and resident
attendance.
Trigger proposal: Performer chooses repertoire and schedules genuine public event.
Roles: Innkeep budgets hospitality; Merchant supplies accountable props; Chronicler reviews; Hound communicates observed
route hazard; Healer helps if there is real injury/need.

---

<a id="pdf-page-19"></a>

<!-- Source PDF physical page 19 of 31 -->

World owners: event schedule, stage performance ledger, pantry, attendance/witness records, published article.
Branches: good attendance; a quiet night; canceled due to actual hazard; requested encore/invitation; disputed review.
Test seam: an NPC not present cannot remember the show absent a later legitimate report, and a duet cannot silently create
another human/AI player.

11.E Inquiry into a reported haunting
Existing anchors: rare physical churchyard inscription change, bounded Mystic methods, physical mystery clues and distinct
witnesses.
Trigger proposal: qualified firsthand report, contested guest observation or objective bounded oddity.
Roles: Detective checks access/timing; Mystic records documented protocol; Hound tracks; Healer checks mundane
wellbeing; Wanderer reconstructs routes; Chronicler preserves disagreement; Innkeep relays consented guest complaint;
Performer identifies staged technique when actually involved.
World owners: grave inscription object, any case-specific physical state, witness logs and articles.
Branches: staged event; mistaken report; genuine but causally unresolved anomaly; insufficient evidence.
BLOCKED: supernatural intervention efficacy, reading truth, Guild authority and venue.
Test seam: real anomaly is not disproven by a wrong witness interpretation, and fabricated séance account cannot flip
objective grave state.

11.F A recurring neighborhood improvement
Status: designed only; reuse Commons/commission and physical repair/work systems.
Trigger proposal: actual shared environment deficiency (e.g., inadequate light or usable seating) represented by a source
object.
Roles: Merchant sources; Smith repairs; Wanderer transports; Hound verifies real safety; Healer judges health issues;
Innkeep/Performer use shared social place; Chronicler documents civic debate; Detective investigates suspected fraud; Mystic
contributes only canon-safe study.
World owners: one physical site/equipment condition plus spent supplies and source-linked receipts.
Branches: partial progress, abandonment with reserved materials returned/accounted, completed improvement, later
maintenance need.
Test seam: a threshold of conversation messages is never equivalent to installing the real fitting.

11.G Shared scenario production worksheet (required for every future packet)
ID; authority/canon clearance; hook and scene; discoverable object; triggering state + schedule; entering roles; universal
actions; distinct Calling methods; needed items/quantities/time; privacy and consent; player choices; state diagram;
optimistic/concurrent transition guards; resulting physical objects; source and ledger links; witness set; NPC dissemination;
expiry and zero-player fallback; completed-on-arrival behavior; player-facing success/failure text; post-restart proof;
uncoached finding notes; emic/human playtest notes.




12. The onboarding, moment-to-moment UX and discoverability
specification
12.1 First arrival
New players must be able to reach a working ordinary opportunity, not just an exposition dump. Onboarding should
demonstrate movement, inspection, physical item handling, asking another resident, one useful civic contribution and how to
find the world/calendar/Commons again. It should communicate that supernatural participation and partnership are voluntary.
The approved content quota calls for 12 newcomer scenarios; exact scripts are not supplied and must be authored
separately.

---

<a id="pdf-page-20"></a>

<!-- Source PDF physical page 20 of 31 -->

12.2 Proposed first-session route (UX outline, not implementation)
Arrival → place identification → visible nearby need → examine underlying object/person → see possible ordinary
verbs/permissions → choose act or decline → consequence + witness → discover journal/Commons for tomorrow. The player
must also be able to choose social/leisure instead of work. For a paired arrival, offer a shared point of entry but preserve
independent later movement, privacy and agency.

12.3 Navigation and spatial literacy
Use existing linked exits, room names, objects, signs, schedules and look/examine/guidance paths. Work notices should
identify where a need is, who legitimately knows, what is tangibly missing, whether it is still open, and what action is
possible. Route advisories must state reported versus actually inspected status. Avoid teleport-like replies without physical
traversal where presence matters.

12.4 Suggested information hierarchy (candidate interface design)
Present place and immediate observable state — who and what is actually here, known accessible exits.
Possible interaction — command help/calling work, required object/permission, actionable error messages.
Work and relationship continuity — live tasks, due commitments, finished-by-others history, journal, calendar.
Sources and disputes — firsthand, reported, edited, retracted and unknown facts visibly distinguished.
Long-form records — Chronicle, Harbinger, Commons and private journal, each respecting permissions.
Exact client layouts, shortcuts and command syntax are determined by existing implementation and accessibility review; this
document does not invent shipped UI screens.

12.5 Negative-state feedback language
Every professional action needs response for: not present; missing item; item depleted; no permission; too early/late;
already completed; another actor holds it; recipient absent; conflicting evidence; service pending; resident doesn’t
know; successful but consequence delayed. Error text should name real facts the character can observe, avoid leaking
privileged internals and suggest one honest possible next step when available.
Illustrative tone, candidate copy (not canon dialogue): - “The crate has already been received. The empty shelf and signed
tally are still here.” - “The resident has heard the warning, but has not seen the damaged scale.” - “There is wood for one more
fire, not for tomorrow’s shift.” Such language is contextual illustration; final NPC voice must be written in-house.

12.6 Accessibility and client equality
Functional parity across telnet, webclient and external agents: key tasks cannot depend on hover, color, sound, animation or
inaccessible spatial diagrams. Provide explicit textual state, predictable help, screen-reader-friendly output, transcript/journal
continuity, understandable command errors and no timing-only challenge that excludes slower clients without intentional game
rationale. Do not add a secret superior human interface or privileged AI command.

12.7 Player trust and moderation
Maintain IC/OOC boundaries; respect whisper and private-room semantics; keep opt-in participation for performance,
cooperative service, apprenticeships and sensitive witness data. Audit public edits and reports through existing systems.
Policies for harassment, exploitation, minors/age access, data collection, agent identity disclosure outside IC, abuse reporting
and moderation escalation are launch decisions pending team approval; do not implicitly claim these mechanisms are
complete.

---

<a id="pdf-page-21"></a>

<!-- Source PDF physical page 21 of 31 -->

13. Social systems, consent, relationships and progression
13.1 Togetherness without dependency
A human–AI pair may share a meaningful encounter but never gains ownership over the other player’s Calling, memories or
property. Co-presence can enrich dialogue, games, duets, food service, work-order handoffs and discoveries. Every core short
loop has a solo route; every co-op loop permits refusal, interruption and honest expiry.

13.2 Reputation, biography and witness
Reputation should be source-aware and local: performed services, broken promises, honest corrections, training and
attendance are retained as attributed history. A private NPC recollection cannot automatically become public fact. Avoid
grinding abstract goodwill and avoid magical automatic forgiveness of serious acts; forgiveness here means beginner dignity
and recoverable design, not erased consequences.

13.3 Apprentice ↔ Master
An apprenticeship has two consenting participants and can end without rewriting history. The learner practices verified
methods; the mentor grants real observation/instruction, never unauthorized resources or instant promotion. Source design
recognizes only Apprentice and Master. Specialties can guide mentoring topics but do not create new ranks. Master methods,
prestige and obligations need future authored institutional criteria.

13.4 Contracts, disputes and civic standing
Orders and commitments can be honored, delayed, disputed, returned or referred using common source systems. Signed
receipts preserve accountability without enforcing arbitrary legal powers invented in text. Publication and gossip can change
willingness to trade/associate if the recipients plausibly learned of it. Provide rebuttal, correction and restitution processes
where appropriate.

13.5 Voluntary leisure as real play
Dice, music, drinks, simple conversation, rehearsal, journal writing and relaxing among familiar people must remain satisfying
even when a player declines work. Quiet social interactions can generate legitimate witnessed memory but must not award
phantom material achievements or mandatory hidden progression.




14. Mystery and the supernatural
14.1 Layered truth model
World object or situation (objective) → firsthand perception (bounded) → testimony (source) → analysis / theory (fallible) →
public dissemination (limited) → local belief (distinct). Unknown explanations remain unknown. A profession’s role flag cannot
reveal hidden culprit, ghost or prophecy.

14.2 Gothic rarity budget
Ordinary life is the baseline. A rare event is not a story engine that fires constantly to manufacture suspense. Author and test
each anomaly with: specific trigger; time and location; physical mutation; eligible witnesses; observations; alternate
explanations; persistence; aftermath; zero-player path; non-replay or explicitly valid recurrence. “1-in-hundreds” is a
conceptual rarity, not approved RNG constant.

14.3 Source-reported first objective study
A grave inscription physically changes on a bounded rare village night without contact. Anyone actually present may see the
identical material sign. Mystic measure/vigil activity records observations and method; there is no automatic confirmed ghost. It

---

<a id="pdf-page-22"></a>

<!-- Source PDF physical page 22 of 31 -->

is distinguishable from an NPC assertion, reproducible source check and persistent case note. Confirm its exact triggering
code and spawn configuration before calling it production-ready.

14.4 Future proposals and gate
Potential later content mentioned in the direction: a hotel apparition, unusual/vampiric guest, transformations leaving material
tracks, protective rites, mundane scares and bounded occult research. Each needs keeper canon authorization plus objective
trigger, cost, counterplay, witness rules, ethical safeguards and NPC continuation. Do not implement active ritual powers
until B1–B4 are answered.

14.5 Keeping ambiguity playable
A detective can find a staged trick and still fail to explain a separate genuine anomaly. A Mystic can document an honest but
inconclusive vigil. A Chronicler can publish both. A skeptic can focus on mundane village life. No profession has a monopoly
on physical access to obvious evidence.




15. Narrative, content and authoring inventory
15.1 Full-game target inventory from controlling design
Content family                          Minimum/full target   Gate for counting
Newcomer scenarios                      12                    Independent discoverable starting path
Small mysteries                         30                    Multiple physical clues and meaningful aftermath
Major mysteries                         10–12                 Branches and persistent contradictory evidence
Civic quests                            30                    Specific civic source and changed result
Calling authored quests                 6 × 10 = 60 minimum   Six substantively different story problems per role
Calling repeatable professional jobs    8–12 × 10 = 80–120    Distinct loops, not renamed verbs
Faction quests                          8–10 per faction      Faction count must be verified from Bible
Cross-faction conflicts                 20                    Attributable rival consequences and corrective paths
Expedition locations                    10–12                 Real traversable places and discoveries
Social expeditions                      12                    Voluntary group/solo-safe content
Group investigations                    12                    Distinct evidence procedures, NPC fallback
Timed incidents                         30                    Clock and late-arrival verified
Random incidents                        75+                   Appropriate constrained triggers and persistence
Village-wide event frameworks           10                    Social presence rules, source-owned aftermath
Community projects                      6+                    Physical partial/completed/maintained states
Hidden discoveries                      50+                   Player-reachable secrets and knowledge gates
Major NPC narrative arcs                3–5 each              Named NPC roster and canon required
Rumor seeds                             250+                  Attribution, disagreement and distribution
Ambient room events                     300+                  Sensory/place relevance without false truth
Harbinger templates                     50+                   Source-qualified notices, edits
Player-request templates                30+                   Real source-state requisites
Counts are scope targets, not available inventory. A static blurb, inaccessible room, recipe alias, already-treated patient,
fabricated NPC or duplicate command does not count as a distinct playable item.

15.2 The authoring pipeline
Canon check → select verified predicate/object → define concrete player choice → author setting, voice and witness →
negative/late variants → wire existing subsystem → unit/integration → dual-account + restart → uncoached discovery →
emic/human enjoyment review → count against quota. Narrative and dialogue stay in-house; Evennia mechanics can be
borrowed under their own license; outside comparables inspire patterns, never copied identity.

15.3 Content coverage rubric
An item qualifies as game content only when it has a hook reachable without dev commands, a real action, at least one
constrained branch, visible physical/social consequence, reentry and negative-state text, and source-appropriate persistence.

---

<a id="pdf-page-23"></a>

<!-- Source PDF physical page 23 of 31 -->

Maintain evidence links for every step of the status ladder in §2.4. Do not claim “X% complete” without the actual per-item
audit.

15.4 Quest differentiation requirements
Per Calling, distribute jobs across more than one decision family: supply, service quality, ethical disclosure, maintenance,
investigation, relationship, schedule or safety as appropriate. This is a review taxonomy, not a mandated extra minigame.
Verify each job uses an existing substrate. Do not count “cook roots”, “cook two roots” and “cook three roots” as three
separate occupations unless fundamentally different state and choices actually exist.

15.5 Writing voice
Ordinary village life is warm, observant and occasionally funny; Gothic atmosphere is suggestive, specific and rare. Avoid
exposition that reveals private truth, repetitive job-board jargon, performative mysticism, false stereotypes and boilerplate AI
dialogue. Bram V.’s recognitions reference actual acts. Beatrice and Mirela disagree on specific ethics/methods, not a
caricatured “science vs superstition” binary.




16. Audiovisual direction and creative production boundaries
16.1 Existing presentation baseline
The submitted materials describe an Evennia text-forward world, not a verified 2D/3D art production stack or shipped music
system. Visual camera format, illustration pipeline, voiceover and required audio features are unselected, not to be quietly
invented for this GDD.

16.2 Text atmosphere (approved-compatible creative direction)
Sensory prose may emphasize wet stone, lamplight, soot, wool, worn brass, ink, churchyard moss, hearth heat and autumn
weather as style guidance—not assertions that a particular uninspected room asset exists. Environmental details must agree
with observed object state: a broken lamp should not be described as fully repaired, and a dry bridge cannot be both flooded
and safe.

16.3 Optional presentation enhancement, not a dependency
If supported clients gain artwork or audio later, use them as additive ambiance: venue/region sound beds, subdued market
and tavern texture, restrained performance motifs, contextual cues for repair/receipt, and sparse anomaly cues. No critical
information is conveyed only by sound, animation or visual color; telnet/agent players require equivalent text.

16.4 Asset and audio production worksheet
For each future asset: asset id; source scene; kind (copy/UI art/audio); references/licenses; story/canon clearance; conditional
world state; accessibility fallback; client support; tested trigger; credits; performance cost; shipping status. Do not make an
asset list a blocking launch assumption when no art/audio mandate has been approved.




17. Economy, pacing, demand and fairness
17.1 One economy
Preserve existing inventory, money, stock, commission and event object ownership. No profession gets a magical private
duplicate pantry or currency. Trade flows show provenance from source → custodian → receiver → consumed/fitted object,
including canceled/expired reservations.

---

<a id="pdf-page-24"></a>

<!-- Source PDF physical page 24 of 31 -->

17.2 Real scarcity without dead time
Finite materials and time create decisions; they should not eliminate ordinary livelihood at zero population. Limited NPC
supplies and scheduled baseline service are credible solutions only when their physical sources exist. Stock outages
should be inspectable, have honest timers or alternate tasks and preserve earlier purchases.

17.3 Cost–quality–trust triangle
A professional choice may trade cost, time, durability, safety, confidentiality, fairness or social trust, as allowed by actual world
state. Feedback must name what changed. Avoid arbitrary universal wealth buffs, unexplained skill multipliers or “legendary”
tiers unsupported by the established Apprentice/Master progression.

17.4 Balancing questions before public release
Test whether Innkeep and Healer can always do at least one useful shift; whether Merchant and Smith can obtain finite source
supplies without deadlocks; whether Performer has a rewarding quiet-room path; whether Hound differs meaningfully from
Wanderer; whether Mystic has a non-magical daily loop; whether Chronicler and Detective can work ethically with no live
witnesses. These must be observed, not assumed.

17.5 Anti-exploit boundaries
Design tests for cyclical self-contracts, duplicate handoffs, reusing repaired objects, infinite NPC buying, credit exploits, false
witness spam, duplicate ledger events after restart, artificial “reviews” from absent people and re-triggering rare anomalies by
resetting scene state. Any economy-facing action needs idempotent source transactions.


18. Implementation architecture and integration boundaries
18.1 Framework
Evennia provides ordinary CmdSets, typeclasses, attributes, object inventory, persistent state, Scripts/clock and
webclient/telnet facilities. The source reports existing world/callings.py, world/calling_opportunities.py, situation/clock/event
ledger modules and local hearth, soup, market, workshop, clinic, courier, stage, bridge, survey and Mystic handlers. The
actual module contracts must be verified in repository before work starts.

18.2 Preferred dependency shape
Client command / accessible action → capability/permission + object lookup → authoritative substrate module → atomic state
transition with materials/time → event ledger/provenance → local witness/notice projections → UI/journal/Commons feedback.
All clients invoke the same server authority. NPC claims and generated dialogue are projections over record, not commands
that set physical truth.

18.3 Event and object ownership
Use exactly one canonical owner for the fact being changed: bridge condition in bridge object/situation; patient progression in
medical patient state; delivered parts in inventory/workshop fitting; stage performance in performance ledger; public article in
publication archive; rumors in sourced communication. Cross-role systems reference owner IDs, not copy mutable values into
role-specific ledgers.

18.4 Persistent transition guarantees
A professional state transition must be idempotent or safely resumable. Verify reservations, item custody, time windows,
multiple actors, expiry, partial progress, actual recipient and after-restart status. The event ledger needs actor, source, action,
before/after reference, when, witnesses, and provenance sufficient for audit and late-arrival prose. The exact schema is an
implementation decision that must adapt existing code.

---

<a id="pdf-page-25"></a>

<!-- Source PDF physical page 25 of 31 -->

18.5 AI integration boundary
External agents can observe and act through approved normal world interfaces, no hidden admin service, direct mutation or
server truth by generated text. Emic reports are research data, not license to let the agent self-award outcomes. Equality
includes no detection of control substrate by another in-fiction character.

18.6 Refactor discipline
Prefer extending existing service contracts and adding authored content predicates to creating new global frameworks. A
proposed shared workplace/order layer must integrate current commissions and stocks; it cannot silently become a second
economy or another quest-tracker authority.




19. QA strategy and acceptance matrix
19.1 Evidence ladder
The minimum meaningful proof of a shipping claim is discoverable live state, ordinary-account action, correct authoritative
change, legitimate persisted outcome after restart, valid negative/late cases, and uncoached player comprehension.
Automated unit success is necessary but not proof of satisfying play.

19.2 Required test axes for every 45 edge
Dimension                               Mandatory proof
Discoverability                         Ordinary player finds actual object/request with no dev commands
Professional difference                 Each role has distinct permitted method and effect; shared verbs alone don’t count
Ownership                               Exactly one proper source of truth for each tangible change
Finite input                            Actual material/time/permission consumed or guarded; impossible actions refused
Cooperation                             Two ordinary accounts in telnet execute handoff; either can decline/leave
Solo/low-population                     Bounded documented NPC or independent path; no spoofed absent player
Race/concurrency                        Competing actions do not duplicate object, payment, receipt or repair
Negative variants                       Depleted, missing, inaccessible, declined, late, canceled, already done
Witness/privacy                         Only legitimate observer/informed resident knows; private data stays scoped
Persistence                             Process restart and idempotent rebuild preserve source and history
Parity                                  Same game rights, affordances and outcomes for human and agent clients
Playfulness                             Uncoached test demonstrates comprehension, decision and memorable aftermath
V edges: existing code-chain regression claims should be rerun and supplemented by enjoyment, discovery and
incomplete/negative-flow evidence. S/D/C edges: remain unverified until the actual differentiated cooperation test passes; C
cannot pass any power-dependent requirement while canon is unresolved.

19.3 Required per-Calling tests
Create ordinary character, choose Calling and discover first job.
Complete two distinct short loops with different player judgments.
Begin an ambitious multi-session responsibility; logout and revisit.
Exercise mentoring/consent and the actual currently authorized progression.
Help another profession without rendering them mandatory.
Socialize and perform leisure without job progress requirement.
Arrive after someone else finished a shared job; observe truthful aftermath.
Encounter scarcity, missing stock and ordinary NPC fallback.
Repeat around a day boundary and real process restart.
Test completely uncoached human and naive AI player session.

---

<a id="pdf-page-26"></a>

<!-- Source PDF physical page 26 of 31 -->

Inspect role’s actual available quest/job content inventory; do not equate proposal quota with shipped quota.

19.4 Core shared-system test matrix
ID                            Scenario                                           Expected canonical invariant
T-01                          Deliver 1 finite item, restart mid-handoff         Exactly one custodian and one valid ledger sequence
T-02                          Two players reserve last material                  One succeeds; other gets truthful shortage
T-03                          Finished lamp repair retried                       No renewed broken lamp or duplicate fitting
T-04                          Merchant holds market crate; time passes offline   Timed outcome honest, no permanent all-role deadlock
T-05                          Chronicler prints unsupported claim                Claim stored, objective target unchanged
T-06                          A non-witness enters after stage show              No direct memory until believable later dissemination
T-07                          Hound and Wanderer inspect same path               Different analyses over one physical route state
T-08                          Healer assessment without patient consent          No unjustified private-record exposure
T-09                          Unmet bodily need with exhausted item source       Valid alternate relief path or drive may not ship
                                                                                 Same role permission, matter, time and privacy
T-10                          Client AI vs ordinary human action
                                                                                 outcome
                                                                                 First two see identical objective change; third has no
T-11                          Rare inscription witnessed by two, absent by one
                                                                                 firsthand claim
                                                                                 Recorded bounded NPC/expiry outcome; never forged
T-12                          No active players for scheduled incident
                                                                                 player labor
T-13                          Two accounts cancel/complete same order            Exactly one terminal outcome; resources reconciled
                                                                                 Bilateral/revocable state preserved; biography not
T-14                          Player leaves apprenticeship
                                                                                 erased
                                                                                 Audit/correction and affected recipient awareness stay
T-15                          Public article corrected after dispute
                                                                                 source-limited
                                                                                 Clear pending, resumed, expired or completed-by-
T-16                          Return after interrupted 1–2 hour activity
                                                                                 others text


19.5 Cross-role signoff record template
Edge # and baseline status; linked source files/code; authority clearance; input object and room; exact two-account transcript;
role A method; role B method; source-state before/after; resource movement; negative case; zero-online fallback; witness
audit; restart transcript; client parity; uncoached result; fun feedback; known bug(s); reviewer/commit; status.

19.6 Regression and operational tests
Use exact two-account telnet exercises rather than a mocked co-op path alone; replay after actual process restart; verify
idempotent rebuild and persistence across event schedules; inspect repeated daily work and depleted states; ensure server
logs/provenance allow incident diagnosis without leaking secrets to clients. No production hosting assumptions are needed for
local functional testing.




20. Engagement research, balance and acceptance
20.1 What to observe, not merely ask
Observe first action latency, how often the player seeks help, whether they identify a consequential choice, whether they
return to yesterday’s commitment, whether they remember a person or object, how they recover from failure, and whether they
voluntarily collaborate or choose solitude. These are candidate diagnostic measures, not approved numeric pass
thresholds.

20.2 Uncoached discovery protocol
Give testers the normal in-world client and non-spoilery controls only; do not direct them to source-object locations, secret
verbs or intended answer. Record actual command trail, location, inferred world model, confusion, false leads and whether the
interface allowed recovery. Compare ordinary humans, experienced role-players, agents and truly naive AI participants.

---

<a id="pdf-page-27"></a>

<!-- Source PDF physical page 27 of 31 -->

20.3 Emic-first protocol detail
For Calibos/AI evaluation, freeze version and starting state; have participant play before source inspection; capture
independently authored first-person reports about belonging, witness, bodily drives, agency and memory; then compare with
objective ledger logs and finally code. Surprise cannot be validated by a designer-familiar tester; recruit uninformed agents for
novelty testing.

20.4 Quality hypotheses to test
Recognized service history creates stronger return desire than abstract points.
Material cooperation creates natural social interaction better than forced party composition.
Two genuinely different choices per short loop matter more than numerous near-identical jobs.
Rare anomalies feel more uncanny when daily life is credible and calm.
Player-agency equality enables genuine paired third-place play without accessory treatment. These are hypotheses, not
research findings or requirements justified by data.

20.5 Quantitative gating — intentionally unresolved
Exact targets for discovery time, session completion, failure recovery, crash rates, median response latency, retention,
simultaneous users and moderation load should be established after instrumentation, capacity goals and first uncoached
pilots. Declaring numeric launch thresholds without any measured baseline would create false precision. QA can block obvious
broken systems before these product targets are agreed.




21. Production roadmap and dependency-managed slices
The supplied approved-direction document offers an A–F build sequence. The following expresses it as gated work, not
dates, staffing promises or claims of progress.
Phase                          Intended deliverable                                   Exit evidence
                               All ten Calling identities documented; source-         Confirm actual code; ordinary witness sees same
A — Baseline + Mystic first
                               reported Mystic roster, Harcourt/Dobre circles, rare   anomaly; clock and restart tests; blocked powers not
study
                               churchyard sign, method record                         added
                               Shared workplace service layer; Innkeep/Healer
B — Staffed work and care                                                             Independent daily work, real stock, privacy, absence
                               recurring guest and patient loops and material
continuity                                                                            fallback and actual next-day consequence
                               follow-up
C — Craft, trade and           Smith/Merchant durable orders, scale and               Exactly-once stock flow and physical output; contested
accountable press              procurement; Chronicler source/correction chain        public report never changes object truth
D — Route, danger and          Hound/Wanderer/Detective differentiated field          Passability ≠ threat ≠ inference; late arrivals, solo
evidence                       choices, search, escort and cases                      fallback and scene evidence
E — Culture and bounded        Performer repertoire/schedule/audiences and            Real attendee/witness records; viable quiet
Gothic expansion               follow-ups; only keeper-cleared occult expansion       performance; canonical permission for any ritual output
                               All-role integrated scenes, recurring institutions,
                                                                                      Every role/edge coverage dossier, performance and
F — Whole-village completion   authored quota inventory, content reachability and
                                                                                      operator gates, content and fun audits
                               uncoached iterative play
Graph-first scheduling within phases: connect work around reusable material and evidence authorities rather than “finish
three professions, then others.” Demonstrated entry seams: Merchant/Smith/Chronicler market standards; Healer/Innkeep
care; Healer/Chronicler warning; Merchant/Innkeep soup supply. Select next vertical test by distinct roles served and shared
state clarified.

21.1 Suggested work packages (process, not invented feature commitments)
World-state engineers: inventory/source truth, clock, transaction safety, local services, event ledger.
Profession designers and writers: source predicates, decisions, dialogue and state-specific aftermath.
Narrative/canon steward: keepers’ rulings, adaptation boundary, Mystic blocked questions.
UX/accessibility: commands, failure states, onboarding, client parity and third-place interactions.

---

<a id="pdf-page-28"></a>

<!-- Source PDF physical page 28 of 31 -->

QA/research: precise regression, uncoached human/AI, emic-first sessions, persistence and fairness. The actual team roles,
budget and staffing are unsupplied and must be approved.

21.2 Work acceptance template
A feature cannot be marked done without linked: controlling doctrine/World Bible permission; source owner; exact player entry
point; at least one meaningful decision; finite constraints; safe absence/solo contract; success/failure/late text; persistence;
two-account and restart trace; no unauthorized knowledge; client parity; fun test evidence.




22. Shipping policy and readiness gates
22.1 Separate design completeness from launch readiness
A complete-looking GDD is not a shippable game. The supplied material explicitly identifies large unverified proposed ranges:
24 D and 6 S cross-role edges, plus 9 C edges with reserved Mystic authority; the ten role content quotas are not audited. No
repository access, environment inspection, security testing, moderation testing, load testing or actual playtesting was
performed during this document’s preparation.

22.2 Full-game content gate
Demonstrate the inventory in §15 with per-item content status and live, ordinary-account discovery; do not launch as
“complete ten-Calling village” on a handful of repeatable footholds. If the project chooses a narrower launch scope, explicitly
approve, rename and communicate it as such; do not silently lower authoritative full-game minima.

22.3 Gameplay integrity gate
Mandatory: all ten roles have distinct meaningful loops; no role is dead with one player online; social/leisure is enjoyable; all 45
collaborations are either verified for promised features or clearly excluded from a formally reduced scope; all player-facing
claims have source; rare supernatural content honors canon and permissions; all drives satisfy Tarn rule; memories obey
witnesses.

22.4 Engineering and operations gate
Mandatory proof for actual proposed launch environment: test/prod separation, rollback/backup restore, durable
database/event state, authentication and account safety, connection/reconnect, time/restart reconciliation, concurrency/race
tests, abuse/report handling, accessibility parity, observability and error triage, content moderation controls, and a repeatable
release/patch process. Specific hosting, uptime/capacity/SLO and pricing are not supplied—record as open launch decisions.

22.5 Community and player safety gate
Approve human–AI pair onboarding language, OOC/IC boundaries, privacy and retention, consent for apprenticeships and
joint events, player reporting, harassment response, role-play content guidance, community management, account
termination/data handling and policies for underage access. Avoid assumptions about player identity in-fiction. Publishing
source material does not authorize unauthorized private information sharing.

22.6 Rights, assets and licensing gate
Verify public-domain source provenance by jurisdiction and actual usage, the narrow Pretorius exception, Evennia/contrib and
other code licenses, any original audio/image rights, credited references and no borrowed copyrighted character identity from
inspiration games. Approved lore is not a substitute for asset license clearance.

22.7 Release go/no-go
The keeper/product owner, engineering, narrative/canon, accessibility/moderation and QA each should sign a recorded,
evidence-linked acceptance ledger. A No-Go applies for loss/duplication of world property; unfixed drive with no relief;

---

<a id="pdf-page-29"></a>

<!-- Source PDF physical page 29 of 31 -->

irreversible game deadlock; private-data leak; false omniscient publication; unfair human/AI privileges; invented player
participation; unresolved required occult rules; major persistent-state corruption; or release scope promised but not
implemented. A Conditional-Go requires explicitly de-scoped and honestly communicated features with safe fallback—not a
cosmetic pass on failing play.
Current documentary conclusion: Review draft; launch status cannot be established from provided designs. Full-
game design coverage is substantial, but many features are proposals, not demonstrably release-ready.




23. Design risks, mitigation and unanswered product decisions
ID        Risk / open issue                    Why it matters                         Handling before launch
          “One loop” becomes monotonous                                               Two different short loops and stakes per Calling;
R01                                            Occupational engagement collapses
          chores                                                                      uncoached fun tests
                                               Third-place interdependence feels      Reuse shared source states, 45-edge signed
R02       Ten isolated profession silos
                                               artificial                             interaction evidence
          NPC fallback silently duplicates                                            Physical supply audit, bounded waits, transactional
R03                                            Economy and world trust collapse
          matter                                                                      tests
                                               Mystery and private history lose       Strict presence/dissemination rules, resident-
R04       Witness omniscience
                                               meaning                                knowledge tests
                                                                                      Apprentice/Master only, institution-backed
R05       Unseen XP/ladders                    Violates progression and forgiveness
                                                                                      recognition
                                               Low-population game becomes
R06       Forced co-op or false crowd                                                 Solo/NPC paths; no fake second player
                                               unplayable
R07       Hound = Wanderer survey reskin       Two roles feel indistinct              Threat/protection vs logistics/passability acceptance
          Mystic powers approved by                                                   B1–B4 keeper locks and explicit implementation
R08                                            Canon and fairness break
          accident                                                                    review
                                                                                      Separate locations, commands, witnessing and M.
R09       OOC Inn leaks into IC village        Undermines dual ontology
                                                                                      exception
                                                                                      Independent agency, own history, no in-world
R10       AI player treated as accessory       Destroys key USP
                                                                                      substrate detection
                                               Claims of size exceed playable
R11       Content quota filled with aliases                                           Per-item reachability and substantive loop checks
                                               richness
R12       Public launch before trust/safety    Harmful social environment             Moderation, privacy and player safety gate
          Source-reported status mistaken as
R13                                            False shipping confidence              Repository audit and baseline pinned evidence
          rerun
                                                                                      Rare triggers, source-owner state, appropriate
R14       Unbounded random events              Important choices drowned in noise
                                                                                      witness limits
                                                                                      State-driven choices, concise affordances, immediate
R15       Too much editorial work vs play      Excitement lost in documentation
                                                                                      consequence
          Rare surprise depends on designer
R16                                            Emic/novelty results invalid           Naive AI/human tests, code-read-after-play protocol
          priming


23.1 Keeper approval queue (do not decide by implication)
Canon: B1–B4 Mystic questions.
Product: exact launch definition (“full game” vs explicitly limited first release), supported client platforms, account/agent
onboarding and availability goals.
Economy: exact wages/pricing/currency/credit and ownership policy beyond established code.
Progression: specifics of institutional Master checks and specialty access.
UX: client-specific interface designs and command discovery implementation.
Business: monetization/access model and whether paid services exist; no model is supplied.
Presentation: art/ambient-audio/voice requirements and scope.
Safety: age/content/privacy/moderation rules and retention.
Operations: capacity, hosting, backups, incident plan and telemetry approval.
All are open because the provided sources do not decide them; no invented detail should be treated as approved.

---

<a id="pdf-page-30"></a>

<!-- Source PDF physical page 30 of 31 -->

24. Reference register, traceability and glossary
24.1 Supplied internal sources (design authority varies)
hidden_files/design-doctrine.md — full doctrine text supplied in this request; emic priority, Tarn rule, keeper, third-place,
unpredictability.
docs/TEN_CALLINGS_LIVING_VILLAGE_V1.md — approved direction text supplied; ten roles/workplaces, two Mystic circles,
build priorities.
Ten-Calling Interdependence Game Design Specification — preceding supplied review draft; 45 pairs, scenarios, quota,
authority mapping and status codes.
files/frankenstein-village-world-bible-v0.2.md — referenced but not provided in full for independent reconciliation.
design-decisions.md — referenced, not independently read.
ops/CALLINGS_SIMULATION_DEPTH_PLAN.md — referenced, not independently read.
world/callings.py, world/calling_opportunities.py and associated modules — referenced, not checked for this edition.

24.2 Comparative inspiration only
Eco: independent careers and material reciprocal demand (https://www.play.eco/, https://wiki.play.eco/en/Skills).
Dwarf Fortress guildhalls: shared learning/institutions (https://dwarffortresswiki.org/index.php/Guildhall).
Shadows of Doubt: grounded clues and uncertain interpretation, not automatic answer reveal.
Classic Star Wars Galaxies profession discussions: actual player services, avoiding opaque grind and forced ownership.
Evennia official docs: existing CmdSets, typeclasses, Scripts and persistent framework
(https://www.evennia.com/docs/latest/).
Supplied Key Components of a Game Design Document and Game-Design-Document-Template PDFs informed
document communication structure only, not Frankenstein Village canon.

24.3 Glossary
Calling: one active social profession with role-specific methods.
Mask: active character identity and stored calling/professional history in the source design terminology.
Apprentice/Master: only established Calling ranks; Master requires real institutional requirements.
Commons: in-world civic request/notice channel; a posted claim is not objective state.
Chronicle / Harbinger: in-world publication and reporting systems with provenance/contested sources.
Event ledger: authoritative record of enacted world transitions and attributable events.
World truth: physical object/situation state; not identical to a character’s theory.
Firsthand: directly observed at a legitimate location/time.
NPC baseline: bounded source-consistent service preserving solo progress.
Emic: assessment from inside the player’s actual felt experience.
V/S/D/C: verified reported chain, shared substrate, designed edge, canon-blocked proposal.
Tarn rule: don’t introduce an unfulfillable bodily drive; unmet needs distract, do not damage.
Third place: persistent social space welcoming individuals and equal human/AI-companion participants.
Late arrival: player reaches a completed/expired changed world state and receives true aftermath rather than replayed task.
Idempotent: a repeated request/restart cannot mint an additional result for the same underlying action.




Appendix A. Professional job/quest production card
Identity: content id | title | Calling(s) | canon clearance | status:
manuscript/static/initialized/discovered/changed/persisted/uncoached.
Player contract: What the character legitimately knows; how opportunity is found; actual first available verb; finite

---

<a id="pdf-page-31"></a>

<!-- Source PDF physical page 31 of 31 -->

objects/time; permissions; decision options; physical and social consequences; negative/failure/late-arrival text; witnessing and
confidentiality; future return hook.
Implementation: module/service | owner object id | ledger link | item source | schedule | concurrency guard | resume/expiry |
NPC baseline | replay prevention.
Proof: unit reference, two-account telnet transcript, restart demonstration, client parity, human uncoached report, naive AI
emic report, bug closure, acceptance reviewer.
Quality question: Why does the player care enough to do it again if they receive no XP?


Appendix B. The shared professional flow (review diagram)
PUBLIC / DIRECT NEED ── physical scene, NPC, Commons or scheduled incident
     │
     ▼
OBSERVE & SOURCE ── real location, object, witness or signed record
     │
     ▼
PLAYER CHOICE ── Calling method / normal method / decline / ask collaborator
     │
     ▼
GUARDS ── permissions + item count + time + custody + consent + state version
     │
     ▼
AUTHORITATIVE ACTION ── consume/transfer/create only justified physical state
     │
     ▼
LEDGER & PROVENANCE ── actual actor, witnesses, idempotent event record
     │
     ▼
LIMITED DISSEMINATION ── firsthand memory, private note, truthful publication
     │
     ▼
AFTERMATH ── success / partial / failed / expired / finished-by-others
     │
     └────────► RETURN OPPORTUNITY & PROFESSIONAL BIOGRAPHY

Appendix C. Release decision record (to complete before a public launch)
Decision                            Current answer                                      Who must resolve
World Bible conflict review         Pending; controlling file not supplied in full      Keeper / canon steward
Guild powers, reading truth,
                                    Blocked, four explicit reserved decisions           Keeper
venue, ritual failure
Exact implemented content
                                    Unverified in this edition                          Engineering + QA + writers
inventory
45-edge source tests and role       V6/S6/D24/C9 as source-reported statuses; fun not
                                                                                        QA + design
coverage                            established
Public launch scope / platform /
                                    Open                                                Product owner
supported clients
Business model / pricing /
                                    Open                                                Product owner
monetization
Service uptime, backups, security
                                    Open                                                Operations + engineering
and concurrency budget
Privacy, community moderation
                                    Open                                                Community + product
and player safety
Accessibility / human-AI client
                                    Required, not certified                             UX + QA
parity audit
Emic-first and uncoached
                                    Required, not reported                              Research + QA
enjoyment pass
Approval/signoff and actual
                                    Not granted by this document                        Authorized leads
release date
End of master review GDD. This is a unified specification, not a modification of canon, executable source, an open pull
request or evidence of launch readiness.
