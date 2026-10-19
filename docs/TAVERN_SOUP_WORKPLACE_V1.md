# The Blood of the Vine: shared soup kitchen, playable slice

Status: implemented first cooking/staffed-workplace slice; validate with
`ops/tests/test_soup_state.py`, the multiplayer telnet script and
post-restart assertions. This is not a finished profession, economic system
or hotel.

## Player experience

A person can devote an evening to improving a soup recipe and never investigate
a monster. The working tavern belongs to the village, not to a mandatory player
owner; Bram's baseline pantry renews each village day and does not depend on
concurrent player employees. This is a deliberately small, *real* kitchen
within a previously traversable location, not an extra empty building.

`look soup pot` displays current pantry inventory, last batch and main-hearth
warmth. An active **Innkeep** can `soup prep turnip thyme`, or select barley
with thyme, salt or pepper. Exact stock decreases from the authoritative Tavern
room; a real packet appears in the player's hands. No stock is spontaneously
restored by a rebuild, repeated command or clock rewind. The player can leave,
log out, give the packet to a colleague or return and `soup simmer` later.
Old packets spoil after two village days.

Simmering at the pot consumes the *actual* packet and creates a physical,
transferable and edible one-serving bowl. `eat homemade soup` invokes the
existing hunger/finite-use mechanics. Food quality and flavor vary by ingredient
combination and whether someone has actively tended the Tavern's shared hearth.
Preparation and cook events are signed into the canonical world-event ledger.
The Tavern maintains a bounded public batch history, and the Innkeep keeps
a personal, persistent `soup notebook`. This is recipe experimentation, not
experience-point farming or automatic Master promotion.

An active **Merchant** in Market Lane may `soup procure` an actual kitchen
root crate, limited to two per village day. The crate can be carried or given
to a courier; at the Tavern anyone holding it may `soup deliver`, spending
that exact object and increasing turnip stock up to a physical limit.
Purchasing a license, founding a company, waiting for an online partner or
owning a building is never necessary for the basic cooking loop.

The existing Healer / Innkeep care case still uses its own real stew stock.
Do not silently count an unserved experimental soup bowl as that patient's
meal. Bridging patient food requirements, lodging requests, menus, guest
ratings, staff shifts, supplier contracts, printed recipes, paid hospitality
and NPC taste feedback are separate future slices.

## Design invariants

- Every cook is a normal in-character player command.
- No owner privileges, empty fictitious transfers, LLM simulation, or paid host.
- Ingredients are finite and their disappearance has a canonical event.
- Prepped parcels and edible results occupy actual inventories and can be given.
- The kitchen and its ledger survive logout, game process restart and rebuild.
- A lone Innkeep can prepare something without a Merchant being logged in.
- A Merchant can enrich stock without preventing the NPC baseline pantry.
- No magical capabilities or combat systems are attached to the kitchen.
- Corrections and public quality records remain attributable to real actors.
- Scarcity is limited; the simulation must not turn routine soup making
  into a starvation or server availability dependency.

## Subsequent kitchen milestones

1. Recipe notes and recorded diners' voluntary evaluations, without automatic
   ratings for absent people.
2. Durable equipment/crockery, ingredient perishability and real cellar space.
3. Shared shifts, handoff ledger, guest needs and hotel reception prototype.
4. Herald/Chronicler publication of attributed recipes, voluntary competitions,
   seasonal menus, and independent NPC orders, all with source-linked outcomes.

See `docs/TEN_CALLINGS_LIVING_VILLAGE_V1.md` for the agreed ten-Calling roadmap.
