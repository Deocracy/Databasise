---
phase: 14-promotion-ledger
lane: A
reviewed: 2026-10-20T00:00:00Z
depth: deep
diff_base: bb52fbb
files_reviewed: 6
files_reviewed_list:
  - databasise/seam/engine.py
  - databasise/seam/promotion.py
  - databasise/seam/refusals.py
  - databasise/seam/rest.py
  - databasise/mcp/tools.py
  - docs/gui/API-INVENTORY.md
findings:
  critical: 0
  warning: 3
  info: 6
  total: 9
status: issues_found
---

# Phase 14: Code Review Report (Lane A)

**Reviewed:** 2026-10-20
**Depth:** deep (cross-file: `databasise/ledger/ledger.py`, `databasise/wirings/resolve.py`, `databasise/seam/selectors.py`, `databasise/runner/scheduler.py` traced as callees)
**Files Reviewed:** 6
**Status:** issues_found

## Summary

The diff is `git diff bb52fbb HEAD`. It covers the engine verb paths (promote, rollback, retire), the shared prologue, `refuse_partial_evidence` and `_arm_name_for_record`, the two new refusal classes, StrictBool `debug` on REST and MCP, the `_corpus_wiring` move to `load_wiring`, and the API inventory.

What holds:
- The ledger verbs are correct under concurrency. Every guard read (`generation_state`, `by_alias`, `lineage`) and the single `append` run inside one `BEGIN IMMEDIATE` span on the executor thread.
- The connection closes after the transaction exits, because the `with Ledger(...) as ledger, ledger.transaction():` nesting puts the close last.
- I traced the lineage walk against retire-after-rollback, rollback-to-a-rollback and re-promotion sequences. No verb sequence lets the alias serve a tombstoned version.
- The new refusals name only caller input: `trace_ids`, `verb` and `alias`. I found no new §18 leak.
- 93 tests across the Phase 14 seam files pass (plain pytest, `-m "not live"`).

Three things fail:
- The "read-only" ledger open still writes, and on a legacy file it permanently drops an index and turns every alias query into a 500 (probe-confirmed).
- An alias whose active row names a wiring that does not resolve can never be repaired: promote, rollback and retire all refuse (probe-confirmed).
- The API inventory, which Phase 16 plans from, contradicts the code in four places.

## Warnings

### WR-01: The "read-only" ledger open writes the file and can permanently break alias reads

**File:** `databasise/seam/selectors.py:295`, `databasise/seam/engine.py:2542`, `databasise/seam/engine.py:2693`. Callee: `databasise/ledger/ledger.py:159-167` (`open_existing` returns `cls(store_root)`), which runs `_set_wal` at `ledger.py:200-207` and `_create_schema` at `ledger.py:238-313`.

**Issue:** D-08 and the docstrings at `selectors.py:280-282` and `engine.py:2537-2540` say the read path "never creates" anything and that a read must not write (CONTRACT §6). In fact `open_existing` runs the full constructor:
- `PRAGMA journal_mode=WAL` rewrites the header of a file that is not in WAL mode.
- On a legacy file, `DROP INDEX IF EXISTS ix_ledger_generation` and `CREATE UNIQUE INDEX ux_ledger_generation` run, plus a `commit()`.
- Each statement autocommits, so when the unique index fails the drop has already been committed.

Probe (scratchpad `probe_a.py`, run against HEAD). The setup is a legacy `ledger.db` with the old plain `ix_ledger_generation` index and two `(prod, 1.0.0)` rows; this is the G-07-1 race that 07-05 fixed, so such files can exist. Then `_resolve_alias("prod", ...)`, the query path:
- It raises a raw `sqlite3.IntegrityError: UNIQUE constraint failed` (a 500 on `/query`, `/compare` and `/documents` with an alias selector).
- The indexes go from `[ix_ledger_mutation_id, ix_ledger_alias, ix_ledger_generation]` before the read to `[ix_ledger_mutation_id, ix_ledger_alias]` after it. The read dropped the legacy index permanently, and every later read fails the same way.

A second probe started from a rollback-journal file. After one refused alias read, the file was in WAL mode.

Rollback and retire take the same path. The behaviour existed before this phase, but this phase now documents the read path as non-writing, so the claim is false.

**Fix:** Give the read path a real read-only open, and leave migration to the write path (`Ledger(...)` in promote):
```python
@classmethod
def open_existing(cls, store_root):
    db_path = Path(store_root) / "ledger.db"
    if not db_path.is_file():
        return None
    self = cls.__new__(cls)
    self._conn = sqlite3.connect(f"{db_path.as_uri()}?mode=ro", uri=True)
    self._conn.row_factory = sqlite3.Row
    return self
```
Rollback and retire append, so they need a read-write connection. Give them a variant that skips `_set_wal` and `_create_schema`, or map `sqlite3.IntegrityError` raised at open to a named fault. Either way, at minimum the docstrings must stop claiming that the read writes nothing.

### WR-02: An alias whose active row names a wiring that does not resolve is permanently unrecoverable

**File:** `databasise/seam/engine.py:1121-1131` (`_wiring_for_row`), with uses at `engine.py:2400-2404` (promote prior), `2558-2563` (rollback current) and `2709-2711` (retire active).

**Issue:** Each verb resolves the alias's current active row only to derive `mutation_class` and the semver surface. When that row's `mutation_id` no longer resolves (an arm renamed or removed in a later build, or a hand-seeded row), all three verbs refuse with `UnsatisfiableSelectorError`. The selector path refuses as well, so the alias cannot be queried, re-promoted, rolled back to a good version, or retired. The only remaining option is to abandon the alias name.

Probe (scratchpad `probe_b.py`): promote `prod` with naive to get 1.0.0, then append an active row with `mutation_id="ghost"`. After that:
- promote hybrid gives `UnsatisfiableSelectorError`;
- rollback to 1.0.0 gives `UnsatisfiableSelectorError`;
- retire 1.0.0 gives `UnsatisfiableSelectorError`, even though 1.0.0 is not in the active lineage.

The docstring and API-INVENTORY:130 document this as a property ("cannot be repaired through promote, rollback or retire"). It is still a dead end with no recovery verb.

**Fix:** Resolve the *target* strictly, as now. Treat an unresolvable *prior/current/active* wiring as "no comparable prior" when classing and minting:
```python
prior_resolved = wiring_for_name(prior_record.mutation_id) if prior_record is not None else None
# None -> derive_mutation_class/mint_version treat it as a first generation for surface purposes,
# but prior_version still comes from prior_record.minted_version so versions stay monotonic.
```
`mint_version` and `derive_mutation_class` would then need to accept a known `prior_version` with an unknown prior surface, for example by forcing a MAJOR bump. Rollback to a resolvable target then repairs the alias.

### WR-03: The API inventory contradicts the code in four places that Phase 16 and the GUI will rely on

**File:** `docs/gui/API-INVENTORY.md:678`, `:570`, `:246`, `:352`. All four are lines changed in this phase.

**Issue:**
1. `:678` (MCP live check) says "failed bypass trace → 1.0.0, again → 1.1.0". A failed node sets `partial = True` (`runner/scheduler.py:819-820`), and `refuse_partial_evidence` refuses it. Lines `:564` and `:588` of the same document say a failed bypass run gives `PartialRunEvidenceError`.
2. `:570` says "`LedgerRecord` omits the table's `id` and `created_at` columns ..., so no read method returns a row's ordinal or timestamp." That is false since D-09: `Ledger.history_for_alias` returns `LedgerEntry` with both fields (`ledger.py:442-451`). Phase 16 CONN-06/07 are designed on this read.
3. `:246` says "Each selector is resolved twice (engine.py:645 and again in `_execute` at 975), so an alias repointed between the two resolutions runs a wiring the pre-check did not inspect." That is false: `compare` resolves each selector once and passes the wiring to `_execute_resolved` (`engine.py:1270-1286`, SEAM-11).
4. `:352` says "Promotion matches arms by exactly this set". Since D-01 the record's `arm_id` is used first and the node set is only the legacy fallback (`promotion.py:150-154`). The cited lines `promotion.py:109-112, 160-168` no longer point at the matcher.

**Fix:** Correct the four sentences:
- On `:678`, change the bypass case to `PartialRunEvidenceError`.
- On `:570`, say `history_for_alias` returns `id` and `created_at` and has no route yet.
- On `:246`, delete the "resolved twice" sentence.
- On `:352`, describe the `arm_id`-first rule and fix the cited lines.

## Info

### IN-01: `refuse_partial_evidence` fails open when the two lists differ in length

**File:** `databasise/seam/promotion.py:169-173`

**Issue:** `zip(trace_ids, resolved_trace_records)` truncates without an error (ruff B905). The one current caller passes lists of the same length. D-03 makes this the shared rule that Phase 16's CONN-09 preview will call, and a caller that passes a shorter `trace_ids` would let a partial record through.

**Fix:** `zip(trace_ids, resolved_trace_records, strict=True)`.

### IN-02: The `PartialRunEvidenceError` text is wrong on rollback and retire, and names only the first trace

**File:** `databasise/seam/refusals.py:555-559`, `databasise/seam/promotion.py:155-157`

**Issue:** On rollback and retire the refusal is raised because the arm cannot be identified, but the message says the traces "cannot be promotion evidence". D-01 says those verbs accept partial traces. The probe confirmed this message on a rollback. `_arm_name_for_record` also raises inside a set comprehension, so only the first unidentifiable partial trace is named, while the class docstring says "naming exactly the trace ids".

**Fix:** Use a message that is neutral to the verb (for example "come from partial runs whose arm cannot be identified" on that path). Collect every unidentifiable id before raising.

### IN-03: The engine-level `debug` check uses truthiness

**File:** `databasise/seam/engine.py:2266`

**Issue:** StrictBool protects REST and MCP only. An in-process embedder that calls `resolve_trace(tok, debug="false")` receives the full record, including `arm_id`, `wiring_instance_hash` and node ids. Databasise is an embeddable product, so the Python API is also a seam.

**Fix:** `if debug is True:` (or raise `TypeError` on a value that is not a bool).

### IN-04: Docstrings in the verbs are out of date after the reorder

**File:** `databasise/seam/engine.py:2370-2371`, `databasise/seam/engine.py:2485-2487`

**Issue:** The promote docstring still says "The gate-verb and not-built refusal branches raising inside that span are correct". Both now refuse before any `Ledger` exists. The rollback docstring says that `trace_ids` "refuse identically to `promote()`", but promote refuses partial traces and rollback does not.

**Fix:** Update both sentences.

### IN-05: A latent node-id leak in the fallback refusal message

**File:** `databasise/seam/promotion.py:141`

**Issue:** `UnknownTraceReferenceError(trace_reference or f"<run with nodes {sorted(node_ids)!r}>")` puts node ids into a consumer-facing 404 body when `trace_reference` is falsy. The new `_arm_name_for_record` re-raises it at `:158`. It cannot be reached today: the engine always passes the caller's ids, and `TraceStore.resolve("")` refuses first. It was not introduced in this phase.

**Fix:** Use a fixed placeholder such as `"<unidentified run>"`.

### IN-06: Line citations in the API inventory are out of date

**File:** `docs/gui/API-INVENTORY.md:570` (`engine.py:1245, 1372, 1501`), the rollback and retire refusal paragraphs (`engine.py:1339, 1341, 1479, 1481`), and `:246` (`engine.py:644-645`, `975`)

**Issue:** These citations point at unrelated code. `proposer_id="operator"` is now at `engine.py:2442/2586/2722`, and the verb refusals are at `2549-2555` and `2700-2706`.

**Fix:** Regenerate the citations, or cite symbols instead of line numbers.

---

_Reviewed: 2026-10-20_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: deep_
