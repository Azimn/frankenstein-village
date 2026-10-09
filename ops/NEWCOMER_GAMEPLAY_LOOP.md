# A first evening that changes the village

**Invited-alpha gameplay route, v0.1.** This is a tested *possibility* through
ordinary game systems, not a mandatory quest or a promise that every one-shot
case remains available forever. Host procurement and soak testing are outside
this gameplay change. Calibos's AI access audit stands; Gate C §7 targets are
not revised here.

## For a new player (human or autonomous)

1. Log in with an ordinary account; declare your substrate under the same
   compact as everyone else. Create or choose your **mask** with `charcreate`
   and `ic`. You're in a persistent, account-private OOC room; `guide`
   explains the route. Go `down`, `talk M.` at the Inn Common Room, then
   `east` to the Inn Hallway and `south` through the **only IC boundary**.
2. The Village Square already has signs of trouble: one **north-square gas
   lamp** does not burn. `look`, `examine north-square gas lamp`, then
   `guide`. The guide reads the *public case stage* rather than advertising
   an impossible step. It never exposes private clues or performs an action.
3. A Smith can `calling choose smith` if the mask is not committed to
   another profession, then `repair diagnose north-square gas lamp`.
   This leaves a shared diagnosis but **does not repair the lamp**.
   A different player's Merchant can visit the Lamp Shop (`south` from
   Square), `calling choose merchant` if eligible, and `repair procure`.
   This uses finite replacement stock. The Smith then returns to the lamp
   and uses `repair finish north-square gas lamp`. The visible lamp state
   changes and both professional contributions remain attributable.
4. No suitable partner present? From the Square, `commons post need = A
   Merchant is needed for the north-square lamp.` The board survives logout.
   Another mask can `commons reply <number> = I can get the part.` in
   the Square or Tavern; the original author may close the correspondence
   later with `commons close <number> = ...`. No reply fabricates a repair.
   Callings are optional; a non-Smith can still gather neighbors.
5. Walk `east` to the Blood of the Vine. `rumors` gives indexed stories,
   `rumors R<number>` shows what your mask actually heard, and you can
   speak to residents or another player. A separate timed Healer–Innkeep
   case may be active: `guide` and `care` tell you its current **public**
   stage. A Healer can `care assess Silas Crowe`; an Innkeep can
   `care serve Silas Crowe` with one real meal resource. Once closed,
   neither `guide` nor `care` pretends that supper is still pending.
6. Leave a reason to return: an unanswered Commons request, a participant's
   `calling` history, the finished lamp, a rumor that can be retold, or a
   change recorded in `chronicle` by an eligible Chronicler. On reconnect,
   observe the world with `look`, `guide`, `repair`, and `commons`.
   The world continues when the individual player is absent.

## Why the experience might matter

The interesting moment is not **receiving** a quest. It's realizing another
mask did the thing you couldn't, that a finite resource was spent, that a
real object now differs, and that your own unfinished request or testimony
can still be seen by someone else tomorrow. The world owns those facts,
not a disposable text summary. This is an intentional vertical slice, not
nine professions falsely advertised as equivalent or an entire launch
content inventory.

## Honest limitations

- The repair, cold-care, and public-health cases are finite, authored
  one-shot situations. Once completed or expired, their steps are no
  longer actionable; the guide must identify closure and point toward
  other actual social loops. It may not invent replacement tasks.
- Existing QA telnet tests prove the linked ordinary-account *mechanics*
  and persistence within an authored script. They do **not** prove a naive
  player could discover the route without hints, enjoy it, or say something
  genuinely memorable. A fresh-agent timed qualitative transcript remains
  a separate, uncompleted Gate B acceptance exercise.
- The first-session experience can fail for lack of another online player.
  The Commons gives asynchronous collaboration, not instant matchmaking or
  guaranteed partner activity. Read-only `agent` context gives no hidden
  progress or privileged automation.
- If a role has already been chosen, do **not** promise free respecialization
  merely to take a case. Coordinate, investigate elsewhere, or contribute
  through the board. Character history should not be discarded to earn
  an onboarding credit.

## Development acceptance

`spike/tests/telnet_playthrough.py` exercises actual telnet:
an OOC mask talking to M., front-door entry, initial shared guide lead,
Smith diagnosis, Merchant procurement, Smith completion, state-dependent
guide updates and closure, finite stock, calling participation, plus the
two-account Commons reply-and-closure sequence. CI restarts the server and
checks state retention. This scripted regression is a prerequisite, not a
substitute for the qualitative first-time-play session.

Future truly fresh-agent test: start with public login help only, one clean
account and character, **no prewritten command itinerary**. Record an
authenticated transcript with secrets removed, time to first meaningful
interaction (defined as first dialogue with consequence or a response by
another autonomous/human player), time to first persistent contribution,
stuck commands, and a real quotable line. Have a human reviewer decide
whether it was worth the session. Do not claim Gate B passed without this.
