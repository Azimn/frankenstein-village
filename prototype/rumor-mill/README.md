# Rumor-mill prototype (2026-10-01)

Deterministic, no-LLM sim of the village's rumor mechanics: event →
Chronicler ledger → Harbinger/rumor → NPC beliefs with provenance.

Run: `python3 rumor_mill.py`

## Finding

Across seeds, after ~200 NPC meetings, **confident falsehood dominates**:
nearly every NPC holds a version of the event with confidence > 0.8 and
accuracy < 100%. The truth survives on average ~5 retellings before a
slot mutates. Mechanism: per-hop mutation of *plausible nearby details*
(same category, so the wrong detail is always believable) plus
confidence that rises with every retelling, independent of accuracy —
the walkthrough effect, reproduced from two rules.

## Design implications

- The Chronicler ledger (server-owned truth) is load-bearing: without
  it, there is no "false" at all, only competing confidences.
- Provenance chains stay intact through every mutation — every false
  belief carries its teller chain, so a player *can* audit a rumor back
  to the witness. The question is whether the game ever rewards doing
  so (inference, not buttons).
- Mutation rate is the tuning knob for truth half-life: lower it near
  the Chronicler/Harbinger (institutional memory), raise it in tavern
  gossip. Different rumor ecologies per location.
- Skepticism as a trait: gullibility-gated acceptance means some NPCs
  hold out for high-confidence tellers — a natural source of
  disagreement, not consensus.

## Next

Wire the ledger diff into quest hooks: a quest fires when a rumor's
confidence crosses a threshold while its accuracy is low — the village
acts on a false belief, and the player can see it coming via the chain.
