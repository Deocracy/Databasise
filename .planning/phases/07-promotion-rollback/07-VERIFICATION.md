---
phase: 07-promotion-rollback
verified: 2026-09-11T00:00:00Z
status: gaps_found
score: 3/3 roadmap success criteria present-and-wired; 1 blocker anti-pattern found in the same subsystem as criterion 3
covered_files:
  - ".planning/REQUIREMENTS.md"
  - ".planning/phases/07-promotion-rollback/07-01-PLAN.md"
  - ".planning/phases/07-promotion-rollback/07-01-SUMMARY.md"
  - ".planning/phases/07-promotion-rollback/07-02-PLAN.md"
  - ".planning/phases/07-promotion-rollback/07-02-SUMMARY.md"
  - ".planning/phases/07-promotion-rollback/07-03-PLAN.md"
  - ".planning/phases/07-promotion-rollback/07-03-SUMMARY.md"
  - ".planning/phases/07-promotion-rollback/07-GATE-AMENDMENT.md"
  - ".planning/phases/07-promotion-rollback/07-REVIEW.md"
  - "databasise/evidence/PROMOTION-LEDGER-EVIDENCE.md"
  - "databasise/ledger/ledger.py"
  - "databasise/mcp/server.py"
  - "databasise/mcp/tools.py"
  - "databasise/seam/engine.py"
  - "databasise/seam/promotion.py"
  - "databasise/seam/refusals.py"
  - "databasise/seam/rest.py"
covered_digest: "v1:sha256:5dc890986147e02ce01171cd7278c1496e137d32457568ad080fbc3a4afbaa07"
gaps:
  - truth: "promote-next and promote-now stay unavailable for answer-level/index-side classes, and the refusal names the posture rather than failing silently (SC3) — evaluated against the full verb-refusal subsystem SC3 lives in, not only the two named verb strings"
    status: partial
    reason: >
      The six-member verb enum (`operator-asserted`, `check`, `preview`, `run`, `promote-next`,
      `promote-now`) each refuse correctly and by name — verified live and by test. But
      `Databasise.promote()`'s `verb` parameter is typed `str` (not the `PromotionVerb` `Literal`
      07-01-PLAN.md's own Task 3 action text explicitly requires), and neither
      `databasise/seam/rest.py`'s `PromoteRequest.verb` nor `databasise/mcp/tools.py`'s
      `PromoteToolArgs.verb` constrain it either. Any string outside the six-member enum (a typo,
      e.g. `"promote_next"` or `"Promote-Next"`) falls through to `_promote_sync`'s final branch,
      which raises a bare `ValueError` — not a `SeamRefusalError` subclass. Reproduced live in this
      session against HEAD (953b203..2bb2b78, no fix commit exists after them): calling
      `engine.promote(alias, [valid_trace_id], "human_edit", verb="promote_next_typo")` raises
      `ValueError("unknown promotion verb 'promote_next_typo'")`, uncaught by
      `rest.py`'s single `add_exception_handler(SeamRefusalError, ...)` (would 500, not 422) and by
      `mcp/server.py`'s `_refusal_mapped` wrapper (would crash the tool call, not raise a
      `ToolError`) — confirmed by reading both call sites; no test in
      `databasise/tests/seam/test_promotion_posture.py`, `test_rest_transport.py`'s
      `_REFUSAL_FACTORIES`, or MCP's refusal-parity tests exercises an out-of-enum verb string, so
      the crash path is untested and unguarded on both public transports. Nothing is written to the
      ledger on this path (confirmed live: 0 rows after the crash), so the ledger's own append-only
      discipline (criterion 1) is not implicated. This is 07-REVIEW.md's CR-01, filed the same day
      as this verification and still unresolved at HEAD.
    artifacts:
      - path: "databasise/seam/engine.py"
        issue: "promote()'s verb: str = \"operator-asserted\" parameter is untyped against PromotionVerb; the terminal branch (~line 1201) raises bare ValueError instead of a SeamRefusalError subclass for any value outside the six-member enum"
      - path: "databasise/seam/rest.py"
        issue: "PromoteRequest.verb: str carries no validator constraining it to the six-member enum, so a malformed value reaches the engine and 500s instead of 422ing"
      - path: "databasise/mcp/tools.py"
        issue: "PromoteToolArgs.verb: str carries no validator either, so the same malformed value crashes the MCP tool call instead of surfacing as a ToolError"
    missing:
      - "A named SeamRefusalError subclass (e.g. UnrecognisedPromotionVerbError) raised for any verb value outside the six known literals, checked before trace-id resolution runs (mirroring InvalidChangeOriginError's own placement and style)"
      - "A _REFUSAL_FACTORIES entry (REST) and an equivalent MCP refusal-parity case covering the new subclass, so the existing generic-handler tests actually exercise this path"
      - "A test asserting that an out-of-enum verb string refuses by name rather than crashing, on all three transports"
---

# Phase 7: Promotion & Rollback Verification Report

**Phase Goal:** The owner can promote a wiring and roll it back on recorded evidence, with nothing
inferable by absence.
**Scope (per `07-GATE-AMENDMENT.md`):** ROADMAP success criteria 1, 2, 3 only. Criteria 4 and 5 are
struck; HARD-01/HARD-02/HARD-04 are deferred and are correctly **not** scored as gaps here.
**Verified:** 2026-09-11
**Status:** gaps_found
**Re-verification:** No — initial verification.

## Goal Achievement

### Observable Truths

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | Every generation record carries `change_origin` and `promotion_provenance`, never defaulted; a semver is minted at promotion and only at promotion; tombstoned losers are never lifted; the active pointer is a derived query | ✓ VERIFIED | `databasise/ledger/ledger.py:134-138` (`change_origin TEXT NOT NULL`, `record_kind TEXT NOT NULL`, no `ALTER TABLE`); `by_alias` (line 231) and `generation_state` (line 253) both `ORDER BY id DESC LIMIT 1` with no written "current" column; `by_alias`'s WHERE clause excludes `record_kind != 'tombstone'`; `test_retire.py::test_never_lifted_repromotion_is_a_new_generation` and the full suite (1054 passed / 1 skipped) pass at HEAD |
| 2 | Owner promotes by explicit call with `operator_asserted` provenance and non-empty `promotion_trace_ids`, no verdict/tier-of-decision; ledger append is the decision, alias repoint is atomic; rollback follows the same path | ✓ VERIFIED | `Databasise.promote`/`rollback`/`retire` each contain exactly one `ledger.append(` call inside one `run_in_executor` dispatch (read `databasise/seam/engine.py:1143-1478`); `test_promote.py`, `test_rollback.py`, `test_retire.py` all pass; three-transport parity confirmed live (`uv run --extra rest --extra mcp pytest tests/seam/test_dual_transport.py -k promot` → 1 passed) |
| 3 | `promote-next`/`promote-now` stay unavailable for answer-level/index-side classes under the default posture, and the refusal names the posture rather than failing silently | ⚠️ PARTIAL — holds for the six declared verb values, fails for any other string | `test_promotion_posture.py` (all cases) pass for the six-member enum; `_MEASUREMENT_POSTURE` is a module-scope literal dict, read at one site, unreachable from env/config/constructor (`test_posture_is_not_flippable_at_runtime` passes). **But** an out-of-enum `verb` string bypasses the named-refusal architecture entirely — reproduced live this session, see Gaps below (CR-01) |
| 4 (deferred) | Owner's corpus in eval bundle before promotion | — struck | Per `07-GATE-AMENDMENT.md`; correctly not built, correctly not scored |
| 5 (deferred) | Gate scripts fail on missing extraction; ANATOMY §F reconciled | — struck | Per `07-GATE-AMENDMENT.md`; correctly not built, correctly not scored |

**Score:** 2/3 live criteria fully verified; 1/3 (criterion 3) verified for its literal enumerated
scope but co-located with a confirmed, reproducible, untested crash defect in the same
verb-dispatch subsystem (see Gaps).

### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `databasise/seam/promotion.py` | pure computation module: posture, semver, class derivation | ✓ VERIFIED | No `sqlite3` import, no `databasise.seam.engine` import; `_MEASUREMENT_POSTURE`, `mint_version`, `derive_mutation_class`, `resolve_single_arm` all present and match plan spec |
| `databasise/ledger/ledger.py` | 4 additive columns, `generation_state`, amended `by_alias` | ✓ VERIFIED | Confirmed via grep and read: `change_origin`, `record_kind`, `minted_version`, `targets_version` columns; no `ALTER TABLE`; both projections use `ORDER BY id DESC LIMIT 1` |
| `databasise/seam/engine.py` — `promote`/`rollback`/`retire` | three operator verbs, refuse-before-write | ✓ VERIFIED (with the CR-01 defect noted above) | All three methods present with the documented signatures; one `append()` each |
| `databasise/seam/rest.py` — 3 routes | thin adapters, no route-local logic | ✓ VERIFIED | `POST /promote`/`/rollback`/`/retire` are single `return await engine....(...)` bodies; single `add_exception_handler` registration |
| `databasise/mcp/tools.py`/`server.py` — 3 tools | `TOOL_NAMES` grows 6→9, `@_refusal_mapped` reused | ✓ VERIFIED | `TOOL_NAMES` = 9 entries ending `promote, rollback, retire`; 9 `@server.tool` registrations counted live |
| `databasise/evidence/PROMOTION-LEDGER-EVIDENCE.md` | evidence doc naming tests per criterion | ✓ VERIFIED | Criteria table cites collectible node ids; `tests/evidence/test_promotion_ledger_record.py` (7 tests) passes live and asserts the document's own claims against pytest collection |
| `.planning/phases/05-opaque-side-admission/COVERAGE.md` | 3 new §18.5 operation rows | ✓ VERIFIED | `promote`/`rollback`/`retire` rows present, each naming in-process/REST/MCP and `07-03` |

### Key Link Verification

| From | To | Via | Status | Details |
|------|----|----|--------|---------|
| `Databasise.promote` | `selectors._resolve_alias` | `Ledger.append` → `Ledger.by_alias` | ✓ WIRED | `test_promote_appends_one_row_the_alias_selector_resolves` passes; confirmed live |
| `Databasise.rollback`/`retire` | `Ledger.generation_state` | tombstone/unknown-version refusals | ✓ WIRED | `UnknownGenerationVersionError`/`TombstonedGenerationError`/`ActiveGenerationRetirementError` all present and raised at the documented call sites |
| `POST /promote`,`/rollback`,`/retire` | `Databasise.promote`/`rollback`/`retire` | thin route bodies | ✓ WIRED | Single-statement route bodies confirmed by reading `rest.py` |
| MCP `promote`/`rollback`/`retire` tools | same engine methods | `@_refusal_mapped` | ✓ WIRED | Confirmed by reading `mcp/server.py`; decorator stacking matches `delete_tool`'s shape |
| `promote()`'s `verb` param | a named refusal for out-of-enum values | — | ✗ NOT_WIRED | No such link exists; falls through to a bare `ValueError` (see Gaps) |

### Behavioral Spot-Checks

| Behavior | Command | Result | Status |
|----------|---------|--------|--------|
| Full test suite at HEAD | `cd databasise && uv run pytest -q` | `1054 passed, 1 skipped in 172.91s` | ✓ PASS (matches known_state exactly) |
| REST/MCP/in-process promote parity | `uv run --extra rest --extra mcp pytest tests/seam/test_dual_transport.py -k promot -x` | `1 passed, 5 deselected` | ✓ PASS |
| Evidence-document self-check | `uv run pytest tests/evidence/test_promotion_ledger_record.py -x` | `7 passed` | ✓ PASS |
| `promote()` with an unrecognised `verb` string | live Python repro (see gap detail) against a fresh temp store, seeded with a real resolvable trace id | `ValueError("unknown promotion verb 'promote_next_typo'")`, 0 ledger rows written | ✗ FAIL — confirms CR-01; nothing else in this defect corrupts state |
| MCP tool roster count | `TOOL_NAMES` read directly from `databasise/mcp/tools.py` | 9 entries, ends `promote, rollback, retire` | ✓ PASS |
| `@server.tool` registration count | `grep -c '@server.tool' databasise/mcp/server.py` | `9` | ✓ PASS |

### Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
|-------------|------------|-------------|--------|----------|
| MACH-07 | 07-01, 07-02 | Append-only promote/rollback ledger, §7 field discipline | ✓ SATISFIED | Ledger columns, projections, tombstone-never-lifted test all verified; the CR-01 defect writes nothing to the ledger, so this requirement's own text is not implicated |
| API-09 | 07-01, 07-03 | Operator can promote/rollback via RIG §PR.3's path, reachable identically over REST/MCP | ✓ SATISFIED (as literally worded) | The three verbs work identically on all three transports for valid input; the enumerated promote-next/promote-now refusal behavior this requirement names works correctly. The unvalidated `verb` field is a robustness gap in the same code path, not a failure of the requirement's own stated text — flagged as a phase-scope gap regardless (see Gaps) |
| HARD-01 | — (deferred) | Gate-script vacuous-pass repair | Pending, correctly deferred | `07-GATE-AMENDMENT.md`; REQUIREMENTS.md carries the dated deferral note, checkbox unchecked |
| HARD-02 | — (deferred) | ANATOMY §F / PARTS Appendix A reconciliation | Pending, correctly deferred | Same |
| HARD-04 | — (deferred) | Owner's corpus in eval bundle | Pending, correctly deferred | Same |

No orphaned requirements: MACH-07 and API-09 are the only two IDs mapped to Phase 7 in
`REQUIREMENTS.md`'s traceability table, and both appear in at least one plan's `requirements:`
frontmatter (07-01: both; 07-02: MACH-07; 07-03: API-09).

### Anti-Patterns Found

| File | Line | Pattern | Severity | Impact |
|------|------|---------|----------|--------|
| `databasise/seam/engine.py` | ~1201 | Bare `raise ValueError(...)` on a public-input-reachable path, instead of the codebase's own `SeamRefusalError` convention | 🛑 Blocker | Uncaught by both transport-level generic refusal handlers; a REST caller gets a 500, an MCP caller gets an unwrapped crash, for what should be a clean, named 422/`ToolError` refusal. Reproduced live this session (see Gaps) |
| `databasise/seam/promotion.py` | 111-124 (`_arm_name_for_node_ids`) | First-match-wins arm resolution with no uniqueness guard | ⚠️ Warning | Not exploitable against the currently registered arm set (confirmed no two arms share a node-id set today), but a future arm patch changing only `component` identity could silently promote the wrong wiring with no error. From 07-REVIEW.md's WR-02, unresolved at HEAD |
| `databasise/seam/engine.py` | `_promote_sync`/`_rollback_sync`/`_retire_sync` | No serialization (lock) across concurrent calls to the same alias | ⚠️ Warning | Confirmed live: no `asyncio.Lock`/`threading` reference anywhere in `engine.py`. Two racing calls on the same alias could mint a duplicate semver, misattribute `parent`, or let `retire()`'s active-generation guard pass on a generation that becomes active only after the guard's own read. From 07-REVIEW.md's WR-01, unresolved at HEAD. Routed to human verification below rather than scored as a gap, because it requires genuine concurrent access to trigger and does not falsify either criterion's literal single-call wording |
| `databasise/seam/engine.py` (`rollback` docstring) | 1248-1296 | `rollback()`'s docstring does not state (as `retire()`'s does) that the resolved arm need not match the rollback target | ℹ️ Info | Untested behavior either way; a future reader could "fix" it into an unwanted match check. From 07-REVIEW.md's IN-01 |

## Human Verification Required

### 1. Concurrent promote/rollback/retire on the same alias (WR-01)

**Test:** Fire two concurrent `promote()` calls (or a `promote()` racing a `retire()`) against the
same alias, e.g. via `asyncio.gather()` against two REST/MCP requests hitting the same alias at
once.
**Expected:** Either true serialization (one call fully completes before the other starts reading
the prior state) or a clean refusal for the loser — never two rows minting the same semver, and
never `retire()`'s `ActiveGenerationRetirementError` guard passing on a generation that becomes
active only after the guard's own read.
**Why human:** This is a genuine concurrency race that requires real parallel dispatch to trigger
non-deterministically; grep/read confirms no lock exists, but only a live concurrent run
demonstrates the actual outcome (duplicate version vs. SQLite-level contention error vs. silent
corruption). The reviewer's severity rating (Warning, not Critical) and the fact that this
milestone's stated scope is a single-process embedded engine both argue for a human decision on
whether this needs closing now or can ship with the risk accepted and tracked.

## Gaps Summary

Phase 7's core ledger/promotion architecture is sound and matches its own plans in detail: the four
additive ledger columns, the `generation_state`/`by_alias` projections, the three operator verbs,
the posture refusal for the six declared verb values, and three-transport parity are all verified
directly against the running code and a live test suite (1054 passed / 1 skipped, matching
`known_state` exactly).

One confirmed, reproducible defect survives in the same subsystem success criterion 3 lives in:
`promote()`'s `verb` parameter is unconstrained `str` at the engine, REST, and MCP layers, and any
value outside the six declared literals (a typo, not a genuine gate-verb attempt) crashes with a
bare `ValueError` rather than refusing by name — reproduced live this session against a real
resolvable trace id, with zero ledger corruption but a genuine 500/crash on both public transports.
This is 07-REVIEW.md's CR-01, filed the same day as this verification, and no fix commit exists
after 07-03's landing commits (`cc5c468`, `2bb2b78`). It also directly contradicts 07-01-PLAN.md's
own Task 3 action text ("declare `PromotionVerb = Literal[...]`... A value outside the enum is
refused by the type/validation layer before any resolution runs" — the code declares `verb: str`
and the check happens deep inside `_promote_sync`, not at the type/validation layer, and raises the
wrong exception family). This is scored as a blocker gap rather than an advisory note because it is
confirmed, reachable from both public transports this phase itself builds, untested, and a direct
deviation from the plan's own explicit instruction — not a hypothetical or deferred concern.

A second, lower-severity concurrency gap (WR-01) is routed to human verification rather than scored
as a blocking gap, because it requires genuine concurrent dispatch to demonstrate and does not
contradict either criterion's literal single-call wording.

---

_Verified: 2026-09-11_
_Verifier: Claude (gsd-verifier)_
