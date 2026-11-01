---
phase: 14-promotion-ledger
reviewed: 2026-10-20T00:00:00Z
depth: deep
iteration: 2
diff_base: dfbc287
diff_head: a1420be
commits:
  - 75f9d59
  - 49b2ee9
  - ccd4fdb
  - a1420be
files_reviewed: 7
files_reviewed_list:
  - databasise/ledger/ledger.py
  - databasise/seam/engine.py
  - databasise/seam/selectors.py
  - databasise/evidence/falsifier2.py
  - databasise/evidence/FALSIFIER-2-EVIDENCE.md
  - docs/gui/API-INVENTORY.md
  - databasise/tests/seam/test_review14_fixes.py
findings:
  critical: 0
  warning: 2
  info: 7
  total: 9
status: issues_found
---

# Phase 14: Code Review Report (iteration 2, fix commits)

**Reviewed:** 2026-10-20
**Depth:** deep (callees traced into `seam/promotion.py` `mint_version`/`derive_mutation_class`, `wirings/resolve.py` `wiring_for_name`, and every caller of `Ledger(...)`/`Ledger.open_existing`; scratch probes run against a1420be)
**Files Reviewed:** 7
**Status:** issues_found (0 Critical, 2 Warning, 7 Info)

## Summary

Scope is `git diff dfbc287 a1420be`: the four fix commits for A-WR-01, A-WR-02, A-WR-03 and B-WR-01 in 14-REVIEW.md. `databasise/tests/seam/test_unresolvable_alias_row_verbs.py` is also in the diff. It was run but not read or diffed, because I could not confirm it is unprotected without reading the requirement ledger. I relied on the fixer's statement that it is unprotected.

Targeted run: `test_review14_fixes.py`, `test_unresolvable_alias_row_verbs.py`, `tests/ledger` and `tests/validator/test_falsifier2_evidence.py` gave **53 passed**. No `-m live` test was run.

Per-fix verdicts:

- **75f9d59 (A-WR-01): resolved, with two residual defects (WR-01, WR-02).**
  - All three probed cases from 14-REVIEW are fixed: the legacy-duplicates 500, the zero-byte file growing to 24576 bytes, and the rollback-journal file being converted to WAL.
  - No SQL statement on the alias read path can write. The statements are `PRAGMA query_only = ON`, one `sqlite_master` SELECT and `by_alias`. The `query_only` handle refuses `INSERT` (pinned by a test) and refuses `BEGIN IMMEDIATE`. Python's legacy isolation mode issues no implicit `BEGIN` before a SELECT, and `close()` does not commit.
  - Zero-byte files and files with no `ledger` table refuse by name as `UnsatisfiableSelectorError` and stay unchanged.
  - D-08's guarantee holds for clean files on the writer path:
    - `test_the_writer_open_still_migrates_a_legacy_file_without_duplicates` passes.
    - A probe shows that a writer open over a current-schema file takes no write lock. It returned in 0.000 s while another connection held `BEGIN IMMEDIATE`.
  - Writer concurrency is safe:
    - Each DDL statement autocommits, and the caught `IntegrityError` leaves no transaction open. A probe ran `transaction()` + `append()` on a duplicates file after the logged warning, and it succeeded.
    - On a duplicates file, a writer open queues behind a held `BEGIN IMMEDIATE` and proceeds once it is released. The probe measured a 1.03 s wait.
  - The residual defects: the connection close still writes `ledger.db` (WR-02). The fix also makes duplicates files writable, and `lineage` is not safe on them (WR-01).
- **49b2ee9 (A-WR-02): resolved, no regression found.**
  - `wiring_for_name` replaces `_wiring_for_row` only on the prior row. For any name that resolves, the two return the same dict (`engine.py:1129-1132`), so classing and minting on healthy aliases are unchanged.
  - The target arm still resolves strictly at `engine.py:2390`, before the transaction.
  - Versions stay monotonic and unique per alias:
    - `by_alias` is the latest non-tombstone row, and tombstones mint nothing.
    - Every row that mints a version mints it from that row's `minted_version`, so by induction the active row always holds the alias's maximum minted version.
    - A MAJOR bump of that maximum therefore cannot equal any existing version, and it is computed inside the same `BEGIN IMMEDIATE` span as the append.
  - No §18 leak: the unresolvable name lands only in the internal `parent` column, and `PromotionResult` carries no row field.
- **ccd4fdb (A-WR-03): resolved.** All four contradictions are fixed, and the three sentences made stale by the other fixes are updated. The fix leaves one new internal inconsistency in the MCP live-check list (IN-03).
- **a1420be (B-WR-01): resolved, per the ruling's wording-only scope.**
  - `render_markdown()` equals the committed file (byte-identical, re-checked).
  - The three part names in `_REGISTRY_TEXT` match the registered parts' `name_at_version`.
  - The names are hard-coded (IN-04).

## Narrative Findings (AI reviewer)

## Warnings

### WR-01: `lineage` reads an arbitrary duplicate row, and 75f9d59 makes writers reach it on duplicates files

**File:** `databasise/ledger/ledger.py:468-473` (made reachable by `ledger.py:323-334`)
**Issue:**
- Before 75f9d59, no writer could open a pre-07-05 file holding duplicate `(alias, minted_version)` rows. Every open raised `IntegrityError`. Now rollback and retire run on such files, and the fixer's report says the duplicates "do not break" `by_alias` and `lineage` because both use `ORDER BY id DESC LIMIT 1`. That is false for `lineage`.
- `lineage` queries `SELECT record_kind, targets_version ... WHERE alias = ? AND minted_version = ?` with `fetchone()` and no `ORDER BY`. Its own docstring relies on "the unique `(alias, minted_version)` index".
- Probe: rows `0.9.0` (promotion), then `1.0.0` (rollback targeting 0.9.0), then `1.0.0` (promotion, the active row). `lineage("prod", "1.0.0")` returned `['1.0.0', '0.9.0']`: it followed the older rollback row, although the active `1.0.0` row is a plain promotion.

Consequences on such a file:
- The retire guard (`engine.py:2710`) refuses to retire `0.9.0` as `ActiveGenerationRetirementError` when it is not in the active lineage.
- The rollback tombstone-in-lineage check (`engine.py:2557-2560`) walks the wrong chain, so it can refuse a legitimate rollback or miss a tombstone.

`generation_state` and `by_alias` are unaffected, because both use `ORDER BY id DESC`.

**Fix:** make `lineage` select the same row the rest of the projections treat as authoritative:
```python
row = self._conn.execute(
    "SELECT record_kind, targets_version FROM ledger "
    "WHERE alias = ? AND minted_version = ? ORDER BY id DESC LIMIT 1",
    (alias, visited[-1]),
).fetchone()
```
Add a regression test that uses the `_legacy_file_with_duplicates` helper with a rollback/promotion pair at the same version. Correct the "only the database-level backstop is missing" comment at `ledger.py:321-322`.

### WR-02: The alias read still writes `ledger.db` on close (WAL checkpoint), contrary to its docstrings and the test name

**File:** `databasise/ledger/ledger.py:181-198`; claims at `selectors.py:280-283`, `ledger.py:169-171`, `API-INVENTORY.md:570`; test `test_review14_fixes.py:76-84`
**Issue:**
- The read-only handle is a read-write connection with `query_only`. `query_only` blocks SQL writes only. It does not stop SQLite's checkpoint-on-close.
- Probe on a WAL file:
  - A writer committed a frame with `wal_autocheckpoint=0`, and the reader opened.
  - The writer closed, so the reader became the last connection.
  - The read created `ledger.db-shm` and `ledger.db-wal`. On `close()` it checkpointed the frames into `ledger.db`, so the main file's bytes changed, and then deleted the `-wal` file.
  - The ledger's logical content is unchanged, but this is a physical write to `ledger.db` on the consumer read path. `mode=ro` (the ruling's letter) would not do it.
- `test_an_alias_read_on_a_legacy_file_resolves_and_changes_nothing` passes only because its WAL is empty at read time.
- Hot-journal rollback in rollback-journal mode is a second write that the plain-path open allows.
- The fixer disclosed both, but the docstrings still state "never changes", without qualification.

**Fix:** pick one of these, then align the docstrings and the test.
- Keep the plain path for the LEDG-06 lifecycle check and disable the close checkpoint on the read handle. I verified this on the venv (Python 3.12.13, SQLite 3.53.1): with it set, the main file is unchanged after close.
  ```python
  self._conn = sqlite3.connect(db_path)
  self._conn.setconfig(sqlite3.SQLITE_DBCONFIG_NO_CKPT_ON_CLOSE, True)
  self._conn.execute("PRAGMA query_only = ON")
  ```
- Or take the `mode=ro` URI form and request the `grant-check-edit` the fixer named for `test_no_ledger_connection_is_left_open`.

With either option, add a test where the WAL holds committed frames when the read happens.

## Info

### IN-01: A non-SQLite or old-shape `ledger.db` still gives a raw sqlite error on the alias read (not a regression)

**File:** `databasise/ledger/ledger.py:186-194`, `databasise/seam/selectors.py:297-301`
**Issue:** Probe results:
- A garbage-bytes file raises `sqlite3.DatabaseError: file is not a database`.
- A `ledger` table without `record_kind` raises `sqlite3.OperationalError: no such column: record_kind`.

Both reach the consumer as a 500. Both behaved the same before the fix, and the fixer disclosed the garbage case.
**Fix:** if the owner wants these cases covered, map `sqlite3.DatabaseError` in the read-only open to a named store fault (not to `UnsatisfiableSelectorError`, which would hide corruption).

### IN-02: Rollback and retire stay blocked on an unresolvable active row, and the vanished generation can never be tombstoned

**File:** `databasise/seam/engine.py:2561-2568`, `2713-2716`
**Issue:**
- The ruling scoped the repair to promote. 14-REVIEW's probe case "retire 1.0.0 refuses although 1.0.0 is not in the active lineage" still refuses until a promote repairs the alias.
- After the repair, retiring the dead generation (`2.0.0`, `retired-arm` in the test) refuses forever, because its target wiring cannot resolve.
- The behaviour matches the documentation, but it is a permanent gap in the ledger.
**Fix:** record the gap as a known limitation. Alternatively, class a tombstone against `None` when the target does not resolve, because a tombstone needs no surface.

### IN-03: The MCP live-check list now describes generations its own promote line no longer creates

**File:** `docs/gui/API-INVENTORY.md:678-680`
**Issue:** `:678` now says a failed bypass trace gives `PartialRunEvidenceError`, so the old "→ 1.0.0, again → 1.1.0" sequence is gone. `:679` (rollback "minted 1.2.0") and `:680` (retire "active 1.2.0", "1.1.0 → tombstone") still assume that sequence.
**Fix:** rewrite the sequence with two complete promotions (1.0.0, 1.1.0) before the rollback and retire steps.

### IN-04: `_REGISTRY_TEXT` hard-codes the probe part names

**File:** `databasise/evidence/falsifier2.py:49-56`
**Issue:**
- The names are correct today.
- The drift gate compares the render to the committed file, not to `probe_registry()`. A renamed or added probe part would therefore leave the provenance statement wrong and the gate green, which is how B-WR-01 arose.
**Fix:** build the sentence from `SHARED_ARTIFACT_WRITER_PROBE_PART.name_at_version`, `EVIDENCE_WRITER_PROBE_PART.name_at_version` and `CODEBASE_MEMORY_MCP_PART.name_at_version`.

### IN-05: Writer opens on a duplicates file contend for the write lock and log on every open

**File:** `databasise/ledger/ledger.py:323-332`
**Issue:**
- On such a file, every promote, rollback and retire open retries `CREATE UNIQUE INDEX`. Each retry takes the write lock, so the open waits behind any held `BEGIN IMMEDIATE`. The probe measured 1.03 s.
- Past the 5 s busy timeout, the open raises a raw `OperationalError`.
- Every retry logs a warning.
- The `transaction()` docstring documents the wait. The repeated warning is noise on a file that can never become clean.
**Fix:** optional. Log once per process for each path, or check `sqlite_master` for `ux_ledger_generation` before attempting the create.

### IN-06: Test gaps left by the fixes

**File:** `databasise/tests/seam/test_review14_fixes.py`
**Issue:**
- No test runs a rollback or retire on a duplicates file. That is the path WR-01 exposes.
- No test covers a read while the WAL holds committed frames (WR-02).
- Promote entries were removed from `test_unresolvable_alias_row_verbs.py`. As far as this review can see, nothing new pins the remaining strict target-arm refusal (`engine.py:2390`) on promote. That arm is likely unreachable, because `resolve_single_arm` returns only wiring names.
**Fix:** add the two ledger tests with WR-01 and WR-02. Add a monkeypatched `wiring_for_name` miss on the target arm, if the owner wants that refusal pinned.

### IN-07: Lint and line-length issues introduced by the fixes

**File:** `databasise/seam/selectors.py:291` (146 characters, docstring not reflowed); `databasise/tests/seam/test_review14_fixes.py:3` (ruff `I001`, import block unsorted)
**Issue:** These are cosmetic. They are new in this diff, while the other ruff hits in the touched files predate it.
**Fix:** reflow the docstring line and run `ruff check --fix` on the new test file.

---

_Reviewed: 2026-10-20_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: deep_
