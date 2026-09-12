---
phase: 01-machine-core
plan: 05
subsystem: infra
tags: [sqlite3, fts5, filesystem, namespace-derivation, rfc8785, content-addressing]

# Dependency graph
requires:
  - phase: 01-machine-core
    provides: "01-02's databasise.stores.base.StorageNameSpace lifecycle ABC and the tracer's SqliteKVStore (namespace, workspace, store_root) shape"
provides:
  - "databasise.namespaces — derive_namespace() (RIG §RUN.1, D-07), namespace_dir() (escape-proof path derivation), artifacts_overlap() (RIG §RUN.2 iff), gc_namespace()"
  - "databasise.stores.kv.SqliteKVStore — completed with PRAGMA journal_mode=WAL / synchronous=NORMAL"
  - "databasise.stores.lexical.SqliteLexicalStore — new FTS5 full-text primitive, same lifecycle ABC as kv.py"
  - "databasise.stores.blob.FilesystemBlobStore — new content-addressed filesystem primitive, git-style two-level fan-out"
affects: ["01-06", "01-07"]

actuals:
  tokens: 8845
  tasks: 3
  commits: 6

tech-stack:
  added: []
  patterns:
    - "namespace_dir()'s bare hex/hyphen token validation (regex allow-list, not a deny-list of '..'/'/'): rejects anything outside [A-Za-z0-9-] so a derived value can never escape store_root"
    - "FTS5 literal-phrase quoting (wrap term in double quotes, double any embedded quote) so an FTS5-operator-bearing query term is bound as a parameter AND searched literally"
    - "Delegating connection wrapper for whitebox failure-injection tests (sqlite3.Connection's C-level type won't accept monkeypatched attributes on CPython — a thin Python wrapper object substituted for store._conn is the only way to simulate a mid-flush failure)"
    - "put()'s temp-file-in-same-directory + os.replace() for atomic content-addressed writes — a partially-written blob is never observable at its final path"

key-files:
  created:
    - databasise/namespaces.py
    - databasise/stores/lexical.py
    - databasise/stores/blob.py
    - databasise/tests/stores/__init__.py
    - databasise/tests/stores/test_namespace_derivation.py
    - databasise/tests/stores/test_kv.py
    - databasise/tests/stores/test_lexical.py
    - databasise/tests/stores/test_blob.py
  modified:
    - databasise/stores/kv.py

key-decisions:
  - "namespace_dir() takes only (store_root, namespace) — kv.py/lexical.py/blob.py retain the tracer's existing (namespace, workspace, store_root) constructor shape rather than being rewired to call namespace_dir() internally. Rationale: the tracer test (01-02) directly instantiates SqliteKVStore with that three-argument constructor and must keep passing; namespaces.py is a standalone RIG §RUN.1 utility for the runner's real namespace-derivation flow (a later plan's wiring), not a mandate to change every existing store constructor in this plan. The store_root/workspace/namespace directory scheme already satisfies D-07's one-directory-per-namespace and per-store isolation properties (verified by test 7/8 in each store's test suite); it is a different, simpler namespace-not-table addressing scheme than the RIG-derived scope-hex tokens namespace_dir() validates, and both coexist without conflict."
  - "Lexical store domain API is upsert(data: dict[id, {'content': str}]) / query(term) / delete(ids), not BaseKVStorage's six methods — task 2 only asked for the identical *lifecycle* ABC (5 async methods) to be shared with kv.py, not the KV CRUD method names, since lexical is a new primitive with its own natural full-text-search shape."
  - "Lexical query() only searches the flushed FTS5 index (no read-your-writes-before-flush for buffered-but-unflushed documents) — the plan's <behavior> tests for lexical test flush/abort lifecycle parity with kv.py, not pre-flush query visibility; kv.py's read-your-writes applies to its own get_by_id, a narrower claim than 'the lexical store searches unflushed content'."
  - "blob.py's CRUD methods (put/get/read_range/delete) are plain synchronous methods, not async — matching the plan's own <action> signatures verbatim (no `async def` in any of them), while the two lifecycle methods it overrides (index_done_callback, drop) stay async to satisfy StorageNameSpace's abstract async contract."

patterns-established:
  - "Whitebox mid-flush failure injection via a delegating wrapper class swapped onto store._conn, used identically in test_kv.py (poison the Nth INSERT) and test_lexical.py (poison any FTS5-referencing SQL) — the pattern any future store test needing to simulate a partial-write failure should reuse, since sqlite3.Connection's methods cannot be monkeypatched directly on CPython (both instance-attribute and class-attribute assignment raise: 'attribute is read-only' / 'immutable type')."

requirements-completed: []

coverage:
  - id: D1
    description: "Two arms whose recipe fields are hash-identical derive the same namespace (RIG §RUN.2 identical-means-shared case); any single differing field derives a different namespace"
    requirement: "MACH-08"
    verification:
      - kind: unit
        ref: "databasise/tests/stores/test_namespace_derivation.py#test_1_hash_identical_recipes_derive_the_same_namespace"
        status: pass
      - kind: unit
        ref: "databasise/tests/stores/test_namespace_derivation.py#test_2_any_single_differing_recipe_field_derives_a_different_namespace"
        status: pass
    human_judgment: false
  - id: D2
    description: "A shared namespace and a quarantined namespace derived from otherwise-identical inputs are different namespaces and resolve to different directories"
    requirement: "MACH-08"
    verification:
      - kind: unit
        ref: "databasise/tests/stores/test_namespace_derivation.py#test_5_shared_and_quarantined_scopes_from_identical_inputs_differ"
        status: pass
    human_judgment: false
  - id: D3
    description: "namespace_dir() raises rather than returning a path outside store_root when handed a namespace containing a separator or parent reference; gc_namespace() removes exactly one namespace's directory and leaves siblings intact"
    requirement: "MACH-08"
    verification:
      - kind: unit
        ref: "databasise/tests/stores/test_namespace_derivation.py#test_6_namespace_dir_stays_inside_store_root_and_refuses_escape_attempts"
        status: pass
      - kind: unit
        ref: "databasise/tests/stores/test_namespace_derivation.py#test_8_gc_namespace_removes_exactly_that_namespace_dir_and_leaves_siblings_intact"
        status: pass
    human_judgment: false
  - id: D4
    description: "SqliteKVStore: read-your-writes before flush, abort discards buffered writes, commit is durable across reopen, a mid-flush failure raises and leaves the pending buffer intact, two namespace-scoped stores are isolated"
    requirement: "EMBED-01"
    verification:
      - kind: unit
        ref: "databasise/tests/stores/test_kv.py (7 tests)"
        status: pass
    human_judgment: false
  - id: D5
    description: "SqliteLexicalStore: FTS5 search returns exactly the matching documents ranked; an FTS5-operator-bearing term is searched literally; empty query returns []; lifecycle mirrors kv.py; no silent LIKE-scan fallback when FTS5 is unavailable"
    requirement: "EMBED-01"
    verification:
      - kind: unit
        ref: "databasise/tests/stores/test_lexical.py (6 tests)"
        status: pass
    human_judgment: false
  - id: D6
    description: "FilesystemBlobStore: content-addressed put/get round-trip, identical-content dedup, git-style two-level fan-out path derivable from digest alone, missing-digest error, zero-length blob, delete isolation, range reads (with past-end refusal), cross-namespace isolation"
    requirement: "EMBED-01"
    verification:
      - kind: unit
        ref: "databasise/tests/stores/test_blob.py (8 tests)"
        status: pass
    human_judgment: false

duration: 55min
completed: 2026-08-30
status: complete
---

# Phase 01 Plan 05: Store Primitives (KV completion, Lexical, Blob) and Namespace Derivation Summary

**Three embedded, namespace-isolated store primitives (SQLite KV completed with WAL pragmas, a new FTS5 lexical store, and a new content-addressed filesystem blob store) plus RIG §RUN.1's namespace-derivation module — all sharing one commit/abort lifecycle and zero new runtime dependencies.**

## Performance

- **Duration:** 55 min
- **Tasks:** 3
- **Files modified:** 9 (8 new, 1 modified)
- **Tests added:** 30 (9 namespace + 7 kv + 6 lexical + 8 blob)

## Accomplishments

- Implemented `databasise/namespaces.py`: `derive_namespace()` (SHA-256/RFC 8785 over RIG §RUN.1's seven named members plus `scope`), `namespace_dir()` (escape-proof `store_root / namespace` with a bare hex/hyphen token allow-list), `artifacts_overlap()` (RIG §RUN.2's iff on index-recipe hash equality), and `gc_namespace()` (deletes exactly one namespace's directory tree)
- Completed `databasise/stores/kv.py`: added `PRAGMA journal_mode=WAL` and `PRAGMA synchronous=NORMAL` at connect time, documented why (concurrent readers must not block on the flush transaction inside a single process tree — the only concurrency shape EMBED-01 admits). The buffer/commit/abort discipline, all six `BaseKVStorage` method signatures, and the five lifecycle methods were already complete from plan 01-02's tracer.
- Implemented `databasise/stores/lexical.py`: `SqliteLexicalStore`, a new FTS5-backed full-text primitive sharing `kv.py`'s lifecycle ABC and buffer/commit/abort discipline. Query terms are always bound as parameters and wrapped in FTS5 double-quote phrase syntax so an operator-bearing term (`AND`, `OR`, `NOT`, `NEAR`, `*`, `^`, `:`, parentheses) is matched literally. FTS5 availability is verified at construction — `Fts5UnavailableError` names FTS5 explicitly rather than silently falling back to a `LIKE` scan.
- Implemented `databasise/stores/blob.py`: `FilesystemBlobStore`, a new content-addressed filesystem primitive with git-object-store-style two-level hex fan-out (`blobs/ab/cd/<64-hex-digest>`). `put()` writes via a same-directory temp file plus `os.replace()` so a partial write is never observable; identical content already stored is a no-op; `read_range()` raises rather than silently truncating past the blob's length.
- 40/40 tests pass (`cd databasise && uv run pytest -q`), including all 7 of plan 01-02's pre-existing tracer tests — the proven end-to-end slice still runs unmodified.
- Zero new runtime dependencies: all three stores use only stdlib `sqlite3` (with FTS5) and the filesystem.

## Task Commits

Each task was committed as a TDD RED/GREEN pair:

1. **Task 1 (RED): Namespace derivation tests** — `29ec11e` (test)
2. **Task 1 (GREEN): Namespace derivation implementation** — `6807a8b` (feat)
3. **Task 2 (RED): KV completion + lexical store tests** — `29617ac` (test)
4. **Task 2 (GREEN): KV WAL pragmas + lexical store implementation** — `31ebcf6` (feat)
5. **Task 3 (RED): Blob store tests** — `b9c0962` (test)
6. **Task 3 (GREEN): Blob store implementation** — `fb1ab21` (feat)

**Plan metadata:** (this commit) `docs(01-05): complete store primitives and namespace derivation plan`

## Files Created/Modified

- `databasise/namespaces.py` — `derive_namespace()`, `namespace_dir()`, `artifacts_overlap()`, `gc_namespace()`
- `databasise/stores/kv.py` (modified) — `PRAGMA journal_mode=WAL` / `synchronous=NORMAL` added at connect, docstring updated
- `databasise/stores/lexical.py` — `SqliteLexicalStore`, `Fts5UnavailableError`, `_quote_literal()`
- `databasise/stores/blob.py` — `FilesystemBlobStore`, `BlobNotFoundError`
- `databasise/tests/stores/__init__.py` — empty package marker
- `databasise/tests/stores/test_namespace_derivation.py` — 9 tests
- `databasise/tests/stores/test_kv.py` — 7 tests
- `databasise/tests/stores/test_lexical.py` — 6 tests
- `databasise/tests/stores/test_blob.py` — 8 tests

## Decisions Made

- **`namespace_dir()` is not wired into `kv.py`/`lexical.py`/`blob.py`'s constructors.** The tracer test (01-02) directly instantiates `SqliteKVStore(namespace=..., workspace=..., store_root=...)`; rewiring the constructor to call `namespace_dir()` internally (which takes only `(store_root, namespace)`, no `workspace`) would have required either breaking that call signature or silently dropping `workspace` from the directory computation. Kept the existing `store_root/workspace/namespace` scheme — it already gives every namespace/workspace pair its own directory (D-07's core property, verified by each store's cross-namespace-isolation test) — and `lexical.py`/`blob.py` mirror the same three-argument shape for consistency across all three adapters. `namespaces.py`'s `derive_namespace()`/`namespace_dir()` remain available as the standalone RIG §RUN.1 utility a later plan's runner wiring will call to produce the real namespace token handed to these constructors.
- **Lexical store's domain API is `upsert`/`query`/`delete`, not `BaseKVStorage`'s six methods.** Task 2's instruction was to share the identical *lifecycle* ABC (the five async `StorageNameSpace` methods) with `kv.py`, not its CRUD method names — lexical is a new primitive with no KV precedent, so it gets a full-text-search-shaped API instead.
- **Blob store's CRUD methods are synchronous, not async** — matches the plan's own `<action>` signatures verbatim (`put(content: bytes) -> str`, none declared `async def`). Its two overridden lifecycle methods (`index_done_callback`, `drop`) stay `async` since `StorageNameSpace` declares them as async abstract methods.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] `sqlite3.Connection`'s methods cannot be monkeypatched directly on CPython**
- **Found during:** Task 2, writing the mid-flush-failure test for `kv.py` and the FTS5-unavailable test for `lexical.py`
- **Issue:** `monkeypatch.setattr(sqlite3.Connection, "execute", ...)` raises `TypeError: cannot set 'execute' attribute of immutable type 'sqlite3.Connection'`; assigning directly on an instance (`conn.execute = ...`) raises `AttributeError: attribute 'execute' is read-only`. Both are C-level restrictions on this Python build, not a bug in the store code.
- **Fix:** Introduced a thin Python delegating-wrapper class in each test file (`_FailNthInsertConnection` in `test_kv.py`, `_NoFts5Connection` in `test_lexical.py`) that wraps a real connection and intercepts specific SQL statements, then substituted it for `store._conn` (kv) or patched `sqlite3.connect` itself (lexical, since the failure must occur during `SqliteLexicalStore.__init__`, before any store instance exists to swap `_conn` on).
- **Files modified:** `databasise/tests/stores/test_kv.py`, `databasise/tests/stores/test_lexical.py`
- **Verification:** both targeted tests pass; full suite (`uv run pytest -q`) green at 40/40.
- **Committed in:** `29617ac` (test commit — fixed before commit, not a follow-up)

**2. [Rule 1 - Bug] ruff import-sort ordering on all four new test files**
- **Found during:** each task's post-implementation lint pass
- **Issue:** `uv run ruff check` flagged `I001` (import block un-sorted) and one `C408` (unnecessary `dict()` call, rewrite as a literal) in `test_namespace_derivation.py`.
- **Fix:** `ruff check --fix` for the `I001` auto-fixes; manually rewrote `_BASE_KWARGS` from `dict(...)` to a `{...}` literal for the `C408` finding (the merge-with-overrides call sites, `dict(_BASE_KWARGS, field=value)`, are unaffected — only the base definition changed).
- **Files modified:** `databasise/tests/stores/test_namespace_derivation.py`, `databasise/tests/stores/test_kv.py`, `databasise/tests/stores/test_lexical.py`, `databasise/tests/stores/test_blob.py`
- **Verification:** `uv run ruff check <this plan's files>` — all checks passed.
- **Committed in:** the corresponding task's RED commit for each file.

---

**Total deviations:** 2 auto-fixed (1 blocking test-infrastructure workaround, 1 lint cleanup). Neither changed any acceptance criterion, dependency, or architectural decision. No scope creep.

## Issues Encountered

None beyond the two deviations above.

## User Setup Required

None — no external service configuration required.

## Next Phase Readiness

All three store primitives (`kv`, `lexical`, `blob`) and the namespace-derivation module are in place, tested, and isolated from plan 01-06's `graph.py`/`vector.py` (neither file touched) and from `stores/base.py` (unmodified). `cd databasise && uv run pytest -q` is green (40 tests), including all 7 pre-existing tracer tests from plan 01-02. No blockers.

Note for the orchestrator: this plan's frontmatter lists `requirements: [EMBED-01, MACH-08]`, both of which are also listed by other plans in this phase — per this phase's shared context, neither should be marked complete in `REQUIREMENTS.md` until its last contributing plan lands; the orchestrator closes them at phase end.

---
*Phase: 01-machine-core*
*Completed: 2026-08-30*

## Self-Check: PASSED

All 9 claimed files found on disk; commits `29ec11e`, `6807a8b`, `29617ac`, `31ebcf6`, `b9c0962`, `fb1ab21` confirmed in `git log --oneline`.
