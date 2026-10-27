# FV-G00: Design authority and integration reconciliation

**Record version:** 2026-10-26. **Package:** FV-G00. **Status:** VERIFIED for FV-G00 only (2026-10-27 UTC, following independently reviewed PR #85, exact-head CI and successful main regression).
**Main baseline observed:** `d7e4ddc45305e35658f7c6bf48eef132b9dfa6be` (GitHub compare against `main`). Pre-integration SHA; the integrated main SHA is `f8cea11584022c827c92985a092028ac96eea449` with green push CI run `40450814068`. A PR base SHA is NOT the current main SHA.
**Canonical package source:** `ops/MASTER_GDD_GAME_COMPLETION_PROGRAM_2026-10-25.json` in merged PR #95.
**Acceptance:** authoritative/conflict register, selection of surviving code paths, no duplicate source files or incompatible lore, independently reviewed exact-head CI, authorized main integration, green exact-main regression. No deployment is part of this package.

## Governing order and immutable decisions

1. `files/frankenstein-village-world-bible-v0.2.md`: authoritative public world canon, Compact, setting, truths, tone and keeper decisions. Reviewed source blob `92ab66aad5af89076eb30697dcfac91a59500db1`.
2. `hidden_files/design-doctrine.md`: simulation, emic experience, Tarn, consent and keeper doctrine; subordinate to World Bible. Reviewed source blob `15e48e5b58393de12a9f789cb4b69f9817bf445e`.
3. `ops/CALLINGS_SIMULATION_DEPTH_PLAN.md`: implementation plan, not proof that Callings are complete. Reviewed source blob `93b0c6981f948f2a697b9790760c8f511739ed2d`.
4. Merged PR #95, head `16ab6d734be8eaf42cab5189d1e396e73a58ab00`: 31-page Master GDD **review draft**, 14-package FV-G00–FV-G13 program, 45-edge review register and 16 negative scenarios. Integration reference beneath canon, not itself a canon amendment.
5. Optional earlier alpha targets in PR #85 are interim planning only. Proposed model-free release contract in PR #89 applies to launch behavior *when independently reviewed and integrated*, not to changing higher-authority fiction or waiving GDD content targets.

**Unchanged boundaries:** one Evennia/Django world authority, no mandatory inference model, no new store/parallel brain, no unapproved Mystic B1–B4, no publication of secrets; 0/45 edge dossiers and 0/16 T-scenario dossiers have been independently certified from this record. Correct operational progression is committed -> exact-head CI -> reviewed -> merged -> exact-main CI -> hosted verification. The steps are NOT interchangeable.

## Historical dependency disposition (no branch resurrection)

| Item | Actual repository disposition | Surviving path and follow-up |
| --- | --- | --- |
| PR #78, model-led public NPC visibility | Closed, not merged; head `b32a0690bba09d385be651fdc33ab4b8239adaaa` | Optional agent experiment only. Do not introduce inference dependency into release. Compare future public agent visibility against the ordinary-client paths already present. |
| PR #88, market workshop | Merged; head `59fad6ab6531969ff7b851b01a220a999276f359` | Existing physical workshop is canonical code, do not reimplement. |
| PR #90, literal-newline Tavern guidance | Closed, not merged; head `24b29549296f22bb2a7c0b011af15205cd8d93bf` | Main still contains the two-character literal `\\n` in `newcomer.py`; **PR #89 branch already uses the correct escape**. Retain the #89 fix, never duplicate #90. Check final main after integrating. |
| PR #91, state-aware first evening | Closed, not merged; head `f25dccb0dca191073d1e2cdcaffdcf82af0f6b35` | PR #92 includes first-evening support and tests. Retire #91 rather than replay it. |
| PR #92, first-evening alternatives | Merged; head `5fc4fa6aa4e7c961903307f8ebdfd647e83ee341` | Main has `first_evening.py` plus state-aware first-evening tests; it is the surviving code. |
| PR #95 and PRs #103–#109 | All merged and closed, verified from GitHub PR metadata on 2026-10-26 | Preserve implementation; treat their feature evidence separately from full GDD package acceptance. No stacked PR dependency still open from these numbers. |

## PR boundaries audited before integration (historical snapshot, supplemented below)

| PR | Exact head SHA | State | Change ownership / decision |
| --- | --- | --- | --- |
| #85 | `f7c54219e5e6b86972aba2d22ae51e409e0961ac` | **MERGED** to main `f8cea11584022c827c92985a092028ac96eea449` | G00 reconciliation home; 4-file register/program/test/roadmap slice. Exact-head CI 40449718259 SUCCESS, Codex 6433775166 no major issues, main CI 40450814068 SUCCESS. |
| #89 | `8aaa19a73fac403179658c4b8588d9107b4a93f8` | Ready, mergeable, 17 files | **Selected model-free product contract and surviving #90 newline fix**. Exact-head clean-checkout regression 40379202445 succeeded. Two Codex comments resolved; Codex COMMENTED review is not an APPROVED review. Must reverify against today's main before merge. |
| #93 | `21c958cf7127ff17536eeab2af8e78fe684e1bac` | Draft, **unmerged**, latest CI 40450257908 SUCCESS | Static content inventory; stale merged-PR references corrected. No content-complete certification. |
| #94 | `3ed106acc20d3348f18446a46ad257e1c5552f5f` | Draft, **unmerged**, latest CI 40450179236 SUCCESS | 10-Calling/45-pair design, corrected World Bible precedence. No accepted Calling edge claimed. |
| #110 | `b4a3e304f126ddf9ec9507fde3016a4ca335bc64` | Ready, mergeable | Daily route history; requires separate role/return QA. |
| #111 | `099df5d300c5a765cd3268362d0822946c65420d` | Ready, mergeable | Independent grave witnesses and absent accounts; check confidentiality and restart. |
| #112 | `13961a2ebf79edecb36289c515d210c7d0af5c02` | Draft, mergeable | Soup conservation; independent gameplay acceptance/CI. |
| #113 | `8d6df09812ac6d73c71d003d492e3139fec53e23` | Draft, mergeable | Square warming; independent gameplay acceptance/CI. |
| #114 | `a0524f9142f502392e444d01bdfd5e38177fd7ae` | Ready, mergeable | Sourced public route map; independent review and GDD edge dossier. |
| #115 | `46cc7a2f58a7a2fde1e8d21d5c1db01c00005622` | Draft, mergeable | Performer/Innkeep hospitality; independent gameplay acceptance. |
| #116 | `9ed82a65aa049f9fb756c972b65907f56b294e15` | Draft, mergeable | Merchant/Chronicler calibration; independent gameplay acceptance. |
| #117 | `e42db4e09765ea51f1d45d1f0318e9dbb67d97ae` | Draft, mergeable | Merchant/Wanderer freight; independent gameplay acceptance. |

**Overlap determination:** GitHub changed-path audits give #85 exactly its roadmap file, #89 a model-free contract and runtime/tests, #93 three audit artifacts, #94 two design artifacts. These four changed-file sets are pairwise disjoint. This is a path-level no-overlap result, NOT proof that their semantics or their eventual merges are safe. The #85 early-access language was specifically reconciled with #89's optional-client policy; exact-main regression is still mandatory.

## FV-G00 pre-integration gate checklist (historical findings, superseded by signoff below)

| Requirement | Acceptance check | Evidence | Status / dependency |
| --- | --- | --- | --- |
| Canon precedence | World Bible > doctrine > depth plan / Master GDD review draft | Exact paths/blob IDs and governing order above | Source read complete; no proposed lore amendment |
| Existing code ownership | Surviving implementation for #90/#91 and previously merged #92/#95/#103–#109 | PR metadata; main file readback for `first_evening.py` and literal newline; #89 newline readback | Paths selected; #90 correction not yet on main |
| Historical conflicts | Recheck #78/#88/#90–#92; avoid duplicate branch merges | Closed/merged dispositions and per-PR changed files above | Recorded |
| Pending design overlap | #85/#89/#93/#94 exact files, drafts and scope | Changed-path comparison, main baseline SHA | File-path separation established; independent review not complete |
| Exact-head PR CI | Full clean checkout on final, reviewed commit | #89 run 40379202445 passed only at prior head; #85 latest head run 40449041298 initially in progress | Recheck after last edits; older CI never substitutes |
| Independent review | No unresolved findings; approval as required by branch policy | #89 two resolved threads, one COMMENTED review; #85 one unresolved feedback thread before wording update | **BLOCKED pending review / response** |
| Verified main integration | Authorized merge; changed files and GDD tests on exact new main SHA | Main `d7e4ddc45305e35658f7c6bf48eef132b9dfa6be` before G00 integration | **NOT DONE** |
| Launch boundary | No host, expense, service activation or release claims from PR green | Only source and GitHub metadata checked | Undeployed; separate post-game gate |

## Final acceptance signoff: FV-G00 verified, 1/14

**Code integrated:** reviewed [PR #85](https://github.com/Azimn/frankenstein-village/pull/85), head `f7c54219e5e6b86972aba2d22ae51e409e0961ac`, merged as main `f8cea11584022c827c92985a092028ac96eea449`. Exact-head clean-checkout CI [40449718259](https://github.com/Azimn/frankenstein-village/actions/runs/40449718259) **SUCCESS**. Exact integrated-main clean-checkout CI [40450814068](https://github.com/Azimn/frankenstein-village/actions/runs/40450814068) **SUCCESS**. Main source readback verified G00 integration register, status/evidence schema and no other prematurely verified package.

**Independent review and authorization:** Codex's exact-head re-review on PR #85, [comment 6433775166](https://github.com/Azimn/frankenstein-village/pull/85#issuecomment-6433775166), found no major issues after the inline concern was addressed/resolved. This is a reviewer no-issues result, **not** a formal GitHub APPROVED state. User directed completion of all necessary FV-G00 changes in this chat after the integration requirement was explained; the scoped authorization and exact-head merge checks were recorded in PR #85 comment 6433881259. No approval was granted for other PRs, hosting or public release.

**Boundaries and remaining dependencies:** Surviving #90 newline correction belongs to still-unmerged PR #89; main may still show the literal newline defect until that separate code integration is reviewed. PR #92 and #95/#103–#109 are already merged; #93 and #94 remain independent draft documents. The program now certifies **exactly one** GDD package, FV-G00, out of 14. Accepted Calling relationships remain **0/45**; individually certified negative scenarios remain **0/16**. Other GDD packages are still `planned`. Neither passing tests nor G00 acceptance establishes a host or a deployed game.

The certification ledger update itself must still undergo exact-head review/CI and main-branch CI on its own resulting SHA before the repository's 1/14 state is accepted as finally released.
