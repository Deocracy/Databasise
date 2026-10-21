---
phase: 14-promotion-ledger
fixed_at: 2026-10-20T00:00:00Z
review_path: .planning/phases/14-promotion-ledger/14-REVIEW.md
iteration: 1
findings_in_scope: 4
fixed: 4
skipped: 0
status: all_fixed
---

# Phase 14: Code Review Fix Report (iteration 1)

**Fixed at:** 2026-10-20
**Source review:** .planning/phases/14-promotion-ledger/14-REVIEW.md (deep, two lanes merged: 0 critical, 4 warning, 14 info)
**Iteration:** 1

**Summary:**
- Findings in scope: 4 (A-WR-01, A-WR-02, A-WR-03, B-WR-01; Info findings out of scope)
- Fixed: 4
- Skipped: 0
- Blocked on a protected-test grant: 0

**Verification:** edits and commits were made in the main checkout (`workflow.use_worktrees` is `false`), and every gate below ran there. Each finding was checked against the source before the fix. A-WR-01 was reproduced at HEAD with a scratch probe: the legacy-duplicates file gave a raw `IntegrityError` and lost `ix_ledger_generation`, a zero-byte file grew to 24576 bytes, and a rollback-journal file was converted to WAL. A-WR-02 was confirmed by reading the code and the unprotected `test_unresolvable_alias_row_verbs.py`, which pinned the refusal on all three verbs. A-WR-03 and B-WR-01 were confirmed by reading the code. The regression tests are in the new, unprotected `databasise/tests/seam/test_review14_fixes.py` (8 tests). The protected list was read from the requirement rows' `test_ref` and `evidence` fields. No protected test file was edited, grepped, read or diffed. No `-m live` test was run.

## Fixed Issues

### A-WR-01: The "read-only" ledger open writes the file and can permanently break alias reads

**Files modified:** `databasise/ledger/ledger.py`, `databasise/seam/selectors.py`, `databasise/seam/engine.py` (docstring), `databasise/tests/seam/test_review14_fixes.py`
**Commit:** 75f9d59
**Status:** fixed: requires human verification (the read-only mechanism differs from the ruling's letter, see below)
**Applied fix:**
- `Ledger.open_existing(store_root, *, read_only=False)`. With `read_only=True` it opens a plain connection with `PRAGMA query_only = ON`. There is no journal-mode change, no schema step, no migration and no commit. A missing file gives `None`, as before. A file with no `ledger` table also gives `None`, and that includes a zero-byte file, which SQLite reads as an empty database. `_resolve_alias` therefore refuses both by name as `UnsatisfiableSelectorError`, identical to the missing-file case, and no raw sqlite error reaches the consumer.
- `_resolve_alias` calls `open_existing(store_root, read_only=True)`.
- The write verbs keep the migrating open. promote uses `Ledger(...)`; rollback and retire use `open_existing(store_root)`.
- **Migration, smallest safe behaviour:** `_create_schema` now runs `CREATE UNIQUE INDEX IF NOT EXISTS ux_ledger_generation` first and `DROP INDEX IF EXISTS ix_ledger_generation` only after the create succeeds. When duplicate `(alias, minted_version)` rows block the create, the `sqlite3.IntegrityError` is caught. The old index stays and a warning is logged on `databasise.ledger.ledger`.
  - *Why this is the smallest safe change:* each DDL statement autocommits, so the old drop-then-create order committed the drop even when the create failed. Swapping the order fixes that loss, and one `except` removes the 500. The duplicates are not repaired, which an append-only ledger could not do anyway.
  - *What the old index covered:* writers on such a file stay serialized by `transaction()`'s `BEGIN IMMEDIATE`, so only the database-level backstop is missing. `by_alias` and `lineage` read with `ORDER BY id DESC LIMIT 1` and `fetchone()`, so the duplicates do not break them.
  - *Cost:* every writer open on such a file retries the create, takes the write lock and logs again. That cost falls only on a file already in this invariant-violating state.
- **Docstrings corrected:**
  - `transaction()` (it said an open over an existing schema "never waits on a writer"). It now says the first-time schema creation and the pre-07-05 unique-index migration take the write lock and can wait up to the busy timeout, and the read-only open never does.
  - The `open_existing`, `_resolve_alias` and module docstrings.
  - The `_rollback_sync` docstring, which called the migrating open "read-only".
  - The `_create_schema` ponytail comment, which said duplicate rows "must surface loudly".

**D-08 is narrowed for the read path.** D-08's reason for running the migrating constructor on `open_existing` was that the index migration must not be skipped on old files. That reason now applies to the writers only. The alias read never migrates, so an old file is migrated by the next promote, rollback or retire, not by a consumer query.

**Deviation from the ruling, for the owner to confirm:** the ruling asks for a `file:...?mode=ro` URI open. That was implemented first. It failed the protected LEDG-06 check `tests/ledger/test_ledger_lifecycle.py::test_no_ledger_connection_is_left_open` ("only 3 ledger.db connections were recorded", where 23 or more were expected). That check recognises ledger connections by their file path, so it no longer saw the alias-read connections. The check cannot be edited, so the open uses the plain path with `PRAGMA query_only = ON` instead. query_only refuses every write statement on the connection, and a test pins this (`append` on the handle raises "attempt to write a readonly database").

The read-only properties the ruling lists all hold and are tested: no WAL change, no schema, no migration, no commit, and no file creation, since the `is_file()` check runs first as before. Two residual differences from `mode=ro`:
1. The file handle is opened read-write. If the file is deleted between the `is_file()` check and the connect, the connect creates an empty file. The old open had the same race.
2. SQLite-internal maintenance still runs: hot-journal recovery, and a WAL checkpoint when the last connection closes. Neither changes the ledger's logical content.

If the owner wants the URI form, the lifecycle check needs a `grant-check-edit` so that it also matches `file:` URIs.

**Tests:**
- `test_an_alias_read_on_a_legacy_file_resolves_and_changes_nothing`: the bytes and indexes are unchanged, and the alias resolves.
- `test_a_zero_byte_ledger_refuses_by_name_and_stays_empty`
- `test_a_file_with_no_ledger_table_refuses_by_name_and_keeps_its_journal_mode`
- `test_an_alias_read_never_converts_a_rollback_journal_file_to_wal`
- `test_the_read_only_handle_refuses_a_write`
- `test_the_writer_open_keeps_the_old_index_and_logs_when_duplicates_block_the_unique_one`
- `test_the_writer_open_still_migrates_a_legacy_file_without_duplicates` (D-08's migration still runs on the writer path).

### A-WR-02: An alias whose active row names an unresolvable wiring is permanently unrepairable

**Files modified:** `databasise/seam/engine.py`, `databasise/tests/seam/test_review14_fixes.py`, `databasise/tests/seam/test_unresolvable_alias_row_verbs.py`
**Commit:** 49b2ee9
**Status:** fixed: requires human verification (classing and minting against an unknown prior)
**Applied fix:** in `_promote_sync`, the prior row is resolved with `wiring_for_name(prior_record.mutation_id)`, and a miss gives `prior_resolved = None` instead of a refusal. The merge note's reading was checked against `promotion.py`:
- `derive_mutation_class(new, None)` classes by the new wiring's own node set.
- `mint_version(prior_version, None, new_surface)` MAJOR-bumps, because `new_surface != None`.
- `prior_version` still comes from `prior_record.minted_version`, so versions stay monotonic.

No change to `promotion.py` was needed. The target arm still resolves strictly through `_wiring_for_row` and refuses as before. Rollback and retire keep their named refusal, as the ruling allows. The `parent` column still records the unresolvable name. The `_wiring_for_row` and `promote` docstrings now describe the repair.

The ruling says "change only engine.py, plus a regression test". `test_unresolvable_alias_row_verbs.py` also had to change: it is not protected, and it asserted the old promote refusal. Its promote entries were removed from both the engine-level and the REST loops, so it now asserts only the rollback and retire refusals.

**Test:** `test_promote_repairs_an_alias_whose_active_row_names_a_retired_arm`. It seeds `prod` with `naive` 1.0.0 and an active `retired-arm` 2.0.0, and checks that the selector refuses. A naive promote then mints 3.0.0 (MAJOR), the selector resolves `prod` to the naive arm, and the new row's `parent` is `retired-arm`.

**Needs a human look:** a repaired alias is always classed as a first promotion and always MAJOR-bumped, even when the vanished wiring had the same surface. No comparable record of that surface exists, so this is the conservative reading.

### A-WR-03: The API inventory contradicts the code in four places

**Files modified:** `docs/gui/API-INVENTORY.md`
**Commit:** ccd4fdb
**Status:** fixed
**Applied fix:**
- **:678.** The MCP live check now says a failed bypass trace gives `PartialRunEvidenceError`, because a failed node makes the run partial.
- **:570.** `LedgerRecord` omits `id` and `created_at`, but `Ledger.history_for_alias` returns `LedgerEntry` rows that carry both (D-09). No route calls it yet.
- **:246.** The "resolved twice" sentence is deleted.
- **:352.** The promote-helper note now gives the `arm_id`-first rule:
  - `_arm_name_for_record` is at promotion.py:144-152.
  - The node-set fallback is at promotion.py:109-141 and 153-154, and covers older records and `"seam"`.
  - Differing `arm_id` values, or differing node sets for older records, predict `DisagreeingPromotionTraceIdsError`.
  - The arm name is returned only in the debug view's `arm_id`.

Three sentences that the A-WR-01 and A-WR-02 fixes made false are also updated in this commit:
- :568 now says promote repairs the alias, and rollback and retire refuse.
- :570 now says `_resolve_alias` opens the ledger read-only.
- The `/promote` refusal list now has the `UnsatisfiableSelectorError` entry for an unresolvable *target* arm, not for the alias row.

**Test:** none (documentation only). `test_seam_doc_consistency.py` and `test_docstring_currency.py` pass.

### B-WR-01: Falsifier-2 gate evidence claims `default_registry()` but is computed against `probe_registry()`

**Files modified:** `databasise/evidence/falsifier2.py`, `databasise/evidence/FALSIFIER-2-EVIDENCE.md`
**Commit:** a1420be
**Status:** fixed
**Applied fix:** the ruling asked for a wording correction, not the review's `evidence_registry()` code change, so the parsing is unchanged.

Rendered text:
- The intro and each wiring's "Resolved against" line now say `probe_registry()`.
- A new paragraph, `_REGISTRY_TEXT`, states that every result in the document is computed against `probe_registry()`. That registry is `default_registry()` plus the catalogued `codebase-memory-mcp@0.1.0` and the two probe-only parts `probe/shared-artifact-writer@0.1.0` and `probe/evidence-writer@0.1.0`. These three parts are admitted only there and none is registered in `default_registry()`.
- The probe section says "the same `probe_registry()`", replacing "plus two probe-only parts".
- The verdict says "plus `probe_registry()` alone".

Docstrings: the module docstring, `evaluate_wiring` and `render_markdown` name `probe_registry()`. The `probe_registry` docstring no longer claims "D-04's seven entries".

`test_falsifier2_evidence.py`'s drift gate requires byte equality with `render_markdown()`, so `FALSIFIER-2-EVIDENCE.md` was re-rendered with `python -m databasise.evidence.falsifier2`. Only the prose lines changed; every table is byte-identical.

**Test:** `tests/evidence` and `tests/validator` together with `test_docstring_currency.py`: 209 passed.

## Skipped Issues

None.

## Wave verification

- **Where:** the main checkout, using `databasise/.venv`.
- **Command:** `databasise/.venv/bin/python -m pytest -q databasise/tests/seam databasise/tests/ledger databasise/tests/parts databasise/tests/parts_core databasise/tests/evidence databasise/tests/validator databasise/tests/wirings databasise/tests/mcp databasise/tests/runner -p no:cacheprovider`
- **Result:** 1916 passed, 0 failed, in 506s, run after all four commits. This includes the 8 new tests and the updated `test_unresolvable_alias_row_verbs.py`.

## Notes for the orchestrator

- **Commits:** each carries the `phase/14` trailer and the Co-Authored-By line.
  - 75f9d59 (A-WR-01)
  - 49b2ee9 (A-WR-02)
  - ccd4fdb (A-WR-03)
  - a1420be (B-WR-01)
- **This report** is not committed. It belongs in a separate `.planning/` commit.
- **Left as is, outside the four findings:**
  - B-WR-01's second effect: W1 and W3 are still parsed against a registry that contains the probe-only parts. The ruling asked for wording only, and the rendered text now states this registry.
  - The docstring of the unprotected `tests/validator/test_falsifier2_evidence.py` (line 2) still says "against the real `default_registry()`".
  - API-INVENTORY's "Ledger reads" row (:701) describes an older `transaction()` docstring.
  - The other stale inventory citations belong to A-IN-06.
- **Not fixed:** a `ledger.db` that is not a SQLite file at all (garbage bytes) still raises a raw `sqlite3.DatabaseError` on the alias read. The ruling covered only the no-table and zero-byte cases.

---

_Fixed: 2026-10-20_
_Fixer: Claude (gsd-code-fixer)_
_Iteration: 1_
