# Village Commons: first persistent player-led civic institution

Date: 2026-10-08

Status: live implementation candidate; all deployment claims still subject to CI and real-host tests.

## Why this exists

The village is a shared social world, not a park whose attractions wait for a
single protagonist. Existing residents and authored institutions already
persist. The civic commons adds a place where player-created needs, offers,
gatherings, and public statements remain after their authors log out.

Two people do not have to be online simultaneously. Neither is granted
ownership of the other's experience. The same verb works for humans and
external AI agents. No player substrate is recorded in the public entries.

## In-world location and verbs

The original board is in Village Square; Bram keeps a copy in the Tavern.
Posting happens at the square. Reading and replying can occur at either place.

Players may post a need, offer, gathering, or notice; answer someone else's
words; inspect the entire signed correspondence of a numbered post; close their
own notice with a closing statement; or read closed history. No central game
manager distributes tasks. There is no XP, automatic fulfillment, or hidden
correct answer. Author closure is attributed testimony, not world truth.

## Continuity and protections

The persistent `village_commons` script stores bounded signed correspondence
with stable numerical IDs. Each author and response includes a mask name,
mask ID, account ID, and village day/hour. Account identity prevents a second
mask from bypassing the personal posting and reply limits. Every notice is
shared across players and survives reload and restart. No hidden private-room
information or account substrate is displayed.

Active notices are never silently removed under archive pressure. Ordinary
players may open up to three notices, with 48 concurrent open notices globally,
16 signed replies per notice, and three replies per account per notice. The
archive retains up to 160 notices, recycling closed/hidden records only when
necessary. Public text is bounded, one line, and free of terminal escape
sequences and Evennia pipes.

Complaints reach the existing human-review moderation queue. A report does
not automatically punish anyone or erase public evidence. Only a staff account
declared human can hide a notice; this leaves an internal moderation record.
Board events enter the world-event ledger with references, not the raw
player-written body. They do not automatically become Chronicle canon.

## What it is not

This is not yet a resource escrow, legal contract, physical stock transfer,
market system, NPC labor marketplace, or proof that a promise was fulfilled.
Do not grant gameplay authority from a player's unverified statement. Future
world mechanics may link a posting to a real delivery, shared worksite, or
scarce resource through world-verified events, but the linkage must be designed
and tested independently.

## Regression requirements

The clean checkout runs the portable civic state regression for distinct
accounts, alternate masks, bounded storage, closure, text sanitation, and
staff hiding. The live telnet playthrough uses independent Smith and Merchant
accounts in separate locations, has one leave a need and the other answer it,
verifies that only its author can close it, then leaves an open offer. The
post-restart assertion proves both the closed history and open offer survive
the actual Evennia server lifecycle.

The existence of this institution does not satisfy the wider multiplayer
soak, public-host transport, moderation service, or disaster recovery gates.
