#!/usr/bin/env python3
"""
Experiment runner for the engagement-tier NPC prototype.

Six experiments, each answering a design question from the task brief.
All runs are seeded and deterministic. Prints reports to stdout.

  python3 experiments.py [1|2|3|4|5|6|all]
"""
import sys
from collections import Counter
from sim import World, TIER_ORDER

SEEDS = [1, 2, 3]
DAYS = 30


def mean(xs):
    return sum(xs) / len(xs) if xs else 0.0


def top_share(world, k=3):
    es = sorted((n.engagement for n in world.npcs if n.alive), reverse=True)
    return sum(es[:k]) / sum(es) if sum(es) else 0.0


def final_tiers(world):
    return world.tier_counts()


# ------------------------------------------------------------------ exp 1
def exp1_concentration():
    print("=" * 70)
    print("EXP 1 — engagement patterns: concentrated vs diffuse vs social")
    print("Q: does engagement concentrate pathologically or distribute sanely?")
    print("=" * 70)
    for pattern in ("concentrated", "diffuse", "social"):
        tiers_acc, ginis, nas, nbs, tops, maxes, shop_max = [], [], [], [], [], [], []
        for s in SEEDS:
            w = World(seed=s, pattern=pattern)
            w.run(days=DAYS)
            t = final_tiers(w)
            tiers_acc.append(t)
            ginis.append(w.history[-1]["gini"])
            nas.append(t.get("A", 0))
            nbs.append(t.get("B", 0))
            tops.append(top_share(w))
            maxes.append(w.history[-1]["max_e"])
            shop_max.append(max([n.tier for n in w.npcs
                                 if n.occupation == "shopkeeper"] or ["D"],
                                key=lambda x: TIER_ORDER[x]))
        tc = {t: round(mean([d.get(t, 0) for d in tiers_acc]), 1)
              for t in TIER_ORDER}
        print(f"\n[{pattern}]")
        print(f"  final tiers (mean over seeds): {tc}")
        print(f"  gini(mean)={mean(ginis):.2f}  A={mean(nas):.1f}  B={mean(nbs):.1f}")
        print(f"  top-3 engagement share={mean(tops):.1%}  max_E={mean(maxes):.0f}")
        print(f"  highest shopkeeper tier reached: {Counter(shop_max).most_common(1)[0][0]}")
        # churn: how many NPCs changed tier more than twice?
        w = World(seed=1, pattern=pattern)
        w.run(days=DAYS)
        churny = sum(1 for c in w.churn.values() if c > 2)
        print(f"  NPCs with >2 tier changes: {churny}  yo-yos: {w.yo_yos}")


# ------------------------------------------------------------------ exp 2
def exp2_stability():
    print("=" * 70)
    print("EXP 2 — stability: 15 days of social engagement, then 15 days of none")
    print("Q: does demotion decay gracefully, or do NPCs yo-yo?")
    print("=" * 70)
    for s in SEEDS:
        w = World(seed=s, pattern="social")
        w.run(days=15)
        mid = dict(final_tiers(w))
        w.pattern = "none"          # the players leave
        w.run(days=30)              # continue to day 30
        end = dict(final_tiers(w))
        prom = len([l for l in w.log if l[1] == "promote"])
        dem = len([l for l in w.log if l[1] == "demote"])
        traj = [(h["day"], h["tiers"]["A"], h["tiers"]["B"],
                 h["tiers"]["C"], h["tiers"]["D"]) for h in w.history[::5]]
        print(f"\n[seed {s}] tiers day15: {mid} -> day30: {end}")
        print(f"  promotions={prom} demotions={dem} yo-yos={w.yo_yos}")
        print(f"  trajectory (day,A,B,C,D): {traj}")
        # ratchet check: hero / married / grieving NPCs must hold their floor
        held = sum(1 for n in w.npcs
                   if n.alive and n.floor > 0 and
                   TIER_ORDER[n.tier] >= TIER_ORDER[{6.0: "C", 10.0: "C", 18.0: "B"}[n.floor]])
        floored = sum(1 for n in w.npcs if n.alive and n.floor > 0)
        print(f"  ratcheted NPCs holding floor tier: {held}/{floored}")


# ------------------------------------------------------------------ exp 3
def exp3_rumor():
    print("=" * 70)
    print("EXP 3 — rumor spread: manor light, evening of day 5")
    print("Q: too fast / too slow? 'several different accounts by morning'?")
    print("=" * 70)
    for p in (0.15, 0.30, 0.50):
        print(f"\n[p_transmit={p}]")
        for s in SEEDS[:2]:
            w = World(seed=s, pattern="social", p_transmit=p)
            w.run(days=DAYS)
            # daily awareness, days 5..9 (event fires evening of day 5)
            daily = [(h["day"], h["rumor_aware"].get("manor_light", 0))
                     for h in w.history if 5 <= h["day"] <= 9]
            rep = [r for r in w.rumor_report() if r["subject"] == "manor_light"][0]
            print(f"  seed {s}: aware by day {daily}; "
                  f"final aware={rep['aware']} variants={rep['variants']} "
                  f"max_gen={rep['max_gen']} mean_conf={rep['mean_conf']:.2f}")
            if s == 1 and p == 0.30:
                print(f"    claim variants: {rep['claims']}")
    # NPC-only spread (no players): does gossip alone carry news?
    print("\n[NPC-only gossip, p=0.30, no players]")
    for s in SEEDS[:2]:
        w = World(seed=s, pattern="none", p_transmit=0.30)
        w.run(days=DAYS)
        daily = [(h["day"], h["rumor_aware"].get("manor_light", 0))
                 for h in w.history if 5 <= h["day"] <= 9]
        rep = [r for r in w.rumor_report() if r["subject"] == "manor_light"][0]
        print(f"  seed {s}: aware by day {daily}; final aware={rep['aware']} "
              f"variants={rep['variants']} max_gen={rep['max_gen']}")


# ------------------------------------------------------------------ exp 4
def exp4_needs():
    print("=" * 70)
    print("EXP 4 — need balance: does anyone starve? degenerate routines?")
    print("=" * 70)
    for s in SEEDS:
        w = World(seed=s, pattern="social")
        w.run(days=DAYS)
        total = sum(w.action_totals.values())
        top = Counter(w.action_totals).most_common(6)
        toppct = [(a, f"{c / total:.1%}") for a, c in top]
        # degenerate: any NPC spending >80% of non-sleep ticks on one action?
        degen = 0
        for n in w.npcs:
            c = Counter({a: v for a, v in n.action_counts.items() if a != "sleep"})
            t = sum(c.values())
            if t and max(c.values()) / t > 0.8:
                degen += 1
        print(f"\n[seed {s}] starve_ticks={w.starve_ticks} "
              f"by_occ={dict(sorted(w.starve_by_occ.items()))}")
        print(f"  top actions: {toppct}")
        print(f"  degenerate NPCs (>80% one action): {degen}")
        print(f"  schedule adherence: {w.sched_hits / w.sched_total:.1%}")


# ------------------------------------------------------------------ exp 5
def exp5_memory():
    print("=" * 70)
    print("EXP 5 — memory bounds under all runs")
    print("=" * 70)
    worst = {t: 0 for t in TIER_ORDER}
    totals = []
    for pattern in ("concentrated", "diffuse", "social", "none"):
        for s in SEEDS:
            w = World(seed=s, pattern=pattern)
            w.run(days=DAYS)
            mx, total = w.memory_report()
            totals.append(total)
            for t in TIER_ORDER:
                worst[t] = max(worst[t], mx[t])
    caps = {"D": 0, "C": 5, "B": 30, "A": 60}
    print(f"max memories per tier across all runs: {worst}")
    print(f"tier caps:                            {caps}")
    print(f"total memories: max={max(totals)} (100 NPCs)")
    assert all(worst[t] <= caps[t] for t in TIER_ORDER), "CAP VIOLATION"
    print("all caps respected: OK")


# ------------------------------------------------------------------ exp 6
def exp6_zero():
    print("=" * 70)
    print("EXP 6 — zero engagement: is the village alive but cheap?")
    print("=" * 70)
    for s in SEEDS:
        w = World(seed=s, pattern="none")
        w.run(days=DAYS)
        total = sum(w.action_totals.values())
        acts = len([a for a, c in w.action_totals.items() if c > 0])
        rum = sum(1 for r in w.rumor_report() if r["aware"] > 5)
        traj = [(h["day"], h["tiers"]["A"], h["tiers"]["B"],
                 h["tiers"]["C"], h["tiers"]["D"]) for h in w.history[::10]]
        print(f"\n[seed {s}] wall={w.wall:.2f}s tiers trajectory {traj}")
        print(f"  distinct actions used: {acts}/{len(w.action_totals)} "
              f"schedule adherence: {w.sched_hits / w.sched_total:.1%}")
        print(f"  rumors reaching >5 NPCs via gossip alone: {rum}")
        print(f"  starve_ticks={w.starve_ticks}")


EXPS = {"1": exp1_concentration, "2": exp2_stability, "3": exp3_rumor,
        "4": exp4_needs, "5": exp5_memory, "6": exp6_zero}

if __name__ == "__main__":
    which = sys.argv[1] if len(sys.argv) > 1 else "all"
    for k in (sorted(EXPS) if which == "all" else [which]):
        EXPS[k]()
        print()
