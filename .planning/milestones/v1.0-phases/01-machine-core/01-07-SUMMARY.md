---
phase: 01-machine-core
plan: 07
subsystem: registry+ledger
tags: [sqlite3, artifact-registry, blast-radius, d-02, append-only-ledger, contract-section-7]

# Dependency graph
requires:
  - phase: 01-machine-core
    provides: "01-05's databasise.stores.blob.FilesystemBlobStore (content-addressed blob store this registry indexes over) and databasise.namespaces.artifacts_overlap (RIG §RUN.2's iff)"
  - phase: 01-machine-core
    provides: "01-04's parts.schema.Part/ArtifactScope and 01-03's validator.blast_radius.blast_radius_violations (the load-time predicate this plan's write path reuses without modification)"
provides:
  - "databasise.registry_artifact.index.ArtifactRegistry — SQLite artifact registry: register()/discover()/overlaps()/delete(), three-scope CHECK constraint, scope-filtered discover() with no disable parameter, REGISTER_AUTHORIZATION gate"
  - "databasise.registry_artifact.write_path.write_artifact() — D-02's second blast-radius call site, delegating to validator.blast_radius.blast_radius_violations via an adapter ParsedWiring rather than restating the predicate"
  - "databasise.ledger.ledger.Ledger — append-only SQLite promotion ledger with database-level UPDATE/DELETE triggers and a derived active_pointer()"
affects: []

actuals:
  tokens: 12654
  tasks: 3
  commits: 6

tech-stack:
  added: []
  patterns:
    - "REGISTER_AUTHORIZATION sentinel gate: register() requires a caller to import and pass a module-level sentinel object explicitly. Not real Python privacy (any caller can import it), but it makes bypassing D-02's second call site a deliberate, grep-able act rather than an accidental plain method call — the property D-02's 'no path can bypass by accident' actually needs, achievable without editing validator/** (off-limits this wave) or breaking Task 1's own tests calling register() directly."
    - "Adapter-ParsedWiring reuse: write_path.py constructs a minimal single-node ParsedWiring/WiringNode/Part in-memory and calls the existing validator.blast_radius.blast_radius_violations() directly, rather than re-deriving the shared/stage condition — guarantees the load-time and write-path refusals can never drift, since they run literally the same function, without modifying the off-limits validator/** module."
    - "Idempotent register() on the UNIQUE(content_hash, namespace, scope) key: a second registration of hash-identical inputs returns the existing row rather than raising or creating a coincidentally-equal duplicate — mirrors blob.py's own content-addressed put() no-op semantics and matches RIG §RUN.2's 'identical means shared' case."
    - "SQLite BEFORE UPDATE/BEFORE DELETE triggers with RAISE(ABORT, ...) enforce ledger append-only at the database level, catching any caller through any connection — not just the absence of Python update/delete methods."

key-files:
  created:
    - databasise/registry_artifact/__init__.py
    - databasise/registry_artifact/index.py
    - databasise/registry_artifact/write_path.py
    - databasise/tests/registry_artifact/__init__.py
    - databasise/tests/registry_artifact/test_index.py
    - databasise/tests/registry_artifact/test_write_path_blast_radius.py
    - databasise/ledger/__init__.py
    - databasise/ledger/ledger.py
    - databasise/tests/ledger/__init__.py
    - databasise/tests/ledger/test_ledger.py
  modified:
    - databasise/pyproject.toml

key-decisions:
  - "REGISTER_AUTHORIZATION sentinel designed into index.py during Task 1 (not deferred to Task 2), even though the plan's own <action> text frames the write-path-only gate as Task 2's job. Task 2's <files> list only includes write_path.py, not index.py, and Task 1's own tests need register() to succeed when called directly — the only way to satisfy both constraints is for the gate to exist in index.py from the start, with Task 1's tests importing the sentinel explicitly (exactly as write_path.py does), and Task 2's test proving the refusal fires for a caller that omits it."
  - "write_path.py's blast-radius check reuses validator.blast_radius.blast_radius_violations() by constructing an adapter ParsedWiring (one synthetic node/Part) rather than the plan's suggested 'import the underlying predicate' — that module exposes only the whole-wiring function, not a standalone single-node predicate, and validator/** is off-limits this wave (owned and stable since Wave 3). The adapter calls the exact same function both call sites use, so drift is structurally impossible without touching the frozen module."
  - "ArtifactRegistry.discover()'s scope filter is applied in Python after an indexed SQL fetch (WHERE clauses over the whitelisted filter columns), rather than compiled into the SQL scope predicate itself — simpler and equally correct at Phase 1's scale, and the acceptance criterion (no parameter that disables the filter, verified by inspect.signature) is about the function's public interface, not its internal implementation strategy."
  - "test_10's 'space_id is a valid, queryable state that does not collapse two corpora into one row' is tested via two distinct namespaces/content hashes with space_id=None, then filtering discover() by corpus_id — not via two rows sharing one (content_hash, namespace, scope) key, since that key IS this registry's uniqueness boundary and colliding it deliberately would just exercise idempotent register(), not the None-handling claim the test is actually about."

patterns-established:
  - "Off-limits-module reuse via synthetic adapter objects: when a plan needs to call a function in a module outside its edit lane, without modifying that module, construct the minimal in-memory object graph the function's own type signature requires (here: ParsedWiring/WiringNode/Part) rather than duplicating its internal logic. Keeps single-source-of-truth guarantees (Task 2's Test 8) even across a wave's file-ownership boundary."

requirements-completed: []

coverage:
  - id: D1
    description: "Artifact registry stores every CONTRACT §7 field, enforces the three-scope and three-tier CHECK constraints at the schema level, and register() is idempotent on hash-identical inputs (RIG §RUN.2)"
    requirement: "MACH-06"
    verification:
      - kind: unit
        ref: "databasise/tests/registry_artifact/test_index.py (13 tests)"
        status: pass
    human_judgment: false
  - id: D2
    description: "discover() applies the scope filter itself with no disable parameter: shared visible to any caller, quarantined only under an explicit Pin, self_storage only to its own producing instance; every result carries scope/SA-2 stamps/space_id/producer/retention_tier/pin_required"
    requirement: "MACH-06"
    verification:
      - kind: unit
        ref: "databasise/tests/registry_artifact/test_index.py::test_3_.. through test_6_.. and test_13_.."
        status: pass
    human_judgment: false
  - id: D3
    description: "The blast-radius rule (CONTRACT §3) is enforced a second time at the artifact-write path, using the identical predicate the load-time check uses, with no route to register() that bypasses it and no depth-absent-defaults-to-stage loophole"
    requirement: "MACH-08"
    verification:
      - kind: unit
        ref: "databasise/tests/registry_artifact/test_write_path_blast_radius.py (8 tests)"
        status: pass
    human_judgment: false
  - id: D4
    description: "The ledger is append-only (database-level triggers, not just absent Python methods), carries every CONTRACT §7 ledger field, and active_pointer() is a derived query with no active-flag column; running a wiring never appends"
    requirement: "MACH-06"
    verification:
      - kind: unit
        ref: "databasise/tests/ledger/test_ledger.py (8 tests)"
        status: pass
    human_judgment: false

duration: 25min
completed: 2026-08-30
status: complete
---

# Phase 01 Plan 07: Artifact Registry, Blast-Radius Write Path, Append-Only Ledger Summary

**A SQLite artifact registry enforcing CONTRACT §7's full field set and three-scope CHECK constraint with a self-applying discovery filter, a second D-02 blast-radius call site that reuses the load-time predicate via an in-memory adapter (no drift possible), and an append-only promotion ledger with database-level UPDATE/DELETE triggers and a query-derived active pointer.**

## Performance

- **Duration:** 25 min
- **Tasks:** 3
- **Files modified:** 11 (10 new, 1 modified)
- **Tests added:** 29 (13 registry + 8 write-path + 8 ledger)

## Accomplishments

- **Task 1 — `databasise/registry_artifact/index.py`:** `ArtifactRegistry` over stdlib `sqlite3`, its own `artifact_registry.db` at the store root. The `artifacts` table carries every CONTRACT §7 field (`content_hash`, `namespace`, `scope`, three SA-2 stamps, `corpus_id`, `space_id`, `producer_instance_hash`, `recipe_hash`, `retention_tier`, `created_at`) with a CHECK constraint keeping the three scopes and three retention tiers exact, a UNIQUE index over `(content_hash, namespace, scope)` making `register()` idempotent on hash-identical inputs, and an index on `recipe_hash` for `overlaps()`. `discover()` applies the §16.1 scope filter itself — `shared` visible to any caller, `quarantined` only under an explicit `Pin`, `self_storage` only to its own producing instance — with no parameter to disable it. `register()` refuses a transient store effect naming §7, and is gated behind the `REGISTER_AUTHORIZATION` sentinel (D-02's second call site).
- **Task 2 — `databasise/registry_artifact/write_path.py`:** `write_artifact()` checks the blast-radius rule *before* touching the blob store (so a refusal leaves no orphan content), by delegating to `validator.blast_radius.blast_radius_violations()` through a minimal synthetic `ParsedWiring` — the exact function the load-time check uses, called directly rather than re-derived, so the two call sites cannot drift. A shared write succeeds only at effective depth `stage`; `quarantined`/`self_storage` writes succeed at any depth including `opaque`; a missing (`None`) effective depth is refused, never defaulted to `stage`. On success, content is put into the blob store first, then registered via `REGISTER_AUTHORIZATION` — the only sanctioned route to `register()`.
- **Task 3 — `databasise/ledger/ledger.py`:** `Ledger` over stdlib `sqlite3`, its own `ledger.db` beside the artifact registry. The `ledger` table carries every CONTRACT §7 ledger field this phase implements (mutation id/class/parent/arm instance hashes/effect size/verdict/evidence pointer/proposer id/depth label/tier-of-decision/decomposition ratio/opaque TTL renewals/parity records/`promotion_provenance`/`promotion_trace_ids`), with list-valued fields stored as JSON. Append-only is enforced by `BEFORE UPDATE`/`BEFORE DELETE` triggers that `RAISE(ABORT, ...)` at the database level. `active_pointer()` is a derived `SELECT ... ORDER BY id DESC LIMIT 1` — no active-flag column exists. Nothing in the runner calls `append()`; running a wiring through `databasise.run_wiring` leaves the ledger untouched (verified directly against the row count).
- 159/159 tests pass (`cd databasise && uv run pytest -q`), including all 130 pre-existing tests from Waves 1-3.
- Added `databasise.registry_artifact` and `databasise.ledger` to `pyproject.toml`'s setuptools `packages` list (the only change to that file).
- Zero new runtime dependencies — both modules use only stdlib `sqlite3`.
- `databasise/runner/**`, `databasise/stores/**`, `databasise/validator/**`, `databasise/identity/**`, `databasise/parts/**` were read but never modified, per this wave's parallel-execution lane boundaries.

## Task Commits

Each task was committed as a TDD RED/GREEN pair:

1. **Task 1 (RED): Artifact registry index tests** — `5a7353c` (test)
2. **Task 1 (GREEN): Artifact registry index implementation** — `582a5e2` (feat)
3. **Task 2 (RED): Write-path blast-radius guard tests** — `8eb4de3` (test)
4. **Task 2 (GREEN): Write-path blast-radius guard implementation** — `40f3af3` (feat)
5. **Task 3 (RED): Append-only ledger tests** — `fa57ce2` (test)
6. **Task 3 (GREEN): Append-only ledger implementation** — `4aa1239` (feat)

**Plan metadata:** (this commit) `docs(01-07): complete artifact registry, blast-radius write path, ledger plan`

## Files Created/Modified

- `databasise/registry_artifact/index.py` — `ArtifactRegistry`, `ArtifactRecord`, `DiscoveryResult`, `Pin`, `REGISTER_AUTHORIZATION`, `TransientWriteNotRegistrableError`, `UnauthorizedRegisterCallError`
- `databasise/registry_artifact/write_path.py` — `write_artifact()`, `BlastRadiusRefusal`
- `databasise/ledger/ledger.py` — `Ledger`, `LedgerRecord`
- `databasise/pyproject.toml` (modified) — added `databasise.registry_artifact` and `databasise.ledger` to the setuptools `packages` list
- `databasise/tests/registry_artifact/test_index.py` — 13 tests (10 numbered `<behavior>` + 3 acceptance-criteria-only)
- `databasise/tests/registry_artifact/test_write_path_blast_radius.py` — 8 tests
- `databasise/tests/ledger/test_ledger.py` — 8 tests

## Decisions Made

- **`REGISTER_AUTHORIZATION` sentinel built into Task 1, not deferred to Task 2** — see key-decisions above; resolves the apparent conflict between Task 1's own tests needing direct `register()` access and Task 2's requirement that an unauthorized direct call be refused.
- **Blast-radius predicate reuse via a synthetic adapter `ParsedWiring`** rather than the plan's literal "import the underlying predicate" phrasing — `validator/blast_radius.py` exposes only the whole-wiring `blast_radius_violations()` function and is off-limits to edit this wave; the adapter calls that exact function, so the two call sites are provably identical without touching the frozen module.
- **`discover()`'s scope filter runs in Python over an indexed SQL fetch**, not compiled into the SQL predicate itself — equally correct at Phase 1's scale and satisfies the "no disable parameter" acceptance criterion, which is about the public signature.
- **test_10 exercises `space_id=None` via two distinct rows** (different namespaces/content) rather than colliding the UNIQUE key — the UNIQUE(content_hash, namespace, scope) triple is the registry's actual identity boundary, so deliberately colliding it would test idempotent `register()`, not the "space_id=None doesn't collapse corpora" claim.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] `blast_radius.py` has no standalone single-node predicate to import**
- **Found during:** Task 2, designing `write_path.py`'s blast-radius check
- **Issue:** The plan's `<action>` text says to "import `blast_radius_violations`'s underlying predicate ... rather than restating the condition here" — but `validator/blast_radius.py` exposes only `blast_radius_violations(parsed, depth_map)`, which operates over a whole `ParsedWiring`, not a per-write predicate. `validator/**` is off-limits this wave (Wave 3's stable, already-landed module), so it could not be refactored to expose one.
- **Fix:** Constructed a minimal synthetic `ParsedWiring`/`WiringNode`/`Part` in `write_path.py` representing exactly the one write under check, and called `blast_radius_violations()` directly against it. This literally reuses the same function both call sites run — the drift-proof property the plan asked for — without modifying the frozen module.
- **Files modified:** `databasise/registry_artifact/write_path.py`
- **Verification:** `tests/registry_artifact/test_write_path_blast_radius.py::test_8_load_time_and_write_path_refusals_carry_the_same_violation_code` — asserts both call sites produce `CODE_BLAST_RADIUS_REFUSAL` for the identical situation; full suite green.
- **Committed in:** `40f3af3`

**2. [Rule 1 - Bug] ruff import-sort and lint findings across all three new test files**
- **Found during:** each task's post-implementation lint pass
- **Issue:** `uv run ruff check` flagged `I001` (unsorted imports) in all three new test files, `C408` (rewrite `dict()` call as a literal) and `B017` (blind `except Exception`, narrowed to `pytest.raises(Exception)`) in `test_index.py`, and `UP035`/`UP017` (import from `collections.abc`, use `datetime.UTC`) in `index.py`.
- **Fix:** `ruff check --fix` for the auto-fixable import-sort findings; manually rewrote the `dict()` call as a `{...}` literal, narrowed the blind `Exception` assertion to `sqlite3.IntegrityError`, and updated `index.py`'s imports (`collections.abc.Sequence`, `datetime.UTC`).
- **Files modified:** `databasise/registry_artifact/index.py`, `databasise/tests/registry_artifact/test_index.py`, `databasise/tests/registry_artifact/test_write_path_blast_radius.py`, `databasise/tests/ledger/test_ledger.py`
- **Verification:** `uv run ruff check` on every file this plan touched — all checks passed; full suite still green.
- **Committed in:** each finding's own task GREEN commit.

---

**Total deviations:** 2 auto-fixed (1 blocking design accommodation for the off-limits-module reuse rule, 1 lint cleanup). Neither changed any acceptance criterion or introduced scope creep; the write-path guarantee (same predicate, same code, no drift) is actually stronger under the adapter approach than a hand-restated condition would have been.

## Known Stubs

None — every artifact this plan's `<artifacts_this_phase_produces>` lists (`ArtifactRegistry`, `ArtifactRecord`, `DiscoveryResult`, `Ledger`, `LedgerRecord`, `BlastRadiusRefusal`, and the `register`/`discover`/`overlaps`/`delete`/`write_artifact`/`append`/`active_pointer`/`history` functions) is fully implemented and tested, not a placeholder.

## Issues Encountered

None beyond the two deviations documented above.

## User Setup Required

None — no external service configuration required; zero new runtime dependencies.

## Next Phase Readiness

The artifact registry, its second blast-radius call site, and the append-only ledger are all in place and tested, closing D-02's bypass concern and giving Phase 2's A/A calibration and trace records a ledger table to land in. `cd databasise && uv run pytest -q` is green (159 tests), including all 130 pre-existing tests. `databasise/runner/**` (plan 01-08's lane this wave) was never touched. No blockers.

Note for the orchestrator: this plan's frontmatter lists `requirements: [MACH-06, MACH-08]`, both of which are also listed by other plans in this phase — per this phase's shared context, do not mark either complete in `REQUIREMENTS.md` until its last contributing plan lands; the orchestrator closes them at phase end. `requirements-completed` above is left empty for the same reason.

---
*Phase: 01-machine-core*
*Completed: 2026-08-30*

## Self-Check: PASSED

All 11 claimed files found on disk (10 new + 1 modified); commits `5a7353c`, `582a5e2`, `8eb4de3`, `40f3af3`, `fa57ce2`, `4aa1239` confirmed in `git log --oneline`.
