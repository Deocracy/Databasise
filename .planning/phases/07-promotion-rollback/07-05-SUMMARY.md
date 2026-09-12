---
phase: 07-promotion-rollback
plan: 05
subsystem: database
tags: [sqlite, concurrency, transactions, ledger, promotion, gap-closure]

# Dependency graph
requires:
  - phase: 07-promotion-rollback
    provides: "07-01/07-02's append-only Ledger and promote/rollback/retire verbs; 07-04's UnrecognisedPromotionVerbError guard"
provides:
  - "Ledger.transaction() — a BEGIN IMMEDIATE span enclosing each operator verb's guard read through its append()"
  - "UNIQUE(alias, minted_version) schema-level backstop (ux_ledger_generation) refusing a duplicate published name independent of any Python read path"
  - "Committed regression coverage for both races: tests/seam/test_operator_verb_concurrency.py, tests/ledger/test_ledger_generation_uniqueness.py"
affects: [promotion-rollback, ledger, seam-engine]

# Actuals (#2632)
actuals:
  tokens: 11500
  tasks: 3
  commits: 3

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Ledger.transaction(): sqlite3 BEGIN IMMEDIATE + try/except/else commit/rollback context manager, widening a caller's guard-read-then-append into one atomic span"
    - "DROP INDEX + CREATE UNIQUE INDEX under a new name, never CREATE UNIQUE INDEX IF NOT EXISTS over an existing plain index of the same name (verified silent no-op in SQLite)"
    - "Deliberately unwrapped sqlite3.IntegrityError as a machine-invariant backstop, unreachable through the seam once transaction() is in place — mirrors the existing unreachable-by-construction UnrecognisedPromotionVerbError backstop pattern"

key-files:
  created:
    - databasise/tests/seam/test_operator_verb_concurrency.py
    - databasise/tests/ledger/test_ledger_generation_uniqueness.py
  modified:
    - databasise/ledger/ledger.py
    - databasise/seam/engine.py
    - databasise/evidence/PROMOTION-LEDGER-EVIDENCE.md
    - .planning/phases/07-promotion-rollback/COVERAGE.md

key-decisions:
  - "SQLite BEGIN IMMEDIATE transaction over the WR-01-proposed asyncio.Lock — serializes at the file, covering multiple Databasise instances, processes, or REST workers sharing one store_root, not only callers on one event loop"
  - "DROP INDEX by name then CREATE UNIQUE INDEX under a new name (ux_ledger_generation) rather than reusing ix_ledger_generation — verified that CREATE UNIQUE INDEX IF NOT EXISTS over an existing same-named plain index is a silent no-op"
  - "The UNIQUE index's sqlite3.IntegrityError stays unwrapped (no new SeamRefusalError) — with transaction() in place it is unreachable through the seam under normal operation, so wrapping it would add new §18 surface for a path no consumer can reach"

requirements-completed: [MACH-07, API-09]

coverage:
  - id: D1
    description: "retire()/rollback() racing on the same generation: no rollback row ever commits after a tombstone naming the same generation; every outcome is a PromotionResult or the already-shipped TombstonedGenerationError, never a bare sqlite3 exception"
    requirement: "MACH-07"
    verification:
      - kind: integration
        ref: "tests/seam/test_operator_verb_concurrency.py::test_retire_vs_rollback_race_never_lets_a_rollback_outrun_a_tombstone"
        status: pass
    human_judgment: false
  - id: D2
    description: "Six concurrent promote() calls on one alias mint six distinct semvers and all six succeed — pure serialization, zero exceptions"
    requirement: "MACH-07"
    verification:
      - kind: integration
        ref: "tests/seam/test_operator_verb_concurrency.py::test_six_concurrent_promotes_mint_six_distinct_versions_with_zero_exceptions"
        status: pass
    human_judgment: false
  - id: D3
    description: "A second row publishing the same non-NULL (alias, minted_version) is refused by the database itself; any number of NULL-minted-version tombstone rows still insert"
    requirement: "MACH-07"
    verification:
      - kind: unit
        ref: "tests/ledger/test_ledger_generation_uniqueness.py::test_a_duplicate_non_null_alias_minted_version_pair_is_refused_by_the_database"
        status: pass
      - kind: unit
        ref: "tests/ledger/test_ledger_generation_uniqueness.py::test_any_number_of_tombstone_rows_null_minted_version_still_insert"
        status: pass
    human_judgment: false
  - id: D4
    description: "An existing ledger.db carrying the old non-UNIQUE ix_ledger_generation index enforces uniqueness after reopen — the schema upgrade is not a silent no-op"
    requirement: "MACH-07"
    verification:
      - kind: unit
        ref: "tests/ledger/test_ledger_generation_uniqueness.py::test_reopening_a_database_carrying_the_old_plain_index_enforces_uniqueness"
        status: pass
    human_judgment: false
  - id: D5
    description: "The §18 seam envelope is unchanged: no new refusal class added; promote/rollback/retire stay field-for-field identical across in-process, REST and MCP"
    requirement: "API-09"
    verification:
      - kind: other
        ref: "git diff databasise/seam/refusals.py (empty)"
        status: pass
      - kind: integration
        ref: "tests/seam/test_dual_transport.py (7 passed, unmodified)"
        status: pass
    human_judgment: false
  - id: D6
    description: "Full suite stays green with no regressions: 1062 baseline + 5 new tests = 1067 passed, 2 skipped, 0 failed"
    verification:
      - kind: other
        ref: "uv run --frozen python -m pytest -q (full suite)"
        status: pass
    human_judgment: false

# Metrics
duration: ~35min
completed: 2026-09-12
status: complete
---

# Phase 7 Plan 5: Close G-07-1 (concurrent operator-verb race) Summary

**SQLite `BEGIN IMMEDIATE` transaction spans each promotion verb's guard-read-through-append, plus a `UNIQUE(alias, minted_version)` schema backstop — closing 07-REVIEW.md's WR-01 with zero new refusal classes.**

## Performance

- **Duration:** ~35 min (approximate — explicit start timestamp not captured before first read)
- **Completed:** 2026-09-12T15:15:27Z
- **Tasks:** 3
- **Files modified:** 6 (2 created, 4 modified)

## Accomplishments

- Added `Ledger.transaction()` — a `contextlib.contextmanager` issuing `BEGIN IMMEDIATE` on
  enter, committing on clean exit, rolling back and re-raising on any exception (`try`/`finally`
  release, load-bearing per the plan's own fact 4: an unreleased write transaction would stall
  the next `Ledger()` construction for the full busy timeout since `_create_schema()` runs DDL on
  every construction).
- Wrapped all three operator verbs' guard-read-through-`append()` spans in
  `with ledger.transaction():` inside `_promote_sync`, `_rollback_sync`, `_retire_sync`
  (`databasise/seam/engine.py`) — the `ledger = Ledger(...)` construction itself stays outside the
  span (unchanged), only the reads and the append moved inside.
- Replaced the non-unique `ix_ledger_generation` index with `DROP INDEX IF EXISTS
  ix_ledger_generation` followed by `CREATE UNIQUE INDEX IF NOT EXISTS ux_ledger_generation ON
  ledger(alias, minted_version)` — a new name, not a reuse, because reusing the old name is a
  verified silent no-op in SQLite over an existing plain index.
- Two new committed test modules reproduce both races (RED, pre-fix) and prove them closed
  (GREEN, post-fix): `tests/seam/test_operator_verb_concurrency.py` (retire-vs-rollback,
  six-concurrent-promote) and `tests/ledger/test_ledger_generation_uniqueness.py`
  (duplicate-refused, tombstones-stay-distinct, old-database-upgrade-is-not-a-no-op).
- Recorded in `COVERAGE.md` and `PROMOTION-LEDGER-EVIDENCE.md` that no `SeamRefusalError`
  subclass was added — the refusal ladder stays at ten `refusals.py` classes plus
  `UnknownTraceReferenceError`, eleven total, unchanged.

## Task Commits

Each task was committed atomically:

1. **Task 1: Close the reproduced retire-vs-rollback race end-to-end** - `89d55fb` (fix)
2. **Task 2: Refuse a duplicate published (alias, version) at schema level, close promote race** - `3fe2ee0` (fix)
3. **Task 3: Record that the seam surface did not change; prove the whole suite is intact** - `9882a4c` (docs)

_No separate plan-metadata commit — `commit_docs: true` and `.planning/` is tracked in this repo;
the STATE.md/ROADMAP.md/REQUIREMENTS.md metadata commit follows this SUMMARY commit as the
standard fourth commit._

## RED Evidence (pre-fix, captured this session)

Captured by temporarily reverting `ledger.py`/`engine.py` to their pre-fix committed state (via
`git checkout --`, restoring the in-progress fix from a scratchpad backup afterward — no history
rewrite, no stash), running the new tests against the real, unmodified pre-fix code, then
restoring the fix:

**Task 1 (retire-vs-rollback), first trial of 20:**
```
AssertionError: a rollback row committed after a tombstone naming the same generation
(rows=[(1, 'promotion'), (3, 'tombstone'), (4, 'rollback')])
assert 4 < 3
```
A rollback row (ledger id 4) committed strictly after a tombstone (id 3) naming the same
generation, and both `retire()`/`rollback()` calls returned `ok` — no refusal for the loser,
exactly the defect `07-UAT.md`/`07-REVIEW.md` WR-01 named.

**Task 2, uniqueness (2 of 3 new assertions failed pre-fix):**
- `test_a_duplicate_non_null_alias_minted_version_pair_is_refused_by_the_database` — FAILED (no
  `IntegrityError` raised; the duplicate was silently accepted).
- `test_reopening_a_database_carrying_the_old_plain_index_enforces_uniqueness` — FAILED
  (`ux_ledger_generation` not found in `sqlite_master` after reopen).
- `test_any_number_of_tombstone_rows_null_minted_version_still_insert` — passed pre-fix too
  (expected: tombstones were never the broken case).

**Task 2, six-way promote race, first trial of 20:**
```
AssertionError: duplicate minted semver among ['1.0.0', '3.1.0', '3.0.0', '3.2.0', '1.0.0', '2.0.0']
assert 5 == 6
```
Two of six concurrent `promote()` calls both minted `1.0.0`.

## Post-fix Trial Results

- Task 1's retire-vs-rollback test: 3 full runs × 20 trials = 60 trials, 0 row-order violations.
- Task 2's six-way promote test: 3 full runs × 20 trials = 60 trials, 0 duplicate semvers, 0
  exceptions of any kind.
- Full committed suite: `uv run --frozen python -m pytest -q` → **1067 passed, 2 skipped, 0
  failed** (1062 baseline + 5 new tests: 2 in `test_operator_verb_concurrency.py`, 3 in
  `test_ledger_generation_uniqueness.py`), matching the plan's own must-have exactly.

## Files Created/Modified

- `databasise/ledger/ledger.py` - Added `Ledger.transaction()` (BEGIN IMMEDIATE span); replaced
  `ix_ledger_generation` with `ux_ledger_generation` (DROP + CREATE UNIQUE under a new name);
  docstring additions
- `databasise/seam/engine.py` - Wrapped `_rollback_sync`/`_retire_sync`/`_promote_sync`'s
  guard-read-through-append in `with ledger.transaction():`; docstring additions on `promote()`/
  `rollback()`/`retire()`
- `databasise/tests/seam/test_operator_verb_concurrency.py` - New: retire-vs-rollback race test
  (Task 1), six-concurrent-promote race test (Task 2)
- `databasise/tests/ledger/test_ledger_generation_uniqueness.py` - New: duplicate refused,
  tombstones stay distinct, old-index database upgrades rather than silently no-opping
- `databasise/evidence/PROMOTION-LEDGER-EVIDENCE.md` - Amended criterion 2's Tests cell with the
  four new node ids; appended a dated G-07-1 correction note (append-only, existing row body
  untouched)
- `.planning/phases/07-promotion-rollback/COVERAGE.md` - Appended a note under "The refusal
  ladder is part of the surface" recording that this plan added no refusal, and why

## Decisions Made

- **`BEGIN IMMEDIATE` over `asyncio.Lock`** (07-REVIEW.md WR-01's proposed fix): rejected on
  correctness, not size. An `asyncio.Lock` only serializes callers sharing one `Databasise`
  instance on one event loop — it does nothing for a second `Databasise` over the same
  `store_root`, a second process, or REST under more than one worker, all of which reach the same
  `ledger.db`. `BEGIN IMMEDIATE` serializes at the file, covering every writer regardless of
  origin, and is also the smaller diff (one context manager, three `with` lines).
- **`DROP INDEX` + `CREATE UNIQUE INDEX` under a new name**, not `CREATE UNIQUE INDEX IF NOT
  EXISTS` reusing the old name — verified directly against SQLite 3.53.1 that the latter is a
  silent no-op over an existing plain index of the same name, which would ship a fix that does
  nothing on any developer machine already holding a `ledger.db`.
- **The `UNIQUE` index's `sqlite3.IntegrityError` stays unwrapped** — no new `SeamRefusalError`.
  Once `transaction()` encloses every write path, this constraint is a backstop no caller can
  reach through the seam under normal operation; wrapping it would add new §18 surface for a path
  no consumer can reach, mirroring the existing unreachable-by-construction
  `UnrecognisedPromotionVerbError` backstop pattern already in `_promote_sync`.

## Deviations from Plan

None - plan executed exactly as written. The RED-evidence capture technique (temporarily
reverting via `git checkout --` on the two touched files, running against real pre-fix code, then
restoring from a scratchpad backup) was used in place of the more common "write test, watch it
fail before implementing" ordering, since `type="tracer" tdd="true"` still requires genuine RED
evidence but this plan's fix and tests were most safely developed together given the precision
required by the four named traps in the plan's own `key_links` frontmatter (entering
`transaction()` one line late, reusing the old index name, missing the `try/finally`, deleting
`append()`'s own `commit()`). Both races reproduced cleanly on the first trial when checked
against genuine pre-fix code, so the evidence is real and directly observed, not narrated.

## Issues Encountered

None.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- G-07-1 is closed: both races from `07-UAT.md`/`07-REVIEW.md` WR-01 are fixed and covered by
  committed regression tests; the sole outstanding gap from `07-VERIFICATION.md`'s Human
  Verification section is resolved with evidence rather than left as an accepted risk.
- `07-REVIEW.md` WR-02 (`_arm_name_for_node_ids`'s first-match-wins, no uniqueness guard against
  two arms sharing a node-id set) and IN-01 (`rollback()`'s docstring not stating the resolved-arm
  need-not-match rule `retire()`'s docstring already states) remain open, carried forward from
  prior review rounds — out of this plan's scope (`gap_ids: [G-07-1]` only) and not touched here.
- No blockers. Phase 7's `human_needed` status from `07-VERIFICATION.md` should be re-evaluated by
  a fresh `/gsd-verify-work 7` pass now that the sole human-verification item is closed with
  evidence.

---
*Phase: 07-promotion-rollback*
*Completed: 2026-09-12*
