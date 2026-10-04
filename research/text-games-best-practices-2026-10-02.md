# Successful Text Games — Best Practices for Frankenstein Village

*Researched 2026-10-02. Covers long-running MUDs (Aardwolf, Achaea, Discworld, Threshold), browser text games (Fallen London, Kingdom of Loathing), the interactive-fiction community (IFComp conventions, puzzle fairness), Choice of Games design discourse, and the Japanese sound-novel/visual-novel tradition. NWN persistent worlds were surveyed separately (research/nwn-rp-servers-2026-10-02.md) and are referenced, not repeated.*

*Why this matters:* text games are the only genre where a two-person team has repeatedly beaten studios — because text is the cheapest content medium ever invented. Every finding below is about what that cheapness enables and what it punishes.

---

## 1. Onboarding that works: the first fifteen minutes

**Discworld MUD's Pumpkin Town.** New players start in a dedicated newbie area, deliberately *away* from the real world — and it wastes no time establishing tone. The Equipment Emporium's weapons department has a sign reading "If you must run with the weapons, please run towards the door." The lesson: the tutorial's job is not to teach commands, it's to teach *what kind of place this is*. Mechanics can come later; voice comes first.

**Achaea's layered help.** Iron Realms built what reviewers call the most newbie-friendly MUD tutorial ever written — immersive, in-fiction — and then accepted that "after that tutorial, the mechanics do become much more foggy." Their answer wasn't a better tutorial; it was *two or three different sources of help* for confused newbies: in-game helpers, friendly players, help files. Redundancy, not perfection.

**Threshold's hardball.** Threshold RPG simply *forces* roleplay and bans OOC chatter except in help channels. An Engadget reviewer: "I would love it if more games did this, but it takes guts." The finding: strictness at the door is cheaper than strictness later. Players who accept the rule on entry never need to be policed.

**Thain's hardest lesson (NWN, but universal).** A player guide warns newcomers: "you are not the focus of Thain... probably the hardest part to get used to." Persistent worlds fail newbies not with complexity but with *irrelevance* — the veteran world doesn't need you. The fix used everywhere that works: give the newcomer something that is *theirs* within minutes (a room, a task, a person who knows their name).

**Village take:** Our arrival guide + M.'s greeting already do the Pumpkin Town job (tone first, in-fiction). The gap to close: the first-15-minutes *task*. A new arrival should leave the Tavern with one rumor they personally chose to follow — a private thread, not a quest marker. And the Threshold lesson validates what we already built: the front door enforces the compact architecturally, so we never have to police it socially.

---

## 2. Retention loops: what brings players back

**Kingdom of Loathing's anti-poop-socking.** KoL gives 40 adventures per day, rollover-capped at 200. The design insight is inverted from most games: *limited daily turns remove the incentive to binge*. You can't fall behind by sleeping, because nobody can play more than the cap. Unused adventures accumulate, so absence is forgiven. This is the single most portable retention mechanic in text games: the game respects the player's time, and the player returns because returning is always worthwhile, never mandatory.

**KoL's Ascension.** Beat the final boss and you can restart from level 1 keeping one skill per run, with challenge paths (robot, boss-class, oxygenarian) and speed leaderboards. It's New Game Plus as the *core* retention loop: the same content, recombined by constraints, with permanent accumulation across runs. Players don't need new zones; they need new *rules for old zones*.

**Fallen London's action economy.** Actions refill over time; monthly Exceptional Stories are "seasons of DLC." But the operative quote is Alexis Kennedy's: "Oh my God, players consume Fallen London content so quickly. I'll spend a week building something and that's including all these careful checks to stop them gobbling everything up all at once." His answer, learned making Sunless Sea: build a *core loop* (sailing, trading, surviving) so there's "room to breathe between writing content." Content-only games are treadmills; loop-first games pace themselves.

**Achaea's social progression gate.** A veteran on Hacker News: "you literally couldn't even get class abilities without joining a group and inheriting its political positions, friends, enemies." The majority of the game was conflict *between players* — guilds, cities — not developer quests. Retention came from other people needing you, not from content.

**Village take:** Three adoptions. (1) The KoL cap, adapted: our mysteries should never punish absence — rumors persist, the ledger remembers, and nobody "falls behind" because there is no ladder. Consider a soft daily rhythm (the Harbinger's morning edition, the Tavern's nightly talk) that rewards return without demanding it. (2) The Ascension shape maps to our calling system: respecialization that keeps history is New Game Plus without the reset — a new calling with old memories is a new ruleset for the same village. (3) The Achaea lesson is our "no one does it all" rule with teeth: interdependence isn't flavor, it's the retention engine. The player who needs the herbalist comes back tomorrow.

---

## 3. Content cadence: shipping without burning out

**The Failbetter treadmill.** Kennedy's week-of-work-gobbled-instantly is the fundamental economics of hand-written content. Their solutions, in order: (a) action-gating to throttle consumption; (b) monthly Exceptional Stories as a sustainable DLC rhythm; (c) eventually, core loops that don't need writing. For us, the generator pipeline (packet → batch → audit) is the throughput answer, but Kennedy's warning stands: *throttle consumption, don't just accelerate production*.

**KoL's writing-carries-gameplay.** Reviewers agree the gameplay is simplistic — three combat actions, fetch quests — and that the *writing* is the game. The lesson: in text, prose quality IS the content budget. A witty item description is cheaper than a new system and retains better.

**Visual novels: routes as content multiplication.** The Japanese tradition (see §7) gets 50+ hours from one cast and one town by routing: the same content, recombined by perspective. Our incident templates already work this way (one skeleton, many variants) — the memo's term for it: *recombination beats production*.

**Player-created content that actually works.** KoL's wiki is player-maintained and essential (crafting "requires a guide on the wiki" — the community filled the documentation gap voluntarily). Arelith's printing press (covered in the NWN memo) puts player books on world shelves. The pattern: give players *a format with a gate* (wiki page, submitted book, chronicle entry) and they produce the long tail for free.

**Village take:** Our six content families are the production side; the missing piece is the *consumption throttle*. Rumor propagation with distortion IS a throttle (one seed becomes weeks of talk), and the legend pipeline (event → ledger → Harbinger → rumor → quest hook) is a content multiplier — one player action becomes many content units. Protect that pipeline; it's the economic engine. And the family-6 chronicle hooks should accept player-authored entries through the audit gate, per the NWN adoption.

---

## 4. Social architecture: belonging vs. cliques

**Achaea's participatory depth.** "These games have always been deeply participatory: player-run guilds, player-run cities." The HN veteran's punchline: a playable class was based on *his* fiction for the official history. When players can change canon, they belong. When they can't, they're tourists.

**KoL's chat gate.** In-game chat requires passing a spelling and grammar test; "leet speak" is frowned upon. This looks elitist and works brilliantly: the social space has a *quality floor*, and the floor is about effort, not status. The community self-selects for people who care about words — in a text game, that's everyone who matters.

**Threshold's enforced IC.** No OOC chatter except help channels. The social architecture *is* the fiction; there is no backstage to retreat to. (Contrast our design: the Inn Between puts the backstage *inside* the fiction. Nobody tried that; it's our experiment.)

**The clique failure mode.** Every long-running MUD thread mentions it: veteran cliques that freeze out newcomers, "you are not the focus" as a permanent condition rather than a phase. The successful counter-pattern, from multiple sources: *newcomer-visible roles* — jobs, tasks, minor offices that only new players can hold, or that explicitly need fresh blood (Achaea's houses recruit; Discworld's guilds take apprentices).

**Village take:** Two moves. (1) A KoL-style quality floor for the Tavern: not a spelling test, but the compact itself does this work — the front door selects for people willing to play along. (2) Newcomer-visible roles from day one: the Chronicle needs stringers, the Harbinger needs distributors, the watch needs runners. A new arrival should be *recruitable* within their first session — belonging is a job offer, not a vibe.

---

## 5. Fairness and trust: what works at small scale

**The IF community's fairness doctrine.** Decades of IFComp judging produced the clearest fairness standard in games: a puzzle must be solvable from information *the game taught*, never from outside lookups or guess-the-verb. Andrew Plotkin's "forgiveness" concept: good games forgive player mistakes rather than punishing exploration. Robin Johnson's *Detectiveland* solved guess-the-verb with a hybrid interface — buttons for all interactions, so the player can never be stuck *on the interface*, only on the mystery. And multiple UNDO as a standard mercy.

**The Rule of Fair Exchange** (from design discourse): you may break any genre convention provided you replace it with a systemic interaction offering equal or greater agency, clarity, or thematic depth. Never strip a player's mental model without giving them a better tool. This is the anti-frustration rule in one sentence.

**KoL's multis rule.** "If your main character is accumulating wealth or advancing at a rate faster than would be possible without multis, you're in violation." Note the shape: the rule targets *the effect* (impossible advancement rate), not the method. Detectable, explainable, fair.

**Invisiclues (1982).** Infocom's progressive hint booklets — the original graduated hint system. Each question reveals a little more, so the player chooses exactly how much help to take. Still the best hint UX ever designed: hints are *player-paced*, never patronizing, never all-or-nothing.

**Small-scale moderation reality.** At small scale, the effective pattern from every source: transparent rules, visible enforcement, warnings-first (our arrival guide already promises this: "warnings first, then removal"), and — critically — *rules that target intent, not action* (the NWN memo's "mechanic allows, norm judges motive"). In a text world everything is intent anyway.

**Village take:** Three adoptions. (1) The IF fairness doctrine becomes our quest-design law, stated plainly: *no mystery may require information the game didn't teach, and no mystery may punish the attempt*. Our "no click-to-solve" rule needs its twin: "no punish-the-guess." (2) Invisiclues-shaped hint design: the *examine* verb and NPC testimony should offer graduated help — first examination gives surface, skilled examination gives depth, and the player controls how deep they go. (3) The KoL multis rule shape for our mixed human/AI population: write rules against *effects* (impossible knowledge, impossible speed), not against *substrates*. Never "AIs can't do X" — always "nobody can do X faster than Y."

---

## 6. Failures: what killed text games and features

**Content exhaustion.** The MMO design notes put it bluntly: hardcore players consume months of developer content in weeks. Every content-treadmill game dies this way unless it finds Kennedy's core loop or KoL's ascension. *Our* hedge is the rumor/distortion engine and the legend pipeline — systems that multiply content rather than merely serving it.

**Fake choices.** The Telltale problem, documented mercilessly: "take a look at when you have the chance to save Nick or Pete... No matter which you choose, they both die." Players forgive a lot; they don't forgive learning their agency was theater. Our "choices close doors" rule is the direct antidote — but it must be *real*. Every door-closing choice in the incident templates needs a genuinely different village on the other side, or it's Telltale with better prose.

**The tutorial wall.** Games that front-load mechanics lose everyone. (Achaea's foggy post-tutorial is the honest version: they stopped pretending the tutorial could teach everything.) Our arrival guide is a pamphlet, not a wall — keep it that way.

**Infrastructure dependency.** Covered in the NWN memo (GameSpy 2014); not repeated here except to note it's the most common *external* cause of text-world death, and we're already hedged.

**Village take:** The two killers to actively design against are content exhaustion (hedge: the rumor engine + legend pipeline as multipliers, not the families as a treadmill) and fake agency (hedge: audit every door-closing choice for a *real* difference, not a reskin). Both are already named in our design; this memo upgrades them from principles to survival requirements.

---

## 7. The Japanese tradition: sound novels and the player's memory

**Chunsoft's sound novels (1992–).** Full-screen text, atmospheric audio, minimal visuals, choices that branch. The founding insight, still prescient: *compelling stories + atmosphere + agency need no complex mechanics*. *Otogirisō* and *Kamaitachi no Yoru* built a commercial genre on text alone — decades before "text games" needed defending in the West.

**The player's brain as storage.** *Kamaitachi no Yoru* deliberately stored critical information (passwords, names) in the *player's* memory rather than the game's — later echoed by *Virtue's Last Reward*. Some modern VNs are returning to this: the game refuses to track what the player should remember. For a mystery world, this is a design tool, not a limitation: *what the game won't write down, the village must talk about*. Our journal is "coming soon" per the arrival guide — consider keeping it *deliberately* thin. A perfect journal kills gossip; a fallible one feeds it.

**Routes, not content.** Fate/stay night: 50+ hours, one town, three routes. The content multiplies by perspective. Our incident variants and rumor distortion ladders are the same move in systemic form.

**Village take:** The sound-novel lesson is *atmosphere over mechanics* — our "dread as weather" rule, independently derived, is the same thesis. And the player-memory insight deserves a real decision: how much does the game remember *for* the player? Every convenience feature (quest log, perfect journal, rumor archive) is a small withdrawal from the social economy. Spend carefully.

---

## 8. Diegetic teaching: the shrine is the manual (2026-10-03 field note)

**Lost Pig (Admiral Jota, IF Comp 2007) teaches its whole verb vocabulary without help text.** The underground complex is a tutorial wearing a dungeon costume: a west mural teaches the pole, an east mural teaches powder-fire-water, the Fountain Room curtain-tapestry teaches torch-and-escape, and the gnome *demonstrates* ignition by spitting into his pipe to make smoke — the spit-spark recipe is shown, never told. The player learns by reading the world's own artifacts, not by typing `help`.

**Village take:** This is our onboarding answer, and it rhymes with the whole design grammar. Murals, tapestries, shrine carvings, NPC habits — lore that is also a manual. A new player should learn verbs from what villagers *do* and what the village *remembers in stone*, not from a help command. It also feeds the rumor engine for free: a mural everyone can read is a rumor with a permanent source. Design rule: before adding any help text or newbie hint, ask what wall it should be painted on first.

---

## Appendix: sources

- Medium, "Multi-User Dungeons: 10 games still serving up text-based fun" (2023, updated 2026): https://medium.com/@the_andruid/multi-user-dungeons-10-games-still-serving-up-text-based-fun-in-2023-1e3951d3bf43
- PC Gamer, "A quick tour of Discworld MUD" (2022): https://www.pcgamer.com/saturday-crapshoot-discworld-mud/
- Engadget, "Free for All: Interviewing Achaea's Matt Mihaly" (2013): https://www.engadget.com/2013/05/29/free-for-all-interviewing-achaeas-matt-mihaly-for-mud-may/
- Engadget, "Rise and Shiny: Threshold RPG" (2012): https://www.engadget.com/2012/05/27/rise-and-shiny-threshold-rpg/
- Wikipedia, "Achaea, Dreams of Divine Lands": https://en.wikipedia.org/wiki/Achaea,_Dreams_of_Divine_Lands
- MUDs Wiki (Fandom), "Achaea" (newbie re-engagement emails): https://muds.fandom.com/wiki/Achaea
- Hacker News, "Multi-User Dungeons (MUDs): What Are They?" (2021): https://news.ycombinator.com/item?id=26291145
- Rock Paper Shotgun, "Impressions: Fallen London": https://www.rockpapershotgun.com/impressions-fallen-london
- PC Gamer, "I've swapped modern live service games for a browser game that's been running since 2009" (2025): https://www.pcgamer.com/games/rpg/ive-swapped-modern-live-service-games-for-a-browser-game-thats-been-running-since-2009/
- Eurogamer, "The city and the sea: the story of Failbetter Games": https://www.eurogamer.net/the-city-and-the-sea-the-story-of-failbetter-games
- Rock Paper Shotgun, "Failbetter on the unlikely success of Fallen London's first ten years": https://www.rockpapershotgun.com/failbetter-games-on-the-unlikely-success-and-10-year-anniversary-of-fallen-london
- GameGrin, "Recommending Kingdom of Loathing in 2023": https://www.gamegrin.com/articles/recommending-kingdom-of-loathing-in-2023/
- The Escapist, "Stumbling Into the Kingdom of Loathing": https://www.escapistmagazine.com/Stumbling-Into-the-Kingdom-of-Loathing/
- Wikipedia, "Kingdom of Loathing" (adventures, ascension): https://en.wikipedia.org/wiki/Kingdom_of_Loathing
- IntFiction Forum, "Forgiveness" (Invisiclues history, Plotkin): https://intfiction.org/t/forgiveness/10200
- Rock Paper Shotgun, "IF Only: Games of Mystery and Discovery from IF Comp 2016" (Detectiveland): https://www.rockpapershotgun.com/if-comp-2016-best-games
- Choice of Games Forum, design discourse (delayed branching, stat indicators): https://forum.choiceofgames.com/t/telltale-games-thoughts/22561?page=8
- Wikipedia, "Visual novel" (history, economics): https://en.wikipedia.org/w/index.php?title=Visual_novel&oldid=1376383113
- TechInBengali, "7 Revolutionary Chunsoft Sound Novels": https://en.techinbengali.com/chunsoft-sound-novels-gaming-history/
