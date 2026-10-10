# Village Commons — Remembering Unfinished Business

**Gameplay slice:** asynchronous, player-authored civic threads with
mask-specific prospective attention. No mission board, experience, bot-only
commands, fictional rewards or unearned NPC intervention.

## The scene

A traveler sees a signed request for help at the Village Square. They cannot
finish it tonight, so they choose to keep the notice in mind. Another traveler
answers the next day. When the first returns, the world hasn't silently reset:
the reply is there, and the watch says something changed. The original author
can close the correspondence with their own account of the outcome. Closing
the note is **not proof that an asserted job was physically completed**.

The Blood of the Vine holds the public copy. If someone asks Bram about the
Commons, he points toward a **real open public notice** rather than inventing
an assignment. He does not quote unscreened user text, assert that it is true,
or expose hidden/removed notices.

## Ordinary player commands

| Command | Effect |
| --- | --- |
| `commons` or `commons archive` | Read open/closed correspondence |
| `commons <number>` | See signed public text and replies, no auto-acknowledgement |
| `commons follow <number>` | Add one visible public notice to this mask's concerns |
| `commons followed` | Read whether watched notices have new signed replies or a closing account |
| `commons check <number>` | Read and explicitly acknowledge a watched notice's current public version |
| `commons unfollow <number>` | Stop tracking one thread (does not delete its shared history) |
| `commons post need = ...` | Post a real need from the Square (existing limits apply) |
| `commons reply <number> = ...` | Reply publicly at Square or Tavern |
| `commons close <number> = ...` | Author's signed closing account, not objective certification |
| `ask Bram about commons` | In Tavern, a non-omniscient referral to actual public correspondence |

**Illustrative player sequence** (not a transcript from a novel first-time
player):

```text
> commons post need = Would another neighbor keep watch while I fetch lamps?
Commons #1 posted.

> commons follow 1
Commons #1 is now in this mask's keeping.

[Another ordinary mask replies, possibly during a later session.]

> commons followed
Commons #1 [need, open] from ...: 1 new signed reply.

> commons check 1
[The public note and attributed reply appear.]
Commons #1: updates noted by this mask.

[The author later closes the notice.]

> commons followed
Commons #1 [need, closed] from ...: closing account added.
```

### Scope and safety rules

- **Per-mask**: an account's alternate mask does not inherit a watch, even
  though the public board remains readable by everyone. There is no API
  shortcut for AI characters. Each command is a normal in-world command.
- **Bounded**: up to 8 watches per mask, with explicit removal; no automatic
  expiry of unfinished watches, no unbounded event subscriptions.
- **Moderation-aware**: staff-hidden or pruned notices become an indistinct
  "no longer publicly available". A saved follow record has only ID, reply
  cursor and closure cursor, so it cannot expose withdrawn text, moderation
  reasons, or private account identifiers.
- **Explicit reading**: `commons followed` is observational, not mutating.
  Only `commons check` moves the read cursor. Following twice does not erase
  unread progress. Normal board read doesn't mark a watch checked.
- **Public claim ≠ world fact**: replying and closing do not create a
  physical item, pay currency, modify a room, certify testimony, or assign
  professional credit. Real case consequences still require actual systems
  such as the Smith/Merchant lamp and Healer/Innkeep care procedures.
- **Offline-compatible**: in the absence of a second live player, a signed
  post remains pending across reconnects. This is persistent asynchronous
  collaboration, not instant match-making.

### Reproducible acceptance

`spike/tests/commons_follow_sim.py` probes duplicated follows, unread
replies, explicit acknowledgement, closing a thread, JSON roundtrips,
staff hiding, capacity enforcement, no cross-mask inheritance, and no
side effects from status reading.

`spike/tests/telnet_playthrough.py` exercises the same features over
ordinary live telnet player accounts: Smith posts and follows a need;
Merchant sees it in Tavern, hears Bram reference the public board and
replies; Smith receives an unread update, explicitly reads it and later
acknowledges closure; Smith follows Merchant's second open offer. The
post-restart assertions verify both watches and no cross-mask bleed from
the database following an actual Evennia stop/restart.

The separate no-script Muse first-player qualitative session is deliberately
deferred at the user's direction. Nothing here qualifies as such a session,
a hosted multiplayer soak test, or a change to Gate C §7 launch targets.
