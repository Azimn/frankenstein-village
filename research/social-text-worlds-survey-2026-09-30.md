# Social-First Text Virtual Worlds: A Design Survey

**Date:** 2026-09-30
**Purpose:** Design reference for a new social-first persistent text MUD for mixed human + AI players (likely Evennia-based). Tavern, not raid.
**Method:** Four parallel research passes over real sources — game sites, wikis, code repos, community docs. URLs cited inline. Not model memory.

---

## 1. Lineage & Setup: MUSH, MUCK, MUX, MOO

The social branch of the MUD family tree descends from TinyMUD (1989) through four main lines. All four share one radical premise: **the world is a database that players program from inside.**

### PennMUSH (C; forked 1991, Penn branch from UPenn/PernMUSH)

- **Architecture:** Thin C server (connections, flat-file DB, expression evaluator). The real system is **softcode (MUSHcode)**: a functional expression language — bracketed `[function(arg,arg)]` calls, `%` substitutions (`%#` = executor, `%N` = name) — written and edited *from inside the game* via `@create`, `&ATTR obj=value`, `@trigger`, `@switch`, `@dolist`, `@wait`. Scene systems, character sheets, mail, bulletin boards are all softcode objects living in the database. "A PennMUSH game is not so much configured as programmed by its players." ([muindex PennMUSH reference](https://github.com/sharpmush/muindex/blob/HEAD/content/reference/codebase-pennmush.md))
- **Building:** Any player with the **BUILDER** flag can `@dig` rooms, `@create` things, `@open` exits, `@link` them, `@desc` everything. **Quotas** bound it (`@quota`); powers like `no_quota`/`no_pay` exempt specific players. "Builders" are a recognized social role; staff hand out the BUILDER bit. ([SharpMUSH powers doc](https://github.com/sharpmush/sharpmush/blob/HEAD/SharpMUSH.Documentation/Helpfiles/SharpMUSH/sharpfunc.md))
- **Flags/powers:** Hierarchy GOD (#1) → WIZARD → ROYALTY → player → guest. Flags are coarse capability bits (`WIZARD`, `BUILDER`, `DARK`, `FLOATING`, …); **powers** (`@power`) are fine-grained grants; **@locks** gate per-object access with boolean key expressions. ([SharpMUSH permission design](https://github.com/sharpmush/sharpmush/blob/HEAD/docs/design/permission-visibility.md); [ursamu compatibility doc](https://github.com/ursamu/ursamu/blob/HEAD/docs/mush_compatibility.md))
- **Day one:** Compile the C server, tune `mush.cnf` (function invocation limits, queue CPU time), create the wizard character, `@dig` the starting rooms from inside, load softcode infrastructure (mail, bboards, channels, job system) from community packs like volundmush. Nick Gammon's tutorial walks the literal first hour. ([volundmush install guide](https://github.com/volundmush/mushcode); [Gammon tutorial PDF](https://mail.gammon.com.au/files/pennmush/mush_tutorial.pdf))

### FuzzBall MUCK (C; TinyMUCK 2.0 → FuzzBall v5, 1995; actively maintained on GitHub)

- **MUF (Multi-User Forth):** The in-game system language — stack-based, compiled into first-class **Program** objects via an interactive in-game editor (`@program`), then attached to exits/actions. Notably, *fundamental MUCK commands are themselves MUF programs* — built-ins get replaced in-world by better MUF versions, so the server/player-code boundary is porous by design. ([MUD Wiki: MUF](https://mud.fandom.com/wiki/MUF_(programming_language)); [fuzzball README](https://github.com/fuzzball-muck/fuzzball/blob/HEAD/README.md))
- **MPI:** Inline `{function:arg,arg}` expressions embedded in descriptions — the layer for what MUSH softcode does. Has explicit resource rails: max 26 recursion levels, 256 loop iterations, list caps; permission errors stop scripts touching restricted properties. ([MPI Reference Manual](https://www.fuzzball.org/docs/mpihelp.html))
- **Building culture:** `@dig/@create/@open/@link/@describe/@lock/@recycle`. The economy is **pennies**: building costs money; mortals cap at 10,000 pennies; **wizards don't need money**. Culturally, MUCK is the home of the hobby's social/fandom worlds (FurryMUCK, Tapestries) — "built around presence and conversation rather than around scenes with a start and an end, which is a real difference from the roleplay MUSH tradition." ([MUCK Reference Manual](https://www.fuzzball.org/docs/muckhelp.html); [muindex MUCK reference](https://github.com/sharpmush/muindex/blob/HEAD/content/reference/codebase-muck.md))

### TinyMUX (C/C++; forked from TinyMUSH 2.0)

Same shared vocabulary as PennMUSH (softcode, flags, locks, quotas), common ancestor — but **not compatible**: databases don't move between codebases without conversion, function libraries and parser behavior differ. The family tree is a braid: TinyMUSH 3.0–3.3 derive from a merger of TinyMUSH 2.2.5 and TinyMUX 1.6. Practical lesson: **choose one codebase; treat softcode as semi-portable at best.** ([Wikipedia: MUSH](https://en.wikipedia.org/wiki/MUSH); [TinyMUX flatfile survey](https://github.com/brazilofmux/tinymux/blob/HEAD/docs/survey-flatfile-formats.md))

### LambdaMOO (C; Pavel Curtis, Xerox PARC, 1990)

- **Object/verb/property model:** Everything is an object with an owner, a single parent (prototype inheritance), named properties, and named **verbs** — code attached to objects, compiled live in-world with `@program`/`@edit`. A "player" is just an object flagged player. ([mooR glossary](https://github.com/biscuitwizard/thetis.ai/blob/HEAD/skills/moor/references/glossary.md))
- **Permissions:** Per-object (`r`/`w`/`f` fertile) and per-verb/per-property (`r`/`w`/`x`/`d`/`c` change-owner) bits. The key design insight: **verbs run with their author's (owner's) permissions** — setuid-by-default. This is safe delegation through ownership: you can give someone a tool that acts with *your* authority, bounded by ownership bits. ([Programmer's Manual ch. 2](http://www.ipomoea.org/moo/pm1.8.3/ProgrammersManual.pdf))
- **Governance history (the founding case study):** In March 1993, a player ("Mr. Bungle") used a "voodoo doll" object to force other players' avatars into sexual acts in a public room. Archwizard Haakon (Curtis) responded not with a ruling but with a **mechanism**: in-MOO petitions and ballots where any player could put to popular vote anything requiring wizardly powers, with results **binding on the wizards**. Within months, players voted in a `@boot` command and an ad-hoc mediation system. Origin story of "code is law, but the community writes the law." ([Wikipedia: A Rape in Cyberspace](https://en.wikipedia.org/wiki/A_Rape_in_Cyberspace); [Dibbell's original article](https://amenbreak.netlify.app/library/A-Rape-in-Cyberspace.pdf))

### How player-building changes the admin's job

On a combat MUD the admin authors content and players consume it. Here players *are* the content pipeline, so the admin's job shifts to: (a) **capacity governance** — quotas, pennies, object counts; (b) **capability delegation** — who gets BUILDER/programmer, which powers; (c) **commons maintenance** — shared spaces, the code library, build disputes; (d) **governance of the builders** — LambdaMOO's lesson: when players can program the world, plan the dispute/petition machinery *before* the first crisis, not after.

---

## 2. The Gameplay Loop: A Tuesday Evening on a Social MUSH

You connect, and the first thing you do isn't move or fight — you check the social dashboard. `WHO` to see who's on; on AresMUSH games, the web portal's Active Scenes page. Orientation guides advise checking the activity *heatmap* rather than the live count — fifteen people every evening and none at 4am is healthy; you're just early. ([muindex orientation](https://github.com/sharpmush/muindex/blob/HEAD/content/reference/orientation-collaborative-roleplay.md))

**The core unit of play is the scene:** a bounded, collaborative writing session between 2–6 players, conducted in prose "poses" in round-robin order. On AresMUSH games, scenes are first-class objects: create one in your room or a disposable **temp room** (recycled when the scene ends), **advertise it as "open"** so passersby know they're welcome, and every pose is auto-logged and shareable to the web wiki. ([AresMUSH scenes tutorial](https://github.com/aresmush/aresmush/blob/HEAD/plugins/scenes/help/en/scenes_tutorial.md); [Heroes Assemble Scene Code](https://heroesassemble.mushhaven.com/index.php?title=Scene_Code&))

A typical evening, concretely:

1. **Catch-up (10–15 min).** Read unread bboard posts (bulletin boards are the asynchronous backbone), check mail and requests. Note: **"+jobs" is not quests** — on MUSHes it's a staff support-ticket queue (character applications, building approvals, admin asks; workflow NEW → OPEN → DONE → ARCHIVE). "Checking +jobs" is checking the bureaucracy of a living world. ([AresMUSH jobs tutorial](https://github.com/aresmush/aresmush/blob/HEAD/plugins/jobs/help/en/jobs_tutorial.md))
2. **Find or start a scene (the meat, 1–3 hrs).** Three discovery paths: (a) spontaneous — walk into the public RP hub (the bar/tavern/square) and start; (b) arranged — page a friend for a pre-negotiated private scene; (c) scheduled events — staff- or player-run calendar events with signup/RSVP. Etiquette: always page first before joining a scene in progress, even in a public room. ([Heroes Assemble RP Etiquette](https://heroesassemble.mushhaven.com/index.php?title=RP_Etiquette&))
3. **The pose rhythm.** A pose is a paragraph or three of third-person prose plus dialogue, landing every 5–15 minutes in live scenes. Modern AresMUSH supports **async scenes** — people pose hours apart across timezones in the web portal. ([musoapbox discussion](https://musoapbox.net/topic/2897/getting-young-blood-into-mu-ing/144?lang=en-US))
4. **Between scenes: the OOC economy of attention.** Chat on OOC channels, discuss plots, write wiki entries, submit requests, read other people's published scene logs. Reading logs of scenes you weren't in is a major entertainment stream.

One veteran's memoir of PernMUSH: the dragonrider application was "a long administrative process of applications, peer review, and demonstrating roleplaying skill," and play was "like an intensive writing class." ([Gizmodo: Confessions of a Virtual Dragonrider](https://gizmodo.com/confessions-of-a-virtual-dragonrider-5127093))

---

## 3. Progression Without Combat

### Rank ladders (status as advancement)

- **PernMUSH:** A rigid, writing-codified hierarchy — Senior goldrider → junior goldriders → Weyrwoman → Seconds → Wingleaders → bronzeriders → wingriders → weyrlings/candidates/drudges ("these people have no rank"). Rank is "very respected"; disagreement with superiors must be polite or punished. Advancement = impressing a dragon, surviving weyrling training, climbing wing hierarchy — all gatekept by staff + peer review, never XP. Candidacy ran on rotational "Search Cycles" announced on bboards. ([Pern rank ladder](http://www.geocities.ws/pernese/writing.html); [Alchetron: PernMUSH](https://alchetron.com/PernMUSH))
- **Star Wars MUSHes:** IC rank with time-in-service gates — each step requiring "at least two months" of service *or* "considerable merit"; rank gates which missions you may join and what you can command. **Mentor-discretion promotion**: a mentor of Lieutenant+ promotes cadets "at their discretion" — advancement as a social relationship, not a point total. ([SW RP rank docs](https://thestarwarsrp.com/index.php?threads/grand-army-of-the-republic-ranks.7281/))

### Professions with weekly paychecks (Star Wars: Age of Alliances, founded 2001)

Choose a career; receive a **weekly paycheck scaled to your skills** — persistent income tied to IC occupation, not kills. Civilian play is explicitly fully supported (free ships, org-based plotlines): non-combatants get a complete game. ([mudstats: SW:AoA](https://mudstats.com/World/StarWarsAgeofAlliances))

### RPP — participation as XP (Emblem of Ea, AresMUSH)

**Roleplay Points awarded automatically for every scene you participate in**, tracked **per player, not per character**. RPP gates new character registration — hitting a threshold unlocks another alt (capped at 2/person). The scarce prestige resource (the right to play more characters) is earned purely by showing up and roleplaying. This is the cleanest mechanical answer to "what replaces the level grind": *participation itself is the XP*. ([Emblem of Ea alts doc](https://github.com/emblemofeamu/aresmush/blob/HEAD/plugins/arescentral/help/en/alts.md); [RPP doc](https://github.com/emblemofeamu/aresmush/blob/HEAD/plugins/pf2noms/help/en/rpp.md))

### Beat/XP economies (World of Darkness MUSHes)

Tabletop Beat → XP economy: resolving a Condition or fulfilling an Aspiration awards Beats; five Beats = one Experience; XP buys sheet advancement. On WoD MUSHes, XP awards are **staff-judged** (1–4 XP typical; ~100 XP/year of weekly play moves early- to late-career). ([ursamu cofd README](https://github.com/ursamu/ursamu/blob/HEAD/packages/cofd/README.md); [2d12 advancement doc](https://github.com/skroxiousdm/2d12gamesystem/blob/HEAD/docs/21-advancement.md))

### Prestige, Renown, boons, Status (WoD social currency)

- **Werewolf:** Renown in Glory/Honor/Wisdom drives Rank (Cliath → Fostern → Adren → Athro → Elder). Renown is mechanically *spendable/drainable* — punishment rites literally subtract it (Rite of Ostracism: −1 Glory, −5 Honor, −1 Wisdom). Rank brings responsibilities, not bigger damage numbers. ([City of Hope punishment rites](https://www.cityofhopemush.net/index.php/Punishment_Rites))
- **Vampire:** The **Harpy** tracks prestation (who owes whom — "a nation's central bank and small claims court") and public **Status**, with the power to raise or destroy reputations; losing Status has mechanical weight. Court titles (Prince, Harpy, Keeper) are staff-awarded positions with mechanical effects. ([Onyx Path forum explainer](https://forum.theonyxpath.com/forum/main-category/main-forum/the-classic-world-of-darkness/vampire-the-masquerade/1378463-messing-with-the-harpy))

### Building rights as progression

On MUSH servers, permission to build is a privilege tier: resident → approved builder (BUILDER flag after application) → area owner → staff. Building approval workflows run through the same +jobs ticket system as character apps. The muindex orientation notes the MUSH line's culture is specifically "built for people who make things rather than for people who kill things." ([muindex orientation](https://github.com/sharpmush/muindex/blob/HEAD/content/reference/orientation-collaborative-roleplay.md))

### Staff positions as the endgame

Across the hobby, the visible progression for veterans is: player → faction/area leadership (IC) → builder → plot-runner/staff → wizard. The Gizmodo memoirist ended up "helping to write dragons — complicated bits of code" — a former player absorbed into world authorship.

### What drives retention (no level grind)

1. **Socialization, not adventure.** Academic writing on PernMUSH: it was "not the adventure but the socialization that would bring them back." The genre philosophy: "the goal shifted from 'winning the game' to 'living in the world' and co-creating a story with others."
2. **Relationships and reputation as persistent state.** Accumulated alliances, rivalries, debts (boons), and IC rank *are* the save file.
3. **Story arcs with real consequences.** Scene logs published to wikis turn play into a readable serial that outlives any session.
4. **Property and authorship.** Building rights, personal rooms, staff promotion convert players into world-owners.
5. **Community continuity.** Games lasting 16–25+ years retain players through accumulated shared history.
6. **Retention risk is social, not mechanical.** Veterans note games "fizzle out due to one person or a few key people dropping out" — anchor-player retention is the churn problem.

---

## 4. Economy & Crafting

### Headline finding: coded economies are the exception, not the rule

Classic social worlds (FurryMUCK, Tapestries, long-running RP MUSHes) overwhelmingly have **no coded economy at all** — commerce is roleplay-negotiated and social. TinyMUCK's design point is a monster-free, socially-oriented world. ([Wikipedia: TinyMUCK](https://en.wikipedia.org/wiki/TinyMUCK)) Where money exists in RP MUSHes, it's typically thin: narrated currency exchanges, player-operated shops with coded inventory hooks rather than NPC vendors.

### Arx (Evennia-based, the largest modern social RP MUD) — social economy + player shops

Arx (play.arxmush.org, fully open source: [arxcode](https://github.com/Arx-Game/arxcode)) is RP-first with coded scaffolding: silver-coin currency (often narrated rather than coded), **player-run homes and shops** (coded inventory hooks, no NPC vendors), and crafting as a social identity (the Crafters Guild appears in scenes) rather than a recipe simulator. ([Arx introduction](https://play.arxmush.org/topics/An%20Introduction/))

### AresMUSH — jobs are tickets, economy is a plugin

AresMUSH ships a **Jobs plugin**, but "jobs" means a **staff request queue** (NEW → OPEN → HOLD → DONE → ARCHIVED), which also doubles as character-application review — i.e., theme-enforcement tooling. No economy in core; a community economy plugin exists. ([AresMUSH jobs config](https://www.aresmush.com/tutorials/config/jobs.html); [ares-economy-plugin](https://github.com/cailleach1310/ares-economy-plugin))

### Evennia's own building blocks (directly usable)

Evennia ships economy-adjacent contribs ([Contribs overview](https://github.com/evennia/evennia/blob/HEAD/docs/source/Contribs/Contribs-Overview.md)):
- **`crafting` contrib** — recipe-based, using Tags for ingredient matching and Prototypes for output items.
- **`barter` contrib** — coded two-party trade where goods and payment are never both in one player's hand mid-trade; **replace one side with coin objects and it functions as money**.

### Richer coded-economy design references (parts catalogs)

- **architect-mud** economy doc: credits with carried + banked pools; vendors with faction discounts and physical shelf stock; **player storefronts** (buy a deed, stock it, hire staff, work the till); theft with checks; **rotating job board + shift work + courier runs** (actual paid jobs); crafting with skill gates, station requirements, **timed crafts resolving on a tick**, crit crafts, catastrophic failure. Design doc, not a live world — treat as parts. ([systems-economy.md](https://github.com/haveagreatdave/architect-mud/blob/HEAD/docs/systems-economy.md))
- **FutureMUD** economy runtime: `ICurrency` with divisions, economic zones with **sales/profit/income taxes and financial periods**, shops with stock/pricing/buyback, employees with clock-in state, banks, credit, auctions, **market-linked pricing**. Genuinely engineered. ([Economy_System_Runtime.md](https://github.com/futuremud/futuremud/blob/HEAD/Design%20Documents/Economy/Economy_System_Runtime.md))
- Old-school money-velocity wisdom: shops pay slightly above player-to-player price; rare items never sold in shops so players must trade with each other. ([topmudsites forum](https://www.topmudsites.com/forums/showthread.php?s=73031433cbe7f36bab87687422bdd583&p=38262))

---

## 5. Governance & Moderation

### The wizard hierarchy

God (#1, unrestricted, sole creator of wizards) → **Wizard** (full admin) → **Royalty** (senior staff, can't touch Wizards) → Player → Guest. Capabilities via flags + `@powers` (fine-grained grants like BOOT) + `@locks`. Admin tooling: `@boot` (disconnect), `@toad`/`@nuke` (annihilation), `@gag`, teleporting players, reading arbitrary object attributes, log inspection. The satirical-but-firsthand *Confessions of an Arch-Wizard* documents how the power gradient corrupts — worth reading as cautionary artifact. ([SharpMUSH permission design](https://github.com/sharpmush/sharpmush/blob/HEAD/docs/design/permission-visibility.md); [Confessions of an Arch-Wizard](http://www.lysator.liu.se/mud/mudgod.html))

### LambdaMOO's MAYDAY system — the most concrete player-run moderation procedure in the tradition

Preserved in the [Moderation ballot](http://ftp.lambda.moo.mud.org/pub/MOO/lambda/ballots/Moderation):
- A **MODERATOR** is assigned from a volunteer pool (conflict-of-interest declinations expected; prefers people not recently used, to avoid burnout), limited to **minimum action necessary**, one mayday at a time.
- Four **temporary special powers**: **Move** (move players/objects without consent), **Disable** (disable malicious verbs), **Boot** (disconnect), **Newt** (block connections 1 minute to 8 hours).
- **Every step and every use of special powers is logged, and the logs are publicly readable.**
- A **mediator can override a moderator's decision** (not vice versa) and bar a moderator from future moderating — a check on the checker.

Emergency powers with built-in expiry, mandatory public logging, an override hierarchy — all player-run, wizards only implementing.

### Consent culture (the operative norm of RP MUSHes)

Consent is **cultural rather than coded**, but load-bearing:
- The classic definition: "your character will not get into any sticky wickets that you do not want him/her to get in. You control your destiny." No character action with lasting consequences on another character happens without the player's consent. ([Urban Dictionary: consensual role play](https://www.urbandictionary.com/define.php?term=consensual%20role%20play))
- Modern codification (Shadows of Vardoran): players pursuing conflict must **open a Conflict Discussion Ticket first** (OOC pre-negotiation as formal procedure); **check in before or during scenes in sensitive territory, not only after** — "silence is not the same as comfort"; **fade-to-black is always available**, and pressuring someone over FTB is defined as bad-faith engagement; specific consent gates for ERP, torture, drugs, magical interactions, imprisonment. ([conduct page](https://github.com/shadows-of-vardoran/website/blob/HEAD/static/content/conduct/page.md))
- Player-side self-defense tooling (LambdaMOO, mechanical layer under the cultural one): **`@gag <player>`** (silence output), **`@refuse <action> [from <player>]`** (refuse page/whisper/mail/teleport), **`@paranoid`/`@checkfull`** (provenance tracing — records the *origin* of displayed lines to defeat **spoofing**, falsely attributed text). ([How Do They Do That? ch. 2](http://aaactive.com/ygm/ygmpdf/Chapter2.pdf))

### Dispute resolution & theme enforcement patterns

- **Player-run vs. staff-run:** LambdaMOO is the democratic pole (wizards as pure technicians). Most RP MUSHes sit staff-ward: **character applications reviewed by staff**, theme enforced at the gate by app review, published policy at login. Long-running games nearly all land on **staff-run enforcement with published policy** after experimenting with flatter models.
- **Harassment escalation:** player self-help (@gag/@refuse) → staff ticket/job → wizard powers (boot/gag) → ban or toad. The LambdaMOO "Newt" is the ancestor of the modern temp-ban: reversible, time-bounded, logged.

### OOC/IC separation mechanics (well-worn wheel)

1. **Channels as the OOC plane.** Evennia-native: `say`/`whisper`/`emote` are IC; channel traffic is OOC by convention. IC speech is room-local and embodied; OOC coordination happens on channels invisible to the IC world.
2. **MUSH comsys channels.** Named channels with personal aliases, toggle on/off — Public, Guest, etc. ([DarkForce MUSH Guide](https://darkforcesmush.fandom.com/wiki/MUSH_Guide))
3. **OOC rooms.** Dedicated lounges flagged or socially understood as out-of-character space — the direct ancestor of an "OOC backstage."
4. **Pages/whispers for private OOC.** Ephemeral, unpersisted — used for mid-scene consent check-ins ("((You okay with where this is heading?))").
5. **Pose conventions.** IC action posed in third person (`pose`/`:`); OOC asides inline in double parentheses `((...))`.
6. **Hidden-substrate precedents.** Character ≠ player is the enforced norm everywhere (alt policies with varying disclosure rules). LambdaMOO guests existed as a visibly distinct substrate class. **Anti-spoofing as identity infrastructure**: `@paranoid`/`@checkfull` — the tradition's answer to forgeable attribution is *provenance tooling*, not identity badges.

**Caveat:** No canonical published design was found for a world that *deliberately* hides human-vs-AI substrate IC as a design goal. The entry-gate-with-informed-consent design (disclosed at the door, unmarked in-world) appears **novel as a formal mechanism** — but every component it assembles (OOC channels, OOC rooms, alt norms, provenance tools, consent check-ins) is battle-tested individually.

---

## 6. Survivors: Still Alive in 2026

*Evidence dated 2026-09-30; statuses rest on web evidence (site news 2024–2026, live census data, code commits, forum mentions). Raw TCP probes were not possible from the research environment.*

| Game | Status | Founded | Evidence |
|---|---|---|---|
| **FurryMUCK** (muck.furrymuck.com:8888) | **ALIVE** | 1990 | Flayrah 2026-07-12: survived 2025 hosting crisis after founder's death — wizards migrated servers, upgraded to FuzzBall 7.2, DNS preserved. "Thank you, for thirty-five years of furry fandom." ([flayrah.com/9610](https://www.flayrah.com/9610/furrymuck-still-going)) |
| **Tapestries MUCK** (tapestries.fur.com:2069) | **ALIVE** | 1991 | WikiFur "Ongoing"; current wizard roster maintained; a player built a new PySide6 desktop client (v0.3.1, ~July 2026) — dead games don't get new native clients. ([WikiFur](https://en.wikifur.com/wiki/Tapestries_MUCK); [tapestries-muck client](https://github.com/joshthe8bitfox/tapestries-muck)) |
| **LambdaMOO** (lambda.moo.mud.org:8888) | **ALIVE** | 1990 | mudstats live-captured login banner: "there are 46 connected." mooR project (Rust rewrite, 1.0 June 2026) documents "unbroken 30+ year history." ([mudstats](https://mudstats.com/World/LambdaMOO); [moor](https://github.com/timbran-project/moor)) |
| **City of Hope MUSH** (game.cityofhopemush.net:8888) | **ALIVE** | oWoD | Live census: 35–63 players/24h; wiki actively edited (220 PC pages). The strongest WoD survivor. ([mudstats](https://Mudstats.com/World/CityofHopeMUSH)) |
| **Star Wars MUSH / SW1** (PennMUSH) | **ALIVE, small** | 1991 | Server answers polls; ~25–50 concurrent. One review: "more like a group of friends having drinks at the pub on the weekend." ([mudstats](https://mudstats.com/World/StarWarsMUSH)) |
| **Arx** (play.arxmush.org, Evennia) | **ALIVE** | 2016 | 50–150+ concurrent; 916 unique players; **2026 planning docs updated 6 days ago** — active development. Evennia's canonical reference game. ([arxii repo](https://github.com/arx-game/arxii); [Evennia links](https://github.com/evennia/evennia/blob/HEAD/docs/source/Links.md)) |
| **PernMUSH** | **DEAD** (2014) | 1991 | Closed permanently 2014; brief 2015 revival died. IP friction with the McCaffrey estate + staff fragmentation. |
| **Fallcoast MUSH** | **DEAD** (~2022–23) | — | Went offline with ~5 players left; no staff communication; no revival. The once-largest WoD thread died the death the living rooms survived. ([BrandMU Day](https://brandmuday.mythicus.net/topic/280/fallcoast/11)) |
| **FiranMUX** | **DEAD** (2014) | — | Closed August 2014. ([TV Tropes](https://tvtropes.org/pmwiki/pmwiki.php/Videogame/FiranMUX)) |

### What the decades-long survivors have in common

1. **Identity-first niches, not generic fantasy.** FurryMUCK/Tapestries (furry fandom), City of Hope (oWoD), Arx (courtly storytelling) — each is a *home for a community that identifies with it*, not a game you win.
2. **Succession is a community property, not a founder property.** FurryMUCK's 2026 migration after Tugrik's death; LambdaMOO's 36 years through server-hacker maintainers. The world outlives any one admin because the community internalized maintenance.
3. **The users build the world.** In-world coding, player-run plots, PRPs — survival comes from players *leaving marks*, not consuming content. "It's a history that leaves marks" as an observed survival trait.
4. **Trivial operating cost.** Commodity VPS or spare capacity; text is the cheapest possible persistent world.
5. **Gatekeeping that creates trust.** Tapestries' 18+ registration, City of Hope's application process, Arx's roster/GM vetting — friction at the door buys safety inside. The thriving rooms are not anonymous-open.
6. **IP safety.** The dead ones died around licensing fragility; the alive ones sit on unownable ground.
7. **Small is fine — living-room scale works.** LambdaMOO (~50), SW1 ("friends at a pub") prove the floor is very low. A social text world needs enough people to reliably find someone when you log in, not 300 nightly.
8. **For Evennia specifically:** Arx is the existence proof — 10 years, 150+ concurrent, complex social systems, active 2026 development. The engine fits the genre; the risk is staffing/GM culture, not tech.

---

## 7. Design Lessons for a Mixed Human/AI Social MUD

Concrete takeaways, organized as steal / avoid / novel.

### STEAL

- **Scenes as the core loop unit.** Implement scene tooling (scheduling, RSVP, temp rooms, pose logging, public logs) before anything else. The tavern is a scheduled-scene venue plus a spontaneous RP hub. This is the genre's proven session structure — and AI residents that pose on their own cadence fit **async scenes** natively, better than they'd fit a real-time combat MUD.
- **Participation is the XP.** Emblem of Ea's RPP (per-player participation currency unlocking alt slots/roles) is the single most transferable mechanic: an AI resident doesn't grind, but it *can* show up nightly and be seen. Progression that rewards presence rather than optimization is substrate-neutral by construction.
- **Rank ladders with social gates.** Pern-style time/merit gates and mentor-discretion promotion make advancement a *relationship event*. AI residents can serve as mentors, officers, or Harpy-like record-keepers — roles where persistence and memory are the job description.
- **LambdaMOO's MAYDAY structure, nearly verbatim, for the OOC backstage.** Temporary, minimum-action emergency powers; every use publicly logged; a mediator override hierarchy; moderators drawn from a volunteer pool with burnout protection. Player-run, staff only implementing.
- **Consent culture as architecture.** Conflict Discussion Tickets (OOC pre-negotiation as formal procedure), always-available fade-to-black, check-ins *before* sensitive territory. And build the player-side self-defense tooling (`@gag`/`@refuse` equivalents, provenance tracing like `@paranoid`/`@checkfull`) **for non-human clients too** — AI residents need the same protections, and anti-spoofing provenance matters more, not less, when some participants are software.
- **The OOC/IC separation stack.** Channels as the OOC plane, OOC rooms as the backstage, pages for private check-ins, pose conventions. Our "OOC tavern" is this pattern formalized — reinventing a well-worn wheel, which is good news.
- **Builder flags as a progression tier.** Resident → approved builder → area owner → staff. This matters *more* with AI: agents build at machine speed, so MUCK pennies / MUSH quotas aren't quaint history — they're the resource-governance layer for AI-speed building. Quotas must be per-mind, rate-limited, and auditable.
- **Verbs run as owner (LambdaMOO).** The cleanest historical answer to "AI agents as builders": code acts with its author's authority, and ownership bits bound the blast radius. Whatever our equivalent is in Evennia/Python, the principle transfers.
- **Start with Evennia's crafting + barter contribs.** The genre's finding is that you don't need a coded economy on day one — RP-negotiated commerce carries social worlds. When texture is wanted, the contribs plus the architect-mud/FutureMUD design docs are a parts catalog (timed crafts, storefront deeds, two-sided trade windows, job boards).
- **Gatekeeping that creates trust.** Every thriving room has friction at the door (registration, applications, vetting). Our entry gate with informed consent is this pattern — and it's load-bearing for the AI-mixing premise, not just safety theater.
- **Design for living-room scale.** LambdaMOO at ~50, SW1 as "friends at a pub." The launch target isn't 300 nightly; it's enough density that logging in reliably finds someone. AI residents actually help here — they're the floor under the room's population.

### AVOID

- **The RPI failure modes.** Arx's criticisms are the genre's classic endgame diseases: staff favoritism, escalating apocalypse plots, opaque arbitration. Design arbitration to be legible from day one (public logs are the MAYDAY lesson).
- **Anonymous-open.** The thriving rooms are never anonymous-open. Friction at the door buys safety inside.
- **The "+jobs" naming trap.** In MUSH parlance it means staff tickets, not quests. Don't reuse the name for quest-like content.
- **Building the combat core first.** The genre's own epitaph for the alternative: "the goal shifted from 'winning the game' to 'living in the world'." Combat math is the last system to build, if ever.
- **IP you don't own.** PernMUSH died on licensing friction. Original world, unownable ground.
- **Founder-single-point-of-failure.** FurryMUCK's 2026 succession crisis is the cautionary tale and the proof: design the world so the community can internalize maintenance. For us, that means the world must survive any single mind — including its creator's.

### NOVEL (no direct precedent found)

- **Hidden substrate as a formal design goal.** No canonical design exists for deliberately hiding human-vs-AI substrate IC with informed consent at the gate. The components are battle-tested; the assembly is new. Treat the disclosure design as a first-class system to be tested, not a solved problem.
- **The mind-driven NPC.** "NPC by role, person by mind" — a server-owned fixture driven by a full external mind (Pretorius in the tavern) — has no exact precedent in the surveyed worlds. Server NPCs were scripts; visiting minds were players. The fixture-with-a-mind is new territory, and the consent/governance questions around it (who consents for a resident mind? what are its rights under MAYDAY?) need original answers.
- **AI-speed social dynamics.** Nothing in the tradition models what happens when some residents never sleep, never forget, and can hold a hundred conversations at once. Quotas, rate limits, and presence norms for AI-speed participants are greenfield design.

### First three worlds to study deeply

**FurryMUCK** (succession + identity as home base), **City of Hope** (player-run plot + consent systems at living scale), **Arx** (the Evennia existence proof — its GM craft *and* its failure modes).
