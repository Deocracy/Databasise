---
phase: 03-lightrag-query-side
fixed_at: 2026-09-01T22:44:20Z
review_path: .planning/phases/03-lightrag-query-side/03-REVIEW.md
iteration: 1
fix_scope: critical_warning
findings_in_scope: 4
fixed: 4
skipped: 1
status: all_fixed
fixes:
  - id: CR-01
    file: databasise/parity/run_comparison.py
    commit: 350caad
    outcome: fixed
  - id: WR-01
    file: databasise/stores/graph.py
    commit: c339cb9
    outcome: fixed
  - id: WR-02
    file: databasise/stores/vector.py
    commit: e20df3a
    outcome: fixed
  - id: WR-03
    file: databasise/runner/scheduler.py
    commit: 5105aa6
    outcome: fixed
  - id: IN-01
    file: databasise/parity/run_arm.py
    commit: null
    outcome: skipped (out of scope for fix_scope=critical_warning)
---

# Phase 03: Code Review Fix Report

**Fixed at:** 2026-09-01T22:44:20Z
**Source review:** .planning/phases/03-lightrag-query-side/03-REVIEW.md
**Iteration:** 1
**Verification environment:** isolated git worktree (`gsd-reviewfix/03-413960`), fast-forwarded onto `main` at cleanup. All test/ruff output below was produced in that worktree, immediately after each edit.

**Summary:**
- Findings in scope (critical + warning): 4
- Fixed: 4
- Skipped: 1 (IN-01, Info tier, out of `fix_scope=critical_warning`)

## Fixed Issues

### CR-01: `run_comparison.py`'s relation-id extraction crashes for `global` (always) and `hybrid` (in practice) arms

**Files modified:** `databasise/parity/run_comparison.py`, `databasise/tests/parity/test_retrieval_parity.py`
**Commit:** `350caad`
**Applied fix:** Replaced the `item['src_tgt'][0]`/`[1]` inline extraction with a new
`_relation_comparison_id` helper that reads `src_tgt` if present, otherwise falls back to
`(item.get("src_id"), item.get("tgt_id"))` — matching `join_roundrobin.py`'s own dual-shape
`_relation_key` dedup logic that the review cites as evidence both shapes legitimately survive
into `budget-relations`. Added a deterministic regression test in the existing "deterministic
group" of `test_retrieval_parity.py` (`test_extract_decomposed_ids_handles_mixed_relation_item_shapes_crossreview_cr01`)
that feeds `_extract_decomposed_ids` a `budget-relations` output mixing both item shapes and
asserts no `KeyError` and correct `src->tgt` ids for both.
**Verification:** `uv run pytest tests/parity/test_retrieval_parity.py -q` → 12 passed, 1 skipped
(pre-existing environment-dependent skip, unrelated to this fix). `uv run ruff check` on both
touched files reports the same 4 pre-existing errors present before the edit (confirmed via
`git stash`/`ruff check`/`git stash pop` diff) — no new violations introduced.

### WR-01: `CozoGraphStore._ensure_relations` swallows any exception whose message merely contains the word "relation"

**Files modified:** `databasise/stores/graph.py`
**Commit:** `c339cb9`
**Applied fix:** Narrowed the guard away from the bare `"relation" not in message` clause. While
narrowing, ran `test_index_done_callback_flush_is_durable_across_reopen` (which reopens a store on
an existing Cozo dir, exercising this exact path) and discovered Cozo's real re-create message is
**not** `"already exists"` — it is `"Stored relation <name> conflicts with an existing one"`
(observed via `pycozo.client.QueryException`). Per the review's own fallback guidance ("if Cozo's
actual re-create message lacks 'already exists', record the exact observed message instead"), the
guard now matches `"already exists"` or `"conflicts with an existing"` (the real observed phrase),
with a comment recording the exact string and citing the test that surfaced it — replacing the
overly broad bare-`"relation"` substring that could have swallowed unrelated schema/RocksDB/
permissions errors.
**Verification:** `uv run pytest tests/stores/test_graph.py tests/stores/test_graph_frozen_bugs.py -q`
→ 21 passed. Full `tests/stores/` → 61 passed. `uv run ruff check stores/graph.py` → all checks
passed.

### WR-02: `import_index.py` reaches into `FaissVectorStore`'s private attributes

**Files modified:** `databasise/stores/vector.py`, `databasise/parity/import_index.py`
**Commit:** `e20df3a`
**Applied fix:** Added `FaissVectorStore.iter_vectors() -> Iterator[tuple[str, np.ndarray]]`, a
minimal public accessor yielding `(doc_id, vector)` for every committed entry (placed next to the
existing `query()` method, in the "Reads" section). Switched `_v2_vector_pairs` in
`import_index.py` to call `store.iter_vectors()` instead of touching `store._entries`/
`store._index` directly. No new abstraction beyond the one accessor method the finding asked for.
**Verification:** `uv run pytest tests/stores/test_vector.py tests/parity/test_import_verification.py -q`
→ 16 passed, 1 skipped (pre-existing environment-dependent skip). `uv run ruff check` on both
touched files reports the same single pre-existing import-sort error present before the edit
(confirmed via `git stash` diff) — the new `Iterator` import was placed in the already-correct
alphabetical slot; the pre-existing `hashlib`/`asyncio` ordering issue is untouched by this fix.

### WR-03: `run_wiring`'s failed/cancelled nodes in a batch never call `ts.done()`

**Files modified:** `databasise/runner/scheduler.py`
**Commit:** `5105aa6`
**Applied fix:** Took the review's smaller, zero-behavior-change alternative: added explicit
invariant comments at both `continue` sites (the `node_failures` branch and the
`task.cancelled()` branch) documenting that skipping `ts.done(node_id)` is safe only because
`node_failures`/`budget_halted` being set forces the unconditional `break` immediately after the
batch loop, so the sorter's inconsistent state is never read again — and warning that a future
change which continues scheduling past a partial batch failure must not rely on this invariant
without fixing the `ts.done()` bookkeeping. No functional code changed.
**Verification:** `uv run pytest tests/runner/test_scheduler.py -q` → 13 passed. `uv run ruff check
runner/scheduler.py` → all checks passed.

## Skipped Issues

### IN-01: `_load_env_file` is duplicated verbatim between `run_arm.py` and `v1_arm.py`

**File:** `databasise/parity/run_arm.py:74-93`, `databasise/parity/v1_arm.py:98-116`
**Reason:** Info-tier finding, out of scope for `fix_scope=critical_warning` per the invocation's
explicit instruction. Not attempted.
**Original issue:** The two `.env.parity` KEY=VALUE parsers have drifted in absent-file behavior
(`run_arm._load_env_file` raises, `v1_arm._load_env_file` returns `{}`); the review's suggested
fix is a one-line comment on each definition cross-referencing the sibling copy and noting the
asymmetry is deliberate.

## Full-suite sanity check

After all four commits, ran the complete `databasise` test suite once from the fix worktree:
`uv run pytest -q` → **416 passed, 4 skipped** (same 4 environment-dependent skips as before any
fixes were applied — no new skips or failures introduced by this pass).

---

_Fixed: 2026-09-01T22:44:20Z_
_Fixer: Claude (gsd-code-fixer)_
_Iteration: 1_
