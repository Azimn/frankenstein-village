# Pre-LLM NPC Depth and Simulation: What Shipped Games Teach Us

Date: 2026-10-01. For the Frankenstein Village text-MUD NPC design.

**Why this memo exists.** Our NPC plan is engagement-tiered: a villager starts as a name, a schedule, and a few lines, and gains depth (memory, personality, beliefs) as players engage — and quietly sheds it when ignored. Compute follows player attention. Every system below did some version of this *without* a language model. The question for each: what actually worked, what broke, and what do we steal.

Related: `research/npc-simulation-handoff-v0.1.md` §§18–23 already covers Cataclysm:DDA, Dwarf Fortress (general), RimWorld, Caves of Qud, Ultima Ratio Regum, and Stanford Generative Agents. This memo does not repeat those — it covers what the handoff didn't, and goes deeper where the handoff was thin.

---

## 1. Ultima Online's virtual ecology — the cautionary tale

**Not to be confused with:** Ultima Ratio Regum (§22 of the handoff), a modern procedural-culture roguelike by Mark Johnson. Different game, different decade, different lesson. This section is about 1997's Ultima Online.

**What it did.** Lead designer Raph Koster and his wife Kristen built a genuine ecosystem simulation: fields grew grass, herbivores ate the grass, carnivores hunted the herbivores, populations moved toward steady state. Dragons had something like Maslow's hierarchy — first food, then shelter, then a lust for shiny treasure. In alpha testing it worked beautifully.

**What worked.** In a closed test with few players, the simulation produced exactly the intended living-world feel. Players could even exploit it cleverly — herding tasty deer into a dragon's path instead of fighting it. (One shipped remnant: rabbits that escaped wolves *leveled up*, a Monty Python joke; Koster says they left one killer rabbit in the final game.)

**What failed.** Two separate failures, and Koster himself insists the popular story conflates them:
1. **Players are a force of nature.** The public beta brought 50,000 players who killed everything faster than spawners could replace it. No population survived long enough unmolested for any equilibrium to establish. The simulation never got to *play out*.
2. **The compute cost was the actual killer.** Koster's own correction: "the ecology failed because of the cost of pathfinding and radial searches." The AI was doing expensive spatial queries for animals nobody was watching. The team tore the whole AI out — though the *resource values* (how much meat/hide each creature represented) stayed in the game and are still there; they're used by crafting and harvesting to this day.

**The failure mode, named:** *Unbounded simulation cost + unprotected equilibrium.* The sim burned server CPU on creatures no player could see, and its core loop assumed players would politely leave the rabbits alone.

**Steal this:** Never simulate what no player can perceive, and never let an equilibrium assume player restraint. Our LOD tiers are the direct answer to failure #2; the "simulation creates hooks, players create consequences" split is the answer to #1 — NPCs react to the world, but the *point* of the sim is producing player-visible situations, not ecological purity.

Sources: [Technology Review on UO](https://www.technologyreview.com/2023/02/17/1068027/ultima-online-oldest-metaverse/), [Koster's HN correction](https://news.ycombinator.com/item?id=18749793), [MassivelyOP Game Archaeologist](https://massivelyop.com/2022/09/03/the-game-archaeologist-how-ultima-online-got-made/), [GDC Online postmortem](https://www.raphkoster.com/2012/10/11/gdconline-uo-classic-game-postmortem/)

---

## 2. Oblivion's Radiant AI — constraints are what ship

**What it did.** The original Radiant AI gave NPCs needs (eat, sleep, work) and let them satisfy those needs *by any means their stats allowed*. Each NPC had stats like Aggression, Responsibility, Confidence, and Disposition that gated which means were acceptable.

**What worked.** When it worked, it was magic. A Bethesda playtester (later art lead Dan Lee) snuck onto a ship, stole all the food from a captain's room, and left a poisoned apple. The hungry captain ate it and died — quest completed. He ran to designer Emil Pagliarulo amazed they'd accounted for it. Pagliarulo: "I didn't — that was just the game systems working." Systemic NPCs let players invent solutions the designers never authored. That is exactly our target feeling.

**What failed.** Unconstrained goal-pursuit is indistinguishable from chaos:
- NPCs addicted to the drug skooma ran out, marched to the dealer, and **murdered him** — he was a Dark Brotherhood quest NPC, so the quest became uncompletable.
- A gardener NPC whose job needed a rake, finding none, **murdered another NPC and took theirs**.
- Hungry guards abandoned their posts to find food; the other guards followed; the town's low-Responsibility residents went on a thieving spree.
- NPCs with Responsibility ≤ 30 stole food when hungry; NPCs could *acquire* bounties but had no way to *pay* them, so guards executed bread thieves. Players walked into towns and found corpses from crimes they'd never witnessed.

Bethesda nerfed it for ship: schedules, role-bounded goal packages, and hard limits on what an NPC may do to satisfy a need. The stats stayed — a low-Responsibility NPC will still steal your lunch in the remaster — but the *means* got fenced in.

**The failure mode, named:** *Means-ends explosion.* Give an NPC a goal and unconstrained means, and "get food" becomes "commit murder." The more unsavory the cast (bandits, addicts, conmen), the faster it detonates.

**Steal this:** This is the single strongest argument for our shopkeeper exception and role bounds generally. "At work, all business; off-duty, a person" is Radiant AI's shipped solution restated. Utility AI picks the *goal*; the role constrains the *means*. And note the positive lesson too: the poison-apple story is our design target — systems colliding to produce player-inventable solutions, with no quest author involved.

Sources: [Escapist](https://www.escapistmagazine.com/oblivion-npcs-brought-their-world-to-life-then-they-nearly-killed-it/), [PC Gamer on the stats](https://www.pcgamer.com/games/the-elder-scrolls/after-hearing-the-king-of-funny-elder-scrolls-clips-explain-how-oblivion-npcs-work-i-have-a-newfound-respect-for-elves-who-steal-food-when-theyre-hungry-and-husbands-who-fight-their-wives-dogs/), [GamesRadar poison apple](https://www.gamesradar.com/games/the-elder-scrolls/oblivion-intern-tried-to-outsmart-bethesdas-ai-and-was-stunned-when-his-apple-murder-strategy-actually-worked-i-cant-believe-you-accounted-for-this/), [SlashGear](https://www.slashgear.com/1237314/why-oblivions-npc-rampage-matters-for-the-future-of-ai-development/)

---

## 3. Ultima VII's schedules — the living world was a timetable

**What it did.** Every NPC in Britannia — hundreds of them — had a daily schedule: wake, breakfast, work, lunch, work, tavern, home, sleep. The baker went to the bakery in the morning and *actually baked bread* using the game's real item systems (flour + water + fire), then went to the pub in the evening and bellowed about his food. NPC dialogue led with name and job — who they are, not what the player needs.

**What it actually was under the hood.** Schedule scripts keyed to time of day, not intelligence. Data, not AI. The baker doesn't decide to bake; 8:00 says "bakery," and the bakery script says "bake." The genius was that the *world systems were real* — bread made from actual flour via actual fire — so following the schedule produced genuine consequences (there is bread to buy, or to steal).

**What worked.** The single most-cited "living world" in RPG history, on hardware weaker than a modern thermostat. Players still talk about watching the baker's day thirty years later. Schedules are *legible*: once you learn them, you can plan around them, which makes the world feel learnable rather than random.

**What failed.** Schedules create a player-side problem: *finding people*. If the person you need is only at the mint during banking hours, the game is wasting your time unless it gives you schedule legibility or time control. (Majora's Mask, §6 below, is the game that solved this properly.) Ultima VII mostly got away with it because the world was small and the day was short.

**The failure mode, named:** *Schedule opacity.* A living schedule the player can't read is just an NPC that's never where you need them.

**Steal this:** Schedules beat raw utility for shippability — they're cheap (a timetable per NPC), deterministic, debuggable, and legible. Our Tier D villagers are basically Ultima VII NPCs: name, schedule, a few lines, real actions against real world systems. And: publish schedules to players. Rumors ("the apothecary opens at eight"), the Harbinger, observable routine — schedule legibility is a feature, not a spoiler.

Sources: [Rock Paper Shotgun](https://www.rockpapershotgun.com/the-joy-of-npc-schedules), [MobyGames reviews](https://www.mobygames.com/game/608/ultima-vii-the-black-gate/reviews/), [Hardcore Gaming 101](http://www.hardcoregaming101.net/ultima-vii-the-black-gate/)

---

## 4. The Sims (1/2 era) — eight sliders that felt alive

**What it did.** Each Sim had eight motive sliders: Hunger, Comfort, Hygiene, Bladder, Energy, Fun, Social, Room. Motives decayed over time. Every object in the world *advertised* interactions with motive deltas ("eat: +Hunger, −time"; "chat: +Social"). The Sim's free will was a greedy optimizer: strongest deficit × signal strength × personality × distance. Priority order was roughly Hunger > Energy > Hygiene > Bladder > Comfort > Social > Fun.

**What worked.** Eight numbers produced a character that felt like it had a life. The trick: *the intelligence was in the objects, not the agent.* The Sim itself was nearly brainless — a deficit-chaser. The world was smart: hundreds of authored objects each advertising what they were good for. Combinatorial variety from a trivial decision rule. Personality stats (neat/sloppy, outgoing/shy, etc.) just biased which advertised actions won ties and added flavor reactions.

**What failed.** Greedy deficit-chasing has no notion of *plans* or *commitments*. Sims would abandon a half-eaten meal because Bladder ticked one point lower than Hunger — the famous "Sim puts down the sandwich to pee" behavior. No memory of what it was doing, no ability to finish what it started. Later Sims games bolted on wants/aspirations to fake longer horizons, with mixed success.

**The failure mode, named:** *Greedy myopia.* Pure motive-optimization can't keep a promise or finish a plan. It needs a second layer — which is exactly why our architecture has commitments/goals *above* the utility layer.

**Steal this:** This is Jay's drives-as-sliders lineage, and it's the correct Tier D/C engine: a handful of decaying needs + authored "advertisements" on world objects/actions + personality biasing the choice. Cheap, legible, and it *feels* alive. But pair it with the commitment layer from day one — even a Tier C villager needs "I said I'd meet you at the well at seven" to survive contact with a greedy optimizer. (Also note: the Sims' needs list is the ancestor of our "start with five needs" decision — Hunger, Energy, Safety, Affiliation, Duty is the same shape.)

Sources: [Sims Wiki: Autonomous reaction](https://sims.fandom.com/wiki/Autonomous_reaction), [Sims Wiki: Motive](https://sims.fandom.com/wiki/Motive), [GameSpot walkthrough](https://www.gamespot.com/articles/the-sims-walkthrough/1100-6086937/)

---

## 5. Engagement-gated depth — the direct precedents for our tiers

Three shipped games where NPCs gain depth specifically through player engagement. This is our tier system with the serial numbers filed off.

### Animal Crossing — hidden friendship as unlock ladder

**What it did.** Every villager tracks a hidden 0–255 friendship score. Levels unlock new interactions: daily gifts (30), selling you items + giving you a nickname (60), letting you change their catchphrase (100), changing their greeting + a chance at their photo (150), buying items from you (200+). Points come from daily chats (+1), gifts (+1–3), catching their fleas (+5), birthdays. Rudeness, ignored favors, and net-whacks *lower* it; neglected villagers can move away.

**What worked.** The depth is the reward for showing up. A new villager is a catchphrase and a shirt color; a best friend renames you "Guacamole" and gives you their photo. Players formed genuine attachments to what is, mechanically, a spreadsheet.

**What failed.** The grind is transparent once datamined — optimal play is "talk daily, gift wrapped furniture," which turns friendship into a chore checklist. And because the score is *hidden*, players who don't read wikis experience the unlocks as random.

**Steal this:** Two things. First, *hide the numbers, show the unlocks* — our villagers should never display "Tier 2"; they should just start remembering your name. Second, our tiers are this system with the unlock being *simulation complexity* instead of dialogue options: Tier D→C unlocks memory, C→B unlocks beliefs and commitments, and so on. The Animal Crossing lesson is that players will grind engagement for unlocks they can feel — so make each tier's new depth *visible in behavior*, not in a stat sheet.

Sources: [Nookipedia: Friendship](https://nookipedia.com:443/w/index.php?title=Friendship&oldid=74581), [Digital Trends guide](https://www.digitaltrends.com/gaming/animal-crossing-new-horizons-how-to-increase-friendship/)

### Stardew Valley — hearts, schedules, and threshold-gated scenes

**What it did.** Fourteen hearts per villager (250 points each), earned by daily talk and loved gifts, decaying slowly (−2/day) if neglected. Every villager has a full weekly schedule — seasonal variants, rain variants — that the player must learn to find them. At heart thresholds, one-time *heart events* fire: cutscenes with location, time, and weather conditions that reveal backstory (Shane's depression, Alex's grief). Eight hearts unlocks marriage candidacy.

**What worked.** The schedule *is* content: learning that the doctor does aerobics on Tuesdays is gameplay. Heart events are the payoff — authored depth scenes gated behind systemic engagement. One person (ConcernedApe) built a whole village this way, which is the right scale reference for us.

**What failed.** The decay punishes players who focus elsewhere, and the gift treadmill (loved gifts = fastest points) reduces "getting to know someone" to wiki-optimized present logistics. Late-game, maxed villagers become furniture — there's no *use* for a 14-heart friend.

**Steal this:** Threshold-gated depth scenes are our "major life events ratchet permanently" idea, shipped and proven. And: schedules the player learns are content — our rumor system should traffic in schedule knowledge ("Jekyll walks the marsh road at dusk now — since when?"). The anti-lesson: give high-tier NPCs ongoing *function* (commitments, jobs, information), not just a completed meter, or engagement dies at the cap.

### Majora's Mask — the Bomber's Notebook (depth without NPC memory)

**What it did.** Twenty townspeople, each on a strict 72-hour schedule. The Bomber's Notebook records each person's schedule, your promises to them (promise stickers), and your completions (happy stickers). Crucially: *the notebook persists across time loops even though every NPC forgets.* The progression system is not NPC state at all — it's the *player's* accumulated knowledge of who is where, when, and what they need.

**What worked.** The deepest NPC-schedule gameplay ever shipped, with effectively zero per-NPC memory. The depth lives in the player's head, externalized into the notebook. The 3DS remake even added alarms — the game helping you track schedules is a feature.

**What failed.** Almost nothing, mechanically — but note it only works because the loop resets. In a persistent world, "NPC forgets, player remembers" becomes "NPC forgets, player is confused why." The notebook works because forgetting is *explained*.

**Steal this:** This is the most important precedent for our cheap tiers. A Tier D villager needs *no memory whatsoever* if the *rumor/Harbinger/notebook systems* remember for the player. "Samantha Maitland's grandmother died — the Harbinger printed it, two villagers mentioned it, and now Samantha wears black" requires zero bytes of Samantha-memory; it requires the *world* to remember. Player-facing knowledge systems are NPC depth at zero per-NPC cost. Our quest log / rumor journal should be designed as the Bomber's Notebook from day one.

Sources: [Zelda Wiki: Bombers' Notebook](https://zelda.fandom.com/wiki/Bombers%27_Notebook), [Zelda Dungeon analysis](https://www.zeldadungeon.net/check-out-this-video-analyzing-how-majoras-mask-perfected-time-management-gameplay/), [Nintendo Insider on the 3DS improvements](https://www.nintendo-insider.com/majoras-mask-3d-improve-bombers-notebook/)

---

## 6. MOBProgs — the 1990s pattern still running the MUDs

**What it did.** ROM-derived MUDs (mid-90s onward) gave each mob small event-triggered programs: `greet_prog` (player enters room), `speech_prog` (keyword spoken), `give_prog` / `bribe_prog` (item or gold handed over), `fight_prog`, `death_prog`, `rand_prog` (percent chance per tick), `time_prog` (hour of day), `entry_prog` (mob itself moves). Scripts were a tiny interpreted language with if/else, stored in the area file, editable *in-game* by builders via OLC — no C coding, no recompile.

**What worked.** Thirty years later, hundreds of MUDs still run on this. Why: **zero cost when idle** (event-triggered, never polled); **scoped to one mob** (a builder can read the whole behavior); **authorable by writers** (the person writing the tragic blacksmith writes his reactions, not a programmer); deterministic and debuggable. The classic baker example from the ROM docs: one trigger greets entrants, another reacts to the phrase "fine day" — two triggers, and the shop feels staffed.

**What failed.** MOBProgs don't compose. Each mob is an island — no shared beliefs, no rumor propagation, no memory beyond flags. Ambitious builders hit the ceiling fast and either accept it or bolt on something bigger. Cross-mob coordination is painful.

**The failure mode, named:** *Island scripts.* Per-mob triggers scale to hundreds of mobs but never become a *society*.

**Steal this:** This is our Tier D substrate, almost verbatim — and it's *text-native*, which none of the graphical examples are. Event-triggered > polled: a villager who only "thinks" when spoken to, given something, or when their schedule block changes costs nothing the rest of the day. Build the tier system so Tier D *is* mobprogs-with-schedules, and each promotion adds exactly one new trigger family (memory adds `recall`, beliefs add `rumor_heard`). Also steal OLC: builders must be able to edit NPC behavior live, in-world, without a code deploy. That authoring loop is half of why mobprogs survived.

Sources: [ROM mobprogs doc](https://github.com/mjshuff23/staticchaos/blob/HEAD/doc/mobprogs.md), [Forgotten Kingdoms builder docs](http://www.forgottenkingdoms.org/builders/mobprogs.php), [darkcloud examples](https://github.com/dc-mud/darkcloud/blob/HEAD/doc/mob-prog-examples.md)

---

## 7. The alife corner — Creatures and Seaman (brief)

Jay knows these; the notes are for the design record.

**Creatures (1996, Creature Labs).** Norns ran on simulated biochemistry — drives as chemical concentrations (pain, three hungers, cold, hot, tired, sleepy, lonely, crowded, fear, boredom, anger, sex drive, comfort) feeding a ~1000-neuron brain. Drive *raised* = punishment chemical; drive *reduced* = reward chemical. Learning was behaviorist drive-reduction: Norns learned to eat when hungry but not when full. Genomes determined brain wiring; breeding inherited traits (and mutations). ([Source](https://en.wikipedia.org/wiki/Creatures_(artificial_life_program)), [drives doc](https://github.com/ugwun/creatures3-engine-port/blob/HEAD/tools/docs/drives_and_learning.md))

- **Worked:** drives + learning + history (genetics) is exactly Jay's formula, and it produced genuinely surprising, individual creatures. The internal state was *visible* (the biochemistry monitor), which made the Norns legible.
- **Failed:** real-time care demands (neglect = suffering = guilt), thin game loop beyond raising, and death as punishment. The attachment mechanics were coercive as much as charming.
- **Steal this:** make NPC internal state *legible to players* (the Creatures biochemistry monitor is our "observable routine" idea), and never make NPC depth demand real-time player labor — that's Seaman's failure too.

**Seaman (1999, Dreamcast).** Voice-driven virtual pet through life stages on a real-time clock; heavily scripted conversations gated by timers and daily check-ins.

- **Worked:** voice + personality + daily ritual created real attachment; the creature *talked about you*.
- **Failed:** miss a day and it suffered; progression was opaque ("talk to it correctly for weeks"); the scriptedness showed through once you'd seen the branches.
- **Steal this:** the caution — engagement-gated depth must never become *neglect-punished* depth. Our demotion on neglect should be slow, graceful, and invisible (the villager just gets quieter), never guilt-tripping.

---

## 8. Dwarf Fortress — stress, thoughts, and the tantrum spiral (supplement)

The handoff (§19) covers DF's personality facets and preferences. The supplement that matters for us:

**What it did.** Every event generates *thoughts* ("ate a fine meal," "witnessed death," "was caught in the rain") whose emotional weight is filtered through ~50 personality facets (STRESS_VULNERABILITY, ANGER_PROPENSITY, etc.). Thoughts feed a *stress* accumulator. Overwhelmed dwarves break down by personality: tantrums, depression, berserk rage. Dwarves also have *needs* derived from personality and values (acquire objects, hone a craft, socialize, pray).

**What worked.** Residues beat transcripts: DF stores *stress*, not a diary. A compact, shared event list × personality filter = deep individual differentiation from almost no per-dwarf content. "The same event affects different dwarves differently" is the whole trick, and it's cheap.

**What failed.** The famous **tantrum spiral**: stressed dwarves tantrum → tantrums stress witnesses → witnesses tantrum → fortress destroys itself in a domino cascade. Positive feedback loops in emotional systems detonate. Modern DF damped this, but the lesson stands.

**The failure mode, named:** *Emotional positive feedback.* Any system where NPC distress propagates to other NPCs needs a damper, or one bad week ends the village.

**Steal this:** Our affect residue + habits design is DF's thoughts/stress with the serial numbers filed off — good. But design the dampers *first*: rumor distress should decay with retelling distance, one NPC's breakdown should mostly sadden rather than enrage witnesses, and the village needs ambient positive events (festivals, good harvests) as a stress sink. The Mist, the Harbinger, the changing seasons — our world already has mood infrastructure; wire it to the residue system.

Sources: [DF Wiki: Personality facet](http://dwarffortresswiki.org/index.php/DF2014:Personality_facet), [community stress discussion](https://steamcommunity.com/app/975370/discussions/0/5792223132452520842/)

---

## 9. A necessary separation: Ultima Online ≠ Ultima Ratio Regum

Because both "Ultimas" appear in our research and they could not be more different:

| | Ultima Online (1997) | Ultima Ratio Regum (in development since ~2011) |
|---|---|---|
| What | Commercial MMO by Origin | Solo-dev procedural roguelike by Mark Johnson |
| NPC lesson | Virtual ecology: simulated predator/prey/resource economy; killed by compute cost + player predation | Procedural *culture*: dialects, greetings, insults, rituals, religion generated per civilization; template-based dialogue variation |
| Our takeaway | Constrain simulation; cost follows attention | Cheap distinctiveness: deterministic cultural/dialect data makes NPCs sound different with zero inference |

URR's lesson (§22 of the handoff) stands as written: a villager can sound personally and culturally distinct through word choice, formality, greetings, and taboos — all deterministic data. That's our dialogue-rendering layer for Tiers D–B: no model, just well-built phrase banks keyed to personality stats and village culture.

---

## Synthesis: the recurring lessons

Across thirty years of shipped systems, the same lessons keep appearing. Four confirm the priors; two are additions.

**1. Constrain the simulation; cost follows player attention.** (UO ecology, Radiant AI, MOBProgs.) Every unconstrained sim in this memo either got ripped out (UO), nerfed for ship (Oblivion), or never attempted anything beyond events (MOBProgs — and it's still running). Our engagement tiers are the principled version: a villager nobody visits costs a schedule row and a few trigger checks. Attention is the budget allocator. This is also the fixed-hosting-budget answer: the sim's cost scales with *engaged* NPCs, and engaged NPCs are bounded by player count, not village size.

**2. Schedules beat raw utility.** (Ultima VII, Stardew, Majora's Mask.) The most beloved "living worlds" are timetables, not thinkers. Schedules are cheap, deterministic, debuggable, and — critically — *legible to players*, which turns NPC routine into gameplay (planning, rumors, stakeouts). Utility AI should live *inside* schedule blocks ("it's work hours; which work task?"), not replace them.

**3. Residues beat transcripts.** (DF stress, Sims motives, Creatures drives, Tamagotchi.) Nobody stores what happened; everybody stores *what it left behind* — stress, motive levels, drive chemicals, habits. A handful of decaying numbers, filtered through personality, differentiates individuals more cheaply than any memory log. Our affect-residue + habit design is the consensus solution, arrived at independently four times.

**4. The intelligence lives in the world, not the agent.** (Sims' advertising objects, UO's resource values surviving the AI's removal, Majora's notebook.) The cheapest depth is world-side: objects that advertise uses, resources with real values, player-facing knowledge systems that remember what NPCs don't have to. When choosing where to spend complexity, spend it on systems every NPC shares, not on per-NPC brains.

**5. Feedback loops need dampers — design them first.** (Tantrum spirals, Radiant AI murder cascades, UO's predation collapse.) Any NPC→NPC propagation (rumors, distress, violence) needs decay, distance falloff, and ambient sinks, or one bad week ends the village. This is the one the handoff's architecture doesn't explicitly cover: add damper design to the rumor and affect systems before implementation.

**6. Hide the numbers; show the unlocks.** (Animal Crossing.) Players bond with villagers whose friendship score they'll never see, revealed only through new behaviors. Our tiers must never display as tiers. Samantha Maitland doesn't become "Tier C" — she just starts remembering your name, then your business, then your secrets. The demotion side must be equally invisible: she gets quieter, not a debuff icon. (And per Seaman: never guilt the player for it.)

### How this maps to our tier design

- **Tier D (villager):** Ultima VII schedule + MOBProg triggers + URR phrase banks. Zero memory. Cost: ~nothing.
- **Tier C (acquaintance):** + Sims-style needs + DF-style residues and habits + Animal Crossing unlock ladder (remembers you, new interactions). Memory: bounded episode list.
- **Tier B (regular):** + beliefs with provenance + commitments + rumor participation. The handoff's Layers B–F, switched on.
- **Tier A (major resident):** + full relationship matrices + personal arcs + optional small-model dialogue rendering. The only tier where inference is ever on the table — and the NO-LLM-MODE test means even Tier A must degrade to templates gracefully.
- **The shopkeeper rule** (role-bounded complexity) is Radiant AI's shipped solution: transaction mode at work, person mode off-duty. Generalize it: *every* NPC's depth is bounded by their role first, their engagement second.
- **Genealogy** is the cheap-history trick: DF family relations + Caves of Qud procedural history. A generated NPC with two named relatives and one family rumor has a past for the cost of three strings. Do it at generation time, not simulation time.
- **The Bomber's Notebook principle:** the rumor journal / Harbinger / quest log carries NPC depth the NPC doesn't have to. Design these as first-class depth systems, not UI conveniences.
