"""Rumor-mill prototype: the walkthrough that colonized its own documentation.

Design question (from the Shade sessions): the published walkthrough
confidently documents a 'take tickets' step that does not exist in the
game — misdirection colonized its own documentation. For the village,
the design note says: let NPC needs drive them, and let the rumor-mill
confidently assert things that are not true.

This prototype asks: given a true event and a chain of retellings with
small per-hop mutation, how fast does a confident-but-false rumor
outrun the truth, and what does provenance buy us?

Mechanics:
- World truth: one event with discrete slots (who, where, what, when).
- Chronicler ledger: append-only truth log (server owns world truth).
- NPCs: each has a need level (curiosity) and a gullibility; when two
  NPCs meet, the teller retells a rumor with per-slot mutation chance;
  the listener records the rumor WITH provenance (chain of tellers).
- Confidence: each retelling bumps the rumor's asserted confidence; the
  walkthrough effect = confidence decoupled from accuracy.

Experiment: run N meetings, then compare each NPC's belief about the
event against the ledger. Report: fraction holding the true version,
fraction holding a false version with confidence > 0.8, and mean
provenance-chain length of false beliefs.

Deterministic: seeded RNG, no LLM, no model tier. Part of the NO-LLM-MODE
acceptance posture: the sim must be playable/analyzable with models
disabled.
"""

from __future__ import annotations

import random
from dataclasses import dataclass, field


@dataclass
class Event:
    who: str
    where: str
    what: str
    when: str

    def slots(self):
        return {"who": self.who, "where": self.where,
                "what": self.what, "when": self.when}


@dataclass
class Rumor:
    """A belief about an event, with provenance.

    confidence is asserted certainty (the walkthrough effect: it grows
    with retellings regardless of accuracy). chain lists tellers in
    order; the Chronicler ledger is ground truth, not a chain link.
    """
    slots: dict
    confidence: float
    chain: list = field(default_factory=list)

    def accuracy(self, truth: Event) -> float:
        t = truth.slots()
        return sum(1 for k in t if self.slots.get(k) == t[k]) / len(t)


@dataclass
class NPC:
    name: str
    curiosity: float   # 0..1: how eagerly they retell
    gullibility: float  # 0..1: how readily they accept (skip verification)
    belief: Rumor | None = None


# The village's small vocabulary of plausible mutations: rumor drift is
# not random noise, it is *plausible* noise — the wrong detail is always
# a nearby one (same category), which is why false rumors are believed.
MUTATIONS = {
    "who": ["the miller", "the blacksmith", "a stranger", "the innkeep",
            "the doctor's assistant"],
    "where": ["the mill", "the churchyard", "the well", "the crossroads",
              "the dark shop"],
    "what": ["took the silver", "broke the truce", "lit a lantern",
             "dug at midnight", "left a crate"],
    "when": ["at dusk", "at midnight", "before dawn", "during the bell"],
}


def retell(rumor: Rumor, teller: NPC, rng: random.Random,
           mutate_p: float = 0.18) -> Rumor:
    """Retell with per-slot mutation chance, scaled by teller curiosity.

    Curious tellers embellish more. Confidence always rises with
    retelling — the walkthrough effect: each teller asserts a little
    more surely than the last, independent of accuracy.
    """
    new_slots = dict(rumor.slots)
    for slot, options in MUTATIONS.items():
        p = mutate_p * (0.5 + teller.curiosity)
        if rng.random() < p:
            choices = [o for o in options if o != new_slots[slot]]
            new_slots[slot] = rng.choice(choices)
    return Rumor(
        slots=new_slots,
        confidence=min(1.0, rumor.confidence + 0.08 + 0.1 * teller.curiosity),
        chain=rumor.chain + [teller.name],
    )


def meet(a: NPC, b: NPC, rng: random.Random) -> None:
    """One encounter: whoever has a rumor (and feels like talking) tells."""
    for teller, listener in ((a, b), (b, a)):
        if teller.belief is None:
            continue
        if rng.random() > 0.3 + 0.7 * teller.curiosity:
            continue  # didn't feel like talking
        heard = retell(teller.belief, teller, rng)
        if listener.belief is None or rng.random() < listener.gullibility:
            # Gullible listeners take the new version; skeptical ones
            # keep their own unless the teller sounds very sure.
            if listener.belief is None or heard.confidence > listener.belief.confidence + 0.2:
                listener.belief = heard
                return


def run(seed: int = 7, npcs: int = 12, meetings: int = 200,
        witness_hears_truth: bool = True) -> dict:
    rng = random.Random(seed)
    truth = Event(who="the miller", where="the well",
                  what="broke the truce", when="at midnight")
    # The Chronicler ledger: append-only truth. NPCs never read it
    # directly (belief != truth); the Harbinger reads it to seed rumors.
    ledger = [("t0", truth)]

    people = [NPC(name=f"npc-{i:02d}",
                  curiosity=rng.random(),
                  gullibility=0.35 + 0.6 * rng.random())
              for i in range(npcs)]
    # One witness saw the true event; the rumor starts from them.
    witness = people[0]
    witness.belief = Rumor(slots=truth.slots(), confidence=0.5,
                           chain=["witness"])
    others = people[1:]

    for _ in range(meetings):
        a, b = rng.sample(people, 2)
        meet(a, b, rng)

    holders = [p for p in others if p.belief is not None]
    true_holders = [p for p in holders
                    if p.belief.accuracy(truth) == 1.0]
    confident_false = [p for p in holders
                       if p.belief.accuracy(truth) < 1.0
                       and p.belief.confidence > 0.8]
    false_chains = [len(p.belief.chain) for p in holders
                    if p.belief.accuracy(truth) < 1.0]
    return {
        "n": npcs, "meetings": meetings,
        "with_belief": len(holders),
        "hold_true": len(true_holders),
        "confident_false": len(confident_false),
        "mean_false_chain": (sum(false_chains) / len(false_chains)
                             if false_chains else 0.0),
        "sample_false": next((p.belief for p in confident_false), None),
    }


if __name__ == "__main__":
    for seed in (7, 8, 9):
        r = run(seed=seed)
        print(f"seed {seed}: {r['with_belief']}/{r['n']-1} hold a belief, "
              f"{r['hold_true']} true, {r['confident_false']} confidently "
              f"false (conf>0.8), mean false chain {r['mean_false_chain']:.1f}")
        if r["sample_false"]:
            s = r["sample_false"]
            print(f"   e.g. {s.slots} conf={s.confidence:.2f} "
                  f"chain={' -> '.join(s.chain[:4])}... "
                  f"({len(s.chain)} links)")
