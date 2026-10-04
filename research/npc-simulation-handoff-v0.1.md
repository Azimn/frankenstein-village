FRANKENSTEIN VILLAGE NPC SIMULATION HANDOFF v0.1
Working title only
Date: 2026-10-01

PURPOSE

This document is a self-contained developer handoff for the NPC simulation layer of a persistent text MMO currently using the temporary working name "Frankenstein Village."

The game is intended to feel like a living social simulation rather than a static MUD populated by quest dispensers. Human players, external AI players, and server-side NPCs should all occupy the same world. NPCs should have schedules, needs, relationships, beliefs, memories, commitments, jobs, and reactions to changing world events. The simulation should remain inexpensive enough to run on modest hardware.

The central implementation principle is:

THE SERVER OWNS THE WORLD STATE.
THE NPC SIMULATION OWNS WHAT CHARACTERS KNOW, WANT, REMEMBER, AND DECIDE.
THE DIALOGUE LAYER ONLY DECIDES HOW AN NPC EXPRESSES AN INTENT.

Do not use an LLM as the authoritative source of NPC identity, memory, knowledge, quest state, or world truth.


======================================================================
1. CURRENT STORY AND IP DIRECTION
======================================================================

The project is moving away from film and theme-park adaptations and toward public-domain literary source material plus original project-owned worldbuilding.

The temporary village name is:

Frankenstein Village

This is not intended as the final public-facing name. A unique village name is still being developed.

Do not hard-code the display name "Frankenstein Village" into systems, database schemas, room IDs, quest IDs, or save structures. Use stable internal identifiers such as:

village_main
world_primary_settlement
settlement_001

Then resolve the displayed name from configuration or content data. This makes a later rename inexpensive.

The earlier name "Darkmoor" or "Darkmoor Village" should not be used for the project. Universal Orlando currently uses "Darkmoor Village" as the village in its Dark Universe land at Epic Universe.

Official Universal reference:
https://www.universalorlando.com/web/en/us/things-to-do/character-encounters/dark-universe-character-encounters

Dark Universe official page:
https://www.universalorlando.com/web/en/us/epic-universe/worlds/dark-universe

The new content rule is:

Use the original public-domain novels as source canon.
Use project-original material to connect and expand them.
Do not import film-only characters, names, costumes, designs, dialogue, plot devices, or iconography unless they are independently present in the source novels or separately cleared.

Important examples for the current audit:

Mary Shelley's novel uses Victor Frankenstein. "Henry Frankenstein" is associated with the Universal film adaptation and should not be treated as novel canon.

Dr. Septimus Pretorius is a character from Bride of Frankenstein, not Mary Shelley's novel. If the game moves to novel-source-only canon, Pretorius must be removed, replaced, or rebuilt as a genuinely original character with a different identity, history, dialogue, visual concept, and role.

The famous "Bride of Frankenstein" as an animated female monster is not a character who comes to life in Shelley's novel. Victor begins creating a female companion and destroys the unfinished body before animating it.

Ygor and similar Universal-specific supporting characters should not be assumed to be available simply because Frankenstein itself is public domain.

Victor Frankenstein, Robert Walton, Elizabeth Lavenza, Henry Clerval, the Creature, Justine Moritz, Alphonse Frankenstein, and other characters actually appearing in Shelley's text are literary-source characters.

Count Dracula, Jonathan Harker, Mina Harker, Lucy Westenra, Abraham Van Helsing, Dr. Seward, Arthur Holmwood, Quincey Morris, Renfield, and related novel elements come from Bram Stoker's Dracula.

Henry Jekyll, Edward Hyde, Gabriel John Utterson, Dr. Lanyon, and related novel elements come from Robert Louis Stevenson's Strange Case of Dr Jekyll and Mr Hyde.

Source edition choices should be documented. Frankenstein exists in important 1818 and 1831 editions with differences. Do not casually merge them. Pick a primary source edition for canon and record deviations explicitly.

PROJECT GUTENBERG SOURCE LINKS

Frankenstein, general Project Gutenberg edition:
https://www.gutenberg.org/ebooks/84

Frankenstein, 1818 edition:
https://www.gutenberg.org/ebooks/41445

Frankenstein, 1831 edition:
https://www.gutenberg.org/ebooks/42324

Dracula:
https://www.gutenberg.org/ebooks/345

Strange Case of Dr Jekyll and Mr Hyde:
https://www.gutenberg.org/ebooks/43

Sherlock Holmes, The Case-Book of Sherlock Holmes:
https://www.gutenberg.org/ebooks/69700

Project Gutenberg identifies the Frankenstein, Dracula, and Jekyll and Hyde texts above as public domain in the USA. Public-domain status can vary by jurisdiction, so international commercial distribution should still receive a jurisdiction-specific review.

Project Gutenberg is a convenient source repository. The project should not copy Project Gutenberg headers, branding, legal notices, or metadata into the game. Use the underlying public-domain literary text as source material and retain internal source citations for design provenance.


======================================================================
2. NPC DESIGN GOAL
======================================================================

NPCs should not feel like static dialogue trees that wait for players.

A convincing resident should be able to:

Have a routine.
Deviate from that routine when something matters.
Know some things and not know others.
Be mistaken.
Hear rumors.
Remember selected events.
Form opinions about people.
Keep or break promises.
Have needs and obligations.
Act while no player is watching.
Create consequences that later become quests or rumors.
Change gradually because of accumulated experience.

The system should favor persistent state and consequences over expensive generative reasoning.

The game should be able to produce situations such as:

The apothecary normally opens at 8:00.

A close friend disappears overnight.

At 7:50, the apothecary evaluates several possible actions.

Open shop: utility 78.
Search for friend: utility 91.
Attend church: utility 25.
Sleep longer: utility 34.

The apothecary searches for the friend.

A player arrives at 8:15 and finds the shop closed.

There was no authored quest called "The Apothecary Is Closed." The simulation created a usable story hook from persistent NPC state.

That is the target behavior.


======================================================================
3. RECOMMENDED ARCHITECTURE
======================================================================

Use a layered system.

LAYER A: WORLD TRUTH

The server owns objective facts.

Examples:

The Manor light activated at 23:43.
A parcel is physically in room cellar_04.
NPC Mara is at the church.
The bridge is damaged.
Player 127 gave NPC Elias a letter.
Event EVT_884 happened.

NPCs never receive unrestricted access to this layer.

LAYER B: PERCEPTION

NPCs receive only events they could reasonably perceive.

Examples:

Saw the blue light.
Heard a scream from the alley.
Read the Harbinger.
Was told a rumor by the innkeeper.
Was present when a player made a promise.

LAYER C: BELIEFS

Perception updates beliefs.

Example records:

saw(manor_light, 1897-10-03 23:43), confidence 0.96
heard(creature_near_well, source=innkeeper), confidence 0.42
believes(player_127_is_reliable), confidence 0.71
suspects(council_clerk_hid_letter), confidence 0.35

Belief is not truth.

This is critical.

Two NPCs should be able to disagree because their belief stores differ.

LAYER D: INTERNAL STATE

Suggested compact state:

fatigue
hunger
safety
affiliation
duty
curiosity
stress
material_security

Do not begin with forty needs. Start small and expand only when a state produces meaningful gameplay.

LAYER E: RELATIONSHIPS

Do not reduce every relationship to one "friendship" score.

A compact relationship can contain:

affinity
trust
fear
respect
debt
familiarity
recent_grievance

Only store detailed relationships for meaningful contacts.

LAYER F: GOALS AND COMMITMENTS

Goals represent longer-lived intentions.

Examples:

keep the shop profitable
protect daughter
learn what caused the Manor light
avoid the Hounds
repay debt to Elias
gain council influence

Commitments represent explicit promises or obligations.

Example:

actor: npc_apothecary
target: player_127
action: meet
place: village_well
time: 1897-10-04 19:00
purpose: discuss missing patient
status: pending

Commitments should compete with other needs and events rather than teleport NPCs into place.

An NPC may keep a promise.
An NPC may deliberately break it.
An NPC may be prevented from keeping it.
The system records what happened and relationships update accordingly.

LAYER G: UTILITY DECISION

For normal everyday activity, use inexpensive utility scoring.

Conceptually:

action_score =
need_weight
+ schedule_weight
+ goal_weight
+ personality_weight
+ relationship_weight
+ event_weight
+ habit_weight
+ small_variation
- cost

The highest valid action wins, or the result is sampled from the top few actions to avoid perfect repetition.

Candidate actions can remain small:

work
eat
sleep
travel_home
visit_tavern
visit_church
talk_to_person
seek_person
investigate_event
deliver_item
buy_supply
sell_item
avoid_person
seek_help
spread_rumor
keep_watch
fulfill_commitment
collect_debt
help_friend

Twenty arithmetic evaluations are vastly cheaper than an LLM inference.

LAYER H: BEHAVIOR SEQUENCES

Use behavior trees or small state machines for complex reactive sequences rather than daily life.

Example:

FIRE EVENT
detect danger
check nearby people
raise alarm
attempt extinguishing if safe
assist vulnerable person
flee if risk threshold exceeded

Utility AI answers:
"What should I do?"

A behavior tree answers:
"How do I carry out this multi-step response?"

LAYER I: ACTION

The NPC performs a real game action through the same world interfaces used by other entities where practical:

move
speak
give
take
buy
sell
write
read
wait
observe
open
close
work
rest

LAYER J: EVENT EMISSION

Actions generate events.

The event system then becomes input for other NPCs.

This creates the loop:

WORLD TRUTH
to PERCEPTION
to BELIEF
to INTERNAL STATE
to DECISION
to ACTION
to NEW WORLD EVENT
to OTHER CHARACTERS' PERCEPTION

LAYER K: DIALOGUE RENDERER

The simulation decides:

What the NPC knows.
What the NPC believes.
What the NPC wants.
What the NPC is willing to reveal.
What conversational intent they currently have.

The dialogue renderer decides how to phrase that intent.

This layer may be:

Authored templates.
Phrase banks.
Grammar systems.
Procedural text.
A local small language model.
A remote language model for selected scenes.

The language model must not invent authoritative facts.


======================================================================
4. SIMULATION LEVEL OF DETAIL
======================================================================

Do not run every NPC at maximum frequency.

Use simulation level of detail.

LOD 0: ACTIVE SCENE

NPC is in a room with active players or in an important live event.

Evaluate fine-grained actions frequently.

Possible cadence: every few seconds to tens of seconds depending on the interaction system.

LOD 1: NEARBY OR RELEVANT

NPC is near active players, participating in an unfolding quest, traveling, or responding to an event.

Evaluate periodically.

Possible cadence: every 30 to 120 seconds.

LOD 2: NORMAL BACKGROUND RESIDENT

NPC is elsewhere in the village.

Evaluate only on meaningful schedule boundaries, incoming events, commitments, or coarse simulation ticks.

Possible cadence: every 5 to 15 game minutes.

LOD 3: DORMANT OR DISTANT

NPC is asleep, off-map, or in an unloaded distant region.

Do not simulate moment-to-moment behavior.

Resolve blocks of activity.

Example:

08:00 to 12:00
worked at forge
purchased coal
spoke with priest
heard rumor R142
fatigue +12
trust(priest) +1

When the NPC becomes relevant again, expand from the accumulated state.

The important rule is:

SIMULATE CONSEQUENCES, NOT UNUSED DETAIL.

This is the primary way to support hundreds or potentially thousands of residents without large hardware costs.


======================================================================
5. EVENT-DRIVEN WORLD
======================================================================

Prefer events over constant polling.

Example objective event:

EVT_MANOR_LIGHT_0042
type: unusual_light
location: manor_east_tower
time: 23:43
color: blue
duration: 41 seconds
visibility_radius: 4
source_truth: unknown_to_public

Nearby NPCs receive perception checks.

NPC A sees it directly and stores:

saw blue light at east tower
confidence 0.97

NPC B is inside and sees nothing.

NPC A tells NPC C in the tavern.

NPC C stores:

heard strange light was seen at Manor
source NPC A
confidence 0.63

NPC C exaggerates it to NPC D.

By morning the rumor ecosystem may contain:

Frankenstein has returned.
Someone is living in the Manor.
Lightning struck the tower.
A scientist restarted the apparatus.
The vampires are signaling the hill.

Only the original event is objective truth.

This supports the game's rumor-as-evidence design without requiring the writers to hand-author every rumor variant.


======================================================================
6. MEMORY MODEL
======================================================================

Do not save a permanent transcript of everything an NPC experiences.

Use three memory forms.

SHORT-TERM CONTEXT

Small rolling buffer of recent events.

Example target:
10 to 30 recent events.

EPISODIC MEMORY

Store only salient experiences.

A simple salience score can combine:

novelty
emotional intensity
goal relevance
relationship relevance
danger
social significance
repetition

Example:

salience =
novelty * 0.20
+ emotion * 0.20
+ goal_relevance * 0.20
+ relationship_relevance * 0.15
+ danger * 0.15
+ social_significance * 0.10

Keep perhaps 20 to 100 meaningful episodes depending on NPC importance.

SUMMARY MEMORY

Compress repeated ordinary experiences.

Instead of:

Worked with Tomas on Oct 1.
Worked with Tomas on Oct 2.
Worked with Tomas on Oct 3.
Worked with Tomas on Oct 4.

Store:

Worked regularly with Tomas during early October.
Relationship familiarity increased.
Tomas was usually dependable.

Important residents can have larger memory budgets than incidental villagers.

Memory should support forgetting.

Forgetting is useful because it prevents infinite growth and makes social knowledge imperfect.

Do not delete all effects when an episode fades. A forgotten event may still leave:

relationship change
habit change
fear association
belief adjustment
debt
commitment
reputation effect


======================================================================
7. AFFECT RESIDUE
======================================================================

Do not reset NPC emotion after each interaction.

Use slow-moving residues such as:

tension
confidence
resentment
fear
sociability
hope

These should decay gradually.

A frightening night may make someone cautious for several days.

A public humiliation may leave resentment even after the exact wording is forgotten.

A successful village celebration may temporarily increase social behavior.

The goal is not a detailed emotion simulator. The goal is for yesterday to influence today.


======================================================================
8. HABITS
======================================================================

Repeated actions should become slightly easier to select.

Examples:

An NPC who repeatedly visits the tavern after work gains a tavern-after-work habit.

An NPC who repeatedly asks the same friend for advice becomes more likely to seek that person again.

An NPC who repeatedly avoids the cemetery after dark gains stronger avoidance.

Habits should be cheap numeric action-value modifiers.

They should be able to change through repeated contrary experience.


======================================================================
9. RUMOR SYSTEM
======================================================================

A rumor should be a data object, not only dialogue text.

Suggested fields:

rumor_id
subject
claim
source_actor
source_type
original_event_id
heard_at
heard_location
confidence
emotional_charge
privacy
distortion_generation
known_by

When an NPC retells a rumor:

confidence may change
specificity may change
emotion may increase
details may be dropped
details may be incorrectly inferred
the listener records the speaker as the immediate source

Do not mutate the single original rumor record. Create transmission records so provenance can be reconstructed.

This enables:

Who started this rumor?
How did the story change?
Which faction believes which version?
Did the Harbinger publish a distorted account?
Does a player have evidence contradicting the public story?

Rumors can become quests naturally.


======================================================================
10. RELATIONSHIP MODEL
======================================================================

Suggested relationship fields:

actor_id
target_id
affinity
trust
fear
respect
debt
familiarity
grievance
last_interaction
relationship_tags

Examples:

friend
employer
employee
family
rival
patient
doctor
creditor
debtor
mentor
apprentice
neighbor
suspect
witness

Relationships should affect:

willingness to share information
belief in testimony
likelihood of helping
pricing
access
rumor spread
commitment keeping
risk tolerance
defense
betrayal
social invitations
quest availability

This makes social variables bite mechanically.


======================================================================
11. DIALOGUE STRATEGY
======================================================================

Default to inexpensive dialogue.

A dialogue intent might be:

intent: report_observation
fact: saw player_127 near cemetery
confidence: 0.86
disclosure: willing
attitude: wary

Template renderer:

Reserved:
"I saw them near the cemetery. I cannot tell you what they were doing."

Gossipy:
"Now, do not say I told you, but I saw them by the cemetery myself."

Hostile:
"I saw them. Ask somebody else if you want a story."

The fact remains stable.

A language model can optionally receive a compact packet:

NPC identity summary
current mood
relationship to listener
allowed facts
forbidden facts
conversation intent
desired length
speech style

The output is only presentation.

If the LLM invents a new fact, discard or ignore that fact unless the game explicitly has an improvisation system that marks it as fiction, lie, speculation, or proposal.


======================================================================
12. USE OF LLMS
======================================================================

Do not run autonomous LLM loops for the whole population.

Recommended use:

Major conversations.
Special NPCs.
External AI-player interfaces.
Occasional reflection or summarization jobs.
Offline content generation that is later reviewed.
Optional local dialogue rendering.

Avoid:

Calling an LLM every NPC tick.
Giving the LLM direct database authority.
Letting the LLM decide whether a quest is complete.
Using model conversation history as the only memory store.
Allowing generated dialogue to silently mutate canon.
Giving AI players privileged access to hidden NPC state.

The low-cost simulation should remain functional with all LLM features disabled.


======================================================================
13. EVENNIA: PRIMARY INFRASTRUCTURE
======================================================================

Evennia should remain the primary server framework unless the project makes a separate platform decision.

Official site:
https://www.evennia.com/

Official GitHub:
https://github.com/evennia/evennia

Documentation:
https://www.evennia.com/docs/latest/

NPC and monster AI tutorial:
https://www.evennia.com/docs/latest/Howtos/Beginner-Tutorial/Part3/Beginner-Tutorial-AI.html

Scripts:
https://www.evennia.com/docs/latest/Components/Scripts.html

TickerHandler:
https://www.evennia.com/docs/latest/Components/TickerHandler.html

HOW TO USE EVENNIA HERE

Use Evennia for:

Accounts and sessions.
Rooms and exits.
Persistent objects.
Characters and NPC typeclasses.
Commands.
Database persistence.
Web and traditional MUD connections.
Scripts.
Timers.
Scheduled callbacks.
Room access rules.
World event integration.

Do not use the tutorial state machine as the complete final NPC brain.

The tutorial is useful because it demonstrates:

Persistent AI state.
Regular ticking.
State transitions.
Roaming.
Reactive behavior.
Lazy initialization.
Database-backed attributes.

Build the project simulation as a higher-level NPCBrain or NPCMind handler attached to an Evennia NPC.

Possible structure:

NPC
  npc.identity
  npc.needs
  npc.relationships
  npc.beliefs
  npc.memory
  npc.goals
  npc.commitments
  npc.schedule
  npc.ai

The Evennia tick infrastructure should trigger the relevant simulation layer according to LOD.

Important performance rule:

Do not create thousands of independent high-frequency timers if a centralized scheduler can batch residents.

Prefer something like:

NPCSimulationService
  active_npcs
  nearby_npcs
  background_npcs
  scheduled_events

The service decides which agents require evaluation.


======================================================================
14. PY_TREES: COMPLEX REACTIVE SEQUENCES
======================================================================

Official documentation:
https://py-trees.readthedocs.io/en/devel/

Introduction:
https://py-trees.readthedocs.io/en/devel/introduction.html

GitHub:
https://github.com/splintered-reality/py_trees

Install:
pip install py_trees

USE CASE

Do not use behavior trees as the entire social simulation.

Use them for structured responses that have several steps and interruptions.

Good examples:

Fire response.
Emergency medical response.
Hound search procedure.
Guard patrol.
Escape behavior.
Complex shop closing routine.
Investigation procedure.
Travel sequence.
Rescue attempt.

Example conceptual tree:

Emergency
  IsDangerPresent?
  Sequence
    IdentifyThreat
    WarnNearbyPeople
    SelectSafeAction
    AssistIfPossible
    Evacuate

py_trees is attractive because it is Python, modular, tick-based, and designed around reactive priority changes.

The utility layer selects the goal.
The tree executes the selected complex behavior.


======================================================================
15. NPC-SIM: REFERENCE IMPLEMENTATION FOR COGNITIVE VILLAGERS
======================================================================

GitHub:
https://github.com/Karyabla55/npc-sim

The current project exposes several ideas directly relevant to this game:

Utility-based action selection.
Big Five-style personality.
Need-driven goals.
Daily schedules.
Episodic memory.
Beliefs.
Traits.
Optional local LLM decision support through Ollama.

RECOMMENDED USE

Treat npc-sim first as a design and prototype reference.

Study:

How action scorers are organized.
How belief records are represented.
How salience-limited memory is handled.
How schedules constrain actions.
How optional LLM support is separated from utility decisions.

Do not immediately make the production game depend on this repository.

First evaluate:

License.
Project maturity.
Persistence assumptions.
Compatibility with Evennia.
Threading and async behavior.
Test coverage.
Data model fit.
Upgrade risk.

We may reuse concepts without adopting the package.


======================================================================
16. OPENNPC: REFERENCE FOR AI LEVEL OF DETAIL
======================================================================

GitHub:
https://github.com/balaraj74/openNPC

OpenNPC describes an engine-agnostic Python pipeline containing:

Heuristic decision making.
Priority-scored goals.
Persistent memory.
Forgetting.
Optional reinforcement-learning policies.
Optional small local LLM use.
AI level-of-detail.

RECOMMENDED USE

The most relevant concept is AI level-of-detail.

Study how the project scales compute based on importance, visibility, and distance.

Use that as inspiration for the project's:

active
nearby
background
dormant

simulation tiers.

Also inspect its memory and heuristic goal organization.

As with npc-sim, treat this as a reference or experimental dependency until its license, maturity, API stability, and integration cost have been reviewed.


======================================================================
17. MESA: OFFLINE SIMULATION AND BALANCING TOOL
======================================================================

GitHub:
https://github.com/mesa/mesa

Documentation:
https://mesa.readthedocs.io/

Mesa is an open-source Python agent-based modeling library.

RECOMMENDED USE

Mesa does not need to run the live MUD.

It could be extremely useful as an offline laboratory.

Build simplified versions of residents and run:

30 simulated days.
100 simulated villagers.
1,000 rumor transmissions.
Repeated faction conflicts.
Economy stress tests.
Disease or panic propagation.
Schedule congestion.
Social network evolution.

Then inspect:

Does everyone converge on the same routine?
Do rumors spread too quickly?
Do NPCs starve because work scores dominate food?
Does one faction absorb the entire village?
Do relationships become permanently extreme?
Does memory grow without bound?
Do players have enough opportunities to encounter events?

Mesa can help tune simulation coefficients before those rules affect the live MMO.


======================================================================
18. CATACLYSM: DARK DAYS AHEAD
======================================================================

Main GitHub:
https://github.com/CleverRaven/Cataclysm-DDA

NPC contributor guide:
https://github.com/CleverRaven/Cataclysm-DDA/wiki/New-Contributor-Guide-NPCs

NPC JSON documentation:
https://github.com/CleverRaven/Cataclysm-DDA/blob/master/doc/JSON/NPCs.md

RECOMMENDED USE

This is not a drop-in dependency for the Python MUD.

Use it as a mature open-source case study for:

NPC classes.
NPC templates.
Factions.
Missions.
Dialogue data.
Attitudes.
Jobs.
Travel.
Guarding.
Behavior separation.
Data-driven content.

The current source also documents movement toward behavior-tree handling for immediate survival needs.

Study how the project separates content data from engine behavior. That separation is particularly valuable for a large quest-heavy MMO.


======================================================================
19. DWARF FORTRESS: DESIGN REFERENCE
======================================================================

Thoughts and preferences reference:
https://dwarffortresswiki.org/Thoughts_and_preferences

RECOMMENDED USE

Dwarf Fortress is a design reference, not a code dependency.

Study:

Personality facets.
Values.
Preferences.
Needs.
Memories.
Dreams.
Long-term accumulated consequences.
How the same event affects different individuals differently.

Do not attempt to reproduce Dwarf Fortress complexity.

The lesson is that a relatively compact personal state can make a resident respond differently to the same world event.


======================================================================
20. RIMWORLD: DESIGN REFERENCE
======================================================================

Social system:
https://rimworldwiki.com/wiki/Opinion

Mood:
https://rimworldwiki.com/wiki/Mood

RECOMMENDED USE

Study the way social relationships feed back into behavior.

Important design lessons:

Opinions can create fights or cooperation.
Relationships affect mood.
Social events produce persistent consequences.
A small number of readable variables can generate stories.

Do not copy RimWorld's numerical model directly.

Use the principle that social state must affect actual decisions.


======================================================================
21. CAVES OF QUD: DESIGN REFERENCE
======================================================================

Official site:
https://cavesofqud.com/

Press kit:
https://cavesofqud.com/press-kit/

RECOMMENDED USE

Caves of Qud is particularly relevant for:

Faction relationships.
Reputation.
Secrets as exchangeable information.
Procedural history.
Hand-authored narrative mixed with simulation.
World entities that use broadly consistent systemic rules.

For this project, the strongest lesson is:

INFORMATION CAN BE GAMEPLAY STATE.

A secret, rumor, historical fact, map location, witness account, or faction belief can be valuable without becoming an inventory object.


======================================================================
22. ULTIMA RATIO REGUM: PROCEDURAL CULTURE AND DIALOGUE
======================================================================

Design article:
https://www.gamedeveloper.com/design/the-10-year-journey-of-ultima-ratio-regum-the-culture-generating-roguelike

RECOMMENDED USE

Study its approach to:

Procedural cultures.
Dialect.
Greetings.
Insults.
Compliments.
Speech verbosity.
Cultural vocabulary.
Template-based variation.

This supports a cheaper alternative to generating every line with an LLM.

A resident can sound culturally and personally distinct through:

word choice
sentence length
formality
preferred idioms
greeting structure
taboo topics
titles
forms of address

These can be deterministic data.


======================================================================
23. STANFORD GENERATIVE AGENTS: RESEARCH REFERENCE ONLY
======================================================================

GitHub:
https://github.com/StanfordHCI/genagents

RECOMMENDED USE

Read this for research ideas around:

Memory.
Agent profiles.
Generative responses.
Simulation experiments.

Do not use this as the baseline production architecture for the town population.

The repository is designed around LLM-backed generative agents and requires model access. That is far more expensive than this MMO needs for ordinary residents.

Take concepts, not runtime cost.


======================================================================
24. CORE DATA MODEL
======================================================================

A practical NPC record might look conceptually like this:

NPCIdentity
  npc_id
  display_name
  occupation
  home_location
  work_location
  factions
  personality_traits
  values
  preferences
  fears
  secrets
  persistent_goals

NPCState
  location
  current_activity
  fatigue
  hunger
  safety
  affiliation
  duty
  curiosity
  stress
  material_security
  affect_residue

Relationship
  actor_id
  target_id
  affinity
  trust
  fear
  respect
  debt
  familiarity
  grievance
  tags

Belief
  belief_id
  actor_id
  proposition
  confidence
  source_actor
  source_event
  learned_at
  last_reinforced
  status

Memory
  memory_id
  actor_id
  event_reference
  summary
  salience
  emotional_tone
  created_at
  last_recalled
  decay_class

Goal
  goal_id
  actor_id
  type
  target
  urgency
  persistence
  status

Commitment
  commitment_id
  actor_id
  target_actor
  action
  location
  due_time
  priority
  status
  reason_if_broken

ScheduleBlock
  actor_id
  start
  end
  preferred_location
  activity
  priority
  flexibility

RumorTransmission
  rumor_id
  speaker
  listener
  proposition
  source_claimed
  confidence
  transmitted_at
  distortion_generation


======================================================================
25. NPC IMPORTANCE TIERS
======================================================================

Not every NPC needs the same cognition budget.

TIER A: MAJOR RESIDENT

Full identity.
Rich relationships.
Persistent beliefs.
50 to 100 episodic memories.
Multiple goals.
Commitments.
Detailed schedule.
Personal quest arcs.
Optional LLM dialogue.

TIER B: REGULAR RESIDENT

Identity.
Core needs.
20 to 50 memories.
Relationships to relevant contacts.
Schedule.
Goals.
Rumors.
Template dialogue.

TIER C: MINOR RESIDENT

Occupation.
Home.
Schedule.
Traits.
A few relationships.
Small memory budget.
Rumor participation.
Mostly template dialogue.

TIER D: CROWD OR TRANSIENT

Generated identity.
Purpose.
Location.
Minimal state.
No persistent simulation unless promoted by player interaction.

PROMOTION RULE

If players repeatedly interact with a transient or incidental NPC, promote that NPC to a higher tier instead of replacing them with a new generic character.

This allows player attention to create permanence.


======================================================================
26. SIMULATION TICK EXAMPLE
======================================================================

At each relevant evaluation:

1. Receive new world events.
2. Update perceptions.
3. Convert perceptions into beliefs.
4. Update needs.
5. Update affect residue.
6. Check schedule.
7. Check commitments.
8. Check urgent goals.
9. Generate currently valid actions.
10. Score actions.
11. Choose an action.
12. Execute action.
13. Emit resulting events.
14. Store a memory if salience threshold is met.
15. Update relationships if applicable.
16. Schedule the next evaluation based on LOD.

Do not run steps that have nothing to update.

An asleep NPC with no incoming event and no due commitment may need no full decision tick at all.


======================================================================
27. QUEST INTEGRATION
======================================================================

The NPC simulation should feed the quest system rather than exist beside it.

Examples:

NPC misses work because a friend vanished.
This produces a missing-person rumor.

A witness remembers seeing someone near the river.
This becomes evidence.

A Hound believes a false rumor and launches an investigation.
This becomes a rival-investigator branch.

The newspaper interviews two NPCs with conflicting beliefs.
This produces competing published accounts.

A merchant breaks a commitment because a shipment failed.
This creates a debt or grievance.

An NPC reaches high stress and asks a trusted player for help.
This creates a relationship-driven quest.

A player ignores a request.
The NPC acts independently.
The world changes.

The simulation should create hooks.
The authored quest system should provide structure when a hook becomes important.


======================================================================
28. EXTERNAL AI PLAYERS
======================================================================

External AI agents must interact through player-facing interfaces.

They should not receive:

raw NPC belief tables
hidden quest states
objective event truth unavailable to their character
secret relationship variables
unseen room state

They receive the same observable outputs a human player would receive.

This preserves the mixed-human-and-AI world experiment.

External agents may have advantages such as patience, record keeping, or regular attendance, but the server should not grant them substrate-specific gameplay privileges.


======================================================================
29. PERFORMANCE RULES
======================================================================

Use integer or small floating-point state where practical.

Batch NPC simulation.

Prefer event subscriptions over polling.

Use coarse resolution for inactive NPCs.

Limit detailed relationship records.

Limit episodic memory.

Summarize repeated history.

Index beliefs by subject and topic.

Index commitments by due time.

Avoid embedding every memory unless semantic search becomes demonstrably necessary.

Do not run vector search for ordinary decisions that can be answered by keyed state.

Do not run an LLM for pathfinding, scheduling, hunger, routine social selection, or simple rumor transmission.

Cache static identity data.

Keep dialogue generation outside the authoritative simulation transaction.

Profile before optimizing complex systems.


======================================================================
30. DEVELOPMENT SEQUENCE
======================================================================

PHASE 1: BASIC RESIDENT

Implement:

persistent NPC identity
home and workplace
daily schedule
movement
sleep and work
basic needs
simple utility action selection

Success test:

A resident follows a recognizable routine and can deviate when hungry, tired, or interrupted.

PHASE 2: RELATIONSHIPS

Implement:

trust
affinity
familiarity
debt
grievance

Success test:

Two residents exposed to the same request choose differently because of relationship state.

PHASE 3: EVENTS AND BELIEFS

Implement:

world event bus
perception filters
belief records
confidence
source provenance

Success test:

Two NPCs hold different beliefs about one event because one witnessed it and one heard a rumor.

PHASE 4: RUMORS

Implement:

retelling
confidence changes
source tracking
distortion
social propagation

Success test:

A single unusual event produces several different village accounts over time.

PHASE 5: MEMORY

Implement:

short-term events
salience
episodic storage
decay
summaries

Success test:

NPC behavior tomorrow is affected by a significant interaction today without storing an unlimited transcript.

PHASE 6: COMMITMENTS

Implement:

promises
appointments
obligations
due times
broken commitment reasons

Success test:

An NPC can agree to meet a player tomorrow and later keep, intentionally break, or be prevented from keeping the promise.

PHASE 7: SIMULATION LOD

Implement:

active
nearby
background
dormant

Success test:

The same village simulation remains coherent when most residents receive coarse updates.

PHASE 8: DIALOGUE RENDERING

Implement:

intent packets
templates
personality phrase banks
optional local LLM renderer

Success test:

Dialogue style varies without allowing generated text to invent game state.

PHASE 9: QUEST FEED

Implement:

simulation event to rumor
rumor to investigation hook
relationship event to personal request
commitment failure to grievance/debt
world event to newspaper candidate

Success test:

The live NPC system creates playable hooks without a designer manually starting each quest.

PHASE 10: LOAD TEST

Simulate:

100 residents
500 residents
1,000 residents

Measure:

tick cost
database writes
memory growth
event queue size
rumor propagation
schedule throughput
inactive-agent cost


======================================================================
31. TESTS THE SYSTEM MUST PASS
======================================================================

WORLD TRUTH SEPARATION

An NPC cannot report an event it did not perceive or learn about.

FALSE BELIEF

An NPC can sincerely hold and act on an incorrect belief.

SOURCE PROVENANCE

A rumor can be traced through its speakers.

SCHEDULE INTERRUPTION

A high-priority event can override routine behavior.

COMMITMENT PERSISTENCE

Promises survive server reloads.

MEMORY LIMIT

Memory storage remains bounded.

RELATIONSHIP CONSEQUENCE

Trust or debt changes a later decision.

LOD CONSISTENCY

An NPC simulated coarsely reaches a state reasonably compatible with detailed simulation.

NO-LLM MODE

The entire resident simulation remains playable with every language model disabled.

DIALOGUE AUTHORITY

Generated prose cannot alter authoritative world state.

OFFLINE PROGRESSION

The world can advance without a connected player while preserving deterministic or reproducible event logs where required.

RENAME SAFETY

Changing the village display name does not require changing IDs, quests, saves, or database relations.


======================================================================
32. WHAT NOT TO BUILD
======================================================================

Do not build a full human mind for every baker.

Do not give every NPC a language model.

Do not store every sentence forever.

Do not make residents omniscient.

Do not use one friendship bar for all social relationships.

Do not make schedules absolute rails.

Do not freeze NPCs when players log out.

Do not make every interruption into an authored quest.

Do not let procedural rumors overwrite objective facts.

Do not let dialogue generation decide canon.

Do not hard-code adaptation-specific names while the literary-source audit is still underway.

Do not hard-code the current village name.


======================================================================
33. TARGET EXPERIENCE
======================================================================

The game should produce stories that sound authored even when the exact sequence was not authored.

A player logs in.

The apothecary is unexpectedly closed.

A neighbor says the apothecary left before dawn.

The church sexton says they saw the apothecary near the cemetery.

Another villager insists it was the marsh road.

The newspaper has not heard about it yet.

A friend of the apothecary is worried.

A rival is irritated because a promised medicine order is late.

A Hound has already started following the wrong lead.

The player can investigate, spread the story, ignore it, exploit it, or help.

The system knows only that several agents followed their needs, beliefs, schedules, relationships, and commitments.

The player experiences a living village.


======================================================================
34. RESOURCE INDEX
======================================================================

EVENNIA
https://www.evennia.com/
https://github.com/evennia/evennia
https://www.evennia.com/docs/latest/
https://www.evennia.com/docs/latest/Howtos/Beginner-Tutorial/Part3/Beginner-Tutorial-AI.html
https://www.evennia.com/docs/latest/Components/Scripts.html
https://www.evennia.com/docs/latest/Components/TickerHandler.html

PY_TREES
https://py-trees.readthedocs.io/en/devel/
https://py-trees.readthedocs.io/en/devel/introduction.html
https://github.com/splintered-reality/py_trees

NPC-SIM
https://github.com/Karyabla55/npc-sim

OPENNPC
https://github.com/balaraj74/openNPC

MESA
https://github.com/mesa/mesa
https://mesa.readthedocs.io/

CATACLYSM: DARK DAYS AHEAD
https://github.com/CleverRaven/Cataclysm-DDA
https://github.com/CleverRaven/Cataclysm-DDA/wiki/New-Contributor-Guide-NPCs
https://github.com/CleverRaven/Cataclysm-DDA/blob/master/doc/JSON/NPCs.md

DWARF FORTRESS DESIGN REFERENCE
https://dwarffortresswiki.org/Thoughts_and_preferences

RIMWORLD DESIGN REFERENCE
https://rimworldwiki.com/wiki/Opinion
https://rimworldwiki.com/wiki/Mood

CAVES OF QUD
https://cavesofqud.com/
https://cavesofqud.com/press-kit/

ULTIMA RATIO REGUM
https://www.gamedeveloper.com/design/the-10-year-journey-of-ultima-ratio-regum-the-culture-generating-roguelike

STANFORD GENERATIVE AGENTS
https://github.com/StanfordHCI/genagents

PUBLIC-DOMAIN LITERARY SOURCE MATERIAL
https://www.gutenberg.org/ebooks/84
https://www.gutenberg.org/ebooks/41445
https://www.gutenberg.org/ebooks/42324
https://www.gutenberg.org/ebooks/345
https://www.gutenberg.org/ebooks/43
https://www.gutenberg.org/ebooks/69700

UNIVERSAL REFERENCE TO AVOID OVERLAP WITH DARKMOOR VILLAGE
https://www.universalorlando.com/web/en/us/things-to-do/character-encounters/dark-universe-character-encounters
https://www.universalorlando.com/web/en/us/epic-universe/worlds/dark-universe


======================================================================
35. FINAL IMPLEMENTATION RECOMMENDATION
======================================================================

Recommended production stack:

Evennia for networking, persistence, rooms, accounts, commands, and scheduling.

A project-owned NPC simulation service for:
identity
needs
schedules
beliefs
memory
relationships
goals
commitments
rumors
utility scoring
simulation LOD

py_trees only for selected multi-step reactive behaviors.

Mesa as an optional offline simulator and balancing laboratory.

npc-sim and OpenNPC as architecture references and possible prototype dependencies after license and maturity review.

Cataclysm: DDA as a data-driven NPC architecture reference.

Dwarf Fortress, RimWorld, Caves of Qud, and Ultima Ratio Regum as design references.

LLMs only as optional language renderers or special-character tools.

Public-domain novels as source canon, with adaptation-specific material excluded unless independently cleared.

The system should remain coherent, persistent, and playable when every LLM is switched off.

END OF HANDOFF
