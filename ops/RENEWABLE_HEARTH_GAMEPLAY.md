# The Hearth That Never Quite Goes Out — Repeatable Civic Work v0.1

**Game development only.** Host decisions and the deferred Muse first-play test
are unaffected. Gate C §7 full-launch content quotas remain unchanged.

## In-world loop

The Blood of the Vine already has a hearth and public Tavern space. The new
resource loop lets real travelers maintain it rather than handing out a new
one-shot quest or grinding XP.

| Place | Ordinary command | Observable consequence |
| --- | --- | --- |
| Village Square | `look woodpile`; `hearth` | See public stock available **today**, capped at 3 bundles |
| Village Square | `hearth gather` | Spend one finite stock unit; create one actual carryable bundle of wood in this mask's inventory |
| Village Square → Tavern | ordinary `east` (or pass wood to someone) | An object actually moves through the world |
| Blood of the Vine | `hearth deliver` | Consume one *carried* bundle into the shared rack, up to 6 bundles |
| Blood of the Vine | `hearth tend` (active Innkeep) | Spend one stored log to strengthen the public hearth for **eight village hours** |
| Tavern or Village Square | `hearth`, `look`, `look hearth` | Public status, stock and current warmth, derived from village time |
| Later day | `hearth gather` | The supply is renewed to 3 bundles/day; no retroactive accumulation or auto-fetching |

A non-Innkeep can do real useful work without choosing a false profession:
bring wood or pass a bundle. An Innkeep performs the skilled hospitality step.
Two players may work on different days because Tavern stock is persistent,
and logged-out players do not need to be present for each other's actions.

The existing tavern fire *never entirely dies*; the improved warmth is a
temporary, earned environmental condition. The player sees a deeper blaze
when fuel is spent and embers again after the eight-hour interval. No
medical recovery, mysterious NPC affinity, world-wide weather alteration or
permanent player advantage is silently inferred from that warmth.

## Authoritative state

- Source: an actual locked scenery object, `a village woodpile` in the
  Square. Its persisted day and remaining bundles are authoritative. A fresh
  day can refill to 3, never stack unclaimed deliveries or materialize stock
  again merely because a builder reruns `build_spike.py`.
- Transit: an Evennia Object, `a bundle of firewood`, with an explicit
  civic resource marker and source event provenance. It can travel normally;
  the gather command refuses to spawn a second bundle for a mask still
  carrying one. The gathering event does not alone count as a delivery.
- Destination: `The Blood of the Vine` room's bounded `civic_hearth` state,
  including reserve, game-hour end of heat, and a twelve-entry signed
  tending history. A successful `hearth deliver` deletes exactly one
  delivered bundle after crediting one unit of Tavern stock.
- Work: only a mask with the active Innkeep calling can `hearth tend`,
  only if an actual reserve bundle exists, and only once the prior eight-hour
  burn has ended. This increments `hearth_tendings` professional
  participation once per successful real action; **never auto-promotes**.
- Provenance: `civic.hearth_firewood_gathered`,
  `civic.hearth_firewood_delivered`, and `civic.hearth_tended` use the
  shared world event ledger and mark no Harbinger/Chronicle auto-publication.
  A real staff-hidden notice, independent mystery, and room-six privacy
  remain outside this mechanic.

## Acceptance

The portable `spike/tests/community_hearth_sim.py` covers stock exhaustion,
daily renewal, no rewind exploits, six-unit rack capacity, refusal to stoke
while a fire is already blazing, eight village-hour expiry, persistence on
JSON roundtrip, and bounded signed history.

The full Evennia telnet test exercises a Smith (non-Innkeep) gathering in
Square, carrying the tangible bundle to the Tavern and delivering it, then
an independent Innkeep using that one stored unit. The Smith cannot claim
Innkeep authority, delivery cannot happen at the Square, a second gather
cannot mint duplicate carried wood, and a second tend cannot create warmth
or participation from nothing. `look hearth` and the Tavern's `look`
must show the change. Post-restart assertions check the original source
decrement, spent inventory object, bounded history and profession credit.

These are *scripted mechanical tests*, not unscripted Muse play quality,
real-time public multiplayer soak, or a claim of full-launch content coverage.

## Design tradeoff and next expansion

This is intentionally one narrow, renewable shared resource. It does not
manufacture villagers' feelings about the fire or a social event around it.
A later integration could have residents choose to congregate at a stoked
hearth, consume accumulated fuel from the rack, and notice neglect, **but only
after separate causal tests prove those derived reactions are valid**.
