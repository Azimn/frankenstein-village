# Engagement-Tiers Prototype

An offline simulation of the Frankenstein Village NPC engagement-tier
system. Pure Python 3 standard library — no network, no LLM, no Evennia.
Deterministic: every run is seeded.

This is the **no-model tier** of the design: the whole NPC layer must stay
playable with all language models disabled. If the village isn't alive
here, no amount of dialogue polish will save it.

## Files

| File | What it is |
|---|---|
| `sim.py` | The village: 100 NPCs, 30 days, 4 ticks/day, 6 simulated players. Needs-driven action selection, schedules, rumor-as-data gossip, episodic memory with tier caps, engagement tiers D→C→B→A, genealogy, personality traits, scripted life events. |
| `experiments.py` | Six experiments answering the design questions below. |
| `FINDINGS.md` | What the experiments actually showed (real numbers), plus design recommendations. |

## Run

```bash
cd prototype/engagement-tiers
python3 sim.py                 # smoke demo: 30 days, social pattern (~0.5s)
python3 experiments.py all     # all six experiments (~20s)
python3 experiments.py 3       # just experiment 3 (rumor spread)
```

`experiments.py` takes one argument: `1`–`6` or `all`.

## The six experiments

1. **Engagement patterns** — concentrated vs diffuse vs social players. Does
   attention concentrate pathologically or distribute sanely?
2. **Stability** — 15 days of players, then 15 days of none. Graceful demotion
   or yo-yo churn? Do life-event ratchets hold?
3. **Rumor spread** — the manor light (day 5, evening). How fast does gossip
   travel, how many variant accounts exist by morning?
4. **Need balance** — does anyone starve? Does any NPC get stuck in a
   degenerate routine (rest-loop, work-loop)?
5. **Memory bounds** — are the per-tier episodic memory caps respected?
6. **Zero engagement** — no players at all. Is the village alive but cheap?

## Design reference

Built from `research/npc-simulation-handoff-v0.1.md` §25 (tiers + promotion
rule) and §9 (rumor as data object), with corrections from
`research/npc-simulation-review-2026-10-01.md`. Key mechanics:

- **Tiers**: D (named + schedule) → C (memory, personality) → B (beliefs,
  relationships) → A (full inner life, migration path to small local models).
- **Promotion**: engagement ≥ threshold (8/16/40), 3-day grace, hysteresis on
  demotion (1.5/8/22), 0.93/day decay.
- **Ratchet**: trauma/marriage/heroism set a permanent engagement floor *and*
  promote to the floor's tier — the village recognizes its heroes immediately.
- **Role-bounded complexity**: shopkeepers earn 0.25× engagement while on
  shift (transaction mode at work, person mode off-duty).
- **Rumor as data**: rumors carry source provenance, generation count, and a
  distortion ladder; confidence decays; stale rumors (<0.35) aren't retold.
- **Memory**: salience-weighted episodic memory, tier-capped (D:0, C:5, B:30,
  A:60), decays with residues.

Tunable constants live at the top of `sim.py` (`UP`, `DOWN`, `GRACE_DAYS`,
`P_TRANSMIT`, drift rates, `RELIEF`/`COST`).
