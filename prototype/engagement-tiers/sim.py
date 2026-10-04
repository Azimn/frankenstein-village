#!/usr/bin/env python3
"""
Frankenstein Village — engagement-tier NPC prototype.

Offline design-validation sim. Pure stdlib, seeded RNG, no network, no LLM.
Tests the evolutionary NPC tier concept:

  D (crowd/transient) -> C (minor: name, schedule, template lines)
    -> B (regular: relationships, beliefs, episodic memory, goals)
    -> A (major: rich memory, commitments, personal arcs)

Player engagement promotes NPCs upward; neglect demotes them slowly;
major life events (death of kin, marriage, heroism) ratchet permanently.

Also models: 5 needs with utility-scored actions, daily schedules,
rumor propagation with source provenance + distortion, episodic memory
with salience caps and decay, genealogy, Sims-like personality traits,
and the shopkeeper exception (role-bounded complexity: transaction mode
at work, person mode off duty).

Run:  python3 sim.py        (smoke demo, 30 days, social engagement)
"""

import random
import math
import time
from collections import Counter
from dataclasses import dataclass, field

# ---------------------------------------------------------------- constants

TICKS = ["morning", "midday", "evening", "night"]
TIER_ORDER = {"D": 0, "C": 1, "B": 2, "A": 3}
MEMORY_CAP = {"D": 0, "C": 5, "B": 30, "A": 60}
NEEDS = ["fatigue", "hunger", "safety", "affiliation", "duty"]

# Promotion thresholds (hysteresis: demote threshold well below promote).
UP = {"D": 8.0, "C": 16.0, "B": 40.0}      # engage >= UP[tier] -> promote
DOWN = {"C": 1.5, "B": 8.0, "A": 22.0}     # engage < DOWN[tier] -> demote
GRACE_DAYS = 3                              # no demotion right after promotion
ENGAGE_DECAY = 0.93                         # per-day multiplier (slow neglect)

# action -> {need: relief} (positive numbers reduce the need)
RELIEF = {
    "sleep":     {"fatigue": 40},
    "eat":       {"hunger": 40},          # a real meal
    "work":      {"duty": 30},
    "serve":     {"duty": 26},               # shopkeeper transaction mode
    "socialize": {"affiliation": 24},
    "gossip":    {"affiliation": 20},
    "trade":     {"hunger": 16, "affiliation": 6, "duty": 6},
    "rest":      {"fatigue": 15},
    "tend_home": {"affiliation": 12},   # family time; NOT duty (duty = your job)
    "travel":    {},
}
# action -> {need: cost} (positive numbers increase the need)
COST = {
    "sleep":     {"hunger": 3},
    "work":      {"fatigue": 9, "hunger": 4},
    "serve":     {"fatigue": 7, "hunger": 3},
    "socialize": {"fatigue": 3},
    "gossip":    {"fatigue": 3},
    "travel":    {"fatigue": 6},
    "tend_home": {"fatigue": 2},
}
# where each action can happen; None = anywhere
WHERE = {
    "sleep": "home", "eat": None, "work": "work", "serve": "work",
    "trade": "market", "tend_home": "home",
}

OCCUPATIONS = {
    # occupation: (count, work_loc, schedule[morning, midday, evening, night], role_bound)
    "innkeeper":  (2, "inn",    ["work", "work", "work", "sleep"], False),
    "blacksmith": (2, "forge",  ["work", "work", "socialize", "sleep"], False),
    "priest":     (1, "church", ["work", "work", "tend_home", "sleep"], False),
    "farmer":     (25, "fields", ["work", "work", "tend_home", "sleep"], False),
    "shopkeeper": (4, "shop",   ["serve", "serve", "serve", "sleep"], True),
    "baker":      (3, "market", ["work", "trade", "tend_home", "sleep"], False),
    "miller":     (3, "market", ["work", "work", "tend_home", "sleep"], False),
    "laborer":    (30, "fields", ["work", "work", "socialize", "sleep"], False),
    "elder":      (6, "home",   ["rest", "socialize", "tend_home", "sleep"], False),
    "peddler":    (12, "street", ["travel", "trade", "rest", "sleep"], False),
    "traveler":   (12, "street", ["rest", "travel", "rest", "sleep"], False),
}

FIRST_M = ["Thomas", "Henry", "William", "James", "George", "Charles", "Arthur",
           "Edwin", "Albert", "Frederick", "Walter", "Harold", "Ernest", "Victor",
           "Silas", "Amos", "Elias", "Tobias", "Nathaniel", "Josiah", "Reuben",
           "Cornelius", "Barnabas", "Ezekiel", "Phineas", "Obadiah", "Rupert"]
FIRST_F = ["Mary", "Elizabeth", "Sarah", "Anna", "Martha", "Eleanor", "Clara",
           "Beatrice", "Florence", "Edith", "Agnes", "Harriet", "Lucy", "Mabel",
           "Nora", "Prudence", "Ruth", "Samantha", "Tessa", "Violet", "Winifred",
           "Ada", "Blanche", "Cora", "Dora", "Esther", "Fanny", "Gertrude"]
SURNAMES = ["Maitland", "Kettle", "Grimm", "Halloway", "Thorne", "Ashby",
            "Blackwood", "Copperfield", "Dunmore", "Ellery", "Fenwick",
            "Godwin", "Harper", "Inkwell", "Jowett", "Kershaw"]

# distortion ladders: accurate -> wild, one step per garbled retelling
DISTORT = {
    "manor_light": [
        "a blue light burned in the manor's east tower",
        "a strange light was seen at the manor",
        "someone is living in the manor again",
        "Frankenstein has returned to the manor",
        "the dead walk at the manor by night",
    ],
    "fire": [
        "a fire broke out at the forge",
        "the forge caught fire",
        "half the forge burned down",
        "the whole street nearly burned",
    ],
    "death": [
        "old {name} has died",
        "{name} was found dead",
        "{name} was taken in the night",
        "something took {name} in the night",
    ],
    "wedding": [
        "{a} and {b} are to be married",
        "{a} and {b} were wed at the church",
        "there was a wedding at the church",
        "a grand wedding has joined two families",
    ],
}

# C-tier flavor: dominant trait picks the response pool (Animal Crossing style)
LINES = {
    "sociable": ["Lovely day, isn't it?", "You must come by the tavern later!"],
    "curious": ["Did you hear about... oh, never mind.", "Strange times, friend."],
    "devout": ["The Lord watches over us.", "Say a prayer for the village."],
    "industrious": ["No rest for the working.", "Back to it, then."],
    "nervous": ["Best keep your head down.", "I don't like the look of things."],
}


# ------------------------------------------------------------------- rumor

@dataclass
class Rumor:
    rid: str
    subject: str
    claim: str
    source_actor: str
    event_id: str
    confidence: float
    gen: int = 0
    chain: list = field(default_factory=list)  # (speaker, listener, day)


@dataclass
class Belief:
    rumor: Rumor
    confidence: float
    heard_from: str
    day: int


@dataclass
class Memory:
    day: int
    kind: str
    summary: str
    salience: float
    emotion: float = 0.0


# --------------------------------------------------------------------- npc

class NPC:
    _ids = 0

    def __init__(self, world, name, occupation, tier):
        self.world = world
        self.rng = world.rng
        self.id = NPC._ids
        NPC._ids += 1
        self.name = name
        self.occupation = occupation
        self.tier = tier
        self.alive = True
        occ = OCCUPATIONS[occupation]
        self.work_loc = occ[1]
        self.schedule = occ[2]
        self.role_bound = occ[3]
        self.loc = "home"
        self.needs = {"fatigue": 20.0, "hunger": 25.0, "safety": 80.0,
                      "affiliation": 45.0, "duty": 30.0}
        self.food = 3
        # Sims-like base personality: which pool responses come from
        self.traits = {t: self.rng.random() for t in
                       ["sociable", "curious", "devout", "industrious", "nervous"]}
        self.engagement = 0.0
        self.floor = 0.0            # ratchet: life events set a permanent floor
        self.grace_until = 0
        self.habits = {}            # action -> small selection bonus
        self.memories = []          # episodic, capped by tier
        self.beliefs = {}           # rid -> Belief
        self.relationships = {}     # other_id -> dict(affinity, trust, familiarity, debt)
        self.met_players = set()    # C+: "have I met you before?"
        self.visitors = set()       # distinct player visitors, for engagement bonus
        self.family = None          # family id
        self.kin = []               # npc ids
        self.backstory = ""
        self.affect = {"fear": 0.0, "hope": 0.0, "resentment": 0.0}
        self.last_action = None
        self.action_counts = {}
        self._rest_streak = 0

    # -- schedule / role ------------------------------------------------
    def on_shift(self, tick):
        sched = self.schedule[tick]
        return sched in ("work", "serve") and self.loc == self.work_loc

    def scheduled_action(self, tick):
        return self.schedule[tick]

    # -- needs ----------------------------------------------------------
    def drift(self, tick):
        n = self.needs
        awake = self.last_action != "sleep"
        n["fatigue"] = min(100, n["fatigue"] + (4 if awake else 0))
        n["hunger"] = min(100, n["hunger"] + 5)
        n["affiliation"] = min(100, n["affiliation"] + 4)
        # duty accrues during work hours when idle
        if tick in (0, 1) and self.last_action not in ("work", "serve"):
            n["duty"] = min(100, n["duty"] + 6)
        # safety recovers at home
        if self.loc == "home":
            n["safety"] = min(100, n["safety"] + 8)
            self.affect["fear"] = max(0, self.affect["fear"] - 0.05)

    # -- utility --------------------------------------------------------
    def valid_actions(self, tick, world):
        cands = ["rest", "tend_home"]
        # only traveling occupations wander aimlessly; others move with purpose
        if "travel" in self.schedule:
            cands.append("travel")
        where_ok = lambda a: WHERE.get(a) in (None, self.loc) or \
            (WHERE.get(a) == "work" and self.loc == self.work_loc) or \
            (WHERE.get(a) == "home" and self.loc == "home")
        for a in ["sleep", "eat", "work", "serve", "trade", "socialize", "gossip"]:
            if a == "eat" and (self.food <= 0 or self.needs["hunger"] <= 45):
                continue  # don't waste a meal on a light appetite
            if a in ("socialize", "gossip") and not world.colocated(self):
                continue
            if a == "gossip" and not self.beliefs:
                continue
            if a == "serve" and not self.role_bound:
                continue
            if a == "work" and self.role_bound:
                continue
            if where_ok(a):
                cands.append(a)
        # sleep only sensible at home (or anywhere if exhausted — handled by override)
        if "sleep" in cands and self.loc != "home" and self.needs["fatigue"] < 93:
            cands.remove("sleep")
        # schedule-driven travel: get to work / get home for the night
        sched = self.scheduled_action(tick)
        if sched in ("work", "serve") and self.loc != self.work_loc:
            cands.append("travel:" + self.work_loc)
        if sched == "sleep" and self.loc != "home":
            cands.append("travel:home")
        return cands

    def score(self, action, tick):
        base = action.split(":")[0]
        s = 0.0
        tw = {"affiliation": 0.6 + 0.8 * self.traits["sociable"],
              "duty": 0.6 + 0.8 * self.traits["industrious"],
              "safety": 0.6 + 0.8 * self.traits["nervous"]}
        rest_mult = 0.6 ** self._rest_streak if base == "rest" else 1.0
        for need, amt in RELIEF[base].items():
            w = tw.get(need, 1.0)
            s += (self.needs[need] / 100.0) * amt * w * rest_mult
        for need, amt in COST.get(base, {}).items():
            w = tw.get(need, 1.0)
            s -= (self.needs[need] / 100.0) * amt * 0.7 * w
        sched = self.scheduled_action(tick)
        if base == sched:
            s += 8.0
        elif action.startswith("travel:"):
            dest = action.split(":")[1]
            # traveling toward the scheduled activity counts as keeping it;
            # getting home for the night counts double (rest is not sleep)
            if sched in ("work", "serve") and dest == self.work_loc:
                s += 8.0
            elif sched == "sleep" and dest == "home":
                s += 12.0
        s += self.habits.get(base, 0.0)
        # curious minds prefer gossip when they carry news
        if base == "gossip" and self.traits["curious"] > 0.6 and self.beliefs:
            s += 3.0
        # don't wait for an emergency to eat
        if base == "eat" and self.needs["hunger"] > 60:
            s += 5.0
        # stock up when the pantry is bare
        if base == "trade" and self.food < 3:
            s += 8.0
        s += self.rng.uniform(0, 2.0)
        return s

    def choose(self, tick, world):
        n = self.needs
        # forced overrides: survival first (Radiant-AI lesson: fence these)
        if n["fatigue"] >= 93:
            return "sleep" if self.loc == "home" else "travel:home"
        if n["hunger"] >= 90:
            if self.food > 0:
                return "eat"
            return "trade" if self.loc == "market" else "travel:market"
        # pantry bare and getting hungry: shop before it's an emergency
        if self.food == 0 and n["hunger"] > 75 and self.loc != "market":
            return "travel:market"
        if n["safety"] <= 28:
            return "travel:home" if self.loc != "home" else "rest"
        # head home in the evening while you still can (protects the night's sleep)
        if tick == 2 and self.loc != "home" and n["fatigue"] > 50:
            return "travel:home"
        best, bs = "rest", -1e9
        for a in self.valid_actions(tick, world):
            sc = self.score(a, tick)
            if sc > bs:
                best, bs = a, sc
        # bare "travel" (peddler schedule) -> wander somewhere plausible
        if best == "travel":
            return "travel:" + self.rng.choice(world.LOCATIONS)
        return best

    # -- execution ------------------------------------------------------
    def do(self, action, tick, world):
        base = action.split(":")[0]
        self.action_counts[base] = self.action_counts.get(base, 0) + 1
        world.sched_total += 1
        if base == self.scheduled_action(tick):
            world.sched_hits += 1
        # rest has diminishing returns: you can't rest away real exhaustion
        self._rest_streak = self._rest_streak + 1 if base == "rest" else 0
        self.last_action = base
        if action.startswith("travel:"):
            dest = action.split(":")[1]
            self.loc = dest
            self.needs["fatigue"] = min(100, self.needs["fatigue"] + 6)
            return
        if action == "eat":
            self.food -= 1
        if action == "trade":
            self.food = min(10, self.food + 5)  # stocking up is worthwhile
        for need, amt in RELIEF[action].items():
            self.needs[need] = max(0, self.needs[need] - amt)
        for need, amt in COST.get(action, {}).items():
            self.needs[need] = min(100, self.needs[need] + amt)
        if action in ("socialize", "gossip"):
            partner = world.random_colocated(self)
            if partner is not None:
                self.mingle(partner, world, gossip=(action == "gossip"))
        # habit formation: repeated actions get slightly easier
        self.habits[base] = min(5.0, self.habits.get(base, 0.0) + 0.05)

    def mingle(self, partner, world, gossip=False):
        # affiliation relief for both
        partner.needs["affiliation"] = max(0, partner.needs["affiliation"] - 8)
        # relationship bookkeeping at B+
        if self.tier in ("B", "A") or partner.tier in ("B", "A"):
            for a, b in ((self, partner), (partner, self)):
                if a.tier in ("B", "A"):
                    r = a.relationships.setdefault(
                        b.id, {"affinity": 0.0, "trust": 0.0,
                               "familiarity": 0.0, "debt": 0.0})
                    r["familiarity"] = min(10, r["familiarity"] + 0.3)
                    r["affinity"] = max(-10, min(10, r["affinity"] +
                        0.2 * (1 if b.traits["sociable"] > 0.5 else -0.5)))
        world.assoc[self.id].add(partner.id)
        world.assoc[partner.id].add(self.id)
        # one telling per encounter: the freshest news the partner lacks.
        # stale rumors (conf < 0.35) aren't worth retelling.
        cands = [b for rid, b in self.beliefs.items()
                 if b.confidence >= 0.35 and
                 (rid not in partner.beliefs or
                  partner.beliefs[rid].confidence < b.confidence * 0.85)]
        if not cands:
            return
        best = max(cands, key=lambda b: b.confidence)
        p = world.p_transmit * (1.35 if gossip else 1.0)
        if self.rng.random() < min(p, 0.95):
            world.transmit_rumor(best.rumor, self, partner,
                                 speaker_conf=best.confidence)

    # -- memory ---------------------------------------------------------
    def remember(self, day, kind, summary, salience, emotion=0.0,
                 novelty=0.5, goal_rel=0.3, rel_rel=0.3, danger=0.0, social=0.3):
        cap = MEMORY_CAP[self.tier]
        if cap == 0:
            return
        # handoff §6 salience weights
        s = (novelty * 0.20 + abs(emotion) * 0.20 + goal_rel * 0.20 +
             rel_rel * 0.15 + danger * 0.15 + social * 0.10)
        s = max(s, salience * 0.5)  # caller floor
        self.memories.append(Memory(day, kind, summary, s, emotion))
        if len(self.memories) > cap:
            self.memories.sort(key=lambda m: m.salience)
            dropped = self.memories[:len(self.memories) - cap]
            self.memories = self.memories[len(self.memories) - cap:]
            for d in dropped:
                self._residue(d)

    def _residue(self, mem):
        # forgotten episodes leave relationship/affect/habit traces
        if mem.emotion > 0.4:
            self.affect["hope"] = min(1, self.affect["hope"] + 0.05)
        elif mem.emotion < -0.4:
            self.affect["fear"] = min(1, self.affect["fear"] + 0.05)

    def decay_memory(self):
        kept = []
        for m in self.memories:
            m.salience *= 0.95
            if m.salience < 0.1:
                self._residue(m)
            else:
                kept.append(m)
        self.memories = kept

    def decay_beliefs(self):
        rate = 0.96 if self.tier != "D" else 0.80  # the crowd forgets fast
        for rid in list(self.beliefs):
            b = self.beliefs[rid]
            b.confidence *= rate
            if b.confidence < 0.12:
                del self.beliefs[rid]

    # -- engagement -----------------------------------------------------
    def engage(self, player, depth, day, world):
        mult = 1.0
        if self.role_bound and self.on_shift(world.tick):
            mult = 0.25  # transaction mode: all business, little depth
        self.engagement += depth * mult
        if player.pid not in self.visitors:
            self.visitors.add(player.pid)
            self.engagement += 1.0  # distinct-visitor bonus
        self.needs["affiliation"] = max(0, self.needs["affiliation"] - 6 * depth)
        if self.tier in ("C", "B", "A"):
            first = player.pid not in self.met_players
            self.met_players.add(player.pid)
            self.remember(day, "player",
                           f"{'met' if first else 'spoke with'} {player.name}"
                           f" (depth {depth})",
                           salience=0.25 + 0.2 * depth,
                           emotion=0.3, novelty=0.8 if first else 0.2,
                           rel_rel=0.8, social=0.6)

    def check_tier(self, day, world):
        """Promotion is eager; demotion is slow, graced, and ratcheted."""
        if self.tier == "A":
            if day >= self.grace_until and max(self.engagement, self.floor) < DOWN["A"]:
                self._demote(day, world)
            return
        if self.engagement >= UP[self.tier]:
            self._promote(day, world)
            return
        # D is the floor: nothing below it
        if self.tier == "D":
            return
        if day >= self.grace_until and max(self.engagement, self.floor) < DOWN[self.tier]:
            self._demote(day, world)

    def _promote(self, day, world):
        old = self.tier
        self.tier = {"D": "C", "C": "B", "B": "A"}[old]
        self.grace_until = day + GRACE_DAYS
        self._last_promote_day = day
        if not self.backstory:
            self.backstory = world.make_backstory(self)
        world.log.append((day, "promote", self.id, self.name, old, self.tier))
        world.churn[self.id] = world.churn.get(self.id, 0) + 1
        self.remember(day, "milestone", f"became a {self.tier}-tier resident",
                      salience=0.8, emotion=0.6, novelty=1.0, social=0.8)

    def _demote(self, day, world):
        old = self.tier
        self.tier = {"C": "D", "B": "C", "A": "B"}[old]
        self.grace_until = day + GRACE_DAYS
        # trim memory to the new cap immediately (residues remain)
        cap = MEMORY_CAP[self.tier]
        if len(self.memories) > cap:
            self.memories.sort(key=lambda m: m.salience)
            for d in self.memories[:len(self.memories) - cap]:
                self._residue(d)
            self.memories = self.memories[len(self.memories) - cap:]
        world.log.append((day, "demote", self.id, self.name, old, self.tier))
        world.churn[self.id] = world.churn.get(self.id, 0) + 1
        if day - getattr(self, "_last_promote_day", -999) <= 5:
            world.yo_yos += 1
        self._last_promote_day = -999  # consumed; a fresh promote restarts it

    # floor value -> lowest tier it locks in
    RATCHET_TIER = {6.0: "C", 10.0: "C", 18.0: "B"}

    def ratchet(self, floor, day, world):
        """A major life event: the floor never decays, and the NPC is
        immediately recognized at the floor's tier (the village hero is
        suddenly a somebody)."""
        self.floor = max(self.floor, floor)
        want = self.RATCHET_TIER[floor]
        if TIER_ORDER[self.tier] < TIER_ORDER[want]:
            old = self.tier
            self.tier = want
            self.grace_until = day + GRACE_DAYS
            self._last_promote_day = day
            if not self.backstory:
                self.backstory = world.make_backstory(self)
            world.log.append((day, "ratchet", self.id, self.name, old, want))
            world.churn[self.id] = world.churn.get(self.id, 0) + 1


# ------------------------------------------------------------------ player

class Player:
    _ids = 0

    def __init__(self, name):
        self.pid = Player._ids
        Player._ids += 1
        self.name = name
        self.met = set()  # npc ids
        self.visits = Counter()  # npc id -> times visited (regulars!)


# ------------------------------------------------------------------- world

class World:
    OUTDOORS = {"street", "well", "market", "fields"}
    LOCATIONS = ["home", "inn", "forge", "church", "fields", "market",
                 "shop", "tavern", "street", "well"]

    def __init__(self, seed=1, n_players=6, pattern="social",
                 p_transmit=0.45, mutate_prob=0.22, events=True):
        self.rng = random.Random(seed)
        self.seed = seed
        self.pattern = pattern
        self.p_transmit = p_transmit
        self.mutate_prob = mutate_prob
        self.events_on = events
        self.day = 0
        self.tick = 0
        self.npcs = []
        self.players = [Player(f"player_{i}") for i in range(n_players)]
        self.rumors = {}          # rid -> Rumor
        self.assoc = {}           # npc_id -> set of npc_ids (met via mingling)
        self.log = []             # (day, kind, npc_id, name, old, new)
        self.yo_yos = 0
        self.history = []         # per-day metrics
        self.action_totals = {}
        self.starve_ticks = 0     # ticks any npc spent at hunger>=95
        self.starve_by_occ = {}   # occupation -> starve ticks
        self.churn = {}           # npc_id -> tier-change count
        self.sched_hits = 0       # ticks where action matched schedule
        self.sched_total = 0
        self._rid = 0
        self._build()
        self.favorites = self.rng.sample([n.id for n in self.npcs[:40]], 10)

    # -- construction ---------------------------------------------------
    def _build(self):
        NPC._ids = 0
        Player._ids = 0
        # initial tier mix: 2 A, 8 B, 66 C, 24 D
        tiers = (["A"] * 2 + ["B"] * 8 + ["C"] * 66 + ["D"] * 24)
        occs = []
        for occ, (count, *_rest) in OCCUPATIONS.items():
            occs += [occ] * count
        self.rng.shuffle(occs)
        self.rng.shuffle(tiers)
        # D tier must be peddlers/travelers; A/B get settled occupations
        for i, tier in enumerate(tiers):
            occ = occs[i]
            if tier == "D" and occ not in ("peddler", "traveler", "laborer"):
                occ = self.rng.choice(["peddler", "traveler"])
            if tier in ("A", "B") and occ in ("peddler", "traveler"):
                occ = self.rng.choice(["innkeeper", "blacksmith", "shopkeeper",
                                       "baker", "farmer"])
            male = self.rng.random() < 0.5
            name = (self.rng.choice(FIRST_M) if male else self.rng.choice(FIRST_F)) \
                + " " + self.rng.choice(SURNAMES)
            npc = NPC(self, name, occ, tier)
            npc.loc = self.rng.choice(["home", npc.work_loc, "street", "tavern"])
            self.npcs.append(npc)
            self.assoc[npc.id] = set()
        self.by_id = {n.id: n for n in self.npcs}
        # seed engagement so initial A/B don't instantly demote;
        # everyone gets launch grace (day-0 demotions would be authorial noise)
        for n in self.npcs:
            n.grace_until = 5
            if n.tier == "A":
                n.engagement = 45.0
            elif n.tier == "B":
                n.engagement = 20.0
            elif n.tier == "C":
                n.engagement = 2.0
            n.backstory = self.make_backstory(n)
        # genealogy: 12 families, instant history for generated NPCs
        fams = {}
        for n in self.npcs:
            fam = self.rng.randrange(12)
            n.family = fam
            fams.setdefault(fam, []).append(n.id)
        for n in self.npcs:
            mates = [i for i in fams[n.family] if i != n.id]
            n.kin = self.rng.sample(mates, min(len(mates), 4))

    def make_backstory(self, npc):
        bits = [f"{npc.occupation}"]
        if npc.kin:
            k = self.by_id[self.rng.choice(npc.kin)]
            bits.append(f"kin of {k.name}")
        dom = max(npc.traits, key=npc.traits.get)
        bits.append(f"{dom} by nature")
        return "; ".join(bits)

    def colocated(self, npc):
        return [o for o in self.npcs
                if o.alive and o is not npc and o.loc == npc.loc]

    def random_colocated(self, npc):
        c = self.colocated(npc)
        return self.rng.choice(c) if c else None

    # -- rumors -----------------------------------------------------------
    def seed_rumor(self, subject, witnesses, event_id, claim=None, conf=0.95):
        self._rid += 1
        rid = f"R{self._rid}"
        claim = claim or DISTORT[subject][0]
        rumor = Rumor(rid, subject, claim, "world", event_id, conf)
        self.rumors[rid] = rumor
        for n in witnesses:
            n.beliefs[rid] = Belief(rumor, conf, "witnessed", self.day)
            n.remember(self.day, "event", f"witnessed: {claim}",
                       salience=0.85, emotion=-0.4 if subject in
                       ("fire", "death") else 0.4,
                       novelty=0.9, danger=0.8 if subject in
                       ("fire", "death") else 0.2, social=0.7)
        return rumor

    def transmit_rumor(self, rumor, speaker, listener, speaker_conf):
        mp = self.mutate_prob + (0.15 if speaker.traits["nervous"] > 0.7 else 0)
        ladder = DISTORT[rumor.subject]
        claim = rumor.claim
        if self.rng.random() < mp and claim in ladder \
                and ladder.index(claim) < len(ladder) - 1:
            claim = ladder[ladder.index(claim) + 1]  # garbled retelling
        nr = Rumor(rumor.rid, rumor.subject, claim, speaker.name,
                   rumor.event_id, speaker_conf * 0.85, rumor.gen + 1,
                   rumor.chain + [(speaker.name, listener.name, self.day)])
        conf = speaker_conf * 0.85
        listener.beliefs[rumor.rid] = Belief(nr, conf, speaker.name, self.day)
        listener.remember(self.day, "rumor", f"heard: {claim} (via {speaker.name})",
                          salience=0.4, emotion=0.1, novelty=0.6, social=0.6)

    # -- events -------------------------------------------------------------
    def fire_events(self):
        key = (self.day, self.tick)
        if not self.events_on:
            return
        if key == (5, 2):  # the manor light
            # a 41-second light: only a handful happen to be looking up.
            # everyone else must hear it through gossip — that's the experiment.
            outdoors = [n for n in self.npcs if n.alive and n.loc in self.OUTDOORS]
            wit = self.rng.sample(outdoors, min(8, len(outdoors)))
            self.seed_rumor("manor_light", wit, "EVT_MANOR_LIGHT")
        elif key == (12, 1):  # fire at the forge
            present = [n for n in self.npcs if n.alive and n.loc == "forge"]
            for n in present:
                n.needs["safety"] = max(0, n.needs["safety"] - 45)
            if present:
                hero = self.rng.choice(present)
                hero.ratchet(18.0, self.day, self)  # heroism: B locked forever
                hero.remember(self.day, "milestone",
                              "pulled someone from the forge fire",
                              salience=1.0, emotion=0.7, novelty=1.0,
                              danger=1.0, social=1.0)
                self.seed_rumor("fire", present, "EVT_FORGE_FIRE")
        elif key == (18, 0):  # an elder dies
            cands = [n for n in self.npcs
                     if n.alive and n.tier == "C" and n.occupation == "elder"]
            cands = cands or [n for n in self.npcs if n.alive and n.tier == "C"]
            if cands:
                dead = self.rng.choice(cands)
                dead.alive = False
                for n in self.npcs:
                    if n.alive and dead.id in n.kin:
                        n.ratchet(6.0, self.day, self)  # grief: C locked forever
                        n.affect["fear"] = min(1, n.affect["fear"] + 0.3)
                        n.remember(self.day, "milestone",
                                   f"{dead.name} has died",
                                   salience=1.0, emotion=-0.9, novelty=0.9,
                                   rel_rel=1.0, social=0.9)
                finders = self.rng.sample([n for n in self.npcs if n.alive], 3)
                claim = DISTORT["death"][0].format(name=dead.name)
                self.seed_rumor("death", finders, "EVT_DEATH", claim=claim)
        elif key == (22, 2):  # a wedding
            cands = [n for n in self.npcs if n.alive and n.tier == "C"]
            if len(cands) >= 2:
                a, b = self.rng.sample(cands, 2)
                for n in (a, b):
                    n.ratchet(10.0, self.day, self)  # marriage: C locked forever
                    n.needs["affiliation"] = 0
                    n.remember(self.day, "milestone",
                               f"married {b.name if n is a else a.name}",
                               salience=1.0, emotion=0.9, novelty=1.0,
                               rel_rel=1.0, social=1.0)
                guests = self.rng.sample([n for n in self.npcs if n.alive],
                                         min(8, len([n for n in self.npcs if n.alive])))
                claim = DISTORT["wedding"][0].format(a=a.name, b=b.name)
                self.seed_rumor("wedding", guests, "EVT_WEDDING", claim=claim)

    # -- players ------------------------------------------------------------
    def player_visits(self):
        if self.pattern == "none":
            return
        for p in self.players:
            n_visits = 1 + (1 if self.rng.random() < 0.4 else 0)
            for _ in range(n_visits):
                target = self._pick_target(p)
                if target is None:
                    continue
                depth = self.rng.choices([1, 2, 3], weights=[0.5, 0.35, 0.15])[0]
                target.engage(p, depth, self.day, self)
                p.met.add(target.id)
                p.visits[target.id] += 1

    def _pick_target(self, p):
        alive = [n for n in self.npcs if n.alive]
        if not alive:
            return None
        if self.pattern == "concentrated":
            pool = [self.by_id[i] for i in self.favorites if self.by_id[i].alive]
            w = [3 if i < 3 else 1 for i in range(len(pool))]
            return self.rng.choices(pool, weights=w)[0]
        if self.pattern == "diffuse":
            return self.rng.choice(alive)
        # social: revisit the known (preferential attachment — regulars),
        # meet friends-of-friends while the inner circle is small,
        # sometimes wander. Creatures of habit: the circle caps ~15.
        if p.met and self.rng.random() < 0.85:
            known = [self.by_id[i] for i in p.met if self.by_id[i].alive]
            friends = []
            if len(p.met) < 15:
                fset = set()
                for k in known:
                    fset.update(self.assoc[k.id])
                fset -= p.met
                friends = [self.by_id[i] for i in fset
                           if self.by_id[i].alive]
            pool = friends or known
            # superlinear preferential attachment: favorites emerge, tail survives
            weights = [(1 + p.visits[n.id]) ** 1.5 for n in pool]
            return self.rng.choices(pool, weights=weights)[0]
        return self.rng.choice(alive)

    # -- main loop ------------------------------------------------------------
    def step(self):
        self.fire_events()
        if self.tick in (0, 1, 2):
            self.player_visits()
        order = [n for n in self.npcs if n.alive]
        self.rng.shuffle(order)
        for n in order:
            n.drift(self.tick)
            if n.needs["hunger"] >= 95:
                self.starve_ticks += 1
                self.starve_by_occ[n.occupation] = \
                    self.starve_by_occ.get(n.occupation, 0) + 1
            action = n.choose(self.tick, self)
            n.do(action, self.tick, self)
            base = action.split(":")[0]
            self.action_totals[base] = self.action_totals.get(base, 0) + 1
        self.tick += 1
        if self.tick == 4:
            self.tick = 0
            self.end_of_day()

    def end_of_day(self):
        for n in self.npcs:
            if not n.alive:
                continue
            n.engagement *= ENGAGE_DECAY
            n.decay_memory()
            n.decay_beliefs()
            n.check_tier(self.day, self)
        self.snapshot()
        self.day += 1

    def snapshot(self):
        tiers = {t: 0 for t in TIER_ORDER}
        es = []
        for n in self.npcs:
            if n.alive:
                tiers[n.tier] += 1
                es.append(n.engagement)
        aware = {}
        for rid, r in self.rumors.items():
            aware[r.subject] = sum(1 for n in self.npcs
                                   if n.alive and rid in n.beliefs)
        self.history.append({
            "day": self.day, "tiers": tiers, "gini": gini(es),
            "mean_e": sum(es) / len(es) if es else 0,
            "max_e": max(es) if es else 0,
            "rumor_aware": aware,
        })

    def run(self, days=30, verbose=False):
        t0 = time.perf_counter()
        while self.day < days:
            self.step()
        self.wall = time.perf_counter() - t0
        if verbose:
            print(f"seed={self.seed} pattern={self.pattern} "
                  f"days={days} wall={self.wall:.2f}s")

    # -- reporting ------------------------------------------------------------
    def tier_counts(self):
        return self.history[-1]["tiers"] if self.history else {}

    def rumor_report(self):
        out = []
        for rid, r in self.rumors.items():
            aware = [n for n in self.npcs
                     if n.alive and rid in n.beliefs]
            claims = {}
            gens, confs = [], []
            for n in aware:
                b = n.beliefs[rid]
                claims[b.rumor.claim] = claims.get(b.rumor.claim, 0) + 1
                gens.append(b.rumor.gen)
                confs.append(b.confidence)
            out.append({
                "rid": rid, "subject": r.subject,
                "aware": len(aware),
                "variants": len(claims),
                "claims": claims,
                "max_gen": max(gens) if gens else 0,
                "mean_conf": sum(confs) / len(confs) if confs else 0,
            })
        return out

    def memory_report(self):
        mx = {t: 0 for t in TIER_ORDER}
        total = 0
        for n in self.npcs:
            if n.alive:
                mx[n.tier] = max(mx[n.tier], len(n.memories))
                total += len(n.memories)
        return mx, total


def gini(xs):
    xs = sorted(x for x in xs if x >= 0)
    n = len(xs)
    if n == 0 or sum(xs) == 0:
        return 0.0
    s = sum(xs)
    return (2 * sum((i + 1) * x for i, x in enumerate(xs)) / (n * s)) - (n + 1) / n


if __name__ == "__main__":
    w = World(seed=1, pattern="social")
    w.run(days=30, verbose=True)
    print("final tiers:", w.tier_counts())
    print("promotions/demotions:", len([l for l in w.log if l[1] == "promote"]),
          len([l for l in w.log if l[1] == "demote"]), "yo-yos:", w.yo_yos)
    for r in w.rumor_report():
        print(r["subject"], "aware:", r["aware"], "variants:", r["variants"],
              "max_gen:", r["max_gen"], f"mean_conf: {r['mean_conf']:.2f}")
    print("memory max/total:", w.memory_report())
    print("starve ticks:", w.starve_ticks)
