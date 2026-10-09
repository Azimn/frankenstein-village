# Invited alpha: Gates A and B execution runbook

Status: **platform candidate chosen; host NOT provisioned, drill NOT executed on
a host, multiplayer soak NOT started**. This is an operator playbook, not
launch evidence. Gate C is deliberately parked. Never revise the content
quantities in `files/frankenstein-village-quest-handoff-v0.3.md` §7 to
retroactively declare the invited alpha a full launch.

Canonical production code to deploy for this sequence:
`4bab7877b5664fe3b88ce02d1c71a417a48164be`. Operational scripts
developed after that commit can be copied from a verified release of `main`
without deploying additional gameplay code.

## Decision record: hosting and accountability

| Property | Invited-alpha selection |
|---|---|
| Provider | DigitalOcean, Basic Droplet (regular shared CPU) |
| Size | 2 vCPU, 4 GiB RAM, 80 GiB SSD, published $24/month |
| State volume | Droplet's persistent 80 GiB boot SSD, under the restricted service user's Evennia `server` tree |
| Off-host copy | Private DigitalOcean Spaces Standard bucket, published $5/month base (250 GiB included) |
| Infrastructure backup | Daily provider image backup, +30% of Droplet = $7.20/month |
| Baseline | **$36.20/month** before tax, domain, extra transfer/storage, growth and incident costs |
| Deployment | A single Linux VM, Python 3.12, pinned Git SHA, Nginx TLS and Evennia |
| Recovery accountable | **Azimn as repository owner or a specifically delegated human operator; acceptance PENDING** |
| Recovery executor | Operator with SSH/console, Spaces access, decryption key held OFF the Droplet |
| Test status | **UNPROVISIONED; host and backup/restore evidence not collected** |

Pricing verified against DigitalOcean:
https://www.digitalocean.com/pricing/droplets
https://docs.digitalocean.com/products/backups/details/pricing/
https://docs.digitalocean.com/products/spaces/details/pricing/

Nothing in this document grants permission to incur costs. An operator must
explicitly provision the subscription and accept recovery responsibility.
Choosing the platform here does not mark the issue #35 selection checkbox
complete until the provider account, named host, storage layout, budget
alerts, and recovery owner are actually recorded.

## Gate A, step 1: prepare the host

1. Provision one Ubuntu LTS Droplet with SSH keys, least-privileged `fvillage`
   service account, firewall and correct DNS. Provider monitoring must be
   enabled and verified. Restrict SSH by source IP where possible.
2. Install Python 3.12, Nginx including the stream module for optional
   terminal TLS, `awscli`, `age`, `logrotate`, Git, and any pinned
   requirements. Lock versions where possible. Do not expose internal ports.
3. Place runtime state on the persistent Droplet SSD, not an ephemeral
   container filesystem. Preserve the Evennia SQLite DB and sidecars when
   upgrading code. Only the operator may write world state. Never run
   `spike/tests/run_all.py` or QA fixtures against a populated host.
4. Checkout exactly `4bab7877` for the GAME deployment. Keep newer
   `ops/deploy/` operational tooling in a separate operators-only directory.
   Back up the database before EVERY update. Do not use a command such as
   `git clean -fdx` against the live server tree.
5. Read [AI_FIRST_HOSTING.md](AI_FIRST_HOSTING.md). Configure
   `FV_DEPLOYMENT_MODE=public`, valid FQDN, WSS proxy port 4042 and invited
   registration policy in a root-readable, non-Git environment file. First
   bootstrap requires operator-injected superuser secrets. Then verify
   certificates with `nginx -t`, HTTPS 443, WSS 4042 and optional
   TLS-wrapped terminal 4040. Firewall 4000/4001/4002/4005/4006 from the
   Internet. AI clients are allowed; abuse controls remain enabled.

## Gate A, step 2: produce a REAL off-host backup receipt

Run the already accepted `ops/sqlite_snapshot.py` **online backup** against
the actual server DB. Capture the output snapshot path and its adjacent
`.manifest.json`. Do not attempt a file copy of a live SQLite DB.

Operator example, showing variable placeholders rather than credentials:

```sh
umask 077
GAME_DB=/srv/fvillage/current/spike/fvillage/server/evennia.db3
BACKUP_DIR=/srv/fvillage/backups
mkdir -p "$BACKUP_DIR"
python3 ops/sqlite_snapshot.py backup \
  --database "$GAME_DB" --output-dir "$BACKUP_DIR"
# Choose the snapshot FILE printed by the command, never guess its name.
SNAPSHOT=/srv/fvillage/backups/<actual-generated-snapshot-name>.db3
python3 -c 'import sys;sys.path.insert(0,"ops");from pathlib import Path;from sqlite_snapshot import _verify_manifest;_verify_manifest(Path(sys.argv[1]))' "$SNAPSHOT"
```

Encrypt snapshot AND manifest as a single archive **before** upload. `age`
recipient public key is installed on the host; the private decryption
identity must remain with the recovery operator off-host. A private Spaces
bucket must forbid public reads and use restricted write-only credentials
where feasible.

```sh
cd "$BACKUP_DIR"
tar -cf - "$(basename "$SNAPSHOT")" "$(basename "$SNAPSHOT").manifest.json" \
  | age -r 'age1REPLACE_WITH_REAL_PUBLIC_RECIPIENT' \
  > "$(basename "$SNAPSHOT").tar.age"
sha256sum "$(basename "$SNAPSHOT").tar.age" > "$BACKUP_DIR/upload.sha256"
aws --endpoint-url https://nyc3.digitaloceanspaces.com \
  s3 cp "$BACKUP_DIR/$(basename "$SNAPSHOT").tar.age" \
  s3://REPLACE-PRIVATE-BUCKET/daily/
# DOWNLOAD it again to a separately controlled location, compare encrypted
# SHA-256 to the local upload, decrypt with the OFF-HOST private key, and
# verify both the source and retrieved SQLite manifests. Do not claim
# off-host success without this download-and-compare evidence.
```

On a genuine recovery station, obtain and decrypt the archive using the
operator's `age` private identity and recover the original file names into
`/recovery/retrieved/`. Set its permissions 0700. Transport receipts must
include provider bucket/object ID (nonsecret), date, size, digest, uploader,
downloader, and human reviewer. Redact host secrets, private identities and
user data; never commit raw DB or transcripts to public GitHub.

Once both copies exist, the isolated rehearsal command is:

```sh
python3 ops/deploy/alpha_restore_rehearsal.py \
  --source-snapshot /protected/backups/<snapshot>.db3 \
  --retrieved-snapshot /recovery/retrieved/<snapshot>.db3 \
  --evidence-out /private/evidence/restore-YYYYMMDD.json
```

The rehearsal refuses mismatched hashes/manifests, injects a change into a
TEMPORARY DB, restores retrieved off-host bytes, verifies category witness
counts, restores a saved rollback snapshot, and finishes back at the original
exact bytes. It NEVER changes the running game's database. Its JSON always
sets `host_drill_certified=false`: it is a necessary but insufficient test.

## Gate A, step 3: full production-environment restore drill

1. Collect an actual **pre-snapshot state inventory** on a protected operator
   console. Assert at least one non-staff test mask and owned Private Room,
   the world-event ledger and actual records, resident facts, published or
   pending Chronicle and Harbinger material, timed incident state, and
   inventory/resources. Record a SHA-256 digest/counter of each category,
   not the private contents themselves. Empty registries do not satisfy
   evidence for real content.
2. Restore the downloaded backup to an **isolated clone** of the selected
   host, with no public network or outbound notifications. Use
   `ops/sqlite_snapshot.py restore ... --confirm-server-stopped`. Inspect
   resulting rollback snapshot and manifest. Compare every category witness
   against the pre-snapshot inventory. Verify a character can log in to
   the clone, returns to the correct room, and finds all previously recorded
   state. Check the clock/tickers after actual restart.
3. Simulate an interrupted upgrade on the isolated clone and execute the
   written rollback. Confirm the exact pre-upgrade state returned and the
   server can restart. Record SHA, paths, timings, process state and result.
4. Independently verify off-host retrieval rights after Droplet deletion
   would be possible. Do **not** delete or restore a live game DB as the
   first recovery test.
5. Review/countersign the sanitized evidence. Gate A checkboxes remain
   unchecked for any missing category or missing verified remote copy.

### Emergency real-host restore and restart

Only after a human declares an incident, exports current evidence, records
affected user sessions, and verifies a usable off-host snapshot:

```sh
sudo systemctl stop fvillage
# Verify BOTH Evennia server and Portal are stopped, including child PIDs.
# Confirm SQLite sidecars are resolved without manually deleting uncheckpointed WAL.
python3 ops/sqlite_snapshot.py restore \
  --database /srv/fvillage/current/spike/fvillage/server/evennia.db3 \
  --snapshot /recovery/retrieved/<snapshot>.db3 \
  --rollback-dir /srv/fvillage/rollback \
  --confirm-server-stopped
# Retain the pre-restore rollback file AND .manifest.json.
sudo systemctl start fvillage
sudo systemctl status fvillage --no-pager
python3 ops/deploy/host_health.py \
  --database /srv/fvillage/current/spike/fvillage/server/evennia.db3 \
  --backup-receipt /srv/fvillage/receipts/latest-offhost-success
```

Use an operator-controlled systemd unit with a verified `ExecStart`,
`ExecStop`, and fail-on-start/health-check behavior. Evennia's
`evennia start` daemonizes; a systemd service that returns success on
launcher exit alone DOES NOT prove the child process remains healthy.
Test cold boot, deliberate process crash, and clean stop/start.

## Health, alerts and retention

- Install the DigitalOcean Monitoring agent. Configure and TEST CPU, RAM,
  disk utilization and host-down alerts delivered to a real human; sample
  initial thresholds 80% sustained for five minutes, subject to capacity
  observations. Verify delivery through a real alert, not just a settings
  screenshot. Resource monitoring is not game-tick monitoring.
- Run the read-only `host_health.py` on an operator timer (suggested once
  every minute). It checks required loopback listeners, DB path, disk
  headroom, and freshness of the **verified off-host upload receipt**.
  The receipt is created only after the actual download-and-compare. A local
  `touch` alone is NOT valid evidence that an off-host backup exists.
  Deliver any nonzero watchdog exit code to a human pager/email endpoint.
- Configure restricted journald/Eventnia logs, daily rotation for 14 days
  and a separate protected copy of security/moderation logs as required by
  policy. Verify that a log can be retrieved from yesterday and that neither
  passwords nor private room text are routinely exposed in logs. Preserve
  incident logs before rotation. Backups require an explicit 7-daily +
  4-weekly retention policy, confirmed in the Spaces bucket lifecycle.
- Establish a written operator escalation path: primary recovery owner,
  backup human contact, incident severity, protected recovery key storage,
  and after-hours notification. Record and demonstrate who can act.
- Record storage growth, process memory and CPU on the host continuously
  BEFORE attempting Gate B soak. Session command latency is not a substitute
  for server tick-latency measurements.

## Gate B, held pending Gate A evidence

Current prerequisite: Calibos's AI-first access audit passed at
`4bab7877`; accepted, no new audit work required. The client at
`ops/headless_ai_client.py` is test-backed but has NOT been validated
against a real public host. Do not start Phase 1 until actual deployment,
monitoring, backup, rollback and external login evidence are green.

Phase 1: **8 independent AI accounts, 30 minutes**. All must
login -> mask -> Tavern -> at least one legitimate game system. Immediately
abort on a server exception, or a session unable to complete this loop.
DO NOT run Phase 2 on the same day after a Phase 1 latency or reliability
failure. The existing headless client is a bounded functional probe: its
present invocation does **not** by itself provide a 30-minute controlled
load, account reinitialization, or verified live PvP.

Phase 2: **24 independent AI accounts, 2 hours** only after documented
Phase 1 acceptance. Record per-session p50/p95/p99 command latency,
disconnect/reconnect/recovery, host CPU/RAM, storage growth, event-tick lag,
and account-creation throttle counts. Include at least four live characters
in the Tavern; two must complete a peer-to-peer dice game and an entire
wrestling bout, not merely play solo or invite without completion. Perform
the live whittle-interrupt test with a clean dedicated mask and verify one
item. Human-led moderation stays available and account abuse is watched
without blocking AI automation.

After passing soak, publish a compact newcomer path: **notice a lead,
take a Calling, work with another player, leave a persistent consequence,
return next session**. Test a genuinely new account from login -> M. ->
Tavern -> one loop with a timed transcript, report stuck points and a
quotable moment or record unequivocally that the experience is not yet
worth having. Separately test report + appeal with two distinct accounts
and keep staff moderation outside the fiction.

## Evidence ledger, NOT automatic approval

| Gate / proof | State | Evidence |
|---|---|---|
| Calibos AI-first audit | Accepted | User-reported at `4bab7877` |
| Platform, 80 GiB persistent disk and budget | Planned only | This runbook; no Droplet ID |
| Recovery owner | Proposed, not accepted | Human acknowledgement required |
| Provider secrets and DNS | Not connected | No host evidence |
| Actual off-host receipt | Not executed | None |
| Isolated restore, rollback and category checks | Rehearsal tool exists; real test pending | CI verifies only disposable fixtures |
| Live stop/start, health and alert delivery | Not executed | None |
| Gate B Phase 1 / Phase 2 | **Not started** | None |
| Newcomer timed qualitative test and moderation | Not started | None |
| Gate C §7 inventory | **Out of scope** | Remains full-launch criterion |

Only checkbox evidence that has a real artifact and operator witness belongs
in issue #35. Public issue comments may link **sanitized metrics and digests**,
not production databases, player-private transcripts, passwords, or unredacted
moderation records.
