# NPC Simulation Handoff — Review (2026-10-01)

Reviewer: Calibos. Source: `research/npc-simulation-handoff-v0.1.md` (ChatGPT handoff v0.1, received 2026-10-01, filed byte-identical as received).

## Verdict

Adopt as the NPC architecture reference, with the corrections and gaps below. This is strong work — the core architecture (§3, layers A–K) is the same philosophy as our own: the server owns world truth, the simulation owns what characters know and want, the dialogue layer only renders. It implements our WORLD ≠ BELIEF split, rumor-as-provenance, and the no-LLM substrate tier directly. The IP audit in §1 is careful and accurate.

It is a design reference, not an implementation order. No Evennia work is authorized yet.

## Adopted without change

- **Layers A–K** (world truth → perception → belief → internal state → relationships → goals/commitments → utility → behavior trees → action → event emission → dialogue renderer). This is our architecture in game form.
- **"The low-cost simulation should remain functional with all LLM features disabled"** (§12, §31 NO-LLM MODE test). This is the single most important sentence in the document — our no-model tier as an explicit acceptance test.
- **Rumor as data object** with transmission records and provenance (§9). Directly satisfies the quest handoff's rumor-provenance requirement.
- **LOD tiers** with "simulate consequences, not unused detail" (§4).
- **Rename safety** — stable internal IDs, display name from config (§1, §31). Consistent with our true-name-unknown canon.
- **External AI players** through player-facing interfaces only, no substrate privileges (§28). Matches our substrate rules.
- **Phased sequence** (§30): identity → relationships → events/beliefs → rumors → memory → commitments → LOD → dialogue → quest feed → load test. Sensible order; Phase 9 maps to our quest grammar.
- **Mesa as offline balancing lab** (§17). Fits Jay's rapid-prototype style (cf. the 2026-09-28 sim batches). Cheap to try early, de-risks coefficient choices before they touch the live world.

## Corrections (disagreements with the handoff)

### 1. Pretorius is cleared — he is not subject to the novel-only rule
§1 says: "If the game moves to novel-source-only canon, Pretorius must be removed, replaced, or rebuilt." Our canon is **not** novel-only; it is "film grammar, novel souls," and Pretorius is explicitly cleared as the deliberate film bridge (world bible §6): a film import hunting the novel's Victor. That collision is the point. The handoff's IP rule stands for everything else, but a future implementer reading §1 cold could conclude Pretorius must be cut. **Record: Pretorius is the licensed exception; the novel-source rule applies to all other imports.**

### 2. Spelling: "Septimus" → "Septimius"
§1 uses "Dr. Septimus Pretorius" (twice). Canon spelling is **Dr. Septimius Pretorius** (bible v0.2). Correct in any derivative work.

### 3. NPCs must never perceive the OOC layer
The handoff never mentions the Inn Between. Perception filters (§3 Layer B) need an explicit IC/OOC rule: NPCs perceive the Inn as an inn, never as backstage; they cannot perceive arrivals, departures through the front door as anything but travel, OOC tells, or substrate identity. **Add as a hard perception constraint before implementation.**

### 4. The 1897 timestamps are an assumption, not canon
Example belief records use 1897 dates. Our exact year is still open (1895 or 1897 suggested). Treat 1897 in the handoff as illustrative.

### 5. Start with fewer needs than the eight listed
Layer D lists eight needs (fatigue, hunger, safety, affiliation, duty, curiosity, stress, material_security). The handoff itself says "do not begin with forty needs" — I'd go further and start with five (fatigue, hunger, safety, affiliation, duty), letting the Mesa lab justify additions. Curiosity, stress, and material_security can enter as derived or later-promoted states.

## Gaps to fill before implementation

### A. NPC departure lifecycle
The handoff has promotion upward (Tier D → A on player attention, §25) but no downward path. Ready Detective One's timed fates require NPCs to die, leave, or retire with persistent consequences. Needed: death, departure, and replacement rules — what happens to relationships, beliefs, debts, and rumors about the departed; who inherits the shop; how the village remembers. The promotion rule should be symmetric: attention promotes, absence and death demote.

### B. Chronicler integration
§27 mentions the newspaper interviewing NPCs, but not the Chronicler's developments ledger. Simulation events (deaths, broken commitments, faction shifts, rumor resolutions) need a **ledger feed**: which events are ledger-worthy, who writes them, and how NPCs learn ledger contents back as beliefs. Without this, the simulation's best output has nowhere canonical to land.

### C. Interdependence hooks
The "No one does it all" principle (bible §9) should appear in the NPC economy: NPC commitments and needs are the demand side of player crafting/trade chains (the apothecary's supplier, the smith's coal, the Harbinger's paper). §27's quest integration touches this but doesn't name the principle. When NPC needs are designed, wire them to cross-calling production chains.

### D. The apothecary example is Jekyll
The running example (apothecary, 8:00 opening, friend disappears) maps directly onto Dr. Henry Jekyll, our actual apothecary. No conflict — but note the mapping so future quest authors don't accidentally duplicate Jekyll's content seeds with a generic "apothecary" NPC.

## Tool verification (checked 2026-10-01)

- **npc-sim** (github.com/Karyabla55/npc-sim): **Apache-2.0**, real and tested (33 commits, 68 tests, seeded deterministic replay, strict invariant diagnostics). Worth studying: UtilityEvaluator, belief records with LRU caps, O(1) ring-buffer episodic memory, bounded-dict discipline. Cautions: standalone world model (zones/grid/Flask dashboard) — borrow patterns, not the framework; its README leans LLM-first ("enable_llm_for_all"), which inverts our priority — we want the utility evaluator as primary with LLM as the optional renderer.
- **openNPC** (github.com/balaraj74/openNPC): **MIT**, but only 4 commits / 2 stars, created April 2026 — very young. Ideas only (LOD engine concept, SQLite memory, async wrapper), not a dependency candidate. Its LOD intervals (100ms–1s) are combat-game timescales; our MUD cadences (§4 of the handoff) are the right scale.
- **py_trees**: mature, standard choice for the behavior-tree layer (§14). No concerns at reference level.
- **Mesa**: established agent-based modeling library; offline use only, no production dependency risk.

## Integration points with existing canon

- Quest grammar (Hook → Investigation/Action → Choice → Persistent Consequence → New Rumor) is the consumer of Phase 9's quest feed.
- The Harbinger's published accounts vs. NPC beliefs (§27) is the same mechanism as handoff v0.3's "conflicting accounts" content pattern.
- Commitment records (§3 Layer F) must survive reload and support the "keep / break / prevented" trichotomy already in quest handoff §4.
- The false-belief and source-provenance tests (§31) are the NPC-side enforcement of "inference, not buttons."

## Open decisions for Jay

1. **Primary Frankenstein edition**: 1818 (radical original) vs 1831 (Shelley's revised, more fatalistic). The handoff rightly demands one be picked and deviations recorded. Either supports Victor-as-absent-center.
2. **Whether to run a Mesa prototype now** (pre-Evennia): cheap, offline, and would validate rumor-propagation and need-balance coefficients before any server work.
3. **NPC population target at launch**: the handoff load-tests 100/500/1000 residents, but our launch village is small — the tier budgets (§25) should be sized to the actual launch roster, not the maximum.
