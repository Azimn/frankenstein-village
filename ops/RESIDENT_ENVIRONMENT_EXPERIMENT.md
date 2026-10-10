# A Resident Caught in the Rain — Environmental Causality v0.2

**Scope:** experimentally distinguish physically encountered weather from
omniscient knowledge; connect the Village Square's *existing* rain to
Resident Life's existing body conditions and the player-tended Tavern fire.

The previous [resident hearth response](RESIDENT_HEARTH_RESPONSE.md) was
merged in PR #49. It proved residents could remember a real fire and, when
cold enough, postpone going home for one hour. However, much of its
cold-stimulus testing used a controlled seed. This experiment supplies a
bounded **ordinary environmental source** of cold.

## New observable loop

A resident whose *normal schedule* places them **physically** in the Village
Square during actual rain gains **10 cold and 14 wet** per experienced village
hour. This happens only once per hour, and only in the rain. It does not apply
to offstage residents, Tavern visitors, dry weather, authored-locked NPCs,
or the same resident called twice in a single hour.

Their first-person perception records **what happened to them**, not a
numeric implementation value. They can subsequently answer an ordinary
`ask <resident> about rain` using their own bounded perception history.
An outside resident does not learn someone else's experience from a
public weather script.

A resident who later occupies the warmed Tavern can lose **up to 12 cold**
from its genuine logged fire, as previously implemented. If already at
zero cold, the resident may still have seen the fire, but must not claim
a reduction in an ailment they did not have. Wet clothes are not instantly
dried, and physical warmth does not magically establish friendship, heal
illness or grant profession advancement.

## Experimental contrast

| Condition | Rain observation | Cold / wet change | Hearth memory |
| --- | --- | --- | --- |
| Square, raining, current hour | Once | +10 cold, +14 wet | Only if later present at a lit hearth |
| Square, same hour repeated | None | No additional rain increase | Unchanged |
| Square, clear or foggy | None | No rain increase | Unchanged |
| Tavern or offstage, raining outdoors | None | No rain increase | Only own actual hearth encounter |
| Authored-locked character | None | Unchanged | No synthetic observations |
| Tavern heat encountered while cold | One record per tending event | Up to −12 cold; wet unchanged | First-person heat and relief |
| Tavern heat encountered while already warm | One record per tending event | Cold remains 0 | Records heat, **not** invented cold relief |

The existing ordinary Resident Life decay still applies as time passes,
so observed *net* changes on a running schedule may be smaller than the
instantaneous rain delta. No skipped hours are replayed. Both the local
clock and body-state updates remain idempotent on repeated calls.

## Test gates

- `spike/tests/resident_environment_sim.py`: matched stateful conditions,
  genuine rain to genuine heat sequence, serialized recall, absence and
  authored-lock nulls, no duplicate or out-of-order exposures, bounded
  12-perception history, cold cap, no invented relationships.
- `spike/tests/post_restart_assertions.py`: on the real Evennia database
  **after a stop/restart**, Tam Rook uses the ordinary wellkeeper's dawn
  Square schedule. A real weather-script transition to rain at day 2,
  hour 6 yields the single bounded exposure; repeating that village hour
  must not mint more rain, absent Marta Kovács must remain unwet by
  exposure, and a return to fog must end rain observations. Restore the
  original weather, leaving the real gameplay loop intact.
- All previous lamp, care, Commons, hearth, first-person and scheduled
  population checks must still pass. No new scheduler or external AI.

## Interpretation

This is **mechanical causal coverage**, not evidence that synthetic minds
feel bodily cold or that their simulated emotions are genuine. It enables
further realistic design: residents can acquire cold through normal public
conditions, seek heat for a measurable reason, and remember what they
actually experienced.

Do not treat these tests as a Muse first-session qualitative run, public
hosted soak, or as meeting the full-launch content quotas. Those remain
separately deferred.
