# Master GDD §19.4 | Negative-case execution map

**Review status:** Phase A source audit, not a gameplay acceptance certificate.  
**Source baseline:** `9b16f73f1acec60cd7803476caaa744a5be4a42f`, with unmerged GDD PR #95 and source-audit PR #103.  
**Design authority:** [Master GDD §19.4](../docs/FRANKENSTEIN_VILLAGE_MASTER_GDD_REVIEW_2026-10-25.md); follow World Bible and existing game state on conflicts.  
**Structured ledger:** [16-case evidence register](PHASE_A_GDD_T01_T16_EVIDENCE_2026-10-25.json).

**Interpretation:** The GDD requires exact scenario execution on a normal client, authoritative world-state verification, race/privacy and restart proof, and eventually uncoached comprehension. Matching a nearby existing test is evidence of a subsystem foothold, **not** evidence that the complete GDD case passed. The source audit below deliberately counts *zero fully accepted GDD scenarios*.

| GDD test | Failure or adversarial setup | Existing nearby automated/source evidence | What must still be executed |
| --- | --- | --- | --- |
| T-01 | Deliver one finite item, restart mid-handoff | `ops/tests/test_courier_state.py:test_delivery_receipt_and_duplicate_guard`; `ops/tests/test_civic_commissions.py:test_restart_and_bounded_history` | Missing forced real process restart precisely between custody transfer and ledger commit. |
| T-02 | Two players reserve last material | `ops/tests/test_civic_commissions.py:test_two_accounts_exact_same_physical_object_and_no_replay`; `ops/tests/test_clinic_state.py:test_dressings_are_finite_and_clock_cannot_refill_backwards` | Missing simultaneous independent clients contending for the final identical stock unit. |
| T-03 | Retry finished lamp repair | `spike/tests/telnet_playthrough.py:repair finish north-square gas lamp`; `spike/tests/post_restart_assertions.py:lamp_repair_case["state"] == "aftermath"` | Post-restart physical state and pre-restart duplicate attempt exist; explicit retry after process restart remains untraced. |
| T-04 | Merchant market hold across offline clock | `ops/tests/test_market_standards.py:test_merchant_release_and_daily_renewal_with_explicit_history`; `spike/tests/telnet_playthrough.py:trade hold` | Pure day transition is covered; missing real offline clock passage with client reconnect/other-role progress. |
| T-05 | Chronicler prints unsupported claim | `spike/tests/post_restart_assertions.py:truth status must remain deliberately unset after restart`; `spike/tests/telnet_playthrough.py:story isn't a witness` | Missing targeted negative publisher action proving unsupported allegation never changes the actual object. |
| T-06 | Non-witness arrives after performance | `ops/tests/test_stage_state.py:test_real_audience_and_hour_guard`; `spike/tests/telnet_playthrough.py:stage witness` | Attendance/hour guards exist; missing explicit late-arrival independent client and post-restart social-memory check. |
| T-07 | Hound and Wanderer inspect same route | `ops/tests/test_route_surveys.py:test_collaboration_repeatability_and_event_receipts` | Current shared report does not establish distinctive passability versus threat/protection decisions. |
| T-08 | Healer assessment without patient consent | `ops/tests/test_clinic_state.py:test_today_requires_real_signed_assessment` | Existing treatment/assessment test is not patient privacy or consent; needs real patient-record permission case. |
| T-09 | Bodily need when item exhausted | `ops/tests/test_soup_state.py:test_real_daily_stock_and_no_duplicate_refill` | Food stock guards do not establish that every live bodily need has valid alternative relief when exhausted. |
| T-10 | Human versus AI client same action | `ops/tests/test_headless_ai_client.py:test_independent_accounts_recover_without_duplicate_items`; `spike/tests/telnet_playthrough.py:agent_json(out)` | AI client test uses fake transport; explicit independent human/AI same-state action parity matrix not evidenced. |
| T-11 | Rare inscription seen by two, missed by third | `ops/tests/test_mystic_circles.py:test_signed_approaches_and_independent_player_limit`; `spike/tests/telnet_playthrough.py:mystic study measure` | Signed studies and firsthand viewing exercised; missing explicitly coordinated 3-account witness/nonwitness test. |
| T-12 | Scheduled incident with no active players | `ops/tests/test_market_standards.py:test_merchant_release_and_daily_renewal_with_explicit_history` | Day renewal is not proof of a no-players scheduled event reaching its canonical NPC/expiry outcome. |
| T-13 | Two accounts cancel versus complete same order | `ops/tests/test_civic_commissions.py:test_two_accounts_exact_same_physical_object_and_no_replay` | Duplicate delivery guards exist; no documented competing cancellation/completion terminal transaction. |
| T-14 | Apprentice leaves consensual relationship | `spike/tests/telnet_playthrough.py:authored respecialization opportunity`; `spike/tests/post_restart_assertions.py:Respecialization did not erase the earlier Chronicler record.` | Profession respecialization is not a bilateral apprenticeship withdrawal; requires explicit two-account relationship test. |
| T-15 | Article corrected after dispute | `spike/tests/post_restart_assertions.py:Harbinger The Correction must survive restart as an archive discrepancy.`; `spike/tests/post_restart_assertions.py:source_deposition_id` | Archive and discrepancy persist; missing explicit after-correction resident recipient knowledge/awareness differentiation. |
| T-16 | Return after interrupted 1–2 hour activity | `ops/tests/test_return_agenda.py:test_returning_mask_sees_own_goal_without_undisclosed_board_content`; `ops/tests/test_civic_commissions.py:test_bad_bundle_and_day_renewal` | Agenda and expiry each work separately; missing integrated genuine interrupted multi-step responsibility and reentry narrative. |

## Engineering priorities extracted from the gap evidence

1. **Role differentiation:** T-07 is an explicit gameplay-content gap. Hound and Wanderer share a legitimate physical route survey, but distinct **threat/protection versus passability/logistics** outcomes on that same route have not been demonstrated. Extend the current route and resident-hazard state only after a targeted red-first test. No duplicate survey job or quest framework.
2. **Consent and player welfare:** T-08 requires a concrete protected patient-record access test. T-09 requires a depleted-supply relief alternative or preventing the corresponding bodily drive from shipping. The existing clinic and soup finite-input tests do not prove either condition.
3. **Exactly-once multiplayer:** T-02 and T-13 need simultaneous or interleaved two-account tests, not just sequential pure transitions. Record one material owner and one terminal order state, including proper failure text.
4. **Strengthen existing footholds:** T-01, T-03–T-06, T-10–T-12, T-14–T-16 have adjacent coverage. Preserve those tests and add only the exact GDD negative variant absent from the current traces.

## Review and evidence rules

Use the existing system owners and tests. Each T-case gets an exact commit, test ID, normal player command sequence, two-account identities where applicable, authoritative before/after, object/ledger provenance, bounded observer knowledge, real process restart, and independent usability note. A GDD test remains open when one of its required parts is unverified; CI success alone does not close it.

No Mystic B1–B4 canon decisions, gameplay mechanics, launch-contract edits, feature replacements, mergers, or hosted operations were made by this audit.
