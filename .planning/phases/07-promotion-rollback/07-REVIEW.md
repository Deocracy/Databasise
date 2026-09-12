---
phase: 07-promotion-rollback
reviewed: 2026-09-12T00:00:00Z
depth: standard
files_reviewed: 5
files_reviewed_list:
  - databasise/ledger/ledger.py
  - databasise/seam/engine.py
  - databasise/tests/ledger/test_ledger_generation_uniqueness.py
  - databasise/tests/seam/test_operator_verb_concurrency.py
  - databasise/evidence/PROMOTION-LEDGER-EVIDENCE.md
findings:
  critical: 0
  warning: 3
  info: 3
  total: 6
status: issues_found
---

# Phase 7: Promotion & Rollback — Code Review Report (Incremental: 07-05, G-07-1)

**Reviewed:** 2026-09-12
**Depth:** standard
**Files Reviewed:** 5
**Status:** issues_found

## Summary

This is an incremental review of 07-05 (G-07-1), whose sole purpose was to close the previous
review's **WR-01** — the check-then-act race across separate autocommit statements in
`promote()`/`rollback()`/`retire()`. The fix is `Ledger.transaction()`, a `BEGIN IMMEDIATE`
context manager now enclosing each verb's guard read through its own `append()`, plus a
`UNIQUE(alias, minted_version)` index (`ux_ledger_generation`) as a database-level backstop.

**WR-01 is genuinely closed** — see "Resolved This Cycle" below. Verified directly (not merely
read) by: tracing every exit path of `transaction()`, confirming no caller performs two appends
inside one `transaction()` span, confirming `transaction()` does not nest anywhere in the current
call graph, and directly executing the SQLite DDL sequence in `_create_schema()` against a
duplicate-seeded database to observe its real failure/self-healing behavior (Python's `sqlite3`
module autocommits DDL statements individually — confirmed empirically, not assumed).

Closing WR-01 introduces its own new concurrency-adjacent gaps, detailed below: every `Ledger()`
construction (including the **read-only** alias lookup `selectors.py` performs on every ordinary
`query()`/`compare()` call) now contends for the same single write lock a `promote`/`rollback`/
`retire` transaction holds, with no `busy_timeout` tuning and no wrapping of a lock-timeout
`sqlite3.OperationalError` into a `SeamRefusalError`; and one of the two new regression tests has a
materially lower single-run detection probability than its sibling despite both being described as
proving the fix. WR-02 and IN-01 from the prior review remain open and unaddressed by 07-05 (carried
forward verbatim below, per this review's own append-only discipline for cross-cycle findings).

## Resolved This Cycle

### WR-01 (prior review) — RESOLVED by 07-05

**Was:** No serialization across concurrent `promote()`/`rollback()`/`retire()` calls on the same
alias — each `_*_sync` body read the alias's current state and appended on two separate autocommit
statements, so a concurrent writer could commit between the read and the append.

**Fix:** `databasise/ledger/ledger.py:140-167` (`Ledger.transaction()`) plus
`databasise/ledger/ledger.py:213-216` (`ux_ledger_generation` unique index, database-level backstop).
Applied at all three call sites: `databasise/seam/engine.py:1203` (`_promote_sync`), `:1336`
(`_rollback_sync`), `:1476` (`_retire_sync`) — the guard read (tombstone check / active-generation
check / prior-version read) and the `append()` that depends on it now share one `BEGIN IMMEDIATE`
span.

**Verified genuinely fixed, not merely re-labeled:**
- Traced every exit path of `transaction()`: normal completion commits (`else` branch); any
  exception (including a refusal raised by a gate-verb posture check or the unreachable-by-
  construction backstop) rolls back and re-raises via `except BaseException`. No path leaves a
  write transaction open.
- Confirmed by direct execution (not assumption) that a `commit()` called after `append()`'s own
  internal `commit()` already closed the span is a safe no-op in `sqlite3` — the "one append per
  transaction" ceiling the docstring documents does not leave a dangling transaction, because
  `append()` is the literal last statement inside all three `with ledger.transaction():` blocks
  (no code runs after it, so the ceiling is never actually exercised by a live call path).
- Confirmed no caller does two appends inside one `transaction()` span (grep + read of all three
  `_*_sync` bodies).
- Confirmed `transaction()` does not nest anywhere in the current call graph: no function called
  from inside a `with ledger.transaction():` block (`by_alias`, `generation_state`,
  `derive_mutation_class`, `mint_version`, `declared_surface`, `resolved_wiring_for_arm`,
  `enforce_gate_verb_posture`) constructs a second `Ledger` or calls `.transaction()` itself.
- `test_operator_verb_concurrency.py`'s two new tests reproduce both races the prior review's
  reproduction measured (retire/rollback outrunning a tombstone; six concurrent promotes minting a
  duplicate semver) and pass against the fixed code. See WR-04 below for a reliability caveat on one
  of the two.

## Warnings

### WR-02 (carried forward, unaddressed by 07-05): `resolve_single_arm`'s promotion-target derivation has no uniqueness guard against two arms sharing a node-id set

**File:** `databasise/seam/promotion.py:115-128` (`_arm_name_for_node_ids`)
**Issue:** `_arm_name_for_node_ids` returns the **first** candidate from `all_wirings()` whose
resolved node-id set equals the trace record's dispatched set:

```python
for name, resolved in all_wirings():
    if frozenset(resolved.get("nodes", {}).keys()) == node_ids:
        return name
```

If a future arm patch changes only a node's `component` (not its node-id membership) — the exact
scenario `derive_mutation_class`'s own docstring calls out as needing separate handling — two arms
could end up with identical node-id sets. `resolve_single_arm` is the sole signal
`promote()`/`rollback()`/`retire()` use to determine which wiring becomes the alias's next
generation; a silent match to the wrong arm here would promote a different wiring than the operator
actually reviewed, with no error raised anywhere. Unchanged by 07-05.

**Fix:** Collect all matches instead of returning on the first, and raise when more than one
candidate's node-id set matches:

```python
matches = [name for name, resolved in all_wirings() if frozenset(resolved.get("nodes", {}).keys()) == node_ids]
if len(matches) > 1:
    raise AssertionError(f"node id set {sorted(node_ids)!r} matches more than one registered wiring: {matches!r}")
if not matches:
    raise AssertionError(...)
return matches[0]
```

### WR-03 (new): Every `Ledger()` construction — including the read-only lookup ordinary queries make — contends for the same write lock `transaction()` holds, with no timeout tuning and no refusal wrapping

**File:** `databasise/ledger/ledger.py:132-244` (`__init__`/`_create_schema`), `140-167`
(`transaction`); `databasise/seam/selectors.py:265` (read-only `Ledger(store_root).by_alias`, called
from every `query()`/`compare()` that resolves an alias-based selector)
**Issue:** `Ledger.__init__` unconditionally runs `_create_schema()` — `CREATE TABLE IF NOT EXISTS`,
two `CREATE INDEX IF NOT EXISTS`, `DROP INDEX IF EXISTS`, `CREATE UNIQUE INDEX IF NOT EXISTS`, two
trigger creations — on **every** construction, including a purely read-only caller. Verified by
direct execution that `sqlite3` autocommits each DDL statement individually rather than batching them
under one transaction, but each still needs SQLite's write lock to run at all. `ledger.py`'s own
module docstring already states this plainly: "an unreleased write transaction would stall the next
`Ledger()` construction for the full busy timeout, because `__init__` always runs `_create_schema`
... even for a read-only caller."

Because `sqlite3.connect(db_path)` (`ledger.py:135`) sets no `timeout=` argument, the busy timeout is
the library default of 5.0 seconds. During the window a `promote()`/`rollback()`/`retire()` call
holds its `BEGIN IMMEDIATE` transaction (guard reads through `append()`), **any other `Ledger()`
construction anywhere in the process — including `selectors.py:265`'s read-only alias lookup that
every ordinary `query()`/`compare()` call performs when resolving a selector — blocks waiting for
that same lock**, and raises a bare `sqlite3.OperationalError: database is locked` if the wait
exceeds 5 seconds. That exception is not caught anywhere on this path and is not a
`SeamRefusalError`: it would surface as a raw, unhandled low-level exception out of an ordinary read
query, in direct tension with this codebase's own stated house style (explicit named refusals, never
a raw exception crossing the seam) — a query should not be able to crash because an unrelated
operator promotion happened to be mid-flight. The same risk applies symmetrically to
`test_six_concurrent_promotes_mint_six_distinct_versions_with_zero_exceptions`'s own "zero exceptions
of any kind" assertion: on a loaded CI runner, six concurrently-serialized short transactions could
in principle exceed 5 seconds cumulatively for reasons unrelated to a real bug, making that assertion
theoretically flaky in the other direction too.

**Fix:** Set an explicit, larger `timeout=` on `sqlite3.connect()` (e.g. 30s) so realistic operator
contention serializes rather than crashes, and wrap a lock-timeout `sqlite3.OperationalError` raised
from `transaction()`/`Ledger.__init__` into a named `SeamRefusalError` subclass (or retry once with
backoff) so it never reaches a caller as a raw low-level exception:

```python
self._conn = sqlite3.connect(db_path, timeout=30.0)
```

### WR-04 (new): The six-concurrent-promotes regression test has a materially lower single-run detection probability than its sibling, despite both being presented as proving the fix

**File:** `databasise/tests/seam/test_operator_verb_concurrency.py:37-39` (`_SIX_WAY_PROMOTE_TRIALS`
comment), `121-148` (`test_six_concurrent_promotes_mint_six_distinct_versions_with_zero_exceptions`)
**Issue:** The retire/rollback race test's own comment explicitly claims 20 trials at the measured
~68% per-trial pre-fix detection rate "makes a regression essentially certain to be caught"
(`1 - 0.32^20 ≈ 1`). The six-way-promote test carries no equivalent claim — it states the measured
rate (~10% per trial, re-measured as 6/60 at plan-authoring time) and the trial count/cost, but never
asserts confidence. The actual math: `1 - 0.9^20 ≈ 0.88` — roughly a **1-in-8 chance that a single CI
run of this test would silently pass even if the `transaction()` fix were fully reverted**, for a
correctness class (duplicate minted semver — a published name reused, violating D-06/CONTRACT §0.4)
that this same evidence document (`PROMOTION-LEDGER-EVIDENCE.md`) cites as proof criterion 2 holds.
A regression test with a ~12% false-negative rate on a single run is a materially weaker guard than
its sibling test, but nothing in the test file or the evidence document flags this asymmetry — a
reader could reasonably assume both tests offer comparable confidence.

**Fix:** Either raise the trial count for this test specifically (e.g. ~45 trials brings single-run
detection to >99%: `1 - 0.9^45 ≈ 0.99`), or state the actual detection probability in the comment so
a future reader (or CI flake investigation) understands this test's guarantee is weaker than its
sibling's, rather than assuming parity.

## Info

### IN-01 (carried forward, unaddressed by 07-05): `rollback()`'s docstring does not state whether the resolved arm must match the rollback target (unlike `retire()`, which states this explicitly)

**File:** `databasise/seam/engine.py:1248-1296`
**Issue:** `retire()`'s docstring explicitly documents that "the resolved arm does not have to
match the generation being retired" as a deliberate, cited design decision. `rollback()` shares the
identical shape — the resolved arm from `_resolve_operator_preconditions` is used only for
`arm_instance_hashes`, never checked against `target.mutation_id` — but `rollback()`'s own
docstring never states this is deliberate, so a future reader may treat it as an oversight and "fix"
it into a match check. Unchanged by 07-05.
**Fix:** Add the same one-paragraph disclosure `retire()` carries, or add a test exercising a
rollback whose trace ids resolve to an arm different from the rollback target, to make the intended
behavior explicit and pinned.

### IN-02 (new): The pre-existing-duplicate-rows index-upgrade failure path is undocumented by any test, though its actual behavior was verified manually during this review

**File:** `databasise/ledger/ledger.py:204-225` (`_create_schema`'s `DROP INDEX`/`CREATE UNIQUE
INDEX` sequence and its accompanying comment)
**Issue:** The comment at `ledger.py:222-225` states plainly that a pre-existing database already
holding duplicate `(alias, minted_version)` rows will fail `CREATE UNIQUE INDEX` at open time and
that "no repair machinery is added for it here" — a deliberate design choice, not a defect. This
review verified by direct execution (not assumption) that the actual failure sequence is: `DROP
INDEX IF EXISTS ix_ledger_generation` commits immediately (SQLite DDL autocommits per-statement
under the `sqlite3` module's legacy transaction handling — confirmed empirically), then `CREATE
UNIQUE INDEX` raises `sqlite3.IntegrityError`, uncaught, out of `Ledger.__init__` — every subsequent
`Ledger()` construction against that file keeps failing identically until the duplicate rows are
manually removed, at which point the migration self-heals (`DROP INDEX IF EXISTS` becomes a no-op,
`CREATE UNIQUE INDEX` then succeeds). This is a genuinely reachable, if rare, production scenario
(any store whose `ledger.db` predates 07-01/07-05's schema and happens to carry a legacy duplicate),
and the on-open crash takes down every ledger read (`active_pointer`, `by_alias`, `history`) as well
as every write, with no test in the suite pinning this exact behavior — only the "old plain index,
no duplicates" upgrade path is tested
(`test_reopening_a_database_carrying_the_old_plain_index_enforces_uniqueness`).
**Fix:** Add a test seeding an actual duplicate `(alias, minted_version)` pair under the old schema
before opening a real `Ledger`, asserting the specific `sqlite3.IntegrityError` and that a second
open (after manually deduplicating) succeeds — turning the comment's claim into a pinned fact rather
than an assertion trusted on the strength of a code comment alone.

### IN-03 (new): Gate-verb refusal paths acquire the sole ledger write lock even though they are guaranteed to never write

**File:** `databasise/seam/engine.py:1213-1214` (`_promote_sync`, inside `with
ledger.transaction():`)
**Issue:** `promote-next`/`promote-now` calls always refuse via `enforce_gate_verb_posture` under
the current milestone's posture (`PROMOTION-LEDGER-EVIDENCE.md` criterion 3, `test_no_gate_verb_
appends_a_row`) — no code path lets them reach `append()`. Yet the check runs *inside* `with
ledger.transaction():`, after `prior_record = ledger.by_alias(alias)` has already opened the
`BEGIN IMMEDIATE` span, so every gate-verb call still takes the same single write lock a real
`promote`/`rollback`/`retire` needs, for zero write benefit. Under concurrent load this adds
avoidable contention on the lock discussed in WR-03, though it is not itself an incorrect-behavior
defect (out of this review's performance scope; noted here only because it interacts with WR-03's
lock-contention concern).
**Fix:** Move the `verb in _GATE_VERBS` / `enforce_gate_verb_posture` check before `with
ledger.transaction():` opens — it only needs `mutation_class`, which is derived from `new_resolved`
and `prior_resolved`; `prior_resolved` can be read via a lightweight, lock-free `by_alias` call
issued outside the transaction (a plain autocommit `SELECT`, not a write), since a gate-verb call
never appends and so never needs the atomicity guarantee `transaction()` provides.

---

_Reviewed: 2026-09-12_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_
