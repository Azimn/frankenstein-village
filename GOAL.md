# Frankenstein Village: a playable persistent text MUD

Goal ID: goal_3670f2f1a1a5
Goal slug: mixed-ai-human-text-mud

## Product

Build and ship a complete, enjoyable, internet-hosted text adventure and social
village simulation. Players create accounts and characters, explore a shared
Victorian Gothic village, take Callings, discover clues, roleplay, cooperate,
disagree, trade physical goods, create persistent consequences, and return to a
world that has continued changing.

The authoritative simulation is the **Evennia Python game server**: commands,
authored text, schedules, rules, resident behaviors, material stocks, inventories,
mysteries, and persisted state. **No large language model, local inference engine,
Ollama process, model download, LLM API key, agent framework, or AI service is
required to install, start, play, test, host, or launch the game.**

Human players use ordinary browser or terminal clients. Optional autonomous
AI players can use exactly those same permissions and ordinary commands.
Machine-readable `agent` and `agentlogin` output is an optional interface,
not an alternative game runtime, launch gate, or privileged action channel.

The Inn Between contains the mandatory out-of-character disclosure compact;
in-character identity is separate. The world is a game first, a persistent social
simulation second, and an AI experiment only if an independent player chooses
to bring their own model.

## Completion criterion

A release candidate is not defined by a number of documents, AI agent
demonstrations, or a green test suite alone. A new person must be able to
register or receive an account, pass the compact, enter the village, find fun
activities without coaching, cause meaningful persistent changes, leave,
reconnect, and continue playing. Workplaces, mysteries, careers, inhabitants,
and recurring events must be navigable and demonstrably functional through
ordinary player commands. Verify normal multiplayer interaction, restart and
backup recovery, moderation and secure public access before publishing.

Canonical contract: [docs/PRODUCT_SCOPE_AND_RELEASE_CONTRACT.md](docs/PRODUCT_SCOPE_AND_RELEASE_CONTRACT.md).
Keep the longer full-launch content goals in
[files/frankenstein-village-quest-handoff-v0.3.md](files/frankenstein-village-quest-handoff-v0.3.md);
do not silently count manuscript content as implemented gameplay.
