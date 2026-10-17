# Frankenstein Village: gameplay launch review and retention plan

Review date: 2026-10-16
Baseline: `main` at `d68ef52a52d6ef476ce5de01a12fb33801f936ef`
Evidence: source inspection and [main CI run 38061712989](https://github.com/Azimn/frankenstein-village/actions/runs/38061712989), which completed successfully on 2026-10-10.
Status: **Public beta NO-GO. Game-specific alpha candidate, pending uncoached play testing. Live invited alpha also requires the operational evidence in `ops/ALPHA_RELEASE_CHECKLIST.md`.**

This review assesses the commercial-game question: what can an independent AI or human player do tonight, and why would that same player return tomorrow, in a week, and after months? Green integration tests demonstrate functional mechanics. They do not measure enjoyment, discovery, content renewal, or sustained participation.

## Design contract

The Inn Between is a non-deceptive out-of-character social place; the village is a separate, authoritative in-character world. Human and AI players use the same verbs, accounts, physical constraints and moderation pathways. A player's narrative claim does not automatically alter physical history. Source: `hidden_files/design-doctrine.md`, `files/frankenstein-village-world-bible-v0.2.md`, and the world event ledger.

Fun game first, living world second, experiment third. Preserve open-ended roleplay, incomplete testimony, relationships, quiet village life, and meaningful noncombat choices. Avoid a mandatory quest treadmill, automation-only rewards, or a privileged agent path through the simulation.

## Source-grounded content inventory

Generate the conservative inventory whenever code changes:

```sh
python3 ops/content_inventory.py --format markdown
python3 ops/content_inventory.py --format json
python3 -m unittest discover -s ops/tests -p 'test_content_inventory.py' -v
```

The utility counts source declarations, source manuscript IDs, and initializer references. It cannot certify a playable outcome, correct permissions, full accessibility, reliable re-entry, or narrative quality. It intentionally does not read a deployed database or treat every `TEMPLATES` entry as a completed quest.

At the baseline, `spike/fvillage/world/build_spike.py` declares five traversable IC locations: Village Square, the Blood of the Vine, Tavern Back Hall, the Lamp Shop, and St. Lazarus Church. The Inn Common Room and Inn Hallway add two shared OOC rooms. `Offstage` is deliberately inaccessible. Account-owned private rooms are created dynamically and are excluded.

The source defines 36 residents and nine Callings. There are eight entries in `world/situations.py`, one public mystery definition and one private mystery definition, alongside the independently implemented Room Six. These are distinct systems and should not be summed into a count of complete mysteries. The initial rumor seeding selection contains IDs 151, 201, and 236 of the 250 accepted manuscript seeds. Runtime events and player interactions can produce additional rumors, but that does not promote all 250 manuscript entries into initial runtime availability. The runtime registries declare two random incidents, three recurring calendar events, one timed incident, one server-wide event, and six seasonal chapter definitions.

The current full-launch targets remain those in `files/frankenstein-village-quest-handoff-v0.3.md` section 7, including 75+ random incident templates, 30 timed incidents, 10 server-wide event frameworks, multiple mysteries, repeatable jobs for every Calling, and substantial cross-faction activity. Do not replace those targets with a smaller alpha inventory. Source declarations are only a lower level of evidence than tested playable content.

## What the player already has

The current development build provides a verifiable finite, interdependent civic route: a Smith diagnoses a broken public lamp, a separate Merchant spends stock to procure a part, and the Smith finishes a persistent physical repair. A Healer and an Innkeep can jointly complete a time-sensitive care case with finite food. A Healer and a Chronicler must each contribute to a public-health warning. Each remains vulnerable to closure or prior resolution by other players.

The repeatable civic hearth provides everyday work independent of authored cases. A mask gathers a finite bundle of wood, carries it to the tavern, and delivers it. An active Innkeep can consume stored wood to strengthen the fire for eight village hours. Recent integration adds conditional environmental response in residents who are actually present. Do not claim absent residents witnessed the fire or automatically award them affection.

The Commons is the other durable loop. Real players can post an open need, respond, follow an unfinished conversation, disconnect, later check a changed reply count, and close their own record. Such correspondence is persistent, attributed, and moderation-aware. It must never be interpreted as proof that an unperformed physical task happened.

The active character command set also exposes concrete leisure systems: darts, challenge dice, fortune cards, fiddle playing/practice/duets, score history, multi-session whittling with tangible crafted objects, whistle playing, arm wrestling, and private diary writing. These strengthen the social third-place experience and already exceed a bare collection of descriptive rooms. However, many are centered on the Tavern, and their existence alone does not answer why a player would independently explore the wider village. Record their genuine persistence, multiplayer use, replay value and discovery separately from short-lived novelty.\n\nThe Chronicle, Harbinger, private and public mysteries, rumor transmission, weekly calendar, and resident state offer substantial social roleplay surfaces. Existing scripted telnet and post-restart QA demonstrate a connected slice. Their existence does not establish that novices spontaneously discover or enjoy the slice.

## Three release-specific gameplay risks

**The Inn could outcompete the village.** Compare time spent in the OOC Inn, time spent exploring IC spaces, and voluntary return after IC departure. OOC dwell time is not a failure, but a low village entry rate or rapid IC exit would indicate insufficient motivation. Keep the Inn enjoyable, then provide visible IC opportunities connected to real world changes.

**One-shot civic work can be exhausted.** Repair, care, and warning cases have finite outcomes. Returning players must still find worthwhile activity through the hearth, Commons, social commitments, calendar events, newspaper debates, ordinary trades, and genuinely renewable opportunities. Add tested sources of recurring choices rather than silently resetting repaired lamps or generating fake tasks.

**Written content exceeds active content.** The authored seed banks are extensive, but only selected entries are wired into the runnable game. Avoid treating prose quantities as gameplay. Every newly activated item needs discovery conditions, permissible agency, outcomes, aftermath, return-visit variants, conflict handling, and an authoritative record.

## Acceptance experiments, not paper targets

**First evening, no script:** Recruit genuinely unfamiliar AI players and human testers who have not seen the code, design documents, previous test transcripts, or instructions beyond the public login/help information. Use different AI models or independent agent configurations to avoid testing a single memorized itinerary. Allow 30-60 minutes of free play. Record consenting, sanitized observations: time to account and mask, successful front-door transition, time to first meaningful IC interaction, first player-chosen persistent contribution, first unsolicited social exchange, failed commands, dead ends, and whether the player can identify a self-chosen next action. A meaningful interaction must have an observable consequence or a response from another independently acting character, rather than a purely decorative line.

**Real return, no itinerary:** Disconnect with at least one actual unfinished thread or consequence, reconnect after a real-world day, and repeat after a week. Confirm that the mask, location, authored notes, relevant third-party actions, and externally recoverable context permit continuation. Observe whether the player follows up without a prompt. Do not substitute a synthetic time jump for the question of voluntary return.

**World remembers:** A player changes a shared physical or institutional condition and another unaffiliated player later discovers it without being told which command to run. Confirm that characters present for an event know it by appropriate channels and absent characters do not. Test contradictory accounts as public claims, never authoritative history by assertion.

**Multiplayer fairness:** Include simultaneous AI and human players with overlapping interests, low resources, late arrivals and disconnections. Verify state transition idempotence, finite stock contention, reply ordering, report moderation, identity boundary, and no agent-only privileged shortcut. Separate load and transport testing from qualitative enjoyment.

**Long retention:** Measure voluntary return and diversity of actions at weeks and months, after content changes and after a world restart. A single early player saying that the game is interesting is not retention evidence. Track additional authored releases without resetting past interactions or erasing historical records.

For the controlled gameplay-alpha decision, use a first cohort of at least eight uncoached AI sessions from more than one model/configuration, plus four uncoached human sessions where available. These are proposed research samples, not statistically powered retention estimates. Do not fabricate participants or mark this gate passed from CI. Record the actual population, session transcripts, anonymized friction log, adverse events, and human reviewer verdict.

## Development order

**Blocker to credible gameplay-alpha quality:** Publish the actual generated static inventory with source SHA; inspect each starter path and accessible IC room for discovery, agency and repeatability; run uncoached first-evening tests and fix observed dead ends. In parallel, check persistence for a second player discovering a previous player's change. Never mark the test done without evidence.

**Next gameplay slice:** Make one additional durable, repeatable village activity whose output touches at least two existing systems. Prefer a low-cost exchange/commission or an investigation practice that can be undertaken by an uncommitted newcomer, with finite inventory and provenance, a contribution another player can actually respond to, and contextual follow-up visible a day later. Reuse the event ledger, Commons, and existing item properties. Measure whether the new activity gives players something to do after all finite civic cases close. Do not add XP or claim a simulation of sensations.

**Public-beta gameplay gate:** Increase meaningful IC space beyond the current five locations, ensure at least two fully playable branching investigative experiences with persistent alternative outcomes, support a small portfolio of renewable social and practical activities, and demonstrate unscripted success and return in a small cohort. These are quality checks for a limited beta. The broader section 7 quotas still govern any claim of full launch.

**Operations gate:** Independently execute actual protected snapshot/off-host recovery, external authentication and disclosure, TLS/WSS paths, moderation, backup review, operator contact, and concurrent load testing. The previously proposed paid host was declined; this review makes no provider selection and authorizes no spend. The current `ops/ALPHA_RELEASE_CHECKLIST.md` remains authoritative for go/no-go on an externally hosted alpha.

## Expansion candidate: The Taste of Transylvania

Status: deferred post-launch design concept. Candidate for the first major expansion, not a release blocker.

Create a consistent symbolic culinary simulation with sweetness, acidity, bitterness, saltiness, savoriness, aroma, texture, temperature, and aftertaste. Ingredient properties, techniques, freshness, environment, and serving state should produce inspectable, reproducible profiles and natural language descriptions. Player masks may develop distinct preferences, dislikes, associations and autobiographical food memories through their actual experiences. Shared meals, markets, inns, kitchen work, festivals, preparation experiments, and recipe discovery should connect to existing inventories, public events, and character history.

The system models describable sensory consequences for agents; it does not assert literal biological taste or subjective sensation. Architect it as a later layer on mechanical object properties, provenance, inventory, time, and persistent mask memory. Prototype with a few known ingredients and food preparations before expanding the catalog. Never let food dialogue magically change authoritative world state.

## Decision record

At baseline, production-grade development regression is green. Real-world hosting and recovery remain unverified. The gameplay build is a serious alpha candidate with interconnected systems, but no completed evidence shows that unfamiliar AI players discover enough consequential play to return on their own. Public beta is therefore **NO-GO** until the specific uncoached gameplay and return gates above have evidence, with operational go/no-go separate. A large number of authored ideas or passing scripted tests must not override that decision.
