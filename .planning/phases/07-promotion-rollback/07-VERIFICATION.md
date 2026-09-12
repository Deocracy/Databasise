---
phase: 07-promotion-rollback
verified: 2026-09-12T00:00:00Z
status: human_needed
score: 3/3 roadmap success criteria verified; 1 open human-verification item (pre-existing, out of 07-04's scope)
covered_files:
  - ".planning/REQUIREMENTS.md"
  - ".planning/phases/07-promotion-rollback/07-01-PLAN.md"
  - ".planning/phases/07-promotion-rollback/07-01-SUMMARY.md"
  - ".planning/phases/07-promotion-rollback/07-02-PLAN.md"
  - ".planning/phases/07-promotion-rollback/07-02-SUMMARY.md"
  - ".planning/phases/07-promotion-rollback/07-03-PLAN.md"
  - ".planning/phases/07-promotion-rollback/07-03-SUMMARY.md"
  - ".planning/phases/07-promotion-rollback/07-04-PLAN.md"
  - ".planning/phases/07-promotion-rollback/07-04-SUMMARY.md"
  - ".planning/phases/07-promotion-rollback/07-GATE-AMENDMENT.md"
  - ".planning/phases/07-promotion-rollback/07-REVIEW.md"
  - ".planning/phases/07-promotion-rollback/07-VALIDATION.md"
  - "databasise/evidence/PROMOTION-LEDGER-EVIDENCE.md"
  - "databasise/ledger/ledger.py"
  - "databasise/mcp/server.py"
  - "databasise/mcp/tools.py"
  - "databasise/seam/engine.py"
  - "databasise/seam/promotion.py"
  - "databasise/seam/refusals.py"
  - "databasise/seam/rest.py"
  - "databasise/tests/seam/test_dual_transport.py"
  - "databasise/tests/seam/test_promotion_posture.py"
  - "databasise/tests/seam/test_rest_transport.py"
covered_digest: "v1:sha256:47f934a4472f59a73ac09c29d853125d1917c43ec546926a6c01f5e63e9786b3"
re_verification:
  previous_status: gaps_found
  previous_score: "2/3 live criteria fully verified; 1/3 (criterion 3) partial"
  gaps_closed:
    - "promote()'s verb was an unconstrained str and an out-of-enum value raised a bare ValueError from a foreign family instead of a named SeamRefusalError — closed by 07-04's UnrecognisedPromotionVerbError guard, checked first in promote()'s body"
  gaps_remaining: []
  regressions: []
human_verification:
  - test: "Fire two concurrent promote()/rollback()/retire() calls (or a promote() racing a retire()) against the same alias, e.g. via asyncio.gather() against two REST/MCP requests hitting the same alias at once."
    expected: "Either true serialization (one call fully completes before the other starts reading prior state) or a clean refusal for the loser — never two rows minting the same semver, and never retire()'s ActiveGenerationRetirementError guard passing on a generation that becomes active only after the guard's own read."
    why_human: "Genuine concurrency race requiring real parallel dispatch to trigger non-deterministically; grep/read confirms no asyncio.Lock/threading.Lock exists anywhere in engine.py (re-confirmed this run, unchanged since the previous verification and untouched by 07-04's scope), but only a live concurrent run demonstrates the actual outcome. Carried forward from the previous verification (WR-01/07-REVIEW.md) rather than re-litigated, since 07-04 did not touch _promote_sync/_rollback_sync/_retire_sync's dispatch shape."
---

# Phase 7: Promotion & Rollback Verification Report

**Phase Goal:** The owner can promote a wiring and roll it back on recorded evidence, with nothing
inferable by absence.
**Scope (per `07-GATE-AMENDMENT.md`):** ROADMAP success criteria 1, 2, 3 only. Criteria 4 and 5 are
struck; HARD-01/HARD-02/HARD-04 are deferred and are correctly **not** scored as gaps here.
**Verified:** 2026-09-12
**Status:** human_needed
**Re-verification:** Yes — after 07-04's gap closure of the previous run's sole gap (CR-01).

## Gap Closure Verdict (07-04 / CR-01)

**CLOSED.** Checked directly against the running code, not against SUMMARY.md's claim:

| Contract item (from the previous `gaps:` block) | Verified against code |
|---|---|
| `UnrecognisedPromotionVerbError` exists in `databasise/seam/refusals.py` as a `SeamRefusalError` subclass, exported | ✓ Confirmed: `class UnrecognisedPromotionVerbError(SeamRefusalError)` at line 360, between `InvalidChangeOriginError` and `GateVerbNotBuiltError`; present in `__all__` |
| The guard is the FIRST statement in `Databasise.promote()`, before trace-id resolution and any ledger read/write | ✓ Confirmed by reading `engine.py:1176-1178`: `if verb not in PROMOTION_VERBS: raise UnrecognisedPromotionVerbError(verb=verb)` is the literal first statement in the method body, preceding the `_NOT_BUILT_VERBS` check (line 1180) and `_resolve_operator_preconditions` (line 1183) |
| Accepted set comes from `typing.get_args(PromotionVerb)` via `PROMOTION_VERBS` in `promotion.py` — no second hand-maintained list | ✓ Confirmed: `promotion.py:62` — `PROMOTION_VERBS: frozenset[str] = frozenset(get_args(PromotionVerb))`; single occurrence of the derivation pattern, no parallel literal list found |
| `promote()`'s `verb` parameter annotated `PromotionVerb` | ✓ Confirmed: `engine.py:1152` — `verb: PromotionVerb = "operator-asserted"` |
| All three transports surface the identical `refusal_type` | ✓ Confirmed by reading `rest.py`'s single `add_exception_handler(SeamRefusalError, ...)` (unchanged, generic), `mcp/server.py`'s `_refusal_mapped` (unchanged, generic, `detail["refusal_type"] = type(exc).__name__`), and both `PromoteRequest`/`PromoteToolArgs` docstrings recording the deliberate `verb: str` (deserialization-only) decision. Live test run: `test_an_out_of_enum_verb_refuses_identically_across_three_transports` — 1 passed, asserting all three `refusal_type` values equal `"UnrecognisedPromotionVerbError"` in one body |
| A refusal leaves ZERO rows in the ledger | ✓ Confirmed: same test asserts `Ledger(store_root)._conn.execute("SELECT COUNT(*) FROM ledger").fetchone()[0] == 0` after all three transport calls; also independently asserted in `test_an_unrecognised_verb_refuses_by_name_before_any_trace_resolution`'s six parametrized cases |

Live re-run of the specific closure tests (not trusted from SUMMARY.md — executed this session):

```
uv run --extra rest --extra mcp pytest -q tests/seam/test_promotion_posture.py tests/seam/test_dual_transport.py -k "verb or Unrecognised"
→ 10 passed, 14 deselected

uv run --extra rest pytest -q tests/seam/test_rest_transport.py::test_every_refusal_subclass_maps_to_a_non_success_status_carrying_its_named_value
→ 30 passed
```

`git log --oneline -- databasise/seam/engine.py` confirms `214faff` ("feat(07-04): refuse an
out-of-enum promotion verb by name before trace-id resolution") is the top commit touching that
file, directly above `07-01`'s original `953b203`/`07-02`'s `94e36b5` — no undocumented later edit.

The bare-`ValueError` terminal branch inside `_promote_sync` (line ~1209-1216) now raises
`UnrecognisedPromotionVerbError(verb=verb)` instead of a foreign exception; the branch is kept as a
backstop (unreachable by construction post-guard) with a comment explaining why, per the plan's own
explicit instruction not to delete it.

**Verdict: 07-04 closes CR-01 exactly as specified. No new gap introduced by its changes.**

## Goal Achievement

### Observable Truths

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | Every generation record carries `change_origin` and `promotion_provenance`, never defaulted; a semver is minted at promotion and only at promotion; tombstoned losers are never lifted; the active pointer is a derived query | ✓ VERIFIED | `databasise/ledger/ledger.py:134-135` (`change_origin TEXT NOT NULL`, `record_kind TEXT NOT NULL`, no `ALTER TABLE` present in the file); `by_alias` (line 231) and `generation_state` (line 253) both use `ORDER BY id DESC LIMIT 1`, no written "current" column. Untouched by 07-04 (not in its `files_modified`); re-confirmed by direct read this session |
| 2 | Owner promotes by explicit call with `operator_asserted` provenance and non-empty `promotion_trace_ids`, no verdict/tier-of-decision; ledger append is the decision, alias repoint is atomic; rollback follows the same path | ✓ VERIFIED | `promote()`'s docstring (`engine.py:1172`) and body confirm one `Ledger.append()` call inside one `run_in_executor` dispatch, unchanged by 07-04 except for the guard ordering documented above and the terminal-branch exception-family fix. `test_promote.py`/`test_rollback.py`/`test_retire.py` all pass per verified full-suite run (1063 passed, 1 skipped) |
| 3 | `promote-next`/`promote-now` stay unavailable for answer-level/index-side classes under the default posture, and the refusal names the posture rather than failing silently — now including every out-of-enum verb string, not only the six declared literals | ✓ VERIFIED | Six declared verbs behave exactly as before (`test_no_gate_verb_appends_a_row`, `test_operator_asserted_verb_still_appends` pass unchanged); the previously-uncovered seventh case (any out-of-enum string) now refuses by name via `UnrecognisedPromotionVerbError`, checked first, before the not-built check, before trace-id resolution, before any ledger touch — closing the sole gap the previous verification scored against this criterion |

**Score:** 3/3 truths verified against the current codebase (not against SUMMARY.md's claim).

### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `databasise/seam/refusals.py` | `UnrecognisedPromotionVerbError(SeamRefusalError)`, keyword-only, `Any`-typed, in `__all__` | ✓ VERIFIED | Confirmed by direct read: matches `InvalidChangeOriginError`'s shape exactly, no menu/default implied in the message |
| `databasise/seam/promotion.py` | `PROMOTION_VERBS` derived via `get_args`, exported | ✓ VERIFIED | `frozenset[str] = frozenset(get_args(PromotionVerb))`, single occurrence, `"PROMOTION_VERBS"` in `__all__` |
| `databasise/seam/engine.py` — `promote()` | `PromotionVerb`-annotated, verb guard first-statement | ✓ VERIFIED | Confirmed line-by-line; guard precedes `_NOT_BUILT_VERBS` check and precondition resolution |
| `databasise/seam/rest.py`/`mcp/tools.py` | `verb: str` stays deserialization-only, no `Literal`/validator | ✓ VERIFIED | Both docstrings record the deliberate rejected-alternative rationale; no `field_validator` or `Literal` found on either `verb` field |
| `databasise/tests/seam/test_promotion_posture.py` | two new tests: refusal ordering + drift guard | ✓ VERIFIED | Both present, both pass live |
| `databasise/tests/seam/test_dual_transport.py` | one three-transport parity test | ✓ VERIFIED | Present, passes live, asserts all three `refusal_type` values in one body (not three separate tests) |
| `databasise/tests/seam/test_rest_transport.py` | `_REFUSAL_FACTORIES` entry for the new class | ✓ VERIFIED | Entry present; exhaustiveness test (30 cases) passes, meaning no `SeamRefusalError` subclass lacks a factory |

### Key Link Verification

| From | To | Via | Status | Details |
|------|----|----|--------|---------|
| `Databasise.promote`'s `verb` param | `UnrecognisedPromotionVerbError` | `PROMOTION_VERBS` membership check, first statement | ✓ WIRED | Confirmed by reading `engine.py:1177-1178` |
| `UnrecognisedPromotionVerbError` | REST 422 + `refusal_type` | `rest.py`'s single generic `add_exception_handler(SeamRefusalError, ...)` | ✓ WIRED | No transport-specific code added; live test confirms `status_code == 422`, `refusal_type == "UnrecognisedPromotionVerbError"` |
| `UnrecognisedPromotionVerbError` | MCP `ToolError` + `refusal_type` | `mcp/server.py`'s generic `_refusal_mapped` | ✓ WIRED | No transport-specific code added; live test confirms `ToolError` raised, JSON detail carries the name |
| `UnrecognisedPromotionVerbError` | REST exhaustiveness test | `test_rest_transport.py`'s `_REFUSAL_FACTORIES` | ✓ WIRED | Confirmed by reading the dict entry and the passing 30-case parametrized run |

### Behavioral Spot-Checks

| Behavior | Command | Result | Status |
|----------|---------|--------|--------|
| Out-of-enum verb refusal (in-process/REST/MCP + drift guard) | `uv run --extra rest --extra mcp pytest -q tests/seam/test_promotion_posture.py tests/seam/test_dual_transport.py -k "verb or Unrecognised"` | `10 passed, 14 deselected` | ✓ PASS |
| Refusal-exhaustiveness gate (every `SeamRefusalError` subclass has a factory) | `uv run --extra rest pytest -q tests/seam/test_rest_transport.py::test_every_refusal_subclass_maps_to_a_non_success_status_carrying_its_named_value` | `30 passed` | ✓ PASS |
| No stray `ValueError` on the promote path | `grep -v '^\s*#' seam/engine.py \| grep -c 'ValueError'` | `1` (the sole pre-existing unrelated `except ValueError` guard) | ✓ PASS |
| Full suite (from orchestrator's `verified_context`, no code changed since) | `uv run --extra rest --extra mcp pytest -q` | `1063 passed, 1 skipped` | ✓ PASS |
| Lock/serialization scan for WR-01 | `grep -n "asyncio.Lock\|threading.Lock\|Lock(" seam/engine.py` | no matches | confirms WR-01 unresolved, unchanged |
| Debt-marker scan on all 07-04-touched files | `grep -n "TBD\|FIXME\|XXX\|TODO\|HACK\|PLACEHOLDER"` across refusals.py, promotion.py, engine.py, rest.py, tools.py | no matches | ✓ PASS — no blocker |

### Probe Execution

No `scripts/*/tests/probe-*.sh` files exist in this project and no phase document references a probe script. **SKIPPED (no runnable probes declared or found).**

### Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
|-------------|------------|-------------|--------|----------|
| MACH-07 | 07-01, 07-02 | Append-only promote/rollback ledger, §7 field discipline | ✓ SATISFIED | Unchanged by 07-04; ledger schema/projections re-confirmed this session; `.planning/REQUIREMENTS.md` line 21 checked `[x]`, traceability table line 91 reads "Phase 7 / Complete" |
| API-09 | 07-01, 07-03, 07-04 | Operator can promote/rollback via RIG §PR.3's path, reachable identically over REST/MCP, including a named refusal for any invalid verb | ✓ SATISFIED (now fully, unqualified) | The verb-refusal gap that previously left this "satisfied as literally worded" with a flagged robustness gap is closed; `.planning/REQUIREMENTS.md` line 45 checked `[x]`, traceability table line 109 reads "Phase 7 / Complete" |
| HARD-01 | — (deferred) | Gate-script vacuous-pass repair | Pending, correctly deferred | `07-GATE-AMENDMENT.md`; unaffected by this run |
| HARD-02 | — (deferred) | ANATOMY §F / PARTS Appendix A reconciliation | Pending, correctly deferred | Same |
| HARD-04 | — (deferred) | Owner's corpus in eval bundle | Pending, correctly deferred | Same |

No orphaned requirements: MACH-07 and API-09 are the only two IDs mapped to Phase 7 in
`REQUIREMENTS.md`'s traceability table; 07-04's own frontmatter declares `requirements: [API-09]`,
consistent with it being a targeted gap-closure plan against the same requirement 07-01/07-03 already
claimed.

### Anti-Patterns Found

| File | Line | Pattern | Severity | Impact |
|------|------|---------|----------|--------|
| `databasise/seam/promotion.py` | 111-124 (`_arm_name_for_node_ids`) | First-match-wins arm resolution with no uniqueness guard | ⚠️ Warning | Carried forward from 07-REVIEW.md's WR-02; not touched by 07-04; not exploitable against the currently registered arm set; unchanged |
| `databasise/seam/engine.py` | `_promote_sync`/`_rollback_sync`/`_retire_sync` | No serialization (lock) across concurrent calls to the same alias | ⚠️ Warning | Carried forward from 07-REVIEW.md's WR-01; not touched by 07-04 (confirmed: no `asyncio.Lock`/`threading.Lock` reference anywhere in `engine.py`, re-checked this session); routed to Human Verification below rather than scored as a gap, because it requires genuine concurrent access to trigger and does not falsify either criterion's literal single-call wording |
| `databasise/seam/engine.py` (`rollback` docstring) | ~1248-1296 | `rollback()`'s docstring does not state (as `retire()`'s does) that the resolved arm need not match the rollback target | ℹ️ Info | Carried forward from 07-REVIEW.md's IN-01; untested behavior either way; unchanged |

No new anti-patterns introduced by 07-04's changes: all five files it modified were scanned directly
for debt markers (`TBD`/`FIXME`/`XXX`/`TODO`/`HACK`/`PLACEHOLDER`) — zero matches.

## Human Verification Required

### 1. Concurrent promote/rollback/retire on the same alias (WR-01 — carried forward, not a new finding)

**Test:** Fire two concurrent `promote()` calls (or a `promote()` racing a `retire()`) against the
same alias, e.g. via `asyncio.gather()` against two REST/MCP requests hitting the same alias at once.
**Expected:** Either true serialization (one call fully completes before the other starts reading the
prior state) or a clean refusal for the loser — never two rows minting the same semver, and never
`retire()`'s `ActiveGenerationRetirementError` guard passing on a generation that becomes active only
after the guard's own read.
**Why human:** Genuine concurrency race requiring real parallel dispatch to trigger
non-deterministically; grep/read re-confirms no lock exists (unchanged since the previous
verification), but only a live concurrent run demonstrates the actual outcome. 07-04 did not touch
`_promote_sync`/`_rollback_sync`/`_retire_sync`'s dispatch shape, so this item is carried forward
unresolved rather than re-litigated. The reviewer's severity rating (Warning, not Critical) and this
milestone's stated scope (single-process embedded engine) both argue for an owner decision on whether
this needs closing now or can ship with the risk accepted and tracked.

## Gaps Summary

**No gaps.** The previous verification's sole scored gap — `promote()`'s `verb` parameter accepting
any `str` and crashing with a bare `ValueError` (a 500 over REST, an unwrapped crash over MCP) on any
out-of-enum value — is closed. Checked directly against the running code and a live, targeted test
run (not trusted from SUMMARY.md's claim): `UnrecognisedPromotionVerbError` exists as a proper
`SeamRefusalError` subclass, is the first statement checked in `promote()`'s body (before the
not-built check, before trace-id resolution, before any ledger touch), derives its accepted set from
`typing.get_args(PromotionVerb)` with no parallel hand-maintained list, and surfaces the identical
`refusal_type` on all three transports with zero ledger rows written on the refusal path. All three
plans from the original phase (07-01/07-02/07-03) continue to hold after 07-04's edits to the shared
files they touch — re-confirmed directly, not merely assumed unchanged.

One pre-existing, out-of-scope concern (WR-01, the concurrent-access race) remains open from the
previous verification and is carried forward as a human-verification item rather than a gap, per the
same reasoning the previous verification applied: it does not falsify either success criterion's
literal single-call wording, and demonstrating it requires genuine concurrent dispatch that only a
human-directed test run can produce. Because it remains an open item in the Human Verification
Required section, the overall status is `human_needed` rather than `passed` — Phase 7's three ROADMAP
success criteria (1–3) are otherwise fully and unqualifiedly verified.

---

_Verified: 2026-09-12_
_Verifier: Claude (gsd-verifier)_
