# FRANKENSTEIN VILLAGE

## Launch Content and Quest Production Handoff v0.3

**Developer and Content Team Working Document**

*Date: 2026-10-01*

*Source authority: FRANKENSTEIN VILLAGE World Bible v0.2 plus the launch-content blueprint from the current design session*

*Status: Production handoff. New titles, NPC details, event outcomes, and location names in this document are working content only until promoted into the World Bible.*

> Canon rule: the World Bible is authoritative. This handoff may create rumors, provisional explanations, false beliefs, and working names, but it must not quietly settle open canon questions.

**Revision v0.2 — 2026-10-01.** Aligned with the morning's design decisions. What changed:

- The absent center is **Victor Frankenstein** — the novel's name, not the film's "Henry." Three seeds renamed accordingly.
- **Pretorius is not present at launch.** His curiosity shop stands leased, fitted out, and dark, with an OPENING SOON sign in the window. Every reference to him in this document now works through his *absence* — letters in immaculate handwriting, standing orders, gossip about the leaseholder — or is explicitly marked post-launch.
- Added the **interdependence principle** to §1 and the **AI-lean design note** to the substrate rule.

Nothing else in the seed bank changed. The content was already built for this canon.

**Revision v0.3 — 2026-10-01: originality pass.** "Darkmoor" was Universal's name — cut everywhere. The working title is now **"Frankenstein Village"** throughout (what outsiders call it; the true name is contested — see the bible). The war is now the **War of the Well** and the peace the **Truce of the Well** (terms carved on the steaming well; the bible carries the rewritten inscription). No other content changed.

**Purpose. **This document converts the Frankenstein Village design into a large implementation backlog for a launch-ready text MMO. It defines the content grammar, gives a standard quest packet, and supplies a broad bank of authored quests, repeatable activities, incidents, rumors, location states, NPC material, community projects, discoveries, and event frameworks.

**Design target. **A player should be able to log in without a plan, discover that something changed, hear several plausible leads, choose one, involve other people, make a decision, alter some persistent state, and log out with at least one unresolved intention for next time.


# Contents

1. Production principles and non-negotiables
2. Quest object and state model
3. Launch content families and example bank
4. Calling content packs
5. World-event, ambient, location, and NPC content
6. Full implementation packets
7. Launch inventory targets and acceptance tests
# 1. Production Principles and Non-Negotiables

**Frankenstein Village is a social world first. **The content system should generate conversation, observation, coordination, disagreement, favors, social memory, and return visits before it generates combat. A quest that could be transplanted unchanged into a generic fantasy MMO is not finished.

**The world continues without the player. **Every major authored quest must define what happens if nobody intervenes. Timed state changes, NPC schedules, rival action, newspaper publication, weather, and disappearance of evidence are not optional flavor. They are part of the simulation.

**Rumor is a first-class mechanic. **Players usually encounter beliefs, reports, accusations, advertisements, testimony, and gossip rather than objective database truth. Provenance matters. A confident NPC can be wrong.

**Inference, not buttons. **Evidence should support theories without automatically naming the correct explanation. No single inspect command should collapse a mystery into its answer. When a clue is decisive, obtaining or interpreting it should itself require meaningful work.

**Consequences persist. **The usual endpoint is not a reward screen. It is a changed relationship, a new debt, an altered schedule, a published story, an opened route, a lost opportunity, a relocated NPC, a faction response, or a new rumor.

**Ordinary life is the stakes. **At least half of routine play should remain understandable as village life even if every supernatural proper noun were temporarily removed. The bakery, press, church, apothecary, workshops, council, streets, lodging, deliveries, funerals, markets, and arguments make the extraordinary matter.

**No one does it all.** Mastery is capped: a character cannot master every craft, calling, or discipline at once, and serious work crosses callings by design — the smith needs the apothecary's reagents, the healer needs the smith's instruments, the scholar needs the merchant's imports. Scientists have assistants; hunters have beaters; patrons have clients. Apprentices, assistants, and patrons are first-class relations, not flavor. If everyone is self-sufficient, there is no social game.

**No substrate-specific privilege. **Humans and AI players use the same world verbs and receive the same in-world treatment. Design activities whose time scale or cognitive demands naturally favor different play styles, but never encode an in-world AI bonus or human bonus. *(Design note, 2026-10-01: where a design decision must favor one player type's engagement over the other's, lean AI — unless it would make the game joyless for humans. This is a tiebreak in design, never an in-world bonus, and never a marker.)*

**Mystery compounds instead of escalating to exhaustion. **Many chains should end with a better question rather than a boss fight. Persistent uncertainty is a feature when players can still make local decisions and see local consequences.

> Default quest grammar: Hook -> Investigation or Action -> Choice -> Persistent Consequence -> New Rumor.

## Content anti-patterns

| **Avoid** | **Replace with** |
|---|---|
| Quest marker over an NPC | A rumor, request, observed condition, letter, newspaper item, schedule change, or player-created posting. |
| Kill ten enemies | Observe, escort, negotiate, map, gather testimony, protect, expose, repair, track, bargain, document, or choose. |
| Single correct dialogue tree | Multiple information sources, different social approaches, and consequences for how knowledge is obtained or shared. |
| Content freezes until accepted | The situation advances according to time and autonomous NPC behavior. |
| Reputation as a decorative bar | Standing changes access, prices, testimony, favors, invitations, suspicion, or institutional authority. |
| Fetch item with no context | Procurement under scarcity, time pressure, competition, risk, provenance, or a meaningful buyer. |
| Quest disappears after completion | Aftermath states, later callbacks, articles, debts, relationship changes, or world-state mutations. |

# 2. Quest Object and State Model

**Implementation principle. **A quest is best represented as a stateful content object tied to world state, NPC knowledge, player knowledge, time, and consequences. The object should not assume one player owns it. Multiple players may discover, advance, contradict, or resolve different aspects of the same situation.

**Identity: **quest_id, working_title, content_family, canonical_status, spoiler_tier.

**World placement: **primary_location, secondary_locations, involved_npcs, factions, calling_relevance.

**Discovery: **hooks, rumor_sources, newspaper_hooks, environmental_hooks, player-generated hooks.

**Eligibility: **preconditions, time windows, prior world states, optional relationship thresholds.

**Evidence: **physical, documentary, witness, environmental, behavioral, historical, false or misleading evidence.

**Agency: **available approaches, branch points, social choices, information-sharing choices, sacrifice or opportunity costs.

**Autonomy: **npc_actions, rival_actions, scheduled changes, what happens without intervention.

**Outcomes: **success variants, partial outcomes, failure states, delay states, unresolved outcomes.

**Persistence: **world mutations, schedule changes, relationships, Standing, Bonds, Debts, access, prices, item provenance.

**Propagation: **rumors generated, Harbinger stories, Chronicle eligibility, follow-up hooks.

**Repeatability: **one-shot, recurring, cooldown, regenerated parameters, reset rules, permanent depletion if any.

**Multiplayer: **parallel tasks, conflict points, group information, individual knowledge, latecomer entry paths.

**Content assets: **room prose, object prose, NPC lines, letters, clues, newspaper copy, failure text, return-visit text.

## Quest state recommendations

- Dormant: exists in the world but has not yet produced a public or personal hook.
- Surfaced: at least one hook is active, but nobody needs to formally accept the quest.
- Investigating: one or more players have interacted with relevant state or evidence.
- Changing: a timer, NPC action, or player action has altered the situation.
- Resolved locally: an immediate problem has reached a stable state, even if the deeper mystery remains open.
- Aftermath: consequences, rumors, articles, debts, memorials, or altered schedules are active.
- Dormant recurrence: repeatable content has returned to the pool with changed parameters.
## Standard content packet

**Every authored quest should be deliverable to engineering in the following packet. **Writers can work in prose, YAML, JSON, a spreadsheet, or a CMS, but these fields must survive into implementation.

1. Working title and quest ID
1. Content family and scope
1. Canonical status
1. Primary hook and alternate hooks
1. Locations and NPCs
1. Preconditions and timers
1. Objective world state
1. NPC beliefs and misinformation
1. Evidence list with provenance
1. Player verbs and available approaches
1. Branch points and opportunity costs
1. Autonomous NPC and rival behavior
1. Success, partial, failure, and delay outcomes
1. Persistent mutations
1. Relationship and faction effects
1. Items created, moved, changed, or destroyed
1. Rumors emitted
1. Harbinger consequences
1. Chronicle eligibility
1. Follow-up content
1. Repeatability and reset rules
1. Multiplayer behavior
1. AI compatibility
1. Required prose and dialogue assets
1. QA cases and exploit risks
# 3. Launch Content Families and Example Bank

**Use these as seeds, not immutable scripts. **Titles are working titles. An example can be expanded into a one-session quest, folded into a larger chain, converted into a repeatable template, or used only as a rumor source. Wherever possible, cross-link one piece of content to several systems instead of creating isolated quests.

## 3.1 Newcomer quests

**How it works. **Newcomer content is tutorialization hidden inside fiction. It teaches movement, time, observation, conversation, rumors, the Inn Between, the in-character Tavern, the Harbinger, Calling identity, and consequence without forcing a single onboarding path.

**Construction rule. **Provide at least three obvious opportunities within the first few minutes, but never require a fixed sequence. Every newcomer quest should touch a permanent resident or institution so that the player begins building a social map.

**THE WRONG TRUNK. **A new arrival receives luggage belonging to someone who supposedly reached Frankenstein Village months ago. The objects can be returned, examined, sold, reported, or used to search for the missing owner; whichever route is taken creates a different first set of relationships.

**NO VACANCY. **Several arrivals need lodging and only one room is free. The apparent logistics problem becomes a social puzzle when one traveler refuses any room previously occupied by a particular person.

**THE NAME IN THE LEDGER. **The registry already contains the newcomer's name in older ink, attached to another occupation and a different signature. No system confirms whether the entry is fraud, coincidence, or something stranger.

**THE LAST COACH. **A coach emerges from Borgo Pass without its driver. Passengers disagree about when the driver disappeared, and the horses refuse to face the road back into the Mists.

**THREE WARNINGS. **Three residents give a newcomer incompatible rules for surviving the first night. Two warnings become relevant before dawn, but not necessarily for supernatural reasons.

**THE UNCLAIMED LETTER. **A letter waits for a recipient who is absent from every official record. Several villagers claim to know the person and give incompatible directions.

**FIRST TRIBUTE. **The newcomer witnesses the blood tribute at the well. The content teaches observation, asking questions, faction perspectives, and the distinction between objective ritual state and rumor.

**THE CHEAP COTTAGE. **A newcomer can rent an unwanted cottage. Nothing attacks them, but minor objects are repositioned overnight and neighbors disagree about whether this is normal.

**A JOB BEFORE SUPPER. **A resident offers three small paid tasks in different parts of town, but the world clock makes completing all three impossible. The newcomer learns that choosing one activity means missing another.

**WHO TOLD YOU MY NAME?. **An NPC greets the newcomer by name before any introduction. The NPC later denies having done so, creating a low-stakes first mystery that teaches memory and testimony mechanics.

## 3.2 Civic quests

**How it works. **Civic quests make Frankenstein Village worth protecting. They are ordinary problems of maintenance, scarcity, records, funerals, work, lodging, trade, and governance that may or may not intersect with the supernatural.

**Construction rule. **At least some civic problems must remain entirely ordinary. Their outcomes should affect Standing, Debts, shop availability, schedules, prices, public space, or community memory.

**THE LEANING FOOTBRIDGE. **A small bridge is becoming unsafe. The smith wants closure, merchants demand repairs without interrupting deliveries, and the council does not agree who should pay.

**A FUNERAL WITH NO FAMILY. **A resident dies without known kin. Players can help identify the deceased, arrange rites, inventory possessions, write an obituary, or discover that several people quietly considered the dead person family.

**MARKET STALL DISPUTE. **Two merchants claim the same market space under contradictory old permits. The problem can be mediated, investigated in council records, exploited, or allowed to become a lasting feud.

**THE MISSING MILK CART. **A routine dairy delivery fails to arrive. The cause can vary by world state: broken axle, illness, theft, fear of the Mists, or a deliberate boycott.

**A ROOF BEFORE RAIN. **A forecasted storm gives the village a short window to repair a damaged roof on a shared building. Different Callings contribute different useful verbs.

**NIGHT WATCH VACANCY. **A watchman is sick. Players can volunteer, hire a substitute, persuade another resident, or leave the post empty and accept whatever the night produces.

**THE COUNCIL PETITION. **Residents gather signatures for or against a new village rule. The content is primarily conversation and social pressure, with later council consequences.

**THE STRAY HORSE. **A valuable horse appears in the square with no rider. Several people claim ownership, and the animal reacts strongly to one route out of town.

**WINTER STORES. **A shortage forces the village to decide which institution receives limited fuel first. Players can procure more, negotiate allocation, expose hoarding, or take sides.

**A BROKEN WATER PUMP. **The public pump fails. Repair reveals old workmanship and a sealed cavity that may be mundane infrastructure or an unrelated discovery.

**SCHOOLROOM WINDOWS. **Several panes in the village schoolhouse are broken repeatedly. The immediate job is repair; the longer question is whether this is vandalism, an accident, or someone trying to see inside at night.

**THE EMPTY SHOPFRONT. **A shop — not the leased curiosity shop, which has its sign; a different premises — has stood unused long enough for the council to reassign it. Players can advocate for a new business, investigate why previous tenants left, or claim it through a future building system.

## 3.3 Rumor quests

**How it works. **Rumor quests begin as information rather than instructions. Players decide whether to investigate, repeat, distort, publish, trade, or ignore the claim.

**Construction rule. **Store provenance, timestamp, witness status, confidence, and motive where possible. False rumors are allowed, but partial truths are more useful because they can connect unrelated facts without collapsing into pure noise.

**THE BLUE LIGHT. **Several people report a blue light in Frankenstein Manor. Witnesses disagree about the hour, the room, and whether the light moved.

**THE WELL IS WARM. **Someone claims the well steamed before tribute night. Another witness insists it always does that in cold weather.

**VICTOR AT THE WINDOW. **A traveler swears Victor Frankenstein was visible in an upper window. The witness has never met Victor and may only know his portrait.

**NO BIRDS AT DAWN. **A baker claims no birds sang on one particular morning. A Hound considers it significant; the apothecary dismisses it.

**THE BELL UNDERFOOT. **A child says a bell can be heard beneath the square after midnight. Adults report only pipes, carts, or imagination.

**A STRANGER IN THE CEMETERY. **Three residents saw a figure among the graves, but descriptions disagree on height, clothing, and whether the figure cast a shadow.

**THE COACH THAT NEVER ARRIVED. **People in a neighboring town supposedly sent a coach to Frankenstein Village. No coach arrived, but a piece of its luggage appears at the post office.

**SOMEONE BOUGHT ALL THE SALT. **A shopkeeper reports a single buyer purchasing an unreasonable amount of salt. Nobody agrees whether this is preparation, superstition, or ordinary trade.

**THE CATACOMBS HAVE MUSIC. **A night worker heard music through a drain. The melody can later be recognized at a social gathering below ground.

**THE HOUNDS ARE LEAVING. **A rumor claims the Hounds are abandoning Frankenstein Village. In reality, a patrol schedule changed, but the rumor itself affects public behavior.

**THE CHURCH DOOR WAS OPEN. **Someone insists the church stood open before dawn despite being locked every night. The sexton quietly changes the lock the same day.

**THE LEASEHOLDER'S CRADLE. **A cradle has been ordered — and paid for, in advance — in the name of the man who leased the curiosity shop: the one with the OPENING SOON sign that never opens. Nobody can agree why he wanted it, whether he knows it arrived, or whether he will ever come to collect it. The true purchase may be less dramatic than the village version.

## 3.4 Small mysteries

**How it works. **These are compact one-session investigations that replace a conventional MMO's routine combat encounters. They should usually be playable in twenty minutes to two hours.

**Construction rule. **Use several independent evidence channels and at least one interpretive choice. Avoid a single clue that produces a canonical solution button.

**TOMORROW'S OBITUARY. **The Harbinger receives an obituary for a living resident. The copy appears legitimate but its source is unclear.

**THE EMPTY CHAIR. **A specific Tavern chair is never used. Sitting there causes no scripted harm, but immediately reveals social history through NPC reactions.

**THE BORROWED VOICE. **A phonograph contains a recording nobody remembers making. The voice may be identifiable while the circumstances remain uncertain.

**SEVEN WET FOOTPRINTS. **Wet prints cross a dry interior floor and stop at a wall. The real investigation includes who had access, weather, floor construction, and recent repairs.

**THE MISSING KEY. **A room key disappears. Several people want access, but only one of them actually stole the key and another has a better reason to lie.

**THE REPLACED PORTRAIT. **A framed portrait in a public building is subtly different after maintenance. Records cannot establish whether anyone deliberately replaced it.

**THE BURNED TELEGRAM. **Only fragments of a telegram survive. Players can reconstruct several plausible messages, each of which points toward different follow-up content.

**THE CLOCK THAT GAINS TIME. **A public clock begins gaining several minutes per day. The mechanism is sound, but its changes correlate with another schedule in town.

**THE WRONG FLOWERS. **Fresh flowers appear on a grave whose occupant had no known visitors. A second grave receives the same flowers the next week.

**A LOCKED PANTRY. **Food is disappearing from a locked pantry. The solution may involve duplicate keys, a hidden service hatch, or a resident protecting someone hungry.

**THREE IDENTICAL COINS. **Unrelated residents possess unusually identical coins. The coins are not magical; the interesting question is how they entered circulation together.

**THE WINDOW ACROSS THE STREET. **A resident reports seeing a person in a window every night. The room is vacant, but the line of sight intersects another reflective surface.

## 3.5 Long mystery chains

**How it works. **Long chains unfold across locations, NPC schedules, real-world sessions, articles, expeditions, and faction responses. They should produce intermediate discoveries so players feel progress without requiring a final metaphysical answer.

**Construction rule. **Structure the chain as a graph, not a line. Multiple hooks should enter different nodes, and several nodes should remain optional or discoverable in different orders.

**THE LAMPS OF FRANKENSTEIN MANOR. **Weeks of intermittent lights create a chain involving watch shifts, electrical measurements, old plans, missing equipment, contradictory witnesses, and changing access to the Manor grounds. The local question can be answered without resolving Victor's ultimate fate.

**THE TRIBUTE RUNS THIN. **Blood delivered at the well is no longer reaching the catacombs in expected quantity. The chain can involve infrastructure, theft, politics, fear, and competing demands from the Castle's brood and village authorities.

**THE VANISHED CORRESPONDENT. **A Harbinger reporter disappears while mapping lower passages. Pages of the reporter's notebook continue appearing in different locations, and different factions want control of the material.

**THE ROAD THAT RETURNS. **Repeated expeditions test a route through the Mists. The path changes, time costs accumulate, maps conflict, and travelers return with objects or memories that do not match each other.

**THE BROKEN TRUCE SEAL. **A physical symbol associated with the Truce is found damaged. Nobody agrees whether the act has legal, ritual, political, or purely symbolic significance.

**THE WINTER WITHOUT RAVENS. **A seasonal absence of familiar birds becomes a long ecological, social, and superstitious investigation connecting hunters, farmers, the church, and the catacombs.

**THE MISSING NAMES. **Old registers contain systematic gaps in several decades. Different institutions hold partial copies, and rebuilding the record threatens reputations in the present.

**THE QUIET HOUSE ON THE HILL ROAD. **A supposedly abandoned residence develops a pattern of deliveries, lights, and visitors over several weeks. The content is about surveillance, identity, and why several factions prefer the house remain unexamined.

**THE BLACK LEDGER. **A set of coded financial records links ordinary businesses to unexplained recurring payments. Solving the accounting reveals obligations rather than a single villain.

**THE SECOND MAP OF FRANKENSTEIN VILLAGE. **A historical map depicts streets and underground routes that do not match the modern village. Each verification attempt confirms some parts and falsifies others.

## 3.6 Expeditions

**How it works. **Expeditions send players into layered locations where preparation, time, navigation, observation, and return visits matter. Information, access, maps, artifacts, and relationships are primary rewards.

**Construction rule. **Every expedition site should support at least three meaningful visits under different conditions. Avoid consuming the location after one successful run.

**THE FIRST DESCENT. **A safe, shallow catacomb route introduces mapping, light, travel time, retreat, and evidence recovery without requiring combat.

**THE COLLAPSED GALLERY. **A previously known catacomb passage has collapsed. Players can clear it, map around it, determine whether the collapse was natural, or leave it sealed.

**MANOR PERIMETER SURVEY. **Players investigate the grounds without entering the Manor, recording lights, tracks, wires, outbuildings, and signs of recent maintenance.

**THE MARSH HERB RUN. **A healer needs plants from a marsh area whose safe path changes with weather and time of day. The expedition can produce medical supplies and unrelated observations.

**THE CASTLE APPROACH. **Players travel far enough toward the ruined Castle to learn the route, social dangers, and signs of occupation without turning the ruins into a conventional dungeon.

**THE COTTAGE IN THE WOODS. **A cottage contains mundane evidence of recent habitation but no resident. Return visits gradually reveal who uses it and why.

**THE OLD QUARRY. **A disused quarry provides stone, fossils, hidden dumping, and a lower opening that different residents remember differently.

**THE FLOODED PASSAGE. **A catacomb section becomes available only when water is low. Players must plan around weather and the world clock.

**BORGO PASS NIGHT SURVEY. **The route every newcomer travels feels different when deliberately explored after dark. Travel time, weather, and sightings become data rather than decoration.

**THE FORGOTTEN ORCHARD. **An overgrown orchard contains old boundary markers, grafted trees, and a locked shed. Its history connects ordinary land ownership with a much older dispute.

## 3.7 Group investigations

**How it works. **Group investigations make multiplayer coordination genuinely useful by creating simultaneous evidence, multiple witnesses, distributed geography, or complementary Calling capabilities.

**Construction rule. **Do not simply increase difficulty or require more hit points. Parallelize information and responsibility so each participant can return with a distinct contribution.

**FOUR WINDOWS. **A suspect location can only be properly observed by watching four approaches during the same hour. Separate players obtain different evidence and must compare notes afterward.

**THE SPLIT INTERVIEW. **Several witnesses will only speak privately and leave town at the same time. A group must divide, interview in parallel, then reconcile contradictions.

**THE MIDNIGHT COUNT. **Players simultaneously count lights, bells, carts, and foot traffic at separate village points to test a theory about an event cycle.

**THE MOVING PACKAGE. **A package is expected to pass through several hands in one evening. Following the entire route requires coordinated shadowing rather than one character tailing everyone.

**THE COUNCIL VOTE. **Different council members can be persuaded or questioned only during overlapping windows. Social coordination replaces a combat party composition problem.

**THE FLOOD GATE. **An underground investigation requires one team to manipulate a surface mechanism while another observes changes below.

**THREE ALIBIS. **Three suspects claim to have been in separate public places during the same event. Players can verify all three only by splitting up or recruiting witnesses.

**THE PROCESSION WATCH. **A public procession creates several simultaneous risks: crowd control, observation, escort, and investigation. Different players see different anomalies.

## 3.8 Social expeditions

**How it works. **These are adventures whose main verbs are converse, observe, negotiate, lie, perform, testify, bargain, and decide whom to trust.

**Construction rule. **Treat seating, invitations, etiquette, private side conversations, public statements, and who overhears what as world mechanics. A social expedition can have stakes without combat.

**DINNER BELOW. **Players attend a vampire gathering where etiquette, observation, favors, and choosing when to leave are the principal mechanics.

**THE COUNCIL IN CLOSED SESSION. **A sensitive meeting allows limited observers. Players can lobby beforehand, choose whom to represent, and later decide what to reveal.

**THE SCIENTIFIC DEMONSTRATION. ***(Post-launch: requires Pretorius present.)* Pretorius demonstrates an invention or specimen. Guests interpret the same event differently, and a technical irregularity becomes socially important.

**THE WAKE. **A funeral wake places rivals, family, Hounds, clergy, and gossiping villagers in one room. Information emerges through who speaks to whom.

**THE AUCTION. **An estate sale puts mundane possessions and one disputed object into public bidding. Money, provenance, sentiment, and secrecy collide.

**THE SEANCE. **The Guild of Mystics hosts a controlled sitting. The content never needs to certify supernatural communication; reactions, planted questions, and unexpected knowledge are sufficient.

**THE VISITING LECTURER. **A scholar gives a public lecture that challenges village beliefs. Players can question, support, heckle, investigate credentials, or use the gathering for unrelated social goals.

**THE RECONCILIATION SUPPER. **Two feuding households agree to dine together under neutral supervision. Players can mediate or quietly exploit the tensions.

## 3.9 Faction quests

**How it works. **Faction quests reveal institutions from the inside. Each faction should contain disagreement, private interests, procedural constraints, and competing interpretations.

**Construction rule. **Do not model factions as a single reputation vendor. Higher Standing should expose more complicated internal problems and more costly obligations, not merely better rewards.

**VILLAGERS: THE NEW TAX. **The council considers a levy to repair public works. Guilds disagree about who benefits and who should pay.

**VILLAGERS: THE MISSING MINUTES. **Minutes from a council meeting are incomplete. Several attendees remember a controversial motion differently.

**VILLAGERS: THE NIGHT CURFEW. **A proposed curfew divides residents between safety, trade, and resentment of authority.

**MANOR SHADOW: THE IDLE GENERATOR. **A piece of Frankenstein apparatus continues to draw power despite having no known purpose. Several people want it disconnected for different reasons.

**MANOR SHADOW: THE FORMER SERVANT. **A person who once worked for the Frankenstein household returns and discovers others have been telling stories in their absence.

**MANOR SHADOW: SALVAGE RIGHTS. **The council, former household staff, and the absent leaseholder — who files his claim by post and has never been seen — dispute who owns equipment removed from the Manor grounds.

**CASTLE BROOD: THE MISSED TRIBUTE. **A scheduled delivery is incomplete. Different members of the brood propose patience, punishment, bargaining, or secrecy.

**CASTLE BROOD: A GUEST ABOVE. **A vampire associated with the catacombs wants temporary lodging on the surface without revealing the reason.

**CASTLE BROOD: THE OLD DEBT. **A generations-old promise becomes relevant to a living family that disputes whether ancestral obligations should bind them.

**CHURCH: SANCTUARY. **A hunted person claims sanctuary. The church must protect institutional authority while deciding what protection actually means.

**CHURCH: THE FALSE RELIC. **A relic is proven historically dubious, yet events associated with it remain unexplained. Clergy disagree over disclosure.

**CHURCH: SEVEN CONFESSIONS. **Several parishioners separately report similar dreams or fears. The priest must decide whether to treat the pattern as spiritual, social, or medical.

**HOUNDS: WRONG MONSTER. **A Hound identifies a resident as dangerous based on incomplete evidence. Players can assist, challenge, slow, or independently investigate.

**HOUNDS: PROFESSIONAL COURTESY. **A rival hunter asks for evidence that could help their theory while strengthening a competing investigator.

**HOUNDS: MISSING PATROL. **A patrol fails to return from an area everyone considered safe.

**MYSTICS: THE SAME CARD. **Different readings produce the same card under circumstances the Mystics themselves consider unusual.

**MYSTICS: THE ABSENT CARAVAN. **One caravan is gone from the encampment without wheel tracks, goodbye, or clear sign of theft.

**MYSTICS: A PREDICTION FOR SALE. **Someone offers to buy a private reading from another player. The social problem is who owns a prediction once money changes hands.

## 3.10 Cross-faction conflicts

**How it works. **Cross-faction content is the most efficient way to create social MMO tension because one object, event, or person can generate several legitimate and incompatible demands.

**Construction rule. **Prefer conflicts of obligation, jurisdiction, interpretation, and secrecy over simple good-versus-evil framing. The player should often be unable to satisfy every interested party.

**THE DISPUTED RELIC. **The church wants an object returned, the absent leaseholder has a standing written offer to examine it, the Hounds want it contained, the Harbinger wants a photograph, and another claimant says it was stolen decades ago.

**THE WELL INSPECTION. **Village officials need the tribute well inspected. The Castle's brood considers the lower system private territory and the church objects to certain methods.

**THE MISSING PATIENT. **A sick resident disappears after consulting both Jekyll and a Mystic. Hounds suspect transformation, while family members fear public scandal.

**THE UNPUBLISHED PHOTOGRAPH. **A photograph from Manor grounds could damage several reputations. The photographer, Harbinger, Hounds, and the absent leaseholder (by letter, in immaculate handwriting) each want a different outcome.

**THE VISITOR FROM THE UNIVERSITY. **An academic arrives to inspect scientific activity. A letter from the absent leaseholder claims the visitor as *his* guest; the council wants discretion, and the Harbinger sees a story.

**THE CATACOMB COLLAPSE. **A collapse threatens surface buildings and lower chambers. Villagers need repairs, the brood needs privacy, and Hounds want the breach left open for surveillance.

**THE PROCESSION ROUTE. **The church procession must cross contested social territory. Merchants, Mystics, Hounds, and old families all lobby for different paths.

**THE FUGITIVE PRINTER. **A printer carrying controversial material seeks shelter. The Harbinger values press freedom, the council fears unrest, and the church disputes the text.

**THE SCIENTIFIC SPECIMEN. **A biological specimen may be rare, dangerous, sacred, fraudulent, or valuable depending on whom players ask.

**THE OLD BOUNDARY STONE. **A land marker places a profitable site inside different jurisdictions according to rival historical maps.

**THE RETURNED BODY. **A body thought buried years ago appears in circumstances that force church, family, Hounds, and undertaker to act before the facts are clear.

**THE INVITATION LIST. **A high-status social event excludes several important groups. Players can negotiate invitations, exploit the insult, or arrange an alternative gathering.

## 3.11 Debt quests

**How it works. **Debts are delayed social hooks. They convert help received today into obligations that can surface later under inconvenient circumstances.

**Construction rule. **Debts should be callable, negotiable, transferable in limited cases, and recordable without forcing compliance. A debt is leverage and history, not mind control.

**THE FAVOR COMES DUE. **An NPC who once helped the player asks for assistance at an inconvenient moment. Refusal is allowed but changes the relationship.

**TRANSFER OF OBLIGATION. **A creditor asks the player to use a favor owed by someone else, turning one bilateral debt into a social network problem.

**QUIET INTRODUCTION. **A resident calls in a favor only to secure an introduction to a person who normally refuses meetings.

**KEEP THIS OUT OF PRINT. **A debtor asks the player to persuade the Harbinger to delay a story. The player may owe the person but not agree with the request.

**ONE NIGHT'S STORAGE. **A merchant who once extended credit asks the player to hide a crate overnight without explaining the contents.

**WITNESS FOR ME. **A friend asks the player to publicly confirm a version of events the player did not personally observe.

**THE APPRENTICE PLACE. **Someone calls in a favor to secure training or employment for a relative, potentially displacing another applicant.

**DEBT AFTER DEATH. **A deceased NPC's ledger shows an unresolved obligation involving the player. The estate, family, or creditor may interpret that debt differently.

## 3.12 Bond quests

**How it works. **Bonds represent accumulated relationship history. Stronger Bonds should create intimacy, access, obligations, vulnerability, and requests that strangers never receive.

**Construction rule. **Do not equate a high Bond with permanent friendliness. Close relationships can produce sharper conflicts because more is at stake.

**THE PRIVATE ROOM. **An NPC with a strong Bond trusts the player enough to show a private space containing clues that casual visitors never see.

**SPEAK FOR ME. **A close contact asks the player to represent them at a meeting they refuse or cannot attend.

**I NEED THE TRUTH. **An NPC asks the player for an honest account of a sensitive event, making prior relationship history more important than a dialogue skill check.

**THE HEIRLOOM. **A trusted resident lends the player a personally important object, creating both access and responsibility.

**DEFEND MY NAME. **A Bonded NPC asks the player to challenge a damaging rumor, even though the rumor may contain truth.

**AN UNCOMFORTABLE INTRODUCTION. **A friend introduces the player to someone they distrust because the relationship matters more than their preference.

**STAY UNTIL MORNING. **An NPC who rarely admits fear asks the player to remain nearby through the night. Nothing dramatic has to happen for the scene to matter.

**THE SECRET THEY REGRET TELLING. **A strong Bond unlocks information, followed later by an attempt to retract or contain it.

## 3.13 Hyde quests

**How it works. **Hyde content turns the character-creation secret into ongoing gameplay. It should create pressure, choices, and social risk without automatically exposing the player or prescribing the secret's meaning.

**Construction rule. **Use parameterized hooks and opt-in intensity settings. The server can know categories and triggers without publishing the secret to other players or forcing a scripted revelation.

**SOMEONE KNOWS THE DESCRIPTION. **A rumor describes a person, object, act, or place connected to the character's secret without naming the character.

**THE FAMILIAR HANDWRITING. **A document resembles handwriting, terminology, or habits associated with the player's hidden past.

**THE OLD ACQUAINTANCE. **A new arrival behaves as though they recognize the player. Whether they truly do can remain ambiguous until the player engages.

**A QUESTION TOO SPECIFIC. **An NPC asks an unexpectedly precise question during an otherwise ordinary conversation.

**THE WRONG NAME. **Someone calls the player by another name and then claims it was a mistake.

**EVIDENCE BY ASSOCIATION. **A quest produces circumstantial evidence that could expose the player if shared widely, even though the evidence is not conclusive.

**THE OFFER. **A faction offers help protecting the player's secret in exchange for future cooperation.

**CONFESSION OR COVER STORY. **A public incident gives the player an opportunity to reveal part of the truth, construct a lie, or let others form their own explanation.

## 3.14 Rival investigator quests

**How it works. **Rivals are autonomous epistemic actors. They form theories, gather evidence, make mistakes, publish, negotiate, and act while players are elsewhere.

**Construction rule. **Do not make rivals cheat by knowing hidden server truth. Give them evidence, biases, schedules, and inference rules. Their errors should be explainable from what they knew.

**FIRST TO THE WITNESS. **A rival investigator reaches an important witness before the players and later publishes a selective account.

**A THEORY IN PRINT. **A Hound or detective publishes a confident theory. Players can test it, support it, dispute it, or discover it changed witness behavior.

**THE RISKY INTERVENTION. **A rival acts before evidence is complete, forcing players to respond to consequences rather than simply beat them to a clue.

**EXCHANGE OF NOTES. **A rival proposes sharing evidence under terms that reveal what they value and what they are hiding.

**THE MISSING PAGE. **A rival has one page the players need, while players possess evidence the rival lacks. Cooperation is possible but not mandatory.

**PUBLIC CHALLENGE. **An investigator openly asks the players to defend their theory before witnesses, turning epistemic disagreement into a social scene.

**THE RIVAL WAS RIGHT. **A competitor correctly predicted one important fact for reasons the players do not yet understand.

**THE RIVAL NEEDS RESCUE. **A professional adversary becomes trapped or endangered. Helping them preserves a future competitor and may earn respect or debt.

## 3.15 Timed incidents

**How it works. **Timed incidents are brief world-state windows that reward presence without making absence equivalent to content loss. Firsthand witnesses receive better evidence; everyone else can still encounter aftermath and rumor.

**Construction rule. **Always author the aftermath. If no player is present, NPCs act and the event still leaves traces, testimony, articles, altered schedules, or unresolved questions.

**A CARRIAGE AT DUSK. **A carriage arrives unexpectedly and waits only twenty minutes before departing. Players present can interview occupants; later players receive secondhand accounts.

**SOMEONE RUNS INTO THE CHURCH. **A frightened person claims sanctuary and pursuers arrive shortly afterward. The scene changes whether players are present or not.

**THE MANOR LIGHTS IGNITE. **A brief illumination creates an observation window for anyone already positioned nearby.

**THE WELL BOILS. **Steam suddenly thickens around the tribute well. Different NPCs converge according to schedule and faction.

**A FIGHT IN THE SQUARE. **A public argument becomes physical unless interrupted, but the more important content is what the participants accuse each other of.

**THE UNATTENDED WAGON. **A wagon blocks traffic for half an hour before its owner returns. Its cargo and route create optional leads.

**THE BELL RINGS ONCE. **A single unexplained bell strike occurs at a fixed minute. Witness presence changes evidence quality.

**A CHILD IS MISSING. **A family raises an alarm. Search geography changes as time passes, and the child can move independently.

**THE SUDDEN FOG. **A district is cut off for an evening. Local scenes continue while information from outside becomes delayed.

**THE STRANGER COLLAPSES. **A traveler falls ill in a public place, creating simultaneous medical, identity, property, and rumor content.

**THE NEWSPAPER RUNNER SHOUTS. **A special edition is released after a major event. Players can obtain the first public account before corrections and rebuttals appear.

**THE FUNERAL PROCESSION STOPS. **A procession unexpectedly halts at a specific location, producing a brief opportunity for observation and social reaction.

## 3.16 Scheduled world events

**How it works. **Scheduled events create rhythm. Players learn that the village has a calendar and that different opportunities appear at different times.

**Construction rule. **The event should be useful even when nothing unusual happens. Layer incidents on top of a stable routine rather than making every recurrence extraordinary.

**MARKET MORNING. **Vendors, travelers, pickpockets, gossip, shortages, and public notices concentrate in the square on a predictable schedule.

**COUNCIL NIGHT. **Petitions, disputes, faction representatives, and public minutes create a recurring civic content hub.

**SUNDAY SERVICE. **The church becomes a social convergence point. Attendance, absence, sermons, announcements, and private conversations all matter.

**TRIBUTE NIGHT. **The established blood tribute produces observation, ceremony, resentment, faction presence, and opportunities for interference or protection.

**HARBINGER PUBLICATION. **The newspaper appears on a fixed cadence, converting prior events into public knowledge and spawning correction, scandal, and follow-up quests.

**THE HOUNDS' PATROL CHANGE. **A scheduled change of watch creates predictable windows of coverage and vulnerability.

**MYSTICS' OPEN EVENING. **The caravans receive visitors for readings, trade, and gossip during known hours.

**PUBLIC LECTURE. **A rotating lecture, demonstration, or debate gives the village a recurring reason to gather indoors.

**DELIVERY DAY. **Bulk goods arrive through Borgo Pass, affecting shop inventories, jobs, rumors, and the chance of unexpected passengers.

**MONTHLY MEMORIAL. **A civic remembrance of the War of the Well creates ritual, speeches, disagreement about history, and Chronicle material.

## 3.17 Random world incidents

**How it works. **Random incidents provide low-cost unpredictability and environmental life. Most are not major quests, but any one of them may become evidence, a social scene, or a seed for generated content.

**Construction rule. **Weight incidents by location, time, weather, NPC presence, and current world state. Do not let every odd occurrence become supernatural or players will stop distinguishing signal from texture.

**DOG AT THE CELLAR. **A dog refuses to pass one cellar door and must be coaxed away.

**DROPPED PARCEL. **A passerby loses a wrapped parcel whose address is smeared by rain.

**BROKEN WHEEL. **A cart wheel fails and blocks a street until repaired or moved.

**EXTINGUISHED LAMP. **One gas lamp goes out repeatedly while neighboring lamps remain lit.

**PUBLIC SNEEZE. **A resident has a dramatic coughing or sneezing fit, producing mundane concern that can later matter during an illness event.

**STRANGER ASKS DIRECTIONS. **A traveler asks for a place that either exists under another name or does not appear on current maps.

**LOOSE PAGES. **Wind scatters pages from a notebook. Most are mundane, one may connect to another system.

**WRONG DELIVERY. **A shop receives a crate meant for another address.

**HORSE SPOOKS. **A horse refuses a particular patch of road for several minutes.

**ARGUMENT THROUGH A WALL. **Players overhear fragments of a dispute without seeing the speakers.

**COIN IN THE DRAIN. **A glint in a gutter can be ignored, retrieved, or noticed by someone else first.

**WINDOW SLAMS. **A window repeatedly opens or closes in changing weather.

**LOST GLOVE. **A distinctive glove appears in a public place and can later be recognized.

**UNEXPECTED SONG. **Someone hums a melody that another NPC reacts to.

**INK SPILL. **A clerk ruins part of a record and asks for help reconstructing it.

**CLOSED EARLY. **A business unexpectedly shuts before normal closing time.

**CROW IN THE SHOP. **A bird becomes trapped indoors and causes minor chaos.

**A SMELL OF OZONE. **A brief electrical odor appears near no visible apparatus.

**THE UNFAMILIAR POSTER. **A notice appears on a wall using official formatting but no recognized signature.

**MUD ON THE STEPS. **Fresh mud appears at a building entrance despite dry weather.

**A CHILD'S CHALK MAP. **Children draw a map of tunnels based on a game. Some lines resemble real underground routes.

**TWO PEOPLE STOP TALKING. **An ordinary conversation ends abruptly when a particular person enters.

**SHOP BELL RINGS. **A shop bell rings when no customer is visible.

**FLOCK TURNS AT ONCE. **Birds change direction suddenly over one district. It may be meaningless unless it recurs.

## 3.18 Server-wide events

**How it works. **Server-wide events are temporary systemic conditions that generate many local tasks and social consequences. One event should create an ecosystem rather than one quest.

**Construction rule. **Author faction, profession, location, economy, rumor, and aftermath layers for each event. Players should be able to participate meaningfully without joining a single central raid.

**THE LONG BLACKOUT. **Village electricity and selected gas lighting fail across several districts. Shops, church, Hounds, Harbinger, patients, travelers, and Manor watchers all receive different problems.

**THE MISTS ADVANCE. **Fog occupies roads and fields usually considered safe, changing travel times, cutting routes, and producing temporary islands of activity.

**THE MISSING BURGOMASTER. **The office holder or acting official disappears, creating administrative uncertainty without requiring the institution itself to disappear.

**A WEEK OF BAD WATER. **Public water becomes suspect. Healers, merchants, council, press, and ordinary households all respond while the cause remains uncertain.

**THE GREAT FUNERAL. **A prominent resident dies, generating processions, inheritance, faction attendance, newspaper coverage, private grief, and old disputes.

**THE UNSCHEDULED TRIBUTE DEMAND. **Someone claiming authority from below requests an extraordinary payment. The village must decide whether the request is legitimate before complying.

**THE ARRIVAL SURGE. **An unusual number of newcomers emerge from the Mists in a short period, straining lodging, food, records, and social trust.

**THE STORM OVER THE MANOR. **A severe electrical storm creates fires, outages, strange instrument behavior, blocked roads, and simultaneous reports from across the valley.

## 3.19 Seasonal and chapter frameworks

**How it works. **Seasonal frameworks let Frankenstein Village accumulate history without requiring everyone to complete a linear expansion. They change environmental conditions, schedules, economies, and the kinds of problems likely to occur.

**Construction rule. **A season should modify probabilities and open content rather than replace the world. Late arrivals inherit the Chronicle and the consequences of prior seasons.

**OCTOBER: THE WEEKS OF LONG SHADOWS. **A month-long pattern of earlier fog, cemetery rumors, and shifting evening schedules creates many small investigations without declaring a singular villain.

**NOVEMBER: THE RECKONING OF ACCOUNTS. **Winter preparation and old debts bring economic records, favors, tribute obligations, and household shortages into focus.

**DECEMBER: THE EMPTY PLACES AT TABLE. **Holiday gatherings emphasize absence, family, newcomers, old feuds, hospitality, and who is not present.

**JANUARY: THE FROZEN ROADS. **Travel becomes expensive, local institutions matter more, and isolated sites develop new states.

**SPRING: THE THAW BELOW. **Flooding and thaw expose catacomb routes, graves, objects, and infrastructure that were inaccessible in winter.

**SUMMER: THE VISITORS. **Better roads bring scholars, performers, merchants, investigators, and opportunists, increasing social rather than military pressure on Frankenstein Village.

## 3.20 Public mysteries

**How it works. **Public mysteries are community-scale questions that many players can investigate over long periods. Their value comes from shared evidence, theory building, and changing public interpretation.

**Construction rule. **Keep a clear distinction between local facts that can be established and metaphysical conclusions the world intentionally withholds. Community progress must still produce usable knowledge.

**WHERE IS VICTOR FRANKENSTEIN?. **The village continually generates testimony, documents, false sightings, interests, and political uses of Victor's absence without requiring the world to answer the question at launch.

**WHY ARE THE MANOR LIGHTS RETURNING?. **The phenomenon is public, observable, and measurable. Different theories can be tested locally even if no single explanation is certified.

**WHY DOES TRIBUTE CHANGE?. **Variations in amount, timing, or ritual become a community research problem spanning records, infrastructure, and faction politics.

**WHO MAPS THE CATACOMBS?. **Different maps circulate with conflicting claims of accuracy, authorship, and ownership.

**WHAT HAPPENED TO THE OLD ROAD?. **Historical references point to a route no longer visible on current maps.

**WHO WRITES THE ANONYMOUS LETTERS?. **A recurring correspondent influences public debate without revealing identity.

**WHY DO SOME NEWCOMERS ARRIVE TOGETHER?. **Arrival patterns appear statistically unusual, but causation is unclear.

**WHO KEEPS THE EMPTY CHAIR?. **A minor Tavern custom grows into a public history question as different residents attach different stories to it.

## 3.21 Private mysteries

**How it works. **Private mysteries create information asymmetry. They give individual players secrets, choices about disclosure, and reasons to seek others without turning the MMO into isolated solo instances.

**Construction rule. **Avoid making private content essential to server-wide progress. It should enrich identity and social exchange, not trap critical world information behind one inactive account.

**THE NOTE UNDER YOUR DOOR. **A player receives a message containing information few others know and must decide whether to share it.

**THE OBJECT IN YOUR ROOM. **A personal possession appears that the player did not acquire. The server need not immediately explain who placed it there.

**THE FAMILIAR FACE. **A newcomer resembles someone from the character's backstory strongly enough to justify investigation but not automatic recognition.

**THE WRONG MEMORY IN THE LEDGER. **A public record contradicts the player's declared history in one specific detail.

**A PRIVATE INVITATION. **A faction invites the player alone to a meeting, creating information asymmetry with their companions.

**THE BUYER. **Someone offers money for an apparently insignificant item the player owns.

**THE REPEATED QUESTION. **Different NPCs independently ask the player the same odd question over several days.

**THE ROOM WITH YOUR INITIALS. **A discovered location contains initials or a mark that could plausibly connect to the player's past but also has alternate explanations.

## 3.22 Harbinger content

**How it works. **The Harbinger turns private events into public knowledge and gives the world a visible memory of recent events. It is both content source and consequence engine.

**Construction rule. **Model reporting as selection and interpretation. Articles should name sources when appropriate, contain uncertainty, and be correctable later. The press must not function as omniscient narration.

**TOMORROW'S OBITUARY. **Editorial staff decide whether to print, investigate, suppress, or mock an obituary submitted for a living person.

**STOP THE PRESS. **Conflicting eyewitness accounts arrive shortly before publication. The chosen version changes public belief until corrections appear.

**THE MISSING TYPE. **Movable type vanishes from the print shop, temporarily preventing certain letters or symbols from being printed accurately.

**ANONYMOUS CORRESPONDENT. **Accurate reports arrive before staff can verify how the writer learned the information.

**THE CORRECTION. **A correction claims the previous issue contained text that surviving copies do not contain.

**CLASSIFIED CONVERSATION. **Ordinary advertisements appear to be communicating through repeated phrases and placement.

**THE LIBEL THREAT. **A resident threatens legal or social action over a story whose facts are mostly correct but whose framing is disputed.

**SPECIAL EDITION. **A major event creates pressure to publish quickly, trading verification for timeliness.

**THE MISSING REPORTER. **A correspondent fails to return, but work attributed to them continues arriving.

**LETTERS TO THE EDITOR. **Player and NPC letters create public arguments that influence Standing and future interviews.

## 3.23 Chronicler content

**How it works. **The Chronicle is slower and more authoritative than the newspaper. It records what Frankenstein Village remembers while preserving provenance and, when needed, disagreement.

**Construction rule. **Never let the Chronicle silently convert rumor into objective truth. An entry can canonize that people believed something without canonizing the belief itself.

**THE BATTLE OVER ONE SENTENCE. **Several witnesses agree an event belongs in the Chronicle but disagree over one consequential phrase.

**TWO VERSIONS SURVIVE. **The Chronicler has incompatible accounts and chooses to preserve both rather than collapse them into false certainty.

**THE MISSING YEAR. **A gap in older records becomes a community reconstruction project.

**A PLAYER'S DEPOSITION. **A participant can submit a signed account of an event, permanently preserving their perspective.

**REVISION BY EVIDENCE. **New evidence justifies annotating an older Chronicle entry without erasing the original record.

**THE REFUSED ENTRY. **A Chronicler declines to canonize a popular rumor, angering people who already treat it as fact.

**THE MEMORIAL VOLUME. **A deceased or retired character's major deeds and relationships are assembled from surviving records.

**THE PUBLIC INDEX. **Players help tag people, places, dates, and unresolved questions in Chronicle entries, making history itself explorable.

## 3.24 Economic content

**How it works. **Economy content makes goods meaningful because people, institutions, and projects need them. Prices and shortages should emerge from world state where practical.

**Construction rule. **Connect demand to real consumers, schedules, community projects, and events. Avoid commodities whose only purpose is conversion into a larger currency number.

**LAMP OIL SHORTAGE. **A delayed delivery raises prices and forces households and businesses to prioritize nighttime lighting.

**COAL FOR THE SMITHY. **The smith cannot maintain normal output without a new coal shipment, connecting transport, repair work, and prices.

**PAPER RUN. **The Harbinger needs paper before publication day, creating procurement and bargaining opportunities.

**RARE GLASS. **Standing orders in the leaseholder's name promise good money for laboratory glassware that is fragile, imported, and useful to other residents too. Payment on his eventual arrival — or so the letters say.

**MARSH HERBS. **Jekyll buys specific plants whose availability changes with season and weather.

**THE CHEAP COUNTERFEIT. **Low-quality goods enter the market, forcing Merchants and buyers to distinguish price from provenance.

**STORAGE SPACE. **A bumper delivery creates temporary demand for secure warehouses and trusted custodians.

**FUNERAL SUPPLIES. **A death creates sudden demand for flowers, timber, cloth, printing, food, and carriage services.

**A BUYER BELOW. **Someone in the catacombs wants ordinary surface goods and pays through an intermediary.

**THE MISSING INVOICE. **A merchant's books show a paid invoice for goods nobody remembers receiving.

**WINTER PRICE CONTROLS. **The council considers limiting prices during scarcity, creating enforcement, evasion, and public debate.

**THE TRAVELING PEDDLER. **A periodic merchant introduces goods, rumors, and price competition from outside Frankenstein Village.

## 3.25 Procurement quests

**How it works. **Procurement is a valid quest form when scarcity, provenance, time, route choice, competition, or consequence makes the object matter.

**Construction rule. **Every procurement task should answer why this item, why now, who else wants it, and what changes if it is not obtained.

**FEVERFEW BEFORE NIGHTFALL. **A patient needs a plant before evening. The safest patch is distant and another buyer may already be gathering there.

**REPLACEMENT PRESS BELT. **The Harbinger needs a mechanical belt quickly enough to publish on time.

**THREE MATCHING CANDLES. **The church requires candles of a specific size for a ceremony; ordinary substitutes change the arrangement.

**CLEAN BOTTLES. **Jekyll needs uncontaminated bottles during a supply crunch, creating salvage and cleaning options.

**SILVER WIRE. **A Hound requests silver wire without explaining whether it is for a trap, instrument, or superstition.

**BLACK CLOTH. **A family needs mourning cloth, but the last bolt has already been promised elsewhere.

**DRY TIMBER. **A carpenter needs seasoned wood for a repair that cannot wait for fresh lumber to cure.

**FOREIGN INK. **A translator needs a particular ink to test whether a disputed document was written locally.

**SAFE ICE. **A healer needs ice from a source not contaminated by recent runoff.

**A CRATE FROM THE PASS. **A specific shipment is expected on a coach. Players can track the crate when the manifest and actual cargo disagree.

## 3.26 Crafting commissions

**How it works. **Crafting begins with a person or institution needing a real object. The order can create social information, provenance, and future evidence.

**Construction rule. **Crafted items should retain maker, commissioner, date, materials, repairs, and ownership history when useful. Object provenance turns crafting into future mystery content.

**THE SILENT LOCK. **A resident commissions a lock designed to open quietly from one side. The craft itself becomes evidence if later discovered.

**A CHILD'S COFFIN. **An undertaker requires careful work under emotional and time pressure, making an ordinary craft socially consequential.

**REINFORCED WINDOW BARS. **A household wants protection but neighbors interpret the installation as evidence of fear or guilt.

**SCIENTIFIC GLASSWARE. **Special shapes must be fabricated or repaired for the absent leaseholder, with unusual tolerances and uncertain purpose. Nobody in the village knows what they are for.

**A HIDDEN COMPARTMENT. **A client wants furniture modified to conceal papers. The craftsperson must decide how much to ask and what records to keep.

**THE BROKEN PRINTING PLATE. **A damaged illustration must be recreated before publication, raising questions about accuracy and alteration.

**SILVER FITTINGS. **A Hound commissions fittings that could be decorative, practical, or weapon-related without the system declaring which.

**PROSTHETIC REPAIR. **A traveler needs a damaged prosthetic restored, revealing biography through practical work.

**THE MEMORIAL PLAQUE. **A public plaque becomes a dispute over wording as much as metalwork.

**THE UNUSUAL CRATE. **A crate must be constructed for an object with odd dimensions and handling instructions.

## 3.27 Travel quests

**How it works. **Travel quests make geography and the world clock matter. The journey itself should create observations, costs, route choices, and timing pressure.

**Construction rule. **Do not teleport quest logic between locations. Travel duration should be part of the decision model and should sometimes prevent a player from doing everything.

**GUIDE THROUGH BORGO PASS. **A traveler hires a guide whose real concern is not getting lost but avoiding a particular stop.

**URGENT MESSAGE. **A message must reach a distant location before another scheduled event begins.

**ESCORT THE MEDICINE. **A fragile medical shipment needs protection from delay, weather, and mishandling rather than combat.

**SURVEY THE NEW WASHOUT. **Rain damages a road and players must determine which routes remain passable.

**FIND THE MISSING CART. **A delivery is overdue and the search area grows as time passes.

**TWO ROADS TO THE MARSH. **One route is faster, another safer, and recent rumors alter player risk assessment.

**BRING BACK THE WITNESS. **A witness outside the village agrees to testify only if someone personally escorts them.

**NIGHT MAIL. **A postal run after dark creates a predictable route for social encounters and observation.

**THE ABANDONED MILESTONE. **A traveler reports a milestone where no official map shows one. Finding it requires careful route logging.

**RETURN BEFORE THE FOG. **Weather forecasts create a hard travel window for an otherwise routine trip.

## 3.28 Watch quests

**How it works. **Watch quests reward persistence, careful logging, and pattern recognition. They are particularly suitable for asynchronous play and for AI residents without being AI-specific.

**Construction rule. **Give watchers a structured way to record observations and later compare them. The value should come from longitudinal data, not merely waiting through a timer.

**MANOR LIGHT WATCH. **Record exactly when and where lights appear over several nights.

**WELL WATCH. **Observe who approaches the tribute well outside ceremony hours.

**CEMETERY COUNT. **Track visitors, durations, and grave locations without assuming every visit is suspicious.

**CATACOMB AIRFLOW. **Monitor drafts and temperatures at fixed points to infer passage changes.

**NIGHT CART LOG. **Record carts entering and leaving one district during late hours.

**CHURCH BELL LOG. **Compare actual bell strikes with the official schedule.

**MIST LINE SURVEY. **Mark how far fog advances at regular intervals and under different weather.

**SHOP WINDOW VIGIL. **A merchant suspects theft and asks for observation, but the watcher may discover a different problem entirely.

## 3.29 Cartography quests

**How it works. **Cartography turns movement and spatial memory into persistent player-created infrastructure. Maps can be private, shared, sold, annotated, wrong, or outdated.

**Construction rule. **Store map provenance and date. When the world changes, old maps should become historical evidence rather than silently updating themselves.

**CATACOMB GRID A. **Map a shallow section with stable landmarks and known exits.

**THE FLOOD MAP. **Record which passages become inaccessible as water rises.

**THE OLD STREET PLAN. **Reconcile historical street names with current buildings.

**BORGO PASS MILEBOOK. **Record travel times and landmarks under different weather.

**THE CEMETERY LAYERS. **Map graves by age, family, and later alterations.

**THE HIDDEN SERVICE WAYS. **Document alleys, courtyards, kitchens, and delivery entrances used by village workers.

**THE CASTLE APPROACH SKETCH. **Build a safe approach map without requiring entry into the ruins.

**MAP DISPUTE. **Two widely used maps disagree. Players must survey the contested segment and preserve uncertainty where evidence remains incomplete.

## 3.30 Collection quests

**How it works. **Collections should reveal patterns, history, provenance, or changing interpretation. They are long-term research projects rather than arbitrary completion meters.

**Construction rule. **Require metadata such as source, date, location, or witness where useful. A collection should become more informative as it grows.

**HARBINGER ARCHIVE. **Assemble surviving issues to reconstruct how public explanations changed over time.

**GRAVE RUBBINGS. **Collect inscriptions from related graves to expose family or chronological patterns.

**ODD INSTRUMENTS. **Document scientific instruments, manufacturers, repairs, and owners rather than merely hoarding objects.

**PHOTOGRAPHS OF THE MANOR. **Build a time-series collection from the same vantage points.

**BORGO PASS TOKENS. **Travelers leave behind tickets, tags, receipts, and luggage labels that collectively reveal movement patterns.

**BOTANICAL CABINET. **Collect seasonal specimens with location, date, and condition metadata for Jekyll or another scholar.

**OLD COUNCIL NOTICES. **Recover public notices from previous administrations to trace changing laws and fears.

**SONGS OF FRANKENSTEIN VILLAGE. **Record variants of local songs whose lyrics preserve contradictory versions of history.

## 3.31 Puzzles and ciphers

**How it works. **Puzzles should arise naturally from documents, devices, maps, codes, routines, and period technology. Multiplayer discussion should make solving easier.

**Construction rule. **Avoid arbitrary riddles detached from world logic. If a solution can be spoiled permanently, use parameter variation, rotating keys, or make interpretation and consequence more important than the raw answer.

**THE CLASSIFIED CIPHER. **Repeated phrases in advertisements encode a conversation through placement or initials.

**THE BELL SEQUENCE. **A nonstandard bell pattern corresponds to an old schedule or code recorded elsewhere.

**THE MISPRINTED MAP. **Printing errors become meaningful when transparent overlays or multiple editions are compared.

**THE ROTATING DIAL. **A scientific instrument has several unlabeled positions whose behavior must be inferred experimentally.

**THE ACROSTIC SERMON. **A written sermon contains an intentional or accidental acrostic that points to another document.

**THE GRAVE NUMBERING. **Plot numbers form a pattern only when older cemetery plans are used.

**THE TELEGRAM KEY. **A coded telegram can be partially solved through repeated commercial phrases and known names.

**THE MUSIC BOX. **A mechanical tune corresponds to a sequence of locations, names, or times rather than a literal treasure map.

## 3.32 Moral choice quests

**How it works. **Moral choices work best when obligations conflict and every option protects something real while risking something else. The game records consequences without assigning morality points.

**Construction rule. **Do not label choices good, evil, correct, or incorrect. Author downstream reactions from people and institutions with their own values.

**SANCTUARY OR SAFETY. **Protect a dangerous but unconvicted person under church sanctuary or assist those who believe immediate removal is necessary.

**PRINT OR PROTECT. **Publish information that could warn the village but expose a vulnerable resident.

**HONOR THE DEBT. **Repay an obligation by doing something legal and socially accepted that the player nevertheless considers wrong.

**EVIDENCE OR HEIRLOOM. **Preserve an object as evidence or return it to a grieving family that may destroy or conceal it.

**BREAK THE TRUCE. **Protect an individual from a demand made under the Truce, risking wider consequences.

**TREAT THE STRANGER FIRST. **A healer must prioritize limited resources between a disliked local and an unknown newcomer.

**THE FALSE CONFESSION. **Expose a confession the player believes is false even though accepting it would calm the village.

**THE DANGEROUS TRUTH. **Tell a friend information they have asked for despite credible concern that they will act recklessly on it.

**KEEP THE PROMISE. **Honor confidentiality when authorities demand the same information for an investigation.

**THE USEFUL LIE. **Correct a false rumor that is currently preventing violence, or allow the falsehood to stand.

## 3.33 Failure content patterns

**How it works. **Failure is authored world continuation. The player loses an opportunity, quality of evidence, relationship, resource, or person, but gains a different state to play.

**Construction rule. **For every major quest, write at least one viable continuation after inaction, delay, mistaken inference, and active failure. Reserve a literal Quest Failed screen for rare mechanical contracts where nothing useful remains.

**WITNESS LEAVES. **The witness is gone, but their room, purchases, correspondence, and people they spoke with remain investigable.

**WRONG STORY PRINTED. **The Harbinger publishes an inaccurate account. The new content becomes correction, reputation damage, changed witness behavior, and public belief.

**RIVAL ACTS FIRST. **Another investigator takes action. Players investigate the consequences rather than receiving a fail screen.

**EVIDENCE DESTROYED. **Rain, fire, cleaning, burial, or deliberate removal erases a clue, leaving testimony about what used to be there.

**PATIENT WORSENS. **A medical delay changes prognosis, family behavior, resource needs, and later testimony.

**SUSPECT RELOCATES. **The person under investigation changes schedule or lodging after sensing attention.

**NEGOTIATION BREAKS DOWN. **The meeting ends without agreement, spawning separate faction actions and new leverage quests.

**OBJECT SOLD ELSEWHERE. **A desired item goes to another buyer, making ownership transfer the next problem.

**PUBLIC TRUST FALLS. **A failed intervention changes Standing and future access rather than ending the storyline.

**SOMEONE DIES. **Death opens funeral, inheritance, testimony, memorial, unfinished debt, and Chronicle content.

## 3.34 Delay content patterns

**How it works. **Time should change the quality, availability, and social meaning of evidence and opportunities. Delay is not merely a countdown to failure.

**Construction rule. **Define what degrades, what improves, who acts, and what new information becomes available at each important timer threshold.

**FRESH TRACKS BECOME MUD. **Physical evidence degrades into lower-confidence information.

**THE INTERVIEW BECOMES GOSSIP. **A firsthand witness tells others first, contaminating later testimony.

**PRICES RISE. **Scarcity becomes more expensive as an event continues.

**A RIVAL PUBLISHES. **The public learns one interpretation before players finish investigating.

**THE WEATHER CHANGES THE ROUTE. **Travel costs or access change before the player departs.

**THE PATIENT IS MOVED. **Medical urgency changes location and available witnesses.

**THE MEETING HAPPENS WITHOUT YOU. **Minutes and secondhand reports replace direct participation.

**THE OBJECT IS REPAIRED. **A damaged object that once contained evidence is restored, hiding the original condition.

**THE CROWD DISPERSES. **Players lose the ability to identify everyone present but gain later rumor trails.

**SOMEONE CHANGES THEIR STORY. **Time, fear, persuasion, or new information alters testimony.

## 3.35 Repeat-visit location states

**How it works. **Important locations need multiple states so returning players encounter changed prose, inhabitants, affordances, and risks.

**Construction rule. **Build location state as composable layers where possible: time, weather, event, occupancy, faction control, damage, and quest state. Avoid rewriting an entire room for every combination.

**TAVERN. **Normal service, market-night crowd, private wake, Hound gathering, storm shelter, after-hours quiet, rumor-heavy evening, or temporary closure.

**VILLAGE SQUARE. **Ordinary traffic, market, tribute preparation, protest, funeral procession, fog isolation, carriage arrival, or public announcement.

**CHURCH. **Open worship, private confession hours, sanctuary crisis, funeral, locked night state, repairs, debate, or feast-day gathering.

**HARBINGER OFFICE. **Routine printing, deadline rush, special edition, equipment failure, anonymous delivery, staff absence, or public complaint.

**APOTHECARY. **Normal trade, patient emergency, ingredient shortage, closed consultation, inspection, delivery day, or contamination concern.

**CATACOMBS. **Dry route, flooded route, occupied social gathering, collapsed passage, active maintenance, quiet watch, or restricted territory.

**MANOR GROUNDS. **Dormant, visible lights, storm, Hound surveillance, scientific activity, repair crews, fresh tracks, or sealed perimeter.

**BORGO PASS. **Clear travel, delivery convoy, heavy fog, washout, stranded coach, night watch, surge of arrivals, or apparent route anomaly.

# 4. Calling Content Packs

**Calling design rule. **Callings are social professions. Advancement should unlock authority, access, specialized verbs, apprentices, better interpretation tools, and responsibility, not raw combat power. Each Calling needs authored arcs plus repeatable work generated from current world conditions.

## Innkeep

**A ROOM FOR THE NIGHT. **Decide how to house travelers when capacity, reputation, secrecy, and ability to pay conflict.

**THE TAB. **A respected regular accumulates an uncomfortable debt. Collection may damage the social hub more than patience does.

**WHO SAT WHERE. **Reconstruct a disputed conversation using seating, serving order, staff memory, and receipts.

**PRIVATE SUPPER. **Host a meeting whose guests do not want to be seen arriving together.

**THE CELLAR COUNT. **Inventory reveals bottles missing and others replaced with unfamiliar stock.

**A HOUSE RULE. **A recurring behavior problem forces the Innkeep to create, enforce, or decline a new house rule.

***Repeatable work: **Serve and record a busy evening whose gossip changes with who is present. Arrange rooms, tabs, private tables, and messages according to current occupancy.*

## Chronicler

**THE CONTRADICTORY DEPOSITIONS. **Preserve incompatible accounts without pretending they agree.

**WHO GETS A NAME. **Decide whether a minor participant belongs in the permanent record or remains anonymous.

**THE MISSING VOLUME. **Recover or reconstruct a lost section of village history.

**ANNOTATION, NOT ERASURE. **New evidence complicates an older Chronicle entry and requires a transparent amendment.

**THE PUBLIC READING. **Present a contested historical account before people whose families are implicated.

**THE LAST TESTIMONY. **Record a dying or departing witness while distinguishing memory from verified fact.

***Repeatable work: **Collect signed accounts after public events. Index new people, places, and unresolved questions from recent records.*

## Smith

**THE REPEATED BREAK. **The same kind of tool fails across several owners, suggesting material, supplier, misuse, or sabotage problems.

**UNKNOWN ALLOY. **An object brought from an expedition cannot be worked normally and requires testing rather than magical identification.

**PRIORITY REPAIR. **Several urgent commissions compete for limited forge time.

**MAKER'S MARK. **A damaged object bears a mark associated with a local craftsperson who denies making it.

**THE LOCK COMMISSION. **A client requests a specialized lock whose purpose raises questions.

**APPRENTICE ERROR. **An apprentice's mistake damages a socially important object and creates responsibility rather than a simple crafting penalty.

***Repeatable work: **Repair tools and equipment whose wear reflects current activities. Inspect commissioned objects and preserve maker and repair provenance.*

## Healer

**TWO PATIENTS, ONE DOSE. **Allocate scarce medicine under incomplete information.

**THE SYMPTOMS DO NOT MATCH. **A patient's story, symptoms, and family testimony conflict.

**HOUSE CALL AT NIGHT. **Travel and observation become part of treatment.

**QUARANTINE DEBATE. **Decide whether uncertain evidence justifies isolating a household.

**THE REFUSED TREATMENT. **A patient declines care for cultural, personal, or faction reasons.

**CASE NOTES. **Longitudinal records reveal a pattern across otherwise unrelated patients.

***Repeatable work: **Hold regular consultation hours for injuries and illness generated by world state. Prepare medicines from current stock and shortages.*

## Merchant

**THE PRICE OF PANIC. **Demand spikes after a rumor. Choose pricing, rationing, or limits while reputation reacts.

**QUESTIONABLE SUPPLIER. **Cheap goods arrive from a source with uncertain provenance.

**THE MISSING SHIPMENT. **Reconcile invoice, manifest, driver testimony, and actual inventory.

**EXCLUSIVE CONTRACT. **A faction offers guaranteed business in exchange for refusing competitors.

**WAREHOUSE SPACE. **Allocate scarce storage among customers with different urgency and influence.

**CREDIT WORTHINESS. **Decide whether to extend credit based on relationships and history rather than a hidden score alone.

***Repeatable work: **Reprice and source goods based on supply events. Post buy orders for goods demanded by residents and projects.*

## Wanderer

**THE ROAD NOTEBOOK. **Record routes, hazards, travel times, and landmarks that become useful to others.

**STRANDED TRAVELER. **Find and guide someone whose directions no longer match the road.

**THE SHORTCUT. **Test a rumored path whose advantage changes with weather.

**COURIER OF LAST RESORT. **Carry a message when normal delivery channels fail.

**A PLACE NOT ON THE MAP. **Investigate a traveler's description of a location no current map records.

**GUIDE THE EXPEDITION. **Choose route, pace, stops, and retreat decisions for a group journey.

***Repeatable work: **Update route conditions after weather and events. Guide or carry messages for travelers whose destinations vary.*

## Performer

**A SONG EVERYONE KNOWS DIFFERENTLY. **Collect and perform variants of a local song, revealing conflicting historical memory.

**THE DIFFICULT AUDIENCE. **Perform before factions with incompatible tastes and sensitivities.

**BENEFIT NIGHT. **Organize entertainment to fund a community need, recruiting other players as participants.

**SATIRE. **A humorous performance changes public discussion and may offend powerful residents.

**THE REQUESTED BALLAD. **A patron asks for a song associated with a private grief or scandal.

**STAGE THE STORY. **Turn an expedition account into public performance, deciding which details to dramatize, conceal, or attribute.

***Repeatable work: **Accept requests and perform at scheduled social gatherings. Collect stories and convert them into songs, recitations, or staged accounts.*

## Detective

**THE CONTRADICTORY CLOCK. **Reconcile witness times with clocks that are known to drift.

**FOLLOW THE MONEY. **Use invoices, tabs, wages, and purchases to test a theory.

**INTERVIEW UNDER PRESSURE. **A witness will speak only before another person arrives.

**THE INNOCENT SUSPECT. **Demonstrate why apparently strong evidence has an alternate explanation.

**CASE BOARD. **Maintain a persistent theory board linking evidence without declaring certainty.

**A CLIENT WHO LIES. **Solve the problem the client actually has while recognizing that the stated problem is false.

***Repeatable work: **Take player and NPC cases generated from disputes, losses, and suspicious observations. Review evidence boards and publish or privately share provisional theories.*

## Hound

**TRACK WITHOUT KILLING. **Identify and follow a suspected creature while the evidence for danger remains uncertain.

**PROFESSIONAL DISPUTE. **Two Hounds interpret the same signs differently and each asks for support.

**THE SAFE HOUSE. **Protect a witness or suspected creature from an angry crowd until facts can be established.

**FIELD TEST. **Evaluate a traditional monster-hunting method whose reputation exceeds its evidence.

**THE FALSE ALARM. **Investigate a frightening event and publicly acknowledge when no monster is responsible.

**WATCH THE WATCHERS. **Discover who has been tracking Hound patrols and why.

***Repeatable work: **Patrol rotating routes and record anomalies. Respond to reports of possible monsters with investigation before intervention.*

# 5. World-Event, Ambient, Location, and NPC Content

## 5.1 Ambient micro-content bank

**Purpose. **Text is the graphics engine. Ambient events provide movement, sensory change, overheard fragments, and occasional low-grade evidence. Most should be ignorable; some become meaningful only in combination.

**AMBIENT 01. **Gas lamps hiss louder as pressure changes in one street.

**AMBIENT 02. **A baker opens a rear door and warm bread smell reaches the lane.

**AMBIENT 03. **A newspaper runner repeats a headline with one word wrong.

**AMBIENT 04. **A church bell begins two seconds later than expected.

**AMBIENT 05. **A horse stamps whenever a cart passes from the Manor road.

**AMBIENT 06. **Two shopkeepers exchange a look and stop talking as someone approaches.

**AMBIENT 07. **Rain reveals older lettering beneath a painted sign.

**AMBIENT 08. **A drain carries red-tinted water that may be dye, rust, blood, or runoff.

**AMBIENT 09. **A shutter bangs three times and then remains still.

**AMBIENT 10. **A child counts windows on a building and starts over when corrected.

**AMBIENT 11. **A chimney begins smoking from a building believed empty.

**AMBIENT 12. **A messenger checks the same address twice before knocking.

**AMBIENT 13. **A woman buys one candle and leaves with three.

**AMBIENT 14. **A dog sleeps across a doorway and refuses to move for one visitor.

**AMBIENT 15. **A scrap of wrapping paper bears a university shipping mark.

**AMBIENT 16. **A carriage wheel leaves an unusual repeating impression in mud.

**AMBIENT 17. **A shop bell rings while the door remains closed.

**AMBIENT 18. **A pair of Hounds disagree quietly over a footprint.

**AMBIENT 19. **A church volunteer replaces flowers earlier than usual.

**AMBIENT 20. **A clock strikes the correct hour but the wrong number of times.

**AMBIENT 21. **A street musician stops midway through a tune when someone passes.

**AMBIENT 22. **A cellar vent exhales warm air on a cold morning.

**AMBIENT 23. **A vendor lowers a price as soon as a particular customer leaves.

**AMBIENT 24. **A Harbinger page is pasted over an older notice before anyone can read it.

**AMBIENT 25. **A stranger asks whether Frankenstein Village has always had the same number of streets.

**AMBIENT 26. **A porter carries a crate labeled FRAGILE upside down.

**AMBIENT 27. **A cat watches an empty roofline for several minutes.

**AMBIENT 28. **A window curtain closes after the observer looks away and back.

**AMBIENT 29. **A resident returns borrowed tools polished but missing one screw.

**AMBIENT 30. **A telegram arrives with a word crossed out by hand.

**AMBIENT 31. **A lamp flame briefly turns pale and then normal again.

**AMBIENT 32. **A merchant quietly removes an item from display when Hounds enter.

**AMBIENT 33. **A carriage passenger writes down the well inscription before asking what it means.

**AMBIENT 34. **A child sells a hand-drawn map of tunnels as a joke.

**AMBIENT 35. **A church collection box contains a foreign coin.

**AMBIENT 36. **A phonograph from inside a shop repeats a phrase before the needle is lifted.

**AMBIENT 37. **A puddle forms beneath a dry cart.

**AMBIENT 38. **A resident receives a package and immediately carries it to someone else.

**AMBIENT 39. **A public notice is signed with an office title but no personal name.

**AMBIENT 40. **Fog reaches one side of a square but not the other for several minutes.

## 5.2 NPC schedule examples

**THE APOTHECARY. **Morning shop hours; midday house calls; late afternoon preparation; selected evenings at the Tavern or private consultations; Sunday reduced hours; emergency call-outs can interrupt the schedule.

**THE HARBINGER EDITOR. **Early morning copy review; late morning reporting; afternoon interviews; publication deadline rush; evening Tavern observation; after major events, schedule shifts to special-edition mode.

**A SENIOR HOUND. **Morning patrol review; rotating field investigation; midday equipment maintenance; evening report exchange; unpredictable private visits to informants.

**A CHURCH OFFICER. **Morning duties; scheduled charity visits; afternoon records; evening services or meetings; night sanctuary responses; funerals override normal routine.

**THE LEASED SHOP. **Dark windows. An OPENING SOON sign. A crate visible through the glass that ticks at irregular hours. Letters arrive monthly in immaculate handwriting: orders, payments promised, apologies for the delay. No one has met the leaseholder.

**THE BURGOMASTER'S OFFICE. **Public petition hours; records work; council preparation; scheduled meetings; emergency session state; office persists even if office holder changes.

**A MERCHANT. **Delivery inspection; shop hours; market attendance; ledger work; supplier meetings; occasional travel to meet incoming wagons.

**A TAVERN REGULAR. **Workday location; predictable meal; evening Tavern seat; weekly family visit; one recurring absence that can become investigable if it changes.

## 5.3 Major NPC personal arc seeds

***These are role-level seeds, not fixed canon biographies. **Use them to ensure major residents have personal concerns beyond delivering lore.*

**THE LEASEHOLDER'S RIVAL. **A university colleague writes to the Harbinger disputing the absent leaseholder's methods and reputation. The conflict creates letters, procurement competition, and social scenes — fought entirely by post, since one of the combatants has never been seen.

**THE UNWANTED CUSTOMER. **Someone repeatedly comes to the dark shop seeking an oddity or procedure, and leaves letters the leaseholder never answers. Players may become intermediaries, witnesses, or investigators.

**THE LEASEHOLDER'S BROKEN INSTRUMENT. **An instrument ordered in the leaseholder's name arrives damaged. The ensuing correspondence — about blame, value, and repair — becomes technically interesting and socially revealing.

**JEKYLL: THE CONFIDENTIAL PATIENT. **A patient's privacy conflicts with public concern about symptoms or behavior.

**JEKYLL: THE FAILED REMEDY. **A treatment does not work as expected and Jekyll must revise his assumptions under public scrutiny.

**JEKYLL: THE COLLEAGUE'S LETTER. **A professional correspondent asks for advice on a case whose details echo local events.

**HARBINGER EDITOR: THE SOURCE. **A trusted anonymous source provides one piece of information that cannot be independently verified.

**HARBINGER EDITOR: THE RETRACTION. **The paper must decide how publicly to admit a serious mistake.

**HARBINGER EDITOR: THE OWNER'S PRESSURE. **Financial or political pressure threatens editorial independence.

**SENIOR HOUND: THE OLD CASE. **A past investigation is reopened when new evidence appears, exposing earlier assumptions.

**SENIOR HOUND: THE APPRENTICE. **A promising junior investigator becomes overconfident and must be corrected, protected, or allowed to fail.

**SENIOR HOUND: THE MONSTER WHO HELPED. **A person categorized as monstrous once saved the Hound's life, complicating professional doctrine.

**CHURCH OFFICER: THE EMPTY PEW. **A regular attendee stops coming and nobody agrees whether this is personal, political, spiritual, or practical.

**CHURCH OFFICER: THE DONOR. **A major donor demands influence over a charitable decision.

**CHURCH OFFICER: THE DOUBTFUL MIRACLE. **A reported miracle would benefit the church institutionally but the evidence is weak.

**BURGOMASTER'S OFFICE: SUCCESSION. **An office holder becomes unavailable and procedure for acting authority is disputed.

**BURGOMASTER'S OFFICE: OLD ORDINANCE. **A forgotten regulation suddenly matters to a current dispute.

**BURGOMASTER'S OFFICE: PUBLIC PETITION. **A popular request conflicts with the Truce or another old obligation.

## 5.4 Player-generated quest templates

**WANTED: WITNESSES. **A player posts a request for anyone present at a specified place and time to provide accounts.

**BUY ORDER. **A Merchant or institution posts quantity, quality, deadline, and payment for needed goods.

**GUIDE NEEDED. **A player requests a guide for a route, expedition, or return trip.

**RESEARCH ASSISTANCE. **A Detective or Chronicler asks others to search records, locations, or testimony for a defined question.

**MISSING PERSON. **A player creates a structured notice with last known location, description, and contact.

**COMMISSION. **A player requests a crafted item with materials, deadline, and confidentiality setting.

**ESCORT REQUEST. **A player asks companions for a scheduled trip or social appearance.

**PUBLIC MEETING. **A player schedules an in-character gathering around a stated issue.

**REWARD FOR RETURN. **A lost or stolen object receives a public or private reward notice.

**APPRENTICE WANTED. **A Master Calling invites another player into recurring work or training.

**THEORY REVIEW. **A player publishes a provisional theory and explicitly asks for contradictory evidence.

**COMMUNITY COLLECTION. **A player starts a shared archive or collection with submission rules and provenance requirements.

## 5.5 Community projects

**REPAIR THE FOOTBRIDGE. **Contributions include timber, metalwork, labor, permits, transport, and funding. Completion changes travel time or route reliability.

**MAP THE SHALLOW CATACOMBS. **Players contribute verified segments, annotations, and dates to a shared map.

**RESTORE THE PUBLIC ARCHIVE. **Recover, clean, index, and house records damaged by age or an event.

**FUND A NEW PRESS. **Raise money, source parts, move equipment, and decide institutional ownership of improved Harbinger machinery.

**WINTER STORES. **Contribute food, fuel, medicine, transport, and storage before scarcity events.

**MEMORIAL TO THE WAR. **Collect names, debate wording, commission materials, and choose placement for a public memorial.

**STREET LIGHTING EXPANSION. **Survey dark areas, fund lamps, arrange installation, and accept that improved lighting changes some nighttime content.

**REOPEN THE OLD ROAD. **Clear, survey, repair, and politically negotiate a route whose reopening changes travel and faction interests.

## 5.6 Hidden discoveries

**LOOSE STONE. **A wall stone shifts and exposes a narrow cavity containing mundane older objects.

**NAMES UNDER PAINT. **Old names remain beneath a repainted shop sign.

**SECOND DRAIN. **A cellar drain connects somewhere unexpected on a map.

**MARGINAL NOTE. **A library book contains a reader's annotation that contradicts the printed text.

**PHOTOGRAPHER'S MARK. **A recurring mark appears at the edge of several unrelated photographs.

**OLD KEYHOLE. **A sealed door has a keyhole despite no visible handle.

**HIDDEN INVOICE. **A shop ledger contains a folded receipt under the binding.

**REUSED STONE. **A building foundation includes carved stone from an older structure.

**FALSE BOTTOM. **A common storage box has a concealed compartment with no current contents.

**ROOFLINE SIGNAL. **From one high vantage point, several ordinary lights align into an unexpected pattern.

**UNLISTED GRAVE. **A grave marker exists without a registry entry.

**DIFFERENT INSCRIPTION. **A rubbing reveals letters the naked eye misses on a weathered stone.

**OLD BELL PULL. **A disused cord disappears into a wall.

**SERVICE PASSAGE. **A narrow staff route links buildings more directly than public streets do.

**FORGOTTEN WATER MARK. **Flood marks show a building once experienced water far above current expectations.

**MATCHING REPAIR. **The same unusual repair technique appears on objects owned by unrelated households.

**UNUSED TELEGRAPH CODE. **A codebook includes abbreviations that appear nowhere in current commercial traffic.

**PORTRAIT BACKING. **The rear of a framed portrait contains a date or name not visible while displayed.

**FOUNDATION HATCH. **A maintenance hatch is hidden by furniture, not supernatural concealment.

**THREE SCRATCHES. **A repeating mark appears in locations whose only known connection is a delivery route.

## 5.7 Legendary discoveries

**THE OLDEST SURVIVING TRUCE COPY. **A version of the Truce text predating the public inscription differs in a small but consequential phrase.

**THE ROOM NO MAP AGREES ON. **Multiple catacomb maps omit or misplace the same chamber.

**THE FIRST HARBINGER. **A very early newspaper issue documents Frankenstein Village before several current institutions existed.

**THE ABANDONED OBSERVATORY. **A difficult-to-reach structure contains decades of sky, weather, and Mist observations.

**A COMPLETE ARRIVAL REGISTER. **A hidden or misfiled ledger contains names from a period believed undocumented.

**THE UNSENT LETTER. **A historically important resident wrote a letter that was never delivered, offering perspective rather than absolute truth.

**THE FORGOTTEN BELL. **A sealed mechanism can ring a bell no current resident knows exists.

**THE MAP THAT PREDICTS NOTHING. **A famous-looking map turns out not to be prophetic at all, but its ownership history reveals a more interesting network of people.

## 5.8 AI-compatible activities without AI-only rules

**MONTH-LONG WATCH. **Any player can contribute timestamped observations to a persistent watch log.

**ARCHIVE COMPARISON. **Compare many Chronicle, Harbinger, and council entries for repeated names, phrases, or dates.

**ROUTE REVALIDATION. **Regularly walk known routes and flag changes in time, access, or landmarks.

**RUMOR PROVENANCE AUDIT. **Trace a rumor backward through people who repeated it and identify where details changed.

**MARKET PRICE LOG. **Record prices and availability over time to detect shortages or unusual purchasing.

**CATACOMB MAPPING SHIFT. **Add one verified segment per session to a shared survey.

**NIGHT WATCH CALLING. **Maintain a socially useful presence during low-population hours and generate reports for later players.

**CORRESPONDENCE INDEX. **Catalog letters, telegrams, notices, and newspaper references without claiming their contents are objectively true.

## 5.9 Retirement and death content

**RETIREMENT: HAND OVER THE KEYS. **A retiring Innkeep or shop owner chooses a successor or closes the establishment, creating property and relationship consequences.

**RETIREMENT: FINAL CHRONICLE ENTRY. **The character submits a personal account of their life in Frankenstein Village, explicitly framed as their perspective.

**RETIREMENT: SETTLE THE LEDGER. **Debts and credits are paid, forgiven, inherited, or intentionally left unresolved.

**RETIREMENT: CHOOSE AN APPRENTICE. **A Master passes tools, access, or institutional responsibility to another character.

**RETIREMENT: FAREWELL SUPPER. **Friends and rivals gather, creating one last social scene whose memories remain.

**RETIREMENT: INTO THE MISTS. **A character deliberately departs. The game records departure without confirming survival or destination.

**RETIREMENT: LEAVE THE COLLECTION. **A personal archive is donated, divided, sold, or destroyed.

**RETIREMENT: RETIRE THE MASK. **The persistent player begins again with a new character while the former character remains in records, relationships, and world history.

**DEATH: THE FUNERAL. **Attendance, eulogies, ritual choices, and absences become social history.

**DEATH: THE ESTATE. **Possessions, business ownership, debts, and unfinished commissions need resolution.

**DEATH: THE LAST CASE. **Open investigations survive their investigator and can be inherited through notes or testimony.

**DEATH: THE OBITUARY. **The Harbinger publishes a public account that may differ from friends' memories.

**DEATH: THE MEMORIAL ENTRY. **The Chronicle decides what belongs in permanent history and what remains private.

**DEATH: UNFINISHED DEBT. **A debt owed by or to the dead becomes an estate, family, or moral question.

**DEATH: THE EMPTY ROUTINE. **NPCs and locations reflect the absence of someone who used to appear there on schedule.

**DEATH: THE SUSPICIOUS DEATH. **If circumstances justify it, death itself creates investigation, but not every death should secretly be murder.

# 6. Full Implementation Packets

**These packets demonstrate the expected depth for engineering handoff. **They are deliberately more detailed than the seed bank. Writers can use this structure as the template for major authored content.

## DM-Q-0001 - The Wrong Trunk

**Family: **Newcomer / private mystery / social

**Canonical status: **Working content; does not alter canon.

**Hook: **On arrival, the player is handed a trunk tagged with their room or account number but bearing another person's initials under the newer label.

**Objective world state: **The trunk genuinely belonged to an earlier traveler. The server does not need to decide at this stage whether the owner is dead, missing, departed, or still in Frankenstein Village under another identity.

**NPC beliefs: **The porter believes it is a simple luggage error. The innkeeper remembers the initials but not the face. A Harbinger worker remembers an old classified notice with the same initials. One resident confidently remembers a different person entirely.

**Evidence: **Old travel tag; one personal object; a receipt; wear marks; registry entry or absence; testimony from two residents; optional Harbinger archive reference.

**Player actions: **Return it unopened; inspect it; ask around; report it; keep it temporarily; sell or surrender specific contents where allowed; publish a notice; search records.

**Autonomous progression: **After one world day the innkeeper moves unclaimed luggage to storage. After several days a claimant may appear, with identity generated from one of several authored variants.

**Outcome space: **Returning immediately earns trust but less information. Investigating may expose private material and create a future relationship. Publicizing it can attract multiple claimants. Keeping property creates ownership and reputation risk.

**Persistence: **Relationship changes with innkeeper and claimant; item provenance persists; any public notice becomes searchable; the claimant can become a later NPC hook.

**Propagation: **Rumor: a newcomer opened someone else's trunk. Harbinger classified: FOUND PROPERTY. Chronicle only if the trunk later matters to a larger event.

**Multiplayer: **Other players can help identify items, search records, or become witnesses to how the newcomer handled the property.

**QA notes: **Ensure no path requires theft. Ensure a player who logs out can resume through storage or aftermath. Do not reveal objective owner truth merely by inspecting the trunk.

## DM-Q-0017 - Tomorrow's Obituary

**Family: **Harbinger / small mystery / timed

**Canonical status: **Working content.

**Hook: **The Harbinger receives a properly formatted obituary for a living resident, dated for the next issue.

**Objective world state: **The submission is real and traceable to a delivery path, but the author and intent may vary by content variant. The system never treats the predicted death as guaranteed.

**NPC beliefs: **The editor suspects a threat or cruel joke. The subject may be frightened, amused, angry, or secretive. Hounds see possible warning value. A rival paper contact may recognize phrasing from older notices.

**Evidence: **Original copy; ink and paper; delivery testimony; office log; wording similarities; the subject's schedule; previous obituaries.

**Player actions: **Warn the subject; investigate quietly; publish; suppress; alter the copy; set a watch; trace materials; interview staff.

**Autonomous progression: **If nobody acts, editorial policy determines publication. The subject continues their normal schedule unless informed through another channel.

**Outcome space: **The subject may survive regardless, making the mystery about intent. A preventable unrelated accident can occur in some variants, but never as punishment for failing to believe prophecy.

**Persistence: **Editorial reputation, subject relationship, public rumor, watch logs, and source trail remain in the world.

**Propagation: **Published obituary or correction; Tavern speculation; possible follow-up anonymous letter.

**Multiplayer: **Different players can protect the subject, trace the submission, and debate publication simultaneously.

**QA notes: **Do not make death inevitable. Preserve multiple plausible theories. Verify the living subject remains playable throughout the investigation unless an independently authored event changes that.

## DM-Q-0033 - The Tribute Runs Thin

**Family: **Long mystery chain / cross-faction / infrastructure

**Canonical status: **Working content built on canonical tribute.

**Hook: **Someone responsible for the tribute observes that the expected quantity is not reaching the lower collection point.

**Objective world state: **There is a measurable discrepancy. Its immediate cause can be infrastructure loss, diversion, theft, accounting error, or a combination. The deeper meaning of the Truce remains untouched.

**NPC beliefs: **Villagers fear punishment. The brood suspects disrespect or theft. The council fears panic. Hounds suspect leverage. Church figures disagree about involvement.

**Evidence: **Measurements at the well; pipe or channel condition; old plans; witness schedules; container volumes; maintenance records; signs of access; prior discrepancies.

**Player actions: **Inspect; repair; negotiate access; conceal the shortage; increase tribute; trace diversion; publish; accuse; create a temporary bypass.

**Autonomous progression: **The discrepancy continues. Interested factions take increasingly visible actions as deadlines pass. NPCs may independently repair, guard, or investigate sections.

**Outcome space: **Players can solve the immediate loss without satisfying every faction. A repaired system can reveal older modifications that seed future content.

**Persistence: **Changed access to infrastructure; faction Standing; new watch schedules; public fear level; possible permanent maintenance location.

**Propagation: **Rumors about punishment; Harbinger debate about public works; Chronicle entry only if the incident materially changes the Truce's administration.

**Multiplayer: **Surface measurement, records, lower negotiation, and physical inspection can proceed in parallel.

**QA notes: **Never silently redefine the canonical Truce. Distinguish measured shortage from beliefs about what the shortage means.

## DM-Q-0040 - Dinner Below

**Family: **Social expedition / faction / invitation

**Canonical status: **Working content.

**Hook: **A player or group receives a formal invitation to dine with residents of the catacombs under declared rules of hospitality.

**Objective world state: **The gathering is real, socially significant, and governed by etiquette. Violence is not the intended gameplay loop and can be structurally restricted by the event rules if needed.

**NPC beliefs: **Guests disagree about why they were invited. Hosts have individual motives rather than a shared hive mind. Surface factions interpret attendance according to their own interests.

**Evidence: **Seating arrangement; invitation wording; menu choices; who arrives; who is absent; private side conversations; references to old debts; gifts or requests.

**Player actions: **Attend; decline; bring a guest if permitted; observe; negotiate; ask questions; make promises; refuse requests; leave early; later disclose or conceal what occurred.

**Autonomous progression: **The dinner proceeds on schedule without every invited player. NPC guests form relationships and exchange information whether players attend or not.

**Outcome space: **Possible invitations, debts, insults, access, warnings, rumors, or misunderstandings. No single ending is the correct social outcome.

**Persistence: **Guest list history; faction Standing; private debts; future invitations; knowledge flags; altered NPC attitudes.

**Propagation: **Surface gossip about who attended; selective accounts; Harbinger may report the gathering only if information escapes.

**Multiplayer: **Private and public conversation channels, seating, simultaneous side discussions, and post-event comparison are core.

**QA notes: **Do not expose account substrate. Do not treat all vampires as one political actor. Ensure declining the invitation remains a valid choice with different consequences.

## DM-Q-0057 - Your Fortune Has Already Happened

**Family: **Mystics / private mystery / identity

**Canonical status: **Working content.

**Hook: **A Mystic describes an event from the character's declared or hidden past but phrases it as something that has not yet happened.

**Objective world state: **The reading can be generated from approved character-history tags plus ambiguous authored language. The system does not certify precognition.

**NPC beliefs: **The Mystic treats the reading seriously but may interpret it differently from the player. Observers may see technique, coincidence, supernatural insight, or social manipulation.

**Evidence: **Exact wording; card or method used; prior statements; whether the Mystic had access to public biography; reactions from witnesses.

**Player actions: **Challenge the reading; ask follow-up questions; conceal reaction; share it; investigate how the Mystic could know; wait for later parallels.

**Autonomous progression: **The Mystic continues normal work. Related phrases may recur in later generated content if the player opts into Hyde pressure.

**Outcome space: **The player can discover a mundane information route, remain uncertain, or create a self-fulfilling social consequence by acting on the reading.

**Persistence: **Private note; relationship with Mystic; possible Hyde hook; rumors only if the player or witnesses disclose the content.

**Propagation: **Optional Tavern retelling; no automatic Chronicle significance.

**Multiplayer: **Other players can witness the reading but do not receive hidden character data unless the scene reveals it in-world.

**QA notes: **Protect private backstory data. Avoid claims of objective prophecy. Parameterize wording so repeated readings do not become a deterministic spoiler system.

## DM-Q-0060 - The Road That Returns

**Family: **Long mystery / expedition / cartography

**Canonical status: **Working content; must not answer what the Mists are.

**Hook: **Travelers report that a route intended to leave the valley returns them to Frankenstein Village from an unexpected direction.

**Objective world state: **The route can be tested and mapped, but the world model intentionally withholds a final explanation of the Mists.

**NPC beliefs: **Wanderers blame navigation, Mystics use symbolic language, Hounds suspect manipulation, villagers treat the story as old news, newcomers may not believe any of them.

**Evidence: **Travel times; compass behavior; landmarks; weather; carried objects; synchronized clocks; notes from separate expeditions; historical maps.

**Player actions: **Survey; mark the route; split teams; carry synchronized records; test different times and weather; turn back; publish findings.

**Autonomous progression: **Weather and Mist conditions change. Other travelers attempt the road and add new reports.

**Outcome space: **Players establish reliable local facts such as typical return points, time distortions if any are explicitly implemented, and safe procedures. They do not receive the cosmological answer.

**Persistence: **Maps, travel logs, route risk estimates, new landmarks, public theory debates.

**Propagation: **Harbinger reports; Wanderer route notes; Chronicle may record verified expedition results.

**Multiplayer: **Parallel expeditions can test variables and compare results.

**QA notes: **Never reveal an authoritative Mist origin. Every extraordinary effect must be explicitly implemented rather than assumed from genre.

## DM-Q-0101 - The Long Blackout

**Family: **Server-wide event

**Canonical status: **Working event framework.

**Hook: **Electrical service and selected gas systems fail across multiple districts within minutes of each other.

**Objective world state: **The event has a defined infrastructure cause or causes at the local level, but rumors may immediately blame the Manor, sabotage, weather, or the catacombs.

**NPC beliefs: **Every faction interprets the outage through existing concerns. Businesses care about loss, Hounds about visibility, the Harbinger about reporting, healers about patients, and everyone about what the Manor's apparatus is doing unattended.

**Evidence: **Failure times by district; generator state; weather; lamp behavior; witness reports; maintenance logs; electrical measurements.

**Player actions: **Repair; light streets manually; escort residents; protect property; continue medical work; monitor Manor lights; publish; investigate sabotage; ration fuel.

**Autonomous progression: **NPC services degrade or adapt according to contingency plans. Crime, accidents, rumors, and public gatherings may emerge from the outage state.

**Outcome space: **Power can return unevenly. Investigation may establish several causes rather than one grand culprit.

**Persistence: **Repair needs, economic losses, injuries, articles, public confidence, new lighting projects, altered preparedness.

**Propagation: **Many local quests, special Harbinger issue, council hearing, possible Chronicle entry.

**Multiplayer: **Designed for distributed participation across the whole server rather than one central objective.

**QA notes: **Performance test simultaneous timers and generated tasks. Ensure low-population periods still progress sensibly through NPC contingency behavior.

## DM-Q-0112 - The Public Theory Board

**Family: **Player-generated / investigation infrastructure

**Canonical status: **Systemic content feature.

**Hook: **Detectives, Hounds, Chroniclers, or ordinary players can post a named theory tied to evidence references.

**Objective world state: **The board stores claims and cited evidence, not truth scores. Players can add support, contradiction, or new questions.

**NPC beliefs: **NPCs may read or react to public theories according to schedule, interests, and Standing. Publication can change behavior even when the theory is wrong.

**Evidence: **Links to discoverable evidence objects, testimony records, Harbinger articles, Chronicle entries, and player depositions.

**Player actions: **Post; revise; retract; cite; challenge; endorse; copy privately; ask for evidence.

**Autonomous progression: **Old theories persist with timestamps. Events can automatically mark cited evidence as outdated, destroyed, or superseded without deleting the theory.

**Outcome space: **The board creates social scholarship, rival schools of thought, and a trail of how community interpretation changes.

**Persistence: **Versioned theory history and attribution.

**Propagation: **Harbinger can quote public theories; rivals can react; later players can reconstruct past debates.

**Multiplayer: **The feature is inherently collaborative and adversarial in an epistemic rather than combat sense.

**QA notes: **Never auto-rank theories by hidden truth. Moderate abuse separately from in-character disagreement. Preserve edit history.

# 7. Launch Inventory Targets and Acceptance Tests

**Launch-scale target. **The numbers below are a content-density target, not a requirement that every row be hand-authored as a unique quest. Repeatable systems, parameterized incidents, and cross-linked world events should produce a large share of the playable surface.

| **Content family** | **Launch target** |
|---|---|
| Newcomer scenarios | 12 |
| Small mysteries | 30 |
| Major mystery chains | 10-12 |
| Civic quests | 30 |
| Calling-specific authored quests | 6 per Calling minimum |
| Repeatable professional jobs | 8-12 per Calling |
| Faction quests | 8-10 per faction |
| Cross-faction conflicts | 20 |
| Expedition locations | 10-12 |
| Social expeditions | 12 |
| Group investigations | 12 |
| Timed incidents | 30 |
| Random incident templates | 75+ |
| Server-wide event frameworks | 10 |
| Community projects | 6+ |
| Hidden discoveries | 50+ |
| Major NPC personal arcs | 3-5 per major NPC |
| Rumor seeds | 250+ |
| Ambient room events | 300+ |
| Harbinger templates | 50+ |
| Player-request templates | 30+ |

## Quest acceptance test

- The content has at least one natural discovery path that does not require a floating quest marker.
- The objective world state is separated from NPC belief and rumor.
- At least one player decision changes something other than a reward payout.
- The quest defines what happens if nobody intervenes.
- Time matters where appropriate and does not merely freeze while the player is offline.
- Multiplayer participation allows distinct contributions instead of making everyone follow one leader.
- The outcome emits at least one useful consequence: rumor, relationship, debt, article, access change, location state, item provenance, schedule change, or follow-up.
- Failure or delay produces playable aftermath rather than only a dead end.
- Any number shown to the player has a behavioral effect. Decorative social variables are removed.
- The quest does not reveal hidden account substrate inside the in-character world.
- The quest does not answer an intentionally unresolved Bible question unless the World Bible is explicitly revised.
- The quest still makes sense after another player has already interacted with part of it.
- Required prose includes normal, active, aftermath, and return-visit variants where state changes are visible.
## Location acceptance test

- Normal description plus time-of-day variation where meaningful.
- Weather or event variation where meaningful.
- NPC schedule integration.
- Ambient event pool.
- Searchable details and at least one non-obvious observation.
- Rumor or information sources.
- At least one recurring activity.
- Several quest hooks or state dependencies.
- Historical or social context that can be learned without an exposition dump.
- Altered states after major events.
## Persistent NPC acceptance test

- Occupation or social role.
- Daily and weekly schedule.
- Distinct conversational priorities.
- Known rumors with provenance.
- Relationships to other residents.
- Current concern and private concern.
- At least one recurring need.
- At least one personal arc seed.
- Reaction rules for major world events.
- Remembered player interactions where implementation allows.
- Beliefs about unresolved mysteries separated from objective state.
> The launch loop is successful when a player can enter with no plan, notice change, hear multiple leads, choose an activity, involve other people, miss something because time passed, produce a persistent consequence, and leave with a reason to return.

***End of v0.3 handoff. **The seed bank is intentionally broader than the initial implementation slice. Promote content into canon only through the World Bible. Prefer connecting these seeds into shared state over shipping them as isolated quest chains.*
