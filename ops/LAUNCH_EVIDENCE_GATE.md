# Public release evidence gate

`python ops/launch_gate.py /private/evidence/launch-manifest.json`
checks the **form** of a human operator's release attestation. The check
is deliberately stricter than a GitHub CI green badge: a fresh clean-checkout
game test is not equivalent to a running multiplayer server. **A local
language model or AI-controlled player is never required.** The required
`ordinary_account_access` and `ordinary_client_reconnect` checks concern
conventional non-staff MUD sessions, not model clients.

The manifest must contain:

- An exact 40-hex-character `deployed_sha` from the **actual deployed**
  game version, not an unrelated branch or a green PR.
- A named accountable `operator`, accepted by that human.
- For every key in `REQUIRED`, `passed: true`, the same exact
  deployment `sha`, a timezone-aware ISO8601 `verified_at` no older
  than thirty days, and a non-placeholder HTTPS `evidence_url` with an
  individually inspectable path. Plain HTTP, loopback/private IPs, fake
  `example.*` hosts, usernames in URLs, expired dates, date-only strings,
  missing entries and SHA mismatches keep the result **NO-GO**.
- Verified conventional browser/terminal account access and reconnection,
  without agent-only commands or model inference.
- Verified continuous connection soak under the chosen hosted conditions,
  event tick behavior under actual multiplayer load, independent review of
  game-breaking problems found during uncoached normal-interface playtests,
  and full-launch content requirements in addition to the earlier backup,
  security, moderation and return-play evidence. Use actual human players or
  other ordinary clients for these playtests. A language-model-driven client
  is optional testing equipment, not a dependency of the game's simulation
  or a separate launch prerequisite.

The operator should prepare the manifest in a **private** evidence folder,
not GitHub. Its JSON structure is illustrated below with intentionally
non-passing placeholders:

```json
{
  "deployed_sha": "REPLACE_WITH_ACTUAL_40_CHARACTER_GIT_COMMIT",
  "operator": "REPLACE_WITH_ACCEPTING_HUMAN_REVIEWER",
  "checks": {
    "exact_deployed_sha": {
      "passed": false,
      "sha": "REPLACE_WITH_ACTUAL_DEPLOYED_COMMIT",
      "verified_at": "REPLACE_WITH_ACTUAL_UTC_TIMESTAMP",
      "evidence_url": "REPLACE_WITH_ACTUAL_PRIVATE_AUDIT_LINK"
    }
  }
}
```

Add **every** key from `REQUIRED` with separate supported evidence.
The software will not fill in missing fields, invent a timestamp, verify
the remote contents of a URL, or accept an operator's name on the user's
behalf. Its only possible positive output is
`READY_FOR_OPERATOR_APPROVAL`, never `PRODUCTION_LIVE` or a
signed release certificate.

**Important limitation:** A syntactically credible link can still
point to false, stale or unrelated content. This tool does not retrieve
links, validate external certificates, authorize cloud billing, check
the true GitHub status, or prove backups can restore. A human operator must
independently inspect evidence, repeat critical tests and sign the deployment
decision outside the tool.

For an **invited alpha**, see `ALPHA_RELEASE_CHECKLIST.md` and
`deploy/INVITED_ALPHA_GATES_A_B.md`. The full-launch content quotas and
D1/D7 player-return requirements are not retroactively waived for a
public launch merely because an invited alpha has run.
