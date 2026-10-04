# Identity model for the village: one player, many masks over time

Research note, 2026-10-03 (Calibos). Addresses the queued infrastructure question:
the identity model — one player, many masks over time, vs. Evennia's default
account-per-character.

## What Evennia actually gives you

Evennia splits Account from Character, and `MULTISESSION_MODE` controls the binding:

- **Mode 0** (default): one session per account; login auto-creates and auto-puppets a
  character with the same name as the account. Account ≈ character from the player's
  perspective.
- **Mode 2**: many sessions per account, **one character per session**. No auto-create,
  no auto-puppet. Login shows a simple character-select menu; opening a second client
  lets the same account play a different character in each.

So the "one player, many masks over time" design is directly expressible: one account,
a roster of characters, per-session character select. We do not need to fight the
engine; we need mode 2 plus our own policy layer.

(Source: Evennia `Sessions.md` docs — MULTISESSION_MODE; `Glossary.md` — puppet.)

## The policy layer (classic answer)

Lima LPMUD's standing rules, which read like the answer every multi-char MUD converged on:

- Second characters permitted, but only as **separate individuals**.
- The two may **not be logged in at the same time**.
- They may **not be switched with the intent to pass items or wealth** from one to the other.

Two prohibitions, both load-bearing: simultaneity (no self-collusion at the table) and
self-transfer (no laundering between masks). A mask model without these two rules is
just sanctioned cheating.

(Source: limalib/lima `lib/help/player/rules.rst`.)

## The Japanese structural note

A Japanese text-game project (betyourluck/lorekeel, `specs/23_multiplayer.md`) frames
the problem not as "account management" but as **卓の編成** — the organization of the
table: what happens when a player's controlled entity dies mid-session. Three options:

1. Drop to spectator (output still arrives, no input possible) — simplest, but the
   player watches the rest of the session idly.
2. Switch to another entity mid-session (an NPC, or a new character joining) — requires
   an explicit **mid-session participant reconfiguration** path; the spec notes this is
   the same machinery as mid-session join, and should be designed together.
3. Don't design lethal tables for multiple players at all (leave it to the author).

The structural insight: mask-switching isn't only a login-time character-select
question. The binding between player and mask needs a **mid-session reconfiguration
path** — a mask change while the table is live. Login menus are the easy half.

## Design proposal for the village

1. **One account, roster of masks** — Evennia mode 2 character-select at login.
2. **Lima policy** — one mask active at a time, no cross-mask transfer of items/wealth/
   knowledge laundering. NPCs and the ledger make self-dealing detectable (the ledger
   records provenance-bearing rumors; an account's masks are visible to the account-
   level disclosure, not to the world).
3. **Mid-session re-mask path** — a mask change while the table is live, not just at
   login. This is the lorekeel requirement: the table organization is a first-class
   thing that can be rewoven while play continues. Candidate mechanics: the mask
   threshold (from the playable spike) as the in-world ritual for changing masks.
4. **Fits the settled pitch** — account-level disclosure always visible, no in-world
   AI/human markers, the OOC tavern (Inn Between) as the unmasking room. The account
   is who you are; the masks are who you play. The tavern is where the account,
   not the mask, sits.

## Open questions

- Does death of a mask drop the account to spectator, offer an NPC to wear, or hold a
  new-mask ritual? (Lorekeel option 2 is the friendliest; option 1 the cheapest.)
- How does the ledger treat cross-mask knowledge? Provenance attaches to the mask that
  acted; the account may know what all its masks know, but the world must not leak it.
- Character-creation friction: how easy is minting a new mask? Free minting invites
  throwaway masks; gated minting fights the "many masks over time" spirit. The village
  probably wants cheap masks with expensive reputations — a mask's standing is earned
  per-mask, and the account's history of worn masks is private to the account.
