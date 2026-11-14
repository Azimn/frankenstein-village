# FV-G01: Executable game-content and 45-edge coverage register

Status: **DELIVERY COMPLETE ON PR #93; ACCEPTANCE PENDING**. This record
describes the package's coverage-index deliverable, not finished GDD
relationships or a release. No branch code is on main until explicitly
reviewed and merged. Do not increase the official verified-package total
before independent review, authorized integration and exact-main CI.

## Authority and scope

World Bible v0.2 and `hidden_files/design-doctrine.md` outrank the
31-page Master GDD review draft. This package has no canon changes,
new world stores, invented Calling powers, deployments or model calls.

GDD package source: `ops/MASTER_GDD_GAME_COMPLETION_PROGRAM_2026-10-25.json`,
`FV-G01`. Package predecessor: verified `FV-G00`.

## Delivered reproducible index

The executable `ops/gdd_g01_evidence_register.py` now produces all:

- **21** content-family cards from the section-15 targets, with source file
  or candidate manuscript and measured counts only when inventory code
  actually provides a count.
- **10** Calling cards, with *registered* command classes and world-owner
  function paths, but no assertion of completed jobs or quest quotas.
- **45** distinct pairwise contract cards with source, command, room, owner,
  signed transition, real-restart and uncoached-UX coverage fields. Missing
  values are explicitly `null` / `UNVERIFIED`. Source-owner candidates do
  not claim that a pair-specific player action occurred.

All 76 cards expose the seven coverage fields, a provenance level, and an
explicit list of missing fields. CLI export supports JSON for follow-on
audits and Markdown for human merge review. No alternate game-state store
or SQL service is introduced.

The source-pinned historical CI receipt
`ops/GDD_G01_CI_OBSERVATIONS_2026-10-27.json` includes **seven partial
scripted client + restart examples** (edges 03, 04, 06, 10, 12, 19, 38)
from previously successful [run 40455328096](https://github.com/Azimn/frankenstein-village/actions/runs/40455328096)
at its stated source commit. The validator checks test-file Git blob IDs
and executable AST calls so modified code cannot inherit stale evidence.
That run is *historical*; it does not prove this branch's latest revision.

## Acceptance commands

From a clean checkout of **the exact PR head**:

```bash
python3.12 ops/gdd_g01_evidence_register.py --format json --source-ref "$(git rev-parse HEAD)" > /tmp/g01-evidence.json
python3.12 ops/gdd_g01_evidence_register.py --format markdown --source-ref "$(git rev-parse HEAD)" > /tmp/g01-evidence.md
python3.12 -m unittest discover -s ops/tests -p 'test_game_completion_audit.py' -v
python3.12 spike/tests/run_all.py
```

The JSON must report `coverage_index_complete: true`, exactly 21/10/45
cards, all seven required fields per card, 7 historical partial cases,
`verified_edge_count: 0`, `package_complete: false` (not yet integrated)
and `live_game_session_executed: false` for the *offline indexer*.
The full CI regression separately exercises real accounts and restart.
Index generation alone never does.

## Signoff boundary and next package dependency

This package is specifically **the trustworthy evidence register**, not
the implementation of all section-15 content or 45 fully playable
interactions. Those are later FV-G04 through FV-G11 requirements. Unknown
rooms, action chains, solo options and uncoached UX remain open requirements
with an explicit location in the register.

Before FV-G01 receives `status: verified` and the official package count
advances to **2/14**, require (1) successful exact-head clean-checkout CI,
(2) independent source/acceptance review, (3) explicit merge authorization,
(4) actual merge and new main SHA, and (5) passing exact-main regression.
This handoff does not grant merge authorization.

Next dependency: `FV-G02` maps the authoritative Evennia contracts and
qualifies GDD T-01 through T-16. Concurrent GDD relationship PRs must be
reconciled per edge ID rather than replacing each other's evidence.
