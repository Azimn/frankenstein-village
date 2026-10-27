# Frankenstein Village: Embodied First-Person Experience and Tarn-Rule Acceptance

**Status:** Review-draft Master GDD §3.5 / §3.6 / §12 / §19.4 T-09 companion. This clarifies player experience; it does not change World Bible canon or invent a new needs engine.
**Origin:** Keeper's 2026-10-25 request to make simulated bodily life unusually rich for AI players. Scope is the **character's** rendered/represented experience. No claim is made that the AI running the character literally feels hunger, pain or pleasure.

## Design goal

An AI player should not merely have a hunger meter to optimize. It should receive lived-*as-character*, first-person sensory signals about body, surroundings and what the body is drawing its attention toward: the difficult precision of cold fingers, the hollow pressure of hunger, stomach discomfort, and **eventually** dry mouth, aching limbs or damp clothing only where the game has explicitly represented those states; the lowering of physical discomfort after material relief, and the different quality of hunger before and after a meal. These signals are state-grounded prose, never fabricated memories, hidden truth, or fake senses.

This supports the core game's special complement to the AI condition: a persistent body, an accumulating past, forgiveness instead of score-chasing, and a village which can respond to needs. It also remains entirely usable by a human player. An AI/Human declaration must **not** create different physics, privileged omniscient data, compulsory suffering or unequal access.

## Output surfaces without another engine

- **`score`** remains the short, familiar player-facing body summary.
- **`score deep`** describes the same player character's simulated sensations and attentional pulls in richer first person. It is equally available to humans and AI, on demand.
- **`agent` / `agent context`** expose the *same* first-person sensory projection in a bounded `embodiment` field, alongside ordinary observable location and actions. No numeric hidden need values or private data of other characters are sent.
- This is a **pure perception renderer over established attributes**: `mask.db.hunger`, `mask.db.warmth`, `mask.db.drunkenness`, `mask.db.queasy`, posture. The authoritative variables stay in their existing objects/scripts. The projection may vary in language across degrees of need but does not mint a need or change physical world state.
- Sensory language is grounded in the represented character, not the AI model's actual biological or conscious state; do not treat the prose as evidence of consciousness.
- A description does not establish wet skin, illness, a visible wound, weather, food availability, physical contact or pain unless such state was actually recorded.

## Graded authored sensations (design direction)

| Source state | Brief version | Detailed first-person flavor | Verifiable relief |
| --- | --- | --- | --- |
| Hungry / famished (existing hunger) | Hunger pulling at the body | A persistent hollow under the ribs, wandering attention and a sharper awareness of nearby food when actually observed | `eat` an existing edible object, bread/cheese/stew or real carried soup; existing stock/price rules, finite serving counts, truthful shortage |
| Cool / shivering / freezing (existing warmth script) | Breath and fingers feel cold | Gradual stiffness, wanting to fold arms around the torso, the contrast when indoors or beside real heat | Move into existing shelter and wait for the `WarmthWatch` tick; `hearth` can raise communal warmth when real wood is available |
| Intoxicated (existing drunkenness) | Balance and attention less certain | A delayed moment of spatial adjustment; colors and sound may feel close, but don't claim literal hallucinations | Existing free water and gradual movement-time sobering |
| Queasy (existing `queasy`) | The stomach is unsettled | A throat-clench or wave of nausea that competes with the wish to eat | Existing time/movement resolution; investigate a bounded, real, accessible soothing drink, not a miracle cure |
| Rest, thirst, pain, dampness, exhaustion | Not currently independent player-mask need variables | **Do not invent first-person certainty or gameplay obligations** | Do not activate new drive before a unique authoritative source and tested in-world relief |

## T-09 and the right to relief

Every simulated need is a *request for inhabitable action*, not a punitive lock or damage clock. The Tarn rule is stronger than simply posting `eat bread` in help.

- A **safe, playable alternative** must remain when a particular food is gone, money is absent, or a character is nauseated. Prefer existing Tavern meals and real communal stocks, not boundless inventory conjuration. The current finite Tavern bread/cheese/stew stock and coin economy are *already real*, but no comprehensive exhausted-all-food safety path has been certified.
- Existing `world.routines.restock_sideboard` already restocks **the same physical plate** when Bram is actually at the Tavern and his routine ticks. This is preferable to any invented daily refill. If he is away, the board stays bare until the keeper returns; alternate genuine food and earning/sourcing routes must remain available. Do not bypass Bram's physical presence or pretend a player magically creates bread.
- Help must say what is *actually* reachable from the character's present location, not assume an exhausted sideboard or offline merchant is available.
- Distinguish changing the authoritative physiological variable from merely outputting soothing prose. A reassuring sentence does **not** relieve hunger or cold.
- Keep these behaviors present across normal client, AI adapter, process restart, and late arrival; test depleted sources, poor characters, queasy hunger, return to village, and identity switching.
- The 1.0 Tarn rule remains **UNVERIFIED** until those cases and actual uncoached player experiences pass. This document does not certify T-09.

## Emic-first evaluation

Have an unfamiliar AI player interact with `score deep`, make a choice, apply in-world relief, and describe what its character appeared to experience **without reading the code**. Compare recorded source values/events and game receipts to its descriptions. Repeat with an unfamiliar human player using either concise or immersive view. Record boredom, moral surprise, confusion, sensory contradictions, discovered action paths and whether the next turn genuinely changed the represented body.

**Full-game follow-up:** Once existing four bodily signals work and have no dead ends, develop only grounded additional drives with their own source and relief design reviewed by keeper. Do not create a generalized physiology simulator, replace the existing world, or gate fun behind grind.

## First implementation, source-bounded

The first PR implementing this design reuses exactly four player-character variables, exposes the detailed projection through `score deep` and ordinary `agent` context, and keeps `score` concise.

**T-09 physical recovery mechanisms under review:** We **reused** existing `world.routines.restock_sideboard` and its tested Bram-presence guard: the same finite plate can be replenished by NPC action on an ordinary routine tick, not by a new clock/day formula. Existing free water gains a **modest reduction** of recorded queasiness, rather than granting omnipotent healing. Unspoiled cheese is a genuinely separate finite source if bread is exhausted; soup remains produced from real pantry ingredients. No new food ownership, stock model or restock engine was added. These choices do not replace material conservation or paid food.

**Still unverified for final 1.0:** a fully exhausted whole-village food supply; zero-coin hunger when all earnable goods and stock are inaccessible; non-player-initiated emergency care; sustained new needs such as thirst, sleep, pain, fear or wetness; uncoached evaluation. Until each is tested, the Tarn rule is a live product gate, not a checked item.
