# Frankenstein Village: product and release contract

**Authority:** game-first scope for all contributors and coding agents.
**Updated:** 2026-10-20.
**Status:** design and technical contract, not certification of a live server.

## What we are building

Frankenstein Village is a persistent, multiplayer, text-based Victorian Gothic
MUD. It is meant to be fun when played by ordinary people using a browser or
terminal, with no other software on their computers. A good session offers
immediate exploration, characters worth talking to, meaningful craft and
service work, mysteries with uncertain evidence, social cooperation, and
recognizable changes to the village. World time and saved consequences survive
disconnection and server restart. Its ordinary villagers use authored dialogue,
schedules, deterministic and probabilistic rules, and persistent state.

The server uses Python 3.12, Evennia, Django and a configured database. An
internet deployment additionally needs a managed process, durable storage,
DNS, HTTPS/WSS, backup/recovery, moderation, and monitoring.

**Model-free guarantee:** the game shall work with **no local model**, **no
Ollama**, **no Transformers**, **no OpenAI/Anthropic API keys**, **no GPU**, **no
external inference endpoint**, and **no autonomous agent service**. Do not
import a model SDK into startup paths, make NPC turns call a model, make a
model test a release prerequisite, or block a startup or player action on
model availability. These are not missing features. They are deliberate
nondependencies. Pre-written NPC text and simple rule-driven conversation
are valid classic MUD design.

## Players and optional integrations

A human can connect through the built-in Evennia web client or a compatible
text terminal. Account/character creation, OOC disclosure, navigation,
communications, professions, inventory, clues, work, events, and logout are
identical regardless of player substrate. AI-controlled *clients* may connect
as regular accounts with the same constraints. The read-only `agent` and
`agentlogin` commands are convenient optional accessibility envelopes, not
proof that a model is installed or required. A model-led playtest is optional, but the mixed-world contract is not:
normal-client acceptance must demonstrate that human- and AI-declared accounts
share the same permissions, discoverable commands, persistent consequences,
and multiplayer interactions. AI-operated players remain first-class citizens
of the village under the World Bible. The game server never supplies their
language model, and external inference is not a startup or release dependency.

## Player-facing definition of done

First session: an uncoached person can understand the compact, make/select
a mask, go through the Inn Between into the shared village, orient with
`look`, `help`, `guide` and exit names, meet inhabitants, select a
Calling if desired, and find at least three discoverable things to do.

Exploration and social play: connected rooms and described exits are usable;
objects can be inspected, carried or used when appropriate; players can
speak and interact without a separate chatbot; public conversations and
reports respect moderation and OOC/IC boundaries.

Consequential activities: professions offer renewable, distinguishable
actions, legitimate finite supplies, meaningful choices and recorded
physical/social outcomes. People can participate alone when population is
low; multi-player handoffs give advantages without permanent dead ends.
Narratives do not award success without underlying state transitions.

Mysteries and living world: clues are discoverable by actually traveling,
examining, questioning, or making choices. Disputed statements remain
disputed, outcomes persist, residents react only to plausible information,
and time, recurring events and world changes work after a restart.

Return: a character may disconnect during an ordinary session, reconnect
with possessions, work history, journals and relevant public consequences
intact, and discover fresh opportunities. The database can be backed up and
restored without silently losing or duplicating state.

Release safety: run clean-checkout tests and genuine ordinary-client
walkthroughs; test multiple accounts, reboot, abuse reporting, permissions,
economy dupes, transport security and recovery. Full-launch content coverage
is measured against the existing section 7 of the quest handoff, with
implemented and merely authored assets separately labeled.

## Work order, not a request for a language model

Prioritize finishing reachable player experiences, debugging active PRs and
stabilizing the main branch. The implementation order is player onboarding,
connected locations with actual verbs, professions/material economy,
investigations, resident/civic consequences, repeatable world activities,
then multiplayer regression and deployment. Ship no room merely to improve
a count, and do not add parallel agent/NPC architectures while gameplay
is incomplete. A model-based chat service is not on the dependency path.

The feature acceptance reference is
`files/frankenstein-village-quest-handoff-v0.3.md`, especially section 7.
`ops/content_inventory.py` is a conservative *declaration inventory*, not
a playable-completion certificate. The optional early-access scope in
PR #85 is a planning proposal, not a waiver of full-launch content goals.

## Release boundary

A green development CI means only its particular tested checkout passed.
A deployable candidate means the code and gameplay have passed release
acceptance, not that a host exists. A public launch additionally requires
real external login, TLS/WSS, persistent host storage, off-host encrypted
backup and disposable restore, moderation, measured ongoing multi-user
stability, and operator approval. The evidence gate in `ops/launch_gate.py`
checks **ordinary client access and reconnection**, never the existence
or performance of an AI model. Do not invent host evidence.

A no-model normal-user smoke scenario is:
`account -> compact -> mask -> IC entry -> look/guide -> explore ->
perform genuine work or gather evidence -> social response ->
logout -> restart -> reconnect -> verify world and inventory`.
Run it for a non-staff human-style client without agent commands and
prove every step on a fresh server. A separate AI client trial is optional.

## Preserve future ideas without allowing scope drift

Pretorius's portable laboratory, independent agent cognition, locally
hosted LLM residents, model verbalizers, and cross-project memory systems
are other research efforts or future optional integrations, **not**
Frankenstein Village launch blockers. Keep related notes explicitly marked
deferred and never promote their setup steps into base installation,
standard regression, or release checklists.
