# Frankenstein Village: local playable Evennia alpha

Frankenstein Village is a **local, model-free multiplayer text game** built on
Evennia. This development alpha is suitable for repeatable technical testing,
not a public release or a declaration that the complete GDD has passed.

The canonical world, player permissions, clock, physical objects and signed
world-event ledger live in the existing Evennia game. No language-model service,
external host, or paid account is required to run it.

## Requirements and clean local installation

Use **Python 3.12** and a clean repository checkout. Work from the repository
root. Set unique local superuser credentials in your own shell, not in Git.

On Linux or macOS:

```bash
export EVENNIA_SUPERUSER_USERNAME=local_admin
export EVENNIA_SUPERUSER_EMAIL=local-admin@example.invalid
export EVENNIA_SUPERUSER_PASSWORD='choose-a-unique-local-password'
python3.12 spike/bootstrap.py
cd spike/fvillage
../venv/bin/evennia start
```

On Windows PowerShell, the equivalent local commands are:

```powershell
$env:EVENNIA_SUPERUSER_USERNAME = "local_admin"
$env:EVENNIA_SUPERUSER_EMAIL = "local-admin@example.invalid"
$env:EVENNIA_SUPERUSER_PASSWORD = "choose-a-unique-local-password"
py -3.12 spike/bootstrap.py
Set-Location spike/fvillage
..\venv\Scripts\evennia.exe start
```

The bootstrap creates a virtual environment, installs pinned dependencies,
initializes a local database and builds the canonical village. Run it only
against a **disposable local development checkout**, not an existing live
database. The automated clean-checkout test runner uses its own temporary
copy and does not modify the working game's database.

## Start, play, stop and restart

With the local server running, open a MUD/telnet client at
`localhost:4000`, or the built-in web client at
`http://localhost:4001`. Use two **separate accounts** in two independent
client sessions for cooperative Calling interactions. Each player creates
and enters their own mask. Ordinary onboarding uses `charcreate <mask>`
and `ic <mask>`, then the Inn's front door. Explore with `look`,
`examine`, `guide`, `help`, `calling` and compass directions.

The bridge route work uses the ordinary `bridgefit` command. A Wanderer
examines the original Riverside Path gauge and signs `survey gauge`.
A Hound examines the original Northern Treeline red cord and signs
`survey protect`. A different account with the active Smith Calling
uses `bridgefit forge span` or `bridgefit forge cord` at Market Lane's
physical civic material table, carries the finite item, and uses
`bridgefit install span` at the Old Stone Bridge or
`bridgefit install cord` at the Northern Treeline. Only a verified
installed span enables the optional `bridgefit cross` action. A Hound
can subsequently inspect and `bridgefit test cord`. The public room
description reports only completed ledger-verified work. These are
site-specific consequences, not a claim that every road is safe.

To stop and restart the same local world on Linux/macOS:

```bash
cd spike/fvillage
../venv/bin/evennia stop
../venv/bin/evennia start
```

On Windows PowerShell from the game directory:

```powershell
..\venv\Scripts\evennia.exe stop
..\venv\Scripts\evennia.exe start
```

Do not delete `server/evennia.db3` when testing persistence. The server's
normal stop/start preserves accounts, masks, world objects, signed event
receipts and Calling work. Check the original physical room after restart,
not just a copied command transcript.

## One reproducible clean-checkout smoke entrypoint

From the **repository root**, with Python 3.12 available:

```bash
python3.12 spike/tests/run_all.py
```

This is the project's existing authoritative smoke entrypoint. It copies
the source into a temporary directory, initializes a fresh disposable
Evennia database, executes Python unit regressions, launches real
authenticated telnet clients, checks physical world consequences, stops
and restarts the server, and runs postrestart assertions. It exits nonzero
on a failed gate and prints the failing logs. The test run may take several
minutes. On Windows, use `py -3.12 spike/tests/run_all.py`; Windows-specific
runtime success must be verified separately rather than inferred from
Linux GitHub Actions.

Record the exact source revision with `git rev-parse HEAD` and preserve
the corresponding GitHub Actions run and job logs when reporting results.
A green automated smoke test is **not** evidence of uninformed human
playtesting, accessibility acceptance, all 45 Calling relationships,
full GDD content quotas, or authorization for public G13 hosting.

For older implementation notes, see `spike/BUILD_NOTES.md`. Some early
spike descriptions are historical and do not describe the current game.
