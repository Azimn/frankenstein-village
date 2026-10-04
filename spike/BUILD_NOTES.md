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

## Quirks hit (Evennia 6.1.0)

1. **Non-TTY superuser infinite loop.** With no superuser and no TTY, the
   `evennia` launcher prints "Create a superuser below ... skipped" and
   *recurses* (`create_superuser()` → `check_database()` → ...) until
   `RecursionError` (it surfaces inside Django's query compiler, which is
   misleading). Fix: set `EVENNIA_SUPERUSER_USERNAME` /
   `EVENNIA_SUPERUSER_PASSWORD` env vars before any `evennia` command.
2. **`twistd` not on PATH.** `evennia start` fails with
   `Portal process error: [Errno 2] No such file or directory: 'twistd'`.
   Fix: put `venv/bin` on PATH.
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
