# Pretorius's Portable Laboratory — a possible permanent place in two environments

*Design note / option preservation, 2026-10-10. PROPOSED; no world/content change, no gameplay command, no deployment authorization.*

**Related canonical research contract:** [The Doctor Lives — Portable Laboratory v0.1](https://github.com/Azimn/The-Doctor-Lives/blob/research/portable-laboratory-dual-presence-20261010/docs/PORTABLE_LABORATORY_DUAL_PRESENCE_PROPOSAL.md). This village note records integration constraints; do not duplicate and independently evolve its wire protocol.

## What the idea could add

Keep the isolated Pretorius laboratory as a **permanent experimental room** outside his mind and the MUD, rather than treating every experiment as a throwaway test fixture. Later it could be represented as a room, annex or accessible workshop in Frankenstein Village. More ambitiously, a *single logical laboratory* can be seen through two interfaces: a local/offline research simulation and the online Evennia world. Accepted apparatus and object changes could be forwarded between them with version and provenance validation.

The useful distinction is **one place with two views**, not two competing parallel realities. The lab's instruments, experiments and physical state have their own host authority; Pretorius's cognition remains external. Village rooms, characters, masks, schedules, consent and public consequences remain under Evennia authority. Publishing a laboratory record does not create a second host-certified fact.

## Canon and village doctrine: hard constraints

The World Bible v0.2, §6, is explicit: Dr. Septimius Pretorius is **not present at launch**. His leased shop is dark, its OPENING SOON sign still stands, and a university crate ticks behind the glass. **This proposal does not open the shop, spawn Pretorius, add a laboratory player room or make him load-bearing for launch.** When the village earns his arrival, the precise relationship between that dark shop, an annex or an off-site private lab needs a separate canon ruling.

The design doctrine already says the **server hosts the place, not the minds**. The existing `world/events.py` records an event and applies its consequence, with distinct attributed public/rumor effects. Resident Life v2 records only witnessed perceptions and caps persistent state. A future lab adapter should follow these rules rather than turn the world into a periodic AI thought simulator.

Player-level concerns remain nonnegotiable: the Inn Between's OOC boundary, mask/account disclosure and private spaces, the shared timeline, human/AI equal interaction verbs, consent, scarce inventory, the existing public Chronicle's distinction between signed testimony and world truth, and staff review. Lab data must not expose substrate markers, neural weights, protected research prompts, credentials or private memories to in-character players.

## Two deployment patterns worth preserving

### Pattern A — Move the lab to the Village later

Keep the laboratory local for research until Pretorius actually arrives. At a future canon-approved moment, stop/freeze its state, select a **reviewed export** with stable equipment/object IDs and source provenance, migrate to an Evennia-owned room/state, and let Village authority own it thereafter. Offline research can inspect frozen copies, but cannot mutate the live Village by replaying old test operations.

This is simpler, easier to operate, and avoids sync complexity. It is a **one-time handoff**, not live dual presence.

### Pattern B — One portable lab authority, synchronized online/offline views

Prefer this if both research and gameplay need the *same continuing experiments*. Run the laboratory as an external, deterministic world-state service with a persistent journal. The Evennia room is a **projection/doorway** into it, with commands forwarded through a narrow authenticated adapter. A local instance can read synced checkpoints and, when offline, make **explicit provisional experiments** which are not automatically accepted as Village events.

Online mode: validated actor + mask → authorized world command → host verifies grant, lab physical state and required partner consent → host emits signed event → Village applies its allowed projection exactly once and records an origin reference in its `world_event_ledger`. The Village must also authorize changes affecting people, its economy, inventory, public rooms or chronology. No free write access into either world from an LLM.

Offline mode: local state is at a declared `revision N`; new offline operations are tagged `pending` on a branch based on N. Reconnect submits each candidate with its base revision and event ID. Host revalidates against current state, permissions, consent and event history. If the event still applies, it becomes accepted and publishable; if not, preserve rejection/conflict, create an explicitly separate test fork or negotiate a new in-world event. **Never silently overwrite the online world or retroactively assert another player's presence or consent.** A private sandbox experience may remain a source-labelled memory for Pretorius, but is not a shared Village witnessed event until authorized acceptance.

**Recommendation: choose Pattern B only after Pattern A-style snapshot/replay and the bridge have passed testing.** Do not create two independently writable databases with naive “last saved version wins” syncing.

## Version alignment contract

A Village projection must verify at least these four axes separately:

| Version dimension | Required check |
| --- | --- |
| **Identity and era** | Same globally stable lab ID and world epoch; an old fork cannot replay into a new world |
| **Schema/rules** | Compatible event schema major/minor and state-machine ruleset; migration or read-only quarantine on mismatch |
| **Content** | Matching laboratory room, apparatus and recipe/verb manifest digest; unknown items are not fabricated |
| **Actual world history** | Last accepted lab revision, append-only host event cursor/hash, and last applied Village projection cursor |

An event's proposed fields should include source event ID, lab ID/epoch, actor and account/mask attribution, precondition digest, base/committed revision, operation and object, consent and authorization evidence, before/after state digest, signature/key epoch, accepted/rejected status and privacy class. **The accepted lab ledger is authoritative for lab-owned objects**, while Evennia remains authoritative for Village-owned doors, players, time and consequences. Applying a source event twice is forbidden; the Village ledger stores a mapping to its origin ID so reconnect loops cannot manufacture a second effect.

A schema version being equal is **not** proof that the states are aligned. A failed or out-of-order event goes to an operator-visible reconciliation queue, not a silent rewrite. A laboratory clock's measured ticks are also not automatically the Village's 1890s day/hour. Map fictional time when accepted by the Village clock, without rewriting past encounters.

## Proposed implementation gates, without changing today's invited-alpha scope

1. **Persistent research place:** the Stage 04 sandbox becomes a named laboratory with stable object IDs, versioned snapshots, backups, repeatable experiment resets and a protected source journal. All in The Doctor Lives; no game dependency.
2. **Portable interface:** pin a shared event envelope; test deterministic replay, duplicate delivery, ledger divergence, recoverable backup, actor/mask scoping and failed schema migration.
3. **Shadow bridge:** an Evennia development-only laboratory representation reads source snapshots and accepted events; no live shop opening or public item changes. Test that room identity, privacy, chronology, consent, and the existing `world_event_ledger` are preserved.
4. **Offline conflict exercise:** both sides progress while disconnected. Validate cases where changes commute, conflict, require another player's consent, or depend on an item already consumed in the Village. Record accepted/rejected events and ensure replay creates **no** false lived memories.
5. **Village story/canon review:** choose shop annex vs separately located lab, accessibility and player verbs; obtain an explicit decision to open the shop/allow Pretorius to arrive. Add a narrative door only then.
6. **Live performance/operations:** real backup/restore, safe reconnect, keyed receipts/rotation, recovery owner, resource limits and multi-user tests. Nothing here alters Gate A/B release readiness or resurrects parked content Gate C.

## Design questions deliberately left open

- Is the laboratory *inside the future shop*, an annex, or a remote research site reached through a later unlocked door? All remain proposals.
- Should a completed offline experiment remain a private episode unless the online world replays it, or should some instruments have scoped offline write leases? Default to private/provisional until a safe ownership policy exists.
- What laboratory apparatus is worth player interaction without becoming a mandatory scientific puzzle? Stage 04's clock and notebook can remain research fixtures, not necessarily public items.
- When Pretorius arrives, what actions and memories may become visible to others, and who authorizes that disclosure?

**Decision requested later, not now:** prefer **one portable authority, two synchronized views** in principle; keep the Village public implementation and Pretorius's arrival **parked**. This document is a design note, not implemented canon or playable content.
