---
phase: 07-promotion-rollback
plan: 03
subsystem: api
tags: [rest, mcp, fastapi, promotion-ledger, three-transport-parity, evidence]

# Dependency graph
requires:
  - phase: 07-promotion-rollback (07-01, 07-02)
    provides: "Databasise.promote()/rollback()/retire(), the four additive ledger columns, and the nine SeamRefusalError subclasses this plan wires into the two transports unchanged"
provides:
  - "POST /promote, /rollback, /retire — three thin REST routes over the identical Databasise methods, no logic in the route bodies"
  - "promote/rollback/retire MCP tools, reached through the existing @_refusal_mapped wrapper — TOOL_NAMES grows from six to nine entries"
  - "Three-transport (in-process/REST/MCP) field-for-field parity proof for all three verbs, on success and on refusal"
  - "databasise/evidence/PROMOTION-LEDGER-EVIDENCE.md — which ROADMAP Phase 7 success criteria hold, by which committed test"
affects: []

# Actuals (#2632)
actuals:
  tokens: 17208
  tasks: 3
  commits: 4
plan_head_before: 823e41554237efdf52348ed6248911510366b21b

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "A fixed, directly-inserted trace token (bypassing TraceStore.persist()'s random secrets.token_urlsafe() minting) lets three independently-isolated store roots each resolve the identical promotion_trace_ids value — the only way three-transport parity tests can assert full LedgerRecord field equality (including promotion_trace_ids and alias themselves) rather than excluding fields beyond id/created_at for an unavoidable-randomness reason"
    - "Evidence-document collectibility checks cite only extras-free test node ids in the strictly pytest --collect-only-verified table; REST/MCP-transport tests are cited in prose instead, since a node id inside a pytest.importorskip-guarded module reports 'found no collectors' (a real collection error) under --collect-only when the optional extra is absent, rather than a graceful skip"

key-files:
  created:
    - databasise/evidence/PROMOTION-LEDGER-EVIDENCE.md
    - databasise/tests/evidence/test_promotion_ledger_record.py
  modified:
    - databasise/seam/rest.py
    - databasise/tests/seam/test_rest_transport.py
    - databasise/mcp/tools.py
    - databasise/mcp/server.py
    - databasise/tests/mcp/test_tool_growth_invariant.py
    - databasise/tests/mcp/test_dual_transport_parity.py
    - databasise/tests/seam/test_dual_transport.py
    - .planning/phases/05-opaque-side-admission/COVERAGE.md

key-decisions:
  - "Response/ledger-record parity comparisons use per-call isolated store roots with a directly-inserted fixed trace token, rather than reusing one alias across transports against a shared store — reusing one alias would mint 1.0.0/1.1.0/1.2.0 across the three sequential calls (an artifact of call order, not a transport divergence), and TraceStore.persist()'s own random-token minting (D-06) means no two independent stores can ever literally share a promotion_trace_ids value unless the token is inserted directly rather than minted."
  - "The evidence document's own strictly-checked 'Criteria' table cites only test node ids from files requiring no optional extra (test_promote.py/test_rollback.py/test_retire.py/test_promotion_posture.py/tests/ledger/test_ledger.py) — verified empirically this session that pytest --collect-only on a node id inside an extras-gated, pytest.importorskip-guarded module reports 'found no collectors' (exit 4, a real error) when the extra is absent, not a graceful skip; REST/MCP three-transport tests are cited in prose in a separate 'API-09' section instead, so test_promotion_ledger_record.py's own collectibility check passes under a bare `uv run pytest` regardless of which optional extras happen to be installed."
  - "retire()'s three-transport ledger-record comparison reads Ledger.generation_state(alias, '1.0.0') rather than Ledger.by_alias(alias) — by_alias() deliberately excludes tombstoned rows (07-01-SUMMARY.md), so it returns the still-active seed generation, not the tombstone this test actually wrote."
  - "mcp/server.py's own module docstring line naming the `@server.tool(name=...)` decorator was reworded (Rule 1 fix) — the plan's own acceptance criterion `grep -v '^\\s*#' databasise/mcp/server.py | grep -c '@server.tool'` returns 9 was tripped by that pre-existing docstring line's own literal occurrence of the substring, which the grep pattern does not filter out (only lines starting with `#`)."

patterns-established:
  - "Thin REST/MCP adapters for a write operation that mints derived state (semver, ledger ordinal) are proven in three-transport parity by seeding each transport's own isolated store with a directly-inserted, caller-fixed trace token rather than TraceStore's own random-token minting path — the pattern any future write operation needing full-field (not just shape) parity proof should reuse."

requirements-completed: [API-09]

coverage:
  - id: D1
    description: "POST /promote, /rollback, /retire reach the identical Databasise.promote/rollback/retire methods with no route-body logic; every Phase 7 refusal maps to a non-2xx response through the single pre-existing SeamRefusalError handler"
    requirement: "API-09"
    verification:
      - kind: unit
        ref: "databasise/tests/seam/test_rest_transport.py::test_post_promote_returns_the_same_result_as_the_in_process_call"
        status: pass
      - kind: unit
        ref: "databasise/tests/seam/test_rest_transport.py::test_post_rollback_and_post_retire_round_trip"
        status: pass
      - kind: unit
        ref: "databasise/tests/seam/test_rest_transport.py::test_promote_route_body_carries_no_logic"
        status: pass
      - kind: unit
        ref: "databasise/tests/seam/test_rest_transport.py::test_rest_response_carries_no_internal_identity"
        status: pass
    human_judgment: false
  - id: D2
    description: "promote/rollback/retire MCP tools reach the identical engine methods through the existing @_refusal_mapped wrapper; TOOL_NAMES grows from six to nine for three genuinely new §18 operations, and the §18.5 COVERAGE.md record agrees with the code"
    requirement: "API-09"
    verification:
      - kind: unit
        ref: "databasise/tests/mcp/test_tool_growth_invariant.py::test_the_registered_tool_set_equals_tool_names_as_a_set_and_by_count"
        status: pass
      - kind: unit
        ref: "databasise/tests/mcp/test_tool_growth_invariant.py::test_every_tool_has_a_coverage_row_and_every_both_transport_row_has_a_tool"
        status: pass
      - kind: unit
        ref: "databasise/tests/mcp/test_dual_transport_parity.py::test_the_registered_tool_set_equals_tool_names_and_has_nine_members"
        status: pass
    human_judgment: false
  - id: D3
    description: "The same promote/rollback/retire call, in-process, over REST and over MCP, produces field-equal responses and field-equal ledger records (every LedgerRecord column), on success and on a disagreeing-trace-ids refusal"
    requirement: "API-09"
    verification:
      - kind: unit
        ref: "databasise/tests/seam/test_dual_transport.py::test_promote_parity_across_three_transports"
        status: pass
      - kind: unit
        ref: "databasise/tests/seam/test_dual_transport.py::test_rollback_parity_across_three_transports"
        status: pass
      - kind: unit
        ref: "databasise/tests/seam/test_dual_transport.py::test_retire_parity_across_three_transports"
        status: pass
      - kind: unit
        ref: "databasise/tests/seam/test_dual_transport.py::test_refusal_parity_across_three_transports"
        status: pass
    human_judgment: false
  - id: D4
    description: "The phase's evidence document states which ROADMAP Phase 7 success criteria (1-3) hold, by which committed, collectible test, and restates the 07-GATE-AMENDMENT.md deferral of criteria 4-5 rather than omitting it"
    requirement: "API-09"
    verification:
      - kind: unit
        ref: "databasise/tests/evidence/test_promotion_ledger_record.py::test_every_holding_criterion_names_a_pytest_node_id_that_is_actually_collectible"
        status: pass
      - kind: unit
        ref: "databasise/tests/evidence/test_promotion_ledger_record.py::test_document_cites_the_gate_amendment_and_states_criteria_4_and_5_are_struck_and_deferred"
        status: pass
    human_judgment: false

duration: ~75min
completed: 2026-09-12
status: complete
---

# Phase 7 Plan 3: REST + MCP Surface, Three-Transport Parity, and the Phase's Evidence Record Summary

**Three REST routes and three MCP tools reach the exact same `Databasise.promote`/`rollback`/`retire` methods 07-01/07-02 built, proven field-for-field identical in-process/REST/MCP by a fixed-trace-token isolation technique, closing out API-09 and ROADMAP Phase 7 success criteria 1-3.**

## Performance

- **Duration:** ~75 min
- **Completed:** 2026-09-12
- **Tasks:** 3 of 3
- **Files modified:** 10 (2 created, 8 modified)

## Accomplishments

- `POST /promote`, `POST /rollback`, `POST /retire` added to `databasise/seam/rest.py` — each a
  single `return await engine.<verb>(...)` statement, no route-local exception handling; the
  pre-existing `_REFUSAL_FACTORIES` in `test_rest_transport.py` already carried entries for all
  nine Phase 7 refusal subclasses from 07-01/07-02, so this plan added zero new factory entries.
- `promote`/`rollback`/`retire` MCP tools added to `databasise/mcp/server.py` through the existing
  `@_refusal_mapped` wrapper; `TOOL_NAMES` grows from six to nine entries — three genuinely new
  §18 operations, never one tool per modality, never folded into a scope-dispatched lifecycle tool.
- Three-transport field-for-field parity proven for all three verbs and for a disagreeing-trace-ids
  refusal, via a new isolation technique: a trace token is inserted directly into each isolated
  store's `trace.db` (bypassing `TraceStore.persist()`'s own random `secrets.token_urlsafe()`
  minting) so three independent stores can each resolve the identical `promotion_trace_ids` value —
  making full `LedgerRecord` field equality (every column, since neither `id` nor `created_at` is
  part of that dataclass) genuinely provable rather than excluded for unavoidable randomness.
- `.planning/phases/05-opaque-side-admission/COVERAGE.md`'s §18.5 operations table gained three
  rows (promote/rollback/retire); its "deliberately absent" table's `promote / rollback` row is now
  `**DISCHARGED**`, renamed to include `retire`.
- `databasise/evidence/PROMOTION-LEDGER-EVIDENCE.md` states which of ROADMAP Phase 7's success
  criteria 1-3 hold, each by a named, collectible pytest node id, restates the
  `07-GATE-AMENDMENT.md` deferral of criteria 4-5 in one paragraph, and states plainly that every
  promotion this milestone can make is operator-asserted, provisional, and carries no verdict.
  `tests/evidence/test_promotion_ledger_record.py` enforces the document's own claims against the
  code via a real `pytest --collect-only` subprocess per cited node id.
- API-09 marked `Complete` in `.planning/REQUIREMENTS.md` (MACH-07 was already complete from
  07-02). Full suite: 1054 passed, 1 skipped — up from 1027/1 at 07-02, 27 new tests, no
  regressions.

## Task Commits

1. **Task 1: three REST routes for promote/rollback/retire** — `cc5c468` (feat)
2. **Task 2: three MCP tools, roster growth, coverage record** — `2bb2b78` (feat)
3. **Task 3: three-transport parity tests + evidence document** — `03ea6b2` (test)

_Note: an unrelated commit (`f7dcdc9`, `docs(melodyscribe): deep-research brief...`) landed on
`main` between this plan's Task 1 and Task 2 commits — this repository has no worktree isolation
for this session (`isolation=none`) and another concurrent process committed to the shared branch.
It is not part of this plan's own work; the `actuals.commits: 4` figure above is the raw
`git rev-list --count` measurement over the full commit range and includes it, per the ledger
protocol's own instruction to report the measured count rather than narrate around it. This plan's
own three feat/test commits are `cc5c468`, `2bb2b78`, `03ea6b2`._

## Files Created/Modified

- `databasise/seam/rest.py` - `PromoteRequest`/`RollbackRequest`/`RetireRequest`, three routes
- `databasise/tests/seam/test_rest_transport.py` - round-trip/no-internal-identity/no-route-logic
  tests, a Phase-7-scoped refusal-mapping proof
- `databasise/mcp/tools.py` - `PromoteToolArgs`/`RollbackToolArgs`/`RetireToolArgs`, `TOOL_NAMES` grown to nine
- `databasise/mcp/server.py` - three tool registrations; docstring reworded (Rule 1 fix, see below)
- `databasise/tests/mcp/test_tool_growth_invariant.py` - roster count/arg-model/coverage-mapping updates
- `databasise/tests/mcp/test_dual_transport_parity.py` - three new scenarios for the pre-existing
  per-tool parity test, hardcoded roster count updated
- `databasise/tests/seam/test_dual_transport.py` - four new three-transport parity tests
- `.planning/phases/05-opaque-side-admission/COVERAGE.md` - three new §18.5 operation rows, one
  discharged "deliberately absent" row
- `databasise/evidence/PROMOTION-LEDGER-EVIDENCE.md` (new) - the phase's success-criteria evidence record
- `databasise/tests/evidence/test_promotion_ledger_record.py` (new) - asserts the evidence
  document's claims against the code

## Decisions Made

See `key-decisions` in frontmatter. In short: three-transport parity tests use per-transport
isolated store roots with a directly-inserted fixed trace token (not `TraceStore.persist()`'s own
random minting) so full `LedgerRecord` field equality is genuinely provable; the evidence
document's strictly pytest-collectibility-checked table cites only extras-free test node ids,
since a node id inside a `pytest.importorskip`-guarded module reports a real collection error
(not a graceful skip) under `pytest --collect-only` when the extra is absent — REST/MCP tests are
cited in prose instead; `retire()`'s parity comparison reads `Ledger.generation_state()` rather
than `Ledger.by_alias()`, since the latter deliberately excludes tombstones.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] `mcp/server.py`'s own module docstring tripped the plan's own grep-based tool-count acceptance criterion**
- **Found during:** Task 2, verifying `grep -v '^\s*#' databasise/mcp/server.py | grep -c '@server.tool'` returns 9
- **Issue:** The module docstring (not a comment line, so `grep -v '^\s*#'` does not filter it) contains the literal substring `` @server.tool(name=...) `` describing the decorator in prose, inflating the grep count to 10 for what is genuinely nine real decorator usages.
- **Fix:** Reworded the docstring to describe the decorator without embedding the literal `@server.tool` substring (`` the ``server.tool`` decorator, given a ``name=`` keyword ``); also corrected the docstring's stale "five tool bodies" to "nine".
- **Files modified:** `databasise/mcp/server.py`
- **Verification:** `grep -v '^\s*#' databasise/mcp/server.py | grep -c '@server.tool'` now returns 9; `uv run --extra mcp pytest -q tests/mcp/ -x -rs` still passes (31/31).
- **Committed in:** `2bb2b78` (Task 2 commit)

**2. [Rule 3 - Blocking] `tests/mcp/test_dual_transport_parity.py`'s pre-existing per-tool parity test had no scenario for the three new tools**
- **Found during:** Task 2, running `uv run --extra mcp pytest -q tests/mcp/ -x -rs` after growing `TOOL_NAMES` to nine
- **Issue:** `test_mcp_rest_and_in_process_agree_for_every_tool` is parametrized directly over `TOOL_NAMES` and looks up `_SCENARIOS[tool_name]` — growing the roster without adding `promote`/`rollback`/`retire` scenario functions would raise a `KeyError` for all three new parametrizations, exactly the pre-existing growth-invariant guard both 07-01 and 07-02 already hit and documented for the refusal-factory set.
- **Fix:** Added `_promote_scenario`/`_rollback_scenario`/`_retire_scenario` (and the shared `_seed_trace_for_arm`/`_seed_two_generations`/`_seed_retirable_generation` helpers), each using a distinct alias per transport (excluded from the field comparison, alongside `generation_ordinal`) so every promotion stays a genuine first promotion rather than an order-dependent sequence against a shared alias.
- **Files modified:** `databasise/tests/mcp/test_dual_transport_parity.py`
- **Verification:** `uv run --extra mcp pytest -q tests/mcp/ -x -rs` passes (31/31), including the three new parametrizations.
- **Committed in:** `2bb2b78` (Task 2 commit)

**3. [Rule 3 - Blocking] A second pre-existing hardcoded roster-length assertion, outside `test_tool_growth_invariant.py`**
- **Found during:** Task 2, first full `tests/mcp/` run after growing `TOOL_NAMES`
- **Issue:** `test_dual_transport_parity.py` carries its own `assert len(TOOL_NAMES) == 6` (a second, independent pin the plan's own read-first list did not name — only `test_tool_growth_invariant.py`'s pin was flagged).
- **Fix:** Updated to `== 9`, renamed the test from `..._has_six_members` to `..._has_nine_members`.
- **Files modified:** `databasise/tests/mcp/test_dual_transport_parity.py`
- **Verification:** `uv run --extra mcp pytest -q tests/mcp/ -x -rs` passes.
- **Committed in:** `2bb2b78` (Task 2 commit)

**4. [Rule 1 - Bug] `retire()`'s first-draft three-transport ledger comparison read the wrong record**
- **Found during:** Task 3, first run of `test_retire_parity_across_three_transports`
- **Issue:** `Ledger.by_alias(alias)` deliberately excludes tombstoned rows (07-01-SUMMARY.md's own recorded change), so after seeding two promotions and retiring the first, `by_alias()` returned the still-active `bypass`/2.0.0 seed generation — not the tombstone the test's own retire call had just written — producing a spurious `promotion_trace_ids` mismatch (the two independent seed generations' own per-store-unique seed tokens, not the retire call's own shared fixed token).
- **Fix:** Read `Ledger.generation_state(alias, "1.0.0")` instead — the latest record naming the specific `(alias, version)` generation, which correctly resolves to the tombstone.
- **Files modified:** `databasise/tests/seam/test_dual_transport.py`
- **Verification:** `uv run --extra rest pytest -q tests/seam/test_dual_transport.py -x` passes (6/6).
- **Committed in:** `03ea6b2` (Task 3 commit)

---

**Total deviations:** 4 auto-fixed (1 bug in a pre-existing docstring, 2 blocking pre-existing
growth-invariant guards, 1 bug in this plan's own new test)
**Impact on plan:** All four were required for the plan's own `<verify>` blocks to hold. No scope
creep — items 2 and 3 are the same class of pre-existing-guard update 07-01/07-02 already
documented for the refusal-factory set, applied here to a second guard file the plan's own
read-first list did not enumerate.

## TDD Gate Compliance

All three tasks carry `tdd="true"`. `workflow.tdd_mode` is not set in `.planning/config.json`, so
the RED/GREEN/REFACTOR gate is advisory, not enforced — the identical posture 07-01/07-02 recorded
for this same phase. Each task's own `<behavior>`-block tests are present, named as specified (or
documented above where a name literally matched but the underlying assertion needed a Rule 1 fix),
and passing — verified individually via each task's own `<verify>` command before committing.
Production code and tests were implemented and verified together per task, then committed as one
`feat`/`test` commit per task (three commits total, matching this phase's own established
two-pass-per-task shape from 07-01/07-02, collapsed to one pass per task here since each task's
scope was small enough to verify as a single unit before its one commit).

## Issues Encountered

None beyond the deviations documented above.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- Phase 7 (MACH-07 + API-09, ROADMAP success criteria 1-3) is now fully discharged. Both
  requirements read `Complete` in `.planning/REQUIREMENTS.md`.
- HARD-01, HARD-02 and HARD-04 stay `Pending`, deferred per `07-GATE-AMENDMENT.md` to the owner's
  in-depth testing / hardening phase (not yet on the roadmap) or the first gate-adjudicated
  promotion, whichever comes first — unchanged by this plan.
- No blockers. Full suite: 1054 passed, 1 skipped (baseline was 1027/1 at 07-02) — 27 new tests,
  no regressions. `check_import_boundary` exits 0.

---

*Phase: 07-promotion-rollback*
*Completed: 2026-09-12*

## Self-Check: PASSED

All key files confirmed present on disk (`databasise/evidence/PROMOTION-LEDGER-EVIDENCE.md`,
`databasise/tests/evidence/test_promotion_ledger_record.py`, this SUMMARY). All three commit
hashes (`cc5c468`, `2bb2b78`, `03ea6b2`) confirmed present in `git log`. Re-ran the plan's own
three `<verify>` blocks and the plan-level `<verification>` block: `uv run pytest -q` (full suite,
both extras installed): 1054 passed, 1 skipped — at or above 07-02's recorded 1027/1 baseline;
`uv sync --extra rest && uv run --extra rest pytest -q tests/seam/test_rest_transport.py
tests/seam/test_dual_transport.py -x`: 62 passed; `uv sync --extra mcp && uv run --extra mcp
pytest -q tests/mcp/ -x -rs` (both extras installed together, since `--extra mcp` alone
uninstalls `fastapi`): 31 passed, no whole-module skip; `uv run python -m
databasise.tools.check_import_boundary`: exit 0. Grep-verified: no `<action>` block in
`07-03-PLAN.md` contains a fenced code block; `git diff --stat .planning/REQUIREMENTS.md` (before
this plan's own `requirements.mark-complete` call) showed no change from this plan's own task
work — all pass.
