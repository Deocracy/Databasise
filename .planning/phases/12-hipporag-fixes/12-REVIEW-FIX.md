---
phase: 12-hipporag-fixes
fixed_at: 2026-10-19T00:00:00Z
review_path: .planning/phases/12-hipporag-fixes/12-REVIEW.md
iteration: 2
findings_in_scope: 3
fixed: 3
skipped: 0
status: all_fixed
---

# Phase 12: Code Review Fix Report (iteration 2)

**Fixed at:** 2026-10-19
**Source review:** .planning/phases/12-hipporag-fixes/12-REVIEW.md (iteration 2: 0 critical, 1 warning, 15 info)
**Iteration:** 2

**Summary:**
- Findings in scope: 3 (A-WR-05, plus the two Info items the coordinator named: IN-06, B-IN-07)
- Fixed: 3
- Skipped: 0
- Blocked on a protected-test grant: 0

**Verification:** edits and commits were made in the main checkout (`workflow.use_worktrees` is `false`). Per-fix checks were targeted pytest runs (parts_core, wirings, parts, validator, runner, evidence, parity and the HippoRAG seam tests: 779 passed after the A-WR-05 code change). The final `cd databasise && .venv/bin/python tools/check_offline_suite.py`, run in the main checkout after all three commits, passed in both styles: `pytest -q -rs` 2203 passed, 4 deselected; `python -m pytest -q -rs` 2203 passed, 4 deselected. No protected test file was edited. The four plant find strings are in files this iteration did not touch (`reset_vector_join.py`, `seam/engine.py`, `mcp/server.py`).

The iteration-1 fixes (commits 26ca959 through edd4883, ten findings) are unchanged and remain in the history.

## Fixed Issues

### A-WR-05: The dense stand-in on an empty PPR branch is invisible in the trace and absent from the port record

**Status:** fixed: requires human verification (D-21 behaviour)
**Files modified:** `databasise/parts_core/hipporag/assemble_result.py`, `databasise/parts_core/hipporag/fact_filter.py`, `databasise/wirings/hipporag/base.json`, `databasise/evidence/HIPPORAG-PORT-RECORD.md`, `databasise/tests/parts_core/hipporag/test_review_fixes.py`, `databasise/tests/seam/test_hipporag_review_fixes.py`
**Commit:** e85c3fc
**Applied fix:** Reused the existing guard mechanism, no new runner code. `assemble-result` now returns a guard-aware dict (`_StandInResult`, a subclass of fact-filter's `_GuardAwareResult`) with a `dpr_stand_in` flag, true when PPR was empty after the `score > 0` filter and `dpr-fallback` supplied items. `fact_filter._GuardAwareResult` gained one class attribute, `_flag = "guard_fired"`, so the subclass can compare a bool sentinel against `dpr_stand_in`; its behaviour is unchanged. `base.json` declares a per-query guard `empty_ppr_dpr_stand_in` (evaluating node `assemble-result`, `value_when_not_fired: false`) on the `assemble-result` node. The scheduler's existing rule `degraded = partial or any(guards_fired)` then reports the node's `guards_fired`, sets `degraded=True` with `stop_reason="declared_fallback"` and `degradation_reason="fallback_path_taken"` (the existing node-free codes), and leaves `partial` false. `corpus-ingest.json` is unaffected (it has no `assemble-result`). Consequences: the hipporag `config_hash` changes again; `parity/run_cross_modality.py` will refuse a HippoRAG arm that took this path, the same as the fact-filter guard (recorded in the port record). The flag is set only when the stand-in supplied at least one item, so an empty corpus with empty dense items is not reported as a substitution. The port record's D-20 entry now describes the divergence from upstream and the guard. The allowlist test in `test_review_fixes.py` gained `guards` for `assemble-result` (it has a reader: the scheduler).
**Test:** `test_an_empty_ppr_query_reads_degraded_with_the_node_free_reason` (in `tests/seam/test_hipporag_review_fixes.py`). It runs an ordinary three-document PPR query and asserts `guards_fired == []`, `degraded=False`, no stop or degradation reason. Then it patches `ppr`'s part body to zero every score (the stub corpus does not reach the degenerate reset vector by itself: a one-chunk query still scored 0.14) and asserts the `assemble-result` trace shows `["empty_ppr_dpr_stand_in"]`, the evidence is still returned, and the envelope reads `degraded=True`, `stop_reason="declared_fallback"`, `degradation_reason="fallback_path_taken"`. No protected test needed a change.
**Needs a human look:** the review's wording "a one-chunk corpus is always empty-PPR" does not hold under the stub clients, so the real-world frequency of this path is unmeasured. Whether the guard name should appear in the owner's S4 trace records is the owner's call.

### IN-06: Docstring and port record still say a synonymy pair is "never re-emitted"

**Files modified:** `databasise/parts_core/hipporag/synonymy_edges.py`, `databasise/evidence/HIPPORAG-PORT-RECORD.md`
**Commit:** f69256e
**Applied fix:** The `synonymy_edges.py` docstring sentence now says a pair is emitted once on the ingest that introduces it, except that a re-ingest restores the edges `document-remover` hid (A-CR-01). The port record's D-05 entry says the same and describes the restore (`removed_synonymy_edges`, endpoints still existing at the end of the run).

### B-IN-07: `list_kv_prefix` turns a benign WAL-removal race into a `StoreFault`

**Files modified:** `databasise/stores/probes.py`, `databasise/tests/seam/test_hipporag_review_fixes.py`
**Commit:** f886e2c
**Applied fix:** The WAL size is read in a `try`/`except FileNotFoundError`; a vanished WAL counts as no frames, and the later `live` check re-reads existence, so the state is re-checked rather than assumed. The test patches `Path.stat` to delete the WAL and raise `FileNotFoundError` for it, then asserts the listing succeeds.

## Skipped Issues

None.

## Notes for the orchestrator

- Other Info items from iteration 2 (IN-01..05, IN-07, B-IN-01..06, B-IN-08) were not in this iteration's scope and are untouched. B-IN-08 (the lax protected originals) still needs an owner `grant-check-edit`; the protected tests that remain lax are `tests/seam/test_hipporag_write_path.py:310-316`, `:394-399` and `tests/seam/test_hipporag_query_path.py:230-240`.
- Commits this iteration (each with the `phase/12` trailer and the Co-Authored-By line): e85c3fc (A-WR-05), f69256e (IN-06), f886e2c (B-IN-07). Hunks shared between findings in one file were split across commits so each commit holds one finding.

---

_Fixed: 2026-10-19_
_Fixer: Claude (gsd-code-fixer)_
_Iteration: 2_
