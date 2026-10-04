# Frankenstein Village — Content Generation Packet v0.1

How to use: feed one content family (§8) per generation run, with §§2–7 as
the standing constraints. Every batch is audited against the acceptance
tests (§10) before it enters canon. A failed batch is regenerated, not
repaired — never edit generated content into compliance by hand-waving;
either it meets the tests or it goes back.

Canon sources: `files/frankenstein-village-world-bible-v0.2.md`,
`files/frankenstein-village-quest-handoff-v0.3.md`,
`files/new-arrivals-guide-v0.2.md`.

---

## 1. The setting in one paragraph

A remote 1890s village beneath a manor, stitched together from
public-domain Victorian novels — Stoker, Shelley (1818), Stevenson,
Wilde, Doyle, and others. Mystery, not horror. The tone is dread as
weather: ordinary life, strange rumors, questions that outlive their
answers. The village's true name is contested; outsiders call it
Frankenstein Village. Victor Frankenstein is the absent center.
Dr. Septimius Pretorius is hunting him from afar — his leased shop
stands fitted-out but dark, OPENING SOON, a crate ticking inside.

## 2. Originality constraints (non-negotiable)

- Every mechanism must be traceable to the Source Shelf (13
  public-domain novels in the bible appendix) or be original
  composition. "Film grammar, novel souls."
- No direct quotations from any film. No Universal proper nouns
  (no "Darkmoor," no Dark Universe lore).
- One licensed exception: **Dr. Septimius Pretorius** is the deliberate
  film bridge. He is absent at launch (see §1). Do not invent other
  film imports.
- Modern adaptations may appear in a private influences note, never in
  canon-facing content.
- Stricter second audit still pending — when in doubt, file the
  questionable element under "flag for audit" rather than using it.

## 3. Tone filter

- Mystery over horror. Rumors over jump scares.
- Existential dread is weather, not plot. Ordinary life supplies stakes.
- Inference, not buttons: no one hands the player the answer; examining,
  witnessing, and testimony are the verbs of discovery.
- Questions often outlive answers. A good rumor is still interesting
  when unresolved.
- Holmes exists as rumor only — never on screen until earned.

## 4. Quest grammar and priorities

Every quest follows: **Hook → Investigation/Action → Choice →
Persistent Consequence → New Rumor.**

Priorities, in order: (1) fun game, (2) living world, (3) experiment.
On close human-fun vs. AI-engagement calls, lean AI — unless humans
would be locked out or the game becomes joyless/unplayable.

- No click-to-solve quests. No inert social values (a social stat that
  does nothing is a lie — cut it or mechanize it).
- Travel costs time. Choices close doors.
- No automatic deduction: the game never assembles the answer for the
  player (Ready Detective One rule).
- No premature finales: don't spend the mystery early.

## 5. No one does it all (interdependence)

- Broad participation, limited simultaneous mastery. A player may learn
  many things but master few at once.
- Crafting and investigation chains must cross-call: the poison-maker
  needs the herbalist's knowledge, the apothecary's tools, a supplier.
- Assistants, apprentices, patrons, suppliers, witnesses, and
  institutions are first-class quest roles — not filler.
- Never design a hard population deadlock: no quest may require a
  specific other *player* to be present. NPCs, letters, ledgers, and
  institutions can stand in.
- Respecialization keeps history: changing calling never erases what
  was learned or done.

## 6. Object contract

Every object is **flavor text + at most 3 mechanical tags** from this pool:

`harm` (instant damage) · `toxin` (damage over time: amount + ticks) ·
`mend` (heals) · `ward` (protection) · `holds` (container capacity) ·
`fuel` (burns) · `uses` (charges/durability) · `worth` (economic value) ·
`perish` (spoils over time) · `tale` (grants information when read) ·
`hidden:<tag>` (a mechanical tag `look` does not reveal)

- Tags are the physics; text is the weather. The sim reads only tags.
- Hidden tags are discovered via skilled examination, risky tasting,
  witnessing, or rumor — never by `look`.
- Examples: apple = mend(2) + perish. Poison apple = apple +
  hidden:toxin. Lamp oil = fuel + portable(flavor). Locket =
  portable + worth(5) + flavor ("warm, engraved E.L.").
- harm/toxin exist (fire burns, poison kills) but there is **no combat
  system at launch** — conflict is ritualized (debate, duels, honor,
  debts).

## 7. NPC and mortality constraints

- Assume mostly Tier D/C villagers (schedules + phrase banks + needs);
  a few Tier B. Content must work when every NPC is running the
  no-model fallback.
- **Anyone can die.** No quest may depend on one specific NPC's
  survival. Every quest-critical role needs a successor, an heir, a
  ledger, or a rival who inherits the thread.
- NPCs never perceive the OOC layer. To them the Inn Between is an inn.
- Deaths, departures, and major events feed the Chronicler's ledger →
  the Harbinger's account (possibly distorted) → rumor propagation.
  Write content with its *legend pipeline* in mind: what does the
  village say about this next week?

## 8. Content families

Generate **one family per run**. Quotas are targets, not promises.

1. **Rumor seeds (250).** One-to-three-sentence village talk with a
   provenance hook (who started it, who benefits). Must admit 2–3
   live variants — distortion-ready.
2. **Ambient events (300).** Small observable happenings (a light in
   the manor, 41 seconds; a dog that won't cross the square). No
   mechanics, just seeds for gossip. Witness counts stay small (≤8).
3. **Incident templates (75).** Reusable skeletons: disappearance,
   theft, strange illness, disputed debt, uncanny sighting. Each with
   3+ variant slots and a consequence branch.
4. **NPC line banks.** Tier D phrase pools per role (shopkeeper,
   farmer, fisher, maid, etc.): greetings, weather talk, deflections,
   work talk. Transaction-mode lines vs. person-mode lines for
   role-bounded NPCs.
5. **Crafting chains (40).** Property-transformation recipes honoring
   §5: each chain crosses at least two callings.
6. **Chronicle hooks (50).** Ledger-ready event summaries written as
   the Chronicler would — the village's official memory, slightly
   wrong in interesting ways.

## 9. Anti-patterns (reject on sight)

Free travel · inert social values · premature finales ·
exhaustive-dialogue strategies (talking to everyone shouldn't solve
it) · automatic hypotheses · click-to-solve · one-NPC load-bearing
plots · combat stats or combat-dependent content · modern language in
villager mouths · jump-scare writing · answers handed to the player.

## 10. Acceptance tests (audit checklist)

- [ ] Quest grammar present: hook → investigation → choice →
      consequence → new rumor.
- [ ] No single NPC's survival is load-bearing.
- [ ] Object tags ≤3, all from the §6 pool; hidden tags discoverable
      only via §6 means.
- [ ] Interdependence: any chain longer than 2 steps crosses callings.
- [ ] Tone filter (§3) holds; originality constraints (§2) hold.
- [ ] Travel/time cost acknowledged where relevant; at least one
      choice closes a door.
- [ ] Legend pipeline considered: what does the village say next week?

## 11. Batch output format

Numbered items. Each item: the content, then a one-line `AUDIT:` note
stating which acceptance tests it satisfies and any flags. Keep flavor
text vivid but compact — the renderer, not the generator, owns the
final prose.
