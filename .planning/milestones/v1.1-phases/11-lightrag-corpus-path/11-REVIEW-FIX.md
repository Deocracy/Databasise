---
phase: 11-lightrag-corpus-path
fixed_at: 2026-10-18T00:00:00Z
review_path: .planning/phases/11-lightrag-corpus-path/11-REVIEW.md
iteration: 3
findings_in_scope: 4
fixed: 4
skipped: 0
status: all_fixed
---

# Phase 11: Code Review Fix Report

**Source review:** .planning/phases/11-lightrag-corpus-path/11-REVIEW.md (Part A)
**Iteration:** 2

## Iteration 1 — Part A (summary)

| Finding | Commit | Fix |
|---------|--------|-----|
| A-CR-01 | 937c640 | a cancelled corpus write holds the gate until the v1 thread returns |
| A-CR-02 | 86da892 | an id v1 already holds is not sent to v1 again |
| A-WR-03 | 91ffcc2 | v1's reserved source names are refused as document ids |
| A-WR-01 | e06bd0b | the sync manifest keeps pruned ids until every store committed |
| A-WR-02 | 347316f | a budget overrun never stops the sync after v1 committed |
| A-WR-04 | d1daff2 | a failed job record after a committed HippoRAG ingest is logged, not raised |
| A-WR-05 | 0cee44e | key-shaped tokens are redacted from the v1 stderr tail before it is logged |

A-WR-05 is accepted as partial. HippoRAG in-process errors stay unredacted, because the protected
`databasise/tests/seam/test_foreign_engine_refusal.py` pins the raw exception on the log record.

## Iteration 2 — Part A

Two regressions from the iteration-1 A-CR-01 fix (937c640). Its `to_thread_until_done` swallowed
every cancel until the worker returned, so the sync's `asyncio.wait_for` could no longer fire
(A2-WR-01), and the worker's outcome was dropped without a log line (A2-WR-02).

### A2-WR-01: the v1-index-sync 300 s ceiling was no longer enforced

**Files modified:** `databasise/parts_core/lightrag/full_ingest.py`,
`databasise/parts_core/lightrag/v1_index_sync.py`, `databasise/parts_core/lightrag/full_delete.py`
(docstring), `databasise/seam/engine.py`, `databasise/tests/seam/test_corpus_write_gate.py`
**Commit:** 0ee22ce
**Status:** fixed: requires human verification (concurrency logic)
**Applied fix:**
- `to_thread_until_done` runs the worker on a module executor. On a cancel or a `wait_for` timeout
  it stops waiting at once, parks the worker's `concurrent.futures.Future` in the
  `ABANDONED_WORKERS` context variable, and re-raises.
- `_write_gate` binds that list while it holds the gate. On exit, if any worker is parked, a daemon
  waiter thread runs `concurrent.futures.wait(parked)` and then releases the gate. The release
  therefore runs in a thread, not on the event loop, so it still happens if the loop has closed.
  Otherwise the gate is released at once, as before.
- The sync converts the `wait_for` `TimeoutError` into the existing
  `CorpusOpTimeoutError("sync", ceiling)`. The public failure class is `CorpusOpTimeoutError`, the
  node fails, and the engine drops pending ops. That class is in `_KEEP_STAGED`, so a raw upload v1
  already holds is kept.
- The iteration-1 cancel test asserted `not first.done()` after the cancel. That assertion
  described the old wait-on-cancel behaviour. It now asserts that the cancel returns at once, the
  gate stays held, a second write gets 409, and the gate frees after the thread returns.
- New test: `test_a_sync_over_its_ceiling_raises_the_timeout_fault_and_holds_the_gate_until_the_read_returns`.
  It patches the ceiling to 0.3 s against a 2 s read and checks four things: the fault arrives in
  under 1.5 s, the failure class is `CorpusOpTimeoutError`, the gate is held and a second write gets
  409 while the read runs, and the gate frees after the read returns. Against HEAD the ingest took
  2.4 s and the test failed.

### A2-WR-02: a cancelled or timed-out write discarded the worker's outcome silently

**Files modified:** `databasise/parts_core/lightrag/full_ingest.py`,
`databasise/tests/seam/test_corpus_write_gate.py`
**Commit:** ca230ac
**Status:** fixed
**Applied fix:**
- A given-up worker gets a done-callback, `_log_discarded`, which logs one server-side WARNING. A
  failed worker is logged with `failure_class=<type name>` and `redact_secrets(str(exc))`, the D-11
  stderr tail with the A-WR-05 redaction. A successful worker is logged with a line saying v1 may
  have committed.
- New test: `test_a_cancelled_write_logs_the_discarded_v1_failure_once_redacted` (caplog). It
  checks for exactly one record that carries `CorpusOpSubprocessError` and `sk-[REDACTED]` and does
  not contain the raw key. Against HEAD no record was logged and the test failed.

### Verification

- The gates ran in the main checkout (`workflow.use_worktrees=false`, no worktree).
- `cd databasise && .venv/bin/pytest -q tests/seam tests/foreign tests/parts_core/lightrag`: 953
  passed.
- Each new test was shown to fail with the HEAD source restored.
- ruff on the touched files reports only issues that already exist at HEAD: I001 in engine.py and
  in the test file, two RUF100, and ASYNC230 in engine.py.

## Iteration 2 — Part B

Scope: the Critical and Warning findings of Part B (B-CR-01..B-WR-06), applied under the
orchestrator's rulings. B-IN-01..B-IN-06 are Info and out of scope. This is the first attempt at
these findings (an earlier attempt was blocked by a ledger hand-off before it changed anything).
Frontmatter counts: 2 Part A iteration-2 findings plus 8 Part B findings.

| Finding | Commits | Status |
|---------|---------|--------|
| B-CR-01 | 7e1ebad | fixed: requires human verification |
| B-CR-02 | c42dc38 | fixed: requires human verification |
| B-WR-01 | d843ed0 | fixed: requires human verification |
| B-WR-02 | 9f7acb9, 9a63474 | fixed |
| B-WR-03 | 8e651ef, 987a292 | fixed: requires human verification |
| B-WR-04 | e2c43a5 | fixed |
| B-WR-05 | 780b9b6 | fixed |
| B-WR-06 | 2b7f609 | fixed (comment and docs only) |

### B-CR-01: promote, rollback and retire cannot resolve a real LightRAG query trace

**Files modified:** `databasise/wirings/resolve.py`, `databasise/seam/promotion.py`,
`databasise/seam/engine.py`, `databasise/tests/seam/test_promote.py`
**Commit:** 7e1ebad
**Applied fix:**
- `without_recipe_only_nodes` moved from the engine to `wirings/resolve.py` as the one shared
  helper. `engine._without_recipe_only_nodes` is now an alias of it, so the protected-style
  `test_query_trace_nodes.py` keeps working unedited.
- `promotion._arm_name_for_node_ids` compares the trace's node-id set with each wiring's run shape
  (recipe-only nodes removed). rollback and retire share this through
  `_resolve_operator_preconditions`.
- Deviation from the ruling, for review: the matcher also accepts a wiring's full node set. This
  keeps traces persisted before 11-10 resolvable, and it keeps the ten other test modules that seed
  full-set traces passing. A probe over `all_wirings()` shows that no full set equals another arm's
  run set, so the match is still unambiguous.
- `test_promote._seed_trace` builds traces in the post-11-10 shape. The new test
  `test_promote_and_rollback_resolve_real_naive_and_hybrid_query_traces` runs a real `engine.query`
  (naive) and a real hybrid run on a populated store, checks that neither trace has
  `embedder-index`, promotes from both, then rolls back to 1.0.0. With HEAD's `promotion.py`
  restored, 17 of the 21 test_promote tests failed.

### B-CR-02: no cosine threshold on any vector lookup

**Files modified:** `databasise/parts_core/lightrag/chunk_vector.py`, `entity_lookup.py`,
`relation_lookup.py`, `databasise/wirings/lightrag/base.json`,
`databasise/tests/parts_core/lightrag/test_cosine_threshold.py` (new)
**Commit:** c42dc38
**Applied fix:**
- The three lookups drop hits with v1's own test, `score < threshold` (faiss_impl.py:421). A NaN
  score is therefore kept and still reaches the evidence fault (protected `test_evidence_refs.py`).
- The score scale was checked. `FaissVectorStore` stores L2-normalised vectors in `IndexFlatIP` and
  normalises the query, so scores are cosine, the same as v1.
- `base.json` sets `cosine_better_than_threshold: 0.2` on entity-lookup, relation-lookup and
  chunk-vector. `cosine_threshold(config)` has no default of its own. v1's store has none either
  (faiss_impl.py:208-211), and a 0.2 part default would have broken the older part unit tests,
  which use sub-0.2 fake scores. A hand-built wiring that omits the key cuts nothing.
- `score_all` in chunk-sel-kg is not filtered, as the review asked.
- Tests: an orthogonal hit is dropped and a near hit kept, for each of the three parts. An
  off-topic query on naive, hybrid, local and global (seeded graph, keyword LLM filling both lists)
  returns `fail_response` with no generation call: 0 LLM calls on naive, 1 (keywords only) on the
  others. All 7 tests failed with the HEAD parts restored.

### B-WR-01: empty-namespace false positive

**Files modified:** `databasise/stores/vector.py`, `databasise/parts_core/lightrag/v1_index_sync.py`,
`databasise/tests/parts_core/lightrag/test_v1_index_sync.py`
**Commit:** d843ed0
**Applied fix:**
- New writer method `FaissVectorStore.ensure_index(dim)`. It is buffered like a write and commits
  an empty, valid index pair (checksummed sidecar, zero entries) through the normal prepare and
  commit path when no committed pair exists. It is a no-op when a pair exists, and
  `abort_prepared` and `drop` clear it.
- After mirroring, the sync calls it for chunks, entities and relationships, using the dimension
  of any mirrored vector kind.
- Limit: a sync that mirrors no vector at all has no known dimension and creates nothing. This only
  happens with zero processed chunks, so "never populated" is still true.
- Test `test_a_corpus_with_no_relations_is_answerable_on_global_and_hybrid`: a fake v1 commits
  chunks and entities but no relationships. The test checks that the relationships pair exists,
  opens clean and answers `[]`. Global and hybrid run undegraded, and again after a second sync
  (snapshot cache, STOR-08). At HEAD the relationships pair was missing and the test failed.

### B-WR-02: compare discards finished arms

**Files modified:** `databasise/seam/engine.py`, `databasise/tests/seam/test_compare_empty_namespace.py`
(new), `databasise/tests/seam/test_mutable_store_exclusion.py`
**Commits:** 9f7acb9, 9a63474
**Applied fix:**
- `compare` runs `_refuse_empty_namespaces` for every resolved wiring after its mutates_store
  pre-check and before any arm runs.
- New test: compare over naive and hybrid on a chunks-only store refuses with `EmptyNamespaceError`,
  with 0 LLM calls, 0 embedding calls and no new trace row. At HEAD naive ran first (1 LLM call).
- `test_comparison_between_two_non_mutable_wirings_is_unaffected` uses a spy on an empty root, so it
  now stubs the pre-check. The edit guard did not block this file.
- Ordering note: in a two-or-more-arm compare, a never-populated namespace is now refused before a
  store-open error. A single-arm query keeps STOR-02's order.

### B-WR-03: assemble chunk costing

**Files modified:** `databasise/parts_core/lightrag/assemble.py`,
`databasise/tests/parts_core/lightrag/test_kg_fidelity.py`,
`databasise/tests/parts_core/lightrag/test_naive_arm_parts.py`
**Commits:** 8e651ef, 987a292
**Applied fix:**
- KG arms cost `{content, file_path, chunk_id}` per chunk.
- The naive arm costs v1's `_get_vector_context` dict `{content, created_at, file_path,
  source_type, chunk_id}`. That dict is what v1's naive path truncates (operate.py:4302-4308,
  5842). This is narrower than the ruling's three keys, but it is what "as v1 does" means on the
  naive arm. `created_at` is None, because the sync strips v1's `__created_at__`.
- New test: with or without a 4000-char extra field, 10 chunks fit on both policies. At HEAD only 4
  fit.
- The existing naive budget test sized its budget from the old whole-item rule, so it is
  re-derived from v1's dict.

### B-WR-04: float-weight sort test

**Files modified:** `databasise/tests/parts_core/lightrag/test_kg_retrieval_fidelity.py`
**Commit:** e2c43a5
**Applied fix:** the equal-rank weights are now `"9.0"` (A-B) and `"10.0"` (A-C), and the expected
order is still A-D, A-C, A-B. With `_as_float` monkeypatched to an identity (a string sort), the
test fails at index 1.

### B-WR-05: keywords_extraction_examples drift guard

**Files modified:** `databasise/parts_core/lightrag/prompts.py`, `keywords.py`,
`databasise/tests/parts_core/lightrag/test_v1_prompt_drift.py`
**Commit:** 780b9b6
**Applied fix:**
- `PROMPTS["keywords_extraction_examples"]` is a list, as in v1. keywords.py builds `{examples}` with
  `"\n".join(...)` (operate.py:4175).
- The AST collector accepts a list of string constants, and the name is in `_DUPLICATED`. A new test
  compares the extractor's examples string with v1's join.
- Probe: a one-token change in a scratch copy of v1's prompt.py fails both the byte-identity test
  and the join test. With the HEAD sources restored, the set test fails.

### B-WR-06: chunk_top_k 10 vs 20

**Files modified:** `databasise/parts_core/lightrag/chunk_vector.py`, `databasise/wirings/lightrag/README.md`
**Commit:** 2b7f609
**Applied fix:**
- The value is unchanged. A `shortcut:` comment at `_DEFAULT_TOP_K` gives v1's chunk_top_k 20 and
  the upgrade path (config.top_k 20 with a parity re-baseline).
- The README provenance gains a "Known shortcut" note and lists the B-CR-02 threshold as edit 10,
  so "nine edits" becomes "ten edits". The recipe-only section now names the shared helper.
- There is no regression test, because the change is comment and docs only.
- Not changed: `parity/run_arm.py`'s stale "six listed edits" comment (B-IN-04, out of scope).

### Verification (Part B)

- The gates ran in the main checkout (`workflow.use_worktrees=false`, no worktree).
- `cd databasise && .venv/bin/pytest -q tests/seam tests/parts_core tests/parity tests/mcp`: 1258
  passed, 3 deselected. Also `tests/stores tests/wirings`: 187 passed.
- Each new or changed test was shown to fail against the HEAD source (restored with
  `git show HEAD:<path>`), except B-WR-06, which is comment-only.
- ruff on the touched files reports only issues that already exist at HEAD (I001 in several test
  files and in engine.py, RUF100, ASYNC230, RUF022).
- Process note: one read-only `git stash list` was run by mistake inside a probe command. It listed
  nothing and changed nothing.

## Iteration 3

Scope: the four Warning findings from the iteration-3 re-review. The re-review wrote no file, so
the findings and the rulings come from the orchestrator's prompt. Each fix has its own commit and a
regression test, and each test was shown to fail before its fix. Counts for this iteration: 4 in
scope, 4 fixed, 0 skipped.

| Finding | Commit | Status |
|---------|--------|--------|
| B3-WR-01 | 72e9c3b | fixed |
| A3-WR-01 | e580f41 | fixed: requires human verification (write-path logic) |
| A3-WR-02 | 3571afd | fixed |
| A3-WR-03 | dc5eea9 | fixed (test only) |

### B3-WR-01: the empty-namespace pre-check called a half-written pair "never populated"

**Files modified:** `databasise/seam/engine.py`, `databasise/tests/seam/test_empty_namespace.py`,
`databasise/tests/seam/test_compare_empty_namespace.py`
**Commit:** 72e9c3b
**Applied fix:**
- `_refuse_empty_namespaces` now calls `stores.vector.load_committed`, the same reader the run's
  open and the health probe use. `None` (neither file) is `EmptyNamespaceError`. A
  `VectorStoreCorruptedError` (one file without the other, an unreadable sidecar or index, or a
  checksum mismatch) is `_foreign_fault("query", ..., failure_class="StoreCorrupted")` (502).
- Both call sites (compare and `_execute_resolved`) share the helper, so both get the fix. The
  read fills the snapshot cache, so the run's own open is then a cache hit.
- Tests: a default query on an index-only pair, a meta-only pair and a garbage sidecar each raise
  `StoreCorrupted` with 0 LLM and 0 embedding calls. A two-arm compare whose hybrid arm sees a
  meta-only `entities` pair raises `StoreCorrupted` before either arm runs. Before the fix all 4
  failed: 3 with `EmptyNamespaceError` and 1 on the call-count assertion.

### A3-WR-01: a document v1 committed before a sync timeout was never mirrored to v2

**Files modified:** `databasise/seam/engine.py`, `databasise/tests/seam/test_corpus_write_gate.py`
**Commit:** e580f41
**Applied fix:**
- When the A-CR-02 precheck finds the id in v1, a LightRAG ingest now calls the new
  `_mirror_v1_index_only`. Under the same write gate and on the stores already open, it runs the
  corpus wiring's `lightrag/v1-index-sync` node alone, with no deps, and then calls `_commit_all`
  and `_narrow_sync_manifest`. A failure drops the pending writes and refuses, as a full ingest
  does. v1 is not called.
- The job keeps `enqueued: 0` and the original track id. It also carries the sync's MACH-11 events,
  as a committed ingest does (LRAG-03).
- The retry precheck never returns a job, so `retry_document` is unaffected.
- Test `test_a_reingest_after_a_sync_timeout_mirrors_the_document_v1_committed`. The first ingest
  times out in the sync (ceiling 0.3 s, read 1 s) after the fake v1 committed. The re-ingest
  returns `(original_track, 0)`, does not call v1 again and releases the gate. Afterwards the v2
  kv holds `a-chunk-000` and the manifest lists it. Before the fix the chunk was missing and the
  test failed.
- Behaviour change for review: a re-ingest of a held id now costs one O(corpus) mirror, and a
  failing mirror makes that re-ingest a 502 where it used to return `enqueued: 0`.

### A3-WR-02: an exception in `_write_gate`'s finally could hold the gate for good

**Files modified:** `databasise/seam/engine.py`, `databasise/tests/seam/test_corpus_write_gate.py`
**Commit:** 3571afd
**Applied fix:** `ABANDONED_WORKERS.reset(token)` now runs in an inner `try`. The release, either
immediate or deferred to the waiter thread for parked workers, sits in that try's `finally`.
**Tests:** a stand-in `ABANDONED_WORKERS` makes the first `reset` raise.
- `test_a_failing_gate_cleanup_still_releases_the_gate`: the ingest raises the cleanup error, the
  gate is free, and the next ingest is admitted.
- `test_a_failing_gate_cleanup_still_defers_the_release_to_a_parked_worker`: the gate stays held
  while a parked future is pending, is released once the future resolves, and the next write is
  admitted.
- Before the fix both failed, because the gate stayed held.

### A3-WR-03: the A2-WR-02 redaction test was vacuous

**Files modified:** `databasise/tests/seam/test_corpus_write_gate.py`
**Commit:** dc5eea9
**Applied fix:**
- The fake now raises a raw `RuntimeError` whose message carries `sk-live1234secret`. Only
  `_log_discarded` can redact it now, because `CorpusOpSubprocessError` redacts in its constructor.
- The test asserts `failure_class=RuntimeError`, that `sk-[REDACTED]` is in the record and that
  the raw token is nowhere in `caplog.text`. The import of `CorpusOpSubprocessError`, now unused,
  is removed.
- Probe: I backed up `parts_core/lightrag/full_ingest.py` to the scratchpad and changed
  `_log_discarded` to log `str(exc)` without redaction. The test then failed: the record held the
  raw key and no `sk-[REDACTED]`. I restored the file with the Edit tool and confirmed it with
  `git diff --quiet` and `cmp` against the backup. The test passes again.

### Verification (iteration 3)

- The gates ran in the main checkout (`workflow.use_worktrees=false`, no worktree).
- `cd databasise && .venv/bin/pytest -q tests/seam tests/foreign tests/parts_core tests/mcp`: 1157
  passed (408.9 s). The real-v1 corpus-path tests in `test_lightrag_corpus_path.py` ran and passed.
- ruff, run on its own on each touched file, reports only issues that already exist at HEAD: I001
  in engine.py and test_corpus_write_gate.py, two RUF100 and ASYNC230 in engine.py.
- Process note: the BAK check-edit guard blocked two read-only commands, a grep across
  `databasise/tests` and a pytest call wrapped in `time`. Each was rerun in a narrower form, and no
  protected file was edited.

---

_Fixer: Claude (gsd-code-fixer)_
_Iteration: 3_
