# Resident Life Simulation v2

Date: 2026-10-07

Status: production integration candidate

## Purpose

Resident Life v2 deepens Frankenstein Village's ordinary simulated population
without turning the game into one continuously thinking agent per NPC.

The governing rule remains:

`CONTINUITY IS ALWAYS ACTIVE. COGNITION IS ACTIVATED ONLY WHEN REQUIRED.`

The system borrows the useful population-scale ideas from the TNHS work:
localized physical condition, affect with cause and target, commitments,
first-person subjective perception, resident-to-resident relationships, and
goal interruption. It deliberately does not import the full neural,
biochemical, or continuous inner-monologue runtime.

## Simulation profiles

Every resident resolves to one of two life-simulation profiles.

### authored_locked

Existing runtime-canon and legacy-routine characters are protected
automatically. Residents that are already bound into authored quest or
institutional content can also be explicitly locked.

Current explicit generic-scheduler lock:

- Ilona Szabó, because she is already an authored Chronicle situation actor.

An authored-locked resident is a strict no-op for Resident Life v2. The
system does not add physical conditions, affect, commitments, subjective
perceptions, social updates, goal overrides, or private thoughts to that
resident.

This boundary lets authored quest NPCs continue using their existing
typeclasses, schedules, dialogue, situation logic, and narrative obligations.

### population

Ordinary residents use the event-driven life layer.

Their persistent state may contain:

- body conditions: cold, wet, pain, injury, illness, intoxication, discomfort;
- bounded affect episodes with kind, intensity, cause, target, and decay;
- bounded first-person perceptions representing what that resident actually
  experienced rather than server omniscience;
- bounded commitments with due time, target, place, priority, and resolution;
- sparse resident-to-resident relationship state;
- a small active-goal set derived only when the resident is awake or engaged.

## Performance contract

No Resident Life v2 feature may require every NPC to think every tick.

Background schedule resolution remains the cheap D-tier path.

Life-state decay and goal derivation run only when a resident is already
above automaton resolution or has a wake reason. A physical condition,
salient perception, or new commitment can create a wake reason.

Resident relationships update only when a real social event occurs. There is
no all-pairs social scan.

Rumor traffic is one current live social event. When two simulated residents
actually exchange a rumor, their sparse relationship state changes and the
listener receives a bounded first-person hearsay perception. Existing social
history can slightly bias which colocated resident a speaker approaches.

All collections are capped so character depth cannot grow without bound.

## Subjective boundary

English inner cognition is generated on demand from consequential state.
It is not a continuous monologue.

Examples:

- `I'm hurting.`
- `I'm getting cold.`
- `I need to return the borrowed lantern.`
- `I heard Rada repeat a rumor.`

These statements are private simulation products. They are not automatically
shown to players and do not require a language model.

## Schedule and goal interaction

The schedule remains the default.

Existing need overrides still take precedence. If no existing need override
fires, a high-priority life goal may temporarily redirect an awake or engaged
ordinary resident.

Examples include:

- severe injury or illness causing a return home;
- severe pain causing bodily protection;
- a high-priority due commitment with a concrete location.

The world remains authoritative. A goal only requests a logical location that
is currently available.

## Testing

The clean-checkout suite now runs `spike/tests/resident_life_sim.py` before
bootstrapping Evennia.

That offline regression proves:

- authored locks are hard no-ops;
- ordinary residents receive life state;
- body conditions and affect are bounded;
- commitments can interrupt routine;
- resident relationships are sparse and event-driven;
- subjective thoughts remain first-person;
- long-run cost stays proportional to current population and time.

The live world assertions separately prove the residents API respects the
same authored locks and that ordinary resident state can be mutated and
restored without contaminating later production tests.

## Future opt-in

Do not remove an authored lock casually.

If an authored quest NPC should eventually gain selected life systems, make
that an explicit design decision and opt the character into a hybrid profile
with dedicated regression coverage. Resident Life v2 does not implicitly
change authored characters.
