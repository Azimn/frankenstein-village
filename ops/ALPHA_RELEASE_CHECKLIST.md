# Alpha release acceptance checklist

This is an operator-controlled decision record, not a certification that the
production server has been deployed. The CI suite and the release preflight
each provide evidence for different layers of readiness.

## Release evidence

Record these values for each deployment before inviting external players:

| Evidence | Required result | Actual evidence / date |
| --- | --- | --- |
| Exact deployed Git SHA | Identical to the reviewed merge commit | Not yet recorded |
| Fresh main-branch clean-checkout CI | Passed on exact deployed SHA | Not yet recorded |
| Persistent data volume | Survives process and host restarts | Not yet verified |
| Snapshot manifest and integrity | Verified current protected snapshot | Not yet verified |
| Disposable restore rehearsal | Restored and inspected away from live DB | Not yet verified |
| Off-host encrypted backup | Transferred snapshot and manifest to independent host/provider | Not yet verified |
| Alpha transport preflight | `ALPHA_TRANSPORT_RECOVERY_GREEN` from actual endpoints | Not yet run |
| Public HTTPS transport | Trusted TLS certificate and no downgrade | Not yet verified |
| Browser WSS transport | Verified HTTP 101 and valid Sec-WebSocket-Accept on public TLS endpoint | Not yet verified |
| AI-client usability | External AI client logs in, accepts compact, uses agentlogin/agent and plays/reconnects | Not yet verified |
| No bot blocking | Registered AI accounts can connect; abuse throttles remain effective | Not yet verified |
| Telnet transport policy | Loopback-only/plain or public TLS front end; no public plaintext credentials | Not yet verified |
| Fresh external account | Login, compact disclosure, consent choice | Not yet verified |
| Player mask and door | Creation, selection, OOC to IC transition, re-entry | Not yet verified |
| Persistence across restart | Same mask, possessions, resident state, situations, rumors, ledger | Not yet verified |
| Moderation | Report flows to human review; false report and abuse protections | Not yet verified |
| Clock and events | Scheduled cadence works without duplicate events after restart | Not yet verified |
| Recovery rollback | Tested documented rollback plan for failed deployment | Not yet verified |
| Incident contact and monitoring | Named human operator, uptime/error review, escalation route | Not yet verified |

## Procedure

1. Verify the exact deployment target and ensure no unreviewed migrations or
   local changes are present. Run the clean-checkout regression on that SHA.
2. Back up the live database with `ops/sqlite_snapshot.py`, and transfer
   snapshot plus manifest to protected off-host storage.
3. Restore into a disposable game environment, start Evennia there, and
   inspect account, mask, resident, case, ledger, and clock state.
4. Run `ops/alpha_preflight.py` against the candidate host and actual HTTPS
   endpoint, with a local or TLS-protected telnet banner check.
5. Use a dedicated external test account to exercise the compact, first
   character creation, travel, and one action in each persistent system.
   Check data before and after a clean server restart. Do not run the
   development telnet fixture against production since it creates accounts
   and alters world state.
6. Verify moderation reports have a working human review route and that
   errors, downtime, and backup failures will reach the operator.
7. Complete and sign the evidence table. If any required item is unverified,
   keep the launch decision **NO-GO**.

## Current decision

**NO-GO until the external deployment and recovery evidence above exists.**
A green GitHub Action means the reproducible development suite passed, not that
a public service is already running or recoverable.


Invited-alpha host and recovery plan:
[deploy/INVITED_ALPHA_GATES_A_B.md](deploy/INVITED_ALPHA_GATES_A_B.md).
This is a costed selection, not an established environment or proof that
off-host storage, restoration, human alert delivery or server monitoring work.
The off-host restoration script prints `host_drill_certified=false` even
after its isolated rehearsal succeeds. No Gate A/B checkbox should be checked
without actual operator-host evidence; Gate C remains out of invited-alpha
scope without changing any full-launch §7 targets.
