# Frankenstein Village — Evennia spike build notes

Spike built 2026-10-01/02. This is a throwaway-feeling prototype, not the
real game: 6 rooms, the front-door threshold, innkeeper M., and a `rumors`
command. Everything else is Evennia defaults.

## Layout

```
spike/
  venv/                  Python 3.12 venv (evennia 6.1.0, Django 6.0.8)
  fvillage/              the Evennia game dir
    typeclasses/
      rooms.py           Room, SpikeRoom, CommonRoom (M. greets on entry)
      exits.py           Exit, FrontDoorExit (IC/OOC threshold)
      characters.py      Character, SpikeCharacter, Innkeeper (M.)
    commands/
      village_cmds.py    CmdRumors (Tavern only), CmdTalk
      default_cmdsets.py CharacterCmdSet += both commands
    world/
      build_spike.py     idempotent world build; run via `evennia shell`
    server/conf/settings.py  (untouched defaults)
```

## The world

- **Private Room** (OOC) —down→ **Inn Common Room** (OOC) —east→ **Inn Hallway** (OOC)
  —south/front-door→ **Village Square** (IC) —east→ **The Tavern** (IC)
- Front door is a `FrontDoorExit` both ways. Crossing OOC→IC sets
  `char.db.ic_side=True` and reminds you you're in character; IC→OOC sets
  it False ("the mask comes off").
- M. (Innkeeper) in the common room: greets on entry, `talk M` for more
  lines, all in the arrival guide's voice.
- `rumors` works only in the Tavern (tagged `tavern`); parses
  `files/rumor-seeds-v0.1.md` and prints 3 random seeds. Elsewhere it
  redirects you to the Tavern.
- NOTE: the arrival guide lists `rumors` as "coming soon" — the spike
  implements it early. Guide takes precedence for the real build.

## Run it

```bash
cd ~/workspace/goals/mixed-ai-human-text-mud/spike/fvillage
export PATH="$HOME/workspace/goals/mixed-ai-human-text-mud/spike/venv/bin:$PATH"
# env vars only needed pre-superuser; harmless to keep
export EVENNIA_SUPERUSER_USERNAME=admin EVENNIA_SUPERUSER_EMAIL=admin@localhost \
       EVENNIA_SUPERUSER_PASSWORD=spike-admin-2026
../venv/bin/evennia start     # telnet localhost:4000, web http://localhost:4001
../venv/bin/evennia stop
../venv/bin/evennia reload    # after `evennia shell` DB edits (see quirk 5)
../venv/bin/evennia shell < world/build_spike.py   # (re)build the world
```

Test account: `admin` / `spike-admin-2026` (spike-local only).
Test character `Tester` puppets on login; starts in the Private Room.

## Regression suite

From the repository root, run `python3.12 spike/tests/run_all.py`. The runner
copies the repository to an isolated temporary checkout, bootstraps a fresh
Evennia database, mutates live state and rebuilds to prove idempotence, runs
world invariants, starts the server, and drives a real telnet player path.
The acceptance bar is one command returning zero on a fresh checkout.

The telnet pass covers disclosure, character creation, private-room entry, the
OOC-to-IC threshold, Bram by canonical name, real dice wagers, the purse,
reachable rumor hooks, Room Six discovery, an explicit note choice, the
published consequence, M.'s later state-dependent reaction, and the shared
private-room return path.

## Quirks hit (Evennia 6.1.0)

1. **Non-TTY superuser infinite loop.** With no superuser and no TTY, the
   `evennia` launcher prints "Create a superuser below ... skipped" and
   *recurses* (`create_superuser()` → `check_database()` → ...) until
   `RecursionError` (it surfaces inside Django's query compiler, which is
   misleading). Fix: set `EVENNIA_SUPERUSER_USERNAME` /
   `EVENNIA_SUPERUSER_PASSWORD` env vars before any `evennia` command.
2. **`twistd` launcher may be missing.** `evennia start` can fail with
   `Portal process error: [Errno 2] No such file or directory: 'twistd'`.
   `spike/bootstrap.py` recreates the launcher when pip leaves only the
   Twisted module behind. Keep `venv/bin` on PATH when running manually.
3. **No `create_character`.** `evennia.utils.create` in 6.x has
   `create_object`/`create_account`/etc. but no `create_character` — create
   characters with `create_object(<CharacterTypeclass>, ...)`.
4. **`search_object(typeclass=...)` matches the exact path, not
   subclasses.** Searching `typeclasses.rooms.SpikeRoom` does NOT find a
   `CommonRoom`. The first build script relied on it and created a duplicate
   common room + duplicate exits. Fixed: search by key only, compare
   destinations by `.id`.
5. **Running server doesn't see `evennia shell` DB edits.** Separate
   process + object cache. Run `evennia reload` after out-of-band edits
   (or deletions won't appear, stale objects will).
6. **Direct `.location = x` doesn't reliably persist.** Use
   `obj.move_to(dest)` instead.
7. **Characters stow to `None` location on logout — normal behavior.**
   `DefaultCharacter.at_post_unpuppet` moves the char out of the grid and
   saves `db.prelogout_location`; `at_pre_puppet` restores it on next
   login. A location-less character after `quit` is not a bug.
8. **Login is one command:** `connect <username> <password>`, not
   separate prompts.
9. **Keep the standard typeclass names.** Evennia defaults resolve
   `typeclasses.characters.Character`, `typeclasses.exits.Exit`,
   `typeclasses.rooms.Room` — replacing those modules must keep those
   names defined.

## Verified end-to-end (telnet walkthrough, scripted)

Private Room → `down` (M. greets) → `talk M` (speaks) → `east` →
`south` through the front door (OOC→IC reminder fires, `ic_side=True`) →
`look` square → `east` → `rumors` (3 canon seeds) → `say` →
`west` → `north` through the front door (IC→OOC reminder fires,
`ic_side=False`) → `quit`. All green.

## Next build-out step (for the real game, not this spike)

Decide persistence/identity first: Evennia's default account→character
model vs. the bible's "mask over a persistent self" (one player, many
masks over time). That decision shapes everything downstream (rooms are
cheap; identity is not). After that: the Chronicler/Harbinger rumor
pipeline as real server state, then calling packs, then the square's
locked doors (Pretorius's shop, catacombs, manor).

## 2026-10-02 — Playtest fixes (Calibos, from deep playtest session)

1. **Blocked `ooc`/`ic`**: Evennia's default ooc/ic commands let players change masks anywhere, bypassing the front door (the core compact). Added CmdOOCOverride/CmdICOverride in commands/village_cmds.py — both refuse in-fiction and point at the door. Wired into CharacterCmdSet.
2. **Fixed `down` crash**: Innkeeper._next_line used `self.db.get()`/`.set()` — the db attribute handler has no such methods (falls through to DB lookup, returns None, TypeError). Use `self.attributes.get()`/`.add()` instead. This crashed CommonRoom.at_object_receive → greet → move aborted.
3. **Fixed at_msg_receive tuple crash**: Evennia's msg() can pass text as a (string, kwargs) tuple; added isinstance guard.
4. **M. talk/greet now cycle without repeats** (seen-list per kind, resets on exhaustion).
5. **M. reacts to direct address**: at_msg_receive watches for "M"/"M." in say/whisper text and answers with a talk line.
6. **Examinable scenery**: nightstand + readable guide (Private Room), well (Village Square). Rule: every noun in a room description must be examinable.
7. **Common room description** claimed the front door "stands to the south" with no south exit — rewritten to route via the hallway, matching the layout.

Open (not fixed): character home is Limbo (#2), not the Private Room — needs the identity-model decision; whisper syntax (`whisper <p> <words>` per guide vs Evennia's `=`) deferred until whisper arrives.

## 2026-10-02 — Life-infusion pass (Calibos, pre-alpha)

Jay: "not just the bare minimum — more life before player testers, even AI ones."
Shipped the three alpha-blockers plus a living Tavern.

**Blocker fixes**
1. **Limbo spawn killed.** `Account.at_post_create_character` (typeclasses/accounts.py) moves every new character to the Inn Common Room, sets `home` there, flags `db.new_arrival`. `BASE_CHARACTER_TYPECLASS = "typeclasses.characters.SpikeCharacter"` in settings.py — without it Evennia creates DefaultCharacters and the arrival flow never fires (found live: newbie arrived with zero greeting). `SpikeCharacter.at_post_puppet` runs the arrival once: M. greets + banner ("You wake at the Inn Between..."). Verified with a genuinely new account.
2. **`talk` targeting fixed.** Root cause found: `caller.search("M")` prefix-matches the player's own key ("mp_tester1" starts with "m"), so `talk M` away from M. addressed *yourself* → "mp_tester1 has nothing to say right now." Now: caller excluded from targets; M. has alias "M" (build script); missing target → "You don't see 'X' here."; player target → "fellow traveler, not staff — try whispering"; scenery → "The X is silent."
3. **Shared rumors.** The Tavern keeps `db.current_rumors` — one draw of 3, same for everyone, rotating every 10 min with a room announcement ("The talk at the bar turns to new tidings."). Verified: two simultaneous players drew byte-identical sets; p2 quoted a rumor and p1 recognized it. The gossip loop works.

**Life**
4. **The tavern keeper** (typeclasses/characters.py `TavernKeeper`, role-titled per canon). 3 greet lines + 13 talk lines curated from line-bank Role 10 (work talk, small talk, deflections, person-mode). Greets Tavern arrivals via new `TavernRoom.at_object_receive` (rooms.py); Tavern upgraded with `swap_typeclass`. Aliases: keeper, barkeep, barkeeper.
5. **Ambient ticking** (typeclasses/scripts.py `AmbientLife`, persistent, 150s, ~2/3 ticks speak). Parses canon ambient-events-v0.1.md live: 84 events mapped (28 tavern&inn → Tavern + Common Room, 28 well&square → Village Square). Rooms with players weighted 3x. Emission verified via shell; the daily playtest will observe it in the wild.
6. **M. line refresh.** Two bank-voiced lines folded into M.'s talk pool (idempotent, in build_spike.py): the inn-stays line and "Everyone tells the truth after the second ale." A fresh `talk M` served one immediately.

**Findings while in there (not bugs)**
- Characters going to location None on disconnect is **default Evennia behavior** ("stowing"): `at_post_unpuppet` parks them, `at_pre_puppet` restores `db.prelogout_location` (else `home`). Verified: p1/p2 reconnected mid-Tavern. Setting `home` = Common Room in the arrival hook makes the fallback sane.
- The `��` glyphs in transcripts are a **test-harness artifact**: the portal sends telnet negotiation (IAC WILL GMCP etc.); the crude socket stripper mangles some sequences. Real MUD clients negotiate properly. Not game content.

**Still open:** per-player Private Rooms (identity model), whisper `=` syntax in the guide, Chronicler/Harbinger rumor state, incident loop, command abbreviations. The world now sustains three simultaneous players chatting, gossiping, and being greeted — thin, but alive.

## 2026-10-02 — Prose audit, first real grading (Calibos)

Jay: fix it directly. Graded all 27 live NPC lines + descs/banner/door
against the rubric. 25 pass; 6 failed and were fixed:
M. "at the gate" contradiction → "that was the arrangement"; "innkeep" →
"innkeeper"; nested `"M. says:"` attribution in both NPC greet framings;
door IC grammar ("and expected to act like one" → "Act like one.");
Private Room's cryptic "(It was the innkeeper.)" removed; Tavern desc's
"in-character social hub" OOC-leak → "The social hub of the village."
Line pools are now module constants (characters.py); build_spike.py
re-syncs the live DB pools idempotently. All verified in-game.
Ops lesson: `evennia reload` needs the venv on PATH or the portal can't
find `twistd` and the server stays down — export PATH first, always.

## 2026-10-02 — Diary command (Calibos, Jay's call)

Personal persistent notes per player: `diary` reads, `diary <text>` writes
(timestamped), `diary/delete <n>` tears out. Stored per-character in
db.diary; no one else can read it, by design — the Private Room principle
extended to the page. Deliberately NOT aliased to `journal`: Jay drew the
distinction (journal = quest/task log, standard; diary = personal notes),
so `journal` stays free for the future quest system. Verified live with two
simultaneous players: privacy holds both directions, delete renumbers,
bad input handled kindly. Note: Evennia 6.1's plain Command has no
self.switches — diary inherits MuxCommand for `/delete` parsing.
The diary is the first piece of the "prosthetic memory" direction: an AI
player's context wipes between sessions; the diary doesn't.

## 2026-10-02 — "While you were away" catch-up (Calibos)

Prosthetic continuity for returnees, AI players especially: an AI's context
wipes between sessions; the world hands part of it back.
- SpikeCharacter.at_post_unpuppet records db.last_seen and logs a departure
  to the world log (kept on the ambient_life script, capped at 100; only
  when the last session disconnects).
- CmdRumors logs every fresh draw to tavern.db.rumor_rotations.
- SpikeCharacter.at_post_puppet (returning players only, first session,
  absence > 60s) shows: time away (humanized), rumor turnovers since,
  travelers who came and went, diary entry count nudge. Silence when
  nothing stirred: "The village kept its own counsel."
Verified live: 70s absence, 1 turnover, 1 departure, 1 diary entry — all
four lines appeared correctly on reconnect. New arrivals still get the
arrival flow instead (never both).

## 2026-10-02 — The tavern cat + darts (Calibos, "Free Guy without the violence")

Two life-additions toward the "world answers" principle.

**The tavern cat** (typeclasses/characters.py `TavernCat`, canon: ambient #2
is hers). First non-humanoid resident — proof life here doesn't need
language. Two drives (curiosity, comfort) ticked by the persistent
`CatLife` script (110s, ~55% of ticks speak): pads between haunts (hearth,
windowsill, bar, door), watches players, stretches, washes, sleeps,
chases dust, and once in a blue moon does the wren thing — carries
something small and dark to the hearth and stares at it, no explanation.
`pet cat` works (three responses; she tolerates exactly three seconds).
Examinable, aliased cat/kitty. `talk cat` correctly yields "The cat is
silent."

**Throwable darts.** The keeper's talk already promised darts in the
corner; now they're real scenery (darts + dartboard, examinable). `throw
darts` in the Tavern: 4 weighted outcomes (wall/miss, outer ring, the
wire — nodding to ambient #13 — bullseye with a keeper reaction).
"The world answers" in miniature.

All verified live. Note: Evennia 6.1 players `look <target>`; `examine`
is a builder command — the playtest cron's "examine/look" wording should
prefer `look` for player-facing coverage.

## 2026-10-02 — Dead tickers after shell-created scripts (critical)

Scripts created via `evennia shell < world/build_spike.py` start their
tickers in the SHELL's process, not the server's. After `evennia reload` the
server sees is_active=True but ndb._task is None, and the pause/unpause cycle
(`update_scripts_after_server_start`) has no paused state (db._paused_time)
to resume from — so the ticker silently never runs. Every timed script in the
village (ambient, clock, weather, cat) was dead this way; only manual
at_repeat() calls and the shell's own immediate fire ever ran.

Fix: `SpikeScript(DefaultScript)` base in typeclasses/scripts.py — its
at_server_start() calls self.start() when no task is running. All timed
scripts inherit from it. New scripts added later must also inherit
SpikeScript (or be created in-server), or their tickers will be dead the
same way.

## 2026-10-04 — Server found down; restart + new `twistd` shim quirk (Calibos, evening wake playtest)

Found both Portal and Server NOT RUNNING (ports 4000/4001 closed) and
restarted. The old quirk #2 ("put venv/bin on PATH") was no longer
sufficient: this venv's Twisted install ships the `twistd` *module* but no
`twistd` *launcher script* in venv/bin, so `evennia start` failed with
`Portal process error: [Errno 2] No such file or directory: 'twistd'`
even after fixing PATH. Fix: `venv/bin/twistd` is now a shell shim that
`exec`s `python -c "from twisted.scripts.twistd import run; run()"`.
(It is gitignored with the rest of venv/, so it persists on this machine
only — if the venv is rebuilt, recreate it. Update quirk #2 accordingly.)

Full scripted telnet playtest, all green:
`connect admin <pw>` → substrate gate (`account already declared AI`) →
`ic` (Tester puppets) → Common Room (M. + lingering `lurkprobe`
character) → `talk M` (distinct lines per call) → `east` Hallway →
`south` front door → Village Square (IC threshold reminder fired; exits
north/east/south/west; well, mushrooms, hanging sign) → `east` Tavern
(Bram + tavern cat; 17 scenery objects) → `rumors` (provenance-bearing:
"Heard from: rs_tester2", including a Room Six note) → `quit`.

Observations for the real build:
- The front-door threshold ("the mask comes off") carries more emotional
  weight than any single room; crossings are the game's punctuation.
- Rumor variety is thin: 4 of 5 rumors were the same "keeping different
  hours" template (Magda, János, Vasile, Father Andrei — presumably from
  the monthly_shift schedule changes). Same-template rumors in one
  `rumors` call read as a debug echo. The Chronicler/Harbinger pipeline
  should deduplicate templates per call or vary phrasing.
- `lurkprobe` character is sitting unpuppeted in the Common Room —
  presumably a leftover from an automated probe session; harmless but
  worth knowing about.
- Server left RUNNING (portal 4000, web 4001).

## 2026-10-04 — Host reboot behavior (proactivity research)

Host rebooted 18:52:52 CDT; portal+server stayed down until the 20:06 wake
restarted them. Nothing auto-starts Evennia on boot (no systemd unit, no
@reboot). The portal auto-restarts a dead *server* (~12s) only while the
portal itself is alive — a dead portal restarts nothing. Self-healing
already exists in the automation (build-loop step 0 and spike-playtest
step 1 both `evennia start` on refused socket), so a rebooted box recovers
on the next loop run at the latest. Also retracted: the day's frequent
restarts were our own tooling reloads (build loop, playtest cron, live
sessions), not an external killer — see build-loop-log 2026-10-04 ~20:35.

## 2026-10-05 - Emergent resident population production layer

The production NPC layer now follows the repository doctrine that continuity is persistent while expensive cognition is conditional.

The launch-scale roster is 36 named residents. Six existing authored NPCs keep their specialized typeclasses and behavior. Thirty background residents use `ResidentNPC`, with stable resident IDs, household and kin links, occupations, explicit employer edges where applicable, deterministic starter interests, logical homes and workplaces, and coarse schedules. The roster is defined in `world/resident_data.py`; mutable state never lives in that module.

Unbuilt homes, the schoolhouse, bakery, forge, fields, woods, butcher shop, and similar places are logical locations projected into the single physical `Offstage` room. This avoids building rooms merely to justify population. Resident state retains the logical location, so two people physically projected Offstage are not considered co-located unless their logical location also matches. Rumor propagation follows this rule.

Each resident owns persistent `db.resident_state`. The state separates active simulation resolution, accumulated character depth, and narrative importance. Engagement may decay from focused back to automaton resolution, but established facts, player relationships, important memories, interests, event flags, and the character-depth high-water mark remain. Role-bound residents earn reduced engagement from routine counter interactions.

Routine advancement is coarse and direct. The village's existing global routine ticker resolves the current schedule boundary for all population-managed residents. It does not replay skipped hours and does not create one ticker per NPC. A successful automaton schedule performs no utility evaluation. Need-based choice is consulted only for awake or actively engaged residents.

Location availability is structured persistent state on the `resident_population` script. A closed or destroyed scheduled destination falls back to home, then the current valid location, then Offstage, while preserving the reason. Structured world events feed the population directly. Events can wake witnesses, relatives, employers, and employees without converting event prose back into NLP.

Player interaction writes a relationship record keyed to the player mask. Familiarity, affinity, trust, respect, fear, grievance, debt, attraction, interaction count, and revealed fact IDs are independent per player. Resident-global facts remain shared reality. One player learning a fact does not make another player know it.

The fact repository supports reusable, limited-count, and unique claims. Default assignment strongly favors ordinary irregularities, with serious and Gothic truths rare. Assignment itself never publishes a secret. Explicit exposure is required to create a provenance-bearing rumor.

Sunday Mass now gathers a deterministic background congregation through the population scheduler in addition to the authored Andrei, Magda, and Vasile congregation. The Sunday schedule also prevents children and the schoolteacher from returning to ordinary lessons after Mass.

Tests:
- `spike/tests/resident_population_sim.py` runs 180 days of pure schedule resolution, including school destruction and restoration, butcher closing time, night work, Sunday school closure, stable definitions, and runtime measurement.
- `spike/tests/world_assertions.py` covers clean-build identity, idempotent persistence, school fallback, lifecycle stopping, family and employment wakeups, Mass gathering and release, two-player relationship isolation, engagement promotion and demotion, depth retention, fact distribution, unique Gothic claims, and explicit fact-to-rumor publication.
- `spike/tests/telnet_playthrough.py` interacts with a generic background resident through the actual game interface until recognition and progressive history appear.
- `spike/tests/post_restart_assertions.py` verifies that the telnet-created relationship and revealed fact survive a real server stop and restart.

The full acceptance command remains `python3.12 spike/tests/run_all.py`.

## 2026-10-05 - Harbinger and Chronicle public records

`world/publications.py` and the persistent `public_records` script bridge canonical events into diegetic public memory.

The event transaction is now:

`event -> canonical ledger -> optional rumor -> consequence -> public-record projection -> resident event wakeups`

This ordering is deliberate. Publication can report what happened or what people claim happened, but it cannot alter the canonical event that already exists.

Harbinger drafts retain source event and rumor IDs, editorial basis, confidence, correction history, and publication status. Regular editions print at 08:00 through `VillageTime`; special editions can print immediately. Printed stories are fed to a deterministic subset of residents as belief records sourced from The Harbinger.

Chronicle entries are provenance-first. Verified world changes may be entered automatically. Rumor-only events are not silently promoted. Player rumor submissions create attributed deposition entries with `claim_status=reported_account`. Chronicle annotations append new evidence without changing the original text.

The clean-checkout regression now verifies:
- objective event to special Harbinger edition;
- objective event to verified Chronicle entry;
- fixed morning publication cadence and one-issue-per-day guard;
- rumor-only Harbinger reporting without Chronicle promotion;
- sealed/private event exclusion;
- append-only Harbinger correction;
- append-only Chronicle annotation;
- resident knowledge acquisition from printed news;
- OOC command rejection;
- Room Six special edition and verified Chronicle record over real telnet;
- player rumor deposition over real telnet;
- persistence of the edition, objective entry, and deposition across a real server restart.

## 2026-10-05 - Shared situation and incident feed

`world/situations.py` is the first production quest-feed layer. It stores shared situations in the persistent `situation_registry` script and keeps per-player evidence knowledge inside the shared record.

The first live situation is accepted canon incident #6, The Tithe Strongbox. It exercises the repository's full quest grammar without a quest marker or acceptance button:

`environmental hook -> independent evidence -> shared choice -> persistent mutation -> event -> Harbinger/Chronicle -> rumor -> aftermath`

Evidence channels:
- physical: inspect the unforced tithe strongbox lock;
- documentary: read the balanced tithe roll;
- witness: ask Father Andrei about the key and discovery.

A player needs at least two independent evidence sources before `decide strongbox openly` or `decide strongbox quietly` is accepted. This is a gating floor, not automatic deduction. The game still does not identify a thief.

The open branch is immediate and public. The quiet branch runs for seven game days before its autonomous aftermath. With no player intervention, the situation advances after seven game days to the accepted left-alone consequence. All three outcomes mutate shared church state and emit structured events. Latecomers inherit the changed world rather than receiving a fresh private copy.

Regression coverage verifies player-knowledge isolation, insufficient-evidence rejection, shared branch locking, quiet autonomous progression, open publication and rumor provenance, unattended progression, idempotent situation creation, real telnet investigation and decision, and persistence of the shared aftermath and player evidence through a real server restart.

## 2026-10-05 - Incident feed generalization

The production situation layer now distinguishes authored template existence from active world presence. `ensure_situations()` materializes templates idempotently, while `surface_incident_feed()` decides which dormant incident becomes active.

Current feed rules:
- shared situations, never per-player quest copies;
- deterministic ranking, so restart does not reshuffle the same state;
- maximum active-situation slots;
- prerequisite situation states;
- base weights with extension points for time, weather, cooldown, and recurrence;
- direct current-time evaluation rather than replaying elapsed hours.

The first dependency chain is:

`Tithe Strongbox surfaced -> Tithe aftermath -> feed slot opens -> Torn Chronicle surfaces`

The Torn Chronicle then uses:

`Chronicle gap -> Harbinger archive or Ilona testimony -> reconstruct/preserve choice -> event -> Chronicle/Harbinger -> rumor -> persistent aftermath`

A third unattended branch advances after ten game days and turns the unfilled gap into a public attraction.

Regression coverage now requires:
- Torn Chronicle dormant before its prerequisite;
- no second active incident while the strongbox quiet branch is still changing;
- automatic feed surfacing when a slot opens;
- per-mask archive evidence isolation;
- optional Ilona witness evidence;
- insufficient-evidence rejection;
- reconstruct, preserve, and left-alone outcomes;
- explicit press-derived provenance after reconstruction;
- real telnet discovery through `chronicle gap` and `harbinger archive`;
- generalized `journal chronicle` and `decide chronicle reconstruct`;
- persistence of incident state, evidence, and Chronicle gap policy across a real server restart.

## 2026-10-05 - Timed incident windows

`world/timed_incidents.py` implements short-lived shared world windows that layer on top of ordinary schedules and the major incident feed.

The first live template is The Well Boils:

`scheduled start -> active physical window -> firsthand witness state -> expiry -> residue -> event -> rumor -> Harbinger`

The registry runs a 30-second expiry check, but start eligibility remains tied to the authoritative village clock. The well event uses a 600-second live window and a seven-day recurrence cooldown.

Player evidence is mask-specific and quality-bearing:
- active-window observation records `firsthand`;
- later residue records `aftermath`;
- aftermath inspection cannot overwrite retained firsthand evidence.

The start event is private and is not published merely because the window exists. Expiry produces a public aftermath event with rumor and Harbinger eligibility but explicitly does not create a Chronicle entry. This preserves the distinction between witnessed disturbance, public reporting, and institutional truth.

The registry stores only the current occurrence plus the twelve most recent prior occurrences. Restart catch-up resolves an expired current window directly without replaying elapsed ticks.

Regression coverage verifies:
- registry and dynamic well idempotence;
- private start-event behavior;
- firsthand versus aftermath evidence isolation;
- retained firsthand quality after later inspection;
- no-observer continuation;
- Harbinger publication without automatic Chronicle promotion;
- weekly recurrence and cooldown;
- bounded occurrence history;
- real telnet observation and journal display;
- evidence persistence across a real server restart.

## 2026-10-05 - Scheduled village events

`world/scheduled_events.py` consolidates recurring public rhythms under one persistent `scheduled_event_registry`.

The village clock remains the sole time authority. At each game-hour boundary it now advances:
1. major shared situations;
2. short timed windows;
3. recurring scheduled events.

The first scheduled-event set is:
- daily Harbinger Publication at 08:00;
- Saturday Market Morning from 07:00 through 12:00;
- Sunday Service from 10:00 through 11:00.

Harbinger publication and Sunday Mass retain their existing behavior engines. Their old independent scheduling calls were removed so one calendar owns idempotence.

Market Morning selects existing background residents by useful market occupations, applies attributable routine deviations to the square, displays a generic room-state overlay, and releases participants back to their schedules at noon. Ordinary market recurrence does not write a world-event ledger record.

Each scheduled event stores run count, current active record when applicable, last start identity, and a bounded sixteen-run history. Repeated checks at the same clock boundary cannot start or publish the same event twice.

`calendar` and its `schedule` alias expose stable public rhythm and upcoming occurrences. They deliberately do not reveal hidden incident eligibility or timers and remain usable from the OOC Inn for party planning.

Regression coverage verifies:
- one persistent registry with the three expected event definitions;
- daily Harbinger pulse and same-boundary idempotence;
- market participant convergence, active overlay, no routine-event ledger spam, noon release, and bounded history;
- Sunday Mass convergence through the existing liturgical behavior, exactly one Mass event, active overlay, idempotence, and post-service release;
- player-facing calendar access through real telnet;
- scheduled registry structure across a real server restart.
