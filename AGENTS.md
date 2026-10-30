# Frankenstein Village contributor rules

This repository is a **classic persistent multiplayer text MUD**, implemented
with Python 3.12, Evennia and Django. The primary product is an enjoyable,
hostable Gothic village game for ordinary people using a browser or text
terminal. The product specification and release criteria are in
`docs/PRODUCT_SCOPE_AND_RELEASE_CONTRACT.md`.

## Hard architectural rule

**The game must install, boot, simulate NPCs, accept humans, save state,
recover and launch with no language model or AI agent running.** Do not make
Ollama, llama.cpp, Transformers, a GPU, local model downloads, OpenAI,
Anthropic or other LLM inference/API credentials part of requirements, startup,
NPC tick logic, player commands, continuous integration, hosting or release
acceptance. Existing villagers use authored speech, schedules, rule-based
actions and persistent state. That is intentional, not a missing subsystem.

AI-controlled characters are optional **external player clients** that use
ordinary accounts and exactly the same in-world verbs and permissions.
`agentlogin` and `agent` are optional read-only client accessibility features.
Never treat a model-driven playtest as a prerequisite for launching the game.
The research projects Kiki, Pretorius's laboratory and other agent cognition
experiments are **out of scope** unless an explicitly separate, optional
post-launch integration is requested.

## Build the game people can play

Prioritize first-session onboarding, usable connected rooms, meaningful
professions and ordinary NPC interactions, items and material provenance,
mysteries with discoverable evidence, roleplay, cooperation, conflicts,
persistent consequences, recurring events, newcomer return paths, and
moderation. A room or calling is not done when it exists only in documentation.
Player verbs must produce state transitions that can be inspected, shared,
reconnected and verified after a real server restart.

Before adding a framework, first try to reuse the existing Evennia command
sets, village clock, event ledger, objects, cases, Commons, scheduled
residents and state storage. Do not create an unneeded AI service, second
database authority or parallel scheduler. New feature work needs a negative
case and a real normal-client route through the system. Avoid a feature that
cannot be enjoyed when only one human is online.

## Tests, merging, and release claims

Start from latest `main`. Read `GOAL.md`, the product contract, the World
Bible, the canonical quest handoff and `hidden_files/design-doctrine.md`.
Use a focused branch, inspect the existing feature, implement, add pure tests
and telnet or browser integration, test multiple players and persistence
across an actual stop/start, then require a green clean-checkout GitHub
Actions run before merging. Verify the new exact main-branch SHA after merge.

A successful test is **not** proof of a running internet service or of
content completeness. Keep full-launch targets in
`files/frankenstein-village-quest-handoff-v0.3.md` section 7 and count
implemented, reachable content separately from source manuscripts. A real
public launch needs an authorized host, TLS/WSS, secure normal account
registration, persistent volume, off-host encrypted backups with a proven
restore, moderation, recovery, multiplayer soak and an operator decision.

**When choosing the next task, prefer a verified gameplay blocker over
agent infrastructure or new planning documents. Never reopen the
"we need a local model before launch" discussion unless the user expressly
changes the product scope.**
