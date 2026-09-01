---
phase: 03-lightrag-query-side
fixed_at: 2026-09-01T00:00:00Z
review_path: .planning/phases/03-lightrag-query-side/03-REVIEW.md
iteration: 1
fix_scope: all
findings_in_scope: 3
fixed: 3
skipped: 0
status: all_fixed
fixes:
  - id: CR-01
    file: databasise/parts_core/lightrag/keywords.py
    commit: 8bf1357
    outcome: fixed
  - id: CR-01 (deviation record)
    file: databasise/evidence/DECLARED-DEVIATIONS.md
    commit: 03dfe05, 09cdcef
    outcome: fixed
  - id: WR-01
    file: databasise/runner/scheduler.py
    commit: 9c3d929
    outcome: fixed
  - id: IN-01
    file: databasise/parity/run_arm.py
    commit: 0588d53
    outcome: fixed
---

# Phase 03: Code Review Fix Report

**Fixed at:** 2026-09-01
**Source review:** .planning/phases/03-lightrag-query-side/03-REVIEW.md
**Iteration:** 1

**Summary:**

- Findings in scope: 3 (fix_scope=all, so Info tier was included this pass)
- Fixed: 3
- Skipped: 0

## Fixed Issues

### CR-01: `embedder-query` embeds an empty string for every arm that keeps the `keywords` node

**Files modified:** `databasise/parts_core/lightrag/keywords.py`, `databasise/parity/run_arm.py`, `databasise/tests/parts_core/lightrag/test_naive_arm_parts.py`, `databasise/tests/parity/test_naive_arm_end_to_end.py`, `databasise/evidence/DECLARED-DEVIATIONS.md`
**Commits:** `8bf1357`, `03dfe05`, `09cdcef` (orchestrator follow-up: `DECLARED-DEVIATIONS.md` is rendered by `parity_report.main()`, so the hand-added deviation section was moved into `render_deviations_markdown()` and covered by an on-disk-matches-render test; suite after: 419 passed, 4 skipped)
**Applied fix:** `keywords.py`'s `_keywords_body` now emits `"query": query` in both the
pinned-replay and live-call branches, matching `embedder_query.py`'s `_query_text` reader.

Reading the code before applying the reviewer's suggested diff surfaced a second, connected gap
the review itself did not call out: `run_arm.py`'s `_inject_query()` only ever stamped
`config["query"]` onto the `embedder-query` and `generate` nodes, never onto `keywords` itself —
so even with the output-shape fix, `_keywords_body`'s own `query = str(config.get("query", ""))`
was always `""` in every real run (not only when `keywords` is pinned), making the shape fix a
no-op in production. Extended `_inject_query` to also stamp `keywords`, closing the actual root
cause. This was caught by writing the new scheduler-level test (below) against the real injection
path rather than a hand-built `NodeContext` — the test failed against the shape-only fix and
passed once the injection gap was closed.

Also fixed the misleading unit test in `test_naive_arm_parts.py`
(`test_embedder_query_prefers_the_keywords_node_output_when_present`), which previously stubbed a
`{"query": ...}`-only `keywords` output shape the real body never produces; it now stubs the real
shape (`high_level_keywords`/`low_level_keywords`/`query`/`tokens`).

Added `test_hybrid_arm_embedder_query_embeds_the_real_query_text_via_run_wiring` in
`test_naive_arm_end_to_end.py`: runs the resolved `hybrid` arm through the real
`databasise.runner.scheduler.run_wiring` (via `resolve_arm`/`_inject_query`/
`_inject_pinned_keywords`/`parse_wiring`, not a hand-built `NodeContext`) with `keywords` pinned
and a spy embedding client, asserting the embedded text is non-empty and equals the injected
query. Downstream nodes (`entity-lookup`/`relation-lookup`) have no store access in this test and
fail with `StoreNotWiredError`, scoring the run `partial` — expected and asserted against, per the
module's own "partial outcomes are never discarded" contract; the assertion is against
`embedder-query`'s own captured result, not full-run completion.

Added a manual entry to `databasise/evidence/DECLARED-DEVIATIONS.md` recording that v2's
`entity-lookup`/`relation-lookup` embed one raw-query vector where v1 embeds two separate
keyword-derived vectors (`", ".join(ll_keywords)` / `", ".join(hl_keywords)`) — a structural
consequence of the frozen v2 wiring (one shared `embedder-query` node), not something this fix
changes, and not yet a measured excursion since no completed parity comparison run exists.

### WR-01: `_validated_token_allowance` does not refuse a negative `config.token_allowance`

**File modified:** `databasise/runner/scheduler.py`, `databasise/tests/runner/test_scheduler.py`
**Commit:** `9c3d929`
**Applied fix:** Mirrored `_validated_max_concurrency`'s shape exactly, per the review's suggested
fix: coerce to `int`, then refuse any value `< 0` with `InvalidTokenAllowanceError`, naming the
offending node, before any node is dispatched. Updated the error's message from "must be
coercible to int" to "must be >= 0" so it stays accurate for the new negative-value refusal path
too. Added `test_3c_negative_token_allowance_is_refused_at_validation_naming_the_node`, mirroring
the existing `test_3_max_concurrency_0_is_refused_at_validation_naming_the_node`.

### IN-01: `_load_env_file` is duplicated between `run_arm.py` and `v1_arm.py`

**Files modified:** `databasise/parity/run_arm.py`, `databasise/parity/v1_arm.py`
**Commit:** `0588d53`
**Applied fix:** Applied the review's suggested fix exactly: a one-line cross-referencing comment
on each `_load_env_file` definition, stating the absent-file behavior asymmetry (raise vs. return
`{}`) is deliberate. No behavior change; the two copies remain duplicated, not merged, per the
original finding's own stated house-style reasoning (each caller's dependency surface stays
obvious).

## Skipped Issues

None — all three in-scope findings were fixed.

## Verification

Ran inside the isolated review-fix worktree
(`.claude/worktrees/rf-03-480454-1788303784`, branch `gsd-reviewfix/03-480454`), not the main
checkout — reproducing these exact counts from the main checkout after cleanup requires checking
out the fast-forwarded commits on `main` and re-running the same commands there.

- `uv run pytest -q` (full `databasise` suite): **418 passed, 4 skipped** (up from the pre-fix
  baseline's 416 passed, 4 skipped — the +2 are `test_3c_negative_token_allowance_is_refused_...`
  and `test_hybrid_arm_embedder_query_embeds_the_real_query_text_via_run_wiring`).
- `uv run ruff check .`: **27 errors**, identical in count, file, and line to the pre-fix baseline
  (verified via `git diff 3dabb02 HEAD --stat` cross-checked against a `ruff check` run against
  the pre-fix commit) — no new ruff errors introduced by any of these fixes, including the two
  touched test files that already carried pre-existing `I001` import-sort findings before this
  pass.

---

_Fixed: 2026-09-01_
_Fixer: Claude (gsd-code-fixer)_
_Iteration: 1_
