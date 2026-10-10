# When the Village Notices the Fire — Resident Hearth Response v0.1

**Gameplay development; not a new artificial mind.** The existing resident
population architecture already has body conditions, first-person perceptions,
ordinary schedules and high-priority needs. The renewable hearth is a public,
finite-resource change created by real player actions. This feature connects
those systems without attaching a romance score, scripted gratitude, or an
independent AI controller.

## Observable player-to-resident consequence

A Smith gathers and delivers a physical firewood bundle. An Innkeep spends
that stock at the Blood of the Vine. During the resulting eight village hours,
a population resident who actually occupies that Tavern can *experience*
the stronger fire:

- Exactly once for that tending event, their existing bounded perception
  store receives a **first-person** observation: "I felt the stronger fire
  at the Blood of the Vine ease the cold."
- Their measured `cold` body condition decreases by 12 points (to a
  minimum of 0). This is limited warmth, **not** healing illness,
  injury or wounds, and not inferred emotion or social loyalty.
- Later, `ask <resident> about hearth` can return their remembered
  sensory experience. A resident who was absent does not impersonate a
  witness or inherit what another character experienced.
- If the resident is still sufficiently cold (55+), physically in the
  Tavern, was scheduled there in the *previous hour*, and would now
  ordinarily go home, they may choose to stay for **one more village hour**
  before departing. This preference operates only while fresh wood is
  burning. At the next hourly schedule it returns to ordinary life.
- High fatigue, safety danger, serious illness or injury, prior life goals
  and authored or legacy-locked characters take precedence. There is
  **no** schedule override for NPCs who were not actually in the Tavern.

This is a constrained choice, not an automatic romance, generalized
personality rewrite, person-to-player gratitude or diagnosis of consciousness.

## Causal guards

The resident consumes the room's actual public `civic_hearth` snapshot
after the normal physical placement step. The live fire's **last tending
event ID** comes from persisted room history and is used only to identify
an observation; repeating a population tick cannot create another heat
effect or perceived episode for the same event. The observation remains
per resident and the standard `Resident Life` life state remains
authoritative. The single-hour schedule preference is evaluated *after*
more important existing need, commitment and safety overrides.

There is one snapshot per population pass and no extra interval timer,
LLM token expense, external server, novel player entitlement, or
high-frequency worldwide activation. Server restart preserves the
existing resident life store and does not replay the same episode.

## Experimental contrast / verification

`spike/tests/resident_hearth_sim.py` is a pure deterministic test for
first exposure, distant observer null, expired-fire null, event-replay
idempotence, actor-locked null, cold reduction, first-person recollection,
one-hour discretionary preference, unsafe/high-fatigue/vulnerable nulls,
serialized continuation and no fabricated relationships.

The full Evennia regression sets a meaningful body-cold stimulus on
Mara Crowe (hunter schedule) and Marta Kovács (Sunday-at-home control)
**after** existing world-assertion simulations and before the ordinary
two-account telnet Hearth delivery and tending. On server restart,
the real persisted fire and the existing population scheduler must show:

1. Mara at Tavern at 21:00 experiences **exactly one** current burn,
   recalls it when asked, and measurably has less cold.
2. A duplicate same-hour population call does not replay the exposure.
3. Marta, absent at home, has no experience of that tending; Father Andrei
   retains his authored-locked life profile.
4. Mara's remaining cold permits a one-hour Tavern stay at 22:00 instead
   of her planned departure. She leaves on the normal schedule by 23:00.
5. No resident-to-player attachment, rank, coins or new quests are
   inferred from sharing a warm room.

**Evidence boundary:** mechanical scripted acceptance is not a real
unscripted Muse playtest, not a survey of all resident cognitive profiles,
and not proof that subjective emotions or consciousness exist. Museum
content scale and hosting are separately tracked and untouched.

## Future expansion

The same physical-experience contract can later mediate rain shelters,
heat-loss by district, illness precautions, public meals and damaged
lighting. Each should first prove the measurable difference between
a resident who was **there** and one who only heard a story about it.
