# Frankenstein Village: Ten-Calling Interdependence Game Design Specification

**Status:** REVIEW DRAFT / design synthesis, *not* a change to the World Bible and *not* implemented gameplay.
**Source baseline:** Azimn/frankenstein-village main 9b16f73f1acec60cd7803476caaa744a5be4a42f, 2026-10-25.
**Scope:** The complete game, all ten Callings, all 45 pairwise overlaps, shared systems, player loops, progression, consequences, social play, content production and cross-role QA. This is **not** a hosting or early-alpha checklist.

## 0. Authority and how to read this design

This document **unifies, does not replace** the existing approved design:
1. hidden_files/design-doctrine.md (including “invent each loop once,” third-place, source skepticism, ordinary human/AI equality);
2. files/frankenstein-village-world-bible-v0.2.md (canon and open questions);
3. design-decisions.md (one active Calling, bilateral apprenticeships, authoritative event ledger, property model, no instant promotion);
4. docs/TEN_CALLINGS_LIVING_VILLAGE_V1.md (approved ten-Calling direction and proposed specialties);
5. ops/CALLINGS_SIMULATION_DEPTH_PLAN.md (systems reused and verified market chain);
6. actual code: world/callings.py, world/calling_opportunities.py, typeclass objects, situation/clock/ledger modules, and real command/world handlers.

Where this draft conflicts with a higher authority, **higher authority wins**. Nothing new here modifies current canon or grants a profession a new authority. Existing means source-and-integration-backed at the baseline; it does not mean playtested for fun, full content density or production-ready. “Proposed” is a design target, not a command that exists. Future playtest and code reviews must update factual status before describing a behavior as shipped.

## 1. What a player actually does

**Player fantasy:** Live in a Victorian Gothic village that continues between sessions. Choose a social vocation because its work, obligations, tools, expertise and relationships make a meaningful difference to the place. Food must come from somewhere; repairs require matter and time; roads carry people and goods; investigations depend on evidence; publications influence *beliefs*, not physical truth. Every Calling has ordinary life, voluntary social activity, an immediate occupation, difficult decisions and longer-term professional ambition. The supernatural is real in the world, but rare and not obligatory.

**Universal actions:** Move, look, examine, speak, listen, trade/hand over permissible objects, inspect the calendar and public Commons, hold intentions, preserve journal entries, investigate public phenomena and participate socially. A Calling may change the *method, efficiency, expertise, risk, trust or appropriate institutional capacity*, not create separate physics or gate all basic play.

**Session arcs:**
- 5 minutes: recognize a current neighborhood need, choose one of several legitimate directions, inspect a tangible object/person/event.
- 20–40 minutes: complete a modest professional or civic contribution and see *who or what changed*.
- 1–2 hours: take part in a multi-stage order, investigation, social event or service; make at least one consequential choice and experience another Calling's contribution, whether from a player or credible NPC.
- Next real session: hear or inspect a changed local state, follow up a promise/claim/service, pursue something newly relevant, and carry the consequences into an evolving professional biography.
These are **design targets**, not verified player timings.

**The common loop, authored ONCE:** Notice live need/event -> inspect source state -> choose role-specific method -> verify real prerequisites -> perform action (finite object/time/permission) -> authoritative state transition -> signed provenance -> inform only plausible witnesses/institutions -> display open/finished/failed/late-arrival text -> re-enter with next legitimate opportunity. Reuse the clock, property vocabulary, situation records, Commons, scheduled events, event ledger, resident memory and normal Evennia commands. Do not build ten quest engines, ten economies, or a new agent orchestration layer.

## 2. Invariants and technical owners (reuse, don't reconstruct)

| World fact or service | Current owner / established substrate | Rule for all Callings |
| --- | --- | --- |
| Time, deadlines, scheduled encounters | Village clock; scheduled/timed/random/server event modules | Only one canonical clock. A deadline is not paused by player logout. |
| Physical item, condition, worth, toxin, fuel, uses | Evennia objects + mechanic tags + db.mechanic_values | Inventory physically moves/spends; prose cannot mint an object. |
| Finite wood, pantry, workshop, market, clinic, courier | Existing community_hearth, soup_kitchen, market/workshop/clinic/courier subsystems | Use each subsystem's source of truth. No parallel profession stock ledger. |
| Objective incident/repair/need | Situation/incident state, world event ledger and specific world objects | An NPC claim, Commons note or role title cannot set objective truth. |
| Civic communication, referrals, player requests | Commons, rumor registry, Chronicle, Harbinger | Notices are claims until action emits an actual consequence. Keep source, edit and moderation history. |
| Profession, Master, apprenticeship | world/callings.py mask calling_state | One active Calling. Existing Apprentice/Master ranks only. Master promotion through authored institutional checks, never invisible XP. Apprenticeship is bilateral and revocable. |
| Witnessed memory and testimony | firsthand discoveries, resident awareness, public/private mysteries | Only physically present or legitimately informed witnesses know. Rumor and interpretation remain distinct. |
| Place, visits and services | Existing rooms, linked exits, NPC schedules, stations | Work is at actual places. Shared facilities, no obligation to own a shop/hotel. |
| Normal controls and accessibility | Evennia CmdSets/webclient/telnet, guide, calling work | Ordinary human and optional agent clients have identical world permissions. |
| Low population | Established ordinary NPC residents and authored idle outcomes | Finite waits/recoveries and baseline NPC service preserve solo play. Never conjure an offline player's work. |

**Status convention for overlap map below.** V: code-backed existing multi-role chain covered by regression, not full design-complete. S: live world substrate is shared but the *unique cooperative outcome* remains unverified. D: design proposal requiring work. C: proposal includes a canon-blocked Mystic capability; everyday observation and social interaction may still occur. Status applies to the *specific edge*, not overall Calling completeness.

## 3. The ten Callings: job descriptions and complete design direction

Each role should ultimately have at least 6 substantively authored quests and 8–12 distinct renewable professional jobs under the existing §7 contract. A daily repeat of one verb and four syntactic aliases count as **one loop**, not five. Four specialties are proposed *development organization*, not current shipped skill trees, and must not introduce a fabricated middle-rank ladder.

### 3.1 Innkeep

**Role fantasy:** Keep people fed, sheltered, and socially connected; ordinary service remains compelling even when every mystery is exhausted.

**Workplace(s):** Blood of the Vine, shared hearth and soup pot; later a small staffed lodging house separate from the OOC Inn Between.

**Four proposed specialties:** Hospitality / Cooking / Guest services / Stewardship.

**Existing code-backed foothold:** Soup preparation and simmering consume pantry stock; hearth tending depends on real delivered wood; the Cold Hunter care case has a finite Innkeep service contribution.

**Player-facing occupation loop:** Witness a customer need or shortage, choose service quality versus reserves, receive and account for real stock, prepare a meal or a safe room, deliver service, preserve customer response and tomorrow's supplies.

**Concrete inputs and guards:** Pantry ingredients, delivered wood, occupied tables, resident needs, optional guest records.

**Authoritative outputs and follow-up:** Prepared food, changed hunger/care/hearth status, guest follow-up, attributed service history; a later guest sees what changed.

**Neighbors and distinct expertise:** Merchant supplies ingredients; Healer judges patient care; Performer supplies entertainment; Chronicler records disputes; Hound/Wanderer bring stranded guests.

**Low-population/negative-state contract:** When no other player is online, basic hospitality and agreed NPC baseline stock/service permit ordinary progress; specialist bonuses and joint consequences remain better, never compulsory.

**Design-complete expansion (NOT implemented):** Expand guest requests, finite room-readiness, menus, repair orders and hospitality reputation through existing object and resident state. None is verified finished.

**Professional progression:** Apprentice learns by legitimate practice and consented mentoring, builds a witnessed service record and applies for institutional Master recognition only under later authored conditions. Master gains socially justified responsibilities or methods, never immunity from scarce supplies or hidden-truth limits. A past Calling's biography survives a later authorized respecialization.


### 3.2 Chronicler

**Role fantasy:** Maintain accountable public memory, journalism, archives and competing testimony, not a machine that converts testimony into truth.

**Workplace(s):** Chronicle, Harbinger, rumor registry, Commons; market scale attestation and health warning sources.

**Four proposed specialties:** Journalism / Archives / Research / Publishing.

**Existing code-backed foothold:** Can inspect and attest market standards after Merchant decision and Smith calibration; existing Chronicle/Harbinger and health-warning records preserve sourced disagreements.

**Player-facing occupation loop:** Select a claim, collect firsthand or signed testimony, decide to print, qualify, challenge or withhold it; track revisions, rights and public consequences without altering objective events.

**Concrete inputs and guards:** Witness records, public notices, physically observed documents, consented testimony, canonical ledger links.

**Authoritative outputs and follow-up:** Source-qualified article, correction, disputed record, institution memory, NPC beliefs only through plausible dissemination.

**Neighbors and distinct expertise:** Healer supplies sensitive care evidence; Merchant and Smith source market claims; Detective supplies contradictions; Performer spreads a public version; Mystic proposes contested interpretations.

**Low-population/negative-state contract:** When no witness responds, work on existing public records or independently inspect physical evidence; a blank source is not fabricated.

**Design-complete expansion (NOT implemented):** Extend editorial review, archive access, chain of custody, press distribution, redactions and information-sensitive institutional effects. No omniscient publication.

**Professional progression:** Apprentice learns by legitimate practice and consented mentoring, builds a witnessed service record and applies for institutional Master recognition only under later authored conditions. Master gains socially justified responsibilities or methods, never immunity from scarce supplies or hidden-truth limits. A past Calling's biography survives a later authorized respecialization.


### 3.3 Smith

**Role fantasy:** Repair and fabricate durable, verifiable changes to the material village, with craftsmanship differing from mere inventory clicking.

**Workplace(s):** Village lamp and Lamp Shop stock; real Market Workshop, physical fitting/install cycle; daily market scale calibration.

**Four proposed specialties:** Forging / Repair / Precision work / Construction.

**Existing code-backed foothold:** One-shot lamp repair and merchant procurement; market-scale calibration; Market Workshop forging and fitting installation have signed physical outputs.

**Player-facing occupation loop:** Inspect fault and measurements, select material/method, procure or receive stock, work at a legitimate bench, install or offer repair, verify wear/fit, publish a service receipt.

**Concrete inputs and guards:** Shop fittings, finite metal/wood supply, equipment tools, workbench, broken object properties, light/fire conditions.

**Authoritative outputs and follow-up:** A specific repaired object, provenance, lasting material quality, accessible infrastructure, repair history and shortage.

**Neighbors and distinct expertise:** Merchant secures materials and disputes weights; Innkeep needs equipment; Wanderer/Hound report hazards; Healer needs medical tools; Chronicler audits repairs.

**Low-population/negative-state contract:** A basic recurring service remains possible via limited NPC baseline procurement or a delayed wait, never by minting materials or reopening a repaired lamp.

**Design-complete expansion (NOT implemented):** Develop work-order families with differing risks, durable outputs, tool upkeep and built environment consequences. Reuse property tags/values and existing repair modules.

**Professional progression:** Apprentice learns by legitimate practice and consented mentoring, builds a witnessed service record and applies for institutional Master recognition only under later authored conditions. Master gains socially justified responsibilities or methods, never immunity from scarce supplies or hidden-truth limits. A past Calling's biography survives a later authorized respecialization.


### 3.4 Healer

**Role fantasy:** Offer uncertain but effective care, public-health investigation, field treatment and follow-up; expertise changes method and confidence, not objective truth.

**Workplace(s):** Hidden-toxin assessment, one-shot Cold Hunter care, recurring Church clinic daily patient and portable dressings.

**Four proposed specialties:** Clinical care / Herbalism / Field medicine / Medical research.

**Existing code-backed foothold:** Existing clinic assess/prepare/treat uses daily finite materials with signed case records; can identify hidden toxin without consuming it; public-health warning and Innkeep care collaboration exist.

**Player-facing occupation loop:** Observe actual symptoms or hazard, choose triage, examine, prepare scarce supplies, treat or refer, document uncertainty, schedule follow-up; make ethically distinct decisions about public alerts.

**Concrete inputs and guards:** Patient condition, finite dressings/food, plant properties, service capacity, witnessed exposures.

**Authoritative outputs and follow-up:** Patient progression, use of finite supplies, justified warning/referral, privacy-safe case history and next-day need.

**Neighbors and distinct expertise:** Innkeep shelters/feeds patients; Wanderer/Hound finds and carries injured travelers; Merchant supplies materials; Chronicler publishes risk with consent; Mystic/Detective distinguish fraud or apparent affliction.

**Low-population/negative-state contract:** A basic clinical round recurs through existing staffed clinic. Other practitioners improve alternatives; no player is forced to wait indefinitely.

**Design-complete expansion (NOT implemented):** Add recurring patient diversity, recovery trajectories, delayed consequences, confidentiality and herbal provenance, never automatic healing by dialogue.

**Professional progression:** Apprentice learns by legitimate practice and consented mentoring, builds a witnessed service record and applies for institutional Master recognition only under later authored conditions. Master gains socially justified responsibilities or methods, never immunity from scarce supplies or hidden-truth limits. A past Calling's biography survives a later authorized respecialization.


### 3.5 Merchant

**Role fantasy:** Manage circulation of finite goods, credible markets, delivery obligations, procurement and fair dealing, not privately own all commerce.

**Workplace(s):** Physical soup crate procurement/delivery, daily market decisions, shared market scale, Lamp Shop parts, commission participation.

**Four proposed specialties:** Retail / Procurement / Contracts / Finance.

**Existing code-backed foothold:** Can hold/honor/release market distribution; a Smith may recalibrate; a Chronicler may attest; procures real goods for Innkeep and lamp repair.

**Player-facing occupation loop:** Inspect real demand and source availability, choose bid/pricing/priority, reserve a specific quantity, arrange transport and handoff, collect or dispute receipt, expose shortages and credit relationships.

**Concrete inputs and guards:** Market crate/material stock, scales, contracts, coin, provenance, NPC service demand.

**Authoritative outputs and follow-up:** Delivered objects, legitimate stock changes, receivables and debts, signed market outcome, local price/availability response.

**Neighbors and distinct expertise:** Smith verifies quality; Wanderer moves parcels; Innkeep consumes goods; Healer requests supplies; Performer and Mystic may request specialty materials; Chronicler exposes disputes.

**Low-population/negative-state contract:** NPC baseline suppliers or deferred arrival keep the economy moving at low concurrency, never bypass finite stock or promised delivery time.

**Design-complete expansion (NOT implemented):** Build an order ledger on existing physical inventory, Commons, civic work and event records rather than a second economy.

**Professional progression:** Apprentice learns by legitimate practice and consented mentoring, builds a witnessed service record and applies for institutional Master recognition only under later authored conditions. Master gains socially justified responsibilities or methods, never immunity from scarce supplies or hidden-truth limits. A past Calling's biography survives a later authorized respecialization.


### 3.6 Wanderer

**Role fantasy:** Connect districts and make distance, timing and physical route knowledge worth paying attention to.

**Workplace(s):** Four-site repeatable daily survey; actual sealed ferry-post parcels from Market Lane to Riverside Path; physical route discoveries.

**Four proposed specialties:** Cartography / Exploration / Courier work / Survival.

**Existing code-backed foothold:** Survey reports are firsthand and day-scoped; courier parcels are real limited items with signed delivery and transferable custody.

**Player-facing occupation loop:** Choose a route after inspecting weather and checkpoints, collect actual item, navigate hazards, observe changed landmarks, deliver or return, update the map with limits on what was actually seen.

**Concrete inputs and guards:** Parcel custody, distance/time, route weather, survey marks, travel supplies, signed physical observations.

**Authoritative outputs and follow-up:** Delivered message/item, verified route condition, travel recommendation, map revision and missing-parcel follow-up.

**Neighbors and distinct expertise:** Merchant offers freight; Hound checks hazards; Detective follows routes and clues; Healer needs delivery; Innkeep receives travelers; Chronicler prints defensible maps.

**Low-population/negative-state contract:** A lone Wanderer can perform local survey/delivery and publish reports; NPC transport handles only explicitly permitted background movements.

**Design-complete expansion (NOT implemented):** Add variable condition choices, supplies and travel consequences, not pointless movement tax or an unbounded new map generator.

**Professional progression:** Apprentice learns by legitimate practice and consented mentoring, builds a witnessed service record and applies for institutional Master recognition only under later authored conditions. Master gains socially justified responsibilities or methods, never immunity from scarce supplies or hidden-truth limits. A past Calling's biography survives a later authorized respecialization.


### 3.7 Performer

**Role fantasy:** Create voluntary social events, shared memories, culture, public gatherings, play and artistic labor.

**Workplace(s):** Tavern stage rehearsal and public witnessed performances; existing fiddle, play/practice/duet and leisure verbs.

**Four proposed specialties:** Music / Theater / Storytelling / Entertainment.

**Existing code-backed foothold:** Stage rehearsals/performance and willing audience witness create public records; ordinary instruments and duets remain available.

**Player-facing occupation loop:** Learn or compose repertoire, rehearse with actual time, choose venue/context, invite voluntary audience, perform with witnesses, accept/reject commissions, deal with success/quiet rooms.

**Concrete inputs and guards:** Instrument condition, repertoire/practice, venue calendar, voluntary attendance, hospitality supplies.

**Authoritative outputs and follow-up:** Performance ledger, lasting invitations, local mood/requests only for witnesses, further festival or patron leads.

**Neighbors and distinct expertise:** Innkeep hosts and feeds crowds; Merchant supplies props/instruments; Chronicler reviews ethically; Mystic/Detective may offer controversial subjects; Healer/others respond as present people.

**Low-population/negative-state contract:** Solo rehearsal and a performance to an authentically staffed room is allowed; a duet never creates a fictional second player or compulsory audience.

**Design-complete expansion (NOT implemented):** Develop repertoire variation, booked shows, festivals, criticism, teaching and social consequences using current stage/calendar/Commons.

**Professional progression:** Apprentice learns by legitimate practice and consented mentoring, builds a witnessed service record and applies for institutional Master recognition only under later authored conditions. Master gains socially justified responsibilities or methods, never immunity from scarce supplies or hidden-truth limits. A past Calling's biography survives a later authorized respecialization.


### 3.8 Detective

**Role fantasy:** Test contradictory accounts against places, witnesses, time and provenance; never get a scripted truth-reveal button.

**Workplace(s):** Bridge plaque and river gauge; public/private mysteries, provisional theory, records and firsthand discovery.

**Four proposed specialties:** Forensics / Interviewing / Casework / Research.

**Existing code-backed foothold:** Can travel and inspect grounded clues, assemble provisional theories, and use existing shared/private mystery systems; conclusions are not world truth by assertion.

**Player-facing occupation loop:** Receive a credible complaint, secure evidence, question individuals with actual knowledge, compare timeline, decide who to inform and what to withhold, document unresolved alternatives.

**Concrete inputs and guards:** Physical scene, signed observations, witness belief, chain-of-custody, timestamps, resident position.

**Authoritative outputs and follow-up:** Case record, justified hypothesis, procedural referral, altered trust or access and evidence retained after closure.

**Neighbors and distinct expertise:** Hound secures area; Wanderer supplies routes; Healer gives cautious assessment; Chronicler publishes records; Merchant tracks contracts; Mystic adds contestable interpretations.

**Low-population/negative-state contract:** Independently inspect public clues and follow alternative leads even if witnesses leave; unsolved case remains playable.

**Design-complete expansion (NOT implemented):** Develop substantive cases and response branches with actual clue/object state rather than multiplying theory text.

**Professional progression:** Apprentice learns by legitimate practice and consented mentoring, builds a witnessed service record and applies for institutional Master recognition only under later authored conditions. Master gains socially justified responsibilities or methods, never immunity from scarce supplies or hidden-truth limits. A past Calling's biography survives a later authorized respecialization.


### 3.9 Hound

**Role fantasy:** Protect paths and people, investigate tracks and risks, prevent harm, and sometimes disagree with other investigators without needing combat.

**Workplace(s):** Daily physical route surveys and resident conversations; Hound presence and social identity; field hazard response remains largely proposed.

**Four proposed specialties:** Tracking / Patrol / Rescue / Wilderness expertise.

**Existing code-backed foothold:** Uses actual shared surveys and geographic clues; no demonstrated full separate Hound patrol/rescue production loop yet.

**Player-facing occupation loop:** Survey real conditions, distinguish mundane/extraordinary sign, choose patrol/escort/search, render aid where appropriate, leave warning/protection that changes later travel, report a source-limited conclusion.

**Concrete inputs and guards:** Tracks, time/weather, route hazards, patrol supplies, evidence, resident claims.

**Authoritative outputs and follow-up:** Road safety, resolved hazard or rescue, witness-based report, meaningful opportunity for Wanderers and Healers.

**Neighbors and distinct expertise:** Wanderer compares passability; Healer handles injuries; Detective manages case integrity; Smith restores infrastructure; Innkeep shelters survivors; Mystic studies possible anomaly.

**Low-population/negative-state contract:** Solo observation and warning work can progress; NPC patrols handle modest baseline safety, not a permanent blocker or universal monster removal.

**Design-complete expansion (NOT implemented):** Build bounded noncombat interventions, distinct from generic survey. Avoid making Hound an obligatory fighter class.

**Professional progression:** Apprentice learns by legitimate practice and consented mentoring, builds a witnessed service record and applies for institutional Master recognition only under later authored conditions. Master gains socially justified responsibilities or methods, never immunity from scarce supplies or hidden-truth limits. A past Calling's biography survives a later authorized respecialization.


### 3.10 Mystic

**Role fantasy:** Investigate and interpret folklore and rare anomalies, providing grounded ritual and research practices while leaving disputed explanations disputed.

**Workplace(s):** Existing Guild identity, two practitioner NPC circles, rare churchyard inscription change, firsthand study and signed method record.

**Four proposed specialties:** Folklore / Divination / Ritual practice / Psychical research.

**Existing code-backed foothold:** Physical grave inscription can change on a bounded rare night; study measure/vigil records method and observation; no automatic claim of a ghost or cause.

**Player-facing occupation loop:** Inspect an actual site and conditions, gather sources/participants, choose a method, distinguish measurement from testimony, record repeatable limitations and safe aftermath.

**Concrete inputs and guards:** Real anomaly state, physical objects, witness presence, weather/calendar, oral traditions, prepared materials when canon-authorized.

**Authoritative outputs and follow-up:** An accountable study report and social interpretation. Any future effective ritual must operate on canon-approved objective state rather than a prompt's assertion.

**Neighbors and distinct expertise:** Chronicler preserves uncertainty; Detective checks staged phenomena; Healer assesses wellbeing; Hound tracks physical traces; Performer carries oral tradition; Merchant/Smith may provide equipment.

**Low-population/negative-state contract:** Study and observation remain viable without a group; neither religious affiliation nor ethnic heritage is prerequisite.

**Design-complete expansion (NOT implemented):** Four unresolved canon decisions are explicitly BLOCKED: Guild authority, truth value of readings, venue/placement, and failure behavior. Do not answer them here. Unapproved magical outputs cannot be designed as implemented rules.

**Professional progression:** Apprentice learns by legitimate practice and consented mentoring, builds a witnessed service record and applies for institutional Master recognition only under later authored conditions. Master gains socially justified responsibilities or methods, never immunity from scarce supplies or hidden-truth limits. A past Calling's biography survives a later authorized respecialization.

## 4. Complete 10 × 10 overlap map

The matrix deliberately covers all **45 unique pairs**. Each cell gives the status of the corresponding numbered entry in §5; diagonal cells are self-role progression, not pair overlaps. V/S/D/C meanings are defined in §2. Every pair is further specified below; nothing is omitted because it seems less central.

| Calling | Inn | Chr | Smi | Hea | Mer | Wan | Per | Det | Hou | Mys |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| Innkeep | — | D1 | D2 | V3 | V4 | D5 | S6 | D7 | D8 | C9 |
| Chronicler | D1 | — | V10 | V11 | V12 | D13 | D14 | S15 | D16 | C17 |
| Smith | D2 | V10 | — | D18 | V19 | D20 | D21 | D22 | D23 | C24 |
| Healer | V3 | V11 | D18 | — | S25 | D26 | D27 | D28 | D29 | C30 |
| Merchant | V4 | V12 | V19 | S25 | — | S31 | D32 | D33 | D34 | C35 |
| Wanderer | D5 | D13 | D20 | D26 | S31 | — | D36 | S37 | S38 | C39 |
| Performer | S6 | D14 | D21 | D27 | D32 | D36 | — | D40 | D41 | C42 |
| Detective | D7 | S15 | D22 | D28 | D33 | S37 | D40 | — | D43 | C44 |
| Hound | D8 | D16 | D23 | D29 | D34 | S38 | D41 | D43 | — | C45 |
| Mystic | C9 | C17 | C24 | C30 | C35 | C39 | C42 | C44 | C45 | — |

Codes are symmetrical. V4 means the existing Innkeep–Healer chain; C indicates that additional truth/ritual rules must await canon decisions.

## 5. All 45 pairwise collaborations and overlaps

For each entry, the relationship is a suggested *systemic* encounter, not necessarily a dedicated quest and not a separate minigame. Ownership must stay with source world objects or the canonical ledger. For S entries, **shared commands alone do not establish true professional differentiation**.

### 01. Innkeep ↔ Chronicler — D (designed, not implemented)

Guest complaints and house accounts create source-limited public disputes; publication may improve confidence but cannot reveal private guest logs. Joint loop: Innkeep provides consented incident receipt, Chronicler verifies and prints, NPC patron reactions require actual receipt circulation.

### 02. Innkeep ↔ Smith — D (designed, not implemented)

Damaged stove, bed fittings or kitchen tool generates a physical service order. Smith inspects/repairs with materials; Innkeep decides whether to close space or spend reserve. Outcome modifies usable hospitality equipment, not an abstract progress bar.

### 03. Innkeep ↔ Healer — V (existing scripted cross-Calling chain)

Cold Hunter at Supper already separates clinical assessment from a finite Tavern meal contribution. Planned daily recurring patient/refuge service extends the same split; resident patient state remains authoritative, and care cannot be declared by mere dialogue.

### 04. Innkeep ↔ Merchant — V (existing scripted cross-Calling chain)

Soup procurement and real delivery already transfer finite roots into Tavern pantry; firewood and workshop stock also create demand. Extend to invoices, late delivery and price/quality choices using the existing item ledger.

### 05. Innkeep ↔ Wanderer — D (designed, not implemented)

Travelers bring verifiable luggage, weather and arrival times; Innkeep offers food/room, Wanderer supplies actual courier/route arrival. Missing travelers become recoverable notices rather than synthetic hotel guests.

### 06. Innkeep ↔ Performer — S (shared live system; distinct joint loop unverified)

Both share the functioning Tavern venue: stage performances are witnessed and hospitality stocks are real, but a joined audience-to-service consequence is unverified. Design events where crowded nights alter finite meal demand and return visits.

### 07. Innkeep ↔ Detective — D (designed, not implemented)

House register, lost items and guest testimony can support consent-limited investigations. Detective examines physically present evidence; Innkeep decides reasonable disclosure without exposing another mask's private room.

### 08. Innkeep ↔ Hound — D (designed, not implemented)

Stranded or protected travelers need shelter; Hound reports and escorts through actual routes. The Innkeep can allocate a finite bed or meal and record arrival, without assuming an unseen rescue succeeded.

### 09. Innkeep ↔ Mystic — C (design overlap with canon-blocked capability)

Reported disturbances at lodging can prompt independent hospitality, wellbeing and study responses. Guest privacy and anomalous outcomes cannot be canonized until Guild authority, venue and failure rules are settled.

### 10. Chronicler ↔ Smith — V (existing scripted cross-Calling chain)

Market scale attestation is source-gated by a real Smith calibration and Merchant decision. Chronicler can publish attributable evidence, not unilaterally certify a repaired object or erase disagreement.

### 11. Chronicler ↔ Healer — V (existing scripted cross-Calling chain)

Existing public-health warning links Healer first-hand assessment to Chronicler communication. Extend through privacy-preserving anonymized cases and correction history; player prose does not replace patient state.

### 12. Chronicler ↔ Merchant — V (existing scripted cross-Calling chain)

Market standards require actual Merchant hold/honor/release state before attestation. Extend to published price analysis, signed receipts and rebuttals that influence customers through proper notice channels.

### 13. Chronicler ↔ Wanderer — D (designed, not implemented)

Wanderer supplies first-hand route logs and map corrections. Chronicler edits/publicizes source-limited travel advisories; the map is a projection of reported routes, not hidden geographic truth.

### 14. Chronicler ↔ Performer — D (designed, not implemented)

Live performances yield witnessed public events; Chronicler reviews, archives and publishes attributed accounts. Performer may dispute portrayal; archive retains both, NPC opinions require plausible exposure.

### 15. Chronicler ↔ Detective — S (shared live system; distinct joint loop unverified)

Both can inspect existing public/private mystery evidence and differing claims; a differentiated custody/publication handoff is planned. Detective produces justified case analysis, Chronicler decides whether and how to publish.

### 16. Chronicler ↔ Hound — D (designed, not implemented)

Hound hazard notices or witnessed rescue records become verifiable civic reporting. False sightings can be corrected without fabricating 'monster' proof; later residents learn only through believable channels.

### 17. Chronicler ↔ Mystic — C (design overlap with canon-blocked capability)

Publish measured anomalous observations alongside alternate interpretations, with consent and provenance. Whether readings have objective predictive truth is a blocked canon issue; articles must not settle it.

### 18. Smith ↔ Healer — D (designed, not implemented)

Healer needs safe instruments, repairable clinic cot or scales. Smith supplies verified tool condition and finite fabrication, while Healer independently determines patient suitability; workmanship is not a cure.

### 19. Smith ↔ Merchant — V (existing scripted cross-Calling chain)

Lamp repair requires Merchant part procurement and Smith installation; market standards share Smith calibration/ Merchant decisions; Market Workshop already has material forge/install. Extend existing transaction/equipment substrate, do not clone it.

### 20. Smith ↔ Wanderer — D (designed, not implemented)

Route tools, ferry fittings and damaged bridges create physical work orders; Wanderer surveys/collects, Smith makes or repairs components. Destination passability changes only after in-world installation.

### 21. Smith ↔ Performer — D (designed, not implemented)

Instruments and stage fittings acquire real wear; Smith repairs/builds, Performer tests acoustics/playability. Quality affects playable methods or durability, not arbitrary 'talent' XP.

### 22. Smith ↔ Detective — D (designed, not implemented)

Forensic tool impressions, weight discrepancies and broken locks can be inspected by Smith for method/fit. Detective assembles hypotheses; an expert report may be mistaken and cannot auto-identify culprit.

### 23. Smith ↔ Hound — D (designed, not implemented)

Route hazard reports produce engineering repairs and defensive infrastructure. Hound establishes exposure and tests protective effect; Smith material work changes a specific bridge/gate/lantern state.

### 24. Smith ↔ Mystic — C (design overlap with canon-blocked capability)

Smith can make ordinary measuring instruments and containers for field studies. No magical ward item gets objectively effective effects until reading, ritual authority and failure canon are determined.

### 25. Healer ↔ Merchant — S (shared live system; distinct joint loop unverified)

Existing daily clinic dressings and traded goods are real stock systems, but a full cross-role pharmacy chain is not verified. Design supply orders with traceable origin, shortages, contraindications and no purchasable miracle cure.

### 26. Healer ↔ Wanderer — D (designed, not implemented)

Wanderer finds/escorts injured people and carries treatments along verifiable routes. Healer prioritizes scarce care and authors referrals; absence makes the situation change over time, not freeze.

### 27. Healer ↔ Performer — D (designed, not implemented)

Public events can create fatigue, accidental injuries or therapeutic company. Performer controls voluntary entertainment; Healer assesses actual need. Neither may impose emotional outcomes on unwilling or absent characters.

### 28. Healer ↔ Detective — D (designed, not implemented)

Medical findings can narrow timelines or expose poisoning without granting hidden case truth. Consent, uncertainty and lawful release are gameplay choices; Detective cannot inspect private patient records by rank.

### 29. Healer ↔ Hound — D (designed, not implemented)

Hound secures and locates hazard scenes; Healer provides field triage and follow-up. Real rescue affects health, route conditions and later reports, with NPC fallback and exhaustion outcomes.

### 30. Healer ↔ Mystic — C (design overlap with canon-blocked capability)

Examine alleged afflictions from clinical and folklore methods. Diagnosis and care operate on existing health state; any true ritual cure or occult harm requires unresolved canon decisions.

### 31. Merchant ↔ Wanderer — S (shared live system; distinct joint loop unverified)

Existing Merchant physical procurement and Wanderer ferry-post deliveries share item custody and routes, but freight contracts linking them are planned. Goods must actually be carried, delayed, delivered or returned.

### 32. Merchant ↔ Performer — D (designed, not implemented)

Market provides stage props, instruments and event sponsorship tied to goods and signed expenses. Performer supplies actual scheduled service; fees/refunds follow attendance and delivery, never imaginary crowds.

### 33. Merchant ↔ Detective — D (designed, not implemented)

Disputed weights, debt, missing cargo and counterfeit receipts generate grounded cases; Detective obtains records through permissions and verifies material evidence. Merchant retains a legitimate rebuttal and restitution path.

### 34. Merchant ↔ Hound — D (designed, not implemented)

High-risk shipments use verified route warnings and optional escort service. Hound reduces specific hazard exposure; Merchant chooses risk and coverage, without automatically creating imaginary robberies.

### 35. Merchant ↔ Mystic — C (design overlap with canon-blocked capability)

Ordinary candles, paper and apparatus may be traded for legitimate study; magical item pricing or a 'verified fortune' guarantee requires canonical outcomes not yet authorized.

### 36. Wanderer ↔ Performer — D (designed, not implemented)

Traveling shows rely on route conditions, actual booking and equipment movement. Performer chooses venue and repertoire, Wanderer delivers and guides; canceled routes create visible substitutions.

### 37. Wanderer ↔ Detective — S (shared live system; distinct joint loop unverified)

Both already use physical district and bridge clues; Wanderer survey is signed and Detective builds provisional theories. Formal route-evidence custody/referral between them is a proposed differentiation.

### 38. Wanderer ↔ Hound — S (shared live system; distinct joint loop unverified)

Shared daily district surveys already exist, but the two professions need distinct payoff: Wanderer evaluates passability/logistics while Hound assesses threat, patrol and rescue. Avoid two identical jobs wearing different labels.

### 39. Wanderer ↔ Mystic — C (design overlap with canon-blocked capability)

Guide field visits to churchyard or anomalous landmarks using real time/weather, leaving Mystic to interpret study. Future ritual location constraints or occult route sensing await canon decisions.

### 40. Performer ↔ Detective — D (designed, not implemented)

Performance timing and crowd observations can be evidence, alibi or misinformation; audience witness records have provenance. Detective may ask, not read backstage omniscient logs.

### 41. Performer ↔ Hound — D (designed, not implemented)

Events near exposed routes require crowd safety, patrol and escort decisions. Hound warns based on observed hazards; Performer reschedules, prevents or adapts without forced attendance.

### 42. Performer ↔ Mystic — C (design overlap with canon-blocked capability)

Folklore storytelling and staged séances create interpretive ambiguity. Performer knows what was staged; Mystic may witness genuine anomaly; outcome cannot imply a true reading until canon settles.

### 43. Detective ↔ Hound — D (designed, not implemented)

Hound preserves scene and tracks, Detective maintains evidence chain and explanation; either can disagree responsibly. Investigations need late-arrival traces and authority boundaries, not rival class combat.

### 44. Detective ↔ Mystic — C (design overlap with canon-blocked capability)

Test apparent hauntings with documented observation, staged-fraud checks and alternative hypotheses. A reading never proves or disproves cosmic truth by profession flag; canon for objective readings remains blocked.

### 45. Hound ↔ Mystic — C (design overlap with canon-blocked capability)

Field patrol finds physical traces of anomalies and safe observation sites. Mystic documents methods/interpretations; any supernatural protection or failure consequences are canon-locked.

## 6. Multi-Calling situations (worked design packets, not feature claims)

### A. Market supply, food, public health and press

**Existing anchors:** Merchant physically procures soup ingredients; Innkeep receives them into the kitchen and prepares meals; Healer has a real assessment method and can cooperate on a finite care case; Chronicler already participates in a source-linked public-health warning.

**Extended designed scenario:** A food-quality complaint starts from *specific* goods and patron symptoms rather than a generated job token. Merchant can trace lot/source and decide to hold or defend supply, Innkeep closes or keeps service open after examining stock, Healer observes actual effects and advises safe care, Smith may inspect damaged equipment if relevant, Chronicler can publish signed findings while preserving disputed evidence. Detective can investigate deliberate substitution; Performer may host a voluntary public meeting. A lone Innkeep must still safely serve unaffected food. The contamination, stock, illness, public notice and resident behavior all live in their existing appropriate authoritative systems.

**Outcomes:** timely containment; partial harm and contested attribution; no player response leading to bounded NPC action; falsely accused trader whose ledger cannot be retroactively rewritten. Every state offers new legitimate work and alternate leads rather than resetting a closed case.

### B. Market weights, workshop repair and reputation

**Existing anchors:** Merchant chooses honor/hold/release; Smith calibrates a real scale and makes/installs fittings; Chronicler's attest depends on signed state. Several core actions are already scripted and post-restart tested.

**Extended designed scenario:** A disputed iron shipment changes a *finite* source stock. A Hound/Wanderer observes damaged route conditions, Merchant arranges release or claim, Smith examines physical damage and chooses repair approach, Chronicler publishes uncertainty. An Innkeep commissioning new equipment can inspect the repaired installation. A hold cannot strand all production forever; a valid release or timed NPC resolution is possible with traceable history.

**Outcomes:** disputed but usable goods; high-cost precise recalibration; delayed delivery with refund/renegotiation; a legitimate correction printed after false accusation. Never allocate the same crate twice.

### C. Storm on the Old Stone Bridge

**Existing anchors:** Old Stone Bridge/Riverside physical evidence, provisional mystery, signed route survey, ferry post, finite workshop materials and the shared village clock.

**Extended designed scenario:** A storm changes route condition. Wanderer makes a firsthand passability log; Hound checks tracks and escort safety; Smith handles measured repair; Merchant procures exact material; Healer treats an actual stranded traveler; Innkeep supplies shelter; Detective compares missing freight records; Chronicler publishes competing testimonies; Performer hosts a voluntary gathering; Mystic may study a documented anomaly *without adding unapproved occult effects*. An absent role leads to limited NPC baseline or delayed results, not story paralysis.

**Canonical owners:** bridge condition object; market stock; patient record; route survey and witnessed records; ledger events. A player cannot declare the bridge safe by writing a letter.

### D. A public performance that matters tomorrow

**Existing anchors:** Performer stage, rehearsal and witnessed performance; Tavern food and hearth; calendar, Commons, journal and resident attendance.

**Extended designed scenario:** Performer chooses a song or public story, books a time, invites patrons through Commons; Innkeep allocates finite service; Merchant supplies props; Chronicler covers the performance; Hound warns of a genuinely observed route hazard; Healer can offer real first aid. Attendance must be voluntary and tracked by actual presence or valid NPC schedule. The event produces a record, a few grounded opportunities and source-aware memory, not magically universal joy.

**Failure/absence:** no audience yields a legitimate rehearsal, canceled booking and alternate local task. NPCs outside the venue are not informed without a plausible later channel.

### E. An inquiry into a reported haunting

**Existing anchors:** rare actual churchyard inscription change, bounded Mystic firsthand methods, bridge/manor public evidence, independent investigative records, distinct witnesses and NPC beliefs.

**Extended designed scenario:** Detective observes access, entry methods and testimony; Mystic records an agreed observational method and interpretations; Hound checks tracks; Healer evaluates mundane effects; Wanderer charts travel; Chronicler keeps conflicting records; Innkeep can report an actual guest complaint; Performer may know a staged trick. A false allegation, real but unexplained anomaly, and incomplete evidence must be playable states.

**BLOCKED:** no mechanic may claim predictive readings, binding rituals, guild coercive power, fixed caravan/venue authority or supernatural failure consequences without explicit World Bible/keeper answers to the four Mystic canon questions.

### F. A recurring neighborhood improvement

**Designed only; reuse existing Commons/commission mechanisms.** Any mask may post an unmet material need. Merchant supplies, Smith manufactures/repairs, Wanderer carries, Hound verifies local safety, Healer inspects health implications, Innkeep and Performer make it useful as a social place, Chronicler records debate, Detective checks suspected fraud, Mystic contributes only authorized study. Every contribution consumes an object, time or signed decision that already exists. The world object changes when actual work finishes, with partial, abandoned and maintained variants, never because a threshold of chat messages was crossed.

## 7. Overlap rules preventing role duplication

- **Shared verbs are fine; shared *solutions* are not.** Wanderer and Hound can both inspect a wet path. Wanderer knows logistics/passability; Hound identifies credible threat/protection. Detective builds a case; Mystic documents method/interpretation; Chronicler can responsibly publish. No role gets its own parallel instance of the same path's condition.
- **World physics do not belong to a profession.** Healer can safely reveal toxin; others can still encounter and suffer the actual toxic object. Smith can assess material fit; ordinary players still have the same door, item and weather state.
- **Distinct economies are forbidden.** Jobs reference the already implemented soup, hearth, market, workshop, care and object state rather than role-specific synthetic inventories.
- **No mandatory human concurrency.** Cooperative roles can improve quality, speed, evidence and social meaning. Design an explicitly bounded solo fallback or expire an order honestly. The fallback must be visible and cannot spoof another player's actions.
- **Do not confuse service with ownership.** NPC institutions already exist. Players can work in the Tavern, clinic or market without buying the building.
- **Do not impose reward-only grind.** Character history and real competence lead to social privileges, apprenticeships, patron relationships and authored responsibility, not arbitrary multiplication of unseen XP.
- **Keep narrative ambiguity.** Physical effects, public record, resident opinion and private theory are separately owned and may disagree.
- **No player identity leak.** Optional AI-controlled and ordinary human accounts use equal verbs, disclosure and permissions; no IC substrate detection.

## 8. Full-game content architecture and authoring responsibilities

Original full-game section 7 minimums stay authoritative: 12 newcomer scenarios; 30 small and 10–12 major mysteries; 30 civic quests; 6 authored quests and 8–12 repeatable jobs **per Calling**; 8–10 faction quests **per faction**; 20 cross-faction conflicts; 10–12 expedition locations; 12 social expeditions; 12 group investigations; 30 timed incidents; 75+ random incidents; 10 village-wide event frameworks; 6+ community projects; 50+ hidden discoveries; 3–5 arcs per major NPC; 250+ rumor seeds; 300+ ambient room events; 50+ Harbinger templates; 30+ player-request templates.

**Production method:** Author content against reusable *verified gameplay predicates* instead of opening one new command or service for every story. One workshop repair mechanism can support many materially distinct work orders; each must have specific real input, player judgment, durable output, discoverability and aftermath. Counting recipe aliases, story blurbs, already-cured patients, or inaccessible scene text is not acceptable coverage.

Each Calling receives:
1. A daily routine with a source-state-dependent start, work and return.
2. Several unrelated decisions (not minor variations on one verb) yielding choices.
3. Work that may be undertaken alone; work with named optional collaborators.
4. At least one workplace with an NPC supervisor or source of finite requests.
5. Apprenticeship/social progression using existing recorded history and consent.
6. Specialized methods that benefit its neighbors, not just its own stats.
7. Competing immediate versus durable goals.
8. Failures, delays, scarcity, completed-case aftermath and returning-player variants.

No arbitrary 'percentage complete' until the content audit has the evidence of player-reachable actions. Each item must be annotated **manuscript / static declaration / initialized / discovered in live session / changed world / persisted after restart / uncoached player-found**.

## 9. Test matrix and acceptance for all overlaps

For **each one of the 45 edges** in §5:
- Source: specific world location, item, need, resident or observed event; at least one player can discover it normally.
- Two roles: distinct concrete methods; separately authorized and unattributable to one another. If one is absent, note actual timeout/NPC/solo fallback.
- Consequence: change owned by *one existing* appropriate world authority, not a second truth store.
- Contracts: physical presence, material spending, finite retries, ID ownership, authority, expiry, competing participants, client parity and no duplicate output.
- Follow-up: visible changed object or record, witness-local social knowledge, late arrival and real server restart; false report remains only a claim.
- Tests: source-state units, exact two-account telnet, negative/depleted/closed variants, client discovery and post-restart witness. S/D/C edges remain **unverified**, not automatically backlog-complete.

For **each Calling**, demonstrate: first work opportunity, at least two genuinely different short loops, a deeper lasting ambition, professional specialization/mentoring, market/community contribution, social interaction without obligation, a case that was completed by someone else, scarcity, an uncoached session and a return with unfinished commitments. After these are sound, scale to §7 quotas and rebalance.

**Prioritization is graph-based, not arbitrary role batches.** Identify the most reusable live source state and connect neighboring Callings where the shared world benefits. The current strongest *demonstrated* cross-role examples are Market standards (Merchant/Smith/Chronicler), care (Healer/Innkeep), public-health warnings (Healer/Chronicler), and soup supply (Merchant/Innkeep). These are *starting evidence*, not a proposal to finish three Callings while neglecting the rest. Plan the next vertical scenario by how many meaningful professions it connects while retaining one consistent world authority.

## 10. Settled decisions and reserved decisions

**Settled:** fun game first; no invented second quest framework; one active Calling and preserved professional biography; Apprentice/Master only; bilateral accepted apprenticeship; finite sourced materials; objective event record independent of claims; limited witnesses; optional NPC fallback; same physics for humans and AI; no Pretorius/Lab as a load-bearing prerequisite; Gothic supernatural uncommon but real.

**Reserved to the keeper, do NOT interpret as resolved:**
- The Guild of Mystics' authority and its limits.
- Whether divinatory readings have any objective truth-value/prediction.
- The authoritative venue/location of the Guild and how any earlier caravan description interacts with later shared workplaces.
- How failed ritual/study interventions work in world state.

Nothing above grants occult authority or requires a specific answer to these four questions.

## 11. Reuse references and external game comparisons

**Internal, binding or precedential:**
- docs/TEN_CALLINGS_LIVING_VILLAGE_V1.md
- ops/CALLINGS_SIMULATION_DEPTH_PLAN.md
- files/frankenstein-village-world-bible-v0.2.md
- hidden_files/design-doctrine.md
- design-decisions.md
- world/callings.py and world/calling_opportunities.py; command/world handlers for hearth, soup, commission, market, workshop, clinic, courier, survey, stage, bridge, Mystic; existing authoritative ledgers and object state.

**External patterns, inspiration ONLY:**
- Eco official professions and asynchronous market/contracts (https://www.play.eco/ , https://wiki.play.eco/en/Skills). Borrow specialization -> real reciprocal demand, not its exact skill-point rules.
- Dwarf Fortress guildhalls (https://dwarffortresswiki.org/index.php/Guildhall). Borrow shared mentorship and institutions, not its population thresholds or simulation code.
- Shadows of Doubt (existing design review reference) for physical clues/uncertain information; never copy its interfaces or suggest that a player automatically knows a culprit.
- Classic SWG profession design as discussed in prior internal design reviews: prefer genuine player service and interdependence, avoid opaque grinding or compelled shop ownership.
- Evennia official documentation (https://www.evennia.com/docs/latest/): reuse CmdSets, typeclasses, persistent object attributes, Scripts/clock and existing webclient. Do not fork an architecture that Evennia already supplies.

**Integration boundary:** This design is a **review draft** off current main. It modifies no game behavior, no canon, no open PRs and no deployment. Approval should precede major new profession features. Treat newly enumerated pair flows as proposals and run normal code + gameplay review before marking them implemented.
