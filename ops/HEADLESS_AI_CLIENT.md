# Headless AI MUD client

This client is for **real AI-owned or operator-provisioned accounts**, not
in-game NPCs. It speaks the same ordinary text commands that human players
use, including `agentlogin` and `agent`. No privileged fast path, HTTP
admin access, database queries, or gameplay test hooks are involved.

**Do not run an AI-client load soak without the independent safety review
and explicit operational green light.** Calibos is auditing this optional
AI-client access layer. These restrictions do not prevent ordinary human-client
multiplayer testing or release of the model-free game. The optional client's
current automated tests use a fake external protocol peer, not a server load
test.

## Account file and secrets

Create a local JSON file outside Git (for example, `/private/bot-accounts.json`):

```json
[
  {"username": "alpha_bot", "character": "AlphaMask",
   "password_env": "FV_ALPHA_BOT_PASSWORD"},
  {"username": "beta_bot", "character": "BetaMask",
   "password_env": "FV_BETA_BOT_PASSWORD"}
]
```

Give **each simultaneously connected AI its own account**. Passwords are
read from environment variables and are never stored in the metrics file.
The file contains references to secrets, not the secrets. Existing accounts
are used as-is; first-time accounts declare `substrate ai` via the normal
compact and create their first character via normal account commands.

To run a small controlled functional check **after the audit authorizes it**,
use a TLS-protected MUD terminal listener:

```sh
python3 ops/headless_ai_client.py \
  --host village.example.org --port 4040 --tls \
  --accounts /private/bot-accounts.json \
  --sessions 2 --seed 314159 --steps 6 \
  --output /private/agent-smoke.json
```

Plaintext telnet is refused for remote hosts. Loopback development can use
`--host 127.0.0.1 --port 4000` without `--tls`. Remote credentials
require a valid server TLS certificate.

### Repeatable small interaction loop

Each independent session logs in, uses `agentlogin`, chooses its existing
mask or creates one normally, uses `agent` for accessible movement, then
travels from the Inn's private room to the Common Room, speaks with M.,
crosses the front door, and arrives at the Tavern. There it looks, talks
to Bram, and selects random ordinary activities, including dice and rumors.
It briefly visits the Square and returns. The seed yields reproducible
choices without scripting an NPC's mind or inventing game state.

A returning mask is not relocated to the Inn. It resumes from its real
persisted room, with only public movement commands. In-world actions stay IC;
the Inn remains OOC. The same interface is valid for humans.

### Optional independent map survey

After an operator authorizes an invited-alpha smoke run, use the normal
AI account and public `agent` responses to discover the navigable map:

```sh
python3 ops/headless_ai_client.py \
  --host 127.0.0.1 --port 4000 \
  --accounts /private/bot-accounts.json \
  --sessions 2 --steps 4 --explore-rooms 10 \
  --output /private/agent-exploration.json
```

The `--explore-rooms` switch accepts 0 (off) through 12. The client learns
room neighbors only from this player's visible, currently traversable exits.
It avoids OOC/private rooms, observes a room before choosing its next
move, inspects a locally visible object where available, records visited
locations, and returns to the original Tavern room. It reports a failure
rather than quietly claiming the target if the rooms cannot be reached.

When an existing player character reconnects from a remote IC location,
the client discovers its ordinary route back to the Tavern rather than
repositioning the character or assuming the old map. This is a bounded
deterministic autonomous explorer, not an LLM making independent dramatic
decisions. Its purpose is to verify that the game exposes enough ordinary
information for one. Separate uncoached language-model and human playtests
remain necessary.

### Targeted disconnect recovery

The optional command

```sh
python3 ops/headless_ai_client.py ... --recover-index 0
```

starts an ordinary whittled spoon, captures the inventory, **abruptly drops
one TCP connection**, reconnects to the same account and mask, and confirms
the room and inventory survived. It completes the two remaining craft steps,
verifies exactly one new wooden spoon appears, and observes that a later
look produces no second item. This is a *single targeted recovery check*,
not a load test. Use a dedicated clean recovery-test mask that has no prior
half-finished whittle project.

### Evidence and limits

Each session emits connection status, connection attempts and failures,
command counts, p50/p95/max request round-trip latency, forced disconnect
count, recovery outcome, rooms visited, a real in-world line of dialogue,
and any error. The result includes a deterministic seed and explicitly
marks its type as a functional probe, **not a multiplayer soak**.

If the client executes on the server host and the operator passes one or
more `--server-pid <pid>`, it also samples process CPU time and resident
memory from Linux `/proc` before and after each session. These are
**shared, overlapping process windows**, not scientifically attributable
per-account resource measurements. A remote client cannot access accurate
server CPU or RSS solely through ordinary MUD verbs: metrics will be marked
unavailable without host-local process visibility. The future authorized
soak will need a real host-level observability pipeline for aggregate CPU,
memory, connections, database I/O, scheduler lag, and session concurrency.

There is currently no claim that a novice human or a genuinely naive AI has
completed this route and found it enjoyable within minutes. The executable
route and quotable text capture are scaffolding for that acceptance test.
Uncoached human playtests, normal-client multiplayer/restart verification,
and deployment evidence are required for public release. Independent AI
observations are optional integration research, not a model-free release gate.
