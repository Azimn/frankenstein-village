# Continuous connected-player load qualification

`ops/continuous_player_soak.py` fills a gap left by
`ops/repeated_concurrent_soak.py`: **the same game sessions remain
connected** during the observation period. The client uses authenticated,
distinct ordinary AI-disclosed characters and the actual public game protocol,
not privileged Evennia shell hooks or a simulated game. A synchronization
barrier starts the timed window only after *every* account has entered the
in-character world. Losing any session fails the test; automatic reconnects
cannot conceal a failed long-lived connection.

## Operator qualification on an approved host

Prepare at least two separate, explicitly permitted non-staff QA accounts.
Each account uses the same `username`, `character` and `password_env`
private manifest format documented in `HEADLESS_AI_CLIENT.md`. Keep the
manifest and generated evidence outside the public repository. Never use
production player passwords or perform unauthorized load testing.

```sh
python3 ops/continuous_player_soak.py \
  --host village.example.org --port 4040 --tls \
  --accounts /private/qa-accounts.json --sessions 5 \
  --minutes 30 --interval-seconds 5 --timeout 8 \
  --max-p95-ms 3500 --output /private/evidence/continuous-soak.json
```

The endpoint above is **an illustrative hostname**, not a claim that the
village is hosted. Plain telnet is restricted to local loopback; external
connections require certificate-verified TLS. Do not bypass authentication,
consent, moderation throttles or transport controls.

Each player remains connected across the full window while taking paced,
read-only, actual player actions: `agent`, `look`, `calendar`, `survey`,
`journal discoveries` and `guide`. The test asserts a valid in-character
observation at both ends. It records each command's latency without copying
player names, credentials, private memories or raw room descriptions.
The maximum observed session-specific p95 is used as a conservative latency
bound. Connection losses, responses disappearing, empty replies, or skipped
held time fail closed.

The **technical** continuous-session threshold requires two or more distinct
simultaneous player connections, at least 30 *observed* minutes each, and
every client maintaining the connection, at least two reads, and an observed
p95 under the selected bound. The JSON always says
`public_launch_certified: false`, because this alone cannot show operational
resilience or gameplay retention. When `--server-pid` is supplied on Linux,
host-local server CPU/RSS deltas are included, explicitly describing that
these are shared-process observations, not per-character usage.

The mandatory clean-checkout CI uses the **short smoke**:

```sh
python3 ops/continuous_player_soak.py \
  --host 127.0.0.1 --port 4000 \
  --accounts /private/qa-accounts.json --sessions 2 \
  --smoke-seconds 8 --interval-seconds 2 \
  --output /private/evidence/continuous-smoke.json
```

This proves that the instrument operates over genuine concurrent sockets,
and intentionally yields `technical_thresholds_met: false`. Never use that
eight-second run as a 30-minute or production soak receipt.

## What remains separate

A real host also requires periodic world clock and event persistence checks,
network interruptions, capacity and database growth measurements, successful
fresh external login/consent on HTTPS/WSS, operator incident escalation,
a verified encrypted off-host restore, and a simulated rollback on an
isolated clone. Actual uncoached people and language-model agents must still
be observed making meaningful choices and returning at D1 and D7.

This test does **not** purchase or provision hosting, leave background
services running, certify a production server, or infer that players enjoy
the game.
