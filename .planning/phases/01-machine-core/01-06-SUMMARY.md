---
phase: 01-machine-core
plan: 06
subsystem: stores
tags: [cozo, faiss, embedded-storage, d-05, d-07, d-14, port-by-copy]

# Dependency graph
requires:
  - phase: 01-machine-core
    provides: "01-02's stores/base.py StorageNameSpace lifecycle ABC and the store_root/workspace/namespace directory pattern established by SqliteKVStore"
provides:
  - "databasise.stores.graph.CozoGraphStore — embedded Cozo (RocksDB) graph store, one database file per namespace directory, four deferred-write buffers, bound-parameter queries, off-loop dispatch"
  - "databasise.stores.vector.FaissVectorStore — embedded Faiss (IndexIDMap2 over IndexFlatIP) vector store, one index+sidecar pair per namespace directory, precomputed-embedding pending buffer, raise-before-mutation on count mismatch, two-phase index+sidecar commit"
  - "databasise/tests/stores/test_graph_frozen_bugs.py — non-skippable regression suite binding Cozo 0.7.6's four known bugs (#244, #296/#269, #253, #275) to the new adapter"
affects: ["01-07", "01-08", "01-09"]

actuals:
  tokens: 11136
  tasks: 3
  commits: 3

tech-stack:
  added: []
  patterns:
    - "Deferred-write buffer discipline (four in-process buffers for graph, one pending-doc buffer for vector), read-your-writes before flush, cleared on index_done_callback (commit) or drop_pending_index_ops (abort) — same shape as 01-02's SqliteKVStore, now proven across three different backends"
    - "Two-phase temp-file-then-os.replace commit for the vector store's index+sidecar pair: both write to .tmp files first; a failure at either step leaves the previously-committed pair on disk untouched and re-raises without clearing the pending buffer"
    - "store_root/workspace/namespace directory computation inlined in each adapter's __init__ (matching kv.py's established precedent), rather than depending on the namespaces.py module plan 01-05 was building concurrently in a sibling worktree this same wave"

key-files:
  created:
    - databasise/stores/graph.py
    - databasise/stores/vector.py
    - databasise/tests/stores/__init__.py
    - databasise/tests/stores/test_graph.py
    - databasise/tests/stores/test_graph_frozen_bugs.py
    - databasise/tests/stores/test_vector.py

key-decisions:
  - "Directory layout computed inline as store_root/workspace/namespace inside each adapter's __init__, identical to plan 01-02's SqliteKVStore precedent, rather than calling a namespace_dir() helper from databasise/namespaces.py — that module is plan 01-05's deliverable, built concurrently in a sibling worktree this same wave, and importing across the wave boundary was out of scope per the parallel-execution lane rules. Functionally equivalent to what namespace_dir() would compute; no cross-lane dependency introduced."
  - "FaissVectorStore's upsert() takes precomputed embeddings from the caller rather than calling an embedding model itself — matches the plan's own <behavior> Test 1 ('upserting documents with precomputed embeddings') and keeps the deferred-embedding buffer analogous to Cozo's deferred-write buffer without pulling an LLM/embedding client into this store adapter."
  - "Vector delete_by_ids() persists immediately via the same two-phase _persist() helper index_done_callback() uses, rather than being deferred through the pending buffer — the plan's <behavior> only specifies buffering for upsert; deletion consistency (index+sidecar staying in sync) is satisfied more simply by an eager commit."
  - "The graph adapter's no-fallback-import test (pycozo unavailable) safely reimports the module in-process; the vector adapter's equivalent test runs in a subprocess instead, because faiss's SWIG wrapper monkeypatches its own C-extension classes at import time — reimporting faiss a second time in the same process corrupted every faiss object already alive (RecursionError), a hazard pycozo does not share."

patterns-established:
  - "Cozo query construction permanently avoids count() aggregation, stores every key as String, consumes Json columns as dict (never by key order), and asserts types on round-trip — bound to the new adapter by a non-skippable regression suite, not merely documented as tribal knowledge."
  - "Faiss adapters commit their binary index and JSON metadata sidecar as one atomic pair via temp-file-write-then-os.replace, so a crash mid-flush can never leave the two files pointing at different snapshots."

requirements-completed: []

coverage:
  - id: T1
    description: "Cozo graph adapter: read-your-writes, canonical edge-key symmetry, abort path, durable commit, Datalog-metacharacter safety, namespace isolation, off-loop dispatch, actionable ImportError"
    requirement: "EMBED-01"
    verification:
      - kind: unit
        ref: "databasise/tests/stores/test_graph.py"
        status: pass
    human_judgment: false
  - id: T2
    description: "Cozo 0.7.6 frozen-bug regression suite bound to the new adapter (#244, #296/#269, #253, #275), non-skippable"
    requirement: "MACH-08"
    verification:
      - kind: unit
        ref: "databasise/tests/stores/test_graph_frozen_bugs.py"
        status: pass
    human_judgment: false
  - id: T3
    description: "Faiss vector adapter: nearest-neighbour ordering, raise-before-mutation on count mismatch, two-phase index+sidecar commit, namespace isolation, empty-index query, deletion consistency, reopen durability, no fallback store"
    requirement: "EMBED-01"
    verification:
      - kind: unit
        ref: "databasise/tests/stores/test_vector.py"
        status: pass
    human_judgment: false

duration: 65min
completed: 2026-08-30
status: complete
---

# Phase 01 Plan 06: Cozo Graph and Faiss Vector Store Adapters Summary

**Cozo (graph) and Faiss (vector) both run embedded, one store per namespace directory, ported by deliberate copy from v1 with their write-buffer discipline, bound-parameter safety, and raise-don't-drop rules carried forward — plus a non-skippable regression suite binding Cozo 0.7.6's four frozen bugs to the new adapter, not just the old one.**

## Performance

- **Duration:** 65 min
- **Tasks:** 3
- **Files modified:** 6 (all new)

## Accomplishments

- Implemented `databasise/stores/graph.py`: `CozoGraphStore`, ported by copy from `v1/lightrag/kg/cozo_impl.py` (`upstream_ref` recorded). Four in-process write buffers (node/edge puts/removes) with read-your-writes-before-flush; `pycozo.Client.run()` dispatched off the event loop via `run_in_executor`; every node id, edge endpoint, and query value passed as a bound parameter; one RocksDB file per namespace directory; module docstring records Cozo 0.7.6 as architecture-frozen and points to `.planning/RECOVERED-FACT-LAYER.md` for the deferred validity-column door.
- Implemented `databasise/tests/stores/test_graph_frozen_bugs.py`: a non-skippable regression suite running directly against `CozoGraphStore`, binding all four Cozo 0.7.6 frozen bugs (#244 aggregation, #296/#269 UUID sort/coercion, #253 JSON key-order, #275 DataValue types) plus a meta-test asserting the module carries no skip/xfail markers.
- Implemented `databasise/stores/vector.py`: `FaissVectorStore`, ported by copy from `v1/lightrag/kg/faiss_impl.py` (`upstream_ref` recorded). `IndexIDMap2(IndexFlatIP)` over L2-normalised vectors for cosine similarity; precomputed-embedding pending buffer; an embedding-count mismatch raises inside `upsert()` before the buffer is touched; index + JSON metadata sidecar committed together via temp-file-write-then-`os.replace`, so a flush failure leaves the previously-committed pair intact; no fallback vector store — a missing `faiss` import raises naming Faiss.
- 23/23 new tests pass (8 graph, 7 frozen-bug regression, 8 vector); full suite is 33/33 including the pre-existing tracer and conftest tests.

## Task Commits

Each task was committed atomically:

1. **Task 1: Cozo graph adapter** — `7e2f053` (feat)
2. **Task 2: Cozo frozen-bug regression suite** — `529aa0f` (test)
3. **Task 3: Faiss vector adapter** — `eadf3e7` (feat)

**Plan metadata:** (this commit) `docs(01-06): complete Cozo graph and Faiss vector adapters plan`

## Files Created/Modified

- `databasise/stores/graph.py` — `CozoGraphStore`, `_cozo_rows`, `_canonical_edge_key`, `_attrs_to_dict` (both helper functions ported by copy from v1)
- `databasise/tests/stores/__init__.py` — empty package marker for `tests/stores/` (shared with plan 01-05, created here since it did not yet exist in this worktree)
- `databasise/tests/stores/test_graph.py` — 8 tests covering all `<behavior>` claims for Task 1
- `databasise/tests/stores/test_graph_frozen_bugs.py` — 7 tests binding the four Cozo 0.7.6 frozen bugs to the new adapter
- `databasise/stores/vector.py` — `FaissVectorStore`, `_PendingVectorDoc`
- `databasise/tests/stores/test_vector.py` — 8 tests covering all `<behavior>` claims for Task 3

## Decisions Made

- **Directory layout computed inline**, not via `namespace_dir()`: plan 01-05 (namespace derivation) was executing concurrently in a sibling worktree this same wave and owns `databasise/namespaces.py`. Both adapters compute `Path(store_root) / workspace / namespace` directly inside `__init__`, matching the precedent plan 01-02's `SqliteKVStore` already established. Functionally identical to what `namespace_dir()` would return; introduces no cross-lane import.
- **`FaissVectorStore.upsert()` takes precomputed embeddings**, never calling an embedding model itself — matches the plan's own `<behavior>` spec ("upserting documents with precomputed embeddings") and keeps this store a pure storage adapter.
- **Vector `delete_by_ids()` commits immediately** via the same two-phase `_persist()` helper the flush path uses, rather than being buffered — simpler than adding a second deferred-delete buffer, and the plan's `<behavior>` only specifies buffering for `upsert`.
- **Two different no-fallback-import test strategies**: the graph test safely reimports `databasise.stores.graph` in-process after monkeypatching `pycozo` out of `sys.modules`. The vector test runs the equivalent check in a subprocess instead — faiss's SWIG wrapper monkeypatches its own C-extension classes at import time, and reimporting `faiss` a second time in the same test process produced a `RecursionError` (every already-live faiss object got corrupted). Discovered by running the test suite, fixed by isolating that one check in a subprocess, matching the pattern `test_tracer_end_to_end.py` already used for its own subprocess-based check.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] `test_bug244_adapter_source_contains_no_count_aggregation` false-positived on its own docstring prose**
- **Found during:** Task 2, first test run
- **Issue:** The module docstring's prose ("never use `count()` aggregation") itself contains the substring `count(`, so a naive `"count(" not in source` check failed against the adapter's own documentation of the mitigation, not against any real query.
- **Fix:** Strip comments and triple-quoted docstrings from the source text with a regex before asserting, leaving the single/double-quoted CozoScript string literals passed to `Client.run()` intact — the assertion now checks real query construction, not prose.
- **Files modified:** `databasise/tests/stores/test_graph_frozen_bugs.py`
- **Verification:** `uv run pytest tests/stores/test_graph_frozen_bugs.py -x` — 7 passed.
- **Committed in:** `529aa0f` (fixed before commit, not a follow-up)

**2. [Rule 1 - Bug] The module docstring's own prose about "no skip/xfail markers" tripped the meta-test checking for exactly that**
- **Found during:** Task 2, same test run
- **Issue:** The docstring explaining the module's non-skippable policy literally contained the strings `pytest.mark.skip` / `pytest.mark.xfail`, and the meta-test's own assertion lines (`assert "mark.skip" not in source`) also matched themselves via `inspect.getsource`.
- **Fix:** Reworded the docstring to avoid the literal substrings ("a pytest skip or xfail marker" instead of naming the marker syntax), and built the meta-test's search strings via string concatenation (`"mark" + "." + "skip"`) so the assertion's own source line does not self-trigger.
- **Files modified:** `databasise/tests/stores/test_graph_frozen_bugs.py`
- **Verification:** `grep -v '^#' tests/stores/test_graph_frozen_bugs.py | grep -cE 'mark\.(skip|xfail)'` returns 0; `uv run pytest tests/stores/test_graph_frozen_bugs.py -x` — 7 passed.
- **Committed in:** `529aa0f` (fixed before commit, not a follow-up)

**3. [Rule 1 - Bug] Vector adapter's no-fallback test corrupted faiss state when run in-process**
- **Found during:** Task 3, test run for `test_delete_by_ids_removes_entries_and_stays_consistent`
- **Issue:** An earlier test in the same file monkeypatched `sys.modules["faiss"]` and reimported `databasise.stores.vector` twice (once to trigger the ImportError, once to restore it) to verify the no-fallback behaviour, mirroring the graph adapter's equivalent pycozo test. faiss's `class_wrappers.py` monkeypatches `__init__` on its own SWIG-wrapped C-extension classes at import time; reimporting it a second time in the same process double-wrapped those classes and produced a `RecursionError` in an unrelated later test (`IndexIDMap2.remove_ids`).
- **Fix:** Moved the no-fallback check into its own test that runs the import-failure scenario in a subprocess (`subprocess.run([sys.executable, "-c", script], ...)`), matching the pattern `databasise/tests/test_tracer_end_to_end.py` already established for its own subprocess-based check. The main test process's `faiss` module is never touched.
- **Files modified:** `databasise/tests/stores/test_vector.py`
- **Verification:** `uv run pytest tests/stores/test_vector.py -x` — 8 passed; full suite `uv run pytest -q` — 33 passed (no regression).
- **Committed in:** `eadf3e7` (fixed before commit, not a follow-up)

---

**Total deviations:** 3 auto-fixed (all Rule 1 — test-construction bugs discovered and fixed during TDD, before any commit). No production-code behavior changed as a result; all three were self-inflicted test-authoring issues caught by running the suite.
**Impact on plan:** All three fixes are scoped entirely to files this plan already owned (the two new test modules). No acceptance criterion, dependency, or architectural decision was changed. No scope creep.

## Issues Encountered

None beyond the three deviations above.

## User Setup Required

None — no external service configuration required. Both `pycozo[embedded]==0.7.6` and `faiss-cpu` were already pinned in `pyproject.toml` by plan 01-01 and installed cleanly via `uv sync`.

## Next Phase Readiness

Both machine-owned graph and vector primitives now exist as real, tested, committed adapters sharing the same lifecycle contract as `stores/kv.py`. `cd databasise && uv run pytest -q` is green (33 tests: 10 pre-existing + 23 new). No blockers.

Note for the orchestrator: this plan's frontmatter lists `requirements: [EMBED-01, MACH-08]`, both of which are also listed by other plans in this phase — per this phase's shared context, neither should be marked complete in `REQUIREMENTS.md` until the last contributing plan lands; the orchestrator closes them at phase end.

Cross-lane note: plan 01-05 (running concurrently this same wave) owns `databasise/namespaces.py`, which does not yet exist in this worktree. This plan's two adapters do not import it — directory layout is computed inline, matching the `stores/kv.py` precedent from plan 01-02 — so there is no merge-order dependency between this plan and 01-05's `namespace_dir()` implementation. A future plan wiring these adapters into the runner may want to switch both to call `namespace_dir()` once 01-05 lands, for a single source of truth on the namespace directory computation; not required for this plan's own correctness.

---
*Phase: 01-machine-core*
*Completed: 2026-08-30*

## Self-Check: PASSED

All 6 claimed files found on disk; commits `7e2f053`, `529aa0f`, and `eadf3e7` confirmed in
`git log --oneline --all`.
