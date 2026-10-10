# Alpha persistence safety

The current development instance uses Evennia's SQLite database at
`spike/fvillage/server/evennia.db3`. That database is live world state,
not source code. Accounts, player masks, rooms, resident memory, public records,
and the event ledger must survive upgrades and machine failure.

This utility is deliberately local and infrastructure-neutral. It is not a
hosted backup service, scheduler, deployment configuration, or evidence that
a public server is running.

## Before inviting outside players

1. Provision a persistent data volume. Never deploy by recreating the database.
2. Keep `server/conf/secret_settings.py` and service credentials out of Git.
3. Run an initial backup and verify a restore into a separate disposable
   database before the first external session.
4. Arrange regular backups to a physically separate location or provider.
   Copies on the same host do not protect against host failure.
5. Test login, disclosure, character selection, travel, persistence, restart,
   moderation, and a recurring world-clock event over the actual public endpoint.
6. Re-run the clean-checkout CI gate and a post-deployment smoke test after
   each release, with a tested rollback path for schema changes.

## Read-only alpha release preflight

The release preflight checks three independent facts without logging into any
player account or mutating the live world:

- A signed-off SQLite snapshot and its manifest pass digest and integrity
  verification, and an isolated disposable copy can be opened.
- The configured Evennia telnet entry point presents the Frankenstein Village
  login banner without sending credentials or commands.
- The configured web landing page responds successfully with nonempty content.

Run it on the deployment host if telnet is only available on its loopback
interface. This example assumes the web client is published through HTTPS:

```bash
python3.12 ops/alpha_preflight.py \
  --snapshot /secure/off-host-staging/frankenstein-backups/SNAPSHOT.db3 \
  --telnet-host 127.0.0.1 --telnet-port 4000 \
  --web-url https://your-village-host.example/
```

For external telnet verification, pass a hostname behind a trusted TLS
termination point and use `--telnet-tls`. The tool refuses plaintext telnet
checks to non-loopback hosts because credentials would otherwise travel over
an unprotected channel during real player sessions. Plain HTTP is accepted
only for local loopback testing. The public web endpoint must use HTTPS,
including after redirects.

A successful command prints `ALPHA_TRANSPORT_RECOVERY_GREEN` and a JSON
report whose `launch_certified` field is always `false`. This deliberately
does **not** establish account login, disclosure consent, character selection,
clock persistence, moderation, off-site backup custody, or successful recovery
of the full Evennia application. Those must be tested separately and logged
as release evidence. Never copy a live SQLite snapshot into a public CI
artifact or commit it to the repository.

See `ops/ALPHA_RELEASE_CHECKLIST.md` for the release decision record.

## Online-safe backup

Run from the repository root. Supply your own protected destination, preferably
outside the game directory and off the server's main disk.

```bash
python3.12 ops/sqlite_snapshot.py backup \
  --database spike/fvillage/server/evennia.db3 \
  --output-dir /secure/off-host-staging/frankenstein-backups
```

The command uses SQLite's backup API, validates integrity, atomically publishes
the snapshot, and writes a sidecar manifest with the byte count and SHA-256.
A completed backup does not stop or rewrite the source database. The operator
must transfer the snapshot and manifest together to off-host storage.

## Restore drill and emergency recovery

Stop Evennia first and verify the process is no longer using the database.
Run restore only while it is stopped. Do not ignore `-wal`, `-shm`, or
`-journal` sidecars: resolve them safely before proceeding.

```bash
python3.12 ops/sqlite_snapshot.py restore \
  --database spike/fvillage/server/evennia.db3 \
  --snapshot /secure/off-host-staging/frankenstein-backups/SNAPSHOT.db3 \
  --rollback-dir /secure/off-host-staging/rollback \
  --confirm-server-stopped
```

The restore checks manifest and SQLite integrity before mutation, refuses
suspicious sidecars, creates a checked snapshot of the current database for
rollback, then atomically replaces the target. The acknowledgment flag records
operator intent; it cannot independently prove that Evennia is stopped.

Restore to a disposable game directory during drills, not the production
database. Start Evennia, verify persistent account, room, case, and clock state,
then stop it cleanly.

## Scope and constraints

- SQLite snapshots are appropriate only for the current SQLite-backed alpha.
  A future PostgreSQL deployment requires database-native backup/restore.
- A verified backup does not replace tested upgrades, monitoring, access
  controls, retention, disaster recovery, or remote connectivity.
- Snapshot contents contain player and account data. Restrict access, encrypt
  copies in transit and at rest, and do not commit or publish them.
- Git ignore rules prevent accidental new commits. They do not erase data from
  earlier Git history; examine prior tracked sidecars if data exposure is suspected.
- No destructive schema migration or untested live restoration is part of
  this repository change.


## Invited alpha Gate A and B

[The costed host/recovery runbook](deploy/INVITED_ALPHA_GATES_A_B.md)
selects a DigitalOcean 2-vCPU/4-GiB candidate, persistent SSD, private off-host
encrypted backups, a human recovery owner, and ordered external evidence gates.
`deploy/alpha_restore_rehearsal.py` checks snapshot retrieval, exact restore,
rollback and category presence **only on isolated copies**.
`deploy/host_health.py` checks host-local listeners, DB existence, disk space
and backup receipt age. CI cannot certify a live host or real off-host access.

Gate C and its §7 full-launch content targets remain untouched.

- [Commons follow-up gameplay](COMMONS_FOLLOWUP_GAMEPLAY.md) — finite per-mask
  attention to real player-authored notices, replies and closures; no invented
  quests and no new hosting dependency.
