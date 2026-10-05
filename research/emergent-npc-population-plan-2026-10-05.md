# Emergent NPC population implementation plan, 2026-10-05

Status: active implementation plan. This document reconciles the live repository with the later emergent-population addendum. When sources disagree, authority is: current design doctrine and world bible, then newer design decisions and live tested runtime, then older genealogy/research notes, then this addendum.

## Reconciliation

The addendum agrees with the adopted repository doctrine on the important points: server-owned truth, no population-wide LLM loop, simulation of consequences rather than unused detail, engagement-driven depth, genealogy as cheap history, persistent rumor provenance, no OOC perception by NPCs, and a no-model acceptance path.

Where older files disagree with current canon, newer repository state wins. The genealogy remains authoritative for its named households, kinship, debts, and feuds, but its older keeper and church notes are superseded by current canon: Bram V. is the named Blood of the Vine keeper, Father Andrei runs St. Lazarus, and M. is the dual-ontology Inn exception. The genealogy's Father Anselm is therefore not materialized as a second current priest.

The engagement-tier prototype remains empirical guidance, not a mandate to erase established characterization on demotion. Production keeps its tested engagement hysteresis and role-bounded-complexity idea, while separating current simulation resolution from accumulated character depth. A resident can become cheap again without losing facts, relationships, important memories, or established history.

## Dependency graph

```
canonical resident identity + stable IDs
            |
            +--> household/genealogy graph
            |
            +--> logical location model + schedule templates
                          |
                          +--> coarse/lazy routine advancement
                          |       |
                          |       +--> destination validation + fallback reason
                          |       +--> lifecycle gating
                          |       +--> observer-sensitive rendering
                          |
                          +--> structured world-event wakeups
                                      |
                                      +--> family/household consequences
                                      +--> narrative importance
                                      +--> persistent event flags

player interaction
      |
      +--> per-player relationship state
      |       |
      |       +--> engagement / active simulation resolution
      |       +--> recognition
      |       +--> relationship-gated revelation
      |
      +--> accumulated character depth high-water mark
              |
              +--> persistent interests
              +--> fact assignment
              |       |
              |       +--> global unique/limited claim registry
              |       +--> shared reality across players
              |
              +--> bounded important memory
                      |
                      +--> state-sensitive dialogue rendering

facts + events + observations
            |
            +--> existing structured rumor registry
                    |
                    +--> NPC belief changes / wakeups
                    +--> player retellings with provenance

all of the above
      |
      +--> multi-day simulation
      +--> restart/idempotence regression
      +--> isolation and duplicate-secret tests
      +--> actual telnet playtest
      +--> population/performance measurements
```

## Production invariants

Mutable resident state is owned by the individual Evennia object. Process-wide module data is definition-only. Global mutable coordination is limited to the persistent resident-population script for location availability, fact-claim accounting, and aggregate metrics.

Physical rooms and logical places are separate. Unbuilt homes, fields, school, workshops, and other locations project to the existing Offstage room while retaining a distinct logical location. This preserves temporal and spatial truth without creating rooms merely to justify simulation.

Automaton-mode routine success performs no utility evaluation. A schedule boundary resolves current location and activity, validates the destination, and persists only consequential changes. More expensive evaluation is reserved for wake conditions or active player relationships.

Simulation resolution, character depth, and narrative importance are separate fields. Resolution may fall. Character depth is a high-water mark and never falls merely because players leave. Narrative importance changes through events, quests, rumors, or explicit world consequences rather than automatically mirroring player attention.

Facts are global truths about one resident. Relationships store what each player has earned access to. Assigning a secret never publishes it as a rumor. Exposure requires a structured pathway.

The existing authored NPCs retain their specialized typeclasses, dialogue, schedules, and mystery behavior. The population layer registers them into shared identity and relationship infrastructure rather than replacing their authored behavior.
