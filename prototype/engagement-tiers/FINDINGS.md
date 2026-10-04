# FINDINGS — engagement-tiers prototype

All numbers below are observed from `experiments.py` runs on 2026-10-01
(seeds 1–3 unless noted). Nothing here is invented; surprises are flagged
as such. The point of the prototype was to find them.

## Setup

100 NPCs (12 families, 10 occupations), 30 days × 4 ticks/day, 6 simulated
players, seeded RNG. Wall time: ~0.4s per 30-day run — the whole village
costs less than a second of CPU, which is the compute-follows-attention
thesis in miniature (D-tier NPCs are nearly free).

---

## EXP 1 — engagement patterns (mean over 3 seeds)

| pattern | D | C | B | A | gini | top-3 share | max_E |
|---|---|---|---|---|---|---|---|
| concentrated (1 player, 1 NPC) | 77 | 11 | 6.7 | 4.3 | 0.90 | 53.7% | 106 |
| diffuse (players meet strangers) | 18 | 75 | 6 | 0 | 0.23 | 6.5% | 17 |
| social (regulars + friends-of-friends) | 46 | 40.7 | 11.7 | 0.7 | 0.54 | 16.1% | 40 |

- **Concentrated is pathological as designed**: one obsessed player mints
  A's (4.3) while 77 NPCs languish at D. This is the streamer-favorite
  scenario; the sim says a single devoted player *can* carry an NPC to A
  in 30 days. That's a feature, not a bug — but see the shopkeeper note.
- **Diffuse is too flat**: nobody reaches A (max_E 17 < 40). Egalitarian
  attention never compounds. Real players aren't this diffuse.
- **Social is the healthy middle**: a dozen B's (genuine friends), C as the
  broad middle, A's rare (0.7). Gini 0.54 — unequal, but that's what a
  village with favorites looks like.

**Shopkeeper check**: under concentrated attention the highest shopkeeper
tier reached was **B**, under social/diffuse **C**. The role-bounded rule
(0.25× engagement on shift) works: you cannot mint an A-tier shopkeeper
by standing at the counter all day. They have to clock out and be a person.

**Surprise — A's need superlinear favorites.** With linear preferential
attachment (`1 + visits`), social play produced **zero** A's at any
timescale (max_E plateaued at ~24 even at 90 days; decay balances inflow).
Quadratic attachment (`(1+v)²`) produced A's but collapsed the village
into oligarchy (90d: D:82, A:6 — worse than concentrated). Exponent 1.5
was the sweet spot. **Design implication**: real players *do* have
favorites ("I always talk to Marta first"), and the tier economy depends
on it. If playtesters turn out to be diffuse, A's will never happen —
consider whether that means the A threshold is wrong or the players need
social scaffolding (tavern regulars' table, etc.).

---

## EXP 2 — stability (15 days players, 15 days none)

- **Zero yo-yos** across all seeds (no NPC promoted then demoted within
  5 days). Hysteresis + 3-day grace do their job.
- Demotion is graceful: B's decay to C over ~10 days after players leave
  (seed 1: B 9→1 from day 15→30; seed 3: B 11→2). No cliff.
- **Ratchet holds**: 8/8, 6/6, 7/7 ratcheted NPCs kept their floor tier
  through the full neglect phase.

**Surprise — the ratchet had to promote, not just floor.** The first
version set the engagement floor but left the tier unchanged: the forge
hero sat at D-tier with an 18.0 floor, unrecognized. The village must
recognize its heroes *immediately* — `ratchet()` now sets the floor *and*
promotes to the floor's tier (trauma/marriage → C, heroism → B).

---

## EXP 3 — rumor spread (manor light, day 5 evening)

p_transmit sweep, aware counts by day (of 100 NPCs):

| p | day 5 | day 6 | day 7 | day 9 | final | variants |
|---|---|---|---|---|---|---|
| 0.15 | 9–10 | 9–11 | 11 | 11–16 | 12–16 | 2 |
| **0.30** | 10–11 | 11–14 | 11–15 | 13–17 | 23–30 | 2–3 |
| 0.50 | 10–12 | 12–16 | 13–16 | 15–24 | 34–41 | 3 |

At p=0.3, seed 1, day 9: three live variants —
*"a blue light burned in the manor's east tower"* (14 believers),
*"a strange light was seen at the manor"* (10),
*"someone is living in the manor again"* (6).
Max generation 4, mean confidence ~0.26. "Several different accounts by
morning" — **confirmed**, roughly: by day 6–7 there are 2–3 distinct
accounts circulating.

- **NPC-only gossip works**: with no players, 8 witnesses → 17–23 aware
  by day 9. Players are rumor *accelerants*, not a requirement.
- **Surprise — 62 witnesses.** The first version seeded the rumor to every
  NPC outdoors that evening — 62 of them. The manor light is a 41-second
  event; it should have a handful of witnesses, with everyone else hearing
  it secondhand. Witnesses are now sampled (8). This matters: the rumor
  *system* is the game, not the event.

**Recommendation: p_transmit = 0.3.** 0.15 stalls (rumor dies in a
corner); 0.5 saturates the village in days (no mystery left). 0.3 gives
multi-day propagation with real variant diversity.

---

## EXP 4 — need balance

| seed | starve_ticks | top actions | degenerate | adherence |
|---|---|---|---|---|
| 1 | 0 | travel 26%, sleep 19%, eat 13%, socialize 12%, rest 12%, work 7.5% | 0 | 41.6% |
| 2 | 0 | (same shape) | 0 | 41.3% |
| 3 | 0 | (same shape) | 0 | 42.6% |

**Zero starvation, zero degenerate NPCs** — but only after fixing three
real bugs the prototype caught:

1. **The rest-loop** (surprise): rest was 45% of all actions, sleep 4%.
   Fatigue drifted +7/tick, so NPCs rested in place instead of going home
   to sleep. Fixed: drift +4, rest has diminishing returns (`0.6^streak`),
   evening head-home heuristic. Rest is now 11–12%, sleep 19%.
2. **Nobody commuted** (surprise): `tend_home` relieved *duty*, so NPCs
   stayed home tending house instead of going to work. Duty is now job-only
   (work/serve/trade); `tend_home` relieves affiliation. Work reappeared
   at 7.5% and duty equilibrates at mean 42, not pinned at 100.
3. **Wasted meals** (surprise): NPCs ate at hunger 30, burned through food,
   then starved until the emergency market trip (500+ starve_ticks). Fixed:
   eat is gated at hunger > 45, trade stocks up (+5 food, bonus when the
   pantry is bare), and a hungry NPC with no food shops *before* it's an
   emergency (hunger > 75 → market). The fix was food *logistics*, not
   utility tuning.

Remaining honest imperfection: schedule adherence is 42% — NPCs follow
their schedule less than half the time because needs intervene. That
reads as lifelike, not broken (a farmer who skips work because he's
exhausted is a character, not a bug). Travel at 26% is the commute +
market trips + peddlers; no ping-pong observed in traces.

---

## EXP 5 — memory bounds

All tier caps respected across all runs: D:0, C:5, B:30, A:60.
Max total memories: 428 across 100 NPCs. The caps are load-bearing for
the compute budget — a village of D's remembers nothing, which is why
it's cheap.

---

## EXP 6 — zero engagement

- 0.39–0.40s wall time for 30 days. The village runs on schedules +
  gossip alone: 10/10 actions used, 1–2 rumors spread past 5 NPCs via
  gossip, zero starvation.
- Tiers collapse honestly: D 24→~90 by day 20, C 66→0, seeded B/A's decay
  out over ~10 days. **Without players, nobody is anybody.** That's the
  design working, not failing — attention is the scarce resource and the
  sim doesn't fake it.

---

## Design recommendations

1. **Keep UP_A = 40.** A's should require devoted, multi-player attention
   over weeks. The sim validates the full D→C→B→A pipeline under organic
   play (social yields A's at 90 days: 2) and under devoted play
   (concentrated yields 4.3 at 30 days).
2. **Favorites are load-bearing.** Superlinear preferential attachment was
   *required* for any A to emerge. Watch playtests: if players spread
   attention evenly, consider social scaffolding (regulars' table, NPCs
   who introduce you to their friends) rather than lowering the threshold.
3. **Ratchet = floor + immediate promotion.** A life event that only sets a
   floor leaves heroes unrecognized. (Fixed in sim.)
4. **p_transmit = 0.3** for rumor spread. Sample event witnesses (8, not 62).
5. **Fence survival overrides, then fix logistics not utilities.** All three
   need-balance bugs were structural (drift rates, what relieves duty, food
   economics) — none were fixed by retuning utility weights.
6. **The no-model tier is viable.** 100 NPCs × 30 days in 0.4s with zero
   starvation, zero degeneracy, graceful demotion, and honest collapse
   under neglect. The tier economy, rumor system, and need engine all run
   without any language model. Dialogue will render on top of this — it
   doesn't have to carry it.

## Open questions for the real build

- **A-tier migration path**: the sim says A's need ~2.8 engagement/day
  sustained. What does "small local model per A-tier NPC" cost at 2–6
  concurrent A's? That's the fixed-budget question this prototype can't
  answer.
- **Player-as-rumor-vector**: players spread rumors faster than NPC gossip
  (23–30 vs 17–23 aware by day 9). In the real game, do player-retold
  rumors distort *more* (they will)? The distortion ladder assumes
  per-retelling mutation — player retellings are unmodeled here.
- **The D-majority village**: under social play, ~46% of NPCs sit at D
  after 30 days. Is "half the village are strangers" the right feel, or
  should first contact be cheaper (stronger distinct-visitor bonus)?
