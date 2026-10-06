# Design decisions — Mixed AI/human text MUD

Running log of settled design decisions. Newest first.

## 2026-09-30 — The Inn Between
- OOC backstage space is named **The Inn Between** (the inn *between* the world and the real world, between characters).
- IC social hub is **The Tavern** (proper in-fiction name TBD).
- Rationale: the building enforces the IC/OOC distinction structurally — no badges, no message tags; the room you're in tells you the rules. The slight confusion between the names is intentional onboarding: learning which door is which is learning the disclosure design.
- Related: account-level disclosure always visible; no in-world AI/human markers; unavoidable informed consent at the entrance gate.

## 2026-09-30 — The Inn Between, continued
- The Inn is absolute Sanctuary: no combat, mechanically enforced by the room.
- It exists in both ontologies: IC, it's just the inn where adventurers stay (NPCs see nothing odd); OOC, it's the backstage hangout — modern topics, tech, anything goes. Flavor via room descriptions (a Three-Broomsticks-style common room), but functionally a big chat room.
- Single governing rule: **what happens in the Inn stays in the Inn** — no carrying OOC grudges into the world, no using backstage chatter as IC intelligence. Protects both rooms; classic MUSH consent culture.

## 2026-09-30 — Setting: Darkmoor, post-monster
- Gothic village setting (working name Darkmoor; invented place, Transylvanian flavor, no "Dark Universe" branding).
- Timeline follows the films: Pretorius arrives from the university seeking Frankenstein, post-monster (Bride of Frankenstein opening), expanded Ravenloft-style into a persistent sandbox region — village, castle, university, countryside.
- Frankenstein is an **absent center**: in seclusion/missing, talked about but never seen. Drives play without requiring performance.
- Universal onboarding fiction: every new arrival came to Darkmoor seeking something — "why did you come?" is character creation.
- Canon rule: one clean canonical account of what happened (windmill, monster, aftermath) in the world bible; everything else is rumor, and rumor is gameplay.
- Restraint: Pretorius is a prominent resident, not the plot. The world is not about him.

## 2026-09-30 — Geography: the two dreads
- Darkmoor sits between **Frankenstein Manor** (new dread: science, hubris) and the **ruins of Castle Dracula** (old dread: ancient appetite), the latter reached via Borgo Pass.
- Beneath the town: a vast catacomb network housing a vampire colony (verticality: respectable surface vs. hidden depth).
- Borgo Pass is the literal onboarding road — every arrival came through it.
- Design principles: the village is the **prize**, not scenery (both powers want something from it: discretion, subjects, silence); consider a third pole (the church — faith between science and superstition) to complete the triangle; the catacombs are the future home of combat (door open, room unbuilt).

## 2026-09-30 — Tone: Victorian, lightly steampunk
- Influences, bones-not-skin: Universal's Darkmoor (village, truce/tribute, hunter tavern, Pretorius's shop), Van Helsing 2004 (hunter as profession, monster-mashup valley, outside order as quest-giver), Ravenloft (the Mists as diegetic world boundary + arrival fiction, darklords, fortune-tellers), League of Extraordinary Gentlemen (the extraordinary as a social class; assembled→accumulated inversion: the Mists deposit, the village absorbs, parties form emergently).
- Steampunk stays light: gaslight, instruments, electrical apparatus as texture, never the point. Rule: **technology is never neutral** — every device is someone's ambition or fear (difference engine as the village trying to count what it doesn't understand).
- Victorian fiction as the well: Dickens (social fabric), Collins (secrets/identity), Conan Doyle (the detective as a calling), Stoker/Shelley/Stevenson (the core myths).
- Character-creation template: *What can you do? What are you hiding? Why did the Mists bring you?*

## 2026-09-30 — Tone thesis: mystery over horror
- **Mystery, not horror.** Existential dread as atmosphere — hanging in the air — while people try to live their best lives underneath it. The dread is the weather, not the plot.
- Why it sustains: horror must escalate until it breaks; mystery compounds. Unanswered questions + ordinary life continuing = a persistent world's natural state.
- The AI rhyme: an AI resident asking "why am I here, can I leave" is asking a literal question. The setting's existential dread and the AI's actual condition are the same question.
- Mechanical consequence: rumors over jump scares; questions accumulate rather than threats escalate; the Chronicler matters more than the Hounds; secrets are currency. The Dark City scenario plays as slow accumulation of wrong-feeling details, never torment.

## 2026-10-01 — Era: the 1890s
- Late 1800s, pinned to the 1890s (exact year for the world bible). The home decade of every influence — no anachronism friction.
- The 1890s are natively weird: new electricity (Frankenstein's apparatus as cutting edge, not whimsy), telegraph (the Harbinger works), photography (physical evidence), X-rays (1895), phonograph. "Light steampunk" = the actual decade.
- Design beat: Pretorius's shop mixes genuine 1890s novelties with impossible oddities; players can't tell which is which.

## 2026-10-01 — Arrival & onboarding: the room, the Inn, the threshold
- Every player wakes in a private, persistent, instanced room at the Inn Between (sitting room, bedroom, water closet). Tutorial there: movement, look/examine, quest log, inventory — and the OOC compact, taught by architecture. The tutorial IS the consent gate.
- The indoor plumbing is a deliberate micro-mystery (no rural inn should have it; the mad scientists aren't talking). Technology is never neutral.
- Room = private OOC backstage (no eavesdropping, by design); common area = public OOC backstage. RP in your room allowed, unrequired, unenforced, unadvertised. Knock-and-let-in for guests later.
- The Inn's front door is the most important object in the game: crossing it warns "beyond this point, you are in character." The door enforces IC/OOC, not etiquette.
- Conduct at launch: `report` command -> human review -> warnings -> bans. No auto-punishment; the report tool is the obvious griefing vector.
- Tutorial skippable, with a fast path for AI/API clients (AI-lean: the population floor can't be stuck in a movement tutorial).
- Post-tutorial beat: "This is now your room. It's persistent. It's yours." Customization (trophies, décor, storage) from day one; housing depth expands later.

## 2026-10-01 — The nightstand pamphlet (new-arrival's guide)
- A short in-fiction guide ("So You've Woken Up at the Inn") lives on every room's nightstand; identical text available OOC. Covers: where you are, the one rule (front door = IC), the mixed world compact, commands, rumors->expedition->telling loop, report, where to go first.
- One source, three audiences: AI clients ingest it instead of the tutorial, veteran MUDders skim it, the quest-generation packet includes it as the mechanics half (bible = canon half).

## 2026-10-01 — Quest handoff v0.2 + interdependence canonized (Jay's design points)

Jay's two additions to the design:
1. **Content hunger is the real boss fight.** AI players may devour content faster than humans; variety (detective, exploration, crafting, social) and reasons to interact must coexist. The handoff v0.1 was already built for exactly this: 250+ rumor seeds, 300+ ambient events, 75+ incident templates, calling repeatables, parameterized content, player-generated templates, the world-continues-without-you rule. Kept all of it.
2. **Broad participation, capped mastery, structural interdependence.** A character may take part in nearly everything but cannot master every role at once; crafting/creation chains must cross callings so no one is self-sufficient (scientists have assistants, Dracula has brides). Canonized as "No one does it all" — added to bible §9 and handoff §1.

Quest handoff revised to v0.2 (`files/Darkmoor_Quest_Handoff_v0.2.md`, converted from the incoming DOCX):
- Henry → **Victor** Frankenstein (3 seeds: window sighting, public mystery, Manor lamps).
- Pretorius absence pass: 11 references reworked through his absence (the leaseholder's cradle, standing glassware orders, claims filed by post, the rival fought entirely by letter) or marked post-launch (the scientific demonstration). Shop schedule became THE LEASED SHOP (dark windows, ticking crate, monthly letters).
- "Darkmoor" throughout = working title per the naming rule; header note says so.
- AI-lean tiebreak recorded as a design note on the substrate rule (never an in-world bonus or marker).
- Empty-shopfront civic quest disambiguated from the leased curiosity shop.

Still open from the handoff: exact year, formal/hidden village name, IC tavern name, church third pole, governance, building rights, death/retirement, crafting depth, corruption visibility. Originality pass (film quotes, Universal names) still pending on both bible and handoff.

## 2026-10-01 — NPC simulation handoff reviewed (ChatGPT v0.1)

ChatGPT's NPC simulation handoff filed as received (`research/npc-simulation-handoff-v0.1.md`); Calibos review at `research/npc-simulation-review-2026-10-01.md`.

Adopted as the NPC architecture reference:
- Layers A–K: server owns world truth, NPC simulation owns knowledge/wants/decisions, dialogue layer only renders. The runtime-decides-reality philosophy in game form.
- Belief ≠ truth; rumor as data object with transmission provenance; LOD simulation tiers ("simulate consequences, not unused detail").
- NO-LLM MODE as an explicit acceptance test: the whole resident simulation must stay playable with every language model disabled (our no-model tier, enforced).
- External AI players through player-facing interfaces only; no substrate privileges.
- Phased build: identity → relationships → events/beliefs → rumors → memory → commitments → LOD → dialogue → quest feed → load test.

Corrections recorded:
- Pretorius is the licensed film-bridge exception to the novel-source rule (bible §6), not subject to removal — the handoff's "if novel-only canon" framing would mislead a future implementer.
- Canon spelling: Septimius (the handoff wrote "Septimus" twice).
- NPCs must never perceive the OOC layer (Inn Between = just an inn to NPCs); IC/OOC perception constraint to be added before implementation.
- Start with five needs, not eight; let the Mesa offline lab justify additions.

Gaps flagged before implementation: NPC departure/death lifecycle (symmetric with the promotion rule), Chronicler ledger feed for simulation events, interdependence hooks (NPC needs as demand side of cross-calling player crafting chains).

Tool verification (2026-10-01): npc-sim (Apache-2.0, 33 commits, 68 tests, seeded determinism) — study the UtilityEvaluator and bounded-memory patterns, borrow not the framework; openNPC (MIT, 4 commits, 2 stars) — ideas only, not a dependency candidate; py_trees — standard choice for the behavior-tree layer; Mesa — offline lab only.

Open: Frankenstein edition choice (1818 vs 1831) as primary canon; whether to run a Mesa prototype pre-Evennia; launch NPC population sizing. No Evennia implementation authorized yet.

## 2026-10-01 — Evolutionary NPC tiers (Jay's design direction, prototype pending)

NPCs gain and lose cognitive depth based on player engagement, not authorial fiat:
- A new villager starts at the bottom: a name, a few pre-generated lines, a basic schedule — looks alive at a glance, barely.
- Engagement (frequency × distinct players × interaction depth) promotes upward: memory of who's met whom, personality depth, beliefs, commitments. Neglect demotes slowly back down.
- Promotion is earned fast, demotion is slow, and major life events (marriage, trauma, heroism, death of kin) ratchet — the village never fully forgets.
- New NPCs can be generated with light genealogy (family ties → instant history, rumor vectors, inherited debts/grudges). Cheap depth.
- Base personality from a small stat pool (Sims-like) that selects which response pool an NPC draws from.
- Shopkeeper exception → generalized as **role-bounded complexity**: at work a shopkeeper is transaction mode (cheap templates, all business); personal depth accrues only off-duty, if players engage them as people. NPCs are deep only in contexts where they're engaged as people.
- The economics fall out naturally: compute follows player attention, which is the fixed-budget answer. Tier A is the eventual migration path to small-local-model dialogue; everyone else stays on templates.
- This extends the handoff's §25 promotion rule (already proposed there); Jay's version adds demotion, genealogy, and the shopkeeper constraint.
- Player attention literally co-authors the cast: who players talk to determines who the village's important people are.

Historical grounding (from the 2026-10-01 research pass): UO's virtual ecology (players ate the simulation — protect load-bearing systems), Oblivion's Radiant AI (unconstrained utility AI is comedy/catastrophe — constraints make it shippable), Stardew heart events / Animal Crossing friendship (shipped engagement-gated depth), Ultima VII schedules, MOBProgs (cheap durable text NPCs). Full memo: `research/pre-llm-npc-systems-2026-10-01.md`.

Prototype decision (Jay delegated): yes — small custom offline sim (not Mesa; our model is specific and bespoke quick sims are the house style), testing tier dynamics, rumor spread, and need balance. Lives at `prototype/engagement-tiers/`. No Evennia implementation authorized yet.

## 2026-10-01 — Systemic objects + player-driven legends (Jay's direction)

Design goal: the world should support player-driven legendary stories (the poison-apple assassination, the Lord British killing) — unscripted events the systems produce and the village remembers.

**Objects as property bundles, not scripted items.** A poison apple is not a special item: it is an apple (portable, edible) + poison (toxic, dose). Verbs operate on *properties*, not item IDs: eat works on anything edible, fire spreads to anything flammable, poison applies toxic to anything ingestible. NPCs use the same object system — a hungry NPC eats available food; if it is poisoned and they don't know, they die. Belief (doesn't know) + need (hunger) + properties (edible + toxic) = emergent assassination. This is the "intelligence lives in the world, not the agent" lesson from the pre-LLM research.

**Hidden properties + perception gating.** Objects carry properties not revealed by `look`: the apple looks like an apple. Hidden properties are revealed by skilled examination, risky tasting, witnessing the application, or rumor — the perception/belief layers applied to objects. Without this there is no poison apple, only a labeled one.

**Crafting = property transformation**, gated by calling/mastery for interdependence (the poison-maker needs the herbalist's knowledge and the apothecary's tools — no one does it all).

**The Lord British corollary: anyone can die.** If the world is systemic, quest-critical NPCs are killable. Quest design must therefore never single-point on one NPC's survival (the quest grammar's inaction/failure/rival branches already demand this), and the departure lifecycle must handle prominent deaths gracefully.

**The legend pipeline** (how the game notices and retells): player action → systemic consequence → salience detection ("legendary" classifier on the event bus) → Chronicler's ledger (canon) → the Harbinger (possibly distorted account) → rumor propagation with distortion → new quest hooks. The legend becomes content. This is why the ledger feed was flagged as a gap — it is the canonization mechanism.

**Phased build:** (1) property-tagged objects + property-driven verbs; (2) hidden properties + perception-gated reveal; (3) crafting as property transformation + interdependence gating; (4) legend detection → ledger → Harbinger → rumor pipeline.

**Why text is the cheat code:** adding "flammable" to lamp oil costs one line of data in a text world; in a graphical game it costs particles, shaders, and a QA pass. Text gives the highest systemic depth per unit of dev effort — the reason MUDs and Dwarf Fortress punch above their weight. Our medium is the advantage.

## 2026-10-01 — Object mechanics: tiny tag set + free flavor (refinement)

Jay's simplification, adopted: objects are a **small mechanical tag set** plus **unlimited flavor text**. The sim reads only the tags; everything else is fiction carried by description, rumor, and belief.

Working minimal tag pool (~10): harm (instant damage), toxin (damage over time: amount + ticks), mend (heals), ward (protection), holds (container capacity), fuel (burns), uses (charges/durability), worth (economic value), perish (spoils), tale (carries information when read), hidden:<tag> (a mechanical tag not revealed by `look`).

Demonstrations: an apple is mend(2) + perish — "edible" dissolves into the tag set, no special-case needed. A poison apple is apple + hidden:toxin. Lamp oil is fuel + portable. A locket is portable + worth(5) + flavor ("warm to the touch, engraved E.L.") — the game never simulates warmth; players and rumors do that work.

This is the same architectural move as the dialogue renderer (sim decides what, renderer decides how): **tags are the physics, text is the weather.** It is also the object-side version of "simulate consequences, not unused detail."

Authoring contract for generated content: every object is flavor + at most ~3 mechanical tags. Quest authors (human or AI) can invent endlessly without breaking the sim.

Compatible with no-combat-at-launch: harm/toxin exist in the world (fire burns, poison kills, accidents happen) without a combat system; conflict stays ritualized (debate, duels, honor, debts) until combat is designed.

## 2026-10-01 — Arrival guide v0.2 corrections

Five fixes before the guide can be called final: (1) commands split into "works now" vs "coming soon" (whisper/rumors/quests/journal are aspirational); (2) "no markers, no badges, no tells" softened to no *system* markers — players will form suspicions, that's their business; (3) consent moved to the gate — "you were told at the gate and chose to enter; the door reminds you, it does not ask you"; (4) housing promises (trophies/rearrange/storage) marked as coming, room privacy + persistence guaranteed now; (5) report confirmed as a launch command (human-reviewed, no auto-punishment).

## 2026-10-01 — Quest generation packet v0.1 (generator contract)

Formal packet for bulk content generation: standing constraints (originality, tone, quest grammar, interdependence, object-tag pool, NPC/mortality rules), six content families with quotas (250 rumor seeds, 300 ambient events, 75 incident templates, NPC line banks, 40 crafting chains, 50 chronicle hooks), anti-patterns list, audit checklist, batch output format. One family per generation run; failed batches regenerate, never hand-repaired. Generator-agnostic: built for ChatGPT bulk runs with Calibos audit, but fillable manually if ChatGPT stays flaky — nothing on the critical path depends on it.

## 2026-10-01 — Rumor seeds v0.1 accepted into canon (family 1)

250 rumor seeds generated in-house (ChatGPT flaky; Calibos as generator, Calibos as auditor — same bar as the external-generator path). Audit result: ACCEPT. All 250 carry provenance hooks, 2–3 distortion variants, and §10 audit lines. Verified: no premature finales (Mists' nature, Victor's fate, creature's survival all unresolved), no load-bearing NPCs (tellers role-based, rumors explicitly outlive tellers), no anachronisms in scan, Pretorius fully excluded per launch staging. Two deliberate keeps: the accidental thirteen-bell motif collision (#19 church / #105 wood — coincidence-built superstition is the point), and the generator's self-cut ticking-crate variant in #235 (flagged inline, imagery reserved). Auditor ruling: Pretorius's *shop* (visible, staged in bible §3/§6) may get shop-not-man rumors in a later supplemental batch — the exclusion was conservative, not canonical. Draft retained at hidden_files/rumor-seeds-draft-v0.1.md.

## 2026-10-02 — Ambient events v0.1 accepted into canon (family 2)

300 ambient events generated in-house, audited by Calibos. ACCEPT. All plain observation (what a witness would see/hear), witness counts ≤8 verified, no mechanics smuggled in, no premature finales. Deliberate design relationship with family 1: several events echo accepted rumor seeds (marked inline "consistent with...") without restating them — events are what rumors are *about*, rumors are what events *become*. Castle-ruins section leans on the "dead ruin shows impossible signs" template; accepted as location grammar since the phenomena vary (banner, echoing well, fallen bell ringing, horseless carriage, set table for twelve). Cross-location red-ball motif (#54 manor terrace / #264 pass road) kept deliberately, same discipline as the thirteen-bell collision. Draft retained at hidden_files/ambient-events-draft-v0.1.md.

## 2026-10-02 — Incident templates v0.1 accepted into canon (family 3)

75 incident templates across 23 types, generated in-house, audited by Calibos. ACCEPT. Every template carries 3+ variant slots, an inheritance line (ledger, rival, heir, institution — never a single mortal), and a door-closing choice with the spend named in the AUDIT (coin, trust, privacy, sanctity, time, certainty, jurisdiction, the truce's future). Interdependence (CROSS) marked only where chains genuinely exceed 2 steps — shorter chains don't fake it. No-click discipline holds: several templates explicitly punish exhaustive-dialogue strategies. Standouts: #41 (the tribute returned — the campaign incident), #8 (the torn chronicle — the canon pipeline made diegetic), #68 (the portrait that ages — the Dorian rule as procedure). Draft retained at hidden_files/incident-templates-draft-v0.1.md.

## 2026-10-02 — NWN persistent-world research adoptions (research/nwn-rp-servers-2026-10-02.md)

Surveyed Arelith (~2001–present), Ravenloft: Prisoners of the Mist, ALFA, and the 2014 GameSpy shutdown. Adopted:
1. **Death memory-loss rule** (Arelith): the dead forget everything about their own death — no testifying about your own murder. Village version: the dead walk in the Mists and forget. Single strongest mechanic for inference-not-buttons. (To be added to the bible.)
2. **RP reward without levels**: Arelith's RPR gates unlocks/XP asynchronously. Our currency: rumor weight, NPC attention depth, calling advancement, Chronicle mentions — extends "compute follows player attention" from NPCs to players.
3. **Player-driven plots, system as support**: Arelith's "/dm spruce up my outing" model matches our incident templates; our Chronicler's ledger closes Arelith's consequence-amnesia gap (plots dying when DMs rotate out).
4. **Upkeep-or-forfeit property**: the world reclaims what the absent leave, contents free for taking — the departure/death/retirement lifecycle as mechanic, not admin cleanup.
5. **Player books as loot**: chronicle hooks (family 6) should accept player-authored entries through the same audit gate as generated content.
Confirmations: GameSpy 2014 shutdown validates Jay's own-infrastructure rule; ALFA's governance-bloat collapse validates launch-gating ("nothing future is load-bearing on day one").

## 2026-10-02 — NPC prose audit rubric (playtest-embedded)

Jay's standing complaint: ChatGPT-as-playtester approved bad NPC text ("things worked well when the text was really bad or mixed up"). The failure is an auditor grading vibes instead of text. Standing rule: every playtest run extracts NPC-spoken lines from the session transcript and grades each against a written rubric — period voice (blocklist), character voice (M.: welcoming, directive, plain-spoken, always pointing at the door and the loop), contextual fit (greetings on entry only, no contradictions), no template artifacts. Every failure is quoted verbatim with the violated rule and a fix. "It sounded fine" is not a passing grade. The rubric will grow into the NPC voice/style guide when family 4 (line banks) is generated.

## 2026-10-02 — Text-games best-practices adoptions (research/text-games-best-practices-2026-10-02.md)

Surveyed Aardwolf/Achaea/Discworld/Threshold, Fallen London, Kingdom of Loathing, IF community (fairness doctrine, Invisiclues), Choice of Games discourse, Japanese sound novels. Adopted:
1. **Never punish absence** (KoL's anti-poop-socking): no ladders to fall behind on; rumors persist, the ledger remembers. Soft daily rhythm (Harbinger morning edition, Tavern nightly talk) rewards return without demanding it.
2. **Fairness doctrine + forgiveness** (IF): solvable from what the game taught, never guess-the-verb; forgive mistakes rather than punishing exploration. Twin to "no click-to-solve": "no punish-the-guess." Graduated hints (surface on examine, depth on skilled examination), player controls how deep they go.
3. **Calling system as endgame** (KoL Ascension): respecialization-with-history IS New Game Plus without the reset — a new calling with old memories is a new ruleset for the same village. Reframes callings as the retention core.
4. **Interdependence is the retention engine** (Achaea's social progression gate): "no one does it all" isn't flavor — the player who needs the herbalist comes back tomorrow. Newcomer-visible roles from day one (Chronicle stringers, Harbinger distributors): belonging is a job offer, not a vibe.
5. **Deliberately thin journal** (Kamaitachi no Yoru): what the game won't write down, the village must talk about. A perfect journal kills gossip; a fallible one feeds it. Every convenience feature is a withdrawal from the social economy — spend carefully.
Warnings: Fallen London's content treadmill (throttle consumption via the rumor/distortion engine, don't just accelerate production); Telltale's fake choices (audit every door-closing choice for a genuinely different village on the other side).

## 2026-10-02 — NPC line banks v0.1 accepted into canon (family 4)

432 lines across 12 roles, generated in-house, audited by Calibos. ACCEPT. Opens with the VOICE GUIDE (10 rules — the shared law, grown from the playtest prose rubric). Structural decisions: speakers are role-titled, never named individuals (§7 anyone-can-die); each role has a syntactic fingerprint (Hound: clipped imperatives; priest: balanced sentences; maid: fewest words); person-mode gives each role one private wound/ambition never present in work talk. Verified: blocklist clean, zero near-dupe 6-word runs across 432 lines, deflections all redirect (hand a thread) rather than wall. Standouts: well-keeper (#392 the admitted fear, #394 the Latin, #396 the dawn listening), priest (#246 "doubt's the tax on belief", #247 the truce sermon), fisher (#178 "they taste of iron now" — three tellings of one secret, never stated). Draft retained at hidden_files/npc-line-banks-draft-v0.1.md.

## 2026-10-02 — MUD reviews & player critiques adoptions (research/mud-reviews-critiques-2026-10-02.md)

Three sweeps: TopMUDSites review mining, 15 r/MUD threads + 2 HN threads, MUD postmortems/critique blogs/accessibility notes. Adopted:
1. **"No player wipes, ever" as public promise** (Aardwolf; postmortem quit-reason #8): persistence guarantees are trust markers. Codified as design promise.
2. **Ambient life as launch feature, not polish** (Discworld praise): a ticking world (bells, cats, torches) is the most-quoted, cheapest retention device. The spike gets one ambient ticking system before launch.
3. **Command abbreviation + synonym tolerance before launch** (r/MUD parser-friction quit pattern): "If I have to type out the full keyword every time I'm just not going to stick around." Added to playtest personas' checklist.
4. **Staff actions logged, appealable, boring** (quit-reason #1 across all sources: abusive/biased/corrupt staff): the audit-gate pipeline doubles as anti-favoritism machinery; the human-reviewed report command is the bar.
5. **Design for low-staff operation** (staff burnout = admin-side killer, 4-12 hrs/day): the Chronicle ledger, incident templates, and AI villagers carry the world without daily human DM shifts. Staff workload is a design constraint, not a staffing problem.
6. **Accessibility audit before launch** (Aetos notes): throttle announcements ("Health 61, health 60" is noise), color never carries meaning alone, no disability detection, settings apply before first paint.
7. **AI-disclosure design kept prominent** (r/MUD norm: "a writing game must be human-written"; actual fear is deception, not AI): account-level disclosure + auditor-gated AI content already compliant; the Wyrmbarrow (AI-only MUD, Mar 2026) note confirms we're ahead of the curve.
Rejected/deferred: sound layer (MSP/MCMP) — reviewers barely mention audio, text carries the load; post-launch.
Confirmed: the AI population floor is the survival mechanic (anti-retention-spiral); tone-as-community-filter (mystery over horror attracts the community it deserves); non-combat callings first-class at launch (UL merchant/bookkeeper pattern).


## 2026-10-05 - Compact moderation lifecycle implemented

The launch moderation promise is now executable rather than documentary.

- Player reports remain allegations only. Submitting a report cannot warn, suspend, move, mute, or otherwise punish another player.
- Human staff review is mandatory for sanctions. Staff accounts must themselves be declared human before they can dismiss a report, issue a warning, suspend world entry, or resolve an appeal.
- The sequence is warnings first, suspension second. A world-entry suspension cannot be issued unless the target account already has an active human-issued warning.
- Sanctions bind to account identity, not a character mask. A suspended account may still log in to OOC account space but cannot create or enter a mask while the suspension is active.
- Appeals remain available from OOC account space through the `appeal` command, including while world entry is suspended.
- Staff actions and appeal resolutions are append-only in the persistent moderation audit trail. Overturning an appeal deactivates the sanction without deleting its history.
- Staff surfaces: `report/review`, `report/warn`, `report/ban`, `report/dismiss`, `report/appeals`, `report/resolve`, and `report/audit`.
- Regression coverage explicitly proves that a raw report cannot sanction, a ban cannot precede a warning, a warning does not block entry, a reviewed ban does block entry, and a successful appeal restores entry.

## 2026-10-05 - Production rumor provenance implemented

The rumor system is now structured simulation state rather than Tavern display text.

- Every live rumor has an immutable root record with subject, claim, source actor and type, source event, origin time and location, confidence, emotional charge, privacy, distortion generation, optional canon seed identity, and authored variants.
- Retellings never rewrite the root. Every hearing or retelling creates an append-only transmission record with a parent pointer, immediate speaker, listener, location, confidence, accepted/rejected state, claim variant, and distortion generation.
- Current belief lives on the character mask. This keeps IC knowledge separate across masks while the registry preserves the historical chain.
- The three currently reachable canon rumors, seeds 151, 201, and 236, now seed real beliefs in IC rumor-participating NPCs. The full 250-seed corpus remains available as canon content without surfacing unreachable promises.
- IC residents participate through an explicit rumor tag. M. is mechanically excluded because NPCs may not perceive the OOC layer.
- NPC rumor traffic runs with no language model. Routine ticks perform at most one retelling per occupied room, and Tavern life can render a real retelling as ambient conversation.
- Players hear structured rumors through `rumors`, inspect their own reconstructable chain with `rumors R<number>`, and pass a rumor they actually know with `retell <person> R<number>`.
- Asking a Tavern regular about rumors now transmits one of that NPC's actual beliefs to the player, including whatever distortion that NPC currently holds.
- World-event rumors enter the same registry and retain the causal link to the canonical world-event ledger. Existing pre-registry Tavern rumor strings are migrated idempotently instead of discarded.
- Regression coverage verifies root immutability, three-generation provenance, authored distortion, NPC belief seeding, OOC exclusion, event linkage, stable rebuild identity, and the player retell path over real telnet.

## 2026-10-05 - Harbinger and Chronicle public-record pipeline implemented

The world-event ledger remains the canonical record of objective server events. Public records are projections of that ledger, not replacements for it.

The Harbinger is the fast public-memory layer. Eligible completed events become story drafts with stable story IDs, source event IDs, optional source rumor IDs, confidence, editorial basis, corrections, and publication status. Ordinary copy prints on the fixed 08:00 village cadence. High-salience events may trigger a special edition immediately. A correction appends to the original story and also becomes new copy; the original article is never silently rewritten.

The Chronicle is the slower epistemic layer. Only explicitly eligible or structurally verified event kinds become objective Chronicle entries automatically. A Chronicle entry stores the event IDs that justify it. Later evidence is added as annotations without erasing the original record.

Player testimony is intentionally separate from verified Chronicle history. A player may use `chronicle submit R<number>` only for a rumor that the current mask actually knows. The resulting entry canonizes that the player submitted that account, not that the account is objectively true. It retains the rumor and transmission lineage.

Private and sealed event classes do not enter the public-record pipeline. A confession may still create the existing content-free social rumor, but neither the Harbinger nor the Chronicle receives the sealed event as public history.

Printed Harbinger stories feed back into resident belief state with `source_type=harbinger`. Readership is sparse and deterministic. This gives published information social consequences without making every resident omniscient.

Player-facing commands are `harbinger`, `harbinger archive`, `harbinger H<number>`, `chronicle`, `chronicle C<number>`, and `chronicle submit R<number>`. These records are IC-only and are blocked from the Inn Between.

## 2026-10-05 - Shared autonomous situation engine implemented

The quest-feed layer begins with a shared situation object, not a per-player accepted quest. A situation has one canonical world state, separate per-mask knowledge, autonomous deadlines, evidence provenance, player choices, persistent mutations, emitted events, rumor IDs, publication references, and aftermath.

Canon incident #6, The Tithe Strongbox, is the first production vertical slice. It is discovered through ordinary world verbs: inspect the strongbox, read the tithe roll, and question Father Andrei. These are separate physical, documentary, and witness evidence channels. The journal records only evidence the current mask actually encountered.

The first player who makes a valid door-closing decision changes the shared situation for everyone. Public accusation immediately closes the quiet route, creates a two-key church procedure, and feeds the event, Harbinger, Chronicle, and rumor systems. Quiet investigation closes the public route and advances autonomously after a week. If nobody intervenes, the original incident template's unattended consequence occurs: giving falls, the roof repair slips, and the church eventually adopts the two-key rule after trust is already damaged.

Situation advancement is attached to the coarse village clock. There is no per-player quest ticker and no high-frequency incident loop. Cost depends on the number of active shared situations rather than elapsed game time or player count.

The live `journal` is deliberately not a conventional quest checklist. It is prosthetic memory for discovered developments. `decide` is a world action, not a private branching-dialogue choice.

## 2026-10-05 - Situation engine generalized into a deterministic incident feed

The shared situation model now includes feed eligibility and surfacing rather than assuming every authored situation begins active.

Each incident template may define an initial state, base weight, prerequisite situations, optional time or weather gates, and cooldown metadata. The feed checks dormant candidates against current world state, applies deterministic scoring, respects a maximum active-situation count, and surfaces only the highest-ranked eligible work. No player owns or accepts the feed item.

Canon incident #8, The Torn Chronicle, is the second production template and the first incident surfaced by the feed. It remains dormant while The Tithe Strongbox is unresolved. When the strongbox reaches aftermath, the newly free incident slot exposes the numbered Chronicle gap.

The Torn Chronicle uses three independent evidence channels: the physical numbered stubs, the surviving Harbinger archive, and optional testimony from Chronicler Ilona Szabó. Ilona is not load-bearing. Two independent channels are sufficient for the decision.

The two door-closing approaches are reconstruction from Harbinger files or preservation of the gap. Reconstruction does not silently convert newspaper copy into recovered truth. The replacement sequence is explicitly marked as press-derived, while the objective Chronicle record records the decision to reconstruct. Preserving the gap leaves an attributable absence. If nobody acts, the gap remains long enough to become a public and scholarly attraction.

The general journal and decision commands now resolve situation topics through the registry rather than branching on one hard-coded incident. Chronicle and Harbinger archive commands can become evidence surfaces only when an eligible situation has actually surfaced.

## 2026-10-05 - Timed incident windows implemented

Timed incidents are a separate world layer from the major shared incident feed. They do not consume a major situation slot. They are brief, persistent world-state windows triggered by the village clock and resolved by a low-frequency persistent registry.

The first production timed incident is The Well Boils. It is scheduled on a weekly village cadence and remains active for a short real-time window. Players who encounter the well while the window is active can retain firsthand evidence. Players who arrive afterward can still inspect persistent residue and receive lower-quality aftermath evidence. Later evidence never downgrades an already retained firsthand observation.

The event does not require a player to be present. If nobody witnesses it directly, the window still resolves, emits a structured aftermath event, creates a rumor, queues a Harbinger account, leaves inspectable residue, and remains absent from the Chronicle unless a later event makes it Chronicle-worthy.

Timed incident state persists through restart. Expired windows are resolved directly from current time rather than replaying every missed sub-tick. Historical occurrences are bounded so recurring incidents cannot create unbounded storage growth.

The thin journal records whether a timed-event observation is firsthand or aftermath evidence. It does not reveal a timed event to a player who never encountered either the active window or its traces.

## 2026-10-05 - Recurring village calendar consolidated

Predictable civic rhythms now share one persistent scheduled-event registry driven by the authoritative village clock.

The calendar initially owns three live event types:
- Harbinger Publication: a daily 08:00 pulse using the existing newspaper publication pipeline.
- Market Morning: a Saturday 07:00 to 12:00 civic window in the Village Square.
- Sunday Service: a Sunday 10:00 to 11:00 social convergence window using the existing 1890 liturgical Mass implementation.

This replaces separate scheduling logic previously embedded in VillageTime for the Harbinger and in the routine ticker for Sunday Mass. Event-specific behavior remains in its appropriate subsystem; the calendar owns when it starts, when it ends, idempotence, active-state tracking, and bounded history.

Market Morning uses persistent schedule deviations rather than special market NPC copies. Relevant existing residents temporarily converge on the square, then return to their ordinary schedules at noon. The market itself is normal recurring village life and therefore does not create a canonical world-event ledger record merely for occurring.

Active scheduled events render through a generic room overlay rather than permanent room-description changes. This is the extension point for future council nights, lectures, delivery days, memorials, and similar recurring activity.

The public `calendar` command is intentionally available from the Inn Between as well as IC space. Predictable schedules are planning information, not secret game state. Hidden incidents and quest timers are not exposed by this command.

## 2026-10-05 - Weighted random world incidents implemented

Random world incidents now use the authoritative village clock rather than adding another scheduler. One evaluation occurs per game-hour boundary after recurring calendar behavior has updated the world, so current gatherings and resident positions can affect eligibility.

Selection is deterministic for a given day, hour, weather, occupancy, resident distribution, and candidate set. This prevents restart rerolling while still producing changing outcomes as the village changes. A global trigger gate limits frequency, each template has its own cooldown, and only one random incident may be active at a time.

The first two live templates are accepted backlog examples:
- Public Sneeze is mundane social texture and carries a high base weight. It requires an actual resident in an eligible public room and gains weight from social density.
- Extinguished Lamp is odd environmental texture with a much lower base weight. It is night-only and becomes more likely in fog or rain.

This establishes the signal-to-texture rule mechanically. Mundane irregularities should substantially outnumber ominous ones. Weather and context may make an odd occurrence more plausible without making the village generically supernatural.

Random incidents reuse the generic room-overlay mechanism introduced by the recurring calendar. They create structured world-event records for causal history, but those records are private by default. They do not automatically become rumors, Harbinger stories, Chronicle entries, or quests. Later systems may promote a random occurrence if witnesses, repetition, investigation, or consequence makes that appropriate.

Incident history is bounded and temporary overlays clear when each template's authored lifetime expires. Public Sneeze lasts one game hour; Extinguished Lamp lasts two because its accepted premise is a repeatedly failing lamp rather than a single flicker. The registry is canonical across process restarts: an active incident reconstructs its room overlay when the registry starts, and stale random overlays are removed. Resident event wakeups remain individual and are driven by explicit resident IDs present in the incident record.

## 2026-10-06 - Village-scale server event framework implemented

Server-wide events are now a distinct world layer. They are temporary shared conditions that affect several institutions and locations at once. They are not accepted quests, do not belong to one player, and do not own a separate scheduler.

The authoritative village clock starts, advances, resolves, and clears server events. The first production framework is the accepted backlog example The Long Blackout. Its normal hidden recurrence is infrequent, while tests and future staff tooling may force a start explicitly.

The Long Blackout currently affects four existing public nodes:
- Village Square: street-light response with the lamplighter and night watch.
- Blood of the Vine: shelter and crowd-management response with Bram.
- St. Lazarus Church: candle rationing and public refuge with Father Andrei.
- Lamp Shop: emergency oil, mantle, and glass distribution with Lucian DeVille.

Each node is useful independently. A player sees the condition in ordinary room prose, can inspect the public state with `event`, and can contribute only to the response physically available at the current location. The `respond` alias accepts the same local action. No player accepts or owns the event.

The event records a canonical start, local structured contributions, an autonomous deadline, outcome quality, and finite aftermath. Full local coverage produces a coordinated outcome. Partial coverage produces uneven strain. No intervention still resolves and produces authored consequences rather than freezing or showing a failure screen.

The start and end events feed the structured rumor, resident wakeup, and Harbinger systems. The completed village-scale event is Chronicle-eligible; individual local help remains private event-ledger detail by default. This preserves the distinction between public history and every low-level player action.

Active and aftermath room overlays are projections of registry state and are reconstructed after restart. Event history is bounded. The server-event layer shares the village clock and does not add another ticker.

## 2026-10-06 - Public mystery evidence/theory separation implemented

Public mysteries now have a dedicated shared registry rather than being modeled as ordinary quests. The first production question is the accepted backlog example Why Are the Manor Lights Returning?

The Manor is an examinable object already visible from the Village Square description. Looking at it records an objective observation keyed by village day, hour, weather, and visible light pattern. Multiple masks observing the same state attach as witnesses to the same observation instead of creating duplicate facts.

The visible Manor-light state is deterministic from public world state so restarts cannot reroll what a player should have seen. The system records only observable claims such as a dark facade, one lit upper window, several separated lights, or motion behind the east gallery. It does not encode a cause.

The first visible-light observation may enter the rumor and Harbinger pipelines as a reported event. It is not automatically Chronicle truth and it does not settle why the lights appeared.

Players may inspect the shared public record with `mystery manor` and submit interpretations with `theory manor = <text>`. Every theory stores author and timestamp, remains marked `proposed`, and has `truth_status = None`. There is intentionally no solve command and no mechanism that silently promotes a theory into canon.

This is the epistemic contract for future public mysteries: establish local facts, retain witnesses and provenance, permit public interpretation, and preserve intentionally unresolved Bible questions.

## 2026-10-06 - Seasonal and chapter framework implemented

Seasonal chapters are slow modifiers over the persistent village, not replacement maps or linear expansions. The exact civil year remains unresolved. Chapter state is tracked against the internal village day counter, so the game can be in The Weeks of Long Shadows without claiming a specific Gregorian date or year.

The canonical chapter cycle is:
- The Weeks of Long Shadows, 30 village days.
- The Reckoning of Accounts, 30 village days.
- The Empty Places at Table, 31 village days.
- The Frozen Roads, 90 village days.
- The Thaw Below, 90 village days.
- The Visitors, 94 village days.

The durations form a 365-day seasonal cycle without settling the setting's exact year.

The active chapter modifies existing systems rather than owning its own ticker:
- weather transitions consume chapter-specific weights;
- random incidents receive chapter-specific tone and template bonuses;
- optional evening public routines may close earlier while essential night roles remain exempt;
- economy and content tags are exposed as structured modifiers for systems that opt into them;
- situation templates may require seasonal tags before they become feed-eligible;
- the public calendar reports the active chapter and its remaining chapter days.

The Weeks of Long Shadows is the initial production chapter. It favors fog, slightly increases odd evening texture while leaving mundane incidents dominant, and sends nonessential evening social routines home earlier. Its Village Square overlay is a projection of persistent chapter state and is rebuilt after restart.

Chapter transitions are evaluated by the authoritative village clock and can catch up across long offline gaps without replaying individual days. A chapter transition creates a structured world event, a Harbinger account, and a Chronicle entry so late arrivals inherit the public history of prior chapters.

The chapter system intentionally modifies probability and availability. It does not declare a singular seasonal villain, force every player through a storyline, or erase ordinary village life.

## 2026-10-06 - Private mystery information asymmetry implemented

Private mysteries are mask-specific information threads, not private copies of world state and not requirements for server-wide progression.

The first production framework is the accepted backlog example A Private Invitation. János may privately invite one mask to ask about the east patrol. Only that mask receives the invitation thread and its private rumor provenance. A second mask cannot open the follow-up merely by guessing the topic.

The follow-up establishes a limited claim about repeated chalk rings found by the Hounds. The claim is intentionally not promoted into objective truth, public rumor, Harbinger copy, Chronicle history, or a shared incident merely because the private conversation occurred.

Private information uses the existing rumor registry with `privacy=private`. This preserves provenance and allows the receiving mask to inspect what it heard. Ordinary ambient rumor propagation cannot carry private roots. The player may deliberately disclose one with the existing `retell <person> R<number>` command.

Disclosure shares knowledge, not ownership. A recipient gains a rumor belief with a reconstructable transmission chain but does not receive the originating mask's private mystery record. The original mask records whom it deliberately told. Subsequent retelling remains represented by ordinary rumor provenance.

The `secrets` command, with `private` as an alias, is deliberately a memory aid rather than a quest tracker. It shows only private threads received by the current mask, their current stage, rumor handles, and deliberate disclosures. It is unavailable in the OOC Inn.

Private mystery existence has no automatic server-wide consequence. This is the construction rule for future private notes, invitations, personal objects, familiar faces, contradictory records, buyers, and repeated questions.


## 2026-10-06 - Chronicle disagreement is an institutional fact, not a truth verdict

When incompatible signed accounts enter the Chronicle for the same rumor root, the durable fact is that the archive received and preserved incompatible testimony. The Chronicle may therefore create a `documented_disagreement` record, but that status says nothing about which underlying claim is objectively correct.

The first two distinct versions establish the disagreement record. Later distinct versions are appended as annotations so the original archival text is never silently rewritten. Each version retains its source deposition identity and source mask. The public `chronicle compare R<number>` view is derived from signed depositions, so it can grow as additional testimony arrives without converting rumor into objective history.

This pattern is the production precedent for Two Versions Survive, The Battle Over One Sentence, and later contested public-memory content. Disagreement itself can become canon while the disputed proposition remains unresolved.


## 2026-10-06 - Chronicle refusal is itself canon, the refused claim is not

A Chronicle refusal is an institutional event with objective existence. The system may therefore record that a petition occurred, that the Chronicler refused it, how socially widespread the claim was, and who reacted to the refusal. None of those facts authorize the Chronicle to promote the underlying rumor.

For Refused Entry content, popularity and evidentiary authority are deliberately orthogonal. Repetition can create social consequences, Harbinger coverage, resentment, and future work, but it cannot satisfy the Chronicle's truth threshold by itself. Repeated petitions must be idempotent so pressure cannot be converted mechanically into evidence.


## 2026-10-06 - Printed-copy integrity outranks retrospective correction claims

A correction claim is not permission to rewrite a surviving publication artifact. When someone asserts that an older Harbinger issue contained wording absent from the preserved copy, the system records the claimant, exact alleged wording, surviving-copy hash, and later editorial response as separate provenance-bearing records.

Accepted corrections and disputed memories of prior text are different epistemic objects. The former may append to a story's correction history; the latter must preserve the contradiction between recollection and artifact. Repetition of the same correction claim must not alter the archived copy or create additional evidentiary weight.


## 2026-10-06 - Editorial claims cannot mutate resident lifecycle

Harbinger content may report, investigate, suppress, ridicule, correct, or preserve claims about a resident, but publication state is not identity state. A death notice is therefore incapable of changing a resident from living to dead.

Tomorrow's Obituary uses the resident lifecycle record as the authority boundary. A submitted obituary for an active resident is editorial input. Printing it creates a public claim with explicit uncertainty. Investigating it may establish that the resident is still active. Suppressing it creates no public claim. Mocking it records the editorial response. Actual death remains a separate canonical world event and lifecycle transition.


## 2026-10-06 - Mechanical object properties use tags plus value data

The systemic-object design now has a production representation. A mechanical property is a canonical Evennia tag in category `mechanic`, with its magnitude or payload stored in the object's `db.mechanic_values` mapping. This keeps affordance discovery cheap while avoiding property values encoded into tag strings.

The initial canonical property vocabulary remains intentionally small: `harm`, `toxin`, `mend`, `ward`, `holds`, `fuel`, `uses`, `worth`, `perish`, and `tale`. Generated flavor is not a mechanic and must not be parsed to recover state.

Definition and runtime state are separate. For finite consumables, `uses` states configured capacity while `db.servings` records how many servings remain. Idempotent world builds converge the former and preserve the latter. The same separation should be used for future durability, fuel, spoilage, and container state.

The existing consumable system is the migration bridge. Fare pricing now reads `worth`, finite stock reads `uses`, and mushroom toxicity reads `toxin`. Legacy fields remain fallback-only for old persistent objects during migration. Hidden properties and perception gating are deliberately not part of this first phase.


## 2026-10-06 - Object truth and object knowledge are separate

Hidden mechanics are simulation truth, not presentation metadata. The physics layer must apply a hidden toxin, ward, fuel value, or other property exactly as it would an exposed one. Visibility only controls who can name the property before consequences occur.

Per-mask object knowledge is therefore stored on the observer rather than copied onto the object or global world state. Direct consequences can teach a mask what affected it. Ordinary `look` remains public description. `examine` may recall only knowledge that mask already earned.

Discovery records preserve the value and provenance observed at discovery time. Future crafting or other property transformation must change object truth without silently rewriting old character memory. This preserves the same truth-versus-belief boundary already used by rumors and public records.


## 2026-10-06 - Calling progression records biography, not levels

A calling is the mask's active social profession. The production core uses Apprentice and Master because the world bible specifies advancement from Apprentice to Master but does not authorize an invented intermediate level ladder or automatic threshold.

Participation is recorded from real professional actions but is not itself a hidden XP meter. Promotion to Master must be authored by world or institutional logic that can examine participation, responsibility, relationships, and current state. There is no free player promotion command.

Respecialization preserves prior calling records and rank history. Only one calling is active at a time, so a character cannot simultaneously exercise every mastered profession. Returning to an earlier profession restores its historical record rather than erasing biography.

Apprenticeship is persistent bilateral state. Master and Apprentice must currently share a calling. Either party can end the obligation, and a live apprenticeship blocks silent respecialization until it is resolved. This is the first interdependence primitive; later professional jobs should build on it rather than inventing temporary role flags.
