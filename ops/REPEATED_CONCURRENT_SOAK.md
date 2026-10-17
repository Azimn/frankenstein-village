# Repeated concurrent-player burn-in

`ops/repeated_concurrent_soak.py` repeatedly connects independent
AI-disclosed test accounts to the actual Evennia game using the existing
standard login and ordinary player verbs. It measures real session and
command latencies over a bounded observation window.

It is **not** the same as uninterrupted 24-hour connected-player load,
live-host recovery, human return-rate evidence or a release go-ahead.
Running against an actual public endpoint requires the chosen operator,
permission to generate load, approved test accounts, TLS, and a defined
test window. No hosting provider is selected by this repository.

## One operator-controlled 30-minute run

Prepare a private JSON manifest following `HEADLESS_AI_CLIENT.md`. It must
contain separately owned non-staff accounts with `username`, `character`,
and `password_env` keys, each password obtained only from the operator's
process environment. **Do not use real player accounts or upload secrets.**

Run on a permitted local game server or approved host. A remote target
requires `--tls` with normal certificate validation, even for AI clients.

```sh
python ops/repeated_concurrent_soak.py \
  --host 127.0.0.1 --port 4000 \
  --accounts /private/qa-accounts.json \
  --sessions 5 --minutes 30 --interval-seconds 20 \
  --steps 3 --test-one-disconnect \
  --max-error-rate 0.01 --max-p95-ms 3500 \
  --output /private/evidence/soak-result.json
```

The program opens at most 32 simultaneous ordinary client sessions per
round and deliberately stays within the server's login throttles. It
runs successive independent rounds with a bounded interval, rather than
opening unlimited sockets or disabling abuse controls. Optionally, one
account performs a real abrupt disconnect and inventory recovery on the
first round. Use a separate, explicitly approved window for heavier tests.

The output intentionally aggregates measurements and contains **no**
credentials, character names, room dialogue, private mysteries or raw
player transcripts. It reports observed elapsed time, rounds, total
session attempts, failures, command counts, maximum session-specific
p95 latency, maximum observed single-command latency and verified
reconnections. Its p95 measure is the **worst of each session's p95**, not
an invalid pooled command-percentile estimate.

A technical threshold pass requires at least 30 minutes of **actual**
elapsed time, at least three rounds, failure rate no higher than the
configured limit, and worst session p95 within the latency ceiling. The
`public_launch_certified` field is **always false**. No positive count
from this script changes the launch gate by itself. Short dry-runs are
supported but deliberately cannot pass the thirty-minute requirement.

A complete operational go/no-go decision still needs a real host,
external HTTPS and WSS, isolated off-host restore and rollback, actual
long-lived connected-user soak, sustained event clock behavior,
moderation response drills, uncoached human and local-model sessions,
plus D1/D7 voluntary return evidence. Record provider, CPU, RSS, SQLite
growth, backup/restore times, network disconnects and operator review
separately. Never run destructive development fixtures on production.
