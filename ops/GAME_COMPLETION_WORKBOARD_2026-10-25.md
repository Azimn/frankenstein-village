# Frankenstein Village 1.0: Game Completion Workboard

Status: proposed **game development** workboard, not a launch plan.
Baseline: main 9b16f73f1acec60cd7803476caaa744a5be4a42f (2026-10-20).
Created: 2026-10-25. Review boundary: draft only; no merge, deployment, canon changes or claims of finished gameplay.

## Definition of game complete

A feature is finished only when:
1. A normal unaided player can find it through rooms, NPCs, commands or plausible evidence.
2. It has at least one executable choice and a real finite input/permission where appropriate.
3. The chosen action makes an attributable world/event/inventory/institutional change.
4. Another player can discover the changed state without omniscient assistance.
5. Refusal, scarcity, completion, absence, expiry and non-participation produce truthful responses.
6. After disconnect and a REAL local game-server restart, state and subsequent choices remain coherent.
7. Actual uncoached player sessions show comprehension and worthwhile continuation; retain friction and balance defects.
8. There are no known critical or major gameplay bugs; full clean-checkout CI passes on the exact integrated main SHA.

The approved quest-handoff section 7 remains an existing full-game quantitative
source; the subsequently merged Master GDD review/program (PR #95, especially
section 15 and FV-G00–FV-G13) is the current integrated **working plan**. Neither
a review draft nor this audit overrides the World Bible v0.2 or the design
doctrine. Escalate any true quota/canon discrepancy to the keeper rather than
quietly adopting a smaller early-access target from PR #85. Implemented
registrations and prose don't count as playable jobs, cases or content. The inventory must distinguish:
MANUSCRIPT -> STATIC SOURCE -> BOOTSTRAP -> DISCOVERED -> ACTION/OUTCOME ->
POST-RESTART -> UNCOACHED PLAY. Never promote a lower state by inference.

## Executable audit

Run from the repository root:

    python3.12 ops/game_completion_audit.py --format markdown --source-ref "$(git rev-parse HEAD)"
    python3.12 ops/game_completion_audit.py --format json --source-ref "$(git rev-parse HEAD)"
    python3.12 -m unittest discover -s ops/tests -p "test_game_completion_audit.py" -v

The report deliberately leaves many count cells unmeasured instead of inventing
zero, and it never declares a sourced row playable-complete. CI unit tests use
the same static scanner from ops/content_inventory.py. This is only the first
tier; the next coding batch must supply command-level execution evidence.

### FV-G01 executable-coverage card export (implemented in this branch)

Run without an Evennia server or inference model, at the exact checkout:

    python3.12 ops/gdd_g01_evidence_register.py --format json --source-ref "$(git rev-parse HEAD)" > g01-evidence.json
    python3.12 ops/gdd_g01_evidence_register.py --format markdown --source-ref "$(git rev-parse HEAD)" > g01-evidence.md
    python3.12 -m unittest discover -s ops/tests -p "test_game_completion_audit.py" -v

The G01 generator joins the existing source inventory with the **merged** Phase A
Calling AST audit and the Master GDD's canonical 45-edge design register.
Every one of the 21 section-15 content families, ten Callings and 45 pairwise
relationships has a source-indexed evidence card. For measured definitions
the relevant repository source file is included; all registered Calling verbs
have their real command class and world owner source paths. For the six V
chains, the world-function anchors include exact source line numbers.
These are **candidate anchors only**, not proof of normal player action or
of pair-specific professions.

Required `observed_room`, normal player command, finite input, authoritative
signed world transition, independent-account view, negative outcome, true
restart and uncoached UX proof remain null until individually observed and
reviewed. Unknown is not failure, nor success. G01 is in progress rather
than certified until missing runtime evidence is linked to its real owner.
The generated JSON is an *output*, not a new database or source of world truth.

## Dependencies and open integration

- This draft's original baseline (`9b16f73f1acec60cd7803476caaa744a5be4a42f`) is historical, not current main. Main was observed at `d7e4ddc45305e35658f7c6bf48eef132b9dfa6be` in the FV-G00 audit on 2026-10-26. Recheck before merging.
- PR #95 (Master GDD program) and stacked PRs #103–#109 are **already merged**. Their real code is the existing implementation baseline, not a pending stack.
- PR #89 is still a proposed model-free release contract. The Tavern newline fix duplicates closed/unmerged PR #90, whose fix is already present on #89's branch; keep that one code path once reviewed and authorized.
- PR #92 **is merged** and includes the usable first-evening path from closed/unmerged #91. Do not replay #91.
- PR #85 remains an optional early-access roadmap; its FV-G00 integration branch now carries the working authority/conflict register `ops/FV_G00_INTEGRATION_REGISTER_2026-10-26.md`. #78 is closed/unmerged, #88 is merged.
- PR #94 is a draft design synthesis, subordinate to the World Bible, doctrine and integrated GDD. Do not treat pair labels as accepted completed relationships.
- PR #47 (Pretorius laboratory) is deferred and outside this game.
- This PR's own code is a source audit plus this workboard. It asserts neither main integration nor new playable content; full GDD acceptance requires real client, restart and player evidence.

## Actual implementation sequence

### Batch 0: audit the playable matrix (next engineering work)

Deliver a per-role registry of real command + physical location + source state +
eligible Calling + cooldown + material input + accepted event type + observable
output + other-player visibility + restart proof. Do not use WORK help text as
job evidence. Prove a normal account can execute the path, or mark it unverified.
Classify every section 7 content family the same way.

Output: exact source-ref JSON, role-by-role verified coverage table and missing
functional paths. Include an actual first-evening path after one-off jobs are
already completed. No host needed.

### Batch 1: complete the lived-in Tavern / Market / Square ecosystem

Finish **Innkeep, Merchant and Smith together**, not three isolated command
menus. Existing concrete foundations: communal soup, hearth, signed commission,
market scale, physical workshop fitting and one-time lamp repair.

Deliverable: multiple genuinely distinct recurring contracts and daily loops,
physical supply/procurement, useful NPC baseline service when partners are absent,
visible shortages and consequences, authored character interactions, completed
and expired state, reputation/earned access grounded in history, and a reason
to return next day. Link cases and neighborhood events to the same physical
stocks. Do not reset the fixed lamp to generate filler.

Completion: each of the three roles satisfies its eventual full quota of at
least 6 authored quests and 8 genuinely different repeatable professional jobs,
rather than eight command aliases or cosmetic variants. Prove 2-account
material transfers, shortage, duplicate protection, local restart, uncoached
discovery and meaningful NPC response. Count only implemented cases.

### Batch 2: domestic care and cultural/public institutions

Complete Healer, Chronicler, Performer with recurring patients, finite medicine,
testimony correction, editorial decisions, scheduled performances and audience
response. Deliver cross-role effects: care -> records, performance -> civic
participation, publication -> attributable changes to NPC beliefs. Integrate
returns and player-authored public records, no hidden-truth promotion.

### Batch 3: investigative and geographic professions

Complete Wanderer, Detective, Hound with useful regional movement, signed route
surveys, evidence disputes, protection/community needs and persistent field
reports. Build physical expedition destinations as actual gameplay spaces.

### Batch 4: Mystic, only after explicit canon answers

Existing permitted mechanics may receive ordinary bug fixes, but any new
Guild authority, truth-value of readings, venue or failure rule is blocked
on the four unsettled canon decisions. Do not invent them.

### Batch 5: world and narrative content

Build toward ALL section 7 families: 12 newcomer scenarios, 30 civic quests,
30 small mysteries, 10-12 substantial chains, factions/cross-faction conflicts,
expeditions, social/group investigations, projects, 50+ hidden discoveries,
resident arcs, Harbinger/player-request templates, ambient events and incident
frameworks (75+ random, 30 timed, 10 server-wide). Use stateful variants,
provenance, real inputs and aftermath, not isolated prose entries. No fabricated
quest rewards or compelled storyline.

### Batch 6: coherence, balance, UX, and game-complete candidate

Audit each location for travel reasons, inspectable evidence, visible conditions,
NPC schedule, events, professions and revisit outcomes. Audit each recurring
system for meaningful decisions and no monopolizing resources. Run full local
Evennia server/telnet/browser/multi-account and post-restart suites, negative
cases, long-session tests and actual unfamiliar-player observations. Repair
defects, rewrite confusing/help text, balance the day-to-day economy and
repeat. Freeze only when the GAME is finished and gameplay evidence supports it.

## Development cadence

One active feature slice. For each slice: inventory -> test-first contract ->
implementation -> pure units -> fresh real client -> two independent accounts ->
local stop/start -> depletion/completed tests -> player usability -> final
clean-checkout CI -> reviewer signoff -> integrate -> verify new main.

Do not introduce a new economy, scheduler, quest engine or agent service.
Do not let AI model availability determine whether a person can play.

### Outside this workboard

Production host, DNS, recurring billing, cloud backup selection, domain, public
deployment and release communications. They follow a completed game and are
separate from the game-complete acceptance decision.
