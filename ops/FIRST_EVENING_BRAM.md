# First Evening — Bram's Counter (gameplay slice)

**Status:** scripted gameplay acceptance; no unscripted player-quality verdict
yet. No hosting decision. Gate C §7 remains untouched.

## Design question

When a newcomer walks from the Inn Between through the one IC front door
and into the Blood of the Vine, is the first meaningful conversation a generic
random quip, or does the world give them something they can ask, investigate,
and later remember?

Bram is not a quest issuer and does not have the player's omniscient situation
registry. He hears public talk at a bar, then names a tangible next action.
His spoken interpretation is not private mystery evidence or institutional
truth. A mask can ask him ordinary questions without knowing command names;
the Tavern `guide` gently indicates `talk Bram` and `ask Bram about work`.

## Player-facing path

1. **M. at the Inn** remains OOC and can orient a new mask without claiming
   in-world supernatural knowledge. `down` → `talk M.` → `east` → `south`
   crosses the front door once; the Village Square is IC.
2. **Reach Bram** by walking east from the Square. First `talk Bram` with
   this mask gets his personal invitation to ask after work, the lamp, or
   Silas. The first talk is tracked by **mask ID**, not account ID.
3. **Ask instead of receiving a task:** `ask Bram about work` starts with a
   public unresolved civic need, then points to the Commons board if no
   partner is present. `ask Bram about lamp` identifies whether diagnosis,
   procurement, or installation remains. The last stage describes the
   persistent physical change instead of offering another fake repair.
4. **A second, finite lead:** `ask Bram about Silas` reflects the
   Healer–Innkeep collaboration using real tavern stock; after resolution
   it describes the care already given without spending food again.
5. **A third path:** `ask Bram about news` points to `rumors`, but stresses
   that hearing a story and proving it are different things. Private rumor
   IDs, hidden toxicities, personal archives and substrate declarations are
   never read by Bram's public questions.
6. **Returnee:** Bram records questions as interests on the active mask.
   Returning as the same mask can produce a line about what this character
   asked and how the public situation has since changed. A second mask on
   the same account does **not** inherit the first mask's greeting or
   interests. The world continues even when that character is offline.

## Non-goals and evidence boundaries

- No new missions, levels, experience points, random task generator,
  omniscient objectives or automatic partner matching.
- No nonconsensual account attribution IC. Public case stages are public,
  whereas private rumors, hidden properties and account data remain private.
- The work is intentionally small: one conversational affordance over
  existing shared mechanics. Full-launch quest quotas (§7) are unchanged.
- Existing clean-checkout regression simulates player commands through
  **real telnet**, tests Bram's answers at several evolving case stages,
  and verifies per-mask topic continuity after server restart. This does
  **not** substitute for a fresh agent's unscripted first-session transcript,
  time-to-interaction measurement, stuck-point review, or subjective
  determination that the experience is worth playing.
- A good future test supplies a new agent only the public login banner,
  permits free exploration, then records which physical-world clue it
  noticed, whether it sought another mask, what persisted, and what the
  player wanted to do next. An empty or uninteresting answer is an honest
  failure, not an excuse to call scripts engaging.

## Test evidence links

See the PR and exact-SHA GitHub Actions run associated with this document.
No acceptance status is asserted until that run and post-merge main pass.
